"""
Phase 9 Demo launch — Gazebo + Nav2 + RViz + Task Visualizer + Experiment Runner.

Generates a robot-count-aware RViz config at launch time so all N robots'
3D models, global plans, and local plans are visible.
Positions Gazebo on the left half and RViz on the right half (1920x1080).

Usage:
  ros2 launch m_ahe_mrta_bringup phase9_demo.launch.py strategy:=full_ahe_mrta scenario:=robot_failure seed:=1
  ros2 launch m_ahe_mrta_bringup phase9_demo.launch.py strategy:=rostam_ea    scenario:=mixed_stress   seed:=2
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_TB3_MODELS = '/opt/ros/jazzy/share/turtlebot3_gazebo/models'
_DEFAULT_RESULTS = os.path.expanduser('~/multi_ahe/results/raw/gazebo')

# Per-robot colors: (R, G, B)
_ROBOT_COLORS = [
    (0,   120, 255),   # 1 blue
    (0,   200,  80),   # 2 green
    (220,  50,  50),   # 3 red
    (255, 140,   0),   # 4 orange
    (160,  32, 240),   # 5 purple
    (0,   200, 200),   # 6 cyan
    (220, 200,   0),   # 7 yellow
    (255,   0, 128),   # 8 pink
    (160,  82,  45),   # 9 brown
    (100, 200,   0),   # 10 lime
]


def _rgb(r, g, b):
    return f'{r}; {g}; {b}'


def _make_rviz_config(robot_count: int) -> str:
    """Generate a robot-count-aware RViz config and return the temp file path."""
    displays = []

    # Grid
    displays.append({
        'Class': 'rviz_default_plugins/Grid',
        'Alpha': 0.4,
        'Cell Size': 1,
        'Color': '160; 160; 164',
        'Enabled': True,
        'Line Style': {'Line Width': 0.03, 'Value': 'Lines'},
        'Name': 'Grid',
        'Plane': 'XY',
        'Plane Cell Count': 20,
        'Reference Frame': '<Fixed Frame>',
        'Value': True,
    })

    # TF
    displays.append({
        'Class': 'rviz_default_plugins/TF',
        'Enabled': True,
        'Filter (blacklist)': '',
        'Filter (whitelist)': '',
        'Frame Timeout': 15,
        'Frames': {'All Enabled': False},
        'Marker Scale': 0.4,
        'Name': 'TF',
        'Show Arrows': False,
        'Show Axes': True,
        'Show Names': True,
        'Tree': {},
        'Update Interval': 0,
        'Value': True,
    })

    # Map (robot_1)
    displays.append({
        'Class': 'rviz_default_plugins/Map',
        'Alpha': 0.6,
        'Color Scheme': 'map',
        'Draw Behind': False,
        'Enabled': True,
        'Name': 'Map',
        'Topic': {
            'Depth': 1,
            'Durability Policy': 'Transient Local',
            'Filter size': 10,
            'History Policy': 'Keep Last',
            'Reliability Policy': 'Reliable',
            'Value': '/robot_1/map',
        },
        'Update Topic': {
            'Depth': 5,
            'Durability Policy': 'Volatile',
            'Filter size': 10,
            'History Policy': 'Keep Last',
            'Reliability Policy': 'Reliable',
            'Value': '/robot_1/map_updates',
        },
        'Use Timestamp': False,
        'Value': True,
    })

    # Per-robot: RobotModel + LaserScan + GlobalPlan + LocalPlan
    for i in range(1, robot_count + 1):
        ns = f'robot_{i}'
        r, g, b = _ROBOT_COLORS[(i - 1) % len(_ROBOT_COLORS)]
        color = _rgb(r, g, b)

        # 3D robot model
        displays.append({
            'Alpha': 1,
            'Class': 'rviz_default_plugins/RobotModel',
            'Collision Enabled': False,
            'Description File': '',
            'Description Source': 'Topic',
            'Description Topic': {
                'Depth': 5,
                'Durability Policy': 'Transient Local',
                'Filter size': 10,
                'History Policy': 'Keep Last',
                'Reliability Policy': 'Reliable',
                'Value': f'/{ns}/robot_description',
            },
            'Enabled': True,
            'Links': {},
            'Name': f'Robot{i}_Model',
            'TF Prefix': ns,
            'Update Interval': 0,
            'Value': True,
            'Visual Enabled': True,
        })

        # Laser scan
        displays.append({
            'Class': 'rviz_default_plugins/LaserScan',
            'Alpha': 0.7,
            'Autocompute Intensity Bounds': True,
            'Autocompute Value Bounds': {'Max Value': 10, 'Min Value': -10, 'Value': True},
            'Axis': 'Z',
            'Channel Name': 'intensity',
            'Color': color,
            'Color Transformer': 'FlatColor',
            'Decay Time': 0,
            'Enabled': True,
            'Invert Rainbow': False,
            'Max Color': '255; 255; 255',
            'Max Intensity': 4096,
            'Min Color': '0; 0; 0',
            'Min Intensity': 0,
            'Name': f'Robot{i}_Laser',
            'Position Transformer': 'XYZ',
            'Queue Size': 10,
            'Selectable': True,
            'Size (Pixels)': 3,
            'Size (m)': 0.01,
            'Style': 'Flat Squares',
            'Topic': {
                'Depth': 5,
                'Durability Policy': 'Volatile',
                'Filter size': 10,
                'History Policy': 'Keep Last',
                'Reliability Policy': 'Best Effort',
                'Value': f'/{ns}/scan',
            },
            'Use Fixed Frame': True,
            'Use rainbow': False,
            'Value': True,
        })

        # Global plan
        displays.append({
            'Alpha': 1,
            'Buffer Length': 1,
            'Class': 'rviz_default_plugins/Path',
            'Color': color,
            'Enabled': True,
            'Head Arrow Shaft Diameter': 0.1,
            'Head Arrow Shaft Length': 0.3,
            'Head Diameter': 0.3,
            'Head Length': 0.2,
            'Length': 0.3,
            'Line Style': 'Lines',
            'Line Width': 0.06,
            'Name': f'Robot{i}_GlobalPlan',
            'Offset': {'X': 0, 'Y': 0, 'Z': 0.05},
            'Pose Color': '255; 85; 255',
            'Pose Style': 'None',
            'Queue Size': 10,
            'Radius': 0.03,
            'Shaft Diameter': 0.1,
            'Shaft Length': 0.1,
            'Topic': {
                'Depth': 5,
                'Durability Policy': 'Volatile',
                'Filter size': 10,
                'History Policy': 'Keep Last',
                'Reliability Policy': 'Reliable',
                'Value': f'/{ns}/plan',
            },
            'Value': True,
        })

        # Local plan (controller trajectory — updates every control cycle)
        lr = min(r + 80, 255)
        lg = min(g + 80, 255)
        lb = min(b + 80, 255)
        displays.append({
            'Alpha': 0.8,
            'Buffer Length': 1,
            'Class': 'rviz_default_plugins/Path',
            'Color': _rgb(lr, lg, lb),
            'Enabled': True,
            'Line Style': 'Lines',
            'Line Width': 0.04,
            'Name': f'Robot{i}_LocalPlan',
            'Offset': {'X': 0, 'Y': 0, 'Z': 0.08},
            'Pose Style': 'None',
            'Queue Size': 10,
            'Topic': {
                'Depth': 5,
                'Durability Policy': 'Volatile',
                'Filter size': 10,
                'History Policy': 'Keep Last',
                'Reliability Policy': 'Reliable',
                'Value': f'/{ns}/local_plan',
            },
            'Value': True,
        })

    # Task markers
    displays.append({
        'Class': 'rviz_default_plugins/MarkerArray',
        'Enabled': True,
        'Name': 'Tasks',
        'Namespaces': {},
        'Topic': {
            'Depth': 5,
            'Durability Policy': 'Volatile',
            'Filter size': 10,
            'History Policy': 'Keep Last',
            'Reliability Policy': 'Reliable',
            'Value': '/visualization/tasks',
        },
        'Value': True,
    })

    config = {
        'Panels': [
            {
                'Class': 'rviz_common/Displays',
                'Help Height': 78,
                'Name': 'Displays',
                'Property Tree Widget': {'Expanded': [], 'Splitter Ratio': 0.5},
                'Tree Height': 900,
            },
            {
                'Class': 'rviz_common/Views',
                'Expanded': ['/Current View1'],
                'Name': 'Views',
                'Splitter Ratio': 0.5,
            },
        ],
        'Preferences': {'PromptSaveOnExit': False},
        'Toolbars': {'toolButtonStyle': 2},
        'Visualization Manager': {
            'Class': '',
            'Displays': displays,
            'Enabled': True,
            'Global Options': {
                'Background Color': '20; 20; 20',
                'Fixed Frame': 'world',
                'Frame Rate': 30,
            },
            'Name': 'root',
            'Tools': [
                {'Class': 'rviz_default_plugins/MoveCamera'},
                {'Class': 'rviz_default_plugins/Select'},
                {'Class': 'rviz_default_plugins/FocusCamera'},
            ],
            'Transformation': {'Current': {'Class': 'rviz_default_plugins/TF'}},
            'Value': True,
            'Views': {
                'Current': {
                    'Class': 'rviz_default_plugins/TopDownOrtho',
                    'Enable Stereo Rendering': {
                        'Stereo Eye Separation': 0.06,
                        'Stereo Focal Distance': 1,
                        'Swap Stereo Eyes': False,
                        'Value': False,
                    },
                    'Invert Z Axis': False,
                    'Name': 'Current View',
                    'Near Clip Distance': 0.009999999776482582,
                    'Scale': 60 if robot_count <= 3 else (45 if robot_count <= 5 else 30),
                    'Target Frame': '<Fixed Frame>',
                    'Value': 'TopDownOrtho',
                    'X': 0,
                    'Y': 0,
                },
                'Saved': None,
            },
        },
        # RViz full screen — Gazebo runs headless, RViz is the only window
        'Window Geometry': {
            'Displays': {'collapsed': False},
            'Height': 1080,
            'Hide Left Dock': False,
            'Hide Right Dock': True,
            'Views': {'collapsed': False},
            'Width': 1920,
            'X': 0,
            'Y': 0,
        },
    }

    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.rviz',
        prefix=f'demo_{robot_count}r_',
        delete=False,
    )
    yaml.dump(config, tmp, default_flow_style=False, allow_unicode=True)
    tmp.close()
    return tmp.name


def _launch_setup(context, *_args, **_kwargs):
    bringup = get_package_share_directory('m_ahe_mrta_bringup')
    robot_count = int(context.launch_configurations.get('robot_count', '3'))

    rviz_config = _make_rviz_config(robot_count)

    robots_nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'robots_and_nav2.launch.py')
        ),
        launch_arguments={
            'gz_gui': context.launch_configurations.get('gz_gui', 'true'),
            'robot_count': str(robot_count),
        }.items(),
    )

    ecosystem_manager = Node(
        package='m_ahe_ecosystem_manager',
        executable='ecosystem_manager_node',
        name='ecosystem_manager_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_count': robot_count,
            'update_period_sec': 2.0,
            'results_dir': context.launch_configurations.get('results_dir', _DEFAULT_RESULTS),
        }],
    )

    experiment_runner = Node(
        package='m_ahe_task_allocator',
        executable='experiment_runner_node',
        name='experiment_runner_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'strategy':     context.launch_configurations.get('strategy', 'full_ahe_mrta'),
            'scenario':     context.launch_configurations.get('scenario', 'robot_failure'),
            'seed':         int(context.launch_configurations.get('seed', '1')),
            'robot_count':  robot_count,
            'task_count':   int(context.launch_configurations.get('task_count', '15')),
            'results_base': context.launch_configurations.get('results_dir', _DEFAULT_RESULTS),
            'gazebo_startup_delay_sec': float(
                context.launch_configurations.get('startup_delay', '75.0')),
        }],
    )

    task_visualizer = Node(
        package='m_ahe_task_manager',
        executable='task_visualizer_node',
        name='task_visualizer_node',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    gz_path_visualizer = Node(
        package='m_ahe_task_manager',
        executable='gz_path_visualizer_node',
        name='gz_path_visualizer_node',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        # RViz on its own virtual screen :3; Gazebo + all other nodes use :2
        additional_env={'DISPLAY': ':3'},
    )

    # Relay per-robot /robot_N/tf[_static] → global /tf[_static] so RViz sees all frames
    tf_relay = Node(
        package='m_ahe_mrta_bringup',
        executable='tf_relay_node',
        name='tf_relay_node',
        output='screen',
        parameters=[{'robot_count': robot_count, 'use_sim_time': True}],
    )

    nodes = [robots_nav2, ecosystem_manager, experiment_runner,
             task_visualizer, gz_path_visualizer, tf_relay]
    # use_rviz=false drops RViz (and tf_relay is only needed for RViz) so the
    # Gazebo-only recording pass stays light enough to avoid the Nav2 lifecycle
    # deadlock under software rendering.
    if context.launch_configurations.get('use_rviz', 'true').lower() != 'false':
        # DELAY RViz: on GPU-less software rendering, RViz's llvmpipe rasterisation
        # competes with the 3x Nav2 bring-up for CPU, pushing load to ~280 and
        # starving DDS service discovery -> lifecycle deadlock. Starting RViz only
        # after Nav2 has had time to activate keeps the bring-up window light.
        rviz_delay = float(context.launch_configurations.get('rviz_delay', '110.0'))
        nodes.append(TimerAction(period=rviz_delay, actions=[rviz]))
    return nodes


def generate_launch_description() -> LaunchDescription:
    args = [
        DeclareLaunchArgument('strategy',      default_value='full_ahe_mrta'),
        DeclareLaunchArgument('scenario',      default_value='robot_failure'),
        DeclareLaunchArgument('seed',          default_value='1'),
        DeclareLaunchArgument('robot_count',   default_value='3'),
        DeclareLaunchArgument('task_count',    default_value='15'),
        DeclareLaunchArgument('results_dir',   default_value=_DEFAULT_RESULTS),
        DeclareLaunchArgument('startup_delay', default_value='75.0'),
        DeclareLaunchArgument('gz_gui',        default_value='true'),
        DeclareLaunchArgument('use_rviz',      default_value='true'),
        DeclareLaunchArgument('rviz_delay',    default_value='110.0'),
    ]

    sw_render = [
        SetEnvironmentVariable('DISPLAY', ':2'),  # Gazebo + all nodes → virtual screen :2
        # Software rendering required: RTX 3050 Mobile has no driver;
        # OGRE1 (not OGRE2) via GLX to avoid EGL driCreateNewScreen3 segfault.
        SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1'),
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
        SetEnvironmentVariable('MESA_LOADER_DRIVER_OVERRIDE', 'llvmpipe'),
        SetEnvironmentVariable('MESA_GL_VERSION_OVERRIDE', '4.5'),
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', _TB3_MODELS),
        # VS Code snap GTK pollution fix (prevents RViz crash on startup)
        SetEnvironmentVariable('GTK_PATH', ''),
        SetEnvironmentVariable('GTK_EXE_PREFIX', ''),
        SetEnvironmentVariable('GTK_MODULES', ''),
        SetEnvironmentVariable('GTK_IM_MODULE_FILE', ''),
        SetEnvironmentVariable('GSETTINGS_SCHEMA_DIR', '/usr/share/glib-2.0/schemas'),
    ]

    return LaunchDescription(args + sw_render + [OpaqueFunction(function=_launch_setup)])
