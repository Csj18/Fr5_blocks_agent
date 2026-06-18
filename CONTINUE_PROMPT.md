## Continue: FR5 Block Stacking Simulation

### ✅ Done (pushed)

- **Base fixed**: 1000kg `world` link in xacro + fixed joint → base stays on table at (0.5, 0, 0.05)
- **Table**: 0.05m thick, top at z=0.05
- **Arm motion**: IK via `/compute_ik` → `JointTrajectory` to `/fairino5_controller` → pre-grasp → grasp → retreat
- **Mesh path**: `IGN_GAZEBO_RESOURCE_PATH` set in launch
- **RViz**: Fixed Frame → `world`
- **URDF typo**: `<origins` → `<origin>` (wrist2_link collision, in frcobot_ros2)

### ❌ Problem — Block doesn't physically follow gripper

`ign service /create` returns `data: true` but creates nothing. Gazebo `EntityFactory` only handles `<model>`, not world-level `<joint>`.

### 🔧 To Try

1. **Timer-based `set_pose`**: After pick, loop `ign service set_pose` to teleport block to `hand_base_link` position each tick
2. **`gz::transport` API**: Write helper node that uses Gazebo Transport to create world joints
3. **Nested model**: Delete block, re-spawn inside robot model with fixed joint

### Launch

```bash
pkill -9 -f "gz sim|rviz2|move_group|robot_state|ros_gz|block_|pick_place|table_|ros2 launch"
sleep 4; ros2 daemon stop; sleep 1; ros2 daemon start; sleep 2
. /opt/ros/humble/setup.bash && . /home/csj/ros2_ws/install/setup.bash
ros2 launch block_stacking_agent sim_agent.launch.py
```

### Test

```bash
ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once
```

### Key Files

- `launch/sim_agent.launch.py`
- `scripts/pick_place_server.py`
- `scripts/block_visual_marker.py`
- `scripts/block_tf_bridge.py`
- `config/fr5_gazebo.urdf.xacro`
- `config/block_stacking_world.sdf`
