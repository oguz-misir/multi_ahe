#!/usr/bin/env python3
"""Republishes nav_msgs/Odometry pose as a TF broadcast at 20 Hz.

The Gazebo bridge publishes robot_N/tf, but Gazebo stops publishing TF
for stationary robots, causing the TF cache to expire after 10 s.
The Odometry message is always published at a steady rate even when
stationary, so this node keeps the odom→base_link TF alive.

Design: subscriber callback only stores the latest message (trivial, no
TF publish); a 20 Hz timer does the actual TF broadcast.  This prevents
the Python callback overhead from becoming a CPU sink when Gazebo sends
odom at 100+ Hz.

Startup race fix: before the first odom message arrives, an identity
transform is broadcast at clock-now so Nav2's lifecycle_manager can
activate controller_server without a TF-tree-missing abort.

Deployed per robot in its namespace so the relative 'odom' topic
resolves to /robot_N/odom.
"""
from typing import Optional

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
import tf2_ros


class OdomToTFNode(Node):
    def __init__(self):
        super().__init__('odom_to_tf')
        self._broadcaster = tf2_ros.TransformBroadcaster(self)
        self._latest: Optional[Odometry] = None

        # Derive frame IDs from namespace (e.g. /robot_3 → robot_3/odom, robot_3/base_link)
        ns = self.get_namespace().lstrip('/')
        self._odom_frame = f'{ns}/odom'
        self._base_frame = f'{ns}/base_link'

        # depth=1: keep only the latest message; default (RELIABLE) QoS is
        # compatible with whatever the Gazebo odom bridge publishes.
        self.create_subscription(Odometry, 'odom', self._store, 1)
        self.create_timer(0.05, self._publish)  # 20 Hz

    def _store(self, msg: Odometry) -> None:
        self._latest = msg

    def _publish(self) -> None:
        t = TransformStamped()
        # Always use current clock so the transform is never stale in TF buffer.
        t.header.stamp = self.get_clock().now().to_msg()
        msg = self._latest
        if msg is None:
            # Seed the TF tree with identity before first odom arrives so
            # Nav2's lifecycle_manager can find odom→base_link on activation.
            t.header.frame_id = self._odom_frame
            t.child_frame_id = self._base_frame
            t.transform.rotation.w = 1.0
        else:
            t.header.frame_id = msg.header.frame_id or self._odom_frame
            t.child_frame_id = msg.child_frame_id or self._base_frame
            t.transform.translation.x = msg.pose.pose.position.x
            t.transform.translation.y = msg.pose.pose.position.y
            t.transform.translation.z = msg.pose.pose.position.z
            t.transform.rotation = msg.pose.pose.orientation
        self._broadcaster.sendTransform(t)


def main():
    rclpy.init()
    node = OdomToTFNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
