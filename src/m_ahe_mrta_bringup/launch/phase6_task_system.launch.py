"""
Phase 6 launch — Gazebo + 3-robot Nav2 stacks + Task Manager + Robot Interfaces.

Starts:
  1. multi_robot_nav2.launch.py  (Gazebo Harmonic headless + Nav2 for robot_1/2/3)
  2. task_manager_node           (publishes /tasks/global_pool)
  3. robot_interface_node x3     (one per robot, Nav2 action client)

Validation (in a separate terminal after lifecycle_managers activate):
  # Check task pool
  ros2 topic echo --no-daemon /tasks/global_pool m_ahe_mrta_msgs/msg/TaskPool

  # Check robot status
  ros2 topic echo --no-daemon /robot_1/status_summary m_ahe_mrta_msgs/msg/RobotStatusSummary

  # Manually send a task queue to robot_1 and watch it navigate
  ros2 topic pub --once /robot_1/optimized_task_queue \\
    m_ahe_mrta_msgs/msg/OptimizedTaskQueue \\
    "{robot_id: 'robot_1', queue_version: 1, waypoints: [{task_id: 'test_01', \\
      target_pose: {header: {frame_id: 'robot_1/map'}, \\
        pose: {position: {x: 2.0, y: 1.0, z: 0.0}, orientation: {w: 1.0}}}, \\
      priority_level: 2, service_time: 3.0}], execution_mode: 'sequential'}"
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

ROBOTS = ['robot_1', 'robot_2', 'robot_3']


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('m_ahe_mrta_bringup')

    sw_render = [
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    # Gazebo + 3-robot Nav2 stacks
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'multi_robot_nav2.launch.py')
        ),
    )

    # Task manager
    task_manager = Node(
        package='m_ahe_task_manager',
        executable='task_manager_node',
        name='task_manager_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_count': len(ROBOTS),
            'task_count': 15,
            'seed': 1,
        }],
    )

    # One robot_interface_node per robot
    robot_interfaces = [
        Node(
            package='m_ahe_robot_interface',
            executable='robot_interface_node',
            name=f'robot_interface_{robot_ns}',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'robot_id': robot_ns,
            }],
        )
        for robot_ns in ROBOTS
    ]

    return LaunchDescription(sw_render + [nav2_launch, task_manager] + robot_interfaces)
