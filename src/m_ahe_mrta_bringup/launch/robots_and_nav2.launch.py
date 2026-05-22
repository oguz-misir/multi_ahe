"""
robots_and_nav2 — Gazebo + Nav2 + Robot Interfaces (no task manager, no allocator).

Used as the base for Phase 9 experiment runs: experiment_runner_node takes the role of
both task manager and allocator, so this launch file provides only the simulation layer.

Launch arguments
----------------
robot_count : number of robots (default 3, max 15)
gz_gui      : Launch Gazebo with GUI window (default false / headless)

The robot_count parameter passed here must match the robot_count in experiment_runner_node.
"""

import os
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Allow importing the sibling helpers module without a python package install
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multi_robot_helpers import robot_namespaces  # noqa: E402


def _launch_setup(context, *_args, **_kwargs):
    bringup = get_package_share_directory('m_ahe_mrta_bringup')
    robot_count = int(context.launch_configurations.get('robot_count', '3'))

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'multi_robot_nav2.launch.py')
        ),
        launch_arguments={
            'gz_gui': LaunchConfiguration('gz_gui'),
            'robot_count': str(robot_count),
        }.items(),
    )

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
        for robot_ns in robot_namespaces(robot_count)
    ]

    return [nav2_launch] + robot_interfaces


def generate_launch_description() -> LaunchDescription:
    robot_count_arg = DeclareLaunchArgument(
        'robot_count', default_value='3',
        description='Number of robots (1..15)')
    gz_gui_arg = DeclareLaunchArgument(
        'gz_gui', default_value='false',
        description='Launch Gazebo with GUI window')

    sw_render = [
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    return LaunchDescription(
        [robot_count_arg, gz_gui_arg] + sw_render + [OpaqueFunction(function=_launch_setup)]
    )
