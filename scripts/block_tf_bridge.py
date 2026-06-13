#!/usr/bin/env python3
"""
Bridge Gazebo Pose_V TF frames → /tf with correct parent frame hierarchy.

Publishes:
  world → fairino5_v6_robot → base_link   (connects robot to world)
  world → block_*                         (blocks in world frame)

This lets RViz (fixed frame: base_link) see blocks via base_link → world → block_*
"""
import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage
from geometry_msgs.msg import TransformStamped


class BlockTFBridge(Node):
    def __init__(self):
        super().__init__("block_tf_bridge")

        self.sub = self.create_subscription(
            TFMessage,
            "/world/block_stacking_world/dynamic_pose/info",
            self.pose_callback,
            10,
        )
        self.tf_pub = self.create_publisher(TFMessage, "/tf", 10)
        self.get_logger().info("Block TF Bridge started...")

    def pose_callback(self, msg: TFMessage):
        out = TFMessage()
        robot_model_pose = None
        base_link_pose = None

        for transform in msg.transforms:
            name = transform.child_frame_id

            # --- Robot model: world → fairino5_v6_robot ---
            if name == "fairino5_v6_robot":
                robot_model_pose = transform
                t = TransformStamped()
                t.header.stamp = self.get_clock().now().to_msg()
                t.header.frame_id = "world"
                t.child_frame_id = name
                t.transform = transform.transform
                out.transforms.append(t)

            # --- base_link (identity relative to model root) ---
            elif name == "base_link":
                base_link_pose = transform

            # --- Block model frames: world → block_* ---
            elif name.startswith("block_") and not name.endswith("_link"):
                transform.header.frame_id = "world"
                out.transforms.append(transform)

        # --- Connect robot chain: fairino5_v6_robot → base_link ---
        if base_link_pose is not None:
            t = TransformStamped()
            t.header.stamp = self.get_clock().now().to_msg()
            t.header.frame_id = "fairino5_v6_robot"
            t.child_frame_id = "base_link"
            t.transform = base_link_pose.transform
            out.transforms.append(t)

        if out.transforms:
            self.tf_pub.publish(out)


def main():
    rclpy.init()
    node = BlockTFBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
