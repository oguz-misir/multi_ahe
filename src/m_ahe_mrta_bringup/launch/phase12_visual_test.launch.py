"""
Phase 12 — Visual Test Launch File

Includes robots_and_nav2_gui (Gazebo GUI + Nav2 + Robot Interfaces + RViz2)
and adds: EcosystemManager + ExperimentRunner + TaskVisualizer.

Usage:
  ros2 launch m_ahe_mrta_bringup phase12_visual_test.launch.py
  ros2 launch m_ahe_mrta_bringup phase12_visual_test.launch.py strategy:=static_weighted
  ros2 launch m_ahe_mrta_bringup phase12_visual_test.launch.py task_count:=3

Output: ~/multi_ahe/results/raw/gazebo_test/
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

_DEFAULT_RESULTS = os.path.expanduser('~/multi_ahe/results/raw/gazebo_test')


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('m_ahe_mrta_bringup')

    args = [
        DeclareLaunchArgument('strategy',      default_value='full_ahe_mrta'),
        DeclareLaunchArgument('scenario',      default_value='dynamic_task_arrival'),
        DeclareLaunchArgument('seed',          default_value='1'),
        DeclareLaunchArgument('task_count',    default_value='5',
                              description='Number of tasks (5 for short test)'),
        DeclareLaunchArgument('startup_delay', default_value='45.0'),
        DeclareLaunchArgument('results_dir',   default_value=_DEFAULT_RESULTS),
    ]

    # Gazebo GUI + Nav2 + Robot Interfaces + RViz2 (all-in-one)
    robots_nav2_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'robots_and_nav2_gui.launch.py')
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
            'robot_count': 3,
            'update_period_sec': 2.0,
            'results_dir': LaunchConfiguration('results_dir'),
        }],
    )

    # Experiment Runner
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
            'robot_count':  3,
            'task_count':   LaunchConfiguration('task_count'),
            'results_base': LaunchConfiguration('results_dir'),
            'gazebo_startup_delay_sec': LaunchConfiguration('startup_delay'),
        }],
    )

    # Task Visualizer — publishes /visualization/tasks MarkerArray
    task_visualizer = Node(
        package='m_ahe_task_manager',
        executable='task_visualizer_node',
        name='task_visualizer_node',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription(
        args + [robots_nav2_gui, ecosystem_manager, experiment_runner, task_visualizer]
    )
