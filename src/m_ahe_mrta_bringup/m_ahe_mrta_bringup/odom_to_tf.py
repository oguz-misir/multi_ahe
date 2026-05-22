#!/usr/bin/env python3
"""Republishes nav_msgs/Odometry pose as a TF broadcast at 10 Hz.

The Gazebo bridge publishes robot_N/tf, but Gazebo stops publishing TF
for stationary robots, causing the TF cache to expire after 10 s.
The Odometry message is always published at a steady rate even when
stationary, so this node keeps the odom→base_link TF alive.

Design: subscriber callback only stores the latest message (trivial, no
TF publish); a 10 Hz timer does the actual TF broadcast.  This prevents
the Python callback overhead from becoming a CPU sink when Gazebo sends
odom at 100+ Hz.

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

        # depth=1: keep only the latest message; default (RELIABLE) QoS is
        # compatible with whatever the Gazebo odom bridge publishes.
        self.create_subscription(Odometry, 'odom', self._store, 1)
        self.create_timer(0.1, self._publish)  # 10 Hz

    def _store(self, msg: Odometry) -> None:
        self._latest = msg

    def _publish(self) -> None:
        msg = self._latest
        if msg is None:
            return
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = msg.header.frame_id
        t.child_frame_id = msg.child_frame_id
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
