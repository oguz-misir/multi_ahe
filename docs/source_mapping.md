# AHE-MRTA Source Mapping Document

This document tracks which source MD file sections were used to make each implementation decision,
per phase. Updated after every phase.

---

## Phase 1 — Workspace, Package Skeleton, Custom Messages

### Source MD Files Inspected

| File | Role |
|------|------|
| `ahe_mrta_ana_md_q1_csv_first_updated.md` | PRIMARY source for all Phase 1 decisions |
| `ahe_mrta_recent_comparison_methods_compact.md` | READ for awareness only; NO implementation in Phase 1 |

### Sections Used from Main MD File

| Section | Heading | Decision Derived |
|---------|---------|-----------------|
| §6.1 | Ana yazılım yığını | Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, ros_gz, TurtleBot3 Waffle Pi, Python 3.12, rclpy, pandas, matplotlib |
| §6.2 | Önemli teknik uyarı | Use ros_gz Gazebo Harmonic APIs; no Gazebo Classic (gazebo_ros_pkgs) assumptions |
| §6.3 | Workspace yapısı | `multi_ahe/src/`, `logs/`, `results/`, `scripts/`, `README.md` top-level layout |
| §6.4 | Paket görevleri | Package names, package roles; normalized to `m_` prefix |
| §6.6 | Custom mesajlar | All 8 message definitions: TaskWaypoint, OptimizedTaskQueue, RobotStatusSummary, LocalExecutionFeedback, TaskInfo, TaskPool, AllocationEvent, EcosystemState |
| §11.1 | Dizin yapısı | `results/raw/`, `results/processed/`, `results/paper_figures/supplementary/`, `results/reports/` |
| §12.1 | Neden tek prompt ile başlanmamalı | Phase-by-phase strategy confirmed |
| §12.4 | Faz 1 | Phase 1 goal: workspace, packages, custom messages, build, `ros2 interface show` validation gate |
| §1.3 | AHE-MRTA katkı maddeleri | 5 core mechanisms documented: dominance, cooperation, suppression, context compatibility, event-triggered replanning |
| §4.1 | Strategy agent kavramı | 7 strategy agents named and documented in package descriptions |
| §4.3 | Context vector | 7-component context vector documented as future Phase 8 target |

### Acknowledgement: Comparison Methods MD Reserved

`ahe_mrta_recent_comparison_methods_compact.md` was read in full during Phase 1 to understand the
scope of BiG-MRTA, RoSTAM-EA, and Consensus-DBTA. No code from this file was implemented in Phase 1.
This file will be the primary source for Phase 9 baseline implementation.

The file defines:
- BiG-MRTA (Ghassemi & Chowdhury, RAS 2022): online weighted bipartite graph MRTA
- RoSTAM-EA (Arif & Haider, IDT 2024): self-adaptive evolutionary MRTA
- Consensus-DBTA (Mahato et al., RAS 2023): communication-efficient distributed bidding MRTA

### Package Name Normalization Decision

**Decision:** All packages are normalized to the `m_` prefix convention.

**Reason:** The main MD file (§6.3, §6.4) lists package names both with and without the `m_` prefix
in different sections (e.g., `ahe_task_manager` in §6.4 table vs. `m_ahe_task_manager` in §6.3 workspace tree).
The workspace directory name in §6.3 uses `m_` prefix. The prompt instruction explicitly specifies
the `m_` prefix as the canonical form.

| MD file name            | Normalized workspace name       | Normalization applied |
|-------------------------|--------------------------------|-----------------------|
| `ahe_mrta_msgs`         | `m_ahe_mrta_msgs`              | Yes |
| `ahe_mrta_bringup`      | `m_ahe_mrta_bringup`           | Yes |
| `ahe_mrta_gazebo`       | `m_ahe_mrta_gazebo`            | Yes |
| `ahe_task_manager`      | `m_ahe_task_manager`           | Yes |
| `ahe_robot_interface`   | `m_ahe_robot_interface`        | Yes |
| `ahe_ecosystem_manager` | `m_ahe_ecosystem_manager`      | Yes |
| `ahe_task_allocator`    | `m_ahe_task_allocator`         | Yes |
| `ahe_recovery_manager`  | `m_ahe_recovery_manager`       | Yes |
| `ahe_evaluation`        | `m_ahe_evaluation`             | Yes |
| `ahe_nav2_config`       | `m_ahe_nav2_config`            | Yes |

### Message Definition Source

All 8 message definitions come directly from §6.6 of `ahe_mrta_ana_md_q1_csv_first_updated.md`.
Field names, types, and field order are copied exactly as specified.

