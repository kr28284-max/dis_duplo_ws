# dis_duplo_ws


## 🛠️ 실행 방법 (Usage)

```bash
cd ~/dis_duplo_ws   (robot1, robot2구동) 
ros2 run control_pkg robot_node2
---

cd ~/dis_duplo_ws   (중요x 다시만들어야함 참고만) 
ros2 run control_pkg master_node_dis6
---


cd ~/dis_duplo_ws   (중요x  1,2 둘다 나오는비전인데 1만 사용예정) 
ros2 run vision_pkg vision_6Dpose_node3
---

cd ~/dis_duplo_ws   (로보티즈 그리퍼)
ros2 run hardware_pkg gripper_node
---

cd ~/dis_duplo_ws   (작은그리퍼 이름 모름) 노드 둘다 켜야 마스터 노드에서 열고닫고 움직였음 
ros2 run hardware_pkg robot2_gpio_gripper_node
---
