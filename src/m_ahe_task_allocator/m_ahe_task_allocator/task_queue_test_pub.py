"""
Phase 2 test node — publishes a dummy OptimizedTaskQueue to /robot_1/optimized_task_queue.

This gives the RobotStatusTestPub subscriber something to receive,
completing the pub/sub round-trip for OptimizedTaskQueue.

In Phase 7+, this node is replaced by the real task allocator.
The OptimizedTaskQueue.replan_required flag and queue_version field
will be used for event-triggered replanning tracking (Phase 8).
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped

from m_ahe_mrta_msgs.msg import OptimizedTaskQueue, TaskWaypoint


class TaskQueueTestPub(Node):

    PUBLISH_HZ = 0.5   # slower: only needed to test the subscriber receives

    def __init__(self) -> None:
        super().__init__('task_queue_test_pub')

        self.declare_parameter('robot_id', 'robot_1')
        self._robot_id: str = self.get_parameter('robot_id').get_parameter_value().string_value

        ns = f'/{self._robot_id}'
        self._pub = self.create_publisher(
            OptimizedTaskQueue, f'{ns}/optimized_task_queue', 10)
        self._version = 0
        self._timer = self.create_timer(1.0 / self.PUBLISH_HZ, self._publish)
        self.get_logger().info(
            f'task_queue_test_pub started → {ns}/optimized_task_queue')

    def _make_waypoint(self, task_id: str, x: float, y: float,
                       priority: int, arrival: float) -> TaskWaypoint:
        wp = TaskWaypoint()
        wp.task_id = task_id
        wp.target_pose = PoseStamped()
        wp.target_pose.header.frame_id = 'map'
        wp.target_pose.pose.position.x = x
        wp.target_pose.pose.position.y = y
        wp.target_pose.pose.orientation.w = 1.0
        wp.priority_level = priority
        wp.expected_arrival_time = arrival
        wp.service_time = 5.0
        wp.local_cost = 0.0
        wp.is_critical = False
        wp.allow_skip = False
        return wp

    def _publish(self) -> None:
        self._version += 1
        msg = OptimizedTaskQueue()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.robot_id = self._robot_id
        msg.queue_version = self._version
        msg.execution_mode = 'sequential'
        msg.queue_cost = 12.5
        msg.replan_required = False
        msg.waypoints = [
            self._make_waypoint('task_001', 2.0, 1.5, 2, 30.0),
            self._make_waypoint('task_003', 4.0, -2.0, 3, 90.0),
        ]
        self._pub.publish(msg)
        self.get_logger().debug(
            f'Published OptimizedTaskQueue v{self._version} '
            f'({len(msg.waypoints)} waypoints) to {self._robot_id}')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TaskQueueTestPub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
