"""multi_robot_helpers — utilities for parametric N-robot launch (v3).

Reads the canonical 3-robot world SDF and bridge config, then synthesizes a
fresh SDF + bridge YAML for an arbitrary robot_count in [1, 15] at launch time.

The original SDF contains three fully-inlined TurtleBot3 Waffle Pi blocks
(robot_1 .. robot_3). robot_1 is treated as the canonical template; robot_2
and robot_3 blocks are stripped, and N robot blocks are emitted with computed
spawn positions and namespace-substituted topic/frame strings.

Spawn layout (Y-axis fan-out, X = -9 for one row, two rows for N > 8):
  N=3  : y = {0.0, 2.0, -2.0}                                  (legacy)
  N=5  : y = {-4.0, -2.0, 0.0, 2.0, 4.0}                       (x = -9)
  N=10 : y = {-4.5, -3.5, -2.5, ..., 4.5}                      (x = -9)
  N=15 : y = {-4.0, -2.0, 0.0, 2.0, 4.0} per row              (x = {-9, -8, -7})

Min inter-robot distance ≥ 1.0 m (robot footprint 0.22 m radius + clearance).
"""

import os
import re
from typing import List, Tuple


def compute_spawn_positions(n: int) -> List[Tuple[float, float]]:
    """Return list of (x, y) spawn positions for N robots in arena.

    Single source of truth: delegates to the obstacle-aware placement module
    (m_ahe_task_allocator.placement.robot_spawns), so the Gazebo SDF spawn and
    the navigation-independent SIM use identical, map-validated positions.
    A local fallback (the same left-centre column layout) is used if the
    package is not importable (e.g. tooling outside a sourced workspace).
    """
    try:
        from m_ahe_task_allocator.placement import robot_spawns
        return [tuple(p) for p in robot_spawns(n)]
    except Exception:
        pass

    # --- Fallback: left-centre columns at x = -4, -3, -2; y = {-4..4} ---
    if n <= 0:
        return []
    if n == 1:
        return [(-4.0, 0.0)]
    if n == 2:
        return [(-4.0, 1.0), (-4.0, -1.0)]
    if n == 3:
        return [(-4.0, 0.0), (-4.0, 2.0), (-4.0, -2.0)]
    ys = [-4.0, -2.0, 0.0, 2.0, 4.0]
    if n <= 5:
        return [(-4.0, y) for y in ys[:n]]
    if n <= 10:
        return [(-4.0, y) for y in ys] + [(-3.0, y) for y in ys[: n - 5]]
    if n <= 15:
        return ([(-4.0, y) for y in ys] + [(-3.0, y) for y in ys]
                + [(-2.0, y) for y in ys[: n - 10]])
    raise ValueError(f'robot_count={n} not supported (max 15)')


def robot_namespaces(n: int) -> List[str]:
    """Return canonical namespace list robot_1 .. robot_N."""
    return [f'robot_{i}' for i in range(1, n + 1)]


