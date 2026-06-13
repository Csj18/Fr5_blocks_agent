# 仿真数据流与 TF 树参考

## 一、TF 树结构

```
world                                ← Gazebo 世界原点
├── fairino5_v6_robot                ← Gazebo 中 FR5 模型位姿（物理仿真）
│   └── base_link                    ← block_tf_bridge 发布的恒等变换
│       ├── shoulder_link            ← robot_state_publisher（URDF 运动学链）
│       │   └── upperarm_link
│       │       └── forearm_link
│       │           └── wrist1_link
│       │               └── wrist2_link
│       │                   └── wrist3_link    ← 末端，无 tool0/夹爪
├── block_red                        ← Gazebo 物理仿真位姿
├── block_green                      ←
├── block_blue                       ←
└── work_table                       ← 静态（x=0.5, 0.8m×0.6m 桌面）
```

### 关键 TF 帧来源

| 帧 | 发布者 | 说明 |
|---|---|---|
| world → fairino5_v6_robot | block_tf_bridge.py | 从 Gazebo 读取并转发到 /tf |
| fairino5_v6_robot → base_link | block_tf_bridge.py | 恒等变换，链接机器人运动学链 |
| base_link → ... → wrist3_link | robot_state_publisher | 根据 /joint_states + URDF 计算 |
| world → block_* | block_tf_bridge.py | 从 Gazebo 读取并过滤转发 |

### RViz Fixed Frame

设置 `Fixed Frame = base_link` 时，积木坐标查找链：

```
base_link → fairino5_v6_robot → world → block_red
```

---

## 二、数据流全景

```
┌────────────────────────────────────────────────┐
│                Gazebo 物理引擎                   │
│  block_stacking_world.sdf  (world)              │
│  ├── Ground Plane                               │
│  ├── Sun (光照)                                  │
│  ├── work_table (静态桌面, x=0.5, 0.02m 厚)      │
│  ├── fairino5_v6_robot (FR5, gz_ros2_control)  │
│  ├── block_red   (3cm³, 0.05kg, μ=1.0)         │
│  ├── block_green (3cm³, 0.05kg, μ=1.0)         │
│  └── block_blue  (3cm³, 0.05kg, μ=1.0)         │
│                                                  │
│  物理参数: ODE 引擎, dt=0.001s, RTF=1.0         │
│  输出: /world/block_stacking_world/             │
│         dynamic_pose/info (Pose_V)              │
└────────────────────┬───────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│              ros_gz_bridge                       │
│  parameter_bridge:                              │
│  Pose_V → tf2_msgs/msg/TFMessage                │
│                                                  │
│  发布到: /world/block_stacking_world/           │
│           dynamic_pose/info                      │
└────────────────────┬───────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     ▼               ▼               ▼
┌──────────┐  ┌────────────┐  ┌───────────────────┐
│block_tf  │  │block_visual│  │block_collision     │
│_bridge   │  │_marker     │  │_updater            │
│          │  │            │  │                    │
│过滤block │  │为每个block │  │为每个block生成      │
│帧+构建   │  │生成彩色    │  │CollisionObject      │
│robot链   │  │CUBE Marker │  │(ADD模式,每帧更新)   │
│          │  │            │  │                    │
│→ /tf     │  │→ /block_   │  │→ /collision_object │
│          │  │  markers   │  │                    │
└────┬─────┘  └─────┬──────┘  └────────┬──────────┘
     │              │                  │
     ▼              ▼                  ▼
┌──────────┐  ┌──────────┐  ┌──────────────────┐
│  RViz    │  │  RViz    │  │  MoveIt           │
│ TF 坐标轴│  │ 彩色立方体│  │  规划时避开积木    │
│          │  │ MarkerArray│  │  (planning scene) │
└──────────┘  └──────────┘  └──────────────────┘
```

---

## 三、MoveIt ↔ Gazebo 控制流

```
用户拖拽 RViz 交互标记 → 点击 "Plan & Execute"
  │
  ▼
MoveIt 运动规划
  │  参考: planning_scene (含 block 碰撞体)
  │  求解: 逆运动学 + 避障路径
  ▼
/fairino5_controller/follow_joint_trajectory (action)
  │
  ▼
Gazebo 的 controller_manager (joint_trajectory_controller)
  │  joint_state_broadcaster 发布 /joint_states
  │  fairino5_controller 执行关节轨迹
  ▼
Gazebo 物理引擎 → FR5 关节转动 → 碰撞响应
  │
  ▼
新位姿 → Pose_V → ros_gz_bridge → ROS → RViz 更新
```

### 启动时序

