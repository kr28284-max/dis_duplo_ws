import rclpy
from rclpy.node import Node
from srvs_pkg.srv import GetTargetPose
from vision_pkg import INUVisionCall as ivc

class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node2')
        self.srv = self.create_service(GetTargetPose, '/get_target_pose', self.get_pose_cb)
        self.get_logger().info('[VISION] 초기화 중... VisionManager 로드')
        
        self.vision = ivc.VisionManager()
        self.class_to_target_id = {
            "2x2_red": 1,
            "2x2_green": 2,
            "2x2_blue": 3,
            "2x2_yellow": 4,
            "4x2_red": 5,
            "4x2_green": 6,
            "4x2_blue": 7,
            "4x2_yellow": 8,
            "assembly": 999,
            "Magnet": 13,
            "Battery": 34,
            "estop": 81,
            "traffic light": 241,
            "carrot": 442,
            "small tree": 462,
            "hammer": 711,
            "big carrot": 4482,
            "burger": 8518,
            "bigtree": 46262,
            "icecream": 48132,
        }
        self.aliases = {
            "2x4_red": "4x2_red",
            "2x4_green": "4x2_green",
            "2x4_blue": "4x2_blue",
            "2x4_yellow": "4x2_yellow",
        }
        self.get_logger().info('[VISION] vision_node2 시작 완료 (INUVisionLib 기반)')

    def parse_target_id(self, target_str):
        target_str = target_str.strip()
        if target_str.startswith("base_nearest:"):
            target_str = target_str.split(":", 1)[1].strip()

        if target_str.isdigit():
            return int(target_str)

        target_name = self.aliases.get(target_str, target_str)
        target_id = self.class_to_target_id.get(target_name)
        if target_id is None:
            raise ValueError(f"등록되지 않은 타겟입니다: {target_str}")
        return target_id

    def get_pose_cb(self, request, response):
        # target_color는 숫자 ID("7") 또는 클래스명("4x2_blue")을 모두 허용.
        target_str = request.target_color.strip()
        self.get_logger().info(f'[VISION] 서비스 요청 수신 - target: {target_str}')

        try:
            target_id = self.parse_target_id(target_str)
            self.get_logger().info(f'[VISION] target 변환 완료: {target_str} -> ID {target_id}')

            # 2. 카메라 최신 프레임 캡처
            self.vision.capture_camera(visualize=False)

            # 3. ID 번호에 따라 탐색(Search) 함수 분기
            if 1 <= target_id <= 8:
                self.get_logger().info(f'[VISION] 일반 브릭(ID:{target_id}) 탐색 모드 실행')
                self.vision.run_search(visualize=True)
            elif target_id == 999:
                self.get_logger().info('[VISION] 조립체(ID:999) 탐색 모드 실행')
                self.vision.run_search_assembly(visualize=True)
            else:
                self.get_logger().info(f'[VISION] 기타 객체(ID:{target_id}) 탐색 모드 실행')
                self.vision.run_search(visualize=True)

            # 4. 탐색된 결과에서 특정 타겟의 Pose 추출
            pose = self.vision.get_pose_by_id(target_id=target_id, local_id=0)

            # 5. 결과 반환 (Service Response)
            if pose is not None:
                response.success = True
                # ROS 표준 단위(미터)에 맞게 mm -> m 변환
                response.x = float(pose["x_mm"] / 1000.0)
                response.y = float(pose["y_mm"] / 1000.0)
                response.z = float(pose["z_mm"] / 1000.0)
                response.yaw = float(pose["yaw_deg"])
                # srv에 추가된 class_name 반환
                response.class_name = str(pose.get("class_name", ""))
                
                self.get_logger().info(
                    f'[VISION] 타겟({target_id}) 발견! X:{response.x*1000:.1f} Y:{response.y*1000:.1f} Yaw:{response.yaw:.1f} Class:{response.class_name}'
                )
            else:
                self.get_logger().error(f'[VISION] 시야에서 타겟(ID:{target_id})을 찾을 수 없습니다.')
                response.success = False

        except Exception as e:
            self.get_logger().error(f'[VISION] 처리 중 심각한 오류 발생: {e}')
            response.success = False

        return response

def main(args=None):
    rclpy.init(args=args)
    node = VisionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
