# 仿真数据流与 TF 树参考

> 最后更新：2026-06-18
> 上级索引：[VIBECODING_LOG.md](./VIBECODING_LOG.md) — 结论性日志
> 关联文档：[simulation_setup_log.md](./simulation_setup_log.md) — 环境搭建与问题记录

---

## 一、TF 树结构

### 1.1 完整 TF 层级

```
world                                ← Gazebo 世界原点
├── fairino5_v6_robot                ← Gazebo 中 FR5 模型位姿（物理仿真）
│   └── base_link                    ← block_tf_bridge 发布的恒等变换
│       ├── shoulder_link            ← robot_state_publisher（URDF 运动学链）
│       │   └── upperarm_link
│       │       └── forearm_link
│       │           └── wrist1_link
│       │               └── wrist2_link
│       │                   └── wrist3_link
│       │                       └── arm_hand_joint (fixed, z+0.12, yaw π)
│       │                           └── hand_base_link      ← 夹爪基座
│       │                               ├── fj1 (prismatic) → finger_link1
│       │                               └── fj2 (prismatic) → finger_link2
├── block_red                        ← Gazebo 物理仿真位姿
├── block_green
├── block_blue
└── work_table                       ← 静态（x=0.5, 0.8m×0.6m 桌面）
```

### 1.2 关键 TF 帧来源

| 帧 | 发布者 | 说明 |
|------|------|------|
| world → fairino5_v6_robot | block_tf_bridge.py | 从 Gazebo Pose_V 读取并转发到 /tf |
| fairino5_v6_robot → base_link | block_tf_bridge.py | 恒等变换，链接机器人运动学链 |
| base_link → ... → wrist3_link | robot_state_publisher | 根据 /joint_states + URDF 计算 |
| wrist3_link → hand_base_link | robot_state_publisher | arm_hand_joint（fixed） |
| hand_base_link → finger_link* | robot_state_publisher | fj1/fj2（prismatic） |
| world → block_* | block_tf_bridge.py | 从 Gazebo 读取，按 `block_` 前缀过滤 |

### 1.3 RViz Fixed Frame

设置 `Fixed Frame = base_link` 时，积木坐标查找链：

```
base_link → fairino5_v6_robot → world → block_red
```

### 1.4 Pick 前后的 TF 变化

**Pick 前（积木独立在世界中）：**
```
world
├── fairino5_v6_robot → ... → hand_base_link
├── block_red      (来自 Gazebo Pose_V 或 pick_place_server)
├── block_green
└── block_blue
```

**Pick 后（block_red 吸附到夹爪）：**
```
world
├── fairino5_v6_robot → ... → hand_base_link
│                               └── block_red   ← pick_place_server 广播 hand_base_link→block TF
├── block_green    (仍独立)
└── block_blue     (仍独立)
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
│  /clock → rosgraph_msgs/Clock                   │
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

### 架构要点

- Gazebo 的 `GazeboSimROS2ControlPlugin` 内部提供 `/controller_manager` 服务
- spawner 将 `fairino5_controller`（joint_trajectory_controller）加载到 Gazebo 的 controller_manager
- MoveIt 的 `moveit_simple_controller_manager` 连接同一 action 命名空间
- MoveIt 规划的轨迹由 Gazebo 控制器执行 → 机器人在 Gazebo 中物理移动

---

## 四、Pick/Place 数据流

### 4.1 架构全景

```
                         ┌────────────────────────┐
                         │     Terminal/CLI        │
                         │  ros2 topic pub         │
                         │  /pick_place            │
                         └───────────┬────────────┘
                                     │ std_msgs/String
                                     │ "pick block_red"
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│                     pick_place_server.py                           │
│                      (orchestrator)                                │
│                                                                    │
│  State:  attached{}  block_positions{}                             │
│                                                                    │
│  On PICK:                    On PLACE:                             │
│  ────────                    ─────────                             │
│  ① AttachedCollisionObject   ① AttachedCollisionObject REMOVE      │
│     → /attached_collision_object  → /attached_collision_object     │
│  ② CollisionObject REMOVE    ② TF lookup world→hand_base_link     │
│     → /collision_object      ③ CollisionObject ADD                │
│  ③ Gazebo fixed joint            → /collision_object              │
│     → ign service            ④ Gazebo joint remove                │
│  ④ State → /block_attachment     → ign service                    │
│  ⑤ TF → hand_base_link→block ⑤ State → /block_attachment          │
│                                                                    │
│  Every 100ms (timer):                                              │
│  - Re-publish attached objects (MoveIt needs refresh)              │
│  - Broadcast block TFs (attached: hand_base_link→block,            │
│                          detached: world→block)                    │
└────┬──────────┬──────────────────┬────────────────────────────────┘
     │          │                  │
     ▼          ▼                  ▼
┌─────────┐ ┌──────────┐ ┌──────────────────┐
│ MoveIt  │ │  Gazebo  │ │ /block_attachment │
│Planning │ │  Physics │ │  (std_msgs/String)│
│ Scene   │ │  (ign)   │ └──────┬───────────┘
└────┬────┘ └────┬─────┘        │
     │           │               ├──────────────┬──────────────┐
     ▼           ▼               ▼              ▼              ▼
┌─────────┐ ┌─────────┐ ┌─────────────┐ ┌──────────┐ ┌────────────────┐
│  RViz   │ │ Gazebo  │ │block_visual │ │block_tf  │ │block_collision │
│Planning │ │  pose   │ │_marker.py   │ │_bridge.py│ │_updater.py     │
│Scene    │ │ bridge  │ │             │ │          │ │                │
│display  │ │         │ │ on attach:  │ │ skip     │ │ skip attached  │
│         │ │         │ │ frame=hand  │ │ attached │ │ blocks         │
│         │ │         │ │ _base_link  │ │ blocks   │ │                │
└─────────┘ └─────────┘ └─────────────┘ └──────────┘ └────────────────┘
```

### 4.2 Pick 流程

```
ros2 topic pub /pick_place "pick block_red"
  │
  ▼
