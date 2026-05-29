import rclpy
from rclpy.node import Node
from srvs_pkg.srv import GetTargetPose
from std_srvs.srv import Trigger
import rbpodo as rb
import numpy as np


ROBOT_CONFIGS = {
    "robot1": {
        "ip": "10.0.2.7",
        "cam_x_off": -53.0,
        "cam_y_off": 32.0,
        "home_joint": [-90.0, 10.0, 40.0, 0.0, 130.0, 0.0],
        "separation_joint": [-90.0, 10.0, 40.0, 0.0, 130.0, 0.0],
    },
    "robot2": {
        "ip": "10.0.2.8",
        "cam_x_off": -53.0,
        "cam_y_off": 32.0,
        "home_joint": [-90.0, -77.0, 125.0, 0.0, 42.0, 0.0],
    },
}


class DualRobotNode(Node):
    def __init__(self):
        super().__init__("dual_robot_node")

        self.robots = {}
        for robot_name, cfg in ROBOT_CONFIGS.items():
            robot = rb.Cobot(cfg["ip"])
            rc = rb.ResponseCollector()
            robot.set_operation_mode(rc, rb.OperationMode.Real)

            self.robots[robot_name] = {
                "robot": robot,
                "rc": rc,
                "ip": cfg["ip"],
                "cam_x_off": cfg["cam_x_off"],
                "cam_y_off": cfg["cam_y_off"],
                "home_joint": np.array(cfg["home_joint"], dtype=float),
                "separation_joint": np.array(cfg.get("separation_joint", cfg["home_joint"]), dtype=float),
            }

            self.create_service(
                Trigger,
                f"/{robot_name}/robot_home",
                lambda req, res, name=robot_name: self.home_cb(name, req, res),
            )
            self.create_service(
                GetTargetPose,
                f"/{robot_name}/robot_move_step",
                lambda req, res, name=robot_name: self.move_step_cb(name, req, res),
            )

            self.get_logger().info(
                f"{robot_name} ready: ip={cfg['ip']}, "
                f"services=/{robot_name}/robot_home, /{robot_name}/robot_move_step"
            )

        self.L_VEL = 500
        self.L_ACC = 800
        self.get_logger().info("Dual Robot Node Ready")

    def wait_move(self, robot_name, name="MOVE"):
        handle = self.robots[robot_name]
        robot = handle["robot"]
        rc = handle["rc"]

        started_result = robot.wait_for_move_started(rc, 1.0)
        started = started_result.is_success() if hasattr(started_result, "is_success") else False

        if not started:
            self.get_logger().warn(f"{robot_name} {name} START SKIPPED")
            return True

        robot.wait_for_move_finished(rc)
        return True

    def home_cb(self, robot_name, req, res):
        try:
            handle = self.robots[robot_name]
            handle["robot"].move_j(handle["rc"], handle["home_joint"], 255, 255)
            self.wait_move(robot_name, "HOME")
            res.success = True
        except Exception as e:
            self.get_logger().error(f"{robot_name} HOME Error: {e}")
            res.success = False
        return res

    def move_step_cb(self, robot_name, req, res):
        try:
            handle = self.robots[robot_name]
            robot = handle["robot"]
            rc = handle["rc"]

            if req.target_size == "YAW":
                if abs(req.yaw) < 0.1:
                    self.get_logger().info(f"{robot_name} YAW skipped: {req.yaw:.2f}")
                    res.success = True
                    return res

                pose = np.array([0, 0, 0, 0, 0, req.yaw], dtype=float)
                robot.move_l_rel(rc, pose, self.L_VEL, self.L_ACC, rb.ReferenceFrame.Tool)
                self.wait_move(robot_name, "YAW")

            elif req.target_size == "XY":
                dx = -(req.x * 1000.0) + handle["cam_y_off"]
                dy = (req.y * 1000.0) + handle["cam_x_off"]
                pose = np.array([dy, dx, 0, 0, 0, 0], dtype=float)
                robot.move_l_rel(rc, pose, self.L_VEL, self.L_ACC, rb.ReferenceFrame.Tool)
                self.wait_move(robot_name, "XY")

            elif req.target_size == "Z":
                pose = np.array([0, 0, req.z, 0, 0, 0], dtype=float)
                robot.move_l_rel(rc, pose, self.L_VEL, self.L_ACC, rb.ReferenceFrame.Tool)
                self.wait_move(robot_name, f"Z_MOVE({req.z:.1f})")

            elif req.target_size == "SEPARATION":
                robot.move_j(rc, handle["separation_joint"], 255, 255)
                self.wait_move(robot_name, "SEPARATION")

            else:
                self.get_logger().error(f"{robot_name} unknown target_size: {req.target_size}")
                res.success = False
                return res

            res.success = True
        except Exception as e:
            self.get_logger().error(f"{robot_name} Move Error: {e}")
            res.success = False

        return res


def main():
    rclpy.init()
    node = DualRobotNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
