# execution_layer — 执行层

封装 MoveIt 2 与硬件接口，将技能层生成的轨迹计划转化为实际的机械臂运动。

## 模块

- **FR5 指挥官** (`fr5_commander.py`)：MoveIt 2 封装，负责轨迹规划、执行与取消
- **夹爪控制** (`gripper_controller.py`)：夹爪开合控制与力反馈读取
- **硬件切换** (`hardware_switch.py`)：仿真/真机模式切换（mock_components ↔ fairino_hardware）

## 依赖

- MoveIt 2
- ros2_control
- fairino_hardware（官方驱动）
