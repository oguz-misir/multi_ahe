# AHE-MRTA: Adaptive Heuristic Ecosystem for Robust Online Multi-Robot Task Allocation

## Implementation Approach

All source code in this workspace is implemented by **Claude Code** (`claude-sonnet-4-6`).
Dr. Oğuz Mışır provides the architectural specification, validation requirements, and
research direction. Claude Code writes all ROS 2 nodes, launch files, configuration files,
experiment scripts, and analysis code. The user runs and validates; Claude Code implements.

---

## Project Purpose

AHE-MRTA is a RA-L/Q1-level research prototype for **explainable, lightweight, communication-efficient**
online multi-robot task allocation (MRTA) under dynamic tasks, robot failures, deadlines, congestion,
and battery stress.

The core novelty is **not** a new single heuristic and **not** adaptive weighting.
AHE-MRTA models known MRTA heuristics as interacting ecological strategy agents with:

- **Dominance vector** — tracks which heuristic strategy is currently most effective
- **Cooperation matrix** — models which strategies reinforce each other
- **Suppression matrix** — models which strategies inhibit each other
- **Context vector** — captures the current mission state (task density, battery risk, deadline pressure, etc.)
- **Context compatibility** — measures how well each strategy fits the current context
- **Event-triggered replanning** — replanning occurs only on significant events (robot failure, deadline risk, battery critical, goal unreachable), not continuously

This is an adaptive heuristic ecosystem, not a fixed or dynamically weighted task allocator.

---

## Requirements

| Component        | Version / Spec             |
|------------------|---------------------------|
| OS               | Ubuntu 24.04 LTS           |
| ROS 2            | Jazzy                      |
| Gazebo           | Harmonic (ros_gz, NOT Gazebo Classic APIs) |
| Navigation       | Nav2                       |
| Robot model      | TurtleBot3 Waffle Pi       |
| Python           | 3.12                       |
| ROS client lib   | rclpy                      |
| Data analysis    | pandas, matplotlib         |

---

## Workspace Build

```bash
cd ~/multi_ahe
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

---

## Interface Validation (Phase 1 Gate)

After building, verify all custom messages:

```bash
source install/setup.bash

