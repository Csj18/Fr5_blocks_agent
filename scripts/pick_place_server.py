#!/usr/bin/env python3
"""
Pick & Place Server for Fairino FR5 — Gazebo detachable joint bridge.

Commands via /pick_place (std_msgs/String):
  "pick block_red"     — attach block to hand_base_link via Gazebo fixed joint
  "place block_red"    — detach block from hand_base_link
  "list"               — list currently attached blocks

The arm motion is done via MoveIt in RViz (Plan & Execute).
This server only creates/removes Gazebo joints to simulate grasping.

Usage:
  source ~/ros2_ws/install/setup.bash
  ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once
  ros2 topic pub /pick_place std_msgs/String "data: \"place block_red\"" --once
"""
import subprocess
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

WORLD = "block_stacking_world"


def gz_joint_create(joint_name: str, parent: str, child: str) -> bool:
    sdf = (
        f'<sdf version="1.6">'
        f'<joint name="{joint_name}" type="fixed">'
        f'<parent>{parent}</parent>'
        f'<child>{child}</child>'
        f'</joint></sdf>'
    )
    try:
        r = subprocess.run(
            ["ign", "service", "-s", f"/world/{WORLD}/create",
             "--reqtype", "ignition.msgs.EntityFactory",
             "--reptype", "ignition.msgs.Boolean",
             "--req", f'sdf: "{sdf}"', "--timeout", "5000"],
            capture_output=True, text=True, timeout=10)
        return "data: true" in r.stdout
    except subprocess.TimeoutExpired:
        return False


def gz_joint_remove(joint_name: str) -> bool:
    try:
        r = subprocess.run(
            ["ign", "service", "-s", f"/world/{WORLD}/remove",
             "--reqtype", "ignition.msgs.Entity",
             "--reptype", "ignition.msgs.Boolean",
             "--req", f'name: "{joint_name}", type: JOINT',
             "--timeout", "5000"],
            capture_output=True, text=True, timeout=10)
        return "data: true" in r.stdout
    except subprocess.TimeoutExpired:
        return False


class PickPlaceServer(Node):
    def __init__(self):
        super().__init__("pick_place_server")
        self.cmd_sub = self.create_subscription(
            String, "/pick_place", self.cmd_callback, 10)
        self.attached = set()

        self.get_logger().info("PickPlace Server ready.")
        self.get_logger().info("  pick block_red   → attach to gripper")
        self.get_logger().info("  place block_red  → detach from gripper")
        self.get_logger().info("  list             → show attached blocks")

    def cmd_callback(self, msg: String):
        cmd = msg.data.strip()
        self.get_logger().info(f"→ {cmd}")
        parts = cmd.split()

        if not parts:
            return

        action = parts[0]

        if action == "pick" and len(parts) >= 2:
            block = parts[1]
            if block in self.attached:
                self.get_logger().warn(f"{block} already attached")
                return
            joint = f"pick_{block}"
            parent = "fairino5_v6_robot::hand_base_link"
            child = f"{block}::block_link"
            if gz_joint_create(joint, parent, child):
                self.attached.add(block)
                self.get_logger().info(f"  ✅ {block} → attached to gripper")
            else:
                self.get_logger().error(f"  ❌ failed to attach {block}")

        elif action == "place" and len(parts) >= 2:
            block = parts[1]
            joint = f"pick_{block}"
            if gz_joint_remove(joint):
                self.attached.discard(block)
                self.get_logger().info(f"  ✅ {block} released")
            else:
                self.get_logger().warn(f"  ⚠️ joint {joint} not found (already released?)")

        elif action == "list":
            if self.attached:
                self.get_logger().info(f"  attached: {', '.join(sorted(self.attached))}")
            else:
                self.get_logger().info("  no blocks attached")

        else:
            self.get_logger().error(f"Unknown: {cmd}")
            self.get_logger().info("  Use: pick <name> | place <name> | list")


def main():
    rclpy.init()
    node = PickPlaceServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
