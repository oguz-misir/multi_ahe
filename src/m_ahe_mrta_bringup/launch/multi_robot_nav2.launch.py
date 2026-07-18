"""
Phase 5 launch file — Gazebo (N robots) + Nav2 stack for each robot (v3).

Nav2 params are generated at launch time from nav2_params.yaml by substituting
the robot namespace, so a single template drives all N stacks.

TF chain per robot (N = 1..robot_count):
  robot_N/map  (static TF at spawn offset — replaces AMCL for sim)
    → robot_N/odom  (Gazebo diff_drive, odom starts at 0,0 relative to spawn)
      → robot_N/base_link  (odom_to_tf)
        → robot_N/base_scan  (robot_state_publisher)
          → robot_N/base_scan/lidar_sensor  (static TF, identity)

AMCL is intentionally omitted. In Gazebo, the diff_drive plugin provides
perfect odometry (no encoder noise). A static map→odom TF at the spawn
offset gives exact ground-truth localization, which is appropriate for
multi-robot task-allocation simulation experiments.

Launch arguments
----------------
robot_count : number of robots (default 3, max 15)
gz_gui      : Launch Gazebo with GUI window (default false / headless)
"""

import os
import sys
import tempfile

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Allow importing the sibling helpers module without a python package install
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multi_robot_helpers import compute_spawn_positions, robot_namespaces  # noqa: E402


NAV2_NODES = [
    'map_server',
    'controller_server', 'planner_server',
    'behavior_server', 'bt_navigator',
]


def _make_behavior_override(robot_ns: str) -> str:
    """Generate a minimal params file that uses /** to force correct frames on behavior_server.

    The main params file uses /robot_N/behavior_server as the key, but in Jazzy
    that key format may not match the node FQN reliably.  A /** wildcard in a
    second params file (loaded last) always wins.
    """
    data = {
        '/**': {
            'ros__parameters': {
                'global_frame': f'{robot_ns}/odom',
                'robot_base_frame': f'{robot_ns}/base_link',
                'local_frame': f'{robot_ns}/odom',
            }
        }
    }
    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml',
        prefix=f'bs_override_{robot_ns}_',
        delete=False,
    )
    yaml.dump(data, tmp)
    tmp.close()
    return tmp.name


def _make_nav2_params(template_path: str, robot_ns: str, map_yaml: str,
                       spawn_x: float, spawn_y: float,
                       other_namespaces: list = None) -> str:
    """Generate a per-robot Nav2 params file from the shared template.

    Rewrites every top-level node key to its fully qualified ROS2 path so
    ROS2 Jazzy namespace matching works (e.g. 'amcl' → '/robot_1/amcl').
    AMCL initial_pose is set to the actual SDF spawn position so the
    particle filter doesn't diverge.
    other_namespaces: list of other robot namespaces whose /scan topics are
    added as marking-only observation sources in the local costmap so that
    each robot avoids all other robots as dynamic obstacles.
    """
    with open(template_path) as f:
        content = f.read().replace('robot_1', robot_ns)
    data = yaml.safe_load(content)

    qualified = {}
    for key, value in data.items():
        if key in ('local_costmap', 'global_costmap'):
            inner = value.get(key, {})
            qualified[f'/{robot_ns}/{key}/{key}'] = inner
        else:
            qualified[f'/{robot_ns}/{key}'] = value

    qualified[f'/{robot_ns}/map_server']['ros__parameters']['yaml_filename'] = map_yaml

    amcl_params = qualified[f'/{robot_ns}/amcl']['ros__parameters']
    amcl_params['initial_pose']['x'] = float(spawn_x)
    amcl_params['initial_pose']['y'] = float(spawn_y)

    # Add other robots' laser scans as dynamic obstacles in the local costmap.
    # marking=True so each robot appears as an obstacle; clearing=False so one
    # robot never clears another's map region based on its own sensor FOV.
    if other_namespaces:
        lc_key = f'/{robot_ns}/local_costmap/local_costmap'
        lc_params = qualified[lc_key]['ros__parameters']
        voxel = lc_params.get('voxel_layer', {})
        extra = []
        for other_ns in other_namespaces:
            src = f'scan_{other_ns}'
            extra.append(src)
            voxel[src] = {
                'topic': f'/{other_ns}/scan',
                'max_obstacle_height': 2.0,
                'clearing': False,
                'marking': True,
                'data_type': 'LaserScan',
                'raytrace_max_range': 3.0,
                'raytrace_min_range': 0.0,
                'obstacle_max_range': 2.5,
                'obstacle_min_range': 0.0,
            }
        current = voxel.get('observation_sources', 'scan')
        voxel['observation_sources'] = current + ' ' + ' '.join(extra)
        lc_params['voxel_layer'] = voxel

    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml',
        prefix=f'nav2_{robot_ns}_',
        delete=False,
    )
    yaml.dump(qualified, tmp)
    tmp.close()
    return tmp.name


def _nav2_nodes(robot_ns: str, params_file: str, robot_description: str, map_yaml: str,
                spawn_x: float = 0.0, spawn_y: float = 0.0,
                eager_delay: float = 0.0,
                lifecycle_delay: float = 0.0) -> list:
    """Return the full Nav2 node list for one robot namespace.

    eager_delay: seconds to wait before starting all non-lifecycle nodes.
    lifecycle_delay: seconds to wait before starting the lifecycle_manager.
    For ≥10r, both are staggered so only one robot's Nav2 stack initializes at a
    time, preventing executor overload and async_send_request failures during
    bt_navigator/map_server configure+activate.
    """
    p = params_file
    bs_override = _make_behavior_override(robot_ns)

    tf_remap = [('/tf', f'/{robot_ns}/tf'), ('/tf_static', f'/{robot_ns}/tf_static')]

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
        remappings=tf_remap,
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
        remappings=tf_remap,
    )

    world_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name=f'static_tf_world_{robot_ns}',
        output='screen',
        arguments=['0', '0', '0', '0', '0', '0', 'world', f'{robot_ns}/map'],
        remappings=tf_remap,
    )

    # map→odom: spawn-pose offset.
    # Gazebo Harmonic diff_drive initializes odometry at ZERO (spawn-relative),
    # NOT at the model's world pose (verified 2026-07-18: every robot's first
    # logged pose is (0,0) while ground truth sits on the spawn grid). Anchoring
    # odom at the spawn pose therefore yields exact ground-truth localization:
    # map pose = spawn + odom displacement. An identity transform here instead
    # shifts each robot's believed frame by -spawn, desynchronizing Nav2/RViz
    # from the physical arena.
    map_odom_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name=f'static_tf_map_odom_{robot_ns}',
        output='screen',
        arguments=[
            str(spawn_x), str(spawn_y), '0',
            '0', '0', '0',
            f'{robot_ns}/map', f'{robot_ns}/odom',
        ],
        remappings=tf_remap,
    )

    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        namespace=robot_ns,
        name='map_server',
        output='screen',
        parameters=[p, {'yaml_filename': map_yaml}],
        remappings=tf_remap,
    )

    controller = Node(
        package='nav2_controller',
        executable='controller_server',
        namespace=robot_ns,
        name='controller_server',
        output='screen',
        parameters=[p, {
            'FollowPath.plugin': 'nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController',
        }],
        remappings=tf_remap,
    )

    planner = Node(
        package='nav2_planner',
        executable='planner_server',
        namespace=robot_ns,
        name='planner_server',
        output='screen',
        parameters=[p],
        remappings=tf_remap,
    )

    behavior = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        namespace=robot_ns,
        name='behavior_server',
        output='screen',
        parameters=[p, bs_override],
        remappings=tf_remap,
    )

    odom_to_tf = Node(
        package='m_ahe_mrta_bringup',
        executable='odom_to_tf',
        namespace=robot_ns,
        name='odom_to_tf',
        output='screen',
        parameters=[{'use_sim_time': True}],
        remappings=tf_remap,
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        namespace=robot_ns,
        name='bt_navigator',
        output='screen',
        parameters=[p],
        remappings=tf_remap,
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
            'bond_timeout': 60.0,
            'service_client_timeout_sec': 120.0,
        }],
        remappings=tf_remap,
    )

    eager = [rsp, static_tf, world_tf, map_odom_tf, map_server, controller,
             planner, behavior, bt_navigator, odom_to_tf]

    if eager_delay > 0.0:
        # Stagger ALL nodes: wrap eager + lifecycle in separate TimerActions.
        # This prevents concurrent executor overload (async_send_request failures)
        # when ≥10 Nav2 stacks all try to configure/activate simultaneously.
        delayed_eager = TimerAction(period=eager_delay, actions=eager)
        delayed_lifecycle = TimerAction(period=lifecycle_delay, actions=[lifecycle])
        return [delayed_eager, delayed_lifecycle]
    if lifecycle_delay > 0.0:
        delayed_lifecycle = TimerAction(period=lifecycle_delay, actions=[lifecycle])
        return eager + [delayed_lifecycle]
    return eager + [lifecycle]


