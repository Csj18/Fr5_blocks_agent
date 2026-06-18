#!/usr/bin/env python3
"""
Pick & Place Server for Fairino FR5.

Commands via /pick_place (std_msgs/String):
  "pick block_red"     — plan arm motion → execute trajectory → attach block
  "place block_red"    — detach from gripper
  "list"               — show currently attached blocks

Mechanism:
  - MoveIt /compute_ik → joint positions for block location
  - JointTrajectory → /fairino5_controller/joint_trajectory → Gazebo arm motion
  - Gazebo fixed joint (ign service) → block physically follows gripper
    → Gazebo pose bridge → world→block TF updates → RViz shows at gripper
  - MoveIt AttachedCollisionObject → planning scene knows block is on gripper

Usage:
  ros2 topic pub /pick_place std_msgs/String "data: \"pick block_red\"" --once
"""
import os
import subprocess
import tempfile
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String
from sensor_msgs.msg import JointState
from geometry_msgs.msg import Pose
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from moveit_msgs.srv import GetPositionIK
from moveit_msgs.msg import CollisionObject, AttachedCollisionObject
from shape_msgs.msg import SolidPrimitive

WORLD = "block_stacking_world"

# Block positions on table (table top at z=0.05, block half-size=0.015 → center z=0.065)
BLOCKS = {
    "block_red":   {"size": 0.03, "x": 0.40, "y": -0.10, "z": 0.065},
    "block_green": {"size": 0.03, "x": 0.50, "y": 0.00, "z": 0.065},
    "block_blue":  {"size": 0.03, "x": 0.60, "y": 0.10, "z": 0.065},
}

