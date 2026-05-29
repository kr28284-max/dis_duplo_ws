# import rclpy
# from rclpy.node import Node
# from srvs_pkg.srv import GetTargetPose
# from std_srvs.srv import SetBool, Trigger
# import time
# import math

# class MasterNode(Node):
#     def __init__(self):
#         super().__init__('master_node')
#         self.cli_v = self.create_client(GetTargetPose, '/get_target_pose')
#         self.cli_r = self.create_client(GetTargetPose, '/robot_move_step')
#         self.cli_g = self.create_client(SetBool, '/control_gripper')
#         self.cli_h = self.create_client(Trigger, '/robot_home')
        
#         self.Z_OFF = -85.0
#         self.Z_MARGIN = 20.0
#         self.WAIT_TIME = 1.5 
        
#     def call(self, cli, req):
#         while not cli.wait_for_service(timeout_sec=1.0):
#             self.get_logger().info(f'Waiting for {cli.srv_name}...')
#         future = cli.call_async(req)
#         rclpy.spin_until_future_complete(self, future)
#         return future.result()

#     def find_target_with_retry(self, color, retries=3):
#         """비전 노드에 타겟 좌표를 요청하고 실패 시 재시도 (스캔 역할)"""
#         for i in range(retries):
#             p = self.call(self.cli_v, GetTargetPose.Request(target_color=color))
#             if p.success:
#                 return p
#             time.sleep(0.5) 
#         return None

#     def pick_target(self, color, expected_layer=None):
#         layer_text = f" ({expected_layer}층)" if expected_layer else ""
#         self.get_logger().info(f"👀 스캔 및 파지 중: [{color.upper()}]{layer_text}")
        
#         p = self.find_target_with_retry(color)
#         if not p: return False

#         if expected_layer is not None:
#             if p.layer != expected_layer:
#                 self.get_logger().warn(f"⚠️ 층수 불일치! 예상: {expected_layer}층 / 비전 인식: {p.layer}층 (파지 시도함)")

#         req = GetTargetPose.Request(); req.yaw = p.yaw; req.target_size = "YAW"
#         self.call(self.cli_r, req)
#         time.sleep(self.WAIT_TIME) 

#         p = self.find_target_with_retry(color)
#         if not p: return False
#         req = GetTargetPose.Request(); req.x = p.x; req.y = p.y; req.target_size = "XY"
#         self.call(self.cli_r, req)
#         time.sleep(self.WAIT_TIME) 

#         p = self.find_target_with_retry(color)
#         if not p: return False
        
#         z_move = (p.z * 1000.0) + self.Z_OFF
#         self.call(self.cli_r, GetTargetPose.Request(z=z_move - self.Z_MARGIN, target_size="Z"))
#         time.sleep(self.WAIT_TIME) 
#         self.call(self.cli_r, GetTargetPose.Request(z=self.Z_MARGIN, target_size="Z"))
#         time.sleep(self.WAIT_TIME) 

#         self.call(self.cli_g, SetBool.Request(data=True))
#         time.sleep(self.WAIT_TIME) 
#         self.call(self.cli_r, GetTargetPose.Request(z=-50.0, target_size="Z")) 
#         time.sleep(self.WAIT_TIME) 
#         return True

#     def drop_target_to_home(self):
#         self.call(self.cli_h, Trigger.Request())
#         self.call(self.cli_g, SetBool.Request(data=False))
#         time.sleep(1.0)

#     # ==========================================
#     # 💥 조합별 분해 시퀀스 모음 (기존 2~3층)
#     # ==========================================
#     def disassemble_battery(self):
#         self.get_logger().info("\n🔋 [배터리 분해] 2층 노랑 -> 1층 파랑")
#         if self.pick_target("2x2_yellow", expected_layer=2):
#             self.drop_target_to_home()
#             self.get_logger().info("✅ 배터리 분해 완료!")

