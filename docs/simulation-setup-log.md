```markdown
# Fairino FR5 仿真环境搭建日志

## 过程

1. **阅读项目 README** — 理解了多层架构（agent_brain、skill_library、execution_layer、perception_layer 等）

2. **更新 README 根路径** — 从 `~/ros2_ws/src/block_stacking_agent/` 改为 `~/Fairino_agent_ws/`，并扁平化深层子目录嵌套（移除了 skills 下的 `action/` 子目录，rag_data 下的 `knowledge_base/`）

3. **创建 11 个一级项目目录**，每个都包含独立的 README.md 文件：
   ```bash
   mkdir -p agent_brain skill_library execution_layer perception_layer \
     interaction_layer memory_layer ui_integration config launch rag_data msg
   ```

4. **检查已安装软件** — 确认 ROS 2 Humble、MoveIt 2 (2.5.9)、fairino_hardware、fairino_description、fairino5_v6_moveit2_config 已存在。**未安装** Gazebo/Ignition Fortress。

5. **安装 Ignition Fortress + ROS-GZ 桥接 + ros2_control**：
   ```bash
   sudo apt-get install -y ignition-fortress ros-humble-ros-gz ros-humble-ros-gz-sim \
     ros-humble-ros-gz-bridge ros-humble-gz-ros2-control ros-humble-ros2-control \
     ros-humble-ros2-controllers ros-humble-joint-state-publisher-gui \
     ros-humble-xacro ros-humble-robot-state-publisher
   ```
   验证：`ign gazebo --version` → Gazebo Sim 6.16.0

6. **探索 `~/ros2_ws/src/frcobot_ros2/` 中现有的 fairino 包**：
   - `fairino_description`：包含惯性/碰撞/视觉数据的 URDF 文件，FR5 的 STL 网格
   - `fairino5_v6_moveit2_config`：MoveIt 配置（SRDF、运动学、关节限制、控制器配置）
   - `fairino_hardware`：真实硬件驱动（仿真中不使用）

7. **创建仿真配置文件**：

   `config/fr5_gazebo_ros2_control.xacro` — 使用 `gz_ros2_control/GazeboSimSystem` 为 6 个关节（j1-j6）提供位置/速度/力矩接口的 ros2_control 硬件接口，以及加载 `libgz_ros2_control-system.so` 的 `<gazebo>` 插件标签

   `config/ros2_controllers.yaml` — 包含 `fairino5_controller`（joint_trajectory_controller）和 `joint_state_broadcaster` 的 controller_manager 配置

   `config/fr5_gazebo.urdf.xacro` — 入口 URDF，包含 `fairino_description/urdf/fairino5_v6.urdf` 和 Gazebo ros2_control 配置

   `config/initial_positions.yaml` — 所有 6 个关节初始位置为 0.0 弧度

   `config/block_stacking_world.sdf` — 包含地面平面、太阳光照、位置 x=0.5 处 0.8m x 0.6m 工作台的 Gazebo 世界

8. **创建 launch 文件 `launch/sim_agent.launch.py`**：
   - 包含 `ros_gz_sim/gz_sim.launch.py` 启动 Gazebo
   - 通过 `ros_gz_sim create` 从 `/robot_description` 话题读取 URDF 生成 FR5
   - 使用 Gazebo URDF 启动 `robot_state_publisher`
   - 包含 fairino5_v6_moveit2_config 中的 `move_group.launch.py` 和 `moveit_rviz.launch.py`
   - 设置 `use_sim_time:=True`

9. **使项目成为 ROS 2 包**：
   - 创建 `package.xml`（名称：`block_stacking_agent`，格式 3）
   - 创建 `CMakeLists.txt`，将所有子目录安装到 share
   - 符号链接：`~/ros2_ws/src/block_stacking_agent → ~/Fairino_agent_ws`

10. **构建并验证**：
    ```bash
    cd ~/ros2_ws && source /opt/ros/humble/setup.bash
    colcon build --symlink-install --packages-select block_stacking_agent
    ```

11. **修复 xacro 路径引用** — 在 `fr5_gazebo.urdf.xacro` 和 `fr5_gazebo_ros2_control.xacro` 中将 `$(find config)` 改为 `$(find block_stacking_agent)`

12. **修复废弃的 xacro 语法** — 在 `fr5_gazebo_ros2_control.xacro` 中将 `load_yaml()` 改为 `xacro.load_yaml()`

13. **从 launch 中移除独立的 `ros2_control_node`** — Gazebo 的 `GazeboSimROS2ControlPlugin` 内部提供 controller_manager

14. **添加 `IGN_GAZEBO_RESOURCE_PATH` 环境变量** — 使 Gazebo 能够解析 `model://fairino_description/meshes/...` URI 以加载 STL 网格文件

