"""
Phase 4 launch file — headless Gazebo Harmonic + ros_gz_bridge for 3 robots.

Spawns robot_1 (blue), robot_2 (green), robot_3 (red) at y = 0, +2, -2 m.
Each robot has separate namespaced topics and TF frames:
  /robot_N/cmd_vel   (ROS → GZ)
  /robot_N/odom      (GZ → ROS, frame_id=robot_N/odom)
  /robot_N/scan      (GZ → ROS)
  /robot_N/imu       (GZ → ROS)
  /tf                (GZ → ROS, all three merged; robot_N/odom → robot_N/base_link)

Validation after launch:
  ros2 topic list | grep robot_1
  ros2 topic list | grep robot_2
  ros2 topic list | grep robot_3
  ros2 topic echo /robot_2/odom --once
  ros2 topic echo /robot_3/odom --once
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

    world_path = os.path.join(gazebo_share, 'worlds', 'ahe_inspection_arena.sdf')
    bridge_config = os.path.join(gazebo_share, 'config', 'all_robots_bridge.yaml')

    sw_render_env = [
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1'),
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
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