#     def disassemble_magnet(self):
#         self.get_logger().info("\n🧲 [자석 분해] 2층 파랑 -> 1층 빨강")
#         if self.pick_target("2x2_blue", expected_layer=2):
#             self.drop_target_to_home()
#             self.get_logger().info("✅ 자석 분해 완료!")

#     def disassemble_emergency_stop(self):
#         self.get_logger().info("\n🛑 [비상정지 분해] 2층 빨강 -> 1층 노랑(4x2)")
#         if self.pick_target("2x2_red", expected_layer=2):
#             self.drop_target_to_home()
#             self.get_logger().info("✅ 비상정지 분해 완료!")

#     def disassemble_traffic_light(self):
#         self.get_logger().info("\n🚦 [신호등 분해] 3층 빨강 -> 2층 노랑 -> 1층 파랑")
#         if not self.pick_target("2x2_red", expected_layer=3):
#             return
#         self.drop_target_to_home()
#         if not self.pick_target("2x2_yellow", expected_layer=2): return
#         self.drop_target_to_home()
#         if not self.pick_target("2x2_blue", expected_layer=1): return
#         self.drop_target_to_home()
#         self.get_logger().info("🎉 신호등 완벽 분해 성공!")

#     def disassemble_carrot(self):
#         self.get_logger().info("\n🥕 [당근 분해] 3층 노랑 -> 2층 파랑 -> 1층 노랑")
#         # 조립 코드(build_carrot) 기준: 노랑(Pick) -> 파랑(Base) -> 노랑(Pick)
#         if not self.pick_target("2x2_yellow", expected_layer=3):
#             return
#         self.drop_target_to_home()
#         if not self.pick_target("2x2_blue", expected_layer=2): return
#         self.drop_target_to_home()
#         if not self.pick_target("2x2_yellow", expected_layer=1): return
#         self.drop_target_to_home()
#         self.get_logger().info("🎉 당근 완벽 분해 성공!")

#     # ==========================================
#     # 💥 4층 블록 추가 분해 시퀀스 (큰 당근, 버거, 아이스크림, 큰 나무)
#     # ==========================================
#     def disassemble_big_carrot(self):
#         self.get_logger().info("\n🥕🥕 [큰 당근 분해] 4층 파랑(2x2) -> 3층 노랑(4x2) -> 2층 노랑(2x2) -> 1층 노랑(2x2)")
#         # 조립 코드 레시피 기준: 상단이 2x2_blue (이미지의 초록색을 파란색으로 대체 조립한 것으로 가정)
#         if not self.pick_target("2x2_blue", expected_layer=4):
#             # 만약 이미지대로 초록색을 사용했다면 "2x2_green"으로 스위칭
#             if not self.pick_target("2x2_green", expected_layer=4):
#                 self.get_logger().error("❌ 큰 당근 상단(4층)을 찾을 수 없습니다.")
#                 return
#         self.drop_target_to_home()

#         if not self.pick_target("4x2_yellow", expected_layer=3): return
#         self.drop_target_to_home()

#         if not self.pick_target("2x2_yellow", expected_layer=2): return
#         self.drop_target_to_home()

#         if not self.pick_target("2x2_yellow", expected_layer=1): return
#         self.drop_target_to_home()
#         self.get_logger().info("🎉 대왕 당근 완벽 분해 성공!")

#     def disassemble_burger(self):
#         self.get_logger().info("\n🍔 [버거 분해] 4층 노랑(4x2) -> 3층 빨강(2x2) -> 2층 빨강(4x2) -> 1층 노랑(4x2)")
#         if not self.pick_target("4x2_yellow", expected_layer=4):
#             self.get_logger().error("❌ 버거 상단 빵(4층 노랑 4x2)을 찾을 수 없습니다.")
#             return
#         self.drop_target_to_home()

#         if not self.pick_target("2x2_red", expected_layer=3): return
#         self.drop_target_to_home()

#         if not self.pick_target("4x2_red", expected_layer=2): return
#         self.drop_target_to_home()

