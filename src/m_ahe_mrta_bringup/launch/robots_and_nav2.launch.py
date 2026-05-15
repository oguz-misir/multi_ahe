"""
robots_and_nav2 — Gazebo + Nav2 + Robot Interfaces (no task manager, no allocator).

Used as the base for Phase 9 experiment runs: experiment_runner_node takes the role of
both task manager and allocator, so this launch file provides only the simulation layer.

Nodes started:
  1. multi_robot_nav2.launch.py  (Gazebo Harmonic headless + Nav2 for robot_1/2/3)
  2. robot_interface_node x3     (Nav2 action client, status publisher, feedback publisher)

The robot_count parameter passed here must match the robot_count in experiment_runner_node.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

ROBOTS = ['robot_1', 'robot_2', 'robot_3']


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('m_ahe_mrta_bringup')

    sw_render = [
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1'),
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    # Gazebo Harmonic headless + Nav2 lifecycle stacks for all robots
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'multi_robot_nav2.launch.py')
        ),
    )

    # One robot_interface_node per robot — listens to /robot_N/optimized_task_queue
    # and drives Nav2 NavigateToPose; publishes status_summary + task_feedback.
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

    return LaunchDescription(sw_render + [nav2_launch] + robot_interfaces)
