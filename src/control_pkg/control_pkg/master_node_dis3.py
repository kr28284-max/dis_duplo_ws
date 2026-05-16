# import rclpy
# from rclpy.node import Node
# from srvs_pkg.srv import GetTargetPose
# from std_srvs.srv import SetBool, Trigger
# import time
# import math

# class MasterNode(Node):
#     def __init__(self):
#         super().__init__('master_node')
#         # 서비스 클라이언트 생성
#         self.cli_v = self.create_client(GetTargetPose, '/get_target_pose')
#         self.cli_r = self.create_client(GetTargetPose, '/robot_move_step')
#         self.cli_g = self.create_client(SetBool, '/control_gripper')
#         self.cli_h = self.create_client(Trigger, '/robot_home')
        
#         # 🌟 로봇 제어 핵심 파라미터
#         self.Z_OFF = -85.0     # 블록을 꽉 쥐기 위해 윗면(Z)에서 아래로 내려가는 오프셋
#         self.Z_MARGIN = 20.0   # 안전 접근 여유 높이
#         self.WAIT_TIME = 1.5   # 로봇 구동 대기 시간
        
#     def call(self, cli, req):
#         """서비스 호출용 동기화 래퍼 함수"""
#         while not cli.wait_for_service(timeout_sec=1.0):
#             self.get_logger().info(f'Waiting for {cli.srv_name}...')
#         future = cli.call_async(req)
#         rclpy.spin_until_future_complete(self, future)
#         return future.result()

#     def find_target_with_retry(self, color, retries=4):
#         """비전 노드에 타겟 좌표를 요청하고 실패 시 재시도"""
#         for i in range(retries):
#             p = self.call(self.cli_v, GetTargetPose.Request(target_color=color))
#             if p.success:
#                 return p
#             self.get_logger().warn(f"⚠️ [{color}] 타겟 찾는 중... ({i+1}/{retries})")
#             time.sleep(1.0) 
#         return None

#     def pick_target(self, color, expected_layer=None):
#         """지정된 색상과 층수의 블록을 파지하는 함수"""
#         layer_text = f" (예상: {expected_layer}층)" if expected_layer else ""
#         self.get_logger().info(f"\n--- PICK TARGET: [{color.upper()}]{layer_text} ---")
        
#         p = self.find_target_with_retry(color)
#         if not p: return False

#         # 🌟 층수(Layer) 검증 로직
#         if expected_layer is not None:
#             if p.layer != expected_layer:
#                 self.get_logger().warn(f"⚠️ 층수 불일치! 예상: {expected_layer}층 / 비전 인식: {p.layer}층")
#                 self.get_logger().warn("하지만 일단 파지를 시도합니다. (문제가 생기면 여기서 막으세요)")

#         # 1. YAW 회전
#         req = GetTargetPose.Request(); req.yaw = p.yaw; req.target_size = "YAW"
#         self.call(self.cli_r, req)
#         time.sleep(self.WAIT_TIME) 

#         # 2. XY 이동
#         p = self.find_target_with_retry(color)
#         if not p: return False
#         req = GetTargetPose.Request(); req.x = p.x; req.y = p.y; req.target_size = "XY"
#         self.call(self.cli_r, req)
#         time.sleep(self.WAIT_TIME) 

#         # 3. Z축 이동 (비전이 준 실제 높이에서 오프셋만 푹 찍어서 파지)
#         p = self.find_target_with_retry(color)
#         if not p: return False
        
#         z_move = (p.z * 1000.0) + self.Z_OFF
        
#         self.call(self.cli_r, GetTargetPose.Request(z=z_move - self.Z_MARGIN, target_size="Z"))
#         time.sleep(self.WAIT_TIME) 
#         self.call(self.cli_r, GetTargetPose.Request(z=self.Z_MARGIN, target_size="Z"))
#         time.sleep(self.WAIT_TIME) 

#         # 4. 그리퍼 닫기 & 상승
#         self.call(self.cli_g, SetBool.Request(data=True))
#         time.sleep(self.WAIT_TIME) 
#         self.call(self.cli_r, GetTargetPose.Request(z=-50.0, target_size="Z")) # 안전 높이로 상승
#         time.sleep(self.WAIT_TIME) 
#         return True