| Message file | Source section |
|---|---|
| `TaskWaypoint.msg` | §6.6 — TaskWaypoint.msg |
| `OptimizedTaskQueue.msg` | §6.6 — OptimizedTaskQueue.msg |
| `RobotStatusSummary.msg` | §6.6 — RobotStatusSummary.msg |
| `LocalExecutionFeedback.msg` | §6.6 — LocalExecutionFeedback.msg |
| `TaskInfo.msg` | §6.6 — TaskInfo.msg |
| `TaskPool.msg` | §6.6 — TaskPool.msg |
| `AllocationEvent.msg` | §6.6 — AllocationEvent.msg |
| `EcosystemState.msg` | §6.6 — EcosystemState.msg |

**Important note on EcosystemState:** The MD file (§6.6, §7.1) explicitly states this message is
for debug/offline evaluation only and must NOT be consumed by robot agents. This constraint is
documented in the package descriptions and will be enforced in Phase 8.

**Note on message referencing in OptimizedTaskQueue.msg and TaskPool.msg:**
The MD specifies `TaskWaypoint[]` and `TaskInfo[]` as array field types. In ROS 2 CMake message
generation these are referenced as `m_ahe_mrta_msgs/TaskWaypoint` and `m_ahe_mrta_msgs/TaskInfo`
because they are defined in the same package. The .msg files use the fully qualified package prefix
to satisfy rosidl_generate_interfaces dependency resolution.

### Files Created or Affected in Phase 1

```
multi_ahe/
├── README.md                                              [CREATED]
├── docs/
│   └── source_mapping.md                                 [CREATED]
├── scripts/                                               [CREATED - empty, reserved for Phase 9-10]
├── results/
│   ├── raw/                                              [CREATED - empty]
│   ├── processed/                                        [CREATED - empty]
│   ├── paper_figures/
│   │   └── supplementary/                                [CREATED - empty]
│   └── reports/                                          [CREATED - empty]
└── src/
    ├── m_ahe_mrta_msgs/
    │   ├── CMakeLists.txt                                [CREATED]
    │   ├── package.xml                                   [CREATED]
    │   └── msg/
    │       ├── TaskWaypoint.msg                          [CREATED]
    │       ├── OptimizedTaskQueue.msg                    [CREATED]
    │       ├── RobotStatusSummary.msg                    [CREATED]
    │       ├── LocalExecutionFeedback.msg                [CREATED]
    │       ├── TaskInfo.msg                              [CREATED]
    │       ├── TaskPool.msg                              [CREATED]
    │       ├── AllocationEvent.msg                       [CREATED]
    │       └── EcosystemState.msg                        [CREATED]
    ├── m_ahe_mrta_bringup/
    │   ├── CMakeLists.txt                                [CREATED]
    │   └── package.xml                                   [CREATED]
    ├── m_ahe_mrta_gazebo/
    │   ├── CMakeLists.txt                                [CREATED]
    │   └── package.xml                                   [CREATED]
    ├── m_ahe_task_manager/
    │   ├── package.xml                                   [CREATED]
    │   ├── setup.py                                      [CREATED]
    │   ├── setup.cfg                                     [CREATED]
    │   ├── resource/m_ahe_task_manager                   [CREATED]
    │   └── m_ahe_task_manager/__init__.py                [CREATED]
    ├── m_ahe_robot_interface/
    │   ├── package.xml                                   [CREATED]
    │   ├── setup.py                                      [CREATED]
    │   ├── setup.cfg                                     [CREATED]
    │   ├── resource/m_ahe_robot_interface                [CREATED]
    │   └── m_ahe_robot_interface/__init__.py             [CREATED]
    ├── m_ahe_ecosystem_manager/
    │   ├── package.xml                                   [CREATED]
    │   ├── setup.py                                      [CREATED]
    │   ├── setup.cfg                                     [CREATED]
    │   ├── resource/m_ahe_ecosystem_manager              [CREATED]
    │   └── m_ahe_ecosystem_manager/__init__.py           [CREATED]
    ├── m_ahe_task_allocator/
    │   ├── package.xml                                   [CREATED]
    │   ├── setup.py                                      [CREATED]
    │   ├── setup.cfg                                     [CREATED]
    │   ├── resource/m_ahe_task_allocator                 [CREATED]
    │   └── m_ahe_task_allocator/__init__.py              [CREATED]
    ├── m_ahe_recovery_manager/
    │   ├── package.xml                                   [CREATED]
    │   ├── setup.py                                      [CREATED]
    │   ├── setup.cfg                                     [CREATED]
    │   ├── resource/m_ahe_recovery_manager               [CREATED]
    │   └── m_ahe_recovery_manager/__init__.py            [CREATED]
    ├── m_ahe_evaluation/
    │   ├── package.xml                                   [CREATED]
    │   ├── setup.py                                      [CREATED]
    │   ├── setup.cfg                                     [CREATED]
    │   ├── resource/m_ahe_evaluation                     [CREATED]
    │   └── m_ahe_evaluation/__init__.py                  [CREATED]
    └── m_ahe_nav2_config/
        ├── CMakeLists.txt                                [CREATED]
        └── package.xml                                   [CREATED]
```