#         if not self.pick_target("4x2_yellow", expected_layer=1): return
#         self.drop_target_to_home()
#         self.get_logger().info("🎉 버거 완벽 분해 성공!")

#     def disassemble_ice_cream(self):
#         self.get_logger().info("\n🍦 [아이스크림 분해] 4층 노랑(2x2) -> 3층 파랑/빨강(2x2) -> 2층 노랑(4x2) -> 1층 노랑(2x2)")
#         # 조립 코드 레시피에 맞춰 4층을 노란색으로 처리
#         if not self.pick_target("2x2_yellow", expected_layer=4):
#             # 만약 이미지대로 초록색이라면 "2x2_green" 시도
#             if not self.pick_target("2x2_green", expected_layer=4):
#                 self.get_logger().error("❌ 아이스크림 상단(4층)을 찾을 수 없습니다.")
#                 return
#         self.drop_target_to_home()

#         # 3층은 2x2 두 개가 나란히 결합되어 있으므로 순차적으로 분해
#         self.get_logger().info("🍦 [아이스크림 3층 분해] 2x2 파랑, 2x2 빨강 수거")
#         if self.pick_target("2x2_blue", expected_layer=3):
#             self.drop_target_to_home()
#         if self.pick_target("2x2_red", expected_layer=3):
#             self.drop_target_to_home()

#         if not self.pick_target("4x2_yellow", expected_layer=2): return
#         self.drop_target_to_home()

#         if not self.pick_target("2x2_yellow", expected_layer=1): return
#         self.drop_target_to_home()
#         self.get_logger().info("🎉 아이스크림 완벽 분해 성공!")

#     def disassemble_big_tree(self):
#         self.get_logger().info("\n🌳 [큰 나무 분해] 4층 빨강(2x2) -> 3층 빨강(4x2) -> 2층 빨강(2x2, 4x2) -> 1층 노랑(2x2)")
#         # 조립 코드의 big_tree 레시피 기준 색상 적용 (잎=빨강, 기둥=노랑)
#         if not self.pick_target("2x2_red", expected_layer=4):
#             self.get_logger().error("❌ 큰 나무 상단(4층 빨강 2x2)을 찾을 수 없습니다.")
#             return
#         self.drop_target_to_home()

#         if not self.pick_target("4x2_red", expected_layer=3): return
#         self.drop_target_to_home()

#         # 2층에는 4x2 빨강과 2x2 빨강이 나란히 있음
#         self.get_logger().info("🌳 [큰 나무 2층 분해] 4x2 빨강, 2x2 빨강 수거")
#         if self.pick_target("4x2_red", expected_layer=2):
#             self.drop_target_to_home()
#         if self.pick_target("2x2_red", expected_layer=2):
#             self.drop_target_to_home()

#         if not self.pick_target("2x2_yellow", expected_layer=1): return
#         self.drop_target_to_home()
#         self.get_logger().info("🎉 큰 나무 완벽 분해 성공!")


#     # ==========================================
#     # ⌨️ 대화형 메인 루프
#     # ==========================================
#     def run(self):
#         self.get_logger().info("🚀 로봇 초기화 중...")
#         self.call(self.cli_h, Trigger.Request())
#         self.call(self.cli_g, SetBool.Request(data=False))
#         time.sleep(1.0) 

#         print("\n" + "="*60)
#         print("🤖 듀플로 지능형 분해 시스템 가동 (4층 지원) 🤖")
#         print("사용 가능한 명령어: 당근, 신호등, 배터리, 자석, 비상정지")
#         print("                 큰당근, 큰나무, 아이스크림, 버거, 종료")
#         print("="*60)

#         while rclpy.ok():
#             try:
#                 user_input = input("\n⌨️ 분해할 조합을 입력하세요: ").strip().replace(" ", "")
                
