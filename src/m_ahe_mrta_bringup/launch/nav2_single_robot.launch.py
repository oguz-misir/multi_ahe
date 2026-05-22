"""
Phase 5 launch file — Gazebo (single robot) + Nav2 stack for robot_1.

TF chain:
  robot_1/map  (AMCL)
    → robot_1/odom  (Gazebo diff_drive)
      → robot_1/base_link  (Gazebo diff_drive)
        → robot_1/base_scan  (robot_state_publisher, frame_prefix=robot_1/)
          → robot_1/base_scan/lidar_sensor  (static TF, identity)
        → robot_1/imu_link, robot_1/wheel_*  (robot_state_publisher)

Scan topic:  /robot_1/scan  (frame_id: robot_1/base_scan/lidar_sensor)
Cmd_vel out: /robot_1/cmd_vel  (velocity_smoother → Gazebo bridge)

Validation:
  ros2 action send_goal /robot_1/navigate_to_pose nav2_msgs/action/NavigateToPose \
    "{pose: {header: {frame_id: robot_1/map}, pose: {position: {x: 1.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}"
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml

ROBOT_NS = 'robot_1'


def generate_launch_description() -> LaunchDescription:
    nav2_cfg_share = get_package_share_directory('m_ahe_nav2_config')
    bringup_share = get_package_share_directory('m_ahe_mrta_bringup')

    map_yaml = os.path.join(nav2_cfg_share, 'maps', 'empty_map.yaml')
    nav2_params_raw = os.path.join(nav2_cfg_share, 'params', 'nav2_params.yaml')

    # Rewrite yaml to add namespace prefix — required for namespaced Nav2 nodes.
    # Without this, nested plugin params (FollowPath.plugin etc.) don't load correctly.
    nav2_params = RewrittenYaml(
        source_file=nav2_params_raw,
        root_key=ROBOT_NS,
        param_rewrites={'yaml_filename': map_yaml},
        convert_types=True,
    )
    urdf_file = os.path.join(nav2_cfg_share, 'urdf', 'waffle_pi.urdf')

    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    sw_render_env = [
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    # Gazebo + bridge (single robot)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'single_robot_gazebo.launch.py')
        ),
    )

    # robot_state_publisher — publishes robot_1/* TF frames from URDF joints
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        namespace=ROBOT_NS,
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_description': robot_description,
            'frame_prefix': f'{ROBOT_NS}/',
        }],
    )

    # Static TF: robot_1/base_scan → robot_1/base_scan/lidar_sensor (identity)
    # Needed because Gazebo sets scan frame_id = model/link/sensor scoped name.
    static_tf_lidar = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_lidar_sensor',
        output='screen',
        arguments=[
            '0', '0', '0', '0', '0', '0',
            f'{ROBOT_NS}/base_scan',
            f'{ROBOT_NS}/base_scan/lidar_sensor',
        ],
    )

    # map_server — yaml_filename is injected via RewrittenYaml param_rewrites above
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        namespace=ROBOT_NS,
        name='map_server',
        output='screen',
        parameters=[nav2_params],
    )

    # amcl
    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        namespace=ROBOT_NS,
        name='amcl',
        output='screen',
        parameters=[nav2_params],
    )

    # controller_server
    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        namespace=ROBOT_NS,
        name='controller_server',
        output='screen',
        parameters=[nav2_params],
        remappings=[('cmd_vel', 'cmd_vel_nav')],
    )

    # smoother_server
    smoother_server = Node(
        package='nav2_smoother',
        executable='smoother_server',
        namespace=ROBOT_NS,
        name='smoother_server',
        output='screen',
        parameters=[nav2_params],
    )

    # planner_server
    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        namespace=ROBOT_NS,
        name='planner_server',
        output='screen',
        parameters=[nav2_params],
    )

    # behavior_server
    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        namespace=ROBOT_NS,
        name='behavior_server',
        output='screen',
        parameters=[nav2_params],
    )

    # bt_navigator
    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        namespace=ROBOT_NS,
        name='bt_navigator',
        output='screen',
        parameters=[nav2_params],
    )

    # waypoint_follower
    waypoint_follower = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        namespace=ROBOT_NS,
        name='waypoint_follower',
        output='screen',
        parameters=[nav2_params],
    )

    # velocity_smoother — bridges cmd_vel_nav → cmd_vel (rate-limited)
    velocity_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        namespace=ROBOT_NS,
        name='velocity_smoother',
        output='screen',
        parameters=[nav2_params],
        remappings=[
            ('cmd_vel', 'cmd_vel_nav'),
            ('cmd_vel_smoothed', 'cmd_vel'),
        ],
    )

    # lifecycle_manager — activates all Nav2 nodes
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        namespace=ROBOT_NS,
        name='lifecycle_manager_nav',
        output='screen',
        parameters=[nav2_params, {
            'use_sim_time': True,
            'autostart': True,
            'node_names': [
                'map_server', 'amcl',
                'controller_server', 'smoother_server', 'planner_server',
                'behavior_server', 'bt_navigator',
                'waypoint_follower', 'velocity_smoother',
            ],
        }],
    )

    return LaunchDescription(sw_render_env + [
        gazebo,
        rsp,
        static_tf_lidar,
        map_server,
        amcl,
        controller_server,
        smoother_server,
        planner_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,
        velocity_smoother,
        lifecycle_manager,
    ])