#     def drop_target_to_home(self):
#         """집어든 블록을 홈 위치로 가져가서 떨어뜨리는 함수"""
#         self.call(self.cli_h, Trigger.Request())
#         self.call(self.cli_g, SetBool.Request(data=False))
#         time.sleep(1.0)


#     # ==========================================
#     # 💥 3단 조합 분해 시퀀스 (당근, 신호등)
#     # ==========================================

#     def disassemble_traffic_light(self):
#         """신호등 분해: 3층 빨강(1) -> 2층 노랑(4) -> 1층 초록(2)"""
#         self.get_logger().info("\n🚦 [신호등 분해 시작] 3층 빨강 -> 2층 노랑 -> 1층 초록")
        
#         if self.pick_target("2x2_red", expected_layer=3):
#             self.get_logger().info("✅ 1단계: 3층 빨간색 분리 완료")
#             self.drop_target_to_home()
#         else:
#             self.get_logger().error("❌ 3층 빨간색 분리 실패. 시퀀스 중단.")
#             return

#         if self.pick_target("4x2_yellow", expected_layer=2):
#             self.get_logger().info("✅ 2단계: 2층 노란색 분리 완료")
#             self.drop_target_to_home()
#         else:
#             self.get_logger().error("❌ 2층 노란색 분리 실패. 시퀀스 중단.")
#             return

#         if self.pick_target("2x2_green", expected_layer=1):
#             self.get_logger().info("✅ 3단계: 1층 초록색 분리 완료")
#             self.drop_target_to_home()
#             self.get_logger().info("🎉 신호등 조합 완벽 분해 성공!")
#         else:
#             self.get_logger().error("❌ 1층 초록색 분리 실패.")


#     def disassemble_carrot(self):
#         """당근 분해: 3층 초록(2) -> 2층 노랑(4) -> 1층 노랑(4)"""
#         self.get_logger().info("\n🥕 [당근 분해 시작] 3층 초록 -> 2층 노랑 -> 1층 노랑")
        
#         if self.pick_target("2x2_green", expected_layer=3):
#             self.get_logger().info("✅ 1단계: 3층 초록색(당근 잎) 분리 완료")
#             self.drop_target_to_home()
#         else:
#             self.get_logger().error("❌ 3층 초록색 분리 실패. 시퀀스 중단.")
#             return

#         # 🌟 여기서 비전 노드가 똑똑하게 2층 노란색을 골라줍니다!
#         if self.pick_target("4x2_yellow", expected_layer=2):
#             self.get_logger().info("✅ 2단계: 2층 노란색(당근 몸통 상단) 분리 완료")
#             self.drop_target_to_home()
#         else:
#             self.get_logger().error("❌ 2층 노란색 분리 실패. 시퀀스 중단.")
#             return

#         # 🌟 이제 남은 바닥의 1층 노란색을 집습니다.
#         if self.pick_target("4x2_yellow", expected_layer=1):
#             self.get_logger().info("✅ 3단계: 1층 노란색(당근 몸통 하단) 분리 완료")
#             self.drop_target_to_home()
#             self.get_logger().info("🎉 당근 조합 완벽 분해 성공!")
#         else:
#             self.get_logger().error("❌ 1층 노란색 분리 실패.")

#     # ==========================================
#     # 메인 실행 루프
#     # ==========================================
#     def run(self):
#         self.get_logger().info("🚀 STARTING 3-LAYER DISASSEMBLY SEQUENCE")
        
#         self.call(self.cli_h, Trigger.Request())
#         self.call(self.cli_g, SetBool.Request(data=False))
#         time.sleep(1.0) 

#         # 원하는 조합의 주석을 해제해서 실행하세요!
        
#         # 1. 신호등 분해
#         self.disassemble_traffic_light()

#         # 2. 당근 분해
#         self.disassemble_carrot()

#         self.call(self.cli_h, Trigger.Request())
#         self.get_logger().info("🎉 ALL SEQUENCE DONE")