### Conflicts Detected

None in Phase 1. The MD file is internally consistent for the workspace structure,
package names (after normalization), and message definitions.

---

## Phase 2 — Message Test Nodes

### Source MD Files Used

| File | Role |
|------|------|
| `ahe_mrta_ana_md_q1_csv_first_updated.md` | §12.5 Faz 2 — node goals and validation commands |

### Sections Used

| Section | Decision |
|---------|----------|
| §12.5 | Four test nodes: TaskPool publisher, RobotStatusSummary publisher, OptimizedTaskQueue subscriber, EcosystemState debug publisher |
| §7.2 Topic table | Topic names confirmed: `/tasks/global_pool`, `/robot_1/status_summary`, `/robot_1/optimized_task_queue`, `/ecosystem/debug_state`, `/allocation/events`, `/robot_1/local_execution_feedback` |
| §6.6 + §7.1 | EcosystemState published to `/ecosystem/debug_state` only — NOT to any robot topic |
| §4.1 + §4.4 | 7 heuristic names and uniform D(0)=1/K initialization used in test node |
| §4.3 | 7-component context vector used as placeholder in test node |

### Decisions

- `task_pool_test_pub` placed in `m_ahe_task_manager` (correct package ownership for Phase 6)
- `robot_status_test_pub` placed in `m_ahe_robot_interface` (pub: status + feedback, sub: task queue)
- `task_queue_test_pub` placed in `m_ahe_task_allocator` (will be replaced by real allocator Phase 7)
- `ecosystem_test_pub` placed in `m_ahe_ecosystem_manager` (debug only — no robot consumption)
- Launch file: `m_ahe_mrta_bringup/launch/phase2_test_messages.launch.py`
- Daemon must be stopped and restarted with the correct environment before `ros2 topic echo` on custom messages works

### Files Created or Modified

```
src/m_ahe_task_manager/m_ahe_task_manager/task_pool_test_pub.py     [CREATED]
src/m_ahe_task_manager/setup.py                                      [MODIFIED — entry point added]
src/m_ahe_robot_interface/m_ahe_robot_interface/robot_status_test_pub.py [CREATED]
src/m_ahe_robot_interface/setup.py                                   [MODIFIED — entry point added]
src/m_ahe_ecosystem_manager/m_ahe_ecosystem_manager/ecosystem_test_pub.py [CREATED]
src/m_ahe_ecosystem_manager/setup.py                                 [MODIFIED — entry point added]
src/m_ahe_task_allocator/m_ahe_task_allocator/task_queue_test_pub.py [CREATED]
src/m_ahe_task_allocator/setup.py                                    [MODIFIED — entry point added]
src/m_ahe_mrta_bringup/launch/phase2_test_messages.launch.py         [CREATED]
```

---

## Phase 3 — Single Robot Gazebo Harmonic Spawn

### Source MD Files Used

| File | Role |
|------|------|
| `ahe_mrta_ana_md_q1_csv_first_updated.md` | §6.1, §6.2, §12.6 Faz 3 — robot model, Gazebo stack, headless requirement |

### Sections Used

| Section | Decision |
|---------|----------|
| §6.1 | TurtleBot3 Waffle Pi as the robot platform; Gazebo Harmonic via ros_gz |
| §6.2 | Use ros_gz (Harmonic) APIs only; no gazebo_ros_pkgs / Gazebo Classic |
| §12.6 | Phase 3 goal: single robot spawned in Gazebo, topics bridged to ROS 2 |

### Key Implementation Decisions

- **Self-contained SDF**: No `ros-jazzy-turtlebot3-*` packages installed; Waffle Pi geometry encoded directly in world SDF (`ahe_inspection_mvp.sdf`). Wheel radius=0.033 m, separation=0.287 m, chassis 0.266×0.266×0.094 m.
- **CPU lidar**: `type="lidar"` (not `gpu_lidar`) — WSL2 has no `/dev/dri`, no Vulkan. `gz-sim-sensors-system` plugin has no `<render_engine>` tag.
- **Headless**: `gz_args='-r -s {world_path}'` — `-s` is server-only (no GUI), required for WSL2.
- **Bridge YAML**: `config_file` parameter to `ros_gz_bridge parameter_bridge`; 6 topic pairs (cmd_vel, odom, scan, imu, tf, clock).
- **DiffDrive frame IDs**: `frame_id=odom`, `child_frame_id=robot_1/base_link` — prepares for multi-robot namespacing in Phase 4.
- **Validation gate**: `ros2 topic list | grep robot_1` shows 5 topics; `ros2 topic echo /robot_1/odom --once` returns live odometry with `frame_id: odom`.