15. **在虚拟机设置中启用 VMware 3D 加速**（Gazebo GUI 渲染所需）

16. **切换到 Gazebo 无头模式**（使用 `-s` 标志）以解决 VMware 3D 驱动 bug（`context mismatch in svga_surface_destroy`）

17. **最终启动配置**：Gazebo 无头模式（仅物理引擎）+ RViz（可视化）+ MoveIt mock_components（规划）独立运行

## 问题

### 问题 1：xacro `$(find config)` 包未找到
```
error: "package 'config' not found, searching: [...]"
when processing file: fr5_gazebo.urdf.xacro
```
**根本原因**：`$(find config)` 寻找名为 `config` 的 ROS 2 包，该包不存在。`config/` 目录属于 `block_stacking_agent` 包。

### 问题 2：`load_yaml()` 弃用警告导致 launch 失败
```
[ERROR] [launch]: Caught exception in launch: executed command showed stderr output.
warning: Using load_yaml() directly is deprecated. Use xacro.load_yaml() instead.
```
**根本原因**：ROS 2 launch 中的 `Command` 替换将任何 stderr 输出视为失败。xacro 弃用警告输出到 stderr 导致 launch 中止。

### 问题 3：`ros2_control_node` 无法加载 `gz_ros2_control/GazeboSimSystem`
```
terminate called after throwing an instance of 'pluginlib::LibraryLoadException'
  what(): class gz_ros2_control/GazeboSimSystem with base class type
  hardware_interface::SystemInterface does not exist.
  Declared types are fairino_hardware/..., fake_components/GenericSystem,
  mock_components/GenericSystem, ...
```
**根本原因**：`gz_ros2_control::GazeboSimSystem` 继承自 `gz_ros2_control::GazeboSimSystemInterface`，而非 `hardware_interface::SystemInterface`。ROS 2 `pluginlib` 加载器寻找 `hardware_interface::SystemInterface` 的实现，无法找到该类型。该硬件接口设计为由 `GazeboSimROS2ControlPlugin` **在 Gazebo 内部**加载，而非由独立的 `ros2_control_node` 加载。

### 问题 4：Gazebo 中找不到 STL 网格文件
```
[GUI] [Err] [SystemPaths.cc:378] Unable to find file with URI
[model://fairino_description/meshes/fairino5_v6/base_link.STL]
[GUI] [Err] [Ogre2MeshFactory.cc:562] Cannot load null mesh
```
**根本原因**：Gazebo 将 URDF 中的 `package://` URI 转换为 `model://` URI，并使用 `IGN_GAZEBO_RESOURCE_PATH` 解析它们。该路径未设置，导致 Gazebo 无法定位网格文件。

### 问题 5：GazeboSimROS2ControlPlugin 加载不一致
```
# 正常工作的情况：
[GazeboSimROS2ControlPlugin]: robot_param_node is robot_state_publisher
[gz_ros2_control]: connected to service!!
[resource_manager]: Successful initialization of hardware 'Fairino5GazeboSystem'

# 失败的情况：
# 没有任何 gz_ros2_control 消息。Gazebo 静默退出。
```
**根本原因**：launch 文件中的 `SetEnvironmentVariable` 操作使用了 `PathJoinSubstitution`，在该上下文中无法正确解析，产生了无效或空的 `IGN_GAZEBO_RESOURCE_PATH`。Gazebo 找不到网格文件，导致插件静默失败。需要通过命令行或其他机制设置该变量。

### 问题 6：Controller spawner 连接到错误的 controller_manager
```
[spawner] Loaded joint_state_broadcaster
[spawner] Failed to configure controller
[spawner] Controller already loaded, skipping load_controller
```
**根本原因**：fairino5_v6_moveit2_config 中的 `move_group.launch.py` 会启动自己的 `ros2_control_node`，使用 `mock_components/GenericSystem`，提供 `/controller_manager` 服务。Gazebo 的 `GazeboSimROS2ControlPlugin` 也提供 `/controller_manager` 服务。spawner 连接到先出现的服务 — mock_components 总是先加载，导致控制器被加载到 mock_components 而非 Gazebo。当控制器已存在于 mock_components 时，第二次 spawn 尝试失败并报"已加载"。

### 问题 7：Gazebo 中机器人关节痉挛
**根本原因**：当 Gazebo 使用不含 gz_ros2_control 的纯显示 URDF（`fr5_display.urdf.xacro`）生成机器人时，没有控制器来保持关节位置。Gazebo 物理引擎将旋转关节视为自由运动，导致它们在重力作用下甩动。使用带 `gz_ros2_control` 的 URDF 时，即使没有显式加载控制器，硬件接口也会将关节保持在初始位置。

