import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

class GoHomeNode(Node):
    def init(self):
        super().init('go_home_node')
        # 마스터 노드와 동일한 홈 이동 서비스 클라이언트 생성
        self.cli_h = self.create_client(Trigger, '/robot_home')

    def call_home(self):
        # 서비스가 켜져 있는지 확인
        while not self.cli_h.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('⏳ /robot_home 서비스 대기 중...')

        self.get_logger().info('🚀 로봇을 홈 위치로 이동시킵니다...')
        req = Trigger.Request()
        future = self.cli_h.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

def main():
    rclpy.init()
    node = GoHomeNode()


    response = node.call_home()

    if response and response.success:
        node.get_logger().info('✅ 홈 위치 이동 명령이 성공적으로 전달되었습니다!')
    else:
        node.get_logger().warn('❌ 홈 위치 이동 실패 또는 응답 없음')

    node.destroy_node()
    rclpy.shutdown()

if name == 'main':
    main()