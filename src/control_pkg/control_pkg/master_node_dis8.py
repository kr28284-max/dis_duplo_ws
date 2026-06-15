# import time

# import rclpy
# from rclpy.node import Node
# from srvs_pkg.srv import GetTargetPose
# from std_srvs.srv import SetBool, Trigger


# class BatteryDualDisassembly(Node):
#     def __init__(self):
#         super().__init__("master_node_dis7")

#         self.cli_v1 = self.create_client(GetTargetPose, "/get_target_pose")
#         self.cli_r1 = self.create_client(GetTargetPose, "/robot1/robot_move_step")
#         self.cli_r2 = self.create_client(GetTargetPose, "/robot2/robot_move_step")
#         self.cli_h1 = self.create_client(Trigger, "/robot1/robot_home")
#         self.cli_h2 = self.create_client(Trigger, "/robot2/robot_home")

#         self.robot1_gripper_service = self.declare_parameter(
#             "robot1_gripper_service",
#             "/control_gripper",
#         ).value
#         self.robot2_gripper_service = self.declare_parameter(
#             "robot2_gripper_service",
#             "/robot2/control_gripper",
#         ).value
#         self.cli_g1 = self.create_client(SetBool, self.robot1_gripper_service)
#         self.cli_g2 = self.create_client(SetBool, self.robot2_gripper_service)

#         self.wait_time = float(self.declare_parameter("wait_time", 1.5).value)
#         self.grip_wait_time = float(self.declare_parameter("grip_wait_time", 2.5).value)

#         self.z_off = float(self.declare_parameter("robot1_z_off", -85.0).value)
#         self.z_margin = float(self.declare_parameter("robot1_z_margin", 20.0).value)
#         self.robot1_initial_lift_mm = float(self.declare_parameter("robot1_initial_lift_mm", -20.0).value)
#         self.robot1_pull_up_mm = float(self.declare_parameter("robot1_pull_up_mm", -30.0).value)

#         self.robot1_cam_x_off = -53.0
#         self.robot1_cam_y_off = 32.0

#         self.get_logger().info(
#             "Dual disassembly ready (keyboard selectable sequence). "
#             f"g1={self.robot1_gripper_service}, g2={self.robot2_gripper_service}"
#         )

#     def call(self, cli, req):
#         while not cli.wait_for_service(timeout_sec=1.0):
#             self.get_logger().info(f"Waiting for {cli.srv_name}...")
#         future = cli.call_async(req)
#         rclpy.spin_until_future_complete(self, future)
#         return future.result()

#     def sleep(self):
#         time.sleep(self.wait_time)

#     def set_gripper(self, cli, closed):
#         res = self.call(cli, SetBool.Request(data=closed))
#         time.sleep(self.grip_wait_time)
#         return res.success

#     def move_z(self, cli, dz_mm):
#         req = GetTargetPose.Request()
#         req.target_size = "Z"
#         req.z = dz_mm
#         return self.call(cli, req).success

#     def find_target_with_retry(self, color, retries=3):
#         for i in range(retries):
#             p = self.call(self.cli_v1, GetTargetPose.Request(target_color=color))
#             if p.success:
#                 return p
#             time.sleep(0.5) 
#         return None

#     def target_fallbacks(self, target):
#         if target.startswith("2x2_"):
#             return [target, target.replace("2x2_", "4x2_", 1)]
#         if target.startswith("4x2_"):
#             return [target, target.replace("4x2_", "2x2_", 1)]
#         return [target]

#     def find_target_candidate_with_retry(self, target, retries=3):
#         for candidate in self.target_fallbacks(target):
#             p = self.find_target_with_retry(candidate, retries=retries)
#             if not p:
#                 continue
#             if candidate != target:
#                 self.get_logger().warn(f"{target} 대신 대체 타겟 {candidate}로 진행")
#             return p, candidate
#         return None, None

#     def move_robot1_separation_pose(self):
#         req = GetTargetPose.Request()
#         req.target_size = "SEPARATION"
#         return self.call(self.cli_r1, req).success

#     def move_robot2_separation_pose(self):
#         req = GetTargetPose.Request()
#         req.target_size = "SEPARATION"
#         return self.call(self.cli_r2, req).success

#     def move_robot1_drop_pose(self):
#         req = GetTargetPose.Request()
#         req.target_size = "DROP"
#         return self.call(self.cli_r1, req).success

#     def move_robot1_drop2_pose(self):
#         req = GetTargetPose.Request()
#         req.target_size = "DROP2"
#         return self.call(self.cli_r1, req).success