#                 if user_input in ["종료", "exit", "quit"]:
#                     self.get_logger().info("👋 프로그램을 종료합니다.")
#                     break
#                 elif "당근" in user_input and "큰" not in user_input:
#                     self.disassemble_carrot()
#                 elif "신호등" in user_input:
#                     self.disassemble_traffic_light()
#                 elif "배터리" in user_input:
#                     self.disassemble_battery()
#                 elif "자석" in user_input:
#                     self.disassemble_magnet()
#                 elif "비상" in user_input: 
#                     self.disassemble_emergency_stop()
#                 elif "큰당근" in user_input:
#                     self.disassemble_big_carrot()
#                 elif "버거" in user_input or "햄버거" in user_input:
#                     self.disassemble_burger()
#                 elif "아이스크림" in user_input:
#                     self.disassemble_ice_cream()
#                 elif "큰나무" in user_input:
#                     self.disassemble_big_tree()
#                 elif user_input == "":
#                     continue
#                 else:
#                     self.get_logger().warn(f"❓ '{user_input}'은(는) 알 수 없는 명령어입니다. 다시 입력해주세요.")
                
#                 # 시퀀스가 끝난 후 로봇을 홈으로 원복
#                 self.call(self.cli_h, Trigger.Request())
                
#             except KeyboardInterrupt:
#                 self.get_logger().info("\n👋 강제 종료 감지. 프로그램을 종료합니다.")
#                 break

# def main():
#     rclpy.init()
#     node = MasterNode()
#     node.run()
#     node.destroy_node()
#     rclpy.shutdown()

# if __name__ == '__main__':
#     main()



import rclpy
from rclpy.node import Node
from srvs_pkg.srv import GetTargetPose
from std_srvs.srv import SetBool, Trigger
import time
import math

