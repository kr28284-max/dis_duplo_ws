# 🤖 ROS 2 지능형 듀플로 조립 로봇 (Intelligent Duplo Assembly Robot)

![ROS 2](https://img.shields.io/badge/ROS_2-Humble-22314E?style=flat&logo=ros&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=flat&logo=python&logoColor=white)
![YOLO](https://img.shields.io/badge/YOLO-Vision-00FFFF?style=flat&logo=yolo&logoColor=black)
![RealSense](https://img.shields.io/badge/Intel_RealSense-RGBD-0071C5?style=flat&logo=intel&logoColor=white)

## 📌 프로젝트 개요 (Overview)
본 작업 공간(Workspace)은 ROS 2 Humble 환경에서 인공지능 비전(YOLOv8)과 깊이(Depth) 카메라를 결합하여, 다양한 구조로 조립된 듀플로(Duplo) 블록 탑을 실시간으로 스캔하고 상단에서부터 안전하게 연쇄 분해(Top-Down Disassembly)하는 지능형 로봇 제어 시스템입니다.


## 🧱 분해 가능한 듀플로 
총 7가지의 다양한 듀플로 조합 패턴을 인식하고 분해할 수 있습니다. 
시스템은 현재 총 5가지의 특수 블록 조합 시퀀스를 지원하며, 지정된 층수 검증(`expected_layer`) 안전장치가 가동됩니다.

1. **당근 (Carrot)** 🥕
   * 구조: 3층 초록(2x2) -> 2층 노랑(4x2) -> 1층 노랑(4x2)
   * 특이사항: 2층과 1층의 동일 색상 중첩 구조를 층수 인지를 통해 순차 분해
2. **신호등 (Traffic Light)** 🚦
   * 구조: 3층 빨강(2x2) -> 2층 노랑(4x2) -> 1층 초록(2x2)
3. **배터리 (Battery)** 🔋
   * 구조: 2층 노랑(4x2) -> 1층 파랑(2x2)
4. **자석 (Magnet)** 🧲
   * 구조: 2층 파랑(2x2) -> 1층 빨강(2x2)
5. **비상정지 (Emergency Stop)** 🛑
   * 구조: 2층 빨강(2x2) -> 1층 노랑(4x2)

---
---

## 🚀 오늘의 주요 기술적 성과 (Key Achievements)

### 1. 앙상블 비전 시스템 (Ensemble Vision Model Integration)
* **좌표 안정성 및 각도 추출의 한계 극복**: 바운딩 박스(Bounding Box) 예측이 정밀하여 3차원 XYZ 좌표 안정성이 높은 신형 모델(`best.pt`)과, 인스턴스 세그멘테이션(Instance Segmentation) 마스크를 제공하여 정밀한 각도(`Yaw`) 추출이 가능한 구형 모델(`best_old.pt`)을 실시간으로 결합하는 **앙상블 매칭 알고리즘**을 구현했습니다.
* **픽셀 거리 기반 객체 매칭**: 새 모델의 중심점과 구형 모델의 마스크 중심점 간의 유클리드 거리를 계산(40픽셀 이내 최적 매칭)하여 두 모델의 장점만을 결합한 고정밀 6자유도(6DoF) 포즈를 추정합니다.

### 2. 실시간 층수 판별 알고리즘 (Intelligent Layer Detection)
* **절대적 기준점 추출 (`floor_z`)**: 필드 내에 존재하는 모든 오브젝트의 깊이(Depth) 데이터를 스캔하여 가장 깊은 지점(물리적 바닥면)을 실시간 기준점(`floor_z`)으로 동적 정의합니다.
* **상대적 층수 역산**: 타겟 블록의 실제 높이와 바닥 기준점 간의 차이를 듀플로 블록 스터드 표준 높이(16mm)로 나누어, 현재 타겟이 몇 층(**1층 ~ 4층**)에 위치하는지 실시간으로 판정합니다. 동일한 색상의 블록이 여러 층에 겹쳐 있어도 정확하게 개별 객체로 분리 인지할 수 있습니다.

### 3. 최고층 우선 탑다운 파지 (Top-Down Disassembly Control)
* **안전한 제어 시퀀스**: 분해 작업 시 하단 블록과의 충돌을 방지하기 위해, 동일 색상 후보군 중 카메라와 가장 가까운(Z축 값이 가장 작은) **최고층 블록을 무조건 최우선 파지 타겟으로 선정**하는 로직을 탑재했습니다.
* **높이 보정 수식 단순화**: 비전 노드가 실제 블록 윗면의 물리적 높이를 직접 계산하여 송신하므로, 마스터 노드는 복잡한 층수 보정 수식 없이 비전 좌표 기반으로 일정한 파지 깊이(`Z_OFF`)를 적용해 안정적으로 다운동작을 수행합니다.

### 4. 사용자 대화형 CLI 인터페이스 (Interactive Command-Line Interface)
* 마스터 제어 노드 내에 무한 루프 기반의 CLI 프롬프트를 구현하여 사용자가 터미널에 직접 구조물 명칭을 입력하여 제어할 수 있습니다.
* 명령이 인입되면 로봇이 즉시 구동하는 대신 비전을 통해 **필드 사전 스캔(Scan Validation)**을 수행하여 해당 구조물의 상단 타겟 블록이 실제 존재하는지 검증 후 시퀀스를 가동합니다.

---
---

## 👨‍💻 Author
* **이다한 (Lee Dahan)** **한덕희 (Han DeokHui)**
* Incheon National University, Dept. of Electrical Engineering
