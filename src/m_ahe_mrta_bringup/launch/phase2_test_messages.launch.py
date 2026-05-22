"""
Phase 2 launch file — starts all message test nodes to validate
that custom message types are importable in rclpy and that all
expected topics appear in 'ros2 topic list'.

Nodes launched:
  task_pool_test_pub     → /tasks/global_pool            (TaskPool, 1 Hz)
  robot_status_test_pub  → /robot_1/status_summary        (RobotStatusSummary, 1 Hz)
                         → /robot_1/local_execution_feedback (LocalExecutionFeedback, 1 Hz)
                         ← /robot_1/optimized_task_queue  (subscriber)
  task_queue_test_pub    → /robot_1/optimized_task_queue  (OptimizedTaskQueue, 0.5 Hz)
  ecosystem_test_pub     → /ecosystem/debug_state          (EcosystemState, 1 Hz)
                         → /allocation/events              (AllocationEvent, on tick)

Validation commands (after launch):
  ros2 topic list
  ros2 topic echo /tasks/global_pool
  ros2 topic echo /robot_1/status_summary
  ros2 topic echo /robot_1/optimized_task_queue
  ros2 topic echo /ecosystem/debug_state
  ros2 topic echo /allocation/events
  ros2 topic echo /robot_1/local_execution_feedback
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    task_pool_pub = Node(
        package='m_ahe_task_manager',
        executable='task_pool_test_pub',
        name='task_pool_test_pub',
        output='screen',
    )

    robot_status_pub = Node(
        package='m_ahe_robot_interface',
        executable='robot_status_test_pub',
        name='robot_status_test_pub',
        output='screen',
        parameters=[{'robot_id': 'robot_1'}],
    )

    task_queue_pub = Node(
        package='m_ahe_task_allocator',
        executable='task_queue_test_pub',
        name='task_queue_test_pub',
        output='screen',
        parameters=[{'robot_id': 'robot_1'}],
    )

    ecosystem_pub = Node(
        package='m_ahe_ecosystem_manager',
        executable='ecosystem_test_pub',
        name='ecosystem_test_pub',
        output='screen',
    )

    return LaunchDescription([
        task_pool_pub,
        robot_status_pub,
        task_queue_pub,
        ecosystem_pub,
    ])
