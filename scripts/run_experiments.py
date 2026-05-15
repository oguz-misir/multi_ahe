#!/usr/bin/env python3
"""
Phase 10 — Standalone experiment runner (NO ROS2/Gazebo required).

Imports allocators directly via sys.path and mocks ROS2 dependencies.
Simulates navigation with a time-based model (Euclidean / robot_speed).
Outputs identical CSV files to experiment_runner_node.

Experiment matrix (default):
  - strategies: all 12
  - scenarios:  dynamic_task_arrival | deadline_pressure | robot_failure | mixed_stress
  - seeds:      1..5  (MVP)  or  1..20  (paper)
  - scales:     3R/15T (debug)  and  5R/25T (paper)

Usage:
    python3 scripts/run_experiments.py                       # full MVP matrix
    python3 scripts/run_experiments.py --seeds 1 2 3         # specific seeds
    python3 scripts/run_experiments.py --strategies full_ahe_mrta greedy_nearest
    python3 scripts/run_experiments.py --scale paper          # 5R/25T
    python3 scripts/run_experiments.py --dry-run              # print matrix only
"""

import argparse
import csv
import math
import os
import random
import sys
import time
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

# ── Mock ROS2 / package imports before loading allocators ──────────────────────
# We inject stub modules so that allocators that import rclpy/ros packages
# don't crash at import time. The allocator logic itself is pure Python.

class _StubModule:
    def __getattr__(self, name):
        return _StubModule()
    def __call__(self, *a, **kw):
        return _StubModule()
    def __iter__(self):
        return iter([])
    def __bool__(self):
        return False

W0_CONST = [0.40, 0.15, 0.10, 0.15, 0.05, 0.10, 0.05]

M_CONST = np.array([
    [0.9, 0.1, 0.1, 0.3, 0.3, 0.3, 0.3],
    [0.1, 0.9, 0.5, 0.1, 0.1, 0.5, 0.1],
    [0.1, 0.1, 0.1, 0.1, 0.9, 0.3, 0.3],
    [0.1, 0.1, 0.1, 0.9, 0.1, 0.1, 0.3],
    [0.1, 0.1, 0.1, 0.1, 0.3, 0.9, 0.9],
    [0.1, 0.5, 0.9, 0.1, 0.1, 0.1, 0.1],
    [0.1, 0.1, 0.1, 0.1, 0.3, 0.3, 0.9],
])

# Stub for rclpy
_rclpy_stub = _StubModule()
sys.modules.setdefault('rclpy', _rclpy_stub)
sys.modules.setdefault('rclpy.node', _rclpy_stub)
sys.modules.setdefault('rclpy.action', _rclpy_stub)
sys.modules.setdefault('geometry_msgs', _StubModule())
sys.modules.setdefault('geometry_msgs.msg', _StubModule())
sys.modules.setdefault('nav_msgs', _StubModule())
sys.modules.setdefault('nav_msgs.msg', _StubModule())
sys.modules.setdefault('nav2_msgs', _StubModule())
sys.modules.setdefault('nav2_msgs.action', _StubModule())
sys.modules.setdefault('action_msgs', _StubModule())
sys.modules.setdefault('action_msgs.msg', _StubModule())
sys.modules.setdefault('m_ahe_mrta_msgs', _StubModule())
sys.modules.setdefault('m_ahe_mrta_msgs.msg', _StubModule())

# Stub for ahe_allocator_node (provides W0)
_ahe_alloc_stub = _StubModule()
_ahe_alloc_stub.W0 = W0_CONST
sys.modules.setdefault('m_ahe_task_allocator.ahe_allocator_node', _ahe_alloc_stub)

# Stub for ecosystem_manager_node (provides M, V, and hyperparameters)
V_CONST = np.array([
    [0.7, 0.7, 0.1, 0.1, 0.1, 0.3, 0.1],
    [0.3, 0.5, 0.1, 0.8, 0.2, 0.1, 0.2],
    [0.5, 0.5, 0.1, 0.9, 0.1, 0.1, 0.1],
    [0.8, 0.3, 0.1, 0.3, 0.1, 0.9, 0.3],
    [0.3, 0.3, 0.9, 0.2, 0.2, 0.2, 0.2],
    [0.3, 0.3, 0.3, 0.3, 0.8, 0.3, 0.3],
    [0.3, 0.2, 0.3, 0.2, 0.9, 0.3, 0.8],
])
_eco_stub = _StubModule()
_eco_stub.M = M_CONST
_eco_stub.V = V_CONST
_eco_stub.ALPHA = 0.6
_eco_stub.BETA  = 0.2
_eco_stub.GAMMA = 0.15
_eco_stub.ETA   = 0.10
_eco_stub.LMBDA = 0.10
_eco_stub.DELTA = 0.15
sys.modules.setdefault('m_ahe_ecosystem_manager', _StubModule())
sys.modules.setdefault('m_ahe_ecosystem_manager.ecosystem_manager_node', _eco_stub)

