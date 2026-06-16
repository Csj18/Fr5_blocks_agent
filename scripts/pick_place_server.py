#!/usr/bin/env python3
"""
Pick & Place Server for Fairino FR5.

Commands via /pick_place (std_msgs/String):
  "pick block_red"     — Gazebo fixed joint + MoveIt AttachedCollisionObject
  "place block_red"    — detach from gripper
  "list"               — show currently attached blocks

Mechanism:
  - Gazebo fixed joint (ign service) → block physically follows gripper
    → Gazebo pose bridge → world→block TF updates → RViz shows at gripper
  - MoveIt AttachedCollisionObject → planning scene knows block is on gripper

Usage:
  ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once
"""
import subprocess
import threading
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String
from geometry_msgs.msg import Pose
from moveit_msgs.msg import CollisionObject, AttachedCollisionObject
from shape_msgs.msg import SolidPrimitive

WORLD = "block_stacking_world"

BLOCKS = {
    "block_red":   {"size": 0.03, "x": 0.40, "y": -0.10, "z": 0.025},
    "block_green": {"size": 0.03, "x": 0.50, "y": 0.00, "z": 0.025},
    "block_blue":  {"size": 0.03, "x": 0.60, "y": 0.10, "z": 0.025},
}

GRASP_OFFSET_Z = -0.08


def make_collision_object(name, pose, size=0.03):
    obj = CollisionObject()
    obj.id = name
    obj.header.frame_id = "world"
    obj.operation = CollisionObject.ADD
    box = SolidPrimitive()
    box.type = SolidPrimitive.BOX
    box.dimensions = [size] * 3
    obj.primitives = [box]
    obj.primitive_poses = [pose]
    return obj


def make_attached(name, link, size=0.03):
    att = AttachedCollisionObject()
    att.link_name = link
    att.object.id = name
    att.object.header.frame_id = link
    att.object.operation = CollisionObject.ADD
    box = SolidPrimitive()
    box.type = SolidPrimitive.BOX
    box.dimensions = [size] * 3
    att.object.primitives = [box]
    p = Pose()
    p.position.z = GRASP_OFFSET_Z
    p.orientation.w = 1.0
    att.object.primitive_poses = [p]
    att.touch_links = ["hand_base_link", "finger_link1", "finger_link2"]
    return att


def gz_create_joint(joint_name, parent, child):
    """Create fixed joint in Gazebo. Returns True on success."""
    sdf = (f'<sdf version="1.6">'
           f'<joint name="{joint_name}" type="fixed">'
           f'<parent>{parent}</parent><child>{child}</child>'
           f'</joint></sdf>')
    try:
        r = subprocess.run(
            ["ign", "service", "-s", f"/world/{WORLD}/create",
             "--reqtype", "ignition.msgs.EntityFactory",
             "--reptype", "ignition.msgs.Boolean",
             "--req", f'sdf: "{sdf}"', "--timeout", "5000"],
            capture_output=True, text=True, timeout=5)
        return "data: true" in r.stdout
    except Exception:
        return False


def gz_remove_joint(joint_name):
    """Remove Gazebo joint."""
    try:
        r = subprocess.run(
            ["ign", "service", "-s", f"/world/{WORLD}/remove",
             "--reqtype", "ignition.msgs.Entity",
             "--reptype", "ignition.msgs.Boolean",
             "--req", f'name: "{joint_name}", type: JOINT',
             "--timeout", "5000"],
            capture_output=True, text=True, timeout=5)
        return "data: true" in r.stdout
    except Exception:
        return False