GRASP_OFFSET_Z = -0.08
JOINT_NAMES = ["j1", "j2", "j3", "j4", "j5", "j6"]


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
    """Create fixed joint in Gazebo via protobuf request written to temp file.

    Uses bash to read the file into --req, avoiding all shell/protobuf escaping issues.
    """
    sdf = (f'<sdf version="1.6">'
           f'<joint name="{joint_name}" type="fixed">'
           f'<parent>{parent}</parent><child>{child}</child>'
           f'</joint></sdf>')
    # Properly escape for protobuf text format: backslash-quote inside string
    escaped = sdf.replace('\\', '\\\\').replace('"', '\\"')
    req_content = f'sdf: "{escaped}"'
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(req_content)
            req_path = f.name
        # Use bash to read file content and pass as --req argument
        # This avoids all shell-escaping issues because bash reads file directly
        cmd = (
            f'REQ=$(cat {req_path}); '
            f'ign service -s /world/{WORLD}/create '
            f'--reqtype ignition.msgs.EntityFactory '
            f'--reptype ignition.msgs.Boolean '
            f'--req "$REQ" --timeout 5000'
        )
        r = subprocess.run(["bash", "-c", cmd],
                           capture_output=True, text=True, timeout=10)
        os.unlink(req_path)
        ok = "data: true" in r.stdout
        if not ok:
            import sys
            print(f"[gz_create_joint] stdout: {r.stdout.strip()}", file=sys.stderr)
            print(f"[gz_create_joint] stderr: {r.stderr.strip()}", file=sys.stderr)
        return ok
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

        # ── Arm motion interfaces ──────────────────────────────────
        # IK service client (MoveIt move_group provides /compute_ik)
        self.ik_cli = self.create_client(GetPositionIK, "/compute_ik")

        # Direct joint trajectory publisher → Gazebo controller
        self.traj_pub = self.create_publisher(
            JointTrajectory, "/fairino5_controller/joint_trajectory", 10)

        # Current joint state (for IK seeding)
        self.joint_state_sub = self.create_subscription(
            JointState, "/joint_states", self.js_callback, 10)
        self.current_positions = {n: 0.0 for n in JOINT_NAMES}

        # ROS parameter: list of currently attached blocks
        # Other nodes (block_visual_marker) read this to know what's attached.
        # Declare with non-empty default so ROS 2 infers string_array type
        # (empty list [] would be mis-inferred as byte_array in Humble).
        self.declare_parameter("attached_blocks", [""])
        self._update_param()

        # Timer: refresh MoveIt attachments + update parameter
        self.timer = self.create_timer(0.5, self._refresh_attachments)

        self._publish_initial_scene()
        self.get_logger().info("PickPlace Server ready (motion enabled)")

    def js_callback(self, msg: JointState):
        """Track current joint positions for IK seeding."""
        for name, pos in zip(msg.name, msg.position):
            if name in self.current_positions:
                self.current_positions[name] = pos

    # ── IK & Motion ───────────────────────────────────────────────

    def _ik_sync(self, x, y, z):
        """Compute IK for hand_base_link (gripper) at target position.

        Called from background thread — uses call_async + spin_until_future_complete.
        Returns list of 6 joint positions, or None on failure.
        """
        req = GetPositionIK.Request()
        ik = req.ik_request
        ik.group_name = "fairino5_v6_group"
        ik.ik_link_name = "wrist3_link"
        ik.pose_stamped.header.frame_id = "world"
        ik.pose_stamped.pose.position.x = x
        ik.pose_stamped.pose.position.y = y
        ik.pose_stamped.pose.position.z = z
        # Orientation: gripper pointing down (approach from above)
        # hand_base_link Z points down → tool-down orientation
        ik.pose_stamped.pose.orientation.x = 0.0
        ik.pose_stamped.pose.orientation.y = 0.707
        ik.pose_stamped.pose.orientation.z = 0.0
        ik.pose_stamped.pose.orientation.w = 0.707
        ik.timeout.sec = 3

        # Seed with current joint positions
        seed = JointState()
        seed.name = JOINT_NAMES
        seed.position = [self.current_positions.get(n, 0.0) for n in JOINT_NAMES]
        ik.robot_state.joint_state = seed

        future = self.ik_cli.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        result = future.result()
        if result is not None and result.error_code.val == 1:  # SUCCESS
            positions = list(result.solution.joint_state.position)
            self.get_logger().info(
                f"  IK solved: {[f'{p:.3f}' for p in positions[:6]]}")
            return positions
        self.get_logger().warn(
            f"  IK failed (error_code={result.error_code.val if result else 'None'})")
        return None

    def _send_trajectory(self, positions, duration=3.0):
        """Publish a single-point joint trajectory to the arm controller."""
        traj = JointTrajectory()
        traj.joint_names = JOINT_NAMES
        point = JointTrajectoryPoint()
        point.positions = positions
        dur_sec = int(duration)
        dur_nsec = int((duration - dur_sec) * 1e9)
        point.time_from_start.sec = dur_sec
        point.time_from_start.nanosec = dur_nsec
        traj.points = [point]
        self.traj_pub.publish(traj)
        self.get_logger().info(f"  Trajectory sent ({duration:.1f}s)")

    def _execute_pick_motion(self, block):
        """Background thread: plan arm motion, execute, then attach block."""
        info = BLOCKS[block]

        # Wait for IK service
        if not self.ik_cli.wait_for_service(timeout_sec=10.0):
            self.get_logger().error("IK service /compute_ik not available")
            return

        # ── 1. Pre-grasp approach (above block) ──
        # hand_base_link target: block_z + |GRASP_OFFSET_Z| = 0.065 + 0.08 = 0.145
        # wrist3_link is ~0.12m above hand_base_link: 0.145 + 0.12 ≈ 0.265
        grasp_z = info["z"] - GRASP_OFFSET_Z + 0.12  # wrist3 at block_z + 0.08 + 0.12
        approach_z = grasp_z + 0.12  # 12cm above grasp
        self.get_logger().info(
            f"  Planning to pre-grasp: ({info['x']:.2f}, {info['y']:.2f}, {approach_z:.2f})")
        pre_joints = self._ik_sync(info["x"], info["y"], approach_z)
        if pre_joints is None:
            self.get_logger().error(f"Pre-grasp IK failed for {block}")
            return

        self.get_logger().info(f"  Moving to pre-grasp…")
        self._send_trajectory(pre_joints, 3.0)
        time.sleep(3.5)

        # ── 2. Approach to grasp pose ──
        self.get_logger().info(
            f"  Planning grasp: ({info['x']:.2f}, {info['y']:.2f}, {grasp_z:.2f})")
        grasp_joints = self._ik_sync(info["x"], info["y"], grasp_z)
        if grasp_joints is not None:
            self.get_logger().info(f"  Moving to grasp…")
            self._send_trajectory(grasp_joints, 2.0)
            time.sleep(2.5)

        # ── 3. Attach block (Gazebo joint + MoveIt) ──
        now = self.get_clock().now().to_msg()

        # Remove block from world collision
        obj = CollisionObject()
        obj.id = block
        obj.operation = CollisionObject.REMOVE
        obj.header.stamp = now
        self.collision_pub.publish(obj)

        # Attach to hand_base_link in MoveIt
        att = make_attached(block, "hand_base_link", BLOCKS[block]["size"])
        att.object.header.stamp = now
        self.attached_pub.publish(att)

        self.attached.add(block)
        self._update_param()

        # Gazebo fixed joint (physics attachment)
        ok = gz_create_joint(
            f"pick_{block}",
            "fairino5_v6_robot::hand_base_link",
            f"{block}::block_link")
        self.get_logger().info(
            f"  Gazebo joint: {'✓' if ok else '✗ (ign not avail)'}")

        # ── 4. Retreat to pre-grasp height ──
        retreat_joints = self._ik_sync(info["x"], info["y"], approach_z)
        if retreat_joints is not None:
            self.get_logger().info(f"  Retreating…")
            self._send_trajectory(retreat_joints, 2.0)

        self.get_logger().info(f"  ✅ {block} picked → hand_base_link")

    # ── Command handlers ──────────────────────────────────────────

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
            a = ", ".join(sorted(self.attached)) if self.attached else "none"
            self.get_logger().info(f"  attached: {a}")

    def _pick(self, block):
        if block not in BLOCKS:
            return self.get_logger().error(f"Unknown: {block}")
        if block in self.attached:
            return self.get_logger().warn(f"{block} already attached")

        # Run entire pick motion in background thread to avoid blocking executor
        threading.Thread(
            target=self._execute_pick_motion, args=(block,), daemon=True).start()

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
        pose.position.z = 0.065
        pose.orientation.w = 1.0
        obj = make_collision_object(block, pose, BLOCKS[block]["size"])
        obj.header.stamp = now
        self.collision_pub.publish(obj)

        self.attached.discard(block)
        self._update_param()

        # 3. Remove Gazebo joint (in background)
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