#     def move_robot2_drop_pose(self):
#         req = GetTargetPose.Request()
#         req.target_size = "DROP"
#         return self.call(self.cli_r2, req).success

#     def robot1_top_pick(self, target, top_label, expected_layer=None):
#         self.get_logger().info(f"1) robot1: 비전 3단계 스캔 시작 [{target}]")

#         p, selected_target = self.find_target_candidate_with_retry(target)
#         if not p:
#             self.get_logger().error("robot1: 1차 스캔(Yaw) 실패")
#             return False
#         req_yaw = GetTargetPose.Request()
#         req_yaw.target_size = "YAW"
#         req_yaw.yaw = p.yaw
#         self.call(self.cli_r1, req_yaw)
#         self.sleep()

#         p = self.find_target_with_retry(selected_target)
#         if not p:
#             self.get_logger().error("robot1: 2차 스캔(XY) 실패")
#             return False
#         req_xy = GetTargetPose.Request()
#         req_xy.target_size = "XY"
#         req_xy.x = p.x
#         req_xy.y = p.y
#         self.call(self.cli_r1, req_xy)
#         self.sleep()

#         p = self.find_target_with_retry(selected_target)
#         if not p:
#             self.get_logger().error("robot1: 3차 스캔(Z) 실패")
#             return False
        
#         z_move = (p.z * 1000.0) + self.z_off
#         self.move_z(self.cli_r1, z_move - self.z_margin)
#         self.sleep()
#         self.move_z(self.cli_r1, self.z_margin)
#         self.sleep()

#         self.set_gripper(self.cli_g1, True)
#         self.sleep()
        
#         self.move_z(self.cli_r1, self.robot1_initial_lift_mm)
#         self.sleep()

#         self.get_logger().info("robot1: 물체 분리 자세 이동")
#         self.move_robot1_separation_pose()
#         self.sleep()
#         return True

#     def robot2_side_hold(self, bottom_label):
#         self.get_logger().info(f"2) robot2: 지정된 분리 조인트로 이동하여 하단({bottom_label}) 고정")
#         if not self.move_robot2_separation_pose():
#             self.get_logger().error("robot2: 고정 자세 이동 실패")
#             return False
#         self.sleep()

#         self.set_gripper(self.cli_g2, True)
#         return True

#     def robot1_pull_up(self, top_label):
#         self.get_logger().info(f"3) robot1: 상단({top_label}) 블럭 3cm 추가 상승하여 강제 분리")
#         self.move_z(self.cli_r1, self.robot1_pull_up_mm)
#         self.sleep()
#         return True

#     def robot2_return_home_holding(self, bottom_label):
#         self.get_logger().info(f"4) robot2: 하단({bottom_label}) 블럭 잡은 상태로 홈 위치 복귀")
#         self.call(self.cli_h2, Trigger.Request())
#         self.sleep()
#         return True

#     def robot2_release_and_home(self, bottom_label):
#         self.get_logger().info(f"6) robot2: 하단({bottom_label}) 고정 해제 후 홈 위치 복귀")
#         self.set_gripper(self.cli_g2, False)
#         self.sleep()
#         self.call(self.cli_h2, Trigger.Request())
#         self.sleep()
#         return True

#     def robot1_drop_top_and_home(self, top_label, drop_slot="DROP"):
#         self.get_logger().info(f"5) robot1: 상단({top_label}) 블럭 {drop_slot} 조인트로 이동하여 내려놓고 홈 복귀")
#         if drop_slot == "DROP2":
#             moved = self.move_robot1_drop2_pose()
#         else:
#             moved = self.move_robot1_drop_pose()

#         if not moved:
#             self.get_logger().error(f"robot1: {drop_slot} 자세 이동 실패")
#             return False
#         self.sleep()
        
#         self.set_gripper(self.cli_g1, False)
#         self.sleep()
        
#         self.call(self.cli_h1, Trigger.Request())
#         self.sleep()
#         return True

#     def robot2_drop_bottom_and_home(self, bottom_label):
#         self.get_logger().info(f"6) robot2: 하단({bottom_label}) 블럭 DROP 조인트로 이동하여 내려놓고 홈 복귀")
#         if not self.move_robot2_drop_pose():
#             self.get_logger().error("robot2: DROP 자세 이동 실패")
#             return False
#         self.sleep()
        
#         self.set_gripper(self.cli_g2, False)
#         self.sleep()

#         self.call(self.cli_h2, Trigger.Request())
#         self.sleep()
#         return True

