# Fairino FR5 仿真环境搭建日志

> 最后更新：2026-06-18
> 上级索引：[VIBECODING_LOG.md](./VIBECODING_LOG.md) — 结论性日志
> 关联文档：[simulation_data_flow.md](./simulation_data_flow.md) — 运行时数据流与 TF 树参考

---

## 一、目标

终端输入 `pick block_red` → RViz 中 block 附着到夹爪并跟随移动，MoveIt 可正常规划避障。

---

## 二、当前状态（2026-06-18）— ✅ 核心功能已实现

| 组件 | 状态 | 备注 |
|------|------|------|
| Gazebo 物理仿真（headless, ODE） | ✅ 运行中 | CPU 占用偏高 |
| fairino5_controller (JointTrajectoryController) | ✅ 已激活 | 通过 Gazebo controller_manager |
| joint_state_broadcaster | ✅ 已激活 | |
| FR5 机器人模型 + 夹爪（RViz RobotModel） | ✅ 显示正常 | |
| block_* TF 帧（Gazebo → ROS） | ✅ block_tf_bridge 发布 | |
| block MarkerArray 可视化（RViz） | ✅ block_visual_marker 发布 | |
| block CollisionObject（MoveIt 避障） | ✅ block_collision_updater 发布 | |
| Pick/Place detachable joint（Gazebo） | ✅ 手动测试通过 | ign service 创建/删除 fixed joint |
| block 在 RViz 中跟随夹爪 | ✅ ROS param 跨节点同步 | 见 3.4 节 |
| gripper_controller（手指运动） | ❌ 已禁用 | 激活失败，手指固定张开 |
| 桌面 Marker（RViz） | ⚠️ VMware 驱动可能导致不可见 | table_marker.py 发布正常 |
| Gazebo CPU 100% | ⚠️ 待优化 | ODE 物理引擎 dt=0.001s |

---

## 三、环境搭建过程

### 3.1 前期准备

1. **理解多层架构** — 阅读项目 README，确认 agent_brain、skill_library、execution_layer、perception_layer 等分层设计
2. **更新目录路径** — README 根路径从 `~/ros2_ws/src/block_stacking_agent/` 改为 `~/Fairino_agent_ws/`
3. **创建 11 个分层目录**，每个含独立 README.md
4. **确认已安装软件** — ROS 2 Humble、MoveIt 2 (2.5.9)、fairino_hardware、fairino_description 已就绪；**Gazebo/Ignition Fortress 未安装**

### 3.2 安装 Ignition Fortress + ros_gz 桥接

```bash
sudo apt-get install -y ignition-fortress ros-humble-ros-gz ros-humble-ros-gz-sim \
  ros-humble-ros-gz-bridge ros-humble-gz-ros2-control ros-humble-ros2-control \
  ros-humble-ros2-controllers ros-humble-joint-state-publisher-gui \
  ros-humble-xacro ros-humble-robot-state-publisher
```
验证：`ign gazebo --version` → Gazebo Sim 6.16.0

### 3.3 创建仿真配置文件

| 文件 | 用途 |
|------|------|
| `config/fr5_gazebo_ros2_control.xacro` | gz_ros2_control 硬件接口（6 关节 + 2 夹爪关节的位置/速度接口） |
| `config/ros2_controllers.yaml` | controller_manager 配置（fairino5_controller + joint_state_broadcaster） |
| `config/fr5_gazebo.urdf.xacro` | URDF 入口，包含 fairino5_v6.urdf + Gazebo ros2_control 配置 |
| `config/initial_positions.yaml` | 所有关节初始位置为 0.0 |
| `config/block_stacking_world.sdf` | Gazebo 世界（地面、光照、工作台 x=0.5） |
| `config/block_red/green/blue.sdf` | 3cm 立方体积木（0.05kg，ODE 物理） |

### 3.4 启动文件 (`launch/sim_agent.launch.py`)

核心启动时序（TimerAction 控制）：