| 时间 | 动作 |
|---|---|
| t=0.0s | robot_state_publisher（注册 robot_description 参数）|
| t=0.0s | ros_gz_bridge, block_tf_bridge, block_collision_updater, block_visual_marker |
| t=0.0s | move_group, RViz |
| t=2.0s | Gazebo 启动（延迟 2s 确保 robot_description 就绪）|
| t=4.0s | spawn FR5 机器人 |
| t=5.0s | spawn block_red (x=0.40, y=-0.10) |
| t=5.5s | spawn block_green (x=0.50, y=0.00) |
| t=6.0s | spawn block_blue (x=0.60, y=0.10) |
| t=7.0s | spawn joint_state_broadcaster → Gazebo controller_manager |
| t=9.0s | spawn fairino5_controller → Gazebo controller_manager |

---

## 四、积木 spawn 初始位姿

| 积木 | 坐标 (x, y, z) | 颜色 | SDF 文件 |
|---|---|---|---|
| block_red | (0.40, -0.10, 0.025) | 红色 | config/block_red.sdf |
| block_green | (0.50, 0.00, 0.025) | 绿色 | config/block_green.sdf |
| block_blue | (0.60, 0.10, 0.025) | 蓝色 | config/block_blue.sdf |

> z=0.025 = 桌面表面(0.01) + 积木半高(0.015)

---

## 五、夹爪 TF 链（2026-06-12 新增）

```
wrist3_link
  └── arm_hand_joint (fixed, z+0.12, yaw π)
      └── hand_base_link                      ← 夹爪基座
          ├── fj1 (prismatic, 0→4cm)          ← 手指1关节
          │   └── finger_link1
          └── fj2 (prismatic, 0→4cm)          ← 手指2关节
              └── finger_link2
```

| 关节 | 类型 | 行程 | 初始值 | 说明 |
|---|---|---|---|---|
| arm_hand_joint | fixed | — | — | wrist3_link → hand_base_link |
| fj1 | prismatic | 0 ~ 0.04m | 0.0 | 手指1 开合 |
| fj2 | prismatic | 0 ~ 0.04m | 0.04 | 手指2 开合（反向安装） |

---

## 六、Pick/Place 数据流（已实现 2026-06-12）

### Pick 流程

```
ros2 topic pub /pick_place "pick block_red"
  │
  ▼
pick_place_server.py
  │
  ▼
ign service /world/block_stacking_world/create
  │  EntityFactory: fixed joint
  │  parent: fairino5_v6_robot::hand_base_link
  │  child:  block_red::block_link
  ▼
Gazebo 物理引擎
  │  block_red 的碰撞体被 joint 锁定到 hand_base_link
  │  block_red 不再受独立重力/碰撞影响
  ▼
joint 创建成功 → block_red 跟随 hand_base_link 运动
  │
  ▼
用户在 RViz 中拖拽 MoveIt → Plan & Execute
  → fairino5_controller 执行关节轨迹
  → 机械臂移动 → hand_base_link 移动 → block_red 跟随
```

### Place 流程

```
ros2 topic pub /pick_place "place block_red"
  │
  ▼
pick_place_server.py
  │
  ▼
ign service /world/block_stacking_world/remove
  │  Entity: pick_block_red (type: JOINT)
  ▼
joint 删除 → block_red 恢复独立物理
  │  受重力下落
  ▼
积木落在桌面 / 被放置位置
```

### 关键实现

| 组件 | 文件 | 说明 |
|---|---|---|
| Pick/Place 服务器 | `scripts/pick_place_server.py` | 订阅 `/pick_place`，调用 ign service |
| 夹爪控制器 | — | **已禁用**（激活失败），手指固定张开 |
| Gazebo joint 创建 | `ign service /world/.../create` | EntityFactory + SDF joint |
| Gazebo joint 删除 | `ign service /world/.../remove` | Entity name + type: JOINT |

### 手动抓取测试

```bash
# 终端 1：启动仿真
source ~/ros2_ws/install/setup.bash
IGN_GAZEBO_RESOURCE_PATH=/home/csj/ros2_ws/install/fairino_description/share:/home/csj/ros2_ws/install/fr5_description/share \
  ros2 launch block_stacking_agent sim_agent.launch.py

# 终端 2：控制 Pick/Place
source ~/ros2_ws/install/setup.bash
ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once
# → 在 RViz 中 Plan & Execute 移动机械臂 → 积木跟随
ros2 topic pub /pick_place std_msgs/String "data: \"place block_red\"" --once
# → 积木落下
```

---

## 七、当前已知问题 (2026-06-12)

| 问题 | 状态 | 影响 |
|---|---|---|
| TF /tf 无数据发布 | ❌ 调查中 | RViz 帧 "base_link" 不存在 |
| VMware Marker 渲染 | ⚠️ 间歇性 | 积木/桌面 Marker 可能不可见 |
| gripper_controller 激活失败 | ❌ 已禁用 | 手指不能运动 |
| Gazebo CPU 100% | ⚠️ 待优化 | VM 性能压力 |
| 多 Gazebo 实例冲突 | ✅ 已记录清理步骤 | 启动前需杀进程 |