#     def run_disassembly_once(self, name, top_target, top_label, bottom_label):
#         self.get_logger().info(f"{name} 협조 분해 시작: 2층 {top_label} / 1층 {bottom_label}")
#         self.call(self.cli_h1, Trigger.Request())
#         self.call(self.cli_h2, Trigger.Request())
#         self.set_gripper(self.cli_g1, False)
#         self.set_gripper(self.cli_g2, False)

#         # 1. 로봇1 스캔 -> 파지 -> 분리자세 이동
#         if not self.robot1_top_pick(top_target, top_label): return False
        
#         # 2. 로봇2 분리자세 이동 -> 하단 고정
#         if not self.robot2_side_hold(bottom_label): return False
        
#         # 3. 로봇1 잡아당기기 (분리)
#         if not self.robot1_pull_up(top_label): return False
        
#         # 4. 로봇2 홈으로 복귀 (그리퍼 닫은 상태 유지)
#         if not self.robot2_return_home_holding(bottom_label): return False
        
#         # 5. 로봇1 DROP 조인트로 이동 -> 내려놓기 -> 홈 복귀
#         if not self.robot1_drop_top_and_home(top_label): return False
        
#         # 6. 로봇2 DROP 조인트로 이동 -> 내려놓기 -> 홈 복귀
#         if not self.robot2_drop_bottom_and_home(bottom_label): return False

#         self.get_logger().info(f"🎉 {name} 협조 분해 완벽 종료")
#         return True

#     def run_battery_once(self):
#         return self.run_disassembly_once(
#             "배터리",
#             top_target="2x2_yellow",
#             top_label="2x2 노랑",
#             bottom_label="2x2 파랑",
#         )

#     def run_magnet_once(self):
#         return self.run_disassembly_once(
#             "자석",
#             top_target="2x2_blue",
#             top_label="2x2 파랑",
#             bottom_label="2x2 빨강",
#         )

#     def run_estop_once(self):
#         return self.run_disassembly_once(
#             "E-stop",
#             top_target="2x2_red",
#             top_label="2x2 빨강",
#             bottom_label="2x4 노랑",
#         )

#     def robot1_pick_layer_and_drop(self, target, label, expected_layer, drop_slot, bottom_label=None):
#         self.get_logger().info(f"{expected_layer}층 분해 시작: {label}")
#         if not self.robot1_top_pick(target, label, expected_layer=expected_layer):
#             self.get_logger().error(f"{expected_layer}층 {label} 분해 실패")
#             return False

#         if bottom_label is not None:
#             if not self.robot2_side_hold(bottom_label):
#                 return False
#             if not self.robot1_pull_up(label):
#                 self.robot2_drop_bottom_and_home(bottom_label)
#                 return False

#             if not self.robot2_return_home_holding(bottom_label):
#                 return False

#             if not self.robot1_drop_top_and_home(label, drop_slot=drop_slot):
#                 self.robot2_drop_bottom_and_home(bottom_label)
#                 return False

#             if not self.robot2_drop_bottom_and_home(bottom_label):
#                 return False
#             return True

#         return self.robot1_drop_top_and_home(label, drop_slot=drop_slot)

#     def run_three_layer_once(self, name, layers):
#         self.get_logger().info(f"{name} 3층 분해 시작")
#         self.call(self.cli_h1, Trigger.Request())
#         self.call(self.cli_h2, Trigger.Request())
#         self.set_gripper(self.cli_g1, False)
#         self.set_gripper(self.cli_g2, False)

#         drop_slots = {
#             3: "DROP",
#             2: "DROP2",
#             1: "DROP3",
#         }

#         for index, (layer, target, label) in enumerate(layers):
#             bottom_label = layers[index + 1][2] if index + 1 < len(layers) else None
#             if not self.robot1_pick_layer_and_drop(
#                 target,
#                 label,
#                 layer,
#                 drop_slots.get(layer, "DROP"),
#                 bottom_label=bottom_label,
#             ):
#                 return False

#         self.get_logger().info(f"🎉 {name} 3층 분해 완료")
#         return True

#     # ---- [새로 추가된 4층 분해용 함수] ----
#     def run_four_layer_once(self, name, layers):
#         self.get_logger().info(f"{name} 4층 분해 시작")
#         self.call(self.cli_h1, Trigger.Request())
#         self.call(self.cli_h2, Trigger.Request())
#         self.set_gripper(self.cli_g1, False)
#         self.set_gripper(self.cli_g2, False)

