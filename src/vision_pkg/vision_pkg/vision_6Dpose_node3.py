import time
import threading

import cv2
import numpy as np
import pyrealsense2 as rs
import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from srvs_pkg.srv import GetTargetPose
from ultralytics import YOLO


CAMERA_CONFIGS = {
    "robot1": {
        "serial": "332322072441",
        "service": "/get_target_pose",
        "title": "Robot1",
    },
    "robot2": {
        "serial": "243522075311",
        "service": "/robot2/get_target_pose",
        "title": "Robot2",
    },
}


class DualVisionNode(Node):
    def __init__(self):
        super().__init__("vision_node3")

        serial_descriptor = ParameterDescriptor(dynamic_typing=True)
        self.robot1_serial = self.declare_parameter(
            "robot1_camera_serial",
            CAMERA_CONFIGS["robot1"]["serial"],
            descriptor=serial_descriptor,
        ).value
        self.robot2_serial = self.declare_parameter(
            "robot2_camera_serial",
            CAMERA_CONFIGS["robot2"]["serial"],
            descriptor=serial_descriptor,
        ).value
        self.camera_fps = int(self.declare_parameter("camera_fps", 15).value)
        self.robot2_depth_x_offset_mm = float(
            self.declare_parameter("robot2_depth_x_offset_mm", 32.5).value
        )

        CAMERA_CONFIGS["robot1"]["serial"] = str(self.robot1_serial)
        CAMERA_CONFIGS["robot2"]["serial"] = str(self.robot2_serial)

        self.model_det = YOLO("/home/user2/dis_duplo_ws/best.pt")
        self.model_seg = YOLO("/home/user2/dis_duplo_ws/best_old.pt")
        self.get_logger().info(f"YOLO det task: {self.model_det.task}")
        self.get_logger().info(f"YOLO seg task: {self.model_seg.task}")

        self.cameras = {}
        self.last_visualize_warn = {}
        self.running = True
        for camera_name in ("robot2", "robot1"):
            cfg = CAMERA_CONFIGS[camera_name]
            pipeline = rs.pipeline()
            config = rs.config()
            config.enable_device(cfg["serial"])
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, self.camera_fps)
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, self.camera_fps)
            profile = pipeline.start(config)
            time.sleep(0.5)

            for _ in range(5):
                try:
                    pipeline.wait_for_frames(timeout_ms=1000)
                except Exception as e:
                    self.get_logger().warn(f"{camera_name} warmup frame failed: {e}")
                    break

            self.cameras[camera_name] = {
                "pipeline": pipeline,
                "align": rs.align(rs.stream.color),
                "intrinsics": profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics(),
                "latest_color": None,
                "latest_depth": None,
                "lock": threading.Lock(),
                "title": cfg["title"],
            }

            self.create_service(
                GetTargetPose,
                cfg["service"],
                lambda req, res, name=camera_name: self.get_pose_cb(name, req, res),
            )
            self.get_logger().info(
                f"{camera_name} camera ready: serial={cfg['serial']}, "
                f"fps={self.camera_fps}, service={cfg['service']}"
            )
            self.last_visualize_warn[camera_name] = 0.0

        self.reader_threads = []
        for camera_name in CAMERA_CONFIGS:
            thread = threading.Thread(target=self.camera_reader_loop, args=(camera_name,), daemon=True)
            thread.start()
            self.reader_threads.append(thread)

        self.create_timer(0.033, self.visualize_callback)
        self.get_logger().info("Vision Node3 ready: dual camera raw display + per-camera YOLO services")

    def calculate_refined_yaw(self, rect):
        (cx, cy), (w, h), angle = rect
        yaw = angle if w < h else angle + 90.0
        if yaw > 90:
            yaw -= 180
        if yaw < -90:
            yaw += 180
        return yaw

    def camera_reader_loop(self, camera_name):
        cam = self.cameras[camera_name]
        while self.running and rclpy.ok():
            try:
                frames = cam["pipeline"].wait_for_frames(timeout_ms=1000)
                aligned = cam["align"].process(frames)
                depth_frame = aligned.get_depth_frame()
                color_frame = aligned.get_color_frame()
                if not color_frame or not depth_frame:
                    continue

                color = np.asanyarray(color_frame.get_data()).copy()
                with cam["lock"]:
                    cam["latest_color"] = color
                    cam["latest_depth"] = depth_frame
            except Exception as e:
                self.warn_visualize(camera_name, f"reader failed: {e}")
                time.sleep(0.05)

    def read_camera(self, camera_name, timeout_ms=None):
        cam = self.cameras[camera_name]
        with cam["lock"]:
            color = None if cam["latest_color"] is None else cam["latest_color"].copy()
            depth_frame = cam["latest_depth"]

        if color is None or depth_frame is None:
            return None, None
        return color, depth_frame

    def visualize_callback(self):
        images = []
        for camera_name in ("robot1", "robot2"):
            try:
                color, depth_frame = self.read_camera(camera_name)
                if color is None or depth_frame is None:
                    display_img = self.make_placeholder(camera_name, "NO FRAME")
                    images.append(display_img)
                    continue

                if camera_name == "robot2":
                    images.append(self.render_center_depth_view(camera_name, color, depth_frame))
                    continue

                res_det = self.model_det(color, verbose=False)[0]
                res_seg = self.model_seg(color, verbose=False)[0]
                display_img = res_det.plot()
                cv2.circle(display_img, (320, 240), 5, (0, 0, 255), -1)

                if res_det.boxes is not None:
                    for box in res_det.boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        u = int((xyxy[0] + xyxy[2]) / 2)
                        v = int((xyxy[1] + xyxy[3]) / 2)
                        yaw = self.match_yaw_from_segmentation(res_seg, u, v)
                        z_val = depth_frame.get_distance(u, v)

                        if z_val > 0:
                            x_r, y_r, _ = rs.rs2_deproject_pixel_to_point(
                                self.cameras[camera_name]["intrinsics"],
                                [u, v],
                                z_val,
                            )
                            cv2.putText(
                                display_img,
                                f"X:{x_r*1000:.1f} Y:{y_r*1000:.1f}",
                                (u - 60, v + 25),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 255, 0),
                                2,
                            )
                            cv2.putText(
                                display_img,
                                f"Yaw:{yaw:.1f}",
                                (u - 60, v + 45),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 255, 255),
                                2,
                            )

                cv2.putText(
                    display_img,
                    self.cameras[camera_name]["title"],
                    (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                )
                images.append(display_img)
            except Exception as e:
                self.warn_visualize(camera_name, str(e))
                images.append(self.make_placeholder(camera_name, "ERROR"))

        if len(images) == 2:
            combined = np.hstack(images)
            cv2.imshow("Dual 6D Pose YOLO Cameras", combined)
            cv2.waitKey(1)

    def render_center_depth_view(self, camera_name, color, depth_frame):
        display_img = color.copy()
        u, v = self.get_robot2_depth_pixel(depth_frame)
        z_val = self.get_valid_depth(depth_frame, u, v)

        cv2.circle(display_img, (u, v), 5, (0, 0, 255), -1)
        cv2.putText(
            display_img,
            self.cameras[camera_name]["title"],
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )

        if z_val > 0:
            x_r, y_r, _ = rs.rs2_deproject_pixel_to_point(
                self.cameras[camera_name]["intrinsics"],
                [u, v],
                z_val,
            )
            cv2.putText(
                display_img,
                f"Offset Z:{z_val*1000:.1f}mm",
                (u - 110, v + 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                display_img,
                f"X:{x_r*1000:.1f} Y:{y_r*1000:.1f}",
                (u - 110, v + 58),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
        else:
            cv2.putText(
                display_img,
                "Offset depth: invalid",
                (u - 120, v + 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

        return display_img

    def get_robot2_depth_pixel(self, depth_frame):
        center_u, center_v = 320, 240
        center_z = self.get_valid_depth(depth_frame, center_u, center_v)
        if center_z <= 0:
            return center_u, center_v

        intrinsics = self.cameras["robot2"]["intrinsics"]
        shift_px = int(round((self.robot2_depth_x_offset_mm * intrinsics.fx) / (center_z * 1000.0)))
        u = max(0, min(depth_frame.get_width() - 1, center_u + shift_px))
        v = max(0, min(depth_frame.get_height() - 1, center_v))
        return u, v

    def make_placeholder(self, camera_name, message):
        display_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            display_img,
            self.cameras[camera_name]["title"],
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )
        cv2.putText(
            display_img,
            message,
            (210, 250),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            2,
        )
        return display_img

    def warn_visualize(self, camera_name, message):
        now = time.time()
        if now - self.last_visualize_warn.get(camera_name, 0.0) > 2.0:
            self.get_logger().warn(f"{camera_name} visualize failed: {message}")
            self.last_visualize_warn[camera_name] = now

    def get_valid_depth(self, depth_frame, u, v, search_radius=10):
        z = depth_frame.get_distance(u, v)
        if z > 0:
            return z
        width = depth_frame.get_width()
        height = depth_frame.get_height()
        for r in range(1, search_radius + 1):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    nu, nv = u + dx, v + dy
                    if 0 <= nu < width and 0 <= nv < height:
                        z = depth_frame.get_distance(nu, nv)
                        if z > 0:
                            return z
        return 0.0

    def match_yaw_from_segmentation(self, res_seg, u, v):
        yaw = 0.0
        min_dist = float("inf")
        best_mask_pts = None

        if res_seg.masks is not None and res_seg.boxes is not None:
            for j, seg_box in enumerate(res_seg.boxes):
                s_xyxy = seg_box.xyxy[0].cpu().numpy()
                s_u = int((s_xyxy[0] + s_xyxy[2]) / 2)
                s_v = int((s_xyxy[1] + s_xyxy[3]) / 2)
                dist = ((u - s_u) ** 2 + (v - s_v) ** 2) ** 0.5
                if dist < 40 and dist < min_dist:
                    min_dist = dist
                    if len(res_seg.masks.xy) > j:
                        best_mask_pts = np.int32(res_seg.masks.xy[j])

        if best_mask_pts is not None and len(best_mask_pts) >= 3:
            M = cv2.moments(best_mask_pts)
            if M["m00"] != 0:
                rect = cv2.minAreaRect(best_mask_pts)
                yaw = self.calculate_refined_yaw(rect)
        return yaw

    def get_pose_cb(self, camera_name, request, response):
        target = request.target_color.lower()
        cam = self.cameras[camera_name]

        if camera_name == "robot2":
            return self.get_robot2_center_depth_pose(response)

        if target.startswith("count_"):
            search_color = target.replace("count_", "")
            start_time = time.time()
            max_count = 0
            while time.time() - start_time < 0.5:
                try:
                    img, _ = self.read_camera(camera_name)
                    if img is None:
                        continue
                    results = self.model_det(img, verbose=False)[0]
                    if results.boxes is not None:
                        current_count = sum(
                            1
                            for box in results.boxes
                            if search_color in results.names[int(box.cls[0])].lower()
                        )
                        max_count = max(max_count, current_count)
                except Exception:
                    pass
            response.success = True
            response.x, response.y, response.z, response.yaw = float(max_count), 0.0, 0.0, 0.0
            response.layer = 0
            return response

        self.get_logger().info(f"{camera_name}: measuring '{target}'")
        samples = []
        start_time = time.time()

        while time.time() - start_time < 1.2:
            try:
                img, depth_f = self.read_camera(camera_name)
                if img is None or depth_f is None:
                    continue

                res_det = self.model_det(img, verbose=False)[0]
                res_seg = self.model_seg(img, verbose=False)[0]
                if res_det.boxes is None:
                    continue

                all_z_values = []
                frame_targets = []

                for box in res_det.boxes:
                    cls_name = res_det.names[int(box.cls[0])].lower()
                    xyxy = box.xyxy[0].cpu().numpy()
                    u = int((xyxy[0] + xyxy[2]) / 2)
                    v = int((xyxy[1] + xyxy[3]) / 2)
                    z = self.get_valid_depth(depth_f, u, v)

                    if z <= 0:
                        continue

                    all_z_values.append(z)
                    if target in cls_name:
                        yaw = self.match_yaw_from_segmentation(res_seg, u, v)
                        frame_targets.append({"u": u, "v": v, "z": z, "yaw": yaw})

                if frame_targets and all_z_values:
                    floor_z = max(all_z_values)
                    best = min(frame_targets, key=lambda t: t["z"])
                    calculated_layer = int(round((floor_z - best["z"]) / 0.016)) + 1
                    x, y, z_real = rs.rs2_deproject_pixel_to_point(
                        cam["intrinsics"],
                        [best["u"], best["v"]],
                        best["z"],
                    )
                    samples.append([x, y, z_real, best["yaw"], calculated_layer])

                time.sleep(0.01)
            except Exception:
                continue

        if len(samples) < 5:
            self.get_logger().error(f"{camera_name}: recognition failed")
            response.success = False
            return response

        median_pose = np.median(np.array(samples), axis=0)
        response.success = True
        response.x = float(median_pose[0])
        response.y = float(median_pose[1])
        response.z = float(median_pose[2])
        response.yaw = float(median_pose[3])
        response.layer = int(median_pose[4])

        self.get_logger().info(
            f"{camera_name}: X:{response.x*1000:.1f}, Y:{response.y*1000:.1f}, "
            f"Yaw:{response.yaw:.1f}, Layer:{response.layer}"
        )
        return response

    def get_robot2_center_depth_pose(self, response):
        samples = []
        start_time = time.time()
        cam = self.cameras["robot2"]

        while time.time() - start_time < 0.5:
            try:
                _, depth_f = self.read_camera("robot2")
                if depth_f is None:
                    continue

                u, v = self.get_robot2_depth_pixel(depth_f)
                z = self.get_valid_depth(depth_f, u, v)
                if z <= 0:
                    continue

                x, y, z_real = rs.rs2_deproject_pixel_to_point(cam["intrinsics"], [u, v], z)
                samples.append([x, y, z_real])
                time.sleep(0.01)
            except Exception:
                continue

        if len(samples) < 3:
            self.get_logger().error("robot2: center depth failed")
            response.success = False
            return response

        median_pose = np.median(np.array(samples), axis=0)
        response.success = True
        response.x = float(median_pose[0])
        response.y = float(median_pose[1])
        response.z = float(median_pose[2])
        response.yaw = 0.0
        response.layer = 0

        self.get_logger().info(
            f"robot2 offset depth(+{self.robot2_depth_x_offset_mm:.1f}mm): X:{response.x*1000:.1f}, "
            f"Y:{response.y*1000:.1f}, Z:{response.z*1000:.1f}"
        )
        return response

    def stop_cameras(self):
        self.running = False
        for thread in getattr(self, "reader_threads", []):
            thread.join(timeout=0.5)
        for cam in self.cameras.values():
            cam["pipeline"].stop()


def main():
    rclpy.init()
    node = DualVisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.stop_cameras()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