def generate_world_sdf(template_sdf_path: str, n_robots: int, output_path: str) -> str:
    """Generate a world SDF with N robots derived from the robot_1 template.

    Strategy:
      1. Read template SDF (canonical 3-robot world).
      2. Locate robot_1 .. robot_3 model blocks by name attribute.
      3. Extract robot_1's text as the template.
      4. Remove robot_2, robot_3 blocks entirely.
      5. Re-insert N robot blocks (namespace + pose substitution) at the same spot.
      6. Write the resulting SDF to output_path.

    Returns output_path.
    """
    with open(template_sdf_path) as f:
        sdf = f.read()

    # Locate robot model blocks by name="robot_N"
    # Each block: <model name="robot_N">  ...  </model>
    def find_block(name: str) -> Tuple[int, int]:
        start_pat = re.compile(rf'(    )?<model name="{name}">')
        m = start_pat.search(sdf)
        if not m:
            return -1, -1
        block_start = m.start()
        # Find matching </model> at the same indent (4 spaces typical)
        end_pat = re.compile(r'    </model>')
        end_m = end_pat.search(sdf, m.end())
        if not end_m:
            return -1, -1
        return block_start, end_m.end()

    s1, e1 = find_block('robot_1')
    s2, e2 = find_block('robot_2')
    s3, e3 = find_block('robot_3')

    if s1 < 0:
        raise RuntimeError(f'robot_1 model block not found in {template_sdf_path}')

    template_block = sdf[s1:e1]

    # Also capture any header comment immediately above robot_1 (the "ROBOT_1 — ..." comment)
    # We'll generate fresh comments for each robot, so strip the existing one
    # from the segment immediately preceding robot_1 in the output.
    # Header comment lives between "</model>" of preceding model and "<model name=\"robot_1\">"
    # We'll keep everything up to s1, then drop the immediately preceding 5-line comment block.
    head_text = sdf[:s1]
    head_text = re.sub(
        r'\n\s*<!-- =+\s*\n\s*ROBOT_1.*?-->\s*\n', '\n', head_text, flags=re.DOTALL
    )

    # Tail starts after the LAST robot block (robot_3 if present, else robot_1)
    tail_start = max(e1, e2, e3)
    tail_text = sdf[tail_start:]

    # Generate N robot blocks
    positions = compute_spawn_positions(n_robots)
    blocks: List[str] = []
    for idx, (x, y) in enumerate(positions, start=1):
        name = f'robot_{idx}'
        block = template_block
        # Replace name attribute and ALL textual robot_1 → robot_N occurrences inside the block
        block = block.replace('"robot_1"', f'"{name}"')
        block = block.replace('robot_1/', f'{name}/')
        block = block.replace('/robot_1/', f'/{name}/')
        block = block.replace('/model/robot_1/', f'/model/{name}/')
        # Replace pose line: <pose>X Y Z R P Y</pose>
        block = re.sub(
            r'<pose>[^<]+</pose>',
            f'<pose>{x:.3f} {y:.3f} 0.033 0 0 0</pose>',
            block,
            count=1,
        )
        header = (
            f'    <!-- ============================================================\n'
            f'         {name.upper()} — TurtleBot3 Waffle Pi at ({x:.2f}, {y:.2f})\n'
            f'         frame_id: {name}/odom  child: {name}/base_link\n'
            f'         ============================================================ -->\n'
        )
        blocks.append(header + block)

    out_sdf = head_text + '\n'.join(blocks) + tail_text
    with open(output_path, 'w') as f:
        f.write(out_sdf)
    return output_path


# Bridge YAML template per-robot block (4 topics: cmd_vel, odom, scan, imu)
# NOTE: /model/robot_N/tf is intentionally omitted — odom_to_tf node handles
# the odom→base_link TF at current sim time. Bridging the gz TF would cause
# TF_OLD_DATA conflicts because the bridge queues and replays old timestamps.
_BRIDGE_HEADER = """# Bridge config — auto-generated for {n} robots + clock
# /clock MUST be first so Nav2 sim_time is stable before any TF data arrives.

# --- shared clock (FIRST) ---
- ros_topic_name: /clock
  gz_topic_name: /clock
  ros_type_name: rosgraph_msgs/msg/Clock
  gz_type_name: gz.msgs.Clock
  direction: GZ_TO_ROS
"""

_BRIDGE_ROBOT_BLOCK = """
# --- robot_{i} ---
- ros_topic_name: /robot_{i}/cmd_vel
  gz_topic_name: /model/robot_{i}/cmd_vel
  ros_type_name: geometry_msgs/msg/Twist
  gz_type_name: gz.msgs.Twist
  direction: ROS_TO_GZ

- ros_topic_name: /robot_{i}/odom
  gz_topic_name: /model/robot_{i}/odometry
  ros_type_name: nav_msgs/msg/Odometry
  gz_type_name: gz.msgs.Odometry
  direction: GZ_TO_ROS

- ros_topic_name: /robot_{i}/scan
  gz_topic_name: /model/robot_{i}/scan
  ros_type_name: sensor_msgs/msg/LaserScan
  gz_type_name: gz.msgs.LaserScan
  direction: GZ_TO_ROS

- ros_topic_name: /robot_{i}/imu
  gz_topic_name: /model/robot_{i}/imu
  ros_type_name: sensor_msgs/msg/Imu
  gz_type_name: gz.msgs.IMU
  direction: GZ_TO_ROS

- ros_topic_name: /robot_{i}/joint_states
  gz_topic_name: /model/robot_{i}/joint_states
  ros_type_name: sensor_msgs/msg/JointState
  gz_type_name: gz.msgs.Model
  direction: GZ_TO_ROS
"""


def generate_bridge_yaml(n_robots: int, output_path: str) -> str:
    """Generate ros_gz bridge YAML covering /clock + N robots."""
    out = _BRIDGE_HEADER.format(n=n_robots)
    for i in range(1, n_robots + 1):
        out += _BRIDGE_ROBOT_BLOCK.format(i=i)
    with open(output_path, 'w') as f:
        f.write(out)
    return output_path
