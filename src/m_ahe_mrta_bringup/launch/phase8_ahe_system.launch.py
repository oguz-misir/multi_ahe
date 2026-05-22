"""
Phase 8 launch — Full AHE-MRTA system.

Adds EcosystemManager + AHE Allocator on top of Phase 6 (Gazebo + Nav2 + Task Manager
+ Robot Interfaces).

Node graph:
  TaskManager  →  /tasks/global_pool  →  EcosystemManager
                                       →  AHEAllocator

  RobotInterface_N  →  /robot_N/status_summary  →  EcosystemManager
                                                 →  AHEAllocator

  EcosystemManager  →  /ecosystem/debug_state  →  AHEAllocator (weights only)

  AHEAllocator  →  /robot_N/optimized_task_queue  →  RobotInterface_N

Robots NEVER receive ecosystem internal state (dominance, cooperation, suppression).

Validation:
  ros2 topic echo --no-daemon /ecosystem/debug_state m_ahe_mrta_msgs/msg/EcosystemState
  cat ~/multi_ahe/results/raw/phase8_ahe/ecosystem_metrics.csv
  cat ~/multi_ahe/results/raw/phase8_ahe/method_runtime.csv
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

ROBOTS = ['robot_1', 'robot_2', 'robot_3']
RESULTS_DIR_ECO = os.path.expanduser('~/multi_ahe/results/raw/phase8_ahe')
RESULTS_DIR_ALLOC = os.path.expanduser('~/multi_ahe/results/raw/phase8_ahe')


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('m_ahe_mrta_bringup')

    sw_render = [
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    # Phase 6 system (Gazebo + Nav2 + Task Manager + Robot Interfaces)
    phase6 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'phase6_task_system.launch.py')
        ),
    )

    # Ecosystem Manager
    ecosystem_manager = Node(
        package='m_ahe_ecosystem_manager',
        executable='ecosystem_manager_node',
        name='ecosystem_manager_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_count': len(ROBOTS),
            'update_period_sec': 2.0,
            'results_dir': RESULTS_DIR_ECO,
        }],
    )

    # AHE Allocator (reads /ecosystem/debug_state for dynamic weights)
    ahe_allocator = Node(
        package='m_ahe_task_allocator',
        executable='ahe_allocator_node',
        name='ahe_allocator_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_count': len(ROBOTS),
            'alloc_period_sec': 5.0,
            'results_dir': RESULTS_DIR_ALLOC,
        }],
    )

    return LaunchDescription(sw_render + [phase6, ecosystem_manager, ahe_allocator])
