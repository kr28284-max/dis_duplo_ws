import time

import rclpy
from rclpy.node import Node
from srvs_pkg.srv import GetTargetPose
from std_srvs.srv import SetBool, Trigger


class BatteryDualDisassembly(Node):
    def __init__(self):
        super().__init__("master_node_dis6")

        self.cli_v1 = self.create_client(GetTargetPose, "/get_target_pose")
        self.cli_r1 = self.create_client(GetTargetPose, "/robot1/robot_move_step")
        self.cli_r2 = self.create_client(GetTargetPose, "/robot2/robot_move_step")
        self.cli_h1 = self.create_client(Trigger, "/robot1/robot_home")
        self.cli_h2 = self.create_client(Trigger, "/robot2/robot_home")

        self.robot1_gripper_service = self.declare_parameter(
            "robot1_gripper_service",
            "/control_gripper",
        ).value
        self.robot2_gripper_service = self.declare_parameter(
            "robot2_gripper_service",
            "/robot2/control_gripper",
        ).value
        self.cli_g1 = self.create_client(SetBool, self.robot1_gripper_service)
        self.cli_g2 = self.create_client(SetBool, self.robot2_gripper_service)

        self.wait_time = float(self.declare_parameter("wait_time", 1.5).value)
        self.grip_wait_time = float(self.declare_parameter("grip_wait_time", 2.5).value)

        self.z_off = float(self.declare_parameter("robot1_z_off", -85.0).value)
        self.z_margin = float(self.declare_parameter("robot1_z_margin", 20.0).value)
        self.robot1_initial_lift_mm = float(self.declare_parameter("robot1_initial_lift_mm", -20.0).value)
        self.robot1_pull_up_mm = float(self.declare_parameter("robot1_pull_up_mm", -20.0).value)
        self.robot1_place_right_x_mm = float(self.declare_parameter("robot1_place_right_x_mm", -100.0).value)
        self.robot1_place_right_y_mm = float(self.declare_parameter("robot1_place_right_y_mm", 0.0).value)
        self.robot1_place_down_mm = float(self.declare_parameter("robot1_place_down_mm", 20.0).value)

        self.robot2_side_x_mm = float(self.declare_parameter("robot2_side_x_mm", 0.0).value)
        self.robot2_side_y_mm = float(self.declare_parameter("robot2_side_y_mm", 0.0).value)
        self.robot2_side_z_mm = float(self.declare_parameter("robot2_side_z_mm", 0.0).value)
        self.robot2_side_yaw_deg = float(self.declare_parameter("robot2_side_yaw_deg", 0.0).value)
        self.robot2_place_down_mm = float(self.declare_parameter("robot2_place_down_mm", 15.0).value)

        # robot_node2의 XY 변환식 역산용 기본 오프셋입니다.
        self.robot1_cam_x_off = -53.0
        self.robot1_cam_y_off = 32.0
        self.robot2_cam_x_off = -53.0
        self.robot2_cam_y_off = 32.0

        self.get_logger().info(
            "Battery dual disassembly ready. "
            f"g1={self.robot1_gripper_service}, g2={self.robot2_gripper_service}"
        )

    def call(self, cli, req):
        while not cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f"Waiting for {cli.srv_name}...")
        future = cli.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def sleep(self):
        time.sleep(self.wait_time)

    def set_gripper(self, cli, closed):
        res = self.call(cli, SetBool.Request(data=closed))
        time.sleep(self.grip_wait_time)
        return res.success

    def move_z(self, cli, dz_mm):
        req = GetTargetPose.Request()
        req.target_size = "Z"
        req.z = dz_mm
        return self.call(cli, req).success

    def move_xy_relative_via_camera_service(self, cli, robot_name, tool_x_mm, tool_y_mm):
        if robot_name == "robot1":
            cam_x_off = self.robot1_cam_x_off
            cam_y_off = self.robot1_cam_y_off
        else:
            cam_x_off = self.robot2_cam_x_off
            cam_y_off = self.robot2_cam_y_off

        req = GetTargetPose.Request()
        req.target_size = "XY"
        req.x = (cam_y_off - tool_y_mm) / 1000.0
        req.y = (tool_x_mm - cam_x_off) / 1000.0
        return self.call(cli, req).success

    def find_target(self, cli, target, retries=3):
        for _ in range(retries):
            res = self.call(cli, GetTargetPose.Request(target_color=target))
            if res.success:
                return res
            time.sleep(0.5)
        return None

    def find_robot1_target(self, target, retries=3):
        return self.find_target(self.cli_v1, target, retries)

    def move_yaw(self, cli, yaw):
        req = GetTargetPose.Request()
        req.target_size = "YAW"
        req.yaw = yaw
        return self.call(cli, req).success

    def move_xy_from_pose(self, cli, pose):
        req = GetTargetPose.Request()
        req.target_size = "XY"
        req.x = pose.x
        req.y = pose.y
        return self.call(cli, req).success

    def move_robot1_separation_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "SEPARATION"
        return self.call(self.cli_r1, req).success

    def robot1_top_pick_yellow(self):
        target = "2x2_yellow"
        self.get_logger().info("1) robot1: 홈자세에서 2x2_yellow xyz/yaw 저장")

        saved_pose = self.find_robot1_target(target)
        if saved_pose is None:
            self.get_logger().error("robot1: 2x2_yellow 인식 실패")
            return False

        self.get_logger().info(
            "robot1 saved pose: "
            f"x={saved_pose.x:.4f}, y={saved_pose.y:.4f}, z={saved_pose.z:.4f}, yaw={saved_pose.yaw:.1f}"
        )

        self.get_logger().info("robot1: 저장한 yaw로 회전")
        self.move_yaw(self.cli_r1, saved_pose.yaw)
        self.sleep()

        self.get_logger().info("robot1: yaw 후 재탐색 없이 저장한 XY 위치로 이동")
        self.move_xy_from_pose(self.cli_r1, saved_pose)
        self.sleep()

        self.get_logger().info("robot1: XY 정렬 후 depth 재측정")
        pose = self.find_robot1_target(target)
        if pose is None:
            self.get_logger().error("robot1: XY 이동 후 depth 재측정 실패")
            return False

        z_move = (pose.z * 1000.0) + self.z_off
        self.move_z(self.cli_r1, z_move - self.z_margin)
        self.sleep()
        self.move_z(self.cli_r1, self.z_margin)
        self.sleep()

        self.set_gripper(self.cli_g1, True)
        self.move_z(self.cli_r1, self.robot1_initial_lift_mm)
        self.sleep()

        self.get_logger().info("robot1: 물체 분리 자세 이동")
        self.move_robot1_separation_pose()
        self.sleep()
        return True

    def robot2_side_hold_blue(self):
        self.get_logger().info("2) robot2: 비전 없이 지정 오프셋으로 밑단 고정 위치 이동")

        if abs(self.robot2_side_yaw_deg) > 0.01:
            self.move_yaw(self.cli_r2, self.robot2_side_yaw_deg)
            self.sleep()

        if abs(self.robot2_side_x_mm) > 0.01 or abs(self.robot2_side_y_mm) > 0.01:
            self.move_xy_relative_via_camera_service(
                self.cli_r2,
                "robot2",
                self.robot2_side_x_mm,
                self.robot2_side_y_mm,
            )
            self.sleep()
        else:
            self.get_logger().warn("robot2_side_x_mm/y_mm가 0입니다. robot2가 XY 이동 없이 파지합니다.")

        if abs(self.robot2_side_z_mm) > 0.01:
            self.move_z(self.cli_r2, self.robot2_side_z_mm)
            self.sleep()
        else:
            self.get_logger().warn("robot2_side_z_mm가 0입니다. robot2가 Z 이동 없이 파지합니다.")

        self.set_gripper(self.cli_g2, True)
        return True

    def robot1_pull_and_place_yellow(self):
        self.get_logger().info("3) robot1: 노랑 블럭 2cm 추가 상승 후 오른쪽에 내려놓기")
        self.move_z(self.cli_r1, self.robot1_pull_up_mm)
        self.sleep()
        self.move_xy_relative_via_camera_service(
            self.cli_r1,
            "robot1",
            self.robot1_place_right_x_mm,
            self.robot1_place_right_y_mm,
        )
        self.sleep()
        self.move_z(self.cli_r1, self.robot1_place_down_mm)
        self.sleep()
        self.set_gripper(self.cli_g1, False)
        self.move_z(self.cli_r1, -self.robot1_place_down_mm)
        self.sleep()
        return True

    def robot2_place_blue(self):
        self.get_logger().info("4) robot2: 잡고 있던 파랑 블럭을 조금 내려놓고 해제")
        self.move_z(self.cli_r2, self.robot2_place_down_mm)
        self.sleep()
        self.set_gripper(self.cli_g2, False)
        self.move_z(self.cli_r2, -self.robot2_place_down_mm)
        self.sleep()
        return True

    def run_battery_once(self):
        self.get_logger().info("배터리 협조 분해 시작: 2x2_yellow / 2x2_blue")
        self.call(self.cli_h1, Trigger.Request())
        self.call(self.cli_h2, Trigger.Request())
        self.set_gripper(self.cli_g1, False)
        self.set_gripper(self.cli_g2, False)

        if not self.robot1_top_pick_yellow():
            return False
        if not self.robot2_side_hold_blue():
            return False
        if not self.robot1_pull_and_place_yellow():
            return False
        if not self.robot2_place_blue():
            return False

        self.call(self.cli_h1, Trigger.Request())
        self.call(self.cli_h2, Trigger.Request())
        self.get_logger().info("배터리 협조 분해 완료")
        return True

    def run(self):
        print("\n=== Battery Dual Disassembly Test ===")
        print("Required services:")
        print("  /get_target_pose")
        print("  /robot1/robot_move_step, /robot2/robot_move_step")
        print("  /robot1/robot_home, /robot2/robot_home")
        print(f"  {self.robot1_gripper_service}, {self.robot2_gripper_service}")
        self.get_logger().info("확인 입력 없이 바로 시작합니다.")
        self.run_battery_once()


def main():
    rclpy.init()
    node = BatteryDualDisassembly()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
