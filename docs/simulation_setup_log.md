# Simulation Setup Log

## 目标
终端输入 `pick block_red` → RViz 中 block 附着到夹爪并跟随移动。

---

## 当前状态 (2026-06-15) — ✅ 已解决

### 已实现
| 组件 | 状态 |
|------|------|
| Gazebo fixed joint (`ign service`) | ✅ 创建成功 |
| MoveIt AttachedCollisionObject | ✅ 发布到 `/attached_collision_object` |
| Gazebo pose bridge → TF | ✅ block_tf_bridge 桥接 |
| Block markers | ✅ block_visual_marker 显示方块 |
| Pick/Place 命令处理 | ✅ 接收并处理 |
| **block 在 RViz 中跟随夹爪** | ✅ **通过 ROS param 跨节点同步** |

### 解决方案：ROS Parameter + 服务调用跨节点同步

**三个关键修复（2026-06-15）：**

1. **`block_visual_marker` 跨节点参数读取** — 原来节点读取自己的 `attached_blocks`（始终为空），改为通过 `GetParameters` 服务客户端定时从 `pick_place_server` 读取参数，绕过 DDS SHM transport 问题。

2. **参数类型修复** — `declare_parameter("attached_blocks", [])` 传入空列表导致 ROS 2 Humble 将类型推断为 `byte_array`，改为 `declare_parameter("attached_blocks", [""])` 使类型正确推断为 `string_array`。

3. **Clock bridge 修复** — 原 launch 文件缺少 Gazebo → ROS `/clock` 桥接，导致所有 `use_sim_time:=True` 节点的 timer 冻结（包括 `block_visual_marker` 的 10Hz marker 发布和 2Hz 参数轮询）。添加了 `parameter_bridge` 桥接 `/world/block_stacking_world/clock`。

### 工作原理
```
pick block_red
  → pick_place_server: self.attached.add("block_red") → set_parameters(attached_blocks=['block_red'])
  → block_visual_marker (每0.5s): GetParameters 服务调用 → 获取 ['block_red']
  → publish_markers (每0.1s): marker.frame_id = "hand_base_link" (而非 "world")
  → RViz: block 显示在夹爪下方并跟随移动
```

### 测试验证
```bash
ros2 launch block_stacking_agent sim_agent.launch.py
ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once
ros2 topic echo /block_markers --once | grep frame_id
# → frame_id: hand_base_link  ✅
```