```
t=0.0s: robot_state_publisher → 注册 robot_description 参数
t=0.0s: ros_gz_bridge, block_tf_bridge, block_collision_updater, block_visual_marker
t=0.0s: move_group, RViz
t=2.0s: Gazebo 启动（延迟 2s 确保 robot_description 就绪）
t=4.0s: spawn FR5 机器人（从 /robot_description 话题读取 URDF）
t=5.0s: spawn block_red   (x=0.40, y=-0.10, z=0.025)
t=5.5s: spawn block_green (x=0.50, y= 0.00, z=0.025)
t=6.0s: spawn block_blue  (x=0.60, y= 0.10, z=0.025)
t=7.0s: spawn joint_state_broadcaster → Gazebo controller_manager
t=9.0s: spawn fairino5_controller → Gazebo controller_manager
```

### 3.5 构建与运行

```bash
cd ~/ros2_ws && source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select block_stacking_agent fr5_description
source ~/ros2_ws/install/setup.bash
IGN_GAZEBO_RESOURCE_PATH=/home/csj/ros2_ws/install/fairino_description/share:/home/csj/ros2_ws/install/fr5_description/share \
  ros2 launch block_stacking_agent sim_agent.launch.py
```

---

## 四、关键问题与解决方案

### 4.1 编译与启动类

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `$(find config)` 包未找到 | `config/` 不是独立 ROS 2 包，属于 `block_stacking_agent` | 全部改为 `$(find block_stacking_agent)` |
| 2 | `load_yaml()` 弃用警告导致 launch 失败 | xacro 弃用警告输出到 stderr，ROS 2 launch 将任何 stderr 视为失败 | 改为 `xacro.load_yaml()` |
| 3 | `ros2_control_node` 无法加载 `GazeboSimSystem` | 该接口由 Gazebo 内部加载，不应独立启动 | 移除独立 `ros2_control_node`，由 `GazeboSimROS2ControlPlugin` 内部提供 controller_manager |
| 4 | STL 网格文件找不到 | Gazebo 将 `package://` 转为 `model://` URI，需 `IGN_GAZEBO_RESOURCE_PATH` 解析 | 命令行设置环境变量（launch 文件中的 `SetEnvironmentVariable` + `PathJoinSubstitution` 不可靠） |
| 5 | 无效 SDF 物理类型 `"ignored"` | 不是有效 SDFormat 物理引擎 | 改为 `type="ode"` |

### 4.2 运行时行为类

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 6 | Gazebo 中机器人关节痉挛 | 使用不含 gz_ros2_control 的纯显示 URDF，无控制器保持关节位置 | 使用含 `gz_ros2_control` 硬件接口的 URDF，即使控制器未加载也能锁定初始位置 |
| 7 | Controller spawner 连接到错误的 controller_manager | MoveIt 的 `move_group.launch.py` 启动了自己的 `ros2_control_node`（mock_components），先于 Gazebo 提供 `/controller_manager` 服务 | 确保 spawner 连接到 Gazebo 的 controller_manager；通过启动时序（TimerAction 延迟）避开竞争 |
| 8 | Gazebo 插件参数中 `$(find ...)` 无法解析 | C++ 插件运行时无法解析 xacro 替换语法 | 通过 launch 文件的 `PathJoinSubstitution` 解析路径后作为 xacro 参数传入 |
| 9 | MoveIt 无法驱动 Gazebo 机器人（架构鸿沟） | 两套独立 ros2_control 系统并行运行无桥接：MoveIt → mock_components；Gazebo → GazeboSimSystem | 让 spawner 将 `fairino5_controller` 加载到 Gazebo 的 controller_manager，MoveIt 的 `moveit_simple_controller_manager` 连接同一 action 命名空间 |

### 4.3 VMware 虚拟化类

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 10 | VMware 3D 驱动 GL 上下文不匹配 | SVGA 3D 驱动与 Gazebo 的现代 OpenGL 上下文冲突 | ① 启用 VMware 3D 加速（≥512MB 显存）；② Gazebo 使用无头模式 `-s` |
| 11 | RViz 中 Marker（积木立方体）不可见 | VMware 驱动对 Marker 渲染路径（简单几何体）与 RobotModel 路径（URDF 网格）的 OpenGL 调用不兼容 | 间歇性问题；RobotModel 始终可见；Marker 部分会话可见 |