#         drop_slots = {
#             4: "DROP",
#             3: "DROP2",
#             2: "DROP3",
#             1: "DROP4",
#         }

#         for index, (layer, target, label) in enumerate(layers):
#             bottom_label = layers[index + 1][2] if index + 1 < len(layers) else None
#             if not self.robot1_pick_layer_and_drop(
#                 target,
#                 label,
#                 layer,
#                 drop_slots.get(layer, "DROP"),
#                 bottom_label=bottom_label,
#             ):
#                 return False

#         self.get_logger().info(f"🎉 {name} 4층 분해 완료")
#         return True
#     # ---------------------------------------

#     def run_carrot_once(self):
#         return self.run_three_layer_once(
#             "당근",
#             [
#                 (3, "2x2_green", "2x2 초록"),
#                 (2, "2x2_yellow", "2x2 노랑"),
#                 (1, "2x2_yellow", "2x2 노랑"),
#             ],
#         )

#     def run_small_tree_once(self):
#         return self.run_three_layer_once(
#             "작은 나무",
#             [
#                 (3, "2x2_green", "2x2 초록"),
#                 (2, "4x2_green", "2x4 초록"),
#                 (1, "2x2_yellow", "2x2 노랑"),
#             ],
#         )

#     def run_traffic_light_once(self):
#         return self.run_three_layer_once(
#             "신호등",
#             [
#                 (3, "2x2_red", "2x2 빨강"),
#                 (2, "2x2_yellow", "2x2 노랑"),
#                 (1, "2x2_green", "2x2 초록"),
#             ],
#         )

#     def run_hammer_once(self):
#         return self.run_three_layer_once(
#             "망치",
#             [
#                 (3, "4x2_blue", "2x4 파랑"),
#                 (2, "2x2_red", "2x2 빨강"),
#                 (1, "2x2_red", "2x2 빨강"),
#             ],
#         )

#     # ---- [큰 당근 시퀀스 함수] ----
#     def run_big_carrot_once(self):
#         return self.run_four_layer_once(
#             "큰 당근",
#             [
#                 (4, "2x2_green", "2x2 초록"),
#                 (3, "4x2_yellow", "4x2 노랑"),
#                 (2, "2x2_yellow", "2x2 노랑"),
#                 (1, "2x2_yellow", "2x2 노랑"),
#             ],
#         )
#     # ---------------------------------------

#     def run(self):
#         print("\n=== Master Node Dis7 Keyboard Select ===")
#         print("1: 배터리  (2층 2x2 노랑 / 1층 2x2 파랑)")
#         print("2: 자석    (2층 2x2 파랑 / 1층 2x2 빨강)")
#         print("3: E-stop  (2층 2x2 빨강 / 1층 2x4 노랑)")
#         print("4: 당근    (3층 2x2 초록 / 2층 2x2 노랑 / 1층 2x2 노랑)")
#         print("5: 작은 나무 (3층 2x2 초록 / 2층 2x4 초록 / 1층 2x2 노랑)")
#         print("6: 신호등  (3층 2x2 빨강 / 2층 2x2 노랑 / 1층 2x2 초록)")
#         print("7: 망치    (3층 2x4 파랑 / 2층 2x2 빨강 / 1층 2x2 빨강)")
#         print("8: 큰 당근 (4층 2x2 초록 / 3층 4x2 노랑 / 2층 2x2 노랑 / 1층 2x2 노랑)") # 메뉴 추가
#         print("q: 종료")

#         actions = {
#             "1": self.run_battery_once,
#             "battery": self.run_battery_once,
#             "배터리": self.run_battery_once,
#             "2": self.run_magnet_once,
#             "magnet": self.run_magnet_once,
#             "자석": self.run_magnet_once,
#             "3": self.run_estop_once,
#             "estop": self.run_estop_once,
#             "e-stop": self.run_estop_once,
#             "비상정지": self.run_estop_once,
#             "4": self.run_carrot_once,
#             "carrot": self.run_carrot_once,
#             "당근": self.run_carrot_once,
#             "5": self.run_small_tree_once,
#             "tree": self.run_small_tree_once,
#             "smalltree": self.run_small_tree_once,
#             "small_tree": self.run_small_tree_once,
#             "작은나무": self.run_small_tree_once,
#             "나무": self.run_small_tree_once,
#             "6": self.run_traffic_light_once,
#             "traffic": self.run_traffic_light_once,
#             "trafficlight": self.run_traffic_light_once,
#             "traffic_light": self.run_traffic_light_once,
#             "신호등": self.run_traffic_light_once,
#             "7": self.run_hammer_once,
#             "hammer": self.run_hammer_once,
#             "망치": self.run_hammer_once,
#             "8": self.run_big_carrot_once,           
#             "bigcarrot": self.run_big_carrot_once,   
#             "큰당근": self.run_big_carrot_once,      
#             "큰 당근": self.run_big_carrot_once,    
#         }

