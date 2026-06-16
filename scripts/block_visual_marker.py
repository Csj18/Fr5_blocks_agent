#!/usr/bin/env python3
"""
Colored cube markers for RViz.

Attached blocks (from /pick_place_server ROS param) use hand_base_link frame
→ they follow the gripper. Detached blocks use world frame from Gazebo poses.
"""
import rclpy
from rclpy.node import Node
from rcl_interfaces.srv import GetParameters
from tf2_msgs.msg import TFMessage
from visualization_msgs.msg import Marker, MarkerArray

GRASP_OFFSET_Z = -0.08
COLORS = {
    "block_red":   (0.9, 0.15, 0.15),
    "block_green": (0.15, 0.8, 0.15),
    "block_blue":  (0.15, 0.15, 0.9),
}
BLOCK_SIZE = 0.03


class BlockVisualMarker(Node):
    def __init__(self):
        super().__init__("block_visual_marker")

        self.gz_sub = self.create_subscription(
            TFMessage, "/world/block_stacking_world/dynamic_pose/info",
            self.gz_callback, 10)
        self.marker_pub = self.create_publisher(MarkerArray, "/block_markers", 10)

        self.gz_poses = {}
        self.have_gz = False

        # Track which blocks are attached (synced from pick_place_server)
        self.attached: set = set()

        # Service client to fetch attached_blocks parameter from pick_place_server
        self._param_cli = self.create_client(
            GetParameters, '/pick_place_server/get_parameters')
        self._pending_req = False  # Avoid overlapping requests

        # Poll for attachment state every 0.5s (service-based, bypasses DDS)
        self.create_timer(0.5, self.check_attached)

        # Publish markers at 10Hz
        self.timer = self.create_timer(0.1, self.publish_markers)
        self.get_logger().info("Block Visual Marker started (param-based)")

    def check_attached(self):
        """Fetch attached_blocks from pick_place_server via parameter service.

        Uses service call (not DDS topic) to avoid SHM transport issues.
        Called at 2Hz by timer.
        """
        if self._pending_req or not self._param_cli.service_is_ready():
            return
        self._pending_req = True
        req = GetParameters.Request()
        req.names = ['attached_blocks']
        future = self._param_cli.call_async(req)
        future.add_done_callback(self._on_param_response)

    def _on_param_response(self, future):
        """Callback for parameter service response."""
        self._pending_req = False
        try:
            result = future.result()
            if result.values:
                val = result.values[0].string_array_value
                new_attached = set(val)
                if new_attached != self.attached:
                    self.attached = new_attached
                    self.get_logger().info(
                        f"Attached blocks: {sorted(self.attached)}")
        except Exception as e:
            self.get_logger().warn(f"Param fetch failed: {e}")

    def gz_callback(self, msg: TFMessage):
        for t in msg.transforms:
            name = t.child_frame_id
            if not name.startswith("block_") or name.endswith("_link"):
                continue
            self.gz_poses[name] = (
                t.transform.translation.x, t.transform.translation.y,
                t.transform.translation.z,
                t.transform.rotation.x, t.transform.rotation.y,
                t.transform.rotation.z, t.transform.rotation.w)
            self.have_gz = True

    def publish_markers(self):
        markers = MarkerArray()
        mid = 0

        for name in ["block_red", "block_green", "block_blue"]:
            m = Marker()
            m.ns = "blocks"
            m.id = mid
            m.type = Marker.CUBE
            m.action = Marker.ADD
            m.scale.x = m.scale.y = m.scale.z = BLOCK_SIZE
            r, g, b = COLORS.get(name, (0.5, 0.5, 0.5))
            m.color.r = r; m.color.g = g; m.color.b = b; m.color.a = 1.0

            if name in self.attached:
                # Attached → hand_base_link frame, below gripper
                m.header.frame_id = "hand_base_link"
                m.pose.position.z = GRASP_OFFSET_Z
                m.pose.orientation.w = 1.0
            elif name in self.gz_poses:
                p = self.gz_poses[name]
                m.header.frame_id = "world"
                m.pose.position.x = p[0]
                m.pose.position.y = p[1]
                m.pose.position.z = p[2]
                m.pose.orientation.x = p[3]
                m.pose.orientation.y = p[4]
                m.pose.orientation.z = p[5]
                m.pose.orientation.w = p[6]
            else:
                mid += 1
                continue

            m.header.stamp = self.get_clock().now().to_msg()
            markers.markers.append(m)
            mid += 1

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