### 4.4 Gazebo 运行时类

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 12 | 多个 Gazebo 实例冲突 | `pkill -f "gz"` 未能杀死所有残留进程 | 启动前执行: `pkill -9 -f "ign gazebo"; pkill -9 -f "gz server"; pkill -9 -f rviz2; pkill -9 -f move_group; pkill -9 -f robot_state`，sleep 3 后验证 |
| 13 | Gazebo 无头模式 CPU 100% | ODE 物理引擎 dt=0.001s + FR5 STL 网格碰撞检测，VM 环境无 GPU 加速物理 | 功能正常，可通过增大 `max_step_size` 或降低 `real_time_update_rate` 缓解 |
| 14 | Gazebo 插件间歇性拿不到 `robot_description` | 时序竞争：Gazebo 启动时 robot_state_publisher 参数尚未就绪 | Gazebo 启动加 2s 延迟 |

### 4.5 TF 与可视化类

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 15 | `/tf` 无数据发布，RViz "base_link 不存在" | `block_tf_bridge.py` 依赖 Gazebo Pose_V，但 ros_gz_bridge 未桥接或 world 名称不匹配 | block_tf_bridge 显式设 `frame_id="world"`；构建正确 TF 层级 `world → fairino5_v6_robot → base_link` |
| 16 | world → base_link TF 链断裂 | 时序竞争：Gazebo 发布机器人位姿前，TF 树只有 robot_state_publisher 的链 | `/joint_states` 到达且 Gazebo 发布位姿后自动恢复；不影响 MoveIt 规划 |
| 17 | 积木仅 TF 帧无视觉形状 | RViz 需要 Marker 才能渲染非 URDF 物体 | 新增 `block_visual_marker.py` 发布 MarkerArray |
| 18 | block_collision_updater 过早删除碰撞体 | 每帧先 REMOVE 再 ADD，间隙中 MoveIt 认为无碰撞体 | 改为纯 ADD 模式（每帧更新覆盖） |
| 19 | MoveIt 启动公差过严 | 关节因重力轻微下垂，超出默认公差被拒 | `allowed_start_tolerance: 0.05` |

---

## 五、Block 跟随夹爪 — ROS Parameter 跨节点同步（2026-06-15 修复）

### 问题

`block_visual_marker.py` 无法跨节点读取 `pick_place_server.py` 的 `attached_blocks` 参数，导致被 pick 的 block marker 不跟随夹爪。

### 三个关键修复

1. **跨节点参数读取** — `block_visual_marker` 原来读取自己节点的 `attached_blocks`（始终为空），改为通过 `GetParameters` 服务客户端定时从 `pick_place_server` 读取参数，绕过 DDS SHM transport 问题
2. **参数类型修复** — `declare_parameter("attached_blocks", [])` 传入空列表导致 ROS 2 Humble 将类型推断为 `byte_array`，改为 `declare_parameter("attached_blocks", [""])` 使类型正确推断为 `string_array`
3. **Clock bridge 修复** — launch 文件缺少 Gazebo → ROS `/clock` 桥接，导致所有 `use_sim_time:=True` 节点的 timer 冻结（包括 marker 发布的 10Hz 和参数轮询的 2Hz）。添加了 `parameter_bridge` 桥接

### 工作原理

```
pick block_red
  → pick_place_server: self.attached.add("block_red") → set_parameters(attached_blocks=['block_red'])
  → block_visual_marker (每0.5s): GetParameters 服务调用 → 获取 ['block_red']
  → publish_markers (每0.1s): marker.frame_id = "hand_base_link" (而非 "world")
  → RViz: block 显示在夹爪下方并跟随移动
```

### 验证

```bash
ros2 launch block_stacking_agent sim_agent.launch.py
ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once
ros2 topic echo /block_markers --once | grep frame_id
# → frame_id: hand_base_link  ✅
```

---

## 六、夹爪集成与 Pick/Place 开发（Phase 2）

### 6.1 过程

