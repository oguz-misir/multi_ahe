"""
Phase 9 GUI launch — Comparative experiment runner with Gazebo GUI + RViz2.

Identical to phase9_experiments.launch.py but uses robots_and_nav2_gui.launch.py
as the simulation base, which opens:
  - Gazebo Harmonic with GUI window
  - RViz2 with 3-robot view (map, laser scan, planned path, AMCL pose)

Launch arguments
----------------
strategy    : allocator (default: full_ahe_mrta)
              choices: greedy_nearest | deadline_aware | auction_based | static_weighted |
                       big_mrta | rostam_ea | consensus_dbta | full_ahe_mrta |
                       ahe_no_dominance | ahe_no_cooperation_suppression |
                       ahe_no_event_replanning | ahe_fixed_context
scenario    : experiment scenario (default: dynamic_task_arrival)
              choices: dynamic_task_arrival | deadline_pressure | robot_failure | mixed_stress
seed        : RNG seed (default: 42)
robot_count : number of robots (default: 3)
task_count  : total tasks (default: 15)
results_dir : base directory for CSV output (default: ~/multi_ahe/results/raw/phase9)

Usage
-----
  ros2 launch m_ahe_mrta_bringup phase9_experiments_gui.launch.py \\
      strategy:=full_ahe_mrta scenario:=robot_failure seed:=1
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

_DEFAULT_RESULTS = os.path.expanduser('~/multi_ahe/results/raw/phase9')


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('m_ahe_mrta_bringup')

    args = [
        DeclareLaunchArgument('strategy',    default_value='full_ahe_mrta'),
        DeclareLaunchArgument('scenario',    default_value='dynamic_task_arrival'),
        DeclareLaunchArgument('seed',        default_value='42'),
        DeclareLaunchArgument('robot_count', default_value='3'),
        DeclareLaunchArgument('task_count',  default_value='15'),
        DeclareLaunchArgument('results_dir', default_value=_DEFAULT_RESULTS),
    ]

    sw_render = [
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1'),
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    # Simulation: Gazebo GUI + RViz2 + Nav2 + Robot Interfaces
    robots_nav2_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'robots_and_nav2_gui.launch.py')
        ),
    )

    # Ecosystem Manager — computes D(t), W(t), publishes /ecosystem/debug_state
    ecosystem_manager = Node(
        package='m_ahe_ecosystem_manager',
        executable='ecosystem_manager_node',
        name='ecosystem_manager_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_count': LaunchConfiguration('robot_count'),
            'update_period_sec': 2.0,
            'results_dir': LaunchConfiguration('results_dir'),
        }],
    )

    # Experiment Runner — task generation + allocation + CSV logging
    experiment_runner = Node(
        package='m_ahe_task_allocator',
        executable='experiment_runner_node',
        name='experiment_runner_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'strategy':     LaunchConfiguration('strategy'),
            'scenario':     LaunchConfiguration('scenario'),
            'seed':         LaunchConfiguration('seed'),
            'robot_count':  LaunchConfiguration('robot_count'),
            'task_count':   LaunchConfiguration('task_count'),
            'results_base': LaunchConfiguration('results_dir'),
        }],
    )

    return LaunchDescription(
        args + sw_render + [robots_nav2_gui, ecosystem_manager, experiment_runner]
    )
