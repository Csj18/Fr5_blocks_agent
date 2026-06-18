#!/usr/bin/env python3
"""
Fairino FR5 Block Stacking — Simulation Launch File
Gazebo (headless): physics + gz_ros2_control + blocks
MoveIt: planning, sends trajectories to Gazebo's controller_manager
RViz: visualization (robot + blocks via TF)
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node, SetParameter
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_project = "block_stacking_agent"
    pkg_moveit_config = "fairino5_v6_moveit2_config"

    project_share = FindPackageShare(pkg_project)
    moveit_config_share = FindPackageShare(pkg_moveit_config)

    use_gazebo = LaunchConfiguration("use_gazebo", default="true")
    use_rviz = LaunchConfiguration("use_rviz", default="true")
    world_file = LaunchConfiguration("world_file",
        default=PathJoinSubstitution([project_share, "config", "block_stacking_world.sdf"]))

    declare_use_gazebo = DeclareLaunchArgument("use_gazebo", default_value="true")
    declare_use_rviz = DeclareLaunchArgument("use_rviz", default_value="true")
    declare_world_file = DeclareLaunchArgument("world_file",
        default_value=PathJoinSubstitution([project_share, "config", "block_stacking_world.sdf"]))

    # ── Resolved xacro argument paths ─────────────────────────────
    initial_positions_path = PathJoinSubstitution([project_share, "config", "initial_positions.yaml"])
    controller_config_path = PathJoinSubstitution([project_share, "config", "ros2_controllers.yaml"])

    # ── Gazebo mesh resource path ──────────────────────────────────
    # Gazebo needs to resolve package://fairino_description and package://fr5_description
    gz_resource_path = "/home/csj/ros2_ws/install/fairino_description/share:" \
                       "/home/csj/ros2_ws/install/fr5_description/share"
    set_gz_resource = SetEnvironmentVariable("IGN_GAZEBO_RESOURCE_PATH", gz_resource_path)

    # ── URDF for Gazebo (with gz_ros2_control) ────────────────────
    gz_robot_desc = {
        "robot_description": Command([
            FindExecutable(name="xacro"), " ",
            PathJoinSubstitution([project_share, "config", "fr5_gazebo.urdf.xacro"]), " ",
            "initial_positions_file:=", initial_positions_path, " ",
            "controller_config_file:=", controller_config_path,
        ])
    }

    # ── Gazebo (delayed: wait for robot_state_publisher params) ──────
    gazebo_launch = TimerAction(
        period=2.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([
                    PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
                ]),
                launch_arguments={
                    "gz_args": [" -s -r ", world_file],
                    "on_exit_shutdown": "false",
                }.items(),
            )
        ],
    )

    spawn_robot = TimerAction(
        period=4.0,
        actions=[
            Node(
                package="ros_gz_sim", executable="create",
                arguments=["-name", "fairino5_v6_robot", "-topic", "robot_description",
                           "-x", "0.5", "-y", "0.0", "-z", "0.0",
                           "-R", "0.0", "-P", "0.0", "-Y", "0.0"],
                output="screen",
            )
        ],
    )

    # ── TF ─────────────────────────────────────────────────────────
    robot_state_pub = Node(
        package="robot_state_publisher", executable="robot_state_publisher",
        output="both", parameters=[gz_robot_desc],
    )

    # ── Controller spawners (into Gazebo's controller_manager) ────
    spawn_joint_state_broadcaster = TimerAction(
        period=7.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["joint_state_broadcaster"],
                output="screen",
            )
        ],
    )

    spawn_fairino5_controller = TimerAction(
        period=9.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["fairino5_controller"],
                output="screen",
            )
        ],
    )

    spawn_gripper_controller = TimerAction(
        period=10.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=["gripper_controller"],
                output="screen",
            )
        ],
    )

    # ── Blocks ─────────────────────────────────────────────────────
    # Table surface at z=0.01, block half-size=0.015 → block center z=0.025
    block_sdf_paths = {
        "block_red":   PathJoinSubstitution([project_share, "config", "block_red.sdf"]),
        "block_green": PathJoinSubstitution([project_share, "config", "block_green.sdf"]),
        "block_blue":  PathJoinSubstitution([project_share, "config", "block_blue.sdf"]),
    }

    spawn_block_red = TimerAction(
        period=5.0,
        actions=[
            Node(
                package="ros_gz_sim", executable="create",
                arguments=["-name", "block_red", "-file", block_sdf_paths["block_red"],
                           "-x", "0.40", "-y", "-0.10", "-z", "0.065"],
                output="screen",
            )
        ],
    )

    spawn_block_green = TimerAction(
        period=5.5,
        actions=[
            Node(
                package="ros_gz_sim", executable="create",
                arguments=["-name", "block_green", "-file", block_sdf_paths["block_green"],
                           "-x", "0.50", "-y", "0.00", "-z", "0.065"],
                output="screen",
            )
        ],
    )

    spawn_block_blue = TimerAction(
        period=6.0,
        actions=[
            Node(
                package="ros_gz_sim", executable="create",
                arguments=["-name", "block_blue", "-file", block_sdf_paths["block_blue"],
                           "-x", "0.60", "-y", "0.10", "-z", "0.065"],
                output="screen",
            )
        ],
    )

    # ── Gazebo → ROS clock bridge ──────────────────────────────────
    gz_clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/world/block_stacking_world/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock"],
        remappings=[("/world/block_stacking_world/clock", "/clock")],
        output="screen",
    )

    # ── Gazebo → ROS pose bridge ───────────────────────────────────
    gz_pose_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/world/block_stacking_world/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V"
        ],
        output="screen",
    )

    # ── Block TF publisher (filter block frames → /tf) ────────────
    block_tf_node = Node(
        package="block_stacking_agent",
        executable="block_tf_bridge.py",
        name="block_tf_bridge",
        output="screen",
    )

    # ── Block collision updater (block poses → MoveIt planning scene)
    block_collision_node = Node(
        package="block_stacking_agent",
        executable="block_collision_updater.py",
        name="block_collision_updater",
        output="screen",
    )

    # ── Pick/Place Server ──────────────────────────────────────────
    pick_place_node = Node(
        package="block_stacking_agent",
        executable="pick_place_server.py",
        name="pick_place_server",
        output="screen",
    )

    # ── Table visual marker (invisible in RViz otherwise)
    table_marker_node = Node(
        package="block_stacking_agent",
        executable="table_marker.py",
        name="table_marker",
        output="screen",
    )

    # ── Block visual markers (colored cubes in RViz)
    block_marker_node = Node(
        package="block_stacking_agent",
        executable="block_visual_marker.py",
        name="block_visual_marker",
        output="screen",
    )

    # ── MoveIt 2 ───────────────────────────────────────────────────
    move_group_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([moveit_config_share, "launch", "move_group.launch.py"])
        ]),
    )

    rviz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([moveit_config_share, "launch", "moveit_rviz.launch.py"])
        ]),
        condition=IfCondition(use_rviz),
    )

    use_sim_time = SetParameter(name="use_sim_time", value=True)

    return LaunchDescription([
        declare_use_gazebo, declare_use_rviz, declare_world_file,
        set_gz_resource, use_sim_time, robot_state_pub,
        gazebo_launch, spawn_robot,
        spawn_block_red, spawn_block_green, spawn_block_blue,
        gz_clock_bridge, gz_pose_bridge, block_tf_node, block_collision_node, block_marker_node,
        table_marker_node, pick_place_node,
        spawn_joint_state_broadcaster, spawn_fairino5_controller,
        # spawn_gripper_controller,  # disabled: position_controllers not available
        move_group_launch, rviz_launch,
    ])
