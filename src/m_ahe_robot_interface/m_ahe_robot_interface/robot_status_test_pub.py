"""
Phase 2 test node — publishes RobotStatusSummary and LocalExecutionFeedback,
subscribes to OptimizedTaskQueue.

Topics:
  pub  /robot_1/status_summary          (RobotStatusSummary)
  pub  /robot_1/local_execution_feedback (LocalExecutionFeedback)
  sub  /robot_1/optimized_task_queue    (OptimizedTaskQueue)

Validates that robot-side message types are importable in rclpy
and that the topics appear in 'ros2 topic list'.

State codes (for reference — Phase 6 will enforce these):
  availability_state: 0=available, 1=busy, 2=unavailable
  battery_state:      0=normal,    1=low,  2=critical
  navigation_state:   0=idle, 1=navigating, 2=stuck, 3=failed, 4=reached
  congestion_indicator: 0=none, 1=low, 2=medium, 3=high
  goal_reachability:    0=reachable, 1=uncertain, 2=unreachable
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped

from m_ahe_mrta_msgs.msg import (
    RobotStatusSummary,
    LocalExecutionFeedback,
    OptimizedTaskQueue,
)


class RobotStatusTestPub(Node):

    PUBLISH_HZ = 1.0

    def __init__(self) -> None:
        super().__init__('robot_status_test_pub')

        self.declare_parameter('robot_id', 'robot_1')
        self._robot_id: str = self.get_parameter('robot_id').get_parameter_value().string_value

        ns = f'/{self._robot_id}'

        self._status_pub = self.create_publisher(
            RobotStatusSummary, f'{ns}/status_summary', 10)
        self._feedback_pub = self.create_publisher(
            LocalExecutionFeedback, f'{ns}/local_execution_feedback', 10)
        self._queue_sub = self.create_subscription(
            OptimizedTaskQueue, f'{ns}/optimized_task_queue',
            self._on_task_queue, 10)

        self._timer = self.create_timer(1.0 / self.PUBLISH_HZ, self._publish)
        self.get_logger().info(
            f'robot_status_test_pub started for {self._robot_id}')

    def _publish(self) -> None:
        now = self.get_clock().now().to_msg()

        status = RobotStatusSummary()
        status.header.stamp = now
        status.header.frame_id = 'map'
        status.robot_id = self._robot_id
        status.current_pose = PoseStamped()
        status.current_pose.header.frame_id = 'map'
        status.current_pose.pose.position.x = 0.0
        status.current_pose.pose.position.y = 0.0
        status.current_pose.pose.orientation.w = 1.0
        status.current_task_id = ''
        status.availability_state = 0   # available
        status.battery_state = 0        # normal
        status.navigation_state = 0     # idle
        status.failure_flag = False
        status.task_completed = False
        status.completed_task_id = ''
        self._status_pub.publish(status)

        feedback = LocalExecutionFeedback()
        feedback.header.stamp = now
        feedback.header.frame_id = 'map'
        feedback.robot_id = self._robot_id
        feedback.current_task_id = ''
        feedback.task_progress = 0.0
        feedback.local_delay = 0.0
        feedback.congestion_indicator = 0   # none
        feedback.goal_reachability = 0      # reachable
        feedback.navigation_effort = 0.0
        feedback.temporary_failure = False
        feedback.request_replan = False
        self._feedback_pub.publish(feedback)

        self.get_logger().debug(
            f'{self._robot_id}: published status + feedback')

    def _on_task_queue(self, msg: OptimizedTaskQueue) -> None:
        self.get_logger().info(
            f'{self._robot_id}: received OptimizedTaskQueue v{msg.queue_version} '
            f'({len(msg.waypoints)} waypoints, mode={msg.execution_mode!r})')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RobotStatusTestPub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