# def main():
#     rclpy.init()
#     node = MasterNode()
#     try:
#         node.run()
#     except KeyboardInterrupt:
#         pass
#     finally:
#         node.destroy_node()
#         rclpy.shutdown()

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
        self.WAIT_TIME = 1.5 
        
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

        self.call(self.cli_g, SetBool.Request(data=True))
        time.sleep(self.WAIT_TIME) 
        self.call(self.cli_r, GetTargetPose.Request(z=-50.0, target_size="Z")) 
        time.sleep(self.WAIT_TIME) 
        return True

    def drop_target_to_home(self):
        self.call(self.cli_h, Trigger.Request())
        self.call(self.cli_g, SetBool.Request(data=False))
        time.sleep(1.0)

    # ==========================================
    # 💥 조합별 분해 시퀀스 모음
    # ==========================================
    def disassemble_battery(self):
        self.get_logger().info("\n🔋 [배터리 분해] 2층 노랑 -> 1층 파랑")
        if self.pick_target("2x2_yellow", expected_layer=2):
            self.drop_target_to_home()
            self.get_logger().info("✅ 배터리 분해 완료!")
        else:
            self.get_logger().error("❌ 필드에 배터리 조합(2층 노랑)이 없습니다.")

    def disassemble_magnet(self):
        self.get_logger().info("\n🧲 [자석 분해] 2층 파랑 -> 1층 빨강")
        if self.pick_target("2x2_blue", expected_layer=2):
            self.drop_target_to_home()
            self.get_logger().info("✅ 자석 분해 완료!")
        else:
            self.get_logger().error("❌ 필드에 자석 조합(2층 파랑)이 없습니다.")

    def disassemble_emergency_stop(self):
        self.get_logger().info("\n🛑 [비상정지 분해] 2층 빨강 -> 1층 노랑")
        if self.pick_target("2x2_red", expected_layer=2):
            self.drop_target_to_home()
            self.get_logger().info("✅ 비상정지 분해 완료!")
        else:
            self.get_logger().error("❌ 필드에 비상정지 조합(2층 빨강)이 없습니다.")

    def disassemble_traffic_light(self):
        self.get_logger().info("\n🚦 [신호등 분해] 3층 빨강 -> 2층 노랑 -> 1층 초록")
        if not self.pick_target("2x2_red", expected_layer=3):
            self.get_logger().error("❌ 신호등 상단(3층 빨강)을 찾을 수 없습니다. 스캔 실패!")
            return
        self.drop_target_to_home()

        if not self.pick_target("2x2_yellow", expected_layer=2): return
        self.drop_target_to_home()

        if not self.pick_target("2x2_green", expected_layer=1): return
        self.drop_target_to_home()
        self.get_logger().info("🎉 신호등 완벽 분해 성공!")

    def disassemble_carrot(self):
        self.get_logger().info("\n🥕 [당근 분해] 3층 초록 -> 2층 노랑 -> 1층 노랑")
        if not self.pick_target("2x2_green", expected_layer=3):
            self.get_logger().error("❌ 당근 상단(3층 초록)을 찾을 수 없습니다. 스캔 실패!")
            return
        self.drop_target_to_home()

        if not self.pick_target("2x2_yellow", expected_layer=2): return
        self.drop_target_to_home()

        if not self.pick_target("2x2_yellow", expected_layer=1): return
        self.drop_target_to_home()
        self.get_logger().info("🎉 당근 완벽 분해 성공!")


    # ==========================================
    # ⌨️ 대화형 메인 루프
    # ==========================================
    def run(self):
        self.get_logger().info("🚀 로봇 초기화 중...")
        self.call(self.cli_h, Trigger.Request())
        self.call(self.cli_g, SetBool.Request(data=False))
        time.sleep(1.0) 

        print("\n" + "="*50)
        print("🤖 듀플로 지능형 분해 시스템 가동 🤖")
        print("사용 가능한 명령어: 당근, 신호등, 배터리, 자석, 비상정지, 종료")
        print("="*50)

        # 🌟 사용자의 입력을 계속 기다리는 무한 루프
        while rclpy.ok():
            try:
                user_input = input("\n⌨️ 분해할 조합을 입력하세요: ").strip().replace(" ", "")
                
                if user_input in ["종료", "exit", "quit"]:
                    self.get_logger().info("👋 프로그램을 종료합니다.")
                    break
                elif "당근" in user_input:
                    self.disassemble_carrot()
                elif "신호등" in user_input:
                    self.disassemble_traffic_light()
                elif "배터리" in user_input:
                    self.disassemble_battery()
                elif "자석" in user_input:
                    self.disassemble_magnet()
                elif "비상" in user_input: # '비상'이나 '비상정지' 모두 인식
                    self.disassemble_emergency_stop()
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