class PickPlaceServer(Node):
    def __init__(self):
        super().__init__("pick_place_server")
        self.cmd_sub = self.create_subscription(
            String, "/pick_place", self.cmd_callback, 10)
        self.collision_pub = self.create_publisher(
            CollisionObject, "/collision_object", 10)
        self.attached_pub = self.create_publisher(
            AttachedCollisionObject, "/attached_collision_object", 10)
        self.attached = set()

        # ROS parameter: list of currently attached blocks
        # Other nodes (block_visual_marker) read this to know what's attached.
        # Declare with non-empty default so ROS 2 infers string_array type
        # (empty list [] would be mis-inferred as byte_array in Humble).
        self.declare_parameter("attached_blocks", [""])
        self._update_param()

        # Timer: refresh MoveIt attachments + update parameter
        self.timer = self.create_timer(0.5, self._refresh_attachments)

        self._publish_initial_scene()
        self.get_logger().info("PickPlace Server ready")

    def _publish_initial_scene(self):
        for name, info in BLOCKS.items():
            pose = Pose()
            pose.position.x = info["x"]
            pose.position.y = info["y"]
            pose.position.z = info["z"]
            pose.orientation.w = 1.0
            obj = make_collision_object(name, pose, info["size"])
            obj.header.stamp = self.get_clock().now().to_msg()
            self.collision_pub.publish(obj)

    def _update_param(self):
        """Sync attached_blocks parameter for other nodes."""
        self.set_parameters([Parameter(
            "attached_blocks",
            Parameter.Type.STRING_ARRAY,
            sorted(self.attached))])

    def _refresh_attachments(self):
        """Re-publish attached objects so MoveIt doesn't time them out."""
        now = self.get_clock().now().to_msg()
        for name in self.attached:
            att = make_attached(name, "hand_base_link", BLOCKS[name]["size"])
            att.object.header.stamp = now
            self.attached_pub.publish(att)

    def cmd_callback(self, msg: String):
        cmd = msg.data.strip()
        self.get_logger().info(f"→ {cmd}")
        parts = cmd.split()
        if not parts:
            return
        action = parts[0]
        if action == "pick" and len(parts) >= 2:
            self._pick(parts[1])
        elif action == "place" and len(parts) >= 2:
            self._place(parts[1])
        elif action == "list":
            a = ', '.join(sorted(self.attached)) if self.attached else 'none'
            self.get_logger().info(f"  attached: {a}")

    def _pick(self, block):
        if block not in BLOCKS:
            return self.get_logger().error(f"Unknown: {block}")
        if block in self.attached:
            return self.get_logger().warn(f"{block} already attached")

        now = self.get_clock().now().to_msg()

        # 1. Remove from world → MoveIt planning scene
        obj = CollisionObject()
        obj.id = block
        obj.operation = CollisionObject.REMOVE
        obj.header.stamp = now
        self.collision_pub.publish(obj)

        # 2. Attach to hand_base_link → MoveIt planning scene (RViz shows it)
        att = make_attached(block, "hand_base_link", BLOCKS[block]["size"])
        att.object.header.stamp = now
        self.attached_pub.publish(att)

        self.attached.add(block)
        self._update_param()

        # 3. Gazebo joint in background (physics attachment)
        #    When created, Gazebo snaps block to gripper.
        #    Gazebo pose bridge → world→block TF updates → RViz block at gripper.
        def _do():
            ok = gz_create_joint(
                f"pick_{block}",
                "fairino5_v6_robot::hand_base_link",
                f"{block}::block_link")
            self.get_logger().info(
                f"  Gazebo joint: {'✓' if ok else '✗ (ign not avail)'}")
        threading.Thread(target=_do, daemon=True).start()

        self.get_logger().info(f"  ✅ {block} → hand_base_link")

    def _place(self, block):
        if block not in BLOCKS:
            return
        now = self.get_clock().now().to_msg()

        # 1. Remove MoveIt attachment
        att = AttachedCollisionObject()
        att.link_name = "hand_base_link"
        att.object.id = block
        att.object.operation = CollisionObject.REMOVE
        att.object.header.stamp = now
        self.attached_pub.publish(att)

        # 2. Add back as world collision object
        pose = Pose()
        pose.position.z = 0.025
        pose.orientation.w = 1.0
        obj = make_collision_object(block, pose, BLOCKS[block]["size"])
        obj.header.stamp = now
        self.collision_pub.publish(obj)

        self.attached.discard(block)
        self._update_param()

        # 3. Remove Gazebo joint
        def _do():
            ok = gz_remove_joint(f"pick_{block}")
            self.get_logger().info(
                f"  Gazebo joint: {'removed' if ok else 'not found'}")
        threading.Thread(target=_do, daemon=True).start()

        self.get_logger().info(f"  ✅ {block} placed")


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