def _launch_setup(context, *_args, **_kwargs):
    nav2_cfg = get_package_share_directory('m_ahe_nav2_config')
    bringup = get_package_share_directory('m_ahe_mrta_bringup')

    map_yaml = os.path.join(nav2_cfg, 'maps', 'obstacle_map.yaml')
    template = os.path.join(nav2_cfg, 'params', 'nav2_params.yaml')
    urdf_file = os.path.join(nav2_cfg, 'urdf', 'waffle_pi.urdf')

    with open(urdf_file) as f:
        robot_description = f.read()

    robot_count = int(context.launch_configurations.get('robot_count', '3'))
    positions = compute_spawn_positions(robot_count)
    namespaces = robot_namespaces(robot_count)

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'multi_robot_gazebo.launch.py')
        ),
        launch_arguments={
            'gz_gui': LaunchConfiguration('gz_gui'),
            'robot_count': str(robot_count),
        }.items(),
    )

    all_nodes = [gazebo]
    if robot_count >= 10:
        # 10s/robot (was 20s): at 20s, the last robot's Nav2 did not finish
        # activating until ~210s+ under load, which exceeded the video capture
        # window so the experiment never dispatched goals. 10s still spaces the
        # lifecycle configure/activate enough to avoid concurrent executor overload.
        stagger_eager_s = 10.0
        lc_offset_s = 20.0
        for idx, (robot_ns, (sx, sy)) in enumerate(zip(namespaces, positions)):
            # NOTE: peer-scan obstacle sources (other_namespaces) are intentionally
            # NOT used: each robot's Nav2 stack remaps /tf -> /robot_N/tf, so a
            # robot's TF buffer has no transforms for peer base_scan frames and
            # cannot place their scans. Each robot already detects peers via its
            # OWN laser (now fed into the global obstacle_layer too).
            params_file = _make_nav2_params(template, robot_ns, map_yaml, sx, sy)
            eager_delay = idx * stagger_eager_s
            lifecycle_delay = eager_delay + lc_offset_s
            all_nodes.extend(_nav2_nodes(robot_ns, params_file, robot_description, map_yaml,
                                         spawn_x=sx, spawn_y=sy,
                                         eager_delay=eager_delay,
                                         lifecycle_delay=lifecycle_delay))
    else:
        stagger_s = 6.0
        for idx, (robot_ns, (sx, sy)) in enumerate(zip(namespaces, positions)):
            params_file = _make_nav2_params(template, robot_ns, map_yaml, sx, sy)
            lifecycle_delay = idx * stagger_s
            all_nodes.extend(_nav2_nodes(robot_ns, params_file, robot_description, map_yaml,
                                         spawn_x=sx, spawn_y=sy,
                                         lifecycle_delay=lifecycle_delay))
    return all_nodes


def generate_launch_description() -> LaunchDescription:
    robot_count_arg = DeclareLaunchArgument(
        'robot_count', default_value='3',
        description='Number of robots to spawn (1..15)')
    gz_gui_arg = DeclareLaunchArgument(
        'gz_gui', default_value='false',
        description='Launch Gazebo with GUI window')

    sw_render = [
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    return LaunchDescription(
        [robot_count_arg, gz_gui_arg] + sw_render + [OpaqueFunction(function=_launch_setup)]
    )
