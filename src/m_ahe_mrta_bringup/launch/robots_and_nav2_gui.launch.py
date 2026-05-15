"""
robots_and_nav2_gui — Gazebo GUI + RViz2 + Nav2 + Robot Interfaces.

Same as robots_and_nav2.launch.py but with:
  - Gazebo Harmonic with GUI window (no -s server-only flag; -r only)
  - RViz2 with multi-robot config (map, laser, path, pose for all 3 robots)

Nav2 nodes are inlined here (not via multi_robot_nav2.launch.py include) to avoid
launching Gazebo twice — multi_robot_nav2 already embeds multi_robot_gazebo headless.

WSL2 / WSLg note:
  GUI requires WSLg (Windows 11) or an X server (VcXsrv / XLaunch on Windows 10).
  Software rendering env vars are still set for OGRE2 / RViz2 OGRE compatibility.
  If Gazebo GUI shows a black screen: export MESA_GL_VERSION_OVERRIDE=3.3
"""

import os
import tempfile

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

ROBOTS = ['robot_1', 'robot_2', 'robot_3']
NAV2_NODES = [
    'map_server', 'amcl',
    'controller_server', 'smoother_server', 'planner_server',
    'behavior_server', 'bt_navigator',
    'waypoint_follower', 'velocity_smoother',
]


def _make_nav2_params(template_path: str, robot_ns: str, map_yaml: str) -> str:
    with open(template_path) as f:
        content = f.read().replace('robot_1', robot_ns)
    data = yaml.safe_load(content)
    data['map_server']['ros__parameters']['yaml_filename'] = map_yaml
    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml',
        prefix=f'nav2_{robot_ns}_',
        delete=False,
    )
    yaml.dump(data, tmp)
    tmp.close()
    return tmp.name


def _nav2_nodes(robot_ns: str, params_file: str, robot_description: str) -> list:
    p = params_file
    return [
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             namespace=robot_ns, name='robot_state_publisher', output='screen',
             parameters=[{'use_sim_time': True, 'robot_description': robot_description,
                          'frame_prefix': f'{robot_ns}/'}]),
        Node(package='tf2_ros', executable='static_transform_publisher',
             name=f'static_tf_lidar_{robot_ns}', output='screen',
             arguments=['0', '0', '0', '0', '0', '0',
                        f'{robot_ns}/base_scan', f'{robot_ns}/base_scan/lidar_sensor']),
        Node(package='nav2_map_server', executable='map_server',
             namespace=robot_ns, name='map_server', output='screen', parameters=[p]),
        Node(package='nav2_amcl', executable='amcl',
             namespace=robot_ns, name='amcl', output='screen', parameters=[p]),
        Node(package='nav2_controller', executable='controller_server',
             namespace=robot_ns, name='controller_server', output='screen',
             parameters=[p], remappings=[('cmd_vel', 'cmd_vel_nav')]),
        Node(package='nav2_smoother', executable='smoother_server',
             namespace=robot_ns, name='smoother_server', output='screen', parameters=[p]),
        Node(package='nav2_planner', executable='planner_server',
             namespace=robot_ns, name='planner_server', output='screen', parameters=[p]),
        Node(package='nav2_behaviors', executable='behavior_server',
             namespace=robot_ns, name='behavior_server', output='screen', parameters=[p]),
        Node(package='nav2_bt_navigator', executable='bt_navigator',
             namespace=robot_ns, name='bt_navigator', output='screen', parameters=[p]),
        Node(package='nav2_waypoint_follower', executable='waypoint_follower',
             namespace=robot_ns, name='waypoint_follower', output='screen', parameters=[p]),
        Node(package='nav2_velocity_smoother', executable='velocity_smoother',
             namespace=robot_ns, name='velocity_smoother', output='screen',
             parameters=[p],
             remappings=[('cmd_vel', 'cmd_vel_nav'), ('cmd_vel_smoothed', 'cmd_vel')]),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             namespace=robot_ns, name='lifecycle_manager_nav', output='screen',
             parameters=[p, {'use_sim_time': True, 'autostart': True,
                             'node_names': NAV2_NODES}]),
    ]


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('m_ahe_mrta_bringup')
    gazebo_share = get_package_share_directory('m_ahe_mrta_gazebo')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    nav2_cfg = get_package_share_directory('m_ahe_nav2_config')

    world_path = os.path.join(gazebo_share, 'worlds', 'ahe_inspection_arena.sdf')
    bridge_config = os.path.join(gazebo_share, 'config', 'all_robots_bridge.yaml')
    rviz_config = os.path.join(bringup, 'config', 'phase9_demo.rviz')
    map_yaml = os.path.join(nav2_cfg, 'maps', 'obstacle_map.yaml')
    template = os.path.join(nav2_cfg, 'params', 'nav2_params.yaml')
    urdf_file = os.path.join(nav2_cfg, 'urdf', 'waffle_pi.urdf')

    with open(urdf_file) as f:
        robot_description = f.read()

    sw_render = [
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1'),
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    # Gazebo with GUI — -r only (no -s server-only flag)
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_path}'}.items(),
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{'config_file': bridge_config}],
    )

    # RViz2 — 3-robot view: map (×3), laser (×3), path (×3), amcl_pose (×3)
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
    )

    # Nav2 stacks (inlined to avoid double-Gazebo when including multi_robot_nav2)
    all_nav2_nodes = []
    for robot_ns in ROBOTS:
        params_file = _make_nav2_params(template, robot_ns, map_yaml)
        all_nav2_nodes.extend(_nav2_nodes(robot_ns, params_file, robot_description))

    # Robot interfaces
    robot_interfaces = [
        Node(
            package='m_ahe_robot_interface',
            executable='robot_interface_node',
            name=f'robot_interface_{robot_ns}',
            output='screen',
            parameters=[{'use_sim_time': True, 'robot_id': robot_ns}],
        )
        for robot_ns in ROBOTS
    ]

    return LaunchDescription(
        sw_render + [gz_sim, bridge, rviz] + all_nav2_nodes + robot_interfaces
    )
