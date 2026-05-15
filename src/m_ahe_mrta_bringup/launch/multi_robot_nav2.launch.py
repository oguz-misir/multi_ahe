"""
Phase 5 launch file — Gazebo (3 robots) + Nav2 stack for each robot.

Nav2 params are generated at launch time from nav2_params.yaml by substituting
the robot namespace, so a single template drives all three stacks.

TF chain per robot (N = 1,2,3):
  robot_N/map  (AMCL)
    → robot_N/odom  (Gazebo diff_drive)
      → robot_N/base_link  (robot_state_publisher)
        → robot_N/base_scan  (robot_state_publisher)
          → robot_N/base_scan/lidar_sensor  (static TF, identity)

Validation (run in separate terminal after lifecycle_manager activates):
  ros2 action send_goal /robot_1/navigate_to_pose nav2_msgs/action/NavigateToPose \
    "{pose: {header: {frame_id: robot_1/map}, pose: {position: {x: 1.0, y: 0.5, z: 0.0}, orientation: {w: 1.0}}}}"
  ros2 action send_goal /robot_2/navigate_to_pose nav2_msgs/action/NavigateToPose \
    "{pose: {header: {frame_id: robot_2/map}, pose: {position: {x: 1.0, y: 2.5, z: 0.0}, orientation: {w: 1.0}}}}"
  ros2 action send_goal /robot_3/navigate_to_pose nav2_msgs/action/NavigateToPose \
    "{pose: {header: {frame_id: robot_3/map}, pose: {position: {x: 1.0, y: -1.5, z: 0.0}, orientation: {w: 1.0}}}}"
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
    """Generate a per-robot Nav2 params file from the shared template.

    Substitutes every occurrence of 'robot_1' with the target namespace and
    injects the absolute map path. Returns the path to a temp file that
    persists for the lifetime of the process.
    """
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
    """Return the full Nav2 node list for one robot namespace."""
    p = params_file

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        namespace=robot_ns,
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_description': robot_description,
            'frame_prefix': f'{robot_ns}/',
        }],
    )

    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name=f'static_tf_lidar_{robot_ns}',
        output='screen',
        arguments=[
            '0', '0', '0', '0', '0', '0',
            f'{robot_ns}/base_scan',
            f'{robot_ns}/base_scan/lidar_sensor',
        ],
    )

    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        namespace=robot_ns,
        name='map_server',
        output='screen',
        parameters=[p],
    )

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        namespace=robot_ns,
        name='amcl',
        output='screen',
        parameters=[p],
    )

    controller = Node(
        package='nav2_controller',
        executable='controller_server',
        namespace=robot_ns,
        name='controller_server',
        output='screen',
        parameters=[p],
        remappings=[('cmd_vel', 'cmd_vel_nav')],
    )

    smoother = Node(
        package='nav2_smoother',
        executable='smoother_server',
        namespace=robot_ns,
        name='smoother_server',
        output='screen',
        parameters=[p],
    )

    planner = Node(
        package='nav2_planner',
        executable='planner_server',
        namespace=robot_ns,
        name='planner_server',
        output='screen',
        parameters=[p],
    )

    behavior = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        namespace=robot_ns,
        name='behavior_server',
        output='screen',
        parameters=[p],
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        namespace=robot_ns,
        name='bt_navigator',
        output='screen',
        parameters=[p],
    )

    waypoint = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        namespace=robot_ns,
        name='waypoint_follower',
        output='screen',
        parameters=[p],
    )

    vel_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        namespace=robot_ns,
        name='velocity_smoother',
        output='screen',
        parameters=[p],
        remappings=[
            ('cmd_vel', 'cmd_vel_nav'),
            ('cmd_vel_smoothed', 'cmd_vel'),
        ],
    )

    lifecycle = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        namespace=robot_ns,
        name='lifecycle_manager_nav',
        output='screen',
        parameters=[p, {
            'use_sim_time': True,
            'autostart': True,
            'node_names': NAV2_NODES,
        }],
    )

    return [rsp, static_tf, map_server, amcl, controller, smoother,
            planner, behavior, bt_navigator, waypoint, vel_smoother, lifecycle]


def generate_launch_description() -> LaunchDescription:
    nav2_cfg = get_package_share_directory('m_ahe_nav2_config')
    bringup = get_package_share_directory('m_ahe_mrta_bringup')

    map_yaml = os.path.join(nav2_cfg, 'maps', 'obstacle_map.yaml')
    template = os.path.join(nav2_cfg, 'params', 'nav2_params.yaml')
    urdf_file = os.path.join(nav2_cfg, 'urdf', 'waffle_pi.urdf')

    with open(urdf_file) as f:
        robot_description = f.read()

    sw_render = [
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1'),
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'multi_robot_gazebo.launch.py')
        ),
    )

    all_nodes = []
    for robot_ns in ROBOTS:
        params_file = _make_nav2_params(template, robot_ns, map_yaml)
        all_nodes.extend(_nav2_nodes(robot_ns, params_file, robot_description))

    return LaunchDescription(sw_render + [gazebo] + all_nodes)