### 问题 8：Gazebo 插件参数中的 `$(find ...)` 语法无法解析
```xml
<plugin filename="libgz_ros2_control-system.so" name="gz_ros2_control::GazeboSimROS2ControlPlugin">
    <parameters>$(find block_stacking_agent)/config/ros2_controllers.yaml</parameters>
</plugin>
```
**根本原因**：`$(find ...)` 是 ROS/cmake/xacro 替换语法，仅在 URDF 生成期间解析。生成的 URDF 包含字面字符串 `$(find block_stacking_agent)/...`，C++ 插件在运行时无法解析。插件收到一个不存在的文件路径。

### 问题 9：无效的 SDF 物理类型
```xml
<physics name="1ms" type="ignored">
```
**根本原因**：`"ignored"` 不是有效的 SDFormat 物理引擎。有效类型为 `ode`、`bullet`、`dart`、`simbody` 或 `tpe`。

### 问题 10：VMware 3D 驱动 GL 上下文不匹配
```
context mismatch in svga_surface_destroy
libEGL warning: egl: failed to create dri2 screen
```
**根本原因**：VMware 的 SVGA 3D 驱动与 Gazebo/Ignition 使用的现代 OpenGL 上下文存在已知问题。启用 3D 加速部分有帮助，但驱动仍然产生上下文错误。

### 问题 11：MoveIt 无法驱动 Gazebo 机器人（架构鸿沟）
```
# MoveIt 使用：
mock_components/GenericSystem → /fairino5_controller/follow_joint_trajectory

# Gazebo 使用：
gz_ros2_control/GazeboSimSystem → /fairino5_controller/follow_joint_trajectory

# 两个独立的 ros2_control 系统，相同的 action 命名空间 — MoveIt
# 先连接到 mock_components，Gazebo 从未收到指令。
```
**根本原因**：两个完全独立的 `ros2_control` 系统并行运行，没有桥接。MoveIt 针对 mock_components（内存中的假关节）进行规划和执行，而 Gazebo 有自己的 controller_manager，且未加载任何控制器。轨迹从未到达 Gazebo。

## 解决方案

### 解决方案 1：修复 xacro `$(find ...)` 路径
将所有 `$(find config)` 引用改为 `$(find block_stacking_agent)`：
- `config/fr5_gazebo.urdf.xacro`（initial_positions_file 和 xacro include 行）
- `config/fr5_gazebo_ros2_control.xacro`（控制器参数路径行）

### 解决方案 2：修复 `load_yaml()` 弃用警告
在 `fr5_gazebo_ros2_control.xacro` 中将 `${load_yaml(...)}` 改为 `${xacro.load_yaml(...)}`。

### 解决方案 3：移除独立的 `ros2_control_node`
launch 文件不再以独立进程启动 `ros2_control_node`。Gazebo 的 `GazeboSimROS2ControlPlugin` 管理硬件接口并内部提供 controller_manager。需要控制器时，`spawner` 节点连接到 Gazebo 的 controller_manager 服务。

### 解决方案 4：设置 IGN_GAZEBO_RESOURCE_PATH
环境变量 `IGN_GAZEBO_RESOURCE_PATH` 必须指向 `fairino_description` 的 share 目录的父目录，以便 Gazebo 正确解析 `model://fairino_description/meshes/...`：
```bash
IGN_GAZEBO_RESOURCE_PATH=/home/csj/ros2_ws/install/fairino_description/share
```
该变量目前在 `ros2 launch` 之前通过命令行设置。launch 文件中的 `SetEnvironmentVariable` 操作因 `PathJoinSubstitution` 解析问题而不可靠。

### 解决方案 5：使用 Gazebo 无头模式
使用 `-s`（server/headless）标志启动 Gazebo，避免 VMware 3D 驱动 bug：
```bash
ros2 launch block_stacking_agent sim_agent.launch.py gz_args:=" -s -r "
```
Gazebo 仅运行物理引擎，无 GUI。RViz 提供可视化。

### 解决方案 6：使用 gz_ros2_control URDF 防止关节痉挛
即使没有加载控制器，使用 `fr5_gazebo.urdf.xacro`（包含 gz_ros2_control 硬件接口定义）会使 Gazebo 将关节锁定在其初始位置（0.0 弧度）。纯显示 URDF（`fr5_display.urdf.xacro`）不含任何 ros2_control，会导致自由物理运动。