#         while rclpy.ok():
#             user_input = input("\n선택하세요 [1/2/3/4/5/6/7/8/q]: ").strip().replace(" ", "").lower() # 입력 프롬프트 
#             if user_input in ("q", "quit", "exit", "종료"):
#                 self.get_logger().info("키보드 선택 모드를 종료합니다.")
#                 break

#             action = actions.get(user_input)
#             if action is None:
#                 print("잘못된 입력입니다. 1~8 또는 q 중에서 선택하세요.")
#                 continue

#             action()


# def main():
#     rclpy.init()
#     node = BatteryDualDisassembly()
#     try:
#         node.run()
#     finally:
#         node.destroy_node()
#         rclpy.shutdown()


# if __name__ == "__main__":
#     main()

import time

import rclpy
from rclpy.node import Node
from srvs_pkg.srv import GetTargetPose
from std_srvs.srv import SetBool, Trigger


class BatteryDualDisassembly(Node):
    def __init__(self):
        super().__init__("master_node_dis7")

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
        self.robot1_pull_up_mm = float(self.declare_parameter("robot1_pull_up_mm", -30.0).value)

        self.robot1_cam_x_off = -53.0
        self.robot1_cam_y_off = 32.0

        self.get_logger().info(
            "Dual disassembly ready (keyboard selectable sequence). "
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

    def find_target_with_retry(self, color, retries=3):
        for i in range(retries):
            p = self.call(self.cli_v1, GetTargetPose.Request(target_color=color))
            if p.success:
                return p
            time.sleep(0.5) 
        return None

    def target_fallbacks(self, target):
        if target.startswith("2x2_"):
            return [target, target.replace("2x2_", "4x2_", 1)]
        if target.startswith("4x2_"):
            return [target, target.replace("4x2_", "2x2_", 1)]
        return [target]

    def find_target_candidate_with_retry(self, target, retries=3):
        for candidate in self.target_fallbacks(target):
            p = self.find_target_with_retry(candidate, retries=retries)
            if not p:
                continue
            if candidate != target:
                self.get_logger().warn(f"{target} 대신 대체 타겟 {candidate}로 진행")
            return p, candidate
        return None, None

    def move_robot1_separation_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "SEPARATION"
        return self.call(self.cli_r1, req).success

    def move_robot2_separation_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "SEPARATION"
        return self.call(self.cli_r2, req).success

    def move_robot1_drop_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "DROP"
        return self.call(self.cli_r1, req).success

    def move_robot1_drop2_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "DROP2"
        return self.call(self.cli_r1, req).success

    def move_robot1_drop3_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "DROP3"
        return self.call(self.cli_r1, req).success

    def move_robot1_drop4_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "DROP4"
        return self.call(self.cli_r1, req).success

    def move_robot2_drop_pose(self):
        req = GetTargetPose.Request()
        req.target_size = "DROP"
        return self.call(self.cli_r2, req).success

    # ---- [수정됨: yaw_offset 파라미터 추가] ----
    def robot1_top_pick(self, target, top_label, expected_layer=None, yaw_offset=90.0):
        self.get_logger().info(f"1) robot1: 비전 3단계 스캔 시작 [{target}] (Yaw Offset: {yaw_offset}도)")

        p, selected_target = self.find_target_candidate_with_retry(target)
        if not p:
            self.get_logger().error("robot1: 1차 스캔(Yaw) 실패")
            return False
            
        req_yaw = GetTargetPose.Request()
        req_yaw.target_size = "YAW"
        # 비전에서 잡은 기본 Yaw 각도에 전달받은 오프셋(예: 90도)을 더함
        req_yaw.yaw = p.yaw + yaw_offset 
        self.call(self.cli_r1, req_yaw)
        self.sleep()

        # 2차/3차 스캔에서는 2x2_* <-> 4x2_* 간 상호 대체 허용
        p, selected_target = self.find_target_candidate_with_retry(target)
        if not p:
            self.get_logger().error("robot1: 2차 스캔(XY) 실패")
            return False
        req_xy = GetTargetPose.Request()
        req_xy.target_size = "XY"
        req_xy.x = p.x
        req_xy.y = p.y
        self.call(self.cli_r1, req_xy)
        self.sleep()

        p, selected_target = self.find_target_candidate_with_retry(target)
        if not p:
            self.get_logger().error("robot1: 3차 스캔(Z) 실패")
            return False
        
        z_move = (p.z * 1000.0) + self.z_off
        self.move_z(self.cli_r1, z_move - self.z_margin)
        self.sleep()
        self.move_z(self.cli_r1, self.z_margin)
        self.sleep()

        self.set_gripper(self.cli_g1, True)
        self.sleep()
        
        self.move_z(self.cli_r1, self.robot1_initial_lift_mm)
        self.sleep()

        self.get_logger().info("robot1: 물체 분리 자세 이동")
        self.move_robot1_separation_pose()
        self.sleep()
        return True

    def robot2_side_hold(self, bottom_label):
        self.get_logger().info(f"2) robot2: 지정된 분리 조인트로 이동하여 하단({bottom_label}) 고정")
        if not self.move_robot2_separation_pose():
            self.get_logger().error("robot2: 고정 자세 이동 실패")
            return False
        self.sleep()

        self.set_gripper(self.cli_g2, True)
        return True

    def robot1_pull_up(self, top_label):
        self.get_logger().info(f"3) robot1: 상단({top_label}) 블럭 3cm 추가 상승하여 강제 분리")
        self.move_z(self.cli_r1, self.robot1_pull_up_mm)
        self.sleep()
        return True

    def robot2_return_home_holding(self, bottom_label):
        self.get_logger().info(f"4) robot2: 하단({bottom_label}) 블럭 잡은 상태로 홈 위치 복귀")
        self.call(self.cli_h2, Trigger.Request())
        self.sleep()
        return True

    def robot2_release_and_home(self, bottom_label):
        self.get_logger().info(f"6) robot2: 하단({bottom_label}) 고정 해제 후 홈 위치 복귀")
        self.set_gripper(self.cli_g2, False)
        self.sleep()
        self.call(self.cli_h2, Trigger.Request())
        self.sleep()
        return True

    def robot1_drop_top_and_home(self, top_label, drop_slot="DROP"):
        self.get_logger().info(f"5) robot1: 상단({top_label}) 블럭 {drop_slot} 조인트로 이동하여 내려놓고 홈 복귀")
        if drop_slot == "DROP2":
            moved = self.move_robot1_drop2_pose()
        elif drop_slot == "DROP3":
            moved = self.move_robot1_drop3_pose()
        elif drop_slot == "DROP4":
            moved = self.move_robot1_drop4_pose()
        else:
            moved = self.move_robot1_drop_pose()

        if not moved:
            self.get_logger().error(f"robot1: {drop_slot} 자세 이동 실패")
            return False
        self.sleep()
        
        self.set_gripper(self.cli_g1, False)
        self.sleep()
        
        self.call(self.cli_h1, Trigger.Request())
        self.sleep()
        return True

    def robot2_drop_bottom_and_home(self, bottom_label):
        self.get_logger().info(f"6) robot2: 하단({bottom_label}) 블럭 DROP 조인트로 이동하여 내려놓고 홈 복귀")
        if not self.move_robot2_drop_pose():
            self.get_logger().error("robot2: DROP 자세 이동 실패")
            return False
        self.sleep()
        
        self.set_gripper(self.cli_g2, False)
        self.sleep()

        self.call(self.cli_h2, Trigger.Request())
        self.sleep()
        return True

    def run_disassembly_once(self, name, top_target, top_label, bottom_label):
        self.get_logger().info(f"{name} 협조 분해 시작: 2층 {top_label} / 1층 {bottom_label}")
        self.call(self.cli_h1, Trigger.Request())
        self.call(self.cli_h2, Trigger.Request())
        self.set_gripper(self.cli_g1, False)
        self.set_gripper(self.cli_g2, False)

        # 1. 로봇1 스캔 -> 파지 -> 분리자세 이동
        if not self.robot1_top_pick(top_target, top_label): return False
        
        # 2. 로봇2 분리자세 이동 -> 하단 고정
        if not self.robot2_side_hold(bottom_label): return False
        
        # 3. 로봇1 잡아당기기 (분리)
        if not self.robot1_pull_up(top_label): return False
        
        # 4. 로봇2 홈으로 복귀 (그리퍼 닫은 상태 유지)
        if not self.robot2_return_home_holding(bottom_label): return False
        
        # 5. 로봇1 DROP 조인트로 이동 -> 내려놓기 -> 홈 복귀
        if not self.robot1_drop_top_and_home(top_label): return False
        
        # 6. 로봇2 DROP 조인트로 이동 -> 내려놓기 -> 홈 복귀
        if not self.robot2_drop_bottom_and_home(bottom_label): return False

        self.get_logger().info(f"🎉 {name} 협조 분해 완벽 종료")
        return True

    def run_battery_once(self):
        return self.run_disassembly_once(
            "배터리",
            top_target="2x2_yellow",
            top_label="2x2 노랑",
            bottom_label="2x2 파랑",
        )

    def run_magnet_once(self):
        return self.run_disassembly_once(
            "자석",
            top_target="2x2_blue",
            top_label="2x2 파랑",
            bottom_label="2x2 빨강",
        )

    def run_estop_once(self):
        return self.run_disassembly_once(
            "E-stop",
            top_target="2x2_red",
            top_label="2x2 빨강",
            bottom_label="2x4 노랑",
        )

    # ---- [수정됨: yaw_offset 인자 전달] ----
    def robot1_pick_layer_and_drop(self, target, label, expected_layer, drop_slot, bottom_label=None, yaw_offset=0.0):
        self.get_logger().info(f"{expected_layer}층 분해 시작: {label}")
        if not self.robot1_top_pick(target, label, expected_layer=expected_layer, yaw_offset=yaw_offset):
            self.get_logger().error(f"{expected_layer}층 {label} 분해 실패")
            return False

        if bottom_label is not None:
            if not self.robot2_side_hold(bottom_label):
                return False
            if not self.robot1_pull_up(label):
                self.robot2_drop_bottom_and_home(bottom_label)
                return False

            if not self.robot2_return_home_holding(bottom_label):
                return False

            if not self.robot1_drop_top_and_home(label, drop_slot=drop_slot):
                self.robot2_drop_bottom_and_home(bottom_label)
                return False

            if not self.robot2_drop_bottom_and_home(bottom_label):
                return False
            return True

        return self.robot1_drop_top_and_home(label, drop_slot=drop_slot)

    # ---- [수정됨: layer 데이터에서 yaw_offset 추출 로직 추가] ----
    def run_three_layer_once(self, name, layers):
        self.get_logger().info(f"{name} 3층 분해 시작")
        self.call(self.cli_h1, Trigger.Request())
        self.call(self.cli_h2, Trigger.Request())
        self.set_gripper(self.cli_g1, False)
        self.set_gripper(self.cli_g2, False)

        drop_slots = {
            3: "DROP",
            2: "DROP2",
            1: "DROP3",
        }

        for index, layer_info in enumerate(layers):
            layer = layer_info[0]
            target = layer_info[1]
            label = layer_info[2]
            # 튜플에 4번째 인자(yaw_offset)가 있으면 가져오고, 없으면 0.0을 사용
            yaw_offset = layer_info[3] if len(layer_info) > 3 else 0.0
            
            bottom_label = layers[index + 1][2] if index + 1 < len(layers) else None
            
            if not self.robot1_pick_layer_and_drop(
                target,
                label,
                layer,
                drop_slots.get(layer, "DROP"),
                bottom_label=bottom_label,
                yaw_offset=yaw_offset,
            ):
                return False

        self.get_logger().info(f"🎉 {name} 3층 분해 완료")
        return True

    def run_four_layer_once(self, name, layers):
        self.get_logger().info(f"{name} 4층 분해 시작")
        self.call(self.cli_h1, Trigger.Request())
        self.call(self.cli_h2, Trigger.Request())
        self.set_gripper(self.cli_g1, False)
        self.set_gripper(self.cli_g2, False)

        drop_slots = {
            4: "DROP",
            3: "DROP2",
            2: "DROP3",
            1: "DROP4",
        }

        for index, layer_info in enumerate(layers):
            layer = layer_info[0]
            target = layer_info[1]
            label = layer_info[2]
            # 튜플에 4번째 인자(yaw_offset)가 있으면 가져오고, 없으면 0.0을 사용
            yaw_offset = layer_info[3] if len(layer_info) > 3 else 0.0
            
            bottom_label = layers[index + 1][2] if index + 1 < len(layers) else None
            
            if not self.robot1_pick_layer_and_drop(
                target,
                label,
                layer,
                drop_slots.get(layer, "DROP"),
                bottom_label=bottom_label,
                yaw_offset=yaw_offset,
            ):
                return False

        self.get_logger().info(f"🎉 {name} 4층 분해 완료")
        return True

    def run_carrot_once(self):
        return self.run_three_layer_once(
            "당근",
            [
                (3, "2x2_green", "2x2 초록"),
                (2, "2x2_yellow", "2x2 노랑"),
                (1, "2x2_yellow", "2x2 노랑"),
            ],
        )

    def run_small_tree_once(self):
        return self.run_three_layer_once(
            "작은 나무",
            [
                (3, "2x2_green", "2x2 초록"),
                (2, "4x2_green", "2x4 초록"),
                (1, "2x2_yellow", "2x2 노랑"),
            ],
        )

    def run_traffic_light_once(self):
        return self.run_three_layer_once(
            "신호등",
            [
                (3, "2x2_red", "2x2 빨강"),
                (2, "2x2_yellow", "2x2 노랑"),
                (1, "2x2_green", "2x2 초록"),
            ],
        )

    def run_hammer_once(self):
        return self.run_three_layer_once(
            "망치",
            [
                (3, "4x2_blue", "2x4 파랑"),
                (2, "2x2_red", "2x2 빨강"),
                (1, "2x2_red", "2x2 빨강"),
            ],
        )

    # ---- [수정됨: 4층 초록 블록에 90도 회전(yaw_offset) 추가] ----
    def run_big_carrot_once(self):
        return self.run_four_layer_once(
            "큰 당근",
            [
                # 4층을 잡을 때 손목을 90도 꺾어서 파지함
                (4, "2x2_green", "2x2 초록", 90.0), 
                (3, "4x2_yellow", "4x2 노랑", 0.0),
                (2, "2x2_yellow", "2x2 노랑", 0.0),
                (1, "2x2_yellow", "2x2 노랑", 0.0),
            ],
        )

    def run(self):
        print("\n=== Master Node Dis7 Keyboard Select ===")
        print("1: 배터리  (2층 2x2 노랑 / 1층 2x2 파랑)")
        print("2: 자석    (2층 2x2 파랑 / 1층 2x2 빨강)")
        print("3: E-stop  (2층 2x2 빨강 / 1층 2x4 노랑)")
        print("4: 당근    (3층 2x2 초록 / 2층 2x2 노랑 / 1층 2x2 노랑)")
        print("5: 작은 나무 (3층 2x2 초록 / 2층 2x4 초록 / 1층 2x2 노랑)")
        print("6: 신호등  (3층 2x2 빨강 / 2층 2x2 노랑 / 1층 2x2 초록)")
        print("7: 망치    (3층 2x4 파랑 / 2층 2x2 빨강 / 1층 2x2 빨강)")
        print("8: 큰 당근 (4층 2x2 초록 / 3층 4x2 노랑 / 2층 2x2 노랑 / 1층 2x2 노랑)")
        print("q: 종료")

        actions = {
            "1": self.run_battery_once,
            "battery": self.run_battery_once,
            "배터리": self.run_battery_once,
            "2": self.run_magnet_once,
            "magnet": self.run_magnet_once,
            "자석": self.run_magnet_once,
            "3": self.run_estop_once,
            "estop": self.run_estop_once,
            "e-stop": self.run_estop_once,
            "비상정지": self.run_estop_once,
            "4": self.run_carrot_once,
            "carrot": self.run_carrot_once,
            "당근": self.run_carrot_once,
            "5": self.run_small_tree_once,
            "tree": self.run_small_tree_once,
            "smalltree": self.run_small_tree_once,
            "small_tree": self.run_small_tree_once,
            "작은나무": self.run_small_tree_once,
            "나무": self.run_small_tree_once,
            "6": self.run_traffic_light_once,
            "traffic": self.run_traffic_light_once,
            "trafficlight": self.run_traffic_light_once,
            "traffic_light": self.run_traffic_light_once,
            "신호등": self.run_traffic_light_once,
            "7": self.run_hammer_once,
            "hammer": self.run_hammer_once,
            "망치": self.run_hammer_once,
            "8": self.run_big_carrot_once,
            "bigcarrot": self.run_big_carrot_once,
            "큰당근": self.run_big_carrot_once,
            "큰 당근": self.run_big_carrot_once,
        }

        while rclpy.ok():
            user_input = input("\n선택하세요 [1/2/3/4/5/6/7/8/q]: ").strip().replace(" ", "").lower()
            if user_input in ("q", "quit", "exit", "종료"):
                self.get_logger().info("키보드 선택 모션을 종료합니다.")
                break

            action = actions.get(user_input)
            if action is None:
                print("잘못된 입력입니다. 1~8 또는 q 중에서 선택하세요.")
                continue

            action()


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