ros2 interface show m_ahe_mrta_msgs/msg/TaskWaypoint
ros2 interface show m_ahe_mrta_msgs/msg/OptimizedTaskQueue
ros2 interface show m_ahe_mrta_msgs/msg/RobotStatusSummary
ros2 interface show m_ahe_mrta_msgs/msg/LocalExecutionFeedback
ros2 interface show m_ahe_mrta_msgs/msg/TaskInfo
ros2 interface show m_ahe_mrta_msgs/msg/TaskPool
ros2 interface show m_ahe_mrta_msgs/msg/AllocationEvent
ros2 interface show m_ahe_mrta_msgs/msg/EcosystemState
```

---

## Package Overview

| Package                    | Role                                                                 | Status     |
|---------------------------|----------------------------------------------------------------------|------------|
| `m_ahe_mrta_msgs`         | Custom ROS 2 message definitions                                     | Phase 1    |
| `m_ahe_mrta_bringup`      | Launch files for all scenarios                                        | Phase 3+   |
| `m_ahe_mrta_gazebo`       | Gazebo Harmonic world, robot spawn, target markers (ros_gz)          | Phase 3    |
| `m_ahe_task_manager`      | Task pool, dynamic task activation, task state tracking              | Phase 6    |
| `m_ahe_robot_interface`   | Robot status, Nav2 action client, local execution feedback           | Phase 6    |
| `m_ahe_ecosystem_manager` | Context vector, dominance, cooperation, suppression, weight gen      | Phase 8    |
| `m_ahe_task_allocator`    | Cost matrix, task allocation, sequence optimization, baselines       | Phase 7+   |
| `m_ahe_recovery_manager`  | Failure detection, event-triggered replanning                        | Phase 8    |
| `m_ahe_evaluation`        | CSV-first event logging, consolidation, post-run analysis            | Phase 9    |
| `m_ahe_nav2_config`       | Per-robot Nav2 parameter YAML files (TurtleBot3 Waffle Pi)           | Phase 5    |

---

## Package Name Normalization

The source MD files (`ahe_mrta_ana_md_q1_csv_first_updated.md`) use package names **without** the `m_`
prefix in some sections (e.g., `ahe_task_manager`, `ahe_mrta_msgs`). All packages in this workspace
are normalized to the `m_` prefix convention:

| MD file name            | Normalized workspace name       |
|-------------------------|--------------------------------|
| `ahe_mrta_msgs`         | `m_ahe_mrta_msgs`              |
| `ahe_mrta_bringup`      | `m_ahe_mrta_bringup`           |
| `ahe_mrta_gazebo`       | `m_ahe_mrta_gazebo`            |
| `ahe_task_manager`      | `m_ahe_task_manager`           |
| `ahe_robot_interface`   | `m_ahe_robot_interface`        |
| `ahe_ecosystem_manager` | `m_ahe_ecosystem_manager`      |
| `ahe_task_allocator`    | `m_ahe_task_allocator`         |
| `ahe_recovery_manager`  | `m_ahe_recovery_manager`       |
| `ahe_evaluation`        | `m_ahe_evaluation`             |
| `ahe_nav2_config`       | `m_ahe_nav2_config`            |

This normalization is documented in `docs/source_mapping.md`.

---

## Phased Implementation

Implementation proceeds phase by phase. Each phase has a validation gate before the next begins.

| Phase | Goal                                                        | Status |
|-------|-------------------------------------------------------------|--------|
| 1     | Workspace, packages, custom messages                        | ✅ Done |
| 2     | Message test publisher/subscriber nodes                     | ✅ Done |
| 3     | Single robot Gazebo Harmonic spawn                          | ✅ Done |
| 4     | Multi-robot namespace and TF separation                     | ✅ Done |
| 5     | Nav2 integration and manual NavigateToPose test             | ✅ Done |
| 6     | Task Manager + Robot Interface                              | ✅ Done |
| 7     | Minimum baseline allocator (greedy, static weighted)        | ✅ Done |
| 8     | Full AHE-MRTA: dominance, cooperation, suppression, weights, replanning | ✅ Done |
| 9     | All experiments: baselines, comparison methods, ablations   | ✅ Done |
| 10    | Paper figures and statistical tables from CSV               | ✅ Done |
| 11    | Gazebo demo arena, GUI launch, visual validation            | ✅ Done |
| 12    | Gazebo real experiment batch runner                         | ✅ Done |
| 13    | ROBOTIS TurtleBot3 model, RViz+Gazebo path/target viz, PNG export | ✅ Done |

---

## Visualization (Phase 13)

### RViz — Full 3D View
`phase9_demo.rviz` shows:
- **RobotModel** (×3) — official ROBOTIS TurtleBot3 Waffle Pi meshes via `turtlebot3_description`
- **Path** (×3) — Nav2 planned path per robot (`/robot_N/plan`)
- **MarkerArray** — task targets with status colour coding (pending/active/assigned/completed/failed)

### Gazebo — Path + Target Markers
`gz_path_visualizer_node` publishes `/visualization/gz` (MarkerArray) bridged → Gazebo `/marker_array`:
- LINE_STRIP per robot (blue/green/red)
- Cylinder markers per task target (colour = status)

`GZ_SIM_RESOURCE_PATH=/opt/ros/humble/share/turtlebot3_gazebo/models` → enables ROBOTIS STL meshes for robot bodies.

### Per-Experiment PNG Export
```bash
python3 scripts/export_experiment_pngs.py \
    --raw-dir results/raw/gazebo \
    --output-dir results/paper_figures/trajectories
```
Outputs one PNG per experiment under:
- `trajectories/baseline/` — SW, BiG-MRTA, RoSTAM-EA, AHE-MRTA*
- `trajectories/ablation/` — AHE-NoD, AHE-NoER, AHE-FC, AHE-MRTA*
- `trajectories/all/`      — all other strategies

### Demo
```bash
ros2 launch m_ahe_mrta_bringup phase9_demo.launch.py \
    strategy:=full_ahe_mrta scenario:=robot_failure seed:=1
```

---

## Comparison Baselines (Phase 9)

Comparison baseline methods (BiG-MRTA, RoSTAM-EA, Consensus-DBTA) will be implemented in Phase 9,
using the supplementary document:

```
ahe_mrta_recent_comparison_methods_compact.md
```

Classical baselines (greedy_nearest, static_weighted, deadline_aware) will be implemented in Phase 7.

---

## AHE-MRTA Core Constraint

The AHE-MRTA implementation must preserve all five core mechanisms:

1. **Dominance** — heuristic performance-driven dominance update
2. **Cooperation** — inter-heuristic reinforcement via cooperation matrix A
3. **Suppression** — inter-heuristic inhibition via suppression matrix S
4. **Context compatibility** — each heuristic is scored against the current context vector
5. **Event-triggered replanning** — replanning on failure, deadline risk, battery critical, goal unreachable

AHE-MRTA must NOT be reduced to adaptive weighting only.

---

## Results Directory Structure

```
results/
├── raw/                        # Per-experiment event CSV files
│   └── exp_<scenario>_<method>_seed<seed>/
│       ├── metadata.yaml
│       ├── task_events.csv
│       ├── robot_state_timeseries.csv
│       ├── robot_workload.csv
│       ├── allocation_events.csv
│       ├── method_runtime.csv
│       ├── communication_metrics.csv
│       ├── ecosystem_metrics.csv   # AHE runs only
│       └── summary.csv
├── processed/                  # Consolidated CSVs (post-run)
├── paper_figures/              # PNG figures (300 dpi, post-run only)
│   └── supplementary/
└── reports/                    # Statistical tables and summary report
```