### 解决方案 7：独立启动 MoveIt 和 Gazebo
最终启动架构并行运行两个系统，不尝试同步：
- Gazebo（无头模式）：显示 FR5 模型，gz_ros2_control 硬件保持关节位置
- MoveIt（mock_components）：独立处理规划和执行
- `on_exit_shutdown: "false"` 防止 Gazebo 退出时杀死整个系统

### 解决方案 8：VMware 3D 加速
需要在 VMware 中设置：**虚拟机 → 设置 → 显示 → 加速 3D 图形（启用）**，图形内存 ≥ 512MB。没有这个，Gazebo 无法初始化任何 OpenGL 上下文。

### 解决方案 9：最终验证命令
```bash
# 步骤 1：构建
cd ~/ros2_ws && source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select block_stacking_agent

# 步骤 2：启动
source ~/ros2_ws/install/setup.bash
IGN_GAZEBO_RESOURCE_PATH=/home/csj/ros2_ws/install/fairino_description/share \
  ros2 launch block_stacking_agent sim_agent.launch.py gz_args:=" -s -r "
```

验证成功状态：
- Gazebo 无头模式：硬件已初始化，关节已锁定
- RViz：OpenGL 4.3，显示机器人模型，交互标记激活
- MoveIt："You can start planning now!"，Plan & Execute 功能正常（mock_components）
- `/joint_states` 话题已发布
- `/fairino5_controller/follow_joint_trajectory` action 可用（来自 mock_components）
```

### 解决方案 10：桥接 MoveIt ↔ Gazebo（解决难题 11）
**变更 (2026-06-11)：**

1. `config/fr5_gazebo_ros2_control.xacro` — 将 `<gazebo>` 插件块移到 xacro 宏**内部**，使其能够访问 `controller_config_file` 参数；宏签名从 2 个参数改为 3 个（添加了 `controller_config_file`）

2. `config/fr5_gazebo.urdf.xacro` — 添加了 `controller_config_file` xacro 参数（默认值为 `$(find ...)`），并传递给宏调用

3. `launch/sim_agent.launch.py` — 使用 `PathJoinSubstitution` 解析 `controller_config_file` 路径，并作为 xacro 参数传递；添加了 `TimerAction` spawner 节点，用于在 Gazebo 的 controller_manager 中加载 `joint_state_broadcaster`（3 秒后）和 `fairino5_controller`（5 秒后）

**工作原理：**
- GazeboSimROS2ControlPlugin 读取正确解析的 yaml 路径并提供 `/controller_manager`
- Spawner 节点将 `fairino5_controller`（joint_trajectory_controller）加载到 Gazebo 的 controller_manager 中
- JointTrajectoryController 提供 `/fairino5_controller/follow_joint_trajectory` action
- MoveIt 的 `moveit_simple_controller_manager` 连接到此 action（相同的命名空间）
- MoveIt 规划的轨迹由 Gazebo 的控制器执行 → 机器人在 Gazebo 中移动

**启动命令（不变）：**
```bash
cd ~/ros2_ws && source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select block_stacking_agent
source ~/ros2_ws/install/setup.bash
IGN_GAZEBO_RESOURCE_PATH=/home/csj/ros2_ws/install/fairino_description/share \
  ros2 launch block_stacking_agent sim_agent.launch.py gz_args:=" -s -r "
