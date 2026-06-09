#!/usr/bin/env python3
"""
tf_relay_node — Aggregates per-robot namespaced TF into global /tf and /tf_static.

Required for RViz: robot_state_publisher and odom_to_tf publish to /robot_N/tf[_static]
(remapped from /tf) so Nav2 nodes stay isolated per namespace.  RViz subscribes to
the global /tf and /tf_static.  This node bridges them.

Launch argument: robot_count (int, default 3)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from tf2_msgs.msg import TFMessage


class TfRelayNode(Node):
    def __init__(self):
        super().__init__('tf_relay_node')

        self.declare_parameter('robot_count', 3)
        n = self.get_parameter('robot_count').value

        qos_dyn = QoSProfile(depth=100)
        qos_static = QoSProfile(
            depth=100,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )

        self._pub_tf = self.create_publisher(TFMessage, '/tf', qos_dyn)
        self._pub_tf_static = self.create_publisher(TFMessage, '/tf_static', qos_static)

        for i in range(1, n + 1):
            ns = f'robot_{i}'
            self.create_subscription(
                TFMessage, f'/{ns}/tf',
                self._pub_tf.publish, qos_dyn)
            self.create_subscription(
                TFMessage, f'/{ns}/tf_static',
                self._pub_tf_static.publish, qos_static)

        self.get_logger().info(f'tf_relay: bridging {n} robot namespaces → global /tf')


def main():
    rclpy.init()
    node = TfRelayNode()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