1. **导入夹爪模型** — `fr5_description/` 包含 FR5+夹爪完整 URDF、STL 网格、DAE 可视化文件
2. **提取夹爪为独立 Xacro 宏** — `config/fr5_gripper.urdf.xacro`，挂载到 `wrist3_link`（fixed joint: arm_hand_joint, z+0.12, yaw 180°）
3. **注册夹爪关节到 ros2_control** — 添加 fj1/fj2 的位置接口
4. **创建 Pick/Place 控制脚本** — `scripts/pick_place_server.py`：订阅 `/pick_place` 话题，调用 `ign service` 创建/删除 Gazebo fixed joint 实现虚拟夹持（detachable joint 方案）
5. **创建桌面可视化** — `scripts/table_marker.py`

### 6.2 夹爪控制器问题

gripper_controller（`position_controllers/JointGroupPositionController`）能加载但无法激活。当前手指保持初始位置（fj1=0.0, fj2=0.04，张开状态），Pick/Place 通过 Gazebo detachable joint 实现，不依赖手指运动。

### 6.3 Pick/Place 控制接口

`scripts/pick_place_server.py` 订阅 `/pick_place` 话题（std_msgs/String）：

| 命令 | 效果 |
|------|------|
| `"pick block_red"` | 创建 Gazebo fixed joint，积木吸附到 hand_base_link |
| `"place block_red"` | 删除 joint，积木恢复独立物理（受重力下落） |
| `"list"` | 显示已吸附积木列表 |

**Gazebo joint 创建命令（底层）：**
```bash
ign service -s /world/block_stacking_world/create \
  --reqtype ignition.msgs.EntityFactory \
  --reptype ignition.msgs.Boolean \
  --req 'sdf: "<sdf version=\"1.6\"><joint name=\"pick_block_red\" type=\"fixed\"><parent>fairino5_v6_robot::hand_base_link</parent><child>block_red::block_link</child></joint></sdf>"'
```

---

## 七、启动命令速查

### 清理旧进程

```bash
pkill -9 -f "gz sim|rviz2|move_group|robot_state|ros_gz|block_|pick_place|table_|ros2 launch"
sleep 4; ros2 daemon stop; sleep 1; ros2 daemon start; sleep 2
```

### 构建与启动

```bash
cd ~/ros2_ws && source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select block_stacking_agent fr5_description
source ~/ros2_ws/install/setup.bash
IGN_GAZEBO_RESOURCE_PATH=/home/csj/ros2_ws/install/fairino_description/share:/home/csj/ros2_ws/install/fr5_description/share \
  ros2 launch block_stacking_agent sim_agent.launch.py
```

### 测试 Pick/Place

```bash
ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once
# 在 RViz 中用 MoveIt 移动机械臂 → 积木跟随
ros2 topic pub /pick_place std_msgs/String "data: \"place block_red\"" --once
```

---

## 八、积木模型导入指南

当需要新积木模型时：

1. **放入 SDF**：将 `.sdf` 文件放入 `config/`
2. **注册 spawn**：在 `launch/sim_agent.launch.py` 的 `block_sdf_paths` 字典中添加路径和 TimerAction spawn 节点
3. **适配前缀**：修改 3 个 Python 脚本中的 `"block_"` 前缀过滤（`block_tf_bridge.py`、`block_collision_updater.py`、`block_visual_marker.py`）
4. **适配尺寸**：若非 3cm 立方体，修改 `self.block_size` 和 `marker.scale`

> 以上为步骤摘要，完整操作细节已整合至本文档各相关章节。

---

## 九、遗留问题

| 问题 | 优先级 | 说明 |
|------|--------|------|
| Gazebo CPU 100% | 低 | 功能正常，可通过物理参数调优缓解 |
| gripper_controller 激活 | 中 | 需要可用的 position controller 类型；当前 detachable joint 方案绕过 |
| VMware Marker 渲染 | 低 | 间歇性问题，RViz RobotModel 正常 |
| Ghost 节点 | 低 | kill -9 后需约 10 秒 ROS 2 discovery 才能清理 |
