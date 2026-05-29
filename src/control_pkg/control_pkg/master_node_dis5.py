import rclpy
from rclpy.node import Node
from srvs_pkg.srv import GetTargetPose
from std_srvs.srv import SetBool, Trigger
import time
import math
import sys


VISION_SERVICES = {
    "robot1": "/get_target_pose",
    "robot2": "/robot2/get_target_pose",
}

ROBOT_NAMES = ("robot1", "robot2")


def get_robot_name_from_argv(default_name="robot1"):
    for arg in sys.argv:
        if arg.startswith("robot_name:="):
            return arg.split(":=", 1)[1]
    return default_name

class MasterNode(Node):
    def __init__(self, robot_name):
        super().__init__('master_node_dis5')
        self.robot_name = self.declare_parameter("robot_name", robot_name).value
        if self.robot_name not in ROBOT_NAMES:
            valid_names = ", ".join(ROBOT_NAMES)
            raise ValueError(f"Unknown robot_name '{self.robot_name}'. Use one of: {valid_names}")

        self.gripper_service = self.declare_parameter("gripper_service", "/control_gripper").value

        self.cli_v_by_robot = {
            name: self.create_client(GetTargetPose, VISION_SERVICES[name])
            for name in ROBOT_NAMES
        }
        self.cli_r_by_robot = {
            name: self.create_client(GetTargetPose, f'/{name}/robot_move_step')
            for name in ROBOT_NAMES
        }
        self.cli_h_by_robot = {
            name: self.create_client(Trigger, f'/{name}/robot_home')
            for name in ROBOT_NAMES
        }
        self.cli_g = self.create_client(SetBool, self.gripper_service)
        
        self.Z_OFF = -85.0
        self.Z_MARGIN = 20.0
        
        # ⏱️ 기본 로봇 팔 이동 대기 시간
        self.WAIT_TIME = 1.5 
        
        # ⏱️ 꽉 잡기 위한 '그리퍼 전용' 넉넉한 대기 시간 (추가됨)
        # 만약 여전히 놓친다면 이 숫자를 3.0 등으로 늘려주세요.
        self.GRIP_WAIT_TIME = 2.5 

        self.set_active_robot(self.robot_name)
        self.get_logger().info(f"Master dis5 ready: active={self.robot_name}, gripper={self.gripper_service}")
        
    def call(self, cli, req):
        while not cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'Waiting for {cli.srv_name}...')
        future = cli.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def set_active_robot(self, robot_name):
        if robot_name not in ROBOT_NAMES:
            self.get_logger().warn(f"Unknown robot selection: {robot_name}")
            return False

        self.robot_name = robot_name
        self.vision_service = VISION_SERVICES[robot_name]
        self.robot_move_service = f'/{robot_name}/robot_move_step'
        self.robot_home_service = f'/{robot_name}/robot_home'
        self.cli_v = self.cli_v_by_robot[robot_name]
        self.cli_r = self.cli_r_by_robot[robot_name]
        self.cli_h = self.cli_h_by_robot[robot_name]

        self.get_logger().info(
            f"Active robot: {robot_name} "
            f"(vision={self.vision_service}, move={self.robot_move_service}, home={self.robot_home_service})"
        )
        return True

    def home_all_robots(self):
        self.get_logger().info("🚀 robot1, robot2 홈 자세 이동 시작")
        for robot_name in ROBOT_NAMES:
            self.get_logger().info(f"🏠 {robot_name} home 호출")
            self.call(self.cli_h_by_robot[robot_name], Trigger.Request())
        self.get_logger().info("✅ robot1, robot2 홈 자세 이동 완료")

    def ask_robot_selection(self):
        while rclpy.ok():
            selected = input("\n🤖 사용할 로봇 선택 (1/2, robot1/robot2): ").strip().lower()
            selected = {"1": "robot1", "2": "robot2"}.get(selected, selected)
            if self.set_active_robot(selected):
                return
            print("robot1 또는 robot2 중 하나를 선택하세요.")

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
        self.home_all_robots()
        self.call(self.cli_g, SetBool.Request(data=False))
        time.sleep(1.0) 
        self.ask_robot_selection()

        print("\n" + "="*60)
        print(f"🤖 듀플로 지능형 분해 시스템 가동 ({self.robot_name}, 4층 지원 & 타이밍 최적화) 🤖")
        print("사용 가능한 명령어: 당근, 신호등, 배터리, 자석, 비상정지")
        print("                 큰당근, 큰나무, 아이스크림, 버거, 종료")
        print("로봇 변경: robot1, robot2 또는 1, 2")
        print("="*60)

        while rclpy.ok():
            try:
                user_input = input("\n⌨️ 분해할 조합을 입력하세요: ").strip().replace(" ", "")
                
                if user_input in ["종료", "exit", "quit"]:
                    self.get_logger().info("👋 프로그램을 종료합니다.")
                    break
                elif user_input.lower() in ["robot1", "로봇1", "1"]:
                    self.set_active_robot("robot1")
                    continue
                elif user_input.lower() in ["robot2", "로봇2", "2"]:
                    self.set_active_robot("robot2")
                    continue
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
    robot_name = get_robot_name_from_argv()
    rclpy.init()
    node = MasterNode(robot_name)
    node.run()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