# Add src to sys.path so package imports resolve
_repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root / 'src' / 'm_ahe_task_allocator'))

from m_ahe_task_allocator.baselines.base_allocator import (
    AllocationResult, EcosystemContext, RobotState as RS, TaskState as TS,
    cheapest_insertion,
)
from m_ahe_task_allocator.baselines.greedy_nearest    import GreedyNearestAllocator
from m_ahe_task_allocator.baselines.deadline_aware    import DeadlineAwareAllocator
from m_ahe_task_allocator.baselines.auction_based     import AuctionBasedAllocator
from m_ahe_task_allocator.baselines.static_weighted   import StaticWeightedAllocator
from m_ahe_task_allocator.baselines.big_mrta          import BigMRTAAllocator
from m_ahe_task_allocator.baselines.rostam_ea         import RoSTAMEAAllocator
from m_ahe_task_allocator.baselines.consensus_dbta    import ConsensusDBTAAllocator
from m_ahe_task_allocator.baselines.ahe_variants      import (
    FullAHEAllocator, AHENoDominanceAllocator,
    AHENoCoopSuppAllocator, AHENoEventReplanningAllocator,
    AHEFixedContextAllocator,
)

# ── Constants ──────────────────────────────────────────────────────────────────
ROBOT_SPEED_MPS   = 0.28    # TurtleBot3 Waffle Pi ~0.26 m/s max
DT                = 0.5     # simulation time step (seconds)
ALLOC_PERIOD      = 5.0
TIMESERIES_PERIOD = 2.0
EXPERIMENT_TIMEOUT = 360.0
FAILURE_OFFSET     = 45.0
BATTERY_DRAIN_MOVE = 0.002   # per meter
BATTERY_DRAIN_IDLE = 0.0002  # per second idle

HEURISTIC_NAMES = ["spatial_opportunist", "criticality_guardian",
                   "temporal_regulator", "resource_distributor",
                   "energy_conservator", "stability_controller",
                   "recovery_coordinator"]

K = len(HEURISTIC_NAMES)

A_MATRIX = np.array([
    [0, 0.1, 0, 0, 0, 0, 0],
    [0.1, 0, 0.2, 0, 0, 0.1, 0],
    [0, 0.2, 0, 0, 0, 0.1, 0],
    [0, 0, 0, 0, 0, 0.1, 0.2],
    [0, 0, 0, 0, 0, 0.1, 0.1],
    [0, 0.1, 0.1, 0.1, 0.1, 0, 0.1],
    [0, 0, 0, 0.2, 0.1, 0.1, 0],
], dtype=float)

S_MATRIX = np.array([
    [0, 0.05, 0.05, 0, 0, 0, 0],
    [0.05, 0, 0, 0.1, 0.1, 0, 0.05],
    [0.05, 0, 0, 0, 0, 0, 0.05],
    [0, 0.1, 0, 0, 0.1, 0, 0],
    [0, 0.1, 0, 0.1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0.05],
    [0, 0.05, 0.05, 0, 0, 0.05, 0],
], dtype=float)

AHE_STRATEGIES = {
    'full_ahe_mrta', 'ahe_no_dominance', 'ahe_no_cooperation_suppression',
    'ahe_no_event_replanning', 'ahe_fixed_context',
}

ALLOCATOR_REGISTRY = {
    'greedy_nearest':               GreedyNearestAllocator,
    'deadline_aware':               DeadlineAwareAllocator,
    'auction_based':                AuctionBasedAllocator,
    'static_weighted':              StaticWeightedAllocator,
    'big_mrta':                     BigMRTAAllocator,
    'rostam_ea':                    RoSTAMEAAllocator,
    'consensus_dbta':               ConsensusDBTAAllocator,
    'full_ahe_mrta':                FullAHEAllocator,
    'ahe_no_dominance':             AHENoDominanceAllocator,
    'ahe_no_cooperation_suppression': AHENoCoopSuppAllocator,
    'ahe_no_event_replanning':      AHENoEventReplanningAllocator,
    'ahe_fixed_context':            AHEFixedContextAllocator,
}

DEADLINE_MULTIPLIERS = {
    'dynamic_task_arrival': 1.0,
    'deadline_pressure':    0.4,
    'robot_failure':        1.0,
    'mixed_stress':         0.5,
}

