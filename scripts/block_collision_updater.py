#!/usr/bin/env python3
"""
Read block transforms from bridged Gazebo pose topic → publish CollisionObject
messages so MoveIt avoids blocks during planning.

Each block is a 0.03m cube. Poses come from Gazebo physics in real-time,
so blocks are avoided wherever they move (pushed, grabbed, dropped).
"""
import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose


class BlockCollisionUpdater(Node):
    def __init__(self):
        super().__init__("block_collision_updater")

        # Subscribe to the Gazebo-bridged pose topic
        self.sub = self.create_subscription(
            TFMessage,
            "/world/block_stacking_world/dynamic_pose/info",
            self.pose_callback,
            10,
        )

        # Publish collision objects for MoveIt planning scene
        self.collision_pub = self.create_publisher(
            CollisionObject, "/collision_object", 10
        )

        # Block cube size (matches block SDF: 0.03 x 0.03 x 0.03)
        self.block_size = 0.03

        self.get_logger().info("Block Collision Updater started — listening for blocks...")

    def pose_callback(self, msg: TFMessage):
        for transform in msg.transforms:
            name = transform.child_frame_id
            # Skip non-block frames and internal link frames (e.g., block_link)
            if not name.startswith("block_") or name.endswith("_link"):
                continue

            obj = CollisionObject()
            obj.id = name
            obj.header.frame_id = "world"
            obj.header.stamp = self.get_clock().now().to_msg()
            obj.operation = CollisionObject.ADD

            # Box primitive (0.03m cube)
            box = SolidPrimitive()
            box.type = SolidPrimitive.BOX
            box.dimensions = [self.block_size] * 3
            obj.primitives = [box]

            # Pose from Gazebo (world frame)
            pose = Pose()
            pose.position.x = transform.transform.translation.x
            pose.position.y = transform.transform.translation.y
            pose.position.z = transform.transform.translation.z
            pose.orientation = transform.transform.rotation
            obj.primitive_poses = [pose]

            self.collision_pub.publish(obj)


def main():
    rclpy.init()
    node = BlockCollisionUpdater()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
