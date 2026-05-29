import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
import serial
import time
import threading

class GripperNode(Node):
    def __init__(self):
        super().__init__('gripper_node')
        self.srv = self.create_service(SetBool, 'control_gripper', self.control_cb)
        
        try:
            # 확인하신 포트 정상 반영 완료
            self.ser = serial.Serial("/dev/ttyACM1", 115200, timeout=1)
            
            # 아두이노/그리퍼 컨트롤러 리셋 대기
            time.sleep(2.0)
            self.get_logger().info("✅ Gripper Serial Connected")

            # [핵심 수정 사항] \n 대신 \r\n(캐리지 리턴 + 라인 피드) 사용
            self.get_logger().info("➡️ Initializing Gripper: Sending 'open'...")
            self.send_command("open")
            
        except Exception as e:
            self.get_logger().error(f"❌ Serial Error: {e}")

        self.keyboard_thread = threading.Thread(target=self.keyboard_loop, daemon=True)
        self.keyboard_thread.start()

    def send_command(self, command):
        serial_command = "grip" if command == "close" else command
        self.ser.write(f"{serial_command}\r\n".encode())
        self.get_logger().info(f"📌 Sent: {serial_command} (input: {command})")

    def control_cb(self, request, response):
        """
        Service Callback
        request.data 가 True면 grip, False면 open 명령을 보냅니다.
        """
        try:
            if request.data:  # True -> Grip
                # [핵심 수정 사항] \r\n 적용
                self.send_command("grip")
                response.message = "Grip Command Sent"
            else:             # False -> Open
                # [핵심 수정 사항] \r\n 적용
                self.send_command("open")
                response.message = "Open Command Sent"
            
            response.success = True
        except Exception as e:
            self.get_logger().error(f"❌ Service Error: {e}")
            response.success = False
            response.message = str(e)
            
        return response

    def keyboard_loop(self):
        print("\n[Gripper Keyboard] Type: open / close / grip / quit")
        while rclpy.ok():
            try:
                command = input("gripper> ").strip().lower()
            except EOFError:
                return

            if command in ("open", "close", "grip"):
                try:
                    self.send_command(command)
                except Exception as e:
                    self.get_logger().error(f"❌ Keyboard Error: {e}")
            elif command in ("quit", "exit"):
                self.get_logger().info("Keyboard exit requested")
                rclpy.shutdown()
                return
            elif command:
                print("Use: open / close / grip / quit")

def main(args=None):
    rclpy.init(args=args)
    node = GripperNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Keyboard Interrupt (SIGINT)')
    finally:
        if hasattr(node, 'ser') and node.ser.is_open:
            node.ser.close()
            node.get_logger().info("✅ Serial Closed")
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