pick_place_server.py
  │ ① AttachedCollisionObject → /attached_collision_object (MoveIt 知道 block 已吸附)
  │ ② CollisionObject REMOVE → /collision_object (从 planning scene 移除独立碰撞体)
  │ ③ ign service → Gazebo fixed joint (parent: hand_base_link, child: block_red::block_link)
  │ ④ set_parameters(attached_blocks=['block_red']) → block_visual_marker 通过 GetParameters 感知
  │ ⑤ TF broadcast: hand_base_link → block_red
  ▼
block_visual_marker (每 0.5s 轮询参数 + 每 0.1s 发布):
  → marker.frame_id = "hand_base_link" → block 在 RViz 中跟随夹爪
```

### 4.3 Place 流程

```
ros2 topic pub /pick_place "place block_red"
  │
  ▼
pick_place_server.py
  │ ① AttachedCollisionObject REMOVE → /attached_collision_object
  │ ② TF lookup world→hand_base_link → 计算 block 在 world 中的放置位姿
  │ ③ CollisionObject ADD → /collision_object (恢复独立碰撞体)
  │ ④ ign service → 删除 Gazebo fixed joint (type: JOINT)
  │ ⑤ set_parameters(attached_blocks=[]) → block_visual_marker 感知脱落
  ▼
block 恢复独立物理 → 受重力下落 → Gazebo 位姿 → ros_gz_bridge → /tf + Marker 更新
```

---

## 五、节点职责分工

| 节点 | 已吸附 Block | 未吸附 Block |
|------|-------------|-------------|
| `pick_place_server.py` | 发布 AttachedCollisionObject；广播 `hand_base_link→block` TF | 发布独立 CollisionObject；广播 `world→block` TF |
| `block_visual_marker.py` | Marker frame_id = `hand_base_link`，位于 (0,0,-0.08) | Marker frame_id = `world`，来自 Gazebo 位姿 |
| `block_tf_bridge.py` | **跳过** — 不发布 `world→block` TF | 从 Gazebo Pose_V 发布 `world→block` TF |
| `block_collision_updater.py` | **跳过** — MoveIt 通过 attachment 处理 | 从 Gazebo Pose_V 发布 CollisionObject |

### 职责分离原则

- `block_tf_bridge` 和 `block_collision_updater` 只处理**未吸附**的积木（数据源：Gazebo Pose_V）
- 已吸附积木由 `pick_place_server` 全权管理（TF + CollisionObject + Attachment）
- `block_visual_marker` 通过 ROS Parameter 服务跨节点感知吸附状态，切换 frame_id

---

## 六、启动时序

| 时间 | 动作 | 节点 |
|------|------|------|
| t=0.0s | 注册 robot_description 参数 | robot_state_publisher |
| t=0.0s | 启动桥接与可视化节点 | ros_gz_bridge, block_tf_bridge, block_collision_updater, block_visual_marker |
| t=0.0s | 启动规划与可视化 | move_group, RViz |
| t=2.0s | 启动 Gazebo 物理引擎 | Gazebo server（headless） |
| t=4.0s | 生成 FR5 机器人 | ros_gz_sim create（从 /robot_description） |
| t=5.0s | 生成 block_red | x=0.40, y=-0.10, z=0.025 |
| t=5.5s | 生成 block_green | x=0.50, y=0.00, z=0.025 |
| t=6.0s | 生成 block_blue | x=0.60, y=0.10, z=0.025 |
| t=7.0s | 加载 joint_state_broadcaster | spawner → Gazebo controller_manager |
| t=9.0s | 加载 fairino5_controller | spawner → Gazebo controller_manager |

---

## 七、积木初始位姿

| 积木 | 坐标 (x, y, z) | 颜色 | SDF 文件 | 质量 |
|------|---------------|------|----------|------|
| block_red | (0.40, -0.10, 0.025) | 红色 | config/block_red.sdf | 0.05 kg |
| block_green | (0.50, 0.00, 0.025) | 绿色 | config/block_green.sdf | 0.05 kg |
| block_blue | (0.60, 0.10, 0.025) | 蓝色 | config/block_blue.sdf | 0.05 kg |

> z=0.025 = 桌面表面(0.01) + 积木半高(0.015)。所有积木为 3cm 立方体，摩擦系数 μ=1.0。

---

## 八、夹爪 TF 链

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
|------|------|------|--------|------|
| arm_hand_joint | fixed | — | — | wrist3_link → hand_base_link |
| fj1 | prismatic | 0 ~ 0.04m | 0.0 | 手指1 开合 |
| fj2 | prismatic | 0 ~ 0.04m | 0.04 | 手指2 开合（反向安装） |

> 注意：gripper_controller 当前未激活，手指固定于初始位置。Pick/Place 通过 Gazebo detachable joint 实现，不依赖手指运动。

---

## 九、积木命名约定与适配

- 所有积木模型名必须以 `block_` 为前缀
- 两个 Python 脚本均按 `block_*` 前缀过滤，排除 `*_link` 帧
- 如需不同前缀，修改以下位置：

| 文件 | 位置 |
|------|------|
| `scripts/block_tf_bridge.py` | `name.startswith("block_")` |
| `scripts/block_collision_updater.py` | `name.startswith("block_")` |
| `scripts/block_visual_marker.py` | `name.startswith("block_")` 和 `self.colors` 字典 |