class MasterNode(Node):
    def __init__(self):
        super().__init__('master_node')
        self.cli_v = self.create_client(GetTargetPose, '/get_target_pose')
        self.cli_r = self.create_client(GetTargetPose, '/robot_move_step')
        self.cli_g = self.create_client(SetBool, '/control_gripper')
        self.cli_h = self.create_client(Trigger, '/robot_home')
        
        self.Z_OFF = -85.0
        self.Z_MARGIN = 20.0
        
        # ⏱️ 기본 로봇 팔 이동 대기 시간
        self.WAIT_TIME = 1.5 
        
        # ⏱️ 꽉 잡기 위한 '그리퍼 전용' 넉넉한 대기 시간 (추가됨)
        # 만약 여전히 놓친다면 이 숫자를 3.0 등으로 늘려주세요.
        self.GRIP_WAIT_TIME = 2.5 
        
    def call(self, cli, req):
        while not cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Waiting for {cli.srv_name}...')
        future = cli.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def find_target_with_retry(self, color, retries=3):
        """비전 노드에 타겟 좌표를 요청하고 실패 시 재시도 (스캔 역할)"""
        for i in range(retries):
            p = self.call(self.cli_v, GetTargetPose.Request(target_color=color))
            if p.success:
                return p
            time.sleep(0.5) 
        return None

    def pick_target(self, color, expected_layer=None):
        layer_text = f" ({expected_layer}층)" if expected_layer else ""
        self.get_logger().info(f"👀 스캔 및 파지 중: [{color.upper()}]{layer_text}")
        
        p = self.find_target_with_retry(color)
        if not p: return False

        if expected_layer is not None:
            if p.layer != expected_layer:
                self.get_logger().warn(f"⚠️ 층수 불일치! 예상: {expected_layer}층 / 비전 인식: {p.layer}층 (파지 시도함)")

        req = GetTargetPose.Request(); req.yaw = p.yaw; req.target_size = "YAW"
        self.call(self.cli_r, req)
        time.sleep(self.WAIT_TIME) 

        p = self.find_target_with_retry(color)
        if not p: return False
        req = GetTargetPose.Request(); req.x = p.x; req.y = p.y; req.target_size = "XY"
        self.call(self.cli_r, req)
        time.sleep(self.WAIT_TIME) 

        p = self.find_target_with_retry(color)
        if not p: return False
        
        z_move = (p.z * 1000.0) + self.Z_OFF
        self.call(self.cli_r, GetTargetPose.Request(z=z_move - self.Z_MARGIN, target_size="Z"))
        time.sleep(self.WAIT_TIME) 
        self.call(self.cli_r, GetTargetPose.Request(z=self.Z_MARGIN, target_size="Z"))
        time.sleep(self.WAIT_TIME) 

        # 👇 [수정됨] 그리퍼를 닫으라는 명령을 내리고 꽉 잡을 때까지 길게 기다림
        self.call(self.cli_g, SetBool.Request(data=True))
        time.sleep(self.GRIP_WAIT_TIME) 
        
        # 완전히 잡은 후 위로 들어올림
        self.call(self.cli_r, GetTargetPose.Request(z=-50.0, target_size="Z")) 
        time.sleep(self.WAIT_TIME) 
        return True

    def drop_target_to_home(self):
        self.call(self.cli_h, Trigger.Request())
        
        # 👇 [수정됨] 그리퍼를 열라는 명령을 내리고 다 열릴 때까지 길게 기다림
        self.call(self.cli_g, SetBool.Request(data=False))
        time.sleep(self.GRIP_WAIT_TIME)

    # ==========================================
    # 💥 조합별 분해 시퀀스 모음 (기존 2~3층)
    # ==========================================
    def disassemble_battery(self):
        self.get_logger().info("\n🔋 [배터리 분해] 2층 노랑 -> 1층 파랑")
        if self.pick_target("2x2_yellow", expected_layer=2):
            self.drop_target_to_home()
            self.get_logger().info("✅ 배터리 분해 완료!")

    def disassemble_magnet(self):
        self.get_logger().info("\n🧲 [자석 분해] 2층 파랑 -> 1층 빨강")
        if self.pick_target("2x2_blue", expected_layer=2):
            self.drop_target_to_home()
            self.get_logger().info("✅ 자석 분해 완료!")

    def disassemble_emergency_stop(self):
        self.get_logger().info("\n🛑 [비상정지 분해] 2층 빨강 -> 1층 노랑(4x2)")
        if self.pick_target("2x2_red", expected_layer=2):
            self.drop_target_to_home()
            self.get_logger().info("✅ 비상정지 분해 완료!")

    def disassemble_traffic_light(self):
        self.get_logger().info("\n🚦 [신호등 분해] 3층 빨강 -> 2층 노랑 -> 1층 파랑")
        if not self.pick_target("2x2_red", expected_layer=3):
            return
        self.drop_target_to_home()
        if not self.pick_target("2x2_yellow", expected_layer=2): return
        self.drop_target_to_home()
        if not self.pick_target("2x2_blue", expected_layer=1): return
        self.drop_target_to_home()
        self.get_logger().info("🎉 신호등 완벽 분해 성공!")

    def disassemble_carrot(self):
        self.get_logger().info("\n🥕 [당근 분해] 3층 노랑 -> 2층 파랑 -> 1층 노랑")
        if not self.pick_target("2x2_yellow", expected_layer=3):
            return
        self.drop_target_to_home()
        if not self.pick_target("2x2_blue", expected_layer=2): return
        self.drop_target_to_home()
        if not self.pick_target("2x2_yellow", expected_layer=1): return
        self.drop_target_to_home()
        self.get_logger().info("🎉 당근 완벽 분해 성공!")

    # ==========================================
    # 💥 4층 블록 추가 분해 시퀀스 (큰 당근, 버거, 아이스크림, 큰 나무)
    # ==========================================
    def disassemble_big_carrot(self):
        self.get_logger().info("\n🥕🥕 [큰 당근 분해] 4층 파랑(2x2) -> 3층 노랑(4x2) -> 2층 노랑(2x2) -> 1층 노랑(2x2)")
        if not self.pick_target("2x2_blue", expected_layer=4):
            if not self.pick_target("2x2_green", expected_layer=4):
                self.get_logger().error("❌ 큰 당근 상단(4층)을 찾을 수 없습니다.")
                return
        self.drop_target_to_home()

        if not self.pick_target("4x2_yellow", expected_layer=3): return
        self.drop_target_to_home()

        if not self.pick_target("2x2_yellow", expected_layer=2): return
        self.drop_target_to_home()

        if not self.pick_target("2x2_yellow", expected_layer=1): return
        self.drop_target_to_home()
        self.get_logger().info("🎉 대왕 당근 완벽 분해 성공!")

    # def disassemble_burger(self):
    #     self.get_logger().info("\n🍔 [버거 분해] 4층 노랑(4x2) -> 3층 빨강(2x2) -> 2층 빨강(4x2) -> 1층 노랑(4x2)")
    #     if not self.pick_target("4x2_yellow", expected_layer=4):
    #         self.get_logger().error("❌ 버거 상단 빵(4층 노랑 4x2)을 찾을 수 없습니다.")
    #         return
    #     self.drop_target_to_home()

    #     if not self.pick_target("2x2_red", expected_layer=3): return
    #     self.drop_target_to_home()

    #     if not self.pick_target("4x2_red", expected_layer=2): return
    #     self.drop_target_to_home()

    #     if not self.pick_target("4x2_yellow", expected_layer=1): return
    #     self.drop_target_to_home()
    #     self.get_logger().info("🎉 버거 완벽 분해 성공!")

    def disassemble_burger(self):
        self.get_logger().info("\n🍔 [버거 분해] 4층 노랑 -> 3층 빨강 -> 2층 빨강 -> 1층 노랑 (비전 오인식 방어 적용)")
        
        # 4층: 4x2_yellow (상단 빵)
        if not self.pick_target("4x2_yellow", expected_layer=4):
            self.get_logger().error("❌ 버거 상단 빵(4층 노랑 4x2)을 찾을 수 없습니다.")
            return
        self.drop_target_to_home()

        # 3층: 2x2_red 시도 후, 실패하면 4x2_red로 오인식했는지 확인
        if self.pick_target("2x2_red", expected_layer=3):
            self.drop_target_to_home()
        elif self.pick_target("4x2_red", expected_layer=3):
            self.get_logger().warn("⚠️ [오인식 방어] 3층 2x2 빨강이 4x2로 인식되어 수거합니다.")
            self.drop_target_to_home()
        else:
            return

        # 2층: 4x2_red 시도 후, 실패하면 2x2_red로 오인식했는지 확인
        if self.pick_target("4x2_red", expected_layer=2):
            self.drop_target_to_home()
        elif self.pick_target("2x2_red", expected_layer=2):
            self.get_logger().warn("⚠️ [오인식 방어] 2층 4x2 빨강이 2x2로 인식되어 수거합니다.")
            self.drop_target_to_home()
        else:
            return

        # 1층: 4x2_yellow (하단 빵)
        if not self.pick_target("4x2_yellow", expected_layer=1): 
            return
        self.drop_target_to_home()
        
        self.get_logger().info("🎉 버거 완벽 분해 성공!")

    # def disassemble_ice_cream(self):
    #     self.get_logger().info("\n🍦 [아이스크림 분해] 4층 노랑(2x2) -> 3층 파랑/빨강(2x2) -> 2층 노랑(4x2) -> 1층 노랑(2x2)")
    #     if not self.pick_target("2x2_yellow", expected_layer=4):
    #         if not self.pick_target("2x2_green", expected_layer=4):
    #             self.get_logger().error("❌ 아이스크림 상단(4층)을 찾을 수 없습니다.")
    #             return
    #     self.drop_target_to_home()

    #     self.get_logger().info("🍦 [아이스크림 3층 분해] 2x2 파랑, 2x2 빨강 수거")
    #     if self.pick_target("2x2_blue", expected_layer=3):
    #         self.drop_target_to_home()
    #     if self.pick_target("2x2_red", expected_layer=3):
    #         self.drop_target_to_home()

    #     if not self.pick_target("4x2_yellow", expected_layer=2): return
    #     self.drop_target_to_home()

    #     if not self.pick_target("2x2_yellow", expected_layer=1): return
    #     self.drop_target_to_home()
    #     self.get_logger().info("🎉 아이스크림 완벽 분해 성공!")

    def disassemble_ice_cream(self):
        self.get_logger().info("\n🍦 [아이스크림 분해] 4층 초록 -> 3층 파랑/빨강 -> 2층 노랑 -> 1층 노랑 (비전 오인식 4x2 방어 적용)")
        
        # 4층: 2x2_green 시도 후, 실패하면 4x2_green 시도
        if not self.pick_target("2x2_green", expected_layer=4):
            self.get_logger().warn("⚠️ [오인식 방어] 2x2 초록 실패. 4x2 초록으로 대체 탐색합니다.")
            if not self.pick_target("4x2_green", expected_layer=4):
                self.get_logger().error("❌ 아이스크림 상단(4층 초록)을 찾을 수 없습니다.")
                return
        self.drop_target_to_home()

        self.get_logger().info("🍦 [아이스크림 3층 분해] 파랑, 빨강 수거")
        
        # 3층 파란색: 2x2 먼저 찾고 없으면 4x2로 수거
        if self.pick_target("2x2_blue", expected_layer=3):
            self.drop_target_to_home()
        elif self.pick_target("4x2_blue", expected_layer=3):
            self.get_logger().warn("⚠️ [오인식 방어] 파란색이 4x2로 인식되어 수거합니다.")
            self.drop_target_to_home()

        # 3층 빨간색: 2x2 먼저 찾고 없으면 4x2로 수거
        if self.pick_target("2x2_red", expected_layer=3):
            self.drop_target_to_home()
        elif self.pick_target("4x2_red", expected_layer=3):
            self.get_logger().warn("⚠️ [오인식 방어] 빨간색이 4x2로 인식되어 수거합니다.")
            self.drop_target_to_home()

        # 2층
        if not self.pick_target("4x2_yellow", expected_layer=2): return
        self.drop_target_to_home()

        # 1층
        if not self.pick_target("2x2_yellow", expected_layer=1): return
        self.drop_target_to_home()
        
        self.get_logger().info("🎉 아이스크림 완벽 분해 성공!")


    # def disassemble_big_tree(self):
    #     self.get_logger().info("\n🌳 [큰 나무 분해] 4층 빨강(2x2) -> 3층 빨강(4x2) -> 2층 빨강(2x2, 4x2) -> 1층 노랑(2x2)")
    #     if not self.pick_target("2x2_red", expected_layer=4):
    #         self.get_logger().error("❌ 큰 나무 상단(4층 빨강 2x2)을 찾을 수 없습니다.")
    #         return
    #     self.drop_target_to_home()

    #     if not self.pick_target("4x2_red", expected_layer=3): return
    #     self.drop_target_to_home()

    #     self.get_logger().info("🌳 [큰 나무 2층 분해] 4x2 빨강, 2x2 빨강 수거")
    #     if self.pick_target("4x2_red", expected_layer=2):
    #         self.drop_target_to_home()
    #     if self.pick_target("2x2_red", expected_layer=2):
    #         self.drop_target_to_home()

    #     if not self.pick_target("2x2_yellow", expected_layer=1): return
    #     self.drop_target_to_home()
    #     self.get_logger().info("🎉 큰 나무 완벽 분해 성공!")


    def disassemble_big_tree(self):
        self.get_logger().info("\n🌳 [큰 나무 분해] 4층 초록 -> 3층 초록 -> 2층 초록(2개) -> 1층 노랑 (비전 오인식 방어 적용)")
        
        # 4층: 2x2_green 시도 후, 실패하면 4x2_green 시도
        if not self.pick_target("2x2_green", expected_layer=4):
            self.get_logger().warn("⚠️ [오인식 방어] 4층 2x2 초록 실패. 4x2 초록으로 대체 탐색합니다.")
            if not self.pick_target("4x2_green", expected_layer=4):
                self.get_logger().error("❌ 큰 나무 상단(4층 초록)을 찾을 수 없습니다.")
                return
        self.drop_target_to_home()

        # 3층: 4x2_green
        if not self.pick_target("4x2_green", expected_layer=3): return
        self.drop_target_to_home()

        self.get_logger().info("🌳 [큰 나무 2층 분해] 4x2 초록, 2x2 초록 순차 수거")
        
        # 2층 첫 번째 블록 (4x2_green)
        if self.pick_target("4x2_green", expected_layer=2):
            self.drop_target_to_home()
            
        # 2층 두 번째 블록 (2x2_green 시도 후, 실패하면 남은 찌꺼기를 4x2_green으로 인식했는지 확인)
        if self.pick_target("2x2_green", expected_layer=2):
            self.drop_target_to_home()
        elif self.pick_target("4x2_green", expected_layer=2):
            self.get_logger().warn("⚠️ [오인식 방어] 2층 2x2 초록이 4x2로 인식되어 수거합니다.")
            self.drop_target_to_home()

        # 1층: 2x2_yellow 기둥
        if not self.pick_target("2x2_yellow", expected_layer=1): return
        self.drop_target_to_home()
        
        self.get_logger().info("🎉 큰 나무 완벽 분해 성공!")


    # ==========================================
    # ⌨️ 대화형 메인 루프
    # ==========================================
    def run(self):
        self.get_logger().info("🚀 로봇 초기화 중...")
        self.call(self.cli_h, Trigger.Request())
        self.call(self.cli_g, SetBool.Request(data=False))
        time.sleep(1.0) 

        print("\n" + "="*60)
        print("🤖 듀플로 지능형 분해 시스템 가동 (4층 지원 & 타이밍 최적화) 🤖")
        print("사용 가능한 명령어: 당근, 신호등, 배터리, 자석, 비상정지")
        print("                 큰당근, 큰나무, 아이스크림, 버거, 종료")
        print("="*60)

        while rclpy.ok():
            try:
                user_input = input("\n⌨️ 분해할 조합을 입력하세요: ").strip().replace(" ", "")
                
                if user_input in ["종료", "exit", "quit"]:
                    self.get_logger().info("👋 프로그램을 종료합니다.")
                    break
                elif "당근" in user_input and "큰" not in user_input:
                    self.disassemble_carrot()
                elif "신호등" in user_input:
                    self.disassemble_traffic_light()
                elif "배터리" in user_input:
                    self.disassemble_battery()
                elif "자석" in user_input:
                    self.disassemble_magnet()
                elif "비상" in user_input: 
                    self.disassemble_emergency_stop()
                elif "큰당근" in user_input:
                    self.disassemble_big_carrot()
                elif "버거" in user_input or "햄버거" in user_input:
                    self.disassemble_burger()
                elif "아이스크림" in user_input:
                    self.disassemble_ice_cream()
                elif "큰나무" in user_input:
                    self.disassemble_big_tree()
                elif user_input == "":
                    continue
                else:
                    self.get_logger().warn(f"❓ '{user_input}'은(는) 알 수 없는 명령어입니다. 다시 입력해주세요.")
                
                # 시퀀스가 끝난 후 로봇을 홈으로 원복
                self.call(self.cli_h, Trigger.Request())
                
            except KeyboardInterrupt:
                self.get_logger().info("\n👋 강제 종료 감지. 프로그램을 종료합니다.")
                break

def main():
    rclpy.init()
    node = MasterNode()
    node.run()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()