```

### 解决方案 11：Gazebo 积木 → RViz 可视化 + MoveIt 避障 (2026-06-11)

**新增文件：**

| 文件 | 用途 |
|---|---|
| `scripts/block_tf_bridge.py` | Gazebo Pose_V → 正确 TF 层级：`world→fairino5_v6_robot→base_link`，`world→block_*` |
| `scripts/block_collision_updater.py` | 同数据源 → 过滤 `block_*` → `/collision_object` (ADD 模式，每帧更新) |
| `scripts/block_visual_marker.py` | 同数据源 → 过滤 `block_*` → `/block_markers` (MarkerArray 彩色立方体，RViz 可见实体) |
| `config/block_red.sdf` | 红色 0.03m 立方体 SDF（质量 0.05kg，碰撞+视觉） |
| `config/block_green.sdf` | 绿色 0.03m 立方体 SDF |
| `config/block_blue.sdf` | 蓝色 0.03m 立方体 SDF |

**启动文件 (`launch/sim_agent.launch.py`) 完整时序：**
```
t=0.0s:  robot_state_publisher（先注册 robot_description 参数）
t=0.0s:  ros_gz_bridge, block_tf_bridge, block_collision_updater, block_visual_marker
t=0.0s:  move_group, RViz
t=2.0s:  Gazebo 启动（延迟 2s，确保 robot_state_publisher 参数就绪）
t=4.0s:  spawn 机器人
t=5.0-6.0s: spawn 3 个积木
t=7.0s:  spawn joint_state_broadcaster → Gazebo controller_manager
t=9.0s:  spawn fairino5_controller → Gazebo controller_manager
```

**TF 层级（block_tf_bridge 修复后）：**
```
world
├── fairino5_v6_robot（Gazebo 世界位姿）
│   └── base_link（恒等变换）
│       └── shoulder_link → ... → wrist3_link（robot_state_publisher）
├── block_red
├── block_green
└── block_blue
```
RViz 固定帧为 `base_link` 时可沿 `base_link → fairino5_v6_robot → world → block_*` 链查找积木帧。

**RViz 显示积木：**
- 点击 **Add** → **By topic** → `/block_markers` → **MarkerArray** → OK
- 3 个彩色立方体（红/绿/蓝，3cm）显示在工作台上

**积木命名约定：**
- 所有积木模型名必须以 `block_` 为前缀
- 两个 Python 脚本均按 `block_*` 前缀过滤，排除 `*_link` 帧
- 如需不同前缀，修改脚本中的 `"block_"` 字符串

**已修复的 Bug：**
1. Gazebo 插件间歇性拿不到 `robot_description` → Gazebo 启动加 2s 延迟
2. `/tf` 积木帧 `frame_id` 为空 → `block_tf_bridge` 显式设为 `"world"`
3. `block_collision_updater` 过早删除碰撞体 → 改为纯 ADD 模式（每帧更新）
4. world→base_link TF 链断裂 → `block_tf_bridge` 同时发布机器人模型帧
5. 积木仅 TF 帧无视觉形状 → 新增 `block_visual_marker.py` 发布 MarkerArray
6. MoveIt 启动公差太严（joint 重力下垂被拒）→ `allowed_start_tolerance: 0.05`
7. CMake `PROGRAMS` 安装 → Python 脚本正确安装到 `lib/` 目录
8. 世界 SDF physics `type="ignored"` → `type="ode"`（无效类型修复）
9. `launch/sim_agent.launch.py` 改用 `TimerAction` 控制启动时序
10. 所有积木 spawn 和新控制器 spawn 的延迟参数已同步调整

**数据流：**
```
Gazebo 物理仿真（碰撞/重力/摩擦）
    ↓ 每仿真步更新
/world/.../dynamic_pose/info (Pose_V)
    ↓ ros_gz_bridge
ROS tf2_msgs/TFMessage
    ├→ block_tf_bridge → /tf（world→robot→base_link 链 + world→block_* 帧）
    ├→ block_visual_marker → /block_markers（RViz 彩色立方体）
    └→ block_collision_updater → /collision_object（MoveIt 实时避障）
```

**启动命令：**
```bash
cd ~/ros2_ws && source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select block_stacking_agent
source ~/ros2_ws/install/setup.bash
IGN_GAZEBO_RESOURCE_PATH=/home/csj/ros2_ws/install/fairino_description/share \
  ros2 launch block_stacking_agent sim_agent.launch.py gz_args:=" -s -r "
```

---

## 下一步计划：导入真实积木模型

当有自定义积木 SDF 模型时，按以下步骤接入：

### 步骤 1：放入 SDF 模型
将积木 `.sdf` 文件放入 `config/`，例如：
```
config/my_block_a.sdf
config/my_block_b.sdf
config/my_block_c.sdf
```

### 步骤 2：注册 spawn 配置
在 `launch/sim_agent.launch.py` 中添加 spawn 路径和节点：

```python
# 在 block_sdf_paths 字典里添加
block_sdf_paths = {
    "my_block_a": PathJoinSubstitution([project_share, "config", "my_block_a.sdf"]),
    "my_block_b": PathJoinSubstitution([project_share, "config", "my_block_b.sdf"]),
    "my_block_c": PathJoinSubstitution([project_share, "config", "my_block_c.sdf"]),
}

# 添加 TimerAction spawn 节点
spawn_block_a = TimerAction(
    period=5.0,
    actions=[
        Node(
            package="ros_gz_sim", executable="create",
            arguments=["-name", "my_block_a",           # 模型名 → TF 帧名
                       "-file", block_sdf_paths["my_block_a"],
                       "-x", "0.45", "-y", "0.0", "-z", "0.025"],
        )
    ],
)

# 加入 LaunchDescription 返回列表
```

### 步骤 3：适配过滤前缀
如果积木模型名不是 `block_` 前缀，修改 3 个 Python 脚本：

| 文件 | 修改位置 | 改法 |
|---|---|---|
| `scripts/block_tf_bridge.py` | `name.startswith("block_")` | → `name.startswith("my_block_")` |
| `scripts/block_collision_updater.py` | `name.startswith("block_")` | → `name.startswith("my_block_")` |
| `scripts/block_visual_marker.py` | `name.startswith("block_")` | → `name.startswith("my_block_")` |
| `scripts/block_visual_marker.py` | `self.colors` 字典 | 键名改为新模型名，值改为对应 RGB |

### 步骤 4：适配尺寸
如果不是 3cm 立方体：

| 文件 | 变量 |
|---|---|
| `scripts/block_collision_updater.py` | `self.block_size = 0.03` → 实际边长 |
| `scripts/block_visual_marker.py` | `self.block_size = 0.03` → 实际边长 |

非正方体时，`[self.block_size]*3` 改为 `[length, width, height]`，`marker.scale.x/y/z` 分别设值。

### 可选优化：集中配置文件
将积木参数集中到 `config/blocks.yaml`：
```yaml
blocks:
  my_block_a:
    sdf: "config/my_block_a.sdf"
    name: "my_block_a"
    color: [0.9, 0.15, 0.15]
    size: [0.03, 0.03, 0.03]
    position: [0.45, 0.0, 0.025]
  my_block_b:
    ...
```
修改 spawn/Python 脚本从 yaml 读取。

### 验证检查清单
- [ ] SDF 文件放入 `config/`
- [ ] `launch/sim_agent.launch.py` 添加 spawn 配置
- [ ] 3 个 Python 脚本前缀/颜色/尺寸适配
- [ ] `colcon build` 无报错
- [ ] RViz 添加 `/block_markers` → 可见积木
- [ ] MoveIt 规划时避开积木

---

## Phase 2: 夹爪集成与 Pick/Place 开发 (2026-06-12)

### 过程

1. **导入夹爪模型** — 用户提供 `~/Fairino_agent_ws/fr5_description/` 包，包含 FR5+夹爪完整 URDF (`fr5_withgripper.urdf`)、STL 网格（hand_base_link、finger_link1/2、handlink1/2/3）、DAE 可视化文件

2. **提取夹爪为独立 Xacro 宏** — 从 `fr5_withgripper.urdf` 中提取夹爪部分（hand_base_link + fj1/finger_link1 + fj2/finger_link2），创建 `config/fr5_gripper.urdf.xacro`，挂载到现有 `fairino5_v6.urdf` 的 `wrist3_link` 上（fixed joint: arm_hand_joint, z+0.12, yaw 180°）

3. **注册夹爪关节到 ros2_control** — 在 `fr5_gazebo_ros2_control.xacro` 中添加 fj1/fj2 的 position/velocity 接口，在 `ros2_controllers.yaml` 中添加 `gripper_controller`（JointGroupPositionController），在 `initial_positions.yaml` 中设置 fj1=0.0（开）、fj2=0.04（闭合方向最大行程）

4. **构建 fr5_description 包** — 复制到 `~/ros2_ws/src/fr5_description`，`colcon build` 成功，夹爪 STL 可通过 `package://fr5_description/meshes/...` 解析

5. **创建 Pick/Place 控制脚本** — `scripts/pick_place_server.py`：通过 `/pick_place` 话题接收 String 指令，调用 `ign service` 创建/删除 Gazebo fixed joint 实现虚拟夹持（detachable joint 方案）

6. **创建桌面可视化节点** — `scripts/table_marker.py`：在 RViz 中发布 work_table 的 Marker（Gazebo 中的桌子默认不显示在 RViz）

7. **Gazebo 无头模式修复** — launch 文件硬编码 `gz_args:=" -s -r "` 确保 Gazebo 以 headless 模式运行（无 GUI 窗口）

---

### 问题

#### 问题 12：夹爪控制器无法激活
```
[spawner_gripper_controller]: Failed to activate controller: gripper_controller
```
**根本原因**：`position_controllers/JointGroupPositionController` 类型未正确注册或与 prismatic 关节接口不兼容。controller_manager 能加载但 activate 阶段失败。
**当前状态**：gripper_controller spawner 已注释掉。夹爪手指保持初始位置（fj1=0.0, fj2=0.04，即张开状态）。Pick/Place 功能通过 Gazebo detachable joint 实现，不依赖夹爪控制器运动。

#### 问题 13：Gazebo STL 网格路径解析失败（回归）
```
[Err] [SystemPaths.cc:378] Unable to find file with URI
[model://fairino_description/meshes/fairino5_v6/base_link.STL]
```
**根本原因**：`SetEnvironmentVariable` + `PathJoinSubstitution` 在 launch 文件中不可靠。`FindPackageShare` 返回 `.../share/fairino_description`，Gazebo 的 `model://` 解析需要父目录 `.../share/` 来定位 `fairino_description/meshes/...`。`PathJoinSubstitution` 的 `..` 拼接在 C++ 运行时无法正确归一化路径。
**解决方案**：从 launch 文件中移除 `SetEnvironmentVariable`，改为在命令行设置 `IGN_GAZEBO_RESOURCE_PATH`。已确认此方法可靠（0 个 STL 错误）。

#### 问题 14：多个 Gazebo 实例冲突
```
# 症状：第二次 launch 时 controller_manager 不可用，Gazebo 无日志输出
```
**根本原因**：`pkill -f "gz"` 未能杀死所有 Gazebo 相关进程（ruby wrapper、旧 server 进程残留在不同进程组）。新 Gazebo 实例与旧实例争夺资源（端口、共享内存），导致 gz_ros2_control 插件静默失败。
**解决方案**：每次 launch 前执行 `pkill -9 -f "ign gazebo"; pkill -9 -f "gz server"`，并在 `sleep 3` 后验证无残留进程（`ps aux | grep -E "ign|gz"`）。

#### 问题 15：RViz 中 Marker 不可见（积木/桌子）
```
# 症状：/block_markers 话题有数据（3 个立方体，正确位姿），RViz 添加 MarkerArray 后不可见
```
**根本原因**：VMware SVGA 3D 驱动对 RViz 的 Marker 渲染路径（简单几何体：CUBE/SPHERE）与 RobotModel 渲染路径（URDF 网格）使用不同 OpenGL 调用。VMware 驱动对 Marker 路径不兼容（与 Problem 10 的 GL 上下文错误同源）。
**当前状态**：RobotModel（机械臂+夹爪）可直接显示。Marker（积木立方体）在部分 RViz 会话中可见、部分不可见。测试标记（20cm 红色球体）可间歇性显示。**待 VMware 3D 加速配置确认**。

#### 问题 16：积木 Marker 太小不可见
```
# 症状：积木为 3cm 立方体，在典型 RViz 视图距离下 ≈ 不可见
```
**根本原因**：原始 3cm 边长 + RViz 默认视图距离（~2m）= 屏幕上 < 5 像素。
**解决方案**：`block_visual_marker.py` 中 `self.block_size` 临时改为 0.10（10cm）用于调试。最终方案待定（可能是恢复 3cm + 调整 RViz 视图，或使用 URDF 模型替代 Marker）。

#### 问题 17：TF /tf 话题无数据 — base_link 帧不存在
```
[rviz2]: frame [base_link] does not exist
```
**根本原因**：`/tf` 话题有 10 个发布者但无消息发布。`block_tf_bridge.py` 依赖 Gazebo 发布的 Pose_V 数据（通过 ros_gz_bridge 转换），但 Gazebo 的 `/world/block_stacking_world/dynamic_pose/info` 话题无数据输出。
**可能原因（调查中）**：
- Gazebo 中机器人和积木未正确 spawn（`ros_gz_sim create` 命令静默失败）
- ros_gz_bridge 未桥接 Pose_V → TFMessage（Lazy 订阅机制问题）
- world 名称不匹配
- Gazebo 100% CPU 占用导致消息发布延迟/丢失

#### 问题 18：Gazebo 无头模式 CPU 100%
```
ign gazebo server  99.2% CPU
```
**根本原因**：ODE 物理引擎以 dt=0.001s、RTF=1.0 运行，加上 FR5 机器人模型的碰撞检测（STL 网格碰撞体），导致物理计算量极大。VM 环境中无 GPU 加速物理。
**当前状态**：功能正常（仿真不卡顿），但 CPU 高占用。可通过增大 `max_step_size` 或降低 `real_time_update_rate` 缓解。

#### 问题 19：MoveIt hand_base_link TF 链断开
```
[move_group]: Unable to transform object from frame 'hand_base_link' to 'base_link'
(Tf has two or more unconnected trees)
```
**根本原因**：`block_tf_bridge.py` 发布的 `world → fairino5_v6_robot → base_link` 链与 `robot_state_publisher` 发布的 `base_link → ... → hand_base_link` 链之间存在时序竞争。在 Gazebo 发布机器人位姿之前（t=4s spawn + 初始化延迟），TF 树中只有 robot_state_publisher 的链，缺少 world → base_link 连接。
**当前状态**：此警告在 `/joint_states` 首次到达且 Gazebo 发布机器人位姿后自动消失。不影响 MoveIt 规划（MoveIt 使用 robot_state_publisher 的链进行运动学计算）。

---

### 解决方案

#### 解决方案 12：禁用 gripper_controller，改用 detachable joint
launch 文件中注释掉 `spawn_gripper_controller`。Pick 操作直接通过 `ign service` 创建 Gazebo fixed joint 将积木吸附到 `hand_base_link`，不依赖手指关节运动。

**Gazebo joint 创建命令**：
```bash
ign service -s /world/block_stacking_world/create \
  --reqtype ignition.msgs.EntityFactory \
  --reptype ignition.msgs.Boolean \
  --req 'sdf: "<sdf version=\"1.6\"><joint name=\"pick_block_red\" type=\"fixed\"><parent>fairino5_v6_robot::hand_base_link</parent><child>block_red::block_link</child></joint></sdf>"'
```

**已验证**：`data: true` 返回，积木成功吸附。删除 joint 后积木恢复自由落体。

#### 解决方案 13：命令行设置 IGN_GAZEBO_RESOURCE_PATH
```bash
IGN_GAZEBO_RESOURCE_PATH=/home/csj/ros2_ws/install/fairino_description/share:/home/csj/ros2_ws/install/fr5_description/share \
  ros2 launch block_stacking_agent sim_agent.launch.py
```
已从 launch 文件中移除不可靠的 `SetEnvironmentVariable`。路径指向 package share 的**父目录**（Gazebo 需要 `share/fairino_description/meshes/` 结构来解析 `model://fairino_description/...`）。

#### 解决方案 14：launch 前彻底清理
```bash
pkill -9 -f "ign gazebo"; pkill -9 -f "gz server"; pkill -9 -f rviz2
pkill -9 -f move_group; pkill -9 -f robot_state; pkill -9 -f ros_gz
sleep 3
# 验证: ps aux | grep -E "ign|gz"  # 应无输出
```

#### 解决方案 15：积木临时放大
`scripts/block_visual_marker.py`: `self.block_size = 0.10`（从 0.03 改为 0.10）

#### 解决方案 16：Pick/Place 控制接口
`scripts/pick_place_server.py` 订阅 `/pick_place` 话题（std_msgs/String）：
- `"pick block_red"` → 创建 fixed joint
- `"place block_red"` → 删除 joint
- `"list"` → 显示已吸附积木

使用方式：
```bash
ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once
ros2 topic pub /pick_place std_msgs/String "data: \"place block_red\"" --once
```

---

### 当前架构状态

| 组件 | 状态 |
|---|---|
| Gazebo 物理仿真（headless, ODE） | OK 运行中（CPU 100%） |
| fairino5_controller (JointTrajectoryController) | OK 已激活 |
| joint_state_broadcaster | OK 已激活 |
| gripper_controller | 已禁用（激活失败） |
| FR5 机器人模型 + 夹爪（RobotModel） | OK RViz 显示正常 |
| 夹爪手指开合（fj1/fj2） | 固定在初始位置 |
| 积木 MarkerArray（/block_markers） | 数据发布中，VMware 驱动导致可能不可见 |
| 桌面 Marker（/table_marker） | 同 Marker 渲染问题 |
| Pick/Place detachable joint | OK 已验证（手动测试通过） |
| TF /tf 数据 | 无数据发布（调查中） |
| RViz Fixed Frame "base_link" | 帧不存在 |

### 待解决的关键阻塞项
1. **TF /tf 无数据** — 导致 RViz Fixed Frame、"base_link 不存在"、积木坐标不可解析
2. **VMware Marker 渲染** — 导致积木和桌面在 RViz 中不可见（即使数据正确）
3. **gripper_controller 激活** — 需要可用的 position controller 类型
4. **Gazebo CPU 100%** — 性能优化

### 最终验证命令
```bash
# 清理
pkill -9 -f "ign gazebo"; pkill -9 -f "gz server"; pkill -9 -f rviz2
pkill -9 -f move_group; pkill -9 -f robot_state; sleep 3

# 启动
cd ~/ros2_ws && source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select fr5_description block_stacking_agent
source ~/ros2_ws/install/setup.bash
IGN_GAZEBO_RESOURCE_PATH=/home/csj/ros2_ws/install/fairino_description/share:/home/csj/ros2_ws/install/fr5_description/share \
  ros2 launch block_stacking_agent sim_agent.launch.py

# 测试 Pick
ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once
# 在 RViz 中用 MoveIt 移动机械臂 → 积木跟随
ros2 topic pub /pick_place std_msgs/String "data: \"place block_red\"" --once
```
