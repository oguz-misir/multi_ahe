"""
Phase 7 launch — Gazebo + Nav2 + Task Manager + Robot Interfaces + Baseline Allocator.

Adds baseline_allocator_node on top of Phase 6.
The allocator subscribes to /tasks/global_pool and /robot_i/status_summary,
then publishes /robot_i/optimized_task_queue once it has tasks to assign.

Validation:
  ros2 topic echo --no-daemon /robot_1/optimized_task_queue \\
    m_ahe_mrta_msgs/msg/OptimizedTaskQueue

  cat ~/multi_ahe/results/raw/phase7_baseline/method_runtime.csv
  cat ~/multi_ahe/results/raw/phase7_baseline/allocation_events.csv
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

ROBOTS = ['robot_1', 'robot_2', 'robot_3']
RESULTS_DIR = os.path.expanduser('~/multi_ahe/results/raw/phase7_baseline')


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('m_ahe_mrta_bringup')

    sw_render = [
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1'),
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    # Phase 6 system (Gazebo + Nav2 + Task Manager + Robot Interfaces)
    phase6 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'phase6_task_system.launch.py')
        ),
    )

    # Baseline allocator
    allocator = Node(
        package='m_ahe_task_allocator',
        executable='baseline_allocator_node',
        name='baseline_allocator_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_count': len(ROBOTS),
            'alloc_period_sec': 5.0,
            'results_dir': RESULTS_DIR,
        }],
    )

    return LaunchDescription(sw_render + [phase6, allocator])
