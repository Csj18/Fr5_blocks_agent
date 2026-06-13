#!/usr/bin/env python3
"""
Publish colored cube markers for each block so RViz displays them as solid shapes.
Subscribes to the same bridged Gazebo pose topic as the other block nodes.
"""
import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage
from visualization_msgs.msg import Marker, MarkerArray


class BlockVisualMarker(Node):
    def __init__(self):
        super().__init__("block_visual_marker")

        self.sub = self.create_subscription(
            TFMessage,
            "/world/block_stacking_world/dynamic_pose/info",
            self.pose_callback,
            10,
        )

        self.marker_pub = self.create_publisher(MarkerArray, "/block_markers", 10)

        # Predefined block colors
        self.colors = {
            "block_red":   (0.9, 0.15, 0.15),
            "block_green": (0.15, 0.8, 0.15),
            "block_blue":  (0.15, 0.15, 0.9),
        }
        self.block_size = 0.10  # 10cm cube (temp for debug)

        self.get_logger().info("Block Visual Marker started — publishing cube markers...")

    def pose_callback(self, msg: TFMessage):
        markers = MarkerArray()
        for i, transform in enumerate(msg.transforms):
            name = transform.child_frame_id
            if not name.startswith("block_") or name.endswith("_link"):
                continue

            marker = Marker()
            marker.header.frame_id = "world"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "blocks"
            marker.id = i
            marker.type = Marker.CUBE
            marker.action = Marker.ADD

            # Pose from Gazebo
            marker.pose.position.x = transform.transform.translation.x
            marker.pose.position.y = transform.transform.translation.y
            marker.pose.position.z = transform.transform.translation.z
            marker.pose.orientation = transform.transform.rotation

            # Size (3cm cube)
            s = self.block_size
            marker.scale.x = s
            marker.scale.y = s
            marker.scale.z = s

            # Color (default gray if not in predefined list)
            r, g, b = self.colors.get(name, (0.5, 0.5, 0.5))
            marker.color.r = r
            marker.color.g = g
            marker.color.b = b
            marker.color.a = 1.0

            markers.markers.append(marker)

        if markers.markers:
            self.marker_pub.publish(markers)


def main():
    rclpy.init()
    node = BlockVisualMarker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