### Files Created or Modified

```
src/m_ahe_mrta_gazebo/worlds/ahe_inspection_mvp.sdf        [CREATED]
src/m_ahe_mrta_gazebo/config/robot_1_bridge.yaml            [CREATED]
src/m_ahe_mrta_gazebo/CMakeLists.txt                        [MODIFIED — config/ install rule added]
src/m_ahe_mrta_bringup/launch/single_robot_gazebo.launch.py [CREATED]
```

### Validation Results

```
ros2 topic list | grep robot_1
  /robot_1/cmd_vel
  /robot_1/imu
  /robot_1/odom
  /robot_1/scan
  (plus /tf, /clock bridged without robot_1 prefix)

ros2 topic echo /robot_1/odom --once
  header.frame_id: odom
  child_frame_id: robot_1/base_link
  position: {x≈0, y≈0, z=0}  — robot stationary at origin ✓
```

---

## Phase 4 — Üç Robot Namespace ve TF Ayrımı

### Kullanılan Kaynak MD Dosyaları

| Dosya | Rol |
|-------|-----|
| `ahe_mrta_ana_md_q1_csv_first_updated.md` | §12.7 Faz 4 — namespace yapısı, TF frame ayrımı, doğrulama kriterleri |

### Kullanılan Bölümler

| Bölüm | Karar |
|-------|-------|
| §12.7 | robot_1, robot_2, robot_3 ayrı namespace; odom/scan/cmd_vel/TF ayrımı |
| §14.4 | Faz 4 prompt: 3 robot, namespace kullanımı, TF frame çakışmasından kaçınma |

### Temel Uygulama Kararları

- **SDF güncellendi**: `ahe_inspection_mvp.sdf` dosyasına robot_2 (y=+2.0m) ve robot_3 (y=-2.0m) eklendi.
- **robot_1 TF frame düzeltildi**: Faz 3'te `frame_id=odom` olarak ayarlıydı; çok-robot TF çakışmasını önlemek için `frame_id=robot_1/odom` olarak güncellendi.
- **Her robotun frame yapısı**: `robot_N/odom → robot_N/base_link` — `/tf` topic'e çakışmadan yayınlanıyor.
- **Renk ayrımı**: robot_1=mavi, robot_2=yeşil, robot_3=kırmızı (debug görselleştirmesi için).
- **all_robots_bridge.yaml**: 3 robot × 5 topic + clock = 16 köprü girişi; 3 TF köprüsü de aynı `/tf` ROS topic'e akıyor (frame isimleri çakışmayı engeller).
- **Yeni launch dosyası**: `multi_robot_gazebo.launch.py` — aynı SDF, yeni bridge config.

### Oluşturulan veya Değiştirilen Dosyalar

```
src/m_ahe_mrta_gazebo/worlds/ahe_inspection_mvp.sdf        [GÜNCELLENDI — robot_2 ve robot_3 eklendi, robot_1 frame_id düzeltildi]
src/m_ahe_mrta_gazebo/config/all_robots_bridge.yaml        [OLUŞTURULDU]
src/m_ahe_mrta_bringup/launch/multi_robot_gazebo.launch.py [OLUŞTURULDU]
```

### Doğrulama Sonuçları

```
ros2 topic list | grep robot_1  →  /robot_1/cmd_vel  /robot_1/imu  /robot_1/odom  /robot_1/scan  ✓
ros2 topic list | grep robot_2  →  /robot_2/cmd_vel  /robot_2/imu  /robot_2/odom  /robot_2/scan  ✓
ros2 topic list | grep robot_3  →  /robot_3/cmd_vel  /robot_3/imu  /robot_3/odom  /robot_3/scan  ✓

ros2 topic echo /robot_2/odom --once
  frame_id: robot_2/odom  child_frame_id: robot_2/base_link  ✓

ros2 topic echo /robot_3/odom --once
  frame_id: robot_3/odom  child_frame_id: robot_3/base_link  ✓
```

---

## Phase 5 — (Reserved)

---

## Phase 6 — (Reserved)

---

## Phase 7 — (Reserved)

---

## Phase 8 — (Reserved)

---

## Phase 9 — (Reserved)
Source: `ahe_mrta_recent_comparison_methods_compact.md` will be primary source for
BiG-MRTA, RoSTAM-EA, Consensus-DBTA implementations.

---

## Phase 10 — (Reserved)
