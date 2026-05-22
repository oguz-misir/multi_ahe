"""
Phase 9 launch — Comparative experiment runner.

Starts the full simulation layer (Gazebo + Nav2 + Robot Interfaces) plus the
EcosystemManager and a single ExperimentRunnerNode configured via launch arguments.

ExperimentRunnerNode replaces both task_manager_node and the per-phase allocator.
It owns the full experiment lifecycle: task generation, allocation, CSV logging, and
graceful shutdown after the 360-second timeout.

Launch arguments
----------------
strategy    : allocator to run (default: full_ahe_mrta)
              choices: greedy_nearest | deadline_aware | auction_based | static_weighted |
                       big_mrta | rostam_ea | consensus_dbta | full_ahe_mrta |
                       ahe_no_dominance | ahe_no_cooperation_suppression |
                       ahe_no_event_replanning | ahe_fixed_context
scenario    : experiment scenario (default: dynamic_task_arrival)
              choices: dynamic_task_arrival | deadline_pressure | robot_failure | mixed_stress
seed        : RNG seed for reproducibility (default: 42)
robot_count : number of robots to use (default: 3)
task_count  : total tasks to generate (default: 15)
results_dir : base directory for CSV output (default: ~/multi_ahe/results/raw/phase9)

Typical usage
-------------
  ros2 launch m_ahe_mrta_bringup phase9_experiments.launch.py \\
      strategy:=full_ahe_mrta scenario:=robot_failure seed:=1

  ros2 launch m_ahe_mrta_bringup phase9_experiments.launch.py \\
      strategy:=rostam_ea scenario:=deadline_pressure seed:=1

Outputs (inside results_dir/experiment_<id>/)
----------------------------------------------
  metadata.yaml            — experiment configuration
  task_events.csv          — per-task lifecycle timestamps
  robot_state_timeseries.csv — per-robot state at each allocation tick
  robot_workload.csv       — final workload summary per robot
  allocation_events.csv    — every allocation decision with latency
  method_runtime.csv       — per-call allocator timing
  communication_metrics.csv — communication footprint per round
  ecosystem_metrics.csv    — AHE dominance / context (if applicable)
  summary.csv              — scalar KPIs for cross-experiment comparison

Security note
-------------
/ecosystem/debug_state is consumed ONLY by ecosystem_manager_node and
experiment_runner_node (both central nodes). It is NEVER forwarded to robots.
Robots receive ONLY /robot_N/optimized_task_queue.
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

_DEFAULT_RESULTS = os.path.expanduser('~/multi_ahe/results/raw/phase9')


def generate_launch_description() -> LaunchDescription:
    bringup = get_package_share_directory('m_ahe_mrta_bringup')

    # ------------------------------------------------------------------
    # Launch arguments
    # ------------------------------------------------------------------
    args = [
        DeclareLaunchArgument('strategy',    default_value='full_ahe_mrta'),
        DeclareLaunchArgument('scenario',    default_value='dynamic_task_arrival'),
        DeclareLaunchArgument('seed',        default_value='42'),
        DeclareLaunchArgument('robot_count', default_value='3'),
        DeclareLaunchArgument('task_count',  default_value='15'),
        DeclareLaunchArgument('results_dir', default_value=_DEFAULT_RESULTS),
        DeclareLaunchArgument('startup_delay', default_value='120.0',
                              description='Seconds to wait for Nav2 init before starting experiment'),
    ]

    sw_render = [
        SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe'),
    ]

    # ------------------------------------------------------------------
    # Simulation layer: Gazebo + Nav2 + Robot Interfaces
    # ------------------------------------------------------------------
    robots_nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, 'launch', 'robots_and_nav2.launch.py')
        ),
        launch_arguments={'robot_count': LaunchConfiguration('robot_count')}.items(),
    )

    # ------------------------------------------------------------------
    # Ecosystem Manager — computes D(t), W(t), publishes /ecosystem/debug_state
    # Only experiment_runner_node reads this topic (not the robots).
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Experiment Runner — task generation + allocation + CSV logging
    # ------------------------------------------------------------------
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
