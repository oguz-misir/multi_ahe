"""
Phase 4 launch file — headless Gazebo Harmonic + ros_gz_bridge for N robots (v3).

Reads the canonical 3-robot SDF as a template and generates a fresh world SDF
and bridge YAML for an arbitrary robot_count in [1, 15] at launch time.

Launch arguments
----------------
robot_count : number of robots to spawn (default 3, max 15)
gz_gui      : Launch Gazebo with GUI window (default false / headless)

Validation after launch (replace N with any robot index):
  ros2 topic list | grep robot_N
  ros2 topic echo /robot_N/odom --once
"""

import os
import sys
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Allow importing the sibling helpers module without a python package install
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multi_robot_helpers import generate_bridge_yaml, generate_world_sdf  # noqa: E402


def _launch_setup(context, *_args, **_kwargs):
    gazebo_share = get_package_share_directory('m_ahe_mrta_gazebo')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')

    template_world = os.path.join(gazebo_share, 'worlds', 'ahe_inspection_arena.sdf')

    robot_count = int(context.launch_configurations.get('robot_count', '3'))
    gz_gui_val = context.launch_configurations.get('gz_gui', 'false')

    # Generate per-launch world + bridge config in /tmp
    tmp_world = tempfile.NamedTemporaryFile(
        mode='w', suffix='.sdf', prefix=f'arena_{robot_count}r_', delete=False
    )
    tmp_world.close()
    generate_world_sdf(template_world, robot_count, tmp_world.name)

    tmp_bridge = tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml', prefix=f'bridge_{robot_count}r_', delete=False
    )
    tmp_bridge.close()
    generate_bridge_yaml(robot_count, tmp_bridge.name)

    # Headless: server-only (-s), no rendering window
    gz_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r -s {tmp_world.name}'}.items(),
        condition=UnlessCondition(LaunchConfiguration('gz_gui')),
    )

    gz_with_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {tmp_world.name}'}.items(),
        condition=IfCondition(LaunchConfiguration('gz_gui')),
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{'config_file': tmp_bridge.name}],
    )

    return [gz_headless, gz_with_gui, bridge]


def generate_launch_description() -> LaunchDescription:
    robot_count_arg = DeclareLaunchArgument(
        'robot_count', default_value='3',
        description='Number of robots to spawn (1..15)')
    gz_gui_arg = DeclareLaunchArgument(
        'gz_gui', default_value='false',
        description='Launch Gazebo with GUI window')

    sw_render_env = [
        SetEnvironmentVariable('DISPLAY', ':1'),
        SetEnvironmentVariable('GTK_PATH', ''),
        SetEnvironmentVariable('GTK_EXE_PREFIX', ''),
        SetEnvironmentVariable('GTK_MODULES', ''),
        SetEnvironmentVariable('GTK_IM_MODULE_FILE', ''),
        SetEnvironmentVariable('GSETTINGS_SCHEMA_DIR', '/usr/share/glib-2.0/schemas'),
    ]

    return LaunchDescription(
        [robot_count_arg, gz_gui_arg] + sw_render_env + [OpaqueFunction(function=_launch_setup)]
    )
