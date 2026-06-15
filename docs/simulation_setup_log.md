# Simulation Setup Log

## Target
Terminal 输入 `pick block_red` → RViz 中 block 附着到夹爪并跟随移动。

## Current State (2026-06-13)

### 已实现
| 组件 | 状态 |
|------|------|
| Gazebo fixed joint (`ign service`) | ✅ 手动测试 `data: true`，joint 创建成功 |
| MoveIt AttachedCollisionObject | ✅ pick_place_server 发布到 `/attached_collision_object` |
| Gazebo pose bridge → TF | ✅ `block_tf_bridge` 桥接 Gazebo 位姿到 `/tf` |
| Block markers | ✅ `block_visual_marker` 显示彩色方块 |
| Pick 命令处理 | ✅ `pick_place_server` 接收并处理 |
| Place 命令处理 | ✅ 移除 joint + 移除 attachment |

### 核心问题：block 在 RViz 中不跟随夹爪

**根因分析：**
1. **TF 树冲突** — `block_tf_bridge` 以 Gazebo 频率 (~10kHz) 发布 `world → block_X`。想让 block 跟随夹爪需要 `hand_base_link → block_X`，但任何替代 TF 都会被高频率的 Gazebo TF 覆盖。

2. **节点间通信不可靠** — 尝试用 `/block_attachment` topic (String) 让其他节点知道附着状态，但 topic 上根本没有数据流动（即使 publisher 存在，ros2 topic echo 也收不到消息）。换用 TF-based 检测 (`lookup_transform("hand_base_link", block_X)`)，但因为 `hand_base_link` 帧的时间戳问题（robot_state_publisher 以 timestamp=0 发布静态变换）导致查找失败。

3. **DDS 发现延迟** — 每次启动后第一条 `ros2 topic pub` 命令经常丢失，需要发两次。

### 已尝试的方案（均失败）

| 方案 | 问题 |
|------|------|
| `/block_attachment` topic 同步状态 | topic 无消息流动（原因不明） |
| TF-based 检测 (`lookup_transform`) | `hand_base_link` 时间戳为 0，lookup 失败 |
| `canTransform` 超时检测 | TF_OLD_DATA 风暴，阻塞回调 |
| pick_place_server 200Hz TF 广播 | timer 似乎不触发 |

### 当前方向

**最简方案：依赖 Gazebo physics joint**

当 `ign service` 创建 Gazebo fixed joint 后，Gazebo 物理引擎会把 block 移到夹爪位置。Gazebo pose bridge 发布新的世界坐标。`block_tf_bridge` 以 `world → block_X` 发布这个新位置。RViz 中 block 出现在夹爪位置。

**不需要改变 TF parent frame。** block 的 TF 仍然是 `world → block_X`，但坐标值已经是夹爪的世界坐标了。

用户需要在 RViz 中 MoveIt Plan & Execute 移动机械臂后，观察 block 是否跟随。如果 Gazebo joint 成功创建，block 会随夹爪一起移动。

### 当前代码状态

```
pick_place_server.py   — 新版（Gazebo joint + MoveIt attachment，无 TF 广播）
block_tf_bridge.py     — 原始版（Gazebo → /tf）
block_collision_updater.py — 原始版
block_visual_marker.py — 原始版
```

### 测试步骤
```bash
# 启动仿真
ros2 launch block_stacking_agent sim_agent.launch.py

# 发送 pick（第一条可能丢失，重试一次）
ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once

# 在 RViz MotionPlanning 面板 Plan & Execute 移动机械臂
# → 观察 block 是否跟随夹爪

# 查看状态
ros2 topic pub /pick_place std_msgs/String "data: \"list\"" --once
```
