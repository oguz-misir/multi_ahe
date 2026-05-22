"""
Phase 9 Record launch — same as phase9_experiments but with Gazebo GUI enabled.

Used exclusively for video recording runs (run_record_experiments.sh).
Passes gz_gui:=true to robots_and_nav2 so Gazebo renders on DISPLAY=:1.
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

_DEFAULT_RESULTS = os.path.expanduser('~/multi_ahe/results/raw/gazebo_video')


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('m_ahe_mrta_bringup')

    args = [
        DeclareLaunchArgument('strategy',    default_value='full_ahe_mrta'),
        DeclareLaunchArgument('scenario',    default_value='robot_failure'),
        DeclareLaunchArgument('seed',        default_value='1'),
        DeclareLaunchArgument('robot_count', default_value='3'),
        DeclareLaunchArgument('task_count',  default_value='15'),
        DeclareLaunchArgument('results_dir', default_value=_DEFAULT_RESULTS),
        DeclareLaunchArgument('startup_delay', default_value='120.0'),
    ]

    sw_render = [
        SetEnvironmentVariable('DISPLAY', ':1'),
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
        SetEnvironmentVariable('GTK_PATH', ''),
        SetEnvironmentVariable('GTK_EXE_PREFIX', ''),
        SetEnvironmentVariable('GTK_MODULES', ''),
        SetEnvironmentVariable('GTK_IM_MODULE_FILE', ''),
    ]

    # GUI mode: gz_gui:=true → Gazebo renders on :1 for ffmpeg capture
    robots_nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'robots_and_nav2.launch.py')
        ),
        launch_arguments={'gz_gui': 'true'}.items(),
    )

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

    return LaunchDescription(
        args + sw_render + [robots_nav2, ecosystem_manager, experiment_runner]
    )
