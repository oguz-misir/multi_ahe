"""
Phase 2 test node — publishes a dummy TaskPool to /tasks/global_pool.

Validates that m_ahe_mrta_msgs/msg/TaskPool is importable in rclpy
and that the topic appears in 'ros2 topic list'.
"""

import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Header

from m_ahe_mrta_msgs.msg import TaskPool, TaskInfo


class TaskPoolTestPub(Node):

    PUBLISH_HZ = 1.0

    def __init__(self) -> None:
        super().__init__('task_pool_test_pub')
        self._pub = self.create_publisher(TaskPool, '/tasks/global_pool', 10)
        self._version = 0
        self._timer = self.create_timer(1.0 / self.PUBLISH_HZ, self._publish)
        self.get_logger().info('task_pool_test_pub started — publishing to /tasks/global_pool')

    def _make_task_info(self, task_id: str, x: float, y: float,
                        priority: int, deadline: float) -> TaskInfo:
        msg = TaskInfo()
        msg.task_id = task_id
        msg.target_pose = PoseStamped()
        msg.target_pose.header.frame_id = 'map'
        msg.target_pose.pose.position.x = x
        msg.target_pose.pose.position.y = y
        msg.target_pose.pose.orientation.w = 1.0
        msg.priority_level = priority
        msg.service_time = 5.0
        msg.deadline = deadline
        msg.active = True
        msg.completed = False
        return msg

    def _publish(self) -> None:
        self._version += 1
        pool = TaskPool()
        pool.header.stamp = self.get_clock().now().to_msg()
        pool.header.frame_id = 'map'
        pool.pool_version = self._version
        pool.tasks = [
            self._make_task_info('task_001', 2.0, 1.5, 2, 120.0),
            self._make_task_info('task_002', -1.5, 3.0, 1, 180.0),
            self._make_task_info('task_003', 4.0, -2.0, 3, 90.0),
        ]
        self._pub.publish(pool)
        self.get_logger().debug(f'Published TaskPool v{self._version} ({len(pool.tasks)} tasks)')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TaskPoolTestPub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
