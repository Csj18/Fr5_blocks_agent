#!/usr/bin/env python3
"""
Publish a visual marker for the work table in RViz.
The table is defined in block_stacking_world.sdf but has no TF/Marker by default.
"""
import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker


class TableMarker(Node):
    def __init__(self):
        super().__init__("table_marker")
        self.pub = self.create_publisher(Marker, "/table_marker", 10)
        self.timer = self.create_timer(1.0, self.publish_table)
        self.get_logger().info("Table Marker started — table visible in RViz")

    def publish_table(self):
        m = Marker()
        m.header.frame_id = "world"
        m.header.stamp = self.get_clock().now().to_msg()
        m.ns = "scene"
        m.id = 0
        m.type = Marker.CUBE
        m.action = Marker.ADD

        # Table pose from block_stacking_world.sdf: <pose>0.5 0 0.025 0 0 0</pose>
        m.pose.position.x = 0.5
        m.pose.position.y = 0.0
        m.pose.position.z = 0.025
        m.pose.orientation.w = 1.0

        # Table size: 0.8 x 0.6 x 0.05
        m.scale.x = 0.8
        m.scale.y = 0.6
        m.scale.z = 0.05

        m.color.r = 0.5
        m.color.g = 0.35
        m.color.b = 0.2
        m.color.a = 0.8

        self.pub.publish(m)


def main():
    rclpy.init()
    node = TableMarker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
