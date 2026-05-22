"""
Phase 3 launch file — headless Gazebo Harmonic + ros_gz_bridge for a single robot.

Nodes launched:
  gz_sim (server only, -s flag)  — loads ahe_inspection_mvp.sdf
  ros_gz_bridge parameter_bridge — bridges 6 topics using robot_1_bridge.yaml

Intel iGPU (OpenGL 4.6 Mesa) handles rendering — NVIDIA driver installed but
  display is Optimus-connected to Intel panel. GTK snap vars cleared to avoid crash.

Validation after launch:
  ros2 topic list | grep robot_1
  ros2 topic echo /robot_1/odom --no-daemon --once
  ros2 topic echo /robot_1/scan --no-daemon --once
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    gazebo_share = get_package_share_directory('m_ahe_mrta_gazebo')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')

    world_path = os.path.join(gazebo_share, 'worlds', 'ahe_inspection_mvp.sdf')
    bridge_config = os.path.join(gazebo_share, 'config', 'robot_1_bridge.yaml')

    sw_render_env = [
        SetEnvironmentVariable('DISPLAY', ':1'),
        SetEnvironmentVariable('GTK_PATH', ''),
        SetEnvironmentVariable('GTK_EXE_PREFIX', ''),
        SetEnvironmentVariable('GTK_MODULES', ''),
        SetEnvironmentVariable('GTK_IM_MODULE_FILE', ''),
    ]

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            # -r: run immediately; -s: server only (no GUI) — required for WSL2 headless
            'gz_args': f'-r -s {world_path}',
        }.items(),
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{'config_file': bridge_config}],
    )

    return LaunchDescription(sw_render_env + [
        gz_sim,
        bridge,
    ])
