"""
Phase 9 Demo launch — Gazebo + Nav2 + RViz + Task Visualizer + Experiment Runner.

Opens RViz with 3-robot view, task markers, Nav2 paths, and laser scans.
Runs a single experiment to completion, then shuts down.

Usage:
  ros2 launch m_ahe_mrta_bringup phase9_demo.launch.py strategy:=full_ahe_mrta scenario:=robot_failure seed:=1
  ros2 launch m_ahe_mrta_bringup phase9_demo.launch.py strategy:=rostam_ea    scenario:=mixed_stress   seed:=2
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

_TB3_MODELS = '/opt/ros/jazzy/share/turtlebot3_gazebo/models'

_DEFAULT_RESULTS = os.path.expanduser('~/multi_ahe/results/raw/gazebo')


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('m_ahe_mrta_bringup')
    rviz_config = os.path.join(bringup, 'config', 'phase9_demo.rviz')

    args = [
        DeclareLaunchArgument('strategy',    default_value='full_ahe_mrta',
                              description='Allocator strategy'),
        DeclareLaunchArgument('scenario',    default_value='robot_failure',
                              description='Experiment scenario'),
        DeclareLaunchArgument('seed',        default_value='1',
                              description='Random seed'),
        DeclareLaunchArgument('robot_count', default_value='3'),
        DeclareLaunchArgument('task_count',  default_value='15'),
        DeclareLaunchArgument('results_dir', default_value=_DEFAULT_RESULTS),
        DeclareLaunchArgument('startup_delay', default_value='75.0',
                              description='Seconds to wait for Nav2 init before starting experiment'),
        DeclareLaunchArgument('gz_gui', default_value='true',
                              description='Show Gazebo GUI window (false for headless batch runs)'),
    ]

    # Intel iGPU — GTK snap pollution fix ensures RViz opens correctly.
    sw_render = [
        SetEnvironmentVariable('DISPLAY', ':1'),
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', _TB3_MODELS),
        SetEnvironmentVariable('GTK_PATH', ''),
        SetEnvironmentVariable('GTK_EXE_PREFIX', ''),
        SetEnvironmentVariable('GTK_MODULES', ''),
        SetEnvironmentVariable('GTK_IM_MODULE_FILE', ''),
        SetEnvironmentVariable('GSETTINGS_SCHEMA_DIR', '/usr/share/glib-2.0/schemas'),
    ]

    # Gazebo + Nav2 + Robot Interfaces
    robots_nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'robots_and_nav2.launch.py')
        ),
        launch_arguments={'gz_gui': LaunchConfiguration('gz_gui')}.items(),
    )

    # Ecosystem Manager
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
            'robot_count':  LaunchConfiguration('robot_count'),
            'task_count':   LaunchConfiguration('task_count'),
            'results_base': LaunchConfiguration('results_dir'),
            'gazebo_startup_delay_sec': LaunchConfiguration('startup_delay'),
        }],
    )

    # Task Visualizer — publishes /visualization/tasks MarkerArray (RViz)
    task_visualizer = Node(
        package='m_ahe_task_manager',
        executable='task_visualizer_node',
        name='task_visualizer_node',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # Gazebo Path Visualizer — publishes /visualization/gz MarkerArray (Gazebo)
    gz_path_visualizer = Node(
        package='m_ahe_task_manager',
        executable='gz_path_visualizer_node',
        name='gz_path_visualizer_node',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # RViz2
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription(
        args + sw_render + [robots_nav2, ecosystem_manager, experiment_runner,
                            task_visualizer, gz_path_visualizer, rviz]
    )