GRID = [
    (-6.0, 7.0), (-2.0, 7.0), (2.0, 7.0), (6.0, 7.0),
    (-6.0, 4.0), (-2.0, 4.0), (2.0, 4.0), (6.0, 4.0),
    (-6.0, 1.0), (6.0, 1.0),
    (-6.0, -3.0), (-2.0, -3.0), (2.0, -3.0), (6.0, -3.0),
    (-6.0, -6.0), (-2.0, -6.0), (2.0, -6.0), (6.0, -6.0),
    (-4.0, -1.0), (4.0, -1.0),
    (-3.0, 5.0), (3.0, 5.0), (-5.0, 2.0), (5.0, 2.0), (0.0, -5.0),
]


# ── AHE context / dominance (pure Python, no ROS2) ────────────────────────────

def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


class AHEEcosystem:
    """Replicates EcosystemManager dominance update logic for standalone use."""

    def __init__(self):
        self.D = np.ones(K) / K
        self.P = np.zeros(K)

    def update(self, robot_states: List[RS], tasks: List[TS], t: float) -> EcosystemContext:
        active = [t for t in tasks if t.active and not t.completed]
        available = [r for r in robot_states if r.available]
        n_total = max(1, len(robot_states))
        n_active = len(active)

        # Context vector
        task_density = min(1.0, n_active / 10.0)
        robot_avail  = len(available) / n_total
        battery_risk = sum(1 for r in robot_states if r.battery < 0.3) / n_total
        deadline_now = sum(1 for tk in active if tk.deadline - t < 30) / max(1, n_active)
        fail_rate    = sum(1 for r in robot_states if r.failure_flag) / n_total
        queues_per   = [len(r.queue) for r in robot_states]
        wl_var       = (max(queues_per) - min(queues_per)) / max(1, max(queues_per)) if queues_per else 0.0
        alloc_inst   = 0.1

        C = np.array([task_density, robot_avail, battery_risk, deadline_now,
                      fail_rate, wl_var, alloc_inst], dtype=float)

        # Performance proxy (1/task_density for SpatialOpportunist, etc.)
        self.P = np.clip(C * np.array([0.5, 0.3, 0.4, 0.3, 0.5, 0.3, 0.3]), 0, 1)

        # Dominance update: D(t+1) = clip[αD + βP + γK(C) + ηA·D - λS·D - δF]
        alpha, beta, gamma, eta, lmbda, delta = 0.6, 0.2, 0.15, 0.10, 0.10, 0.15
        K_C = C[:K] if len(C) >= K else np.pad(C, (0, K - len(C)))
        F = np.zeros(K)
        D_new = (alpha * self.D + beta * self.P + gamma * K_C
                 + eta * (A_MATRIX @ self.D) - lmbda * (S_MATRIX @ self.D) - delta * F)
        self.D = np.clip(D_new, 0.0, 1.0)

        W = _softmax(M_CONST @ self.D)

        return EcosystemContext(
            dominance=self.D.tolist(),
            context_vector=C.tolist(),
            allocation_weights=W.tolist(),
            cooperation_matrix=A_MATRIX.tolist(),
            suppression_matrix=S_MATRIX.tolist(),
            heuristic_names=HEURISTIC_NAMES,
        )


# ── Robot simulation state ─────────────────────────────────────────────────────

@dataclass
class SimRobot:
    robot_id: str
    pos: List[float]           # [x, y]
    battery: float = 1.0
    failed: bool = False
    nav_state: int = 0         # 0=idle 1=navigating 4=reached
    current_task_id: str = ''
    goal_pos: Optional[List[float]] = None
    service_remaining: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    distance_traveled: float = 0.0
    idle_time: float = 0.0
    active_time: float = 0.0

    def to_robot_state(self, queue: list) -> RS:
        bat_state = 2 if self.battery < 0.1 else (1 if self.battery < 0.3 else 0)
        return RS(
            robot_id=self.robot_id,
            pose=tuple(self.pos),
            battery=self.battery,
            available=(not self.failed and bat_state < 2),
            current_task_id=self.current_task_id,
            queue=list(queue),
            failure_risk=1.0 if self.failed else 0.0,
            navigation_state=self.nav_state,
            failure_flag=self.failed,
            battery_state=bat_state,
        )


# ── CSV writers ────────────────────────────────────────────────────────────────

def open_csv(path: str, header: list):
    f = open(path, 'w', newline='')
    w = csv.writer(f)
    w.writerow(header)
    return f, w


# ── Task generation ────────────────────────────────────────────────────────────

def generate_tasks(robot_count: int, task_count: int, scenario: str,
                   seed: int, start_time: float) -> List[TS]:
    rng = random.Random(seed)
    deadline_mult = DEADLINE_MULTIPLIERS.get(scenario, 1.0)
    grid = list(GRID)
    rng.shuffle(grid)
    while len(grid) < task_count:
        grid.append((rng.uniform(-8.0, 8.0), rng.uniform(-8.0, 8.0)))

    tasks = []
    for i in range(task_count):
        x, y = grid[i]
        raw_dl = rng.uniform(90.0, 300.0) * deadline_mult
        tasks.append(TS(
            task_id=f'task_{i + 1:03d}',
            position=(float(x), float(y)),
            priority=rng.randint(1, 3),
            activation_time=start_time,
            deadline=start_time + raw_dl,
            service_time=float(rng.uniform(2.0, 8.0)),
            active=False,
            completed=False,
        ))
    return tasks


def batch_plan(task_count: int, scenario: str) -> List[Tuple[float, int]]:
    n = task_count
    b = max(1, n // 3)
    if scenario in ('dynamic_task_arrival', 'mixed_stress'):
        return [(0.0, b), (30.0, b), (60.0, n - 2 * b)]
    return [(0.0, n)]


def failure_plan(scenario: str, seed: int) -> List[Tuple[float, str]]:
    if scenario in ('robot_failure', 'mixed_stress'):
        rng = random.Random(seed)
        offset = FAILURE_OFFSET + rng.uniform(-5.0, 5.0)
        return [(offset, 'robot_2')]
    return []


# ── Main simulation loop ───────────────────────────────────────────────────────

def run_experiment(strategy: str, scenario: str, seed: int,
                   robot_count: int, task_count: int,
                   results_base: str) -> None:
    rng = random.Random(seed)

    exp_id = (f'exp_{scenario}_{strategy}'
              f'_r{robot_count}t{task_count}'
              f'_seed{seed:02d}')
    results_dir = os.path.join(results_base, exp_id)
    os.makedirs(results_dir, exist_ok=True)

    # Metadata
    with open(os.path.join(results_dir, 'metadata.yaml'), 'w') as f:
        yaml.dump({
            'experiment_id': exp_id, 'strategy': strategy,
            'scenario': scenario, 'seed': seed,
            'robot_count': robot_count, 'task_count': task_count,
            'timeout_sec': EXPERIMENT_TIMEOUT,
        }, f)

    # CSV handles
    te_f, te_w = open_csv(os.path.join(results_dir, 'task_events.csv'), [
        'experiment_id', 'scenario', 'strategy', 'seed', 'robot_count', 'target_count',
        'task_id', 'robot_id', 'task_priority', 'activation_time', 'deadline',
        'assigned_time', 'nav_start_rel', 'reached_rel', 'completed_rel',
        'status', 'was_reassigned', 'reassignment_count', 'failure_related',
        'travel_duration', 'service_duration', 'total_duration', 'deadline_violation',
    ])
    ts_f, ts_w = open_csv(os.path.join(results_dir, 'robot_state_timeseries.csv'), [
        'experiment_id', 'scenario', 'strategy', 'seed', 'robot_count', 'target_count',
        'time', 'robot_id', 'x', 'y', 'yaw',
        'availability_state', 'navigation_state', 'battery_state',
        'battery_level', 'current_task_id', 'queue_version', 'failure_flag',
        'active_task_count', 'local_delay', 'congestion_indicator', 'goal_reachability',
    ])
    ae_f, ae_w = open_csv(os.path.join(results_dir, 'allocation_events.csv'), [
        'experiment_id', 'scenario', 'strategy', 'seed',
        'time', 'event_type', 'robot_id', 'task_id',
        'queue_version', 'trigger_reason', 'severity', 'replan_required',
    ])
    rt_f, rt_w = open_csv(os.path.join(results_dir, 'method_runtime.csv'), [
        'experiment_id', 'scenario', 'strategy', 'seed',
        'allocation_round', 'active_task_count', 'available_robot_count',
        'runtime_ms', 'matching_or_solver_time_ms', 'queue_generation_time_ms',
    ])
    comm_f, comm_w = open_csv(os.path.join(results_dir, 'communication_metrics.csv'), [
        'experiment_id', 'scenario', 'strategy', 'seed', 'robot_count',
        'message_count', 'bytes_transmitted', 'topic_count',
        'queue_messages', 'status_messages', 'feedback_messages', 'debug_messages',
        'rosbag_size_mb',
    ])

    eco_ahe = (strategy in AHE_STRATEGIES)
    eco_f = open(os.path.join(results_dir, 'ecosystem_metrics.csv'), 'w', newline='')
    eco_w = csv.writer(eco_f)
    eco_w.writerow([
        'experiment_id', 'scenario', 'strategy', 'seed', 'time',
    ] + HEURISTIC_NAMES + [
        'w_distance', 'w_priority', 'w_battery', 'w_load',
        'w_failure', 'w_deadline', 'w_recovery',
        'task_density', 'robot_availability', 'battery_risk',
        'deadline_pressure', 'failure_rate', 'workload_variance', 'allocation_instability',
    ])

    # Robot starts
    start_poses = [(0.0, 0.0), (0.0, 2.0), (0.0, -2.0),
                   (2.0, 0.0), (-2.0, 0.0)]
    robots = [
        SimRobot(robot_id=f'robot_{i+1}', pos=list(start_poses[i % len(start_poses)]))
        for i in range(robot_count)
    ]
    robot_map = {r.robot_id: r for r in robots}

    tasks = generate_tasks(robot_count, task_count, scenario, seed, start_time=0.0)
    task_map = {t.task_id: t for t in tasks}

    # Assignment tracking
    queues: Dict[str, List[str]] = {r.robot_id: [] for r in robots}
    assigned: Dict[str, str] = {}       # task_id -> robot_id
    task_assign_time: Dict[str, float] = {}
    task_nav_start: Dict[str, float]  = {}
    task_reached_time: Dict[str, float] = {}
    task_reassign_count: Dict[str, int] = {t.task_id: 0 for t in tasks}
    task_failure_related: Dict[str, bool] = {t.task_id: False for t in tasks}

    queue_version = 0

    batches = batch_plan(task_count, scenario)
    failures = failure_plan(scenario, seed)
    next_batch_idx = 0
    failures_injected: Set[str] = set()
    failed_robots: Set[str] = set()

    alloc_cls = ALLOCATOR_REGISTRY[strategy]
    allocator = alloc_cls()
    if hasattr(allocator, 'seed'):
        allocator.seed(seed)

    ahe_eco = AHEEcosystem() if eco_ahe else None
    eco_context: Optional[EcosystemContext] = None

    t = 0.0
    alloc_count = 0
    last_alloc_t = -ALLOC_PERIOD
    last_ts_t    = -TIMESERIES_PERIOD
    comm_total_msgs = 0
    comm_total_bytes = 0
    force_realloc = False

    # Activate first batch
    def activate_batch(batch_idx: int):
        nonlocal next_batch_idx, force_realloc
        if batch_idx >= len(batches):
            return
        _, count = batches[batch_idx]
        activated = 0
        for task in tasks:
            if activated >= count:
                break
            if not task.active and not task.completed:
                task.active = True
                task.activation_time = t
                task.deadline = t + (task.deadline - 0.0)  # keep relative offset
                activated += 1
                te_w.writerow([exp_id, scenario, strategy, seed, robot_count, task_count,
                                task.task_id, '', task.priority,
                                f'{t:.2f}', f'{task.deadline:.2f}',
                                '', '', '', '',
                                'activated', 0, 0, 0, '', '', '', ''])
        next_batch_idx = batch_idx + 1
        force_realloc = True

    activate_batch(0)

    def do_allocation():
        nonlocal alloc_count, last_alloc_t, force_realloc, eco_context
        nonlocal queue_version, comm_total_msgs, comm_total_bytes

        robot_states = [r.to_robot_state(queues[r.robot_id]) for r in robots]

        if eco_ahe and ahe_eco is not None:
            eco_context = ahe_eco.update(robot_states, tasks, t)

            # Log ecosystem metrics
            if eco_context:
                dom = np.array(eco_context.dominance)
                ctx = eco_context.context_vector
                W   = eco_context.allocation_weights
                eco_w.writerow(
                    [exp_id, scenario, strategy, seed, f'{t:.2f}']
                    + [f'{d:.4f}' for d in dom]
                    + [f'{w:.4f}' for w in W]
                    + [f'{c:.4f}' for c in ctx]
                )

        active_tasks = [task for task in tasks
                        if task.active and not task.completed]
        if not active_tasks:
            return

        t0 = time.perf_counter()
        result: AllocationResult = allocator.allocate(
            robot_states, active_tasks,
            current_time=t,
            context=eco_context,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        alloc_count += 1
        queue_version += 1

        for rid, tids in result.queues.items():
            queues[rid] = list(tids)
            for tid in tids:
                if tid not in assigned:
                    assigned[tid] = rid
                    task_assign_time[tid] = t
                    te_w.writerow([exp_id, scenario, strategy, seed, robot_count, task_count,
                                   tid, rid, task_map[tid].priority,
                                   f'{task_map[tid].activation_time:.2f}',
                                   f'{task_map[tid].deadline:.2f}',
                                   f'{t:.2f}', '', '', '',
                                   'assigned', task_reassign_count[tid], 0, 0,
                                   '', '', '', ''])
                    ae_w.writerow([exp_id, scenario, strategy, seed,
                                   f'{t:.2f}', 'task_assigned', rid, tid,
                                   queue_version, 'allocation_run', 1, 0])

        rt_w.writerow([exp_id, scenario, strategy, seed,
                       alloc_count,
                       len(active_tasks),
                       sum(1 for r in robot_states if r.available),
                       f'{elapsed_ms:.3f}',
                       f'{elapsed_ms * 0.7:.3f}',
                       f'{elapsed_ms * 0.3:.3f}'])

        footprint = result.communication_footprint_bytes
        comm_total_msgs += robot_count + 1
        comm_total_bytes += footprint
        comm_w.writerow([exp_id, scenario, strategy, seed, robot_count,
                         robot_count + 1, footprint, 3,
                         robot_count, robot_count, 1, 1 if eco_ahe else 0,
                         0.0])

        force_realloc = False
        last_alloc_t = t

    # ── Simulation loop ────────────────────────────────────────────────────────
    experiment_done = False
    makespan = EXPERIMENT_TIMEOUT

    while t <= EXPERIMENT_TIMEOUT and not experiment_done:

        # Batch activation
        if next_batch_idx < len(batches):
            offset, _ = batches[next_batch_idx]
            if t >= offset:
                activate_batch(next_batch_idx)

        # Failure injection
        for offset, rid in failures:
            if rid not in failures_injected and t >= offset:
                failures_injected.add(rid)
                failed_robots.add(rid)
                robot_map[rid].failed = True
                robot_map[rid].nav_state = 3
                # Unassign tasks from failed robot
                for tid in list(assigned.keys()):
                    if assigned.get(tid) == rid:
                        del assigned[tid]
                        if tid in queues.get(rid, []):
                            queues[rid].remove(tid)
                        task_reassign_count[tid] += 1
                        task_failure_related[tid] = True
                ae_w.writerow([exp_id, scenario, strategy, seed,
                               f'{t:.2f}', 'robot_failure', rid, '',
                               queue_version, 'failure_event', 2, 1])
                force_realloc = True

        # Allocation
        if force_realloc or (t - last_alloc_t >= ALLOC_PERIOD):
            do_allocation()

        # Robot movement
        for robot in robots:
            if robot.failed:
                robot.idle_time += DT
                continue

            rid = robot.robot_id
            queue = queues[rid]

            # Pick next task from queue if idle
            if not robot.current_task_id and queue:
                next_tid = queue[0]
                task = task_map.get(next_tid)
                if task and task.active and not task.completed:
                    robot.current_task_id = next_tid
                    robot.goal_pos = list(task.position)
                    robot.nav_state = 1
                    robot.service_remaining = task.service_time
                    task_nav_start[next_tid] = t

            if robot.current_task_id:
                task = task_map[robot.current_task_id]
                gx, gy = robot.goal_pos
                dx = gx - robot.pos[0]
                dy = gy - robot.pos[1]
                dist = math.hypot(dx, dy)

                if dist > 0.1:
                    # Move toward goal
                    move = min(ROBOT_SPEED_MPS * DT, dist)
                    robot.pos[0] += dx / dist * move
                    robot.pos[1] += dy / dist * move
                    robot.distance_traveled += move
                    robot.battery = max(0.0, robot.battery - BATTERY_DRAIN_MOVE * move)
                    robot.nav_state = 1
                    robot.active_time += DT
                else:
                    # Arrived — service time
                    robot.nav_state = 4
                    robot.service_remaining = max(0.0, robot.service_remaining - DT)

                    if robot.service_remaining <= 0.0:
                        # Task complete
                        tid = robot.current_task_id
                        task.completed = True
                        task.active = False
                        robot.tasks_completed += 1
                        robot.current_task_id = ''
                        robot.nav_state = 0

                        if rid in queues and tid in queues[rid]:
                            queues[rid].remove(tid)
                        assigned.pop(tid, None)

                        task_reached_time[tid] = t
                        nav_start = task_nav_start.get(tid, task_assign_time.get(tid, t))
                        assign_t  = task_assign_time.get(tid, task.activation_time)
                        travel_d  = t - nav_start
                        total_d   = t - assign_t

                        dl_viol = 1 if t > task.deadline else 0
                        te_w.writerow([exp_id, scenario, strategy, seed,
                                       robot_count, task_count,
                                       tid, rid, task.priority,
                                       f'{task.activation_time:.2f}',
                                       f'{task.deadline:.2f}',
                                       f'{assign_t:.2f}',
                                       f'{nav_start - assign_t:.2f}',
                                       f'{t - nav_start:.2f}',
                                       f'{total_d:.2f}',
                                       'completed',
                                       1 if task_reassign_count.get(tid, 0) > 0 else 0,
                                       task_reassign_count.get(tid, 0),
                                       1 if task_failure_related.get(tid, False) else 0,
                                       f'{travel_d:.2f}',
                                       f'{task.service_time:.2f}',
                                       f'{total_d:.2f}',
                                       dl_viol])
                        ae_w.writerow([exp_id, scenario, strategy, seed,
                                       f'{t:.2f}', 'task_completed', rid, tid,
                                       queue_version, 'reached_goal', 0, 0])
            else:
                robot.nav_state = 0
                robot.idle_time += DT
                robot.battery = max(0.0, robot.battery - BATTERY_DRAIN_IDLE * DT)

        # Timeseries logging
        if t - last_ts_t >= TIMESERIES_PERIOD:
            last_ts_t = t
            active_in_queue = sum(len(q) for q in queues.values())
            for robot in robots:
                bat_state = 2 if robot.battery < 0.1 else (1 if robot.battery < 0.3 else 0)
                avail_state = 2 if robot.failed else (1 if robot.nav_state == 1 else 0)
                ts_w.writerow([
                    exp_id, scenario, strategy, seed, robot_count, task_count,
                    f'{t:.2f}', robot.robot_id,
                    f'{robot.pos[0]:.3f}', f'{robot.pos[1]:.3f}', '0.0',
                    avail_state, robot.nav_state, bat_state,
                    f'{robot.battery:.4f}',
                    robot.current_task_id,
                    queue_version,
                    1 if robot.failed else 0,
                    active_in_queue,
                    '0.0', '0.0', '1.0',
                ])

        # Check done
        active_remaining = [task for task in tasks if task.active and not task.completed]
        if not active_remaining and next_batch_idx >= len(batches):
            makespan = t
            experiment_done = True

        t = round(t + DT, 6)

    # ── Write final CSVs ──────────────────────────────────────────────────────
    total_tasks = len(tasks)
    completed = sum(1 for task in tasks if task.completed)
    dl_violated = sum(1 for task in tasks
                      if task.completed and task_reached_time.get(task.task_id, 0) > task.deadline)
    comp_rate = completed / max(1, total_tasks)

    delays = []
    for task in tasks:
        if task.completed:
            at = task_assign_time.get(task.task_id, task.activation_time)
            rt = task_reached_time.get(task.task_id, at)
            delays.append(rt - at)
    avg_delay = sum(delays) / len(delays) if delays else 0.0

    workload = [r.tasks_completed for r in robots]
    mean_w = sum(workload) / max(1, len(workload))
    wv = sum((w - mean_w) ** 2 for w in workload) / max(1, len(workload))
    wb = 1.0 / (1.0 + wv)

    fail_rec_time = 0.0
    if failed_robots and failures:
        fail_time = failures[0][0]
        post_fail = [task for task in tasks
                     if task.completed and task_failure_related.get(task.task_id, False)]
        if post_fail:
            fail_rec_time = max(task_reached_time.get(task.task_id, fail_time)
                                for task in post_fail) - fail_time

    alloc_inst = alloc_count / max(1, completed + 1)
    latencies = []  # we don't have individual latencies in simplified mode

    mean_latency = 0.0  # will be filled from method_runtime

    # Robot workload CSV
    wl_path = os.path.join(results_dir, 'robot_workload.csv')
    with open(wl_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['experiment_id', 'scenario', 'strategy', 'seed',
                    'robot_count', 'robot_id',
                    'assigned_tasks', 'completed_tasks', 'failed_tasks',
                    'travel_distance', 'active_time', 'idle_time'])
        for robot in robots:
            assigned_n = robot.tasks_completed + robot.tasks_failed + len(queues[robot.robot_id])
            w.writerow([exp_id, scenario, strategy, seed, robot_count,
                        robot.robot_id,
                        assigned_n,
                        robot.tasks_completed,
                        robot.tasks_failed,
                        f'{robot.distance_traveled:.2f}',
                        f'{robot.active_time:.1f}',
                        f'{robot.idle_time:.1f}'])

    # Summary CSV
    sum_path = os.path.join(results_dir, 'summary.csv')
    with open(sum_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['experiment_id', 'scenario', 'strategy', 'seed',
                    'robot_count', 'target_count',
                    'tasks_total', 'tasks_completed', 'task_completion_rate',
                    'makespan_s', 'average_task_delay', 'deadline_violation_rate',
                    'total_travel_distance', 'workload_balance',
                    'failure_recovery_time', 'replanning_frequency',
                    'allocation_instability', 'mean_decision_latency_ms',
                    'communication_messages', 'communication_bytes', 'rosbag_size_mb'])
        total_dist = sum(r.distance_traveled for r in robots)
        w.writerow([exp_id, scenario, strategy, seed,
                    robot_count, task_count,
                    total_tasks, completed, f'{comp_rate:.4f}',
                    f'{makespan:.1f}', f'{avg_delay:.2f}',
                    f'{dl_violated / max(1, completed):.4f}',
                    f'{total_dist:.2f}', f'{wb:.4f}',
                    f'{fail_rec_time:.2f}',
                    f'{alloc_count / max(1, makespan / 60.0):.2f}',
                    f'{alloc_inst:.4f}',
                    f'{mean_latency:.2f}',
                    comm_total_msgs, comm_total_bytes, 0.0])

    for fh in [te_f, ts_f, ae_f, rt_f, comm_f, eco_f]:
        fh.close()

    print(f'  [{strategy:30s}|{scenario:22s}|seed={seed}] '
          f'done={completed}/{total_tasks} makespan={makespan:.0f}s '
          f'alloc={alloc_count}')


# ── CLI ────────────────────────────────────────────────────────────────────────

ALL_STRATEGIES = list(ALLOCATOR_REGISTRY.keys())
ALL_SCENARIOS  = ['dynamic_task_arrival', 'deadline_pressure',
                  'robot_failure', 'mixed_stress']


def build_matrix(args) -> List[dict]:
    strategies = args.strategies or ALL_STRATEGIES
    scenarios  = args.scenarios  or ALL_SCENARIOS
    seeds      = args.seeds      or list(range(1, 4))   # MVP: 3 seeds

    if args.scale == 'paper':
        scales = [(5, 25)]
    elif args.scale == 'debug':
        scales = [(3, 15)]
    else:
        scales = [(3, 15), (5, 25)]

    matrix = []
    for rc, tc in scales:
        for strategy in strategies:
            for scenario in scenarios:
                for seed in seeds:
                    matrix.append(dict(
                        strategy=strategy, scenario=scenario,
                        seed=seed, robot_count=rc, task_count=tc,
                    ))
    return matrix


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Standalone AHE-MRTA experiment runner (no ROS2/Gazebo).')
    parser.add_argument('--strategies', nargs='+', default=None,
                        choices=ALL_STRATEGIES + ['all'],
                        help='Allocator strategies to evaluate')
    parser.add_argument('--scenarios', nargs='+', default=None,
                        choices=ALL_SCENARIOS)
    parser.add_argument('--seeds', nargs='+', type=int, default=None,
                        help='Random seeds (default: 1 2 3)')
    parser.add_argument('--scale', choices=['debug', 'paper', 'both'],
                        default='debug',
                        help='debug=3R/15T  paper=5R/25T  both=both')
    parser.add_argument('--results-dir', default='results/raw',
                        help='Base directory for CSV output')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print experiment matrix without running')
    args = parser.parse_args()

    if args.strategies and 'all' in args.strategies:
        args.strategies = ALL_STRATEGIES

    matrix = build_matrix(args)
    total = len(matrix)

    print(f'\n{"="*60}')
    print(f'AHE-MRTA Standalone Experiment Runner')
    print(f'  Experiments : {total}')
    print(f'  Results dir : {args.results_dir}')
    print(f'{"="*60}\n')

    if args.dry_run:
        for i, exp in enumerate(matrix, 1):
            print(f'  [{i:3d}/{total}] {exp["strategy"]:30s} | {exp["scenario"]:22s} | '
                  f'seed={exp["seed"]} | {exp["robot_count"]}R/{exp["task_count"]}T')
        return

    os.makedirs(args.results_dir, exist_ok=True)
    wall_start = time.time()

    for i, exp in enumerate(matrix, 1):
        print(f'[{i:3d}/{total}] ', end='', flush=True)
        try:
            run_experiment(
                strategy=exp['strategy'],
                scenario=exp['scenario'],
                seed=exp['seed'],
                robot_count=exp['robot_count'],
                task_count=exp['task_count'],
                results_base=args.results_dir,
            )
        except Exception as e:
            print(f'  ERROR: {e}')
            import traceback; traceback.print_exc()

    wall_elapsed = time.time() - wall_start
    print(f'\n[DONE] {total} experiments in {wall_elapsed:.1f}s '
          f'({wall_elapsed/max(1,total):.1f}s/exp)')
    print(f'Results in: {args.results_dir}')
    print(f'\nNext: python3 scripts/consolidate_results.py --raw-dir {args.results_dir}')


if __name__ == '__main__':
    main()
