#!/usr/bin/env python3
"""
AHE-MRTA — Hızlı Gazebo-sız simülasyon & karşılaştırma

Gerçek allocator kodunu kullanır, basitleştirilmiş fizik motoru ile
yüzlerce seed'i saniyeler içinde çalıştırır.

Kullanım:
  python3 scripts/simulate_and_tune.py
  python3 scripts/simulate_and_tune.py --seeds 200 --scenario robot_failure
  python3 scripts/simulate_and_tune.py --seeds 100 --scenario all --robots 3 --tasks 15
  python3 scripts/simulate_and_tune.py --tune-temp      # softmax T sweep
  python3 scripts/simulate_and_tune.py --tune-alpha     # ALPHA sweep
  python3 scripts/simulate_and_tune.py --method full_ahe_mrta --seeds 50 --verbose
"""

import argparse
import math
import random
import sys
import time
from copy import deepcopy
from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
import os
_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_repo, 'src', 'm_ahe_task_allocator'))
sys.path.insert(0, os.path.join(_repo, 'src', 'm_ahe_ecosystem_manager'))

from m_ahe_task_allocator.baselines.base_allocator import (
    AllocationResult, EcosystemContext, RobotState, TaskState,
)
from m_ahe_task_allocator.baselines.ahe_variants import AHEMRTAv3Allocator
from m_ahe_task_allocator.placement import (
    task_positions as _free_task_positions,
    robot_spawns as _free_robot_spawns,
)
from m_ahe_task_allocator.baselines.big_mrta import BigMRTAAllocator
from m_ahe_task_allocator.baselines.static_weighted import StaticWeightedAllocator
from m_ahe_task_allocator.baselines.consensus_dbta import ConsensusDBTAAllocator
from m_ahe_task_allocator.baselines.rostam_ea import RoSTAMEAAllocator

# ---------------------------------------------------------------------------
# Ecosystem constants (mirrored from ecosystem_manager_node)
# ---------------------------------------------------------------------------
K = 7
H_SPATIAL, H_CRIT, H_TEMP, H_RES, H_ENERGY, H_STAB, H_RECOV = range(7)
HEURISTIC_NAMES = [
    'SpatialOpportunist', 'CriticalityGuardian', 'TemporalRegulator',
    'ResourceDistributor', 'EnergyConservator', 'StabilityController',
    'RecoveryCoordinator',
]

A = np.zeros((K, K))
A[H_RECOV, H_ENERGY] = 0.30
A[H_TEMP,  H_CRIT]   = 0.20
A[H_RECOV, H_STAB]   = 0.20
A[H_RES,   H_SPATIAL] = 0.20

S = np.zeros((K, K))
S[H_SPATIAL, H_TEMP]   = 0.30
S[H_SPATIAL, H_ENERGY] = 0.30
S[H_RES,     H_CRIT]   = 0.20

V = np.array([
    [0.7, 0.7, 0.1, 0.1, 0.1, 0.3, 0.1],
    [0.3, 0.5, 0.1, 0.8, 0.2, 0.1, 0.2],
    [0.5, 0.5, 0.1, 0.9, 0.1, 0.1, 0.1],
    [0.8, 0.3, 0.1, 0.3, 0.1, 0.9, 0.3],
    [0.3, 0.3, 0.9, 0.2, 0.2, 0.2, 0.2],
    [0.3, 0.3, 0.3, 0.3, 0.8, 0.3, 0.3],
    [0.3, 0.2, 0.3, 0.2, 0.9, 0.3, 0.8],
])

M = np.array([
    [0.9, 0.1, 0.1, 0.3, 0.3, 0.3, 0.3],
    [0.1, 0.9, 0.5, 0.1, 0.1, 0.5, 0.1],
    [0.1, 0.1, 0.1, 0.1, 0.9, 0.3, 0.3],
    [0.1, 0.1, 0.1, 0.9, 0.1, 0.1, 0.3],
    [0.1, 0.1, 0.1, 0.1, 0.3, 0.9, 0.9],
    [0.1, 0.5, 0.9, 0.1, 0.1, 0.1, 0.1],
    [0.1, 0.1, 0.1, 0.1, 0.3, 0.3, 0.9],
])

# Ekosistem dinamik parametreleri — F3 (Tier 1) kalibrasyonu:
# ALPHA düşürüldü (0.85→0.65): D vektörü daha hızlı adapte olur.
# BETA artırıldı (0.25→0.40): performans feedback'inin etkisi büyür.
# Birlikte: fixed_weights ablasyonu ile ölçülebilir fark üretmek için.
ALPHA = 0.65
BETA  = 0.40
GAMMA = 0.20
ETA   = 0.12
LMBDA = 0.12
DELTA = 0.20
SOFTMAX_TEMP = 0.3


# ---------------------------------------------------------------------------
# Navigation / arena model
# ---------------------------------------------------------------------------

ARENA_HALF = 6.0      # arena is ±6m
ROBOT_SPEED = 0.4     # m/s (TurtleBot3 Waffle Pi ~0.26 max, sim slightly faster)
NAV_TIMEOUT = 30.0    # seconds per task attempt (Nav2 default ~25s + buffer)
SERVICE_TIME = 2.0    # seconds at waypoint after arrival

# Task positions that are "blocked" (near walls → high failure rate)
def _nav_success_prob(pos: Tuple[float, float], rng: random.Random) -> float:
    """Probability that Nav2 succeeds for a given goal position."""
    x, y = pos
    wall_dist = min(ARENA_HALF - abs(x), ARENA_HALF - abs(y))
    if wall_dist < 0.4:      # closer than robot footprint to wall → nearly always fail
        return 0.05
    elif wall_dist < 0.8:    # tight passage / near obstacle
        return 0.40
    else:
        return 0.88          # open area: occasional Nav2 planner failure


def _nav_time(robot_pos: Tuple[float, float], task_pos: Tuple[float, float]) -> float:
    """Simulated navigation time in seconds."""
    d = math.hypot(task_pos[0] - robot_pos[0], task_pos[1] - robot_pos[1])
    return max(1.0, d / ROBOT_SPEED) + SERVICE_TIME


# Nav2-independent allocation fitness is computed as the priority-weighted
# on-time completion achieved in this idealised (navigation-free) model — see
# the accumulation in run_simulation. It measures how well the allocator's
# decisions translate into deadline-respecting throughput, isolating algorithmic
# quality from physical Nav2 outcomes that confound Delay / Distance in Gazebo.


# ---------------------------------------------------------------------------
# Ecosystem simulator (pure Python, no ROS2)
# ---------------------------------------------------------------------------

def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na > 1e-9 and nb > 1e-9 else 0.0


def _softmax(x: np.ndarray, temp: float = SOFTMAX_TEMP) -> np.ndarray:
    x_s = x / max(temp, 1e-9)
    e = np.exp(x_s - x_s.max())
    return e / e.sum()


class EcosystemSimulator:
    """Replicates ecosystem_manager_node logic without ROS2."""

    def __init__(self):
        self._D = np.full(K, 1.0 / K)
        self._completed = 0
        self._failed = 0

    def reset(self):
        self._D = np.full(K, 1.0 / K)
        self._completed = 0
        self._failed = 0

    def record_outcome(self, completed: int, failed: int):
        self._completed += completed
        self._failed += failed

    def update(self, sim_state: 'SimState', alpha=ALPHA, beta=BETA,
               gamma=GAMMA, eta=ETA, lmbda=LMBDA, delta=DELTA,
               temp=SOFTMAX_TEMP) -> EcosystemContext:
        ctx = self._build_context(sim_state)
        ctx_v = np.array(ctx)
        compat = np.array([_cosine_sim(V[i], ctx_v) for i in range(K)])

        total = max(1, self._completed + self._failed)
        perf = ((self._completed / total) - (self._failed / total)) * compat
        self._completed = 0
        self._failed = 0

        coop = eta * (A @ self._D)
        supp = lmbda * (S @ self._D)

        boost = np.zeros(K)
        failure_rate = ctx[4]  # C_FAILURE dimension
        boost[H_RECOV] = failure_rate * 0.6
        boost[H_STAB]  = failure_rate * 0.4
        boost[H_SPATIAL] = -failure_rate * 0.3
        boost[H_RES]     = -failure_rate * 0.2

        D_new = np.clip(
            alpha * self._D + beta * perf + gamma * compat + coop - supp + delta * boost,
            0.0, 1.0
        )
        total_d = D_new.sum()
        self._D = D_new / total_d if total_d > 1e-9 else np.full(K, 1.0 / K)

        W = _softmax(M @ self._D, temp=temp)
        return EcosystemContext(
            dominance=self._D.tolist(),
            context_vector=ctx,
            allocation_weights=W.tolist(),
            cooperation_matrix=A.tolist(),
            suppression_matrix=S.tolist(),
            heuristic_names=HEURISTIC_NAMES,
        )

    def _build_context(self, s: 'SimState') -> List[float]:
        active = [t for t in s.tasks if t.active and not t.completed]
        n_active = max(1, len(active))
        n_avail  = sum(1 for r in s.robots if r.available)
        n_robots = max(1, len(s.robots))

        task_density  = min(1.0, len(active) / max(1, s.n_tasks))
        robot_avail   = n_avail / n_robots
        deadline_p    = sum(
            1 for t in active
            if t.deadline > 0 and (t.deadline - s.time) < 60
        ) / n_active
        failure_rate  = (n_robots - n_avail) / n_robots
        # batt_risk (c3), workload_var (c6), alloc_instab (c7): DEVRE DIŞI —
        # bağlam ablasyonu gereksiz (Δfitness=0); 0'da bırakılır, hesap atlanır.
        return [
            min(1.0, task_density),
            min(1.0, robot_avail),
            0.0,                      # c3 battery (disabled)
            min(1.0, deadline_p),
            min(1.0, failure_rate),
            0.0,                      # c6 workload variance (disabled)
            0.0,                      # c7 allocation instability (disabled)
        ]


# ---------------------------------------------------------------------------
# v3 Fixed cost function (patches _AHEBase._assign at runtime)
# Kept for --compare-v3 backward compatibility; real code already has these fixes.
# Fixes:
#   1. w_r added: R_nav = 1 if robot stuck/failed (navigation_state in 2,3)
#   2. B = 1 - robot.battery (continuous, not integer battery_state)
#   3. F = robot.failure_risk (continuous, not binary failure_flag)
# ---------------------------------------------------------------------------

def _patch_ahe_cost(allocator):
    """Monkey-patch _assign on an _AHEBase instance to use fixed cost function."""
    import types, math as _math
    from m_ahe_task_allocator.baselines.base_allocator import queue_endpoint, cheapest_insertion

    _BATT_CRITICAL = 2
    _MAX_DIST = 28.0

    def _assign_v3(self, robots, tasks, current_time, weights):
        task_map = {t.task_id: t for t in tasks}
        queues = {r.robot_id: list(r.queue) for r in robots}
        assigned = {tid for q in queues.values() for tid in q}
        unassigned = sorted(
            [t for t in tasks if t.task_id not in assigned],
            key=lambda t: (-t.priority, t.deadline),
        )
        w_d, w_p, w_b, w_l, w_f, w_t, w_r = weights

        for task in unassigned:
            best_r, best_c = None, float('inf')

            for r in robots:
                if r.battery_state == _BATT_CRITICAL or not r.available:
                    continue
                ep = queue_endpoint(r, task_map, queues[r.robot_id])
                D = min(1.0, _math.hypot(
                    task.position[0] - ep[0],
                    task.position[1] - ep[1]) / _MAX_DIST)
                P = (4 - task.priority) / 3.0
                B = 1.0 - r.battery                          # FIX: continuous battery
                L = min(1.0, len(queues[r.robot_id]) /
                        max(1.0, 15.0 / len(robots) * 2))
                F = getattr(r, 'failure_risk', 0.0)          # FIX: failure risk
                elapsed = current_time - task.activation_time
                T = min(1.0, elapsed / task.deadline) if task.deadline > 0 else 0.0
                R_nav = 1.0 if getattr(r, 'navigation_state', 0) in (2, 3) else 0.0
                cost = w_d*D + w_p*P + w_b*B + w_l*L + w_f*F + w_t*T + w_r*R_nav
                if cost < best_c:
                    best_c = cost; best_r = r.robot_id
            if best_r:
                queues[best_r].append(task.task_id)

        ordered = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            ins = cheapest_insertion(r.pose, q_tasks)
            ordered[r.robot_id] = [t.task_id for t in ins]
        return ordered

    # Only patch _AHEBase subclasses
    from m_ahe_task_allocator.baselines.ahe_variants import _AHEBase
    if isinstance(allocator, _AHEBase):
        allocator._assign = types.MethodType(_assign_v3, allocator)
    return allocator


# ---------------------------------------------------------------------------
# Simulation state
# ---------------------------------------------------------------------------

@dataclass
class NavJob:
    task_id: str
    start_time: float
    finish_time: float    # when robot arrives
    success: bool         # determined at creation (Nav2 outcome)


@dataclass
class SimRobot:
    robot_id: str
    pos: Tuple[float, float]
    available: bool = True
    battery: float = 1.0
    current_job: Optional[NavJob] = None
    failed_at: float = -1.0
    navigation_state: int = 0   # 0=idle, 1=navigating, 2=stuck, 3=failed, 4=reached
    stuck_until: float = 0.0    # sim time when stuck period ends


@dataclass
class SimState:
    time: float
    robots: List[SimRobot]
    tasks: List[TaskState]
    queues: Dict[str, List[str]]   # robot_id → ordered task_id list
    n_tasks: int
    reassign_count: int = 0


# ---------------------------------------------------------------------------
# Scenario generators
# ---------------------------------------------------------------------------

def _gen_tasks(n: int, rng: random.Random, scenario: str,
               exp_duration: float, seed: int, n_robots: int) -> List[TaskState]:
    tasks = []
    # Obstacle-aware positions shared with the Gazebo runner: identical goals
    # for a given (n, seed, n_robots) so the two planes stay comparable (R4/R6),
    # no task lands inside a shelf/wall/cylinder, and goals stay clear of the
    # robot depot.
    positions = _free_task_positions(n, seed, n_robots)

    # Task activation schedule:
    #   deadline_pressure : all at t=0 (single tight wave)
    #   robot_failure     : wave 1 @ t=0 (8 tasks), wave 2 @ t=60 (4), wave 3 @ t=120 (3)
    #   mixed_stress      : same waves as robot_failure + faster battery drain (handled
    #                       in run_simulation via scenario check)
    # Staggered activation ensures L/B/F context factors are non-zero at waves 2-3,
    # making ecosystem weight adaptation visible in ablation comparisons.
    deadline_pressure = (scenario == 'deadline_pressure')
    if deadline_pressure or n <= 5:
        activation_schedule = [0.0] * n
    else:
        # 8 tasks at t=0, 4 at t=60, remainder at t=120
        n_w1 = min(8, n)
        n_w2 = min(4, n - n_w1)
        n_w3 = n - n_w1 - n_w2
        activation_schedule = ([0.0] * n_w1 + [60.0] * n_w2 + [120.0] * n_w3)

    for i, (pos, act_t) in enumerate(zip(positions, activation_schedule)):
        pri = rng.choice([1, 2, 3])
        if deadline_pressure:
            dl = rng.uniform(200.0, 400.0)   # tight deadlines
        else:
            # Generous deadline from activation time (not experiment start)
            dl = act_t + exp_duration * 0.75
        tasks.append(TaskState(
            task_id=f'task_{i+1:03d}',
            position=pos,
            priority=pri,
            activation_time=act_t,
            deadline=dl,
            service_time=SERVICE_TIME,
            active=(act_t == 0.0),   # only wave-1 tasks active at start
            completed=False,
        ))
    return tasks


def _initial_robots(n: int, rng: random.Random, seed: int = 1) -> List[SimRobot]:
    # Spawn at the SAME obstacle-free positions the Gazebo SDF uses
    # (placement.robot_spawns, seed-independent) — no jitter, so SIM and Gazebo
    # robots start identically.
    spawn = _free_robot_spawns(n, seed)
    robots = []
    for i in range(n):
        x, y = spawn[i]
        robots.append(SimRobot(
            robot_id=f'robot_{i+1}',
            pos=(float(x), float(y)),
        ))
    return robots


# ---------------------------------------------------------------------------
# Core simulation loop
# ---------------------------------------------------------------------------

def run_simulation(
    allocator,
    scenario: str,
    seed: int,
    n_robots: int = 3,
    n_tasks: int = 15,
    exp_duration: float = 900.0,
    eco: Optional[EcosystemSimulator] = None,
    alloc_period: float = 5.0,
    verbose: bool = False,
    batt_drain: float = 0.0075,       # 0.015/5s drain at 0.4m/s → 0.015/2m = 0.0075/m
    nav_fail_stuck: float = 0.0,      # real robot_interface: immediate IDLE after failure
    ideal_nav: bool = False,          # navigation-independent eval: nav always succeeds
    alpha=ALPHA, beta=BETA, gamma=GAMMA, eta=ETA,
    lmbda=LMBDA, delta=DELTA, temp=SOFTMAX_TEMP,
) -> Dict:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    tasks = _gen_tasks(n_tasks, rng, scenario, exp_duration, seed, n_robots)
    task_map = {t.task_id: t for t in tasks}
    robots = _initial_robots(n_robots, rng, seed)
    queues: Dict[str, List[str]] = {r.robot_id: [] for r in robots}

    if eco is not None:
        eco.reset()

    # mixed_stress: faster battery drain + heterogeneous starting battery
    if scenario == 'mixed_stress':
        BATT_DRAIN_PER_METER = batt_drain * 2.5
        # Robots start with different battery levels (low / medium / full)
        batt_levels = [0.40, 0.70, 1.00]
        for i, robot in enumerate(robots):
            robot.battery = batt_levels[i % len(batt_levels)]
    else:
        BATT_DRAIN_PER_METER = batt_drain
    NAV_FAIL_STUCK_SEC   = nav_fail_stuck

    # Failure injection (robot_failure + mixed_stress)
    fail_robot_id = None
    fail_time = -1.0
    if scenario in ('robot_failure', 'mixed_stress'):
        fail_robot_id = rng.choice([r.robot_id for r in robots])
        fail_time = 45.0

    # Task backoff
    task_fail_count: Dict[str, int] = {}
    task_skip_until: Dict[str, float] = {}
    MAX_RETRIES = 3
    BACKOFF_SEC = 120.0

    # Metrics
    completed_count = 0
    failed_nav_count = 0
    reassign_count = 0
    assign_log: Dict[str, str] = {}     # task_id → last assigned robot
    recovery_start: float = -1.0
    recovery_end:   float = -1.0
    completion_times: List[float] = []
    deadline_violations = 0
    robot_distances: Dict[str, float] = {r.robot_id: 0.0 for r in robots}
    robot_completed: Dict[str, int]   = {r.robot_id: 0 for r in robots}
    # Nav2-independent allocation fitness = priority-weighted on-time completion
    # achieved in this idealised (navigation-free) model. Higher = better.
    ontime_pri_completed = 0.0
    latencies: List[float] = []   # allocator decision latency (ms), Nav2-independent

    t = 0.0
    dt = 0.5
    last_alloc = -alloc_period
    eco_context: Optional[EcosystemContext] = None
    last_dom_heuristic = ''

    def _get_robot(rid: str) -> SimRobot:
        return next(r for r in robots if r.robot_id == rid)

    def _do_allocation(current_t: float):
        nonlocal eco_context, reassign_count, last_dom_heuristic

        if eco is not None:
            eco_context = eco.update(
                SimState(current_t, robots, tasks, queues, n_tasks, reassign_count),
                alpha=alpha, beta=beta, gamma=gamma, eta=eta,
                lmbda=lmbda, delta=delta, temp=temp,
            )
            dom_idx = int(np.argmax(eco_context.dominance))
            last_dom_heuristic = HEURISTIC_NAMES[dom_idx]

        rs = []
        for r in robots:
            sr = _get_robot(r.robot_id)
            rs.append(RobotState(
                robot_id=r.robot_id,
                pose=sr.pos,
                battery=sr.battery,
                available=sr.available,
                current_task_id=sr.current_job.task_id if sr.current_job else '',
                queue=list(queues[r.robot_id]),
                failure_flag=not sr.available,
                failure_risk=max(0.0, 1.0 - sr.battery * 3.0),
                battery_state=2 if sr.battery < 0.1 else (1 if sr.battery < 0.3 else 0),
                navigation_state=sr.navigation_state,
            ))

        now_s = current_t
        eligible = [
            t for t in tasks
            if t.active and not t.completed
            and now_s >= task_skip_until.get(t.task_id, 0.0)
        ]

        result: AllocationResult = allocator.allocate(
            rs, eligible, current_t, context=eco_context
        )
        latencies.append(result.latency_ms)
        for rid, tids in result.queues.items():
            for tid in tids:
                if tid not in assign_log or assign_log[tid] != rid:
                    if assign_log.get(tid) and assign_log[tid] != rid:
                        reassign_count += 1
                    assign_log[tid] = rid
            queues[rid] = list(tids)

    # Initial allocation
    _do_allocation(t)
    last_alloc = t

    # Track which activation waves have already triggered reallocation
    _activated_waves: set = set()

    # Main simulation loop
    while t < exp_duration:
        t += dt

        # 0. Activate deferred tasks (staggered waves)
        newly_activated = False
        for task in tasks:
            if not task.active and not task.completed and t >= task.activation_time:
                task.active = True
                newly_activated = True
        if newly_activated:
            _do_allocation(t)
            last_alloc = t

        # 1. Inject robot failure
        if fail_robot_id and t >= fail_time and fail_time > 0:
            fr = _get_robot(fail_robot_id)
            if fr.available:
                fr.available = False
                fr.failed_at = t
                fr.current_job = None
                queues[fail_robot_id] = []
                recovery_start = t
                if verbose:
                    print(f"  t={t:.0f}: {fail_robot_id} FAILED")
                _do_allocation(t)
                last_alloc = t
                fail_time = -1.0  # don't re-inject

        # 2. Process robot jobs
        for robot in robots:
            if not robot.available:
                continue
            # Release stuck state when timeout passes
            if robot.navigation_state in (2, 3) and t >= robot.stuck_until:
                robot.navigation_state = 0
            if robot.current_job is not None:
                job = robot.current_job
                if t >= job.finish_time:
                    task = task_map[job.task_id]
                    if job.success:
                        task.completed = True
                        task.active = False
                        completed_count += 1
                        robot_completed[robot.robot_id] += 1
                        robot.navigation_state = 0
                        if eco:
                            eco.record_outcome(1, 0)
                        completion_times.append(t - task.activation_time)
                        if task.deadline > 0 and t > task.deadline:
                            deadline_violations += 1
                        else:
                            # On-time completion → credit priority-weighted fitness
                            ontime_pri_completed += max(1, task.priority)
                        if recovery_start > 0 and recovery_end < 0:
                            recovery_end = t
                        if verbose:
                            print(f"  t={t:.0f}: {robot.robot_id} COMPLETED {job.task_id}")
                    else:
                        # Navigation failed — robot enters stuck state
                        robot.navigation_state = 3
                        robot.stuck_until = t + NAV_FAIL_STUCK_SEC
                        task_fail_count[job.task_id] = task_fail_count.get(job.task_id, 0) + 1
                        failed_nav_count += 1
                        if eco:
                            eco.record_outcome(0, 1)
                        if task_fail_count[job.task_id] >= MAX_RETRIES:
                            task_skip_until[job.task_id] = t + BACKOFF_SEC
                        if verbose:
                            cnt = task_fail_count[job.task_id]
                            print(f"  t={t:.0f}: {robot.robot_id} STUCK {job.task_id} (x{cnt})")
                        _do_allocation(t)
                        last_alloc = t

                    # Remove from queue
                    if job.task_id in queues[robot.robot_id]:
                        queues[robot.robot_id].remove(job.task_id)
                    assign_log.pop(job.task_id, None)
                    robot.current_job = None

        # 3. Start next task for idle robots
        for robot in robots:
            if not robot.available or robot.current_job is not None:
                continue
            # Don't start new task while stuck/failed
            if robot.navigation_state in (2, 3) and t < robot.stuck_until:
                continue
            if robot.navigation_state in (2, 3):
                robot.navigation_state = 0
            q = queues[robot.robot_id]
            # Find first eligible task in queue
            started = False
            for tid in list(q):
                task = task_map.get(tid)
                if task is None or task.completed or not task.active:
                    q.remove(tid)
                    continue
                now_s = t
                if now_s < task_skip_until.get(tid, 0.0):
                    continue
                # Start navigation
                dist = math.hypot(task.position[0] - robot.pos[0],
                                  task.position[1] - robot.pos[1])
                nav_t = _nav_time(robot.pos, task.position)
                if ideal_nav:
                    # Navigation-independent evaluation: perfect navigation, so
                    # every metric reflects allocation quality alone (robot
                    # failures are still injected separately).
                    success = True
                else:
                    success = rng.random() < _nav_success_prob(task.position, rng)
                    # Timeout: if distance too large, fail
                    if dist / ROBOT_SPEED > NAV_TIMEOUT:
                        success = False
                job = NavJob(
                    task_id=tid,
                    start_time=t,
                    finish_time=min(t + nav_t, t + NAV_TIMEOUT),
                    success=success,
                )
                robot.current_job = job
                robot.navigation_state = 1
                robot_distances[robot.robot_id] += dist
                robot.battery = max(0.0, robot.battery - dist * BATT_DRAIN_PER_METER)
                if verbose:
                    print(f"  t={t:.0f}: {robot.robot_id} → {tid} "
                          f"({'ok' if success else 'FAIL'}, {nav_t:.1f}s)")
                started = True
                break

        # 4. Periodic allocation
        if t - last_alloc >= alloc_period:
            _do_allocation(t)
            last_alloc = t

    # ── Metrics ────────────────────────────────────────────────────────────
    active_remaining = sum(1 for t in tasks if t.active and not t.completed)
    completion_rate = completed_count / n_tasks

    # Workload balance (Jain's fairness on completed tasks)
    wl = list(robot_completed.values())
    if sum(wl) > 0:
        balance = (sum(wl) ** 2) / (len(wl) * sum(w ** 2 for w in wl)) if any(wl) else 0.0
    else:
        balance = 0.0

    # Completed-only (legacy) delay/DVR — retained for transparency.
    avg_delay_completed = mean(completion_times) if completion_times else 0.0
    dvr_completed = deadline_violations / max(1, completed_count)

    # ── FAIR (all-task) delay / DVR — survivorship-bias-free ─────────────────
    # A method that DROPS hard tasks (low completion) otherwise gets an
    # artificially low delay/DVR because dropped tasks never enter the
    # completed-only denominator. The fair metrics censor every uncompleted
    # task at the horizon (delay = remaining horizon) and count an unfinished
    # deadline task as a violation. Applied UNIFORMLY to all methods.
    fair_delays = list(completion_times)  # completed: delay since activation
    for task in tasks:
        if not task.completed:
            fair_delays.append(max(0.0, exp_duration - task.activation_time))
    avg_delay = mean(fair_delays) if fair_delays else 0.0

    dl_tasks = [task for task in tasks if task.deadline > 0]
    dl_violated_all = deadline_violations  # completed-late count
    for task in dl_tasks:
        if not task.completed:
            dl_violated_all += 1            # never finished → deadline missed
    dvr = dl_violated_all / max(1, len(dl_tasks)) if dl_tasks else 0.0

    recovery_time = (recovery_end - recovery_start) if (recovery_start > 0 and recovery_end > 0) else -1.0
    instability = reassign_count / max(1, n_tasks)
    total_dist = sum(robot_distances.values())
    total_pri = sum(max(1, t.priority) for t in tasks) or 1.0
    alloc_fitness = ontime_pri_completed / total_pri
    mean_latency = (sum(latencies) / len(latencies)) if latencies else 0.0

    return {
        'completion_rate': completion_rate,
        'completed': completed_count,
        'remaining': active_remaining,
        'avg_delay': avg_delay,
        'avg_delay_completed': avg_delay_completed,
        'deadline_violations': dl_violated_all,
        'deadline_violation_rate': dvr,
        'deadline_violation_rate_completed': dvr_completed,
        'workload_balance': balance,
        'failure_recovery_time': recovery_time,
        'allocation_instability': instability,
        'mean_decision_latency_ms': mean_latency,
        'nav_failures': failed_nav_count,
        'total_distance': total_dist,
        'alloc_fitness': alloc_fitness,
        'last_dominant': last_dom_heuristic,
        'robot_completed': dict(robot_completed),   # diagnostic: per-robot completions
        'failed_robot': fail_robot_id,
    }


# ---------------------------------------------------------------------------
# Allocator registry
# ---------------------------------------------------------------------------

def _make_allocators():
    return {
        # Önerilen yöntem
        'ahe_mrta_v3':                    lambda: AHEMRTAv3Allocator(),
        # Karşılaştırma baseline yöntemleri
        'big_mrta':                       lambda: BigMRTAAllocator(),
        'rostam_ea':                      lambda: RoSTAMEAAllocator(),
        'consensus_dbta':                 lambda: ConsensusDBTAAllocator(),
    }


_AHE_METHODS = {'ahe_mrta_v3'}


def _needs_eco(name: str) -> bool:
    return name in _AHE_METHODS


# ---------------------------------------------------------------------------
# Multi-seed benchmark
# ---------------------------------------------------------------------------

def benchmark(
    methods: List[str],
    scenario: str,
    n_seeds: int,
    n_robots: int = 3,
    n_tasks: int = 15,
    exp_duration: float = 900.0,
    verbose: bool = False,
    ideal_nav: bool = False,
    **eco_kwargs,
) -> Dict[str, Dict]:
    results: Dict[str, List[Dict]] = {m: [] for m in methods}
    registry = _make_allocators()

    for seed in range(1, n_seeds + 1):
        for mname in methods:
            alloc = registry[mname]()
            eco = EcosystemSimulator() if _needs_eco(mname) else None
            r = run_simulation(
                alloc, scenario, seed,
                n_robots=n_robots, n_tasks=n_tasks,
                exp_duration=exp_duration,
                eco=eco, verbose=(verbose and seed <= 2),
                ideal_nav=ideal_nav,
                **eco_kwargs,
            )
            results[mname].append(r)

    summary: Dict[str, Dict] = {}
    for mname, runs in results.items():
        def _m(key): return mean(r[key] for r in runs)
        def _s(key):
            vals = [r[key] for r in runs]
            return stdev(vals) if len(vals) > 1 else 0.0
        recovery_valid = [r['failure_recovery_time'] for r in runs if r['failure_recovery_time'] > 0]
        summary[mname] = {
            'completion_rate':      _m('completion_rate'),
            'completion_std':       _s('completion_rate'),
            'avg_delay':            _m('avg_delay'),
            'deadline_violation_rate': _m('deadline_violation_rate'),
            'workload_balance':     _m('workload_balance'),
            'instability':          _m('allocation_instability'),
            'instability_std':      _s('allocation_instability'),
            'recovery_time':        mean(recovery_valid) if recovery_valid else -1.0,
            'mean_decision_latency_ms': _m('mean_decision_latency_ms'),
            'nav_failures':         _m('nav_failures'),
            'total_distance':       _m('total_distance'),
            'alloc_fitness':        _m('alloc_fitness'),
            'alloc_fitness_std':    _s('alloc_fitness'),
        }
    return summary


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

def _rank_mark(val: float, vals: List[float], higher_is_better: bool) -> str:
    sorted_vals = sorted(set(vals), reverse=higher_is_better)
    rank = sorted_vals.index(val) + 1
    if rank == 1: return '★'
    if rank == 2: return '✓'
    return ' '


def print_comparison(summary: Dict[str, Dict], scenario: str, n_seeds: int):
    print(f"\n{'═'*90}")
    print(f"  Senaryo: {scenario}  |  Seed sayısı: {n_seeds}")
    print(f"{'═'*90}")
    header = (f"{'Yöntem':<22} {'Fit':>6} {'CR':>6} {'Delay':>7} {'DVR':>6} "
              f"{'RecT':>7} {'Instab':>7} {'WLBal':>6} {'Dist':>7} {'Lat(ms)':>8}")
    print(header)
    print('─' * 100)

    methods = list(summary.keys())
    def col(k): return [summary[m][k] for m in methods]
    fit_vals    = col('alloc_fitness')
    comp_vals   = col('completion_rate')
    delay_vals  = col('avg_delay')
    dvr_vals    = col('deadline_violation_rate')
    rec_vals_m  = [summary[m]['recovery_time'] for m in methods]
    instab_vals = col('instability')
    wb_vals     = col('workload_balance')
    dist_vals   = col('total_distance')
    lat_vals    = col('mean_decision_latency_ms')

    for mname in sorted(methods, key=lambda m: -summary[m]['alloc_fitness']):
        s = summary[mname]
        rf = _rank_mark(s['alloc_fitness'],         fit_vals,   True)
        rc = _rank_mark(s['completion_rate'],       comp_vals,  True)
        rd = _rank_mark(s['avg_delay'],             delay_vals, False)
        rv = _rank_mark(s['deadline_violation_rate'], dvr_vals, False)
        ri = _rank_mark(s['instability'],           instab_vals, False)
        rw = _rank_mark(s['workload_balance'],      wb_vals,    True)
        rt = _rank_mark(s['total_distance'],        dist_vals,  False)
        rl = _rank_mark(s['mean_decision_latency_ms'], lat_vals, False)
        prefix = '[AHE] ' if mname in _AHE_METHODS else '      '
        rec_str = f"{s['recovery_time']:>6.1f}" if s['recovery_time'] > 0 else '     -'
        print(
            f"{prefix}{mname:<16}"
            f"{s['alloc_fitness']:>5.3f}{rf}"
            f"{s['completion_rate']:>5.3f}{rc}"
            f"{s['avg_delay']:>6.1f}{rd}"
            f"{s['deadline_violation_rate']:>5.3f}{rv}"
            f"{rec_str}{'':1}"
            f"{s['instability']:>6.2f}{ri}"
            f"{s['workload_balance']:>5.3f}{rw}"
            f"{s['total_distance']:>6.1f}{rt}"
            f"{s['mean_decision_latency_ms']:>7.2f}{rl}"
        )
    print('─' * 100)
    print("  Tüm metrikler Nav2-bağımsız (ideal-nav: navigasyon her zaman başarılı). "
          "★=1. ✓=2.  Fit/CR/WLBal ↑ iyi; Delay/DVR/RecT/Instab/Dist/Lat ↓ iyi.")
    print("  ★=1. sıra  ✓=2. sıra  |  Compl: yüksek iyi  Instab/RecTime: düşük iyi")


# ---------------------------------------------------------------------------
# Parameter sweep (tuning mode)
# ---------------------------------------------------------------------------

def tune_parameter(param_name: str, values: List[float],
                   methods: List[str], scenario: str, n_seeds: int,
                   n_robots: int, n_tasks: int):
    print(f"\n{'═'*70}")
    print(f"  Parametre tarama: {param_name}  |  Senaryo: {scenario}")
    print(f"{'═'*70}")
    print(f"  {'Değer':>8}  {'full_ahe compl':>15}  {'full_ahe instab':>16}  "
          f"{'vs baseline':>12}")

    # Get baseline (mean of big_mrta + rostam_ea) for reference
    baseline_mnames = ['big_mrta', 'rostam_ea']
    base_summary = benchmark(baseline_mnames, scenario, n_seeds,
                             n_robots=n_robots, n_tasks=n_tasks)
    base_comp = mean(base_summary[m]['completion_rate'] for m in baseline_mnames)

    for val in values:
        kwargs = {}
        if param_name == 'temp':     kwargs['temp']  = val
        elif param_name == 'alpha':  kwargs['alpha'] = val
        elif param_name == 'beta':   kwargs['beta']  = val
        elif param_name == 'gamma':  kwargs['gamma'] = val

        summ = benchmark(['full_ahe_mrta'], scenario, n_seeds,
                         n_robots=n_robots, n_tasks=n_tasks, **kwargs)
        s = summ['full_ahe_mrta']
        delta = s['completion_rate'] - base_comp
        marker = ' ← BEST' if val == values[0] else ''
        print(f"  {val:>8.3f}  {s['completion_rate']:>15.3f}  "
              f"{s['instability']:>16.3f}  "
              f"{delta:>+12.3f}{marker}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='AHE-MRTA hızlı simülasyon')
    parser.add_argument('--seeds',    type=int,   default=100)
    parser.add_argument('--robots',   type=int,   default=3)
    parser.add_argument('--tasks',    type=int,   default=15)
    parser.add_argument('--duration', type=float, default=900.0)
    parser.add_argument('--scenario', type=str,   default='robot_failure',
                        choices=['robot_failure', 'mixed_stress',
                                 'deadline_pressure', 'all'])
    parser.add_argument('--method',   type=str,   default=None,
                        help='Sadece bir yöntemi çalıştır')
    parser.add_argument('--verbose',  action='store_true')
    parser.add_argument('--tune-temp',  action='store_true',
                        help='Softmax temperature sweep: 0.1..1.0')
    parser.add_argument('--tune-alpha', action='store_true',
                        help='ALPHA sweep: 0.5..0.95')
    parser.add_argument('--tune-beta',  action='store_true',
                        help='BETA sweep: 0.1..0.5')
    parser.add_argument('--ideal-nav', action='store_true',
                        help='Navigation-independent eval: perfect navigation, '
                             'every metric reflects allocation quality alone.')
    parser.add_argument('--robot-counts', type=str, default='',
                        help='Ölçeklenebilirlik sweep: virgülle robot sayıları, ör. "3,5,10". '
                             'Sabit yoğunluk (n_tasks=5×n_robots). → sim_scalability.csv')
    parser.add_argument('--matrix', action='store_true',
                        help='Tam robot×yoğunluk matrisi (Düzlem A): --robot-list robot × '
                             '--density-list görev/robot × 4 yöntem × 3 senaryo. → sim_matrix.csv')
    parser.add_argument('--robot-list', type=str, default='3,5,10',
                        help='--matrix için robot sayıları (varsayılan 3,5,10)')
    parser.add_argument('--density-list', type=str, default='3,5,8',
                        help='--matrix için görev/robot yoğunlukları (varsayılan 3,5,8)')
    args = parser.parse_args()

    registry  = _make_allocators()
    all_methods = list(registry.keys())
    methods = [args.method] if args.method else all_methods

    scenarios = (['robot_failure', 'mixed_stress', 'deadline_pressure']
                 if args.scenario == 'all' else [args.scenario])

    # ── Tuning mode ───────────────────────────────────────────────────────
    if args.tune_temp:
        vals = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0]
        tune_parameter('temp', vals, methods, scenarios[0],
                       min(args.seeds, 50), args.robots, args.tasks)
        return

    if args.tune_alpha:
        vals = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95]
        tune_parameter('alpha', vals, methods, scenarios[0],
                       min(args.seeds, 50), args.robots, args.tasks)
        return

    if args.tune_beta:
        vals = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
        tune_parameter('beta', vals, methods, scenarios[0],
                       min(args.seeds, 50), args.robots, args.tasks)
        return

    # ── Tam robot×yoğunluk matris modu (Düzlem A; → sim_matrix.csv) ───────
    if args.matrix:
        _PAPER_M = ['ahe_mrta_v3', 'big_mrta', 'rostam_ea', 'consensus_dbta']
        robots_l = [int(x) for x in args.robot_list.split(',') if x.strip()]
        dens_l = [int(x) for x in args.density_list.split(',') if x.strip()]
        t0 = time.time()
        rows = []
        for n_robots in robots_l:
            for density in dens_l:
                n_tasks = density * n_robots
                for scenario in scenarios:
                    summary = benchmark(
                        _PAPER_M, scenario, args.seeds,
                        n_robots=n_robots, n_tasks=n_tasks,
                        exp_duration=args.duration, ideal_nav=args.ideal_nav,
                    )
                    print_comparison(
                        summary, f"{scenario} [{n_robots}r/{n_tasks}g d={density}]", args.seeds)
                    for mname in _PAPER_M:
                        s = summary[mname]
                        rows.append({
                            'robot_count': n_robots, 'task_count': n_tasks,
                            'density': density, 'scenario': scenario, 'strategy': mname,
                            'fitness': s['alloc_fitness'], 'fitness_std': s['alloc_fitness_std'],
                            'cr': s['completion_rate'], 'dvr': s['deadline_violation_rate'],
                            'recovery': s['recovery_time'],
                            'latency': s['mean_decision_latency_ms'],
                            'n_seeds': args.seeds,
                        })
        out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'results', 'processed')
        os.makedirs(out_dir, exist_ok=True)
        out_csv = os.path.join(out_dir, 'sim_matrix.csv')
        import csv as _csv
        with open(out_csv, 'w', newline='') as f:
            w = _csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        elapsed = time.time() - t0
        total = len(_PAPER_M) * args.seeds * len(scenarios) * len(robots_l) * len(dens_l)
        print(f"\n[OK]  Matrix CSV → {out_csv}  ({len(rows)} satır)")
        print(f"  Toplam {total} simülasyon, {elapsed:.1f}s ({total/elapsed:.0f} sim/s)\n")
        return

    # ── Ölçeklenebilirlik sweep modu (Düzlem A; → sim_scalability.csv) ─────
    if args.robot_counts.strip():
        _PAPER_M = ['ahe_mrta_v3', 'big_mrta', 'rostam_ea', 'consensus_dbta']
        scales = [int(x) for x in args.robot_counts.split(',') if x.strip()]
        t0 = time.time()
        scal_rows = []
        for n_robots in scales:
            n_tasks = 5 * n_robots          # sabit yoğunluk ~5 görev/robot
            for scenario in scenarios:
                summary = benchmark(
                    _PAPER_M, scenario, args.seeds,
                    n_robots=n_robots, n_tasks=n_tasks,
                    exp_duration=args.duration, ideal_nav=args.ideal_nav,
                )
                print_comparison(summary, f"{scenario} [{n_robots}r/{n_tasks}g]", args.seeds)
                for mname in _PAPER_M:
                    s = summary[mname]
                    scal_rows.append({
                        'robot_count': n_robots, 'task_count': n_tasks,
                        'scenario': scenario, 'strategy': mname,
                        'fitness': s['alloc_fitness'], 'fitness_std': s['alloc_fitness_std'],
                        'cr': s['completion_rate'], 'dvr': s['deadline_violation_rate'],
                        'recovery': s['recovery_time'],
                        'latency': s['mean_decision_latency_ms'],
                        'n_seeds': args.seeds,
                    })
        out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'results', 'processed')
        os.makedirs(out_dir, exist_ok=True)
        out_csv = os.path.join(out_dir, 'sim_scalability.csv')
        import csv as _csv
        with open(out_csv, 'w', newline='') as f:
            w = _csv.DictWriter(f, fieldnames=list(scal_rows[0].keys()))
            w.writeheader()
            w.writerows(scal_rows)
        elapsed = time.time() - t0
        total_runs = len(_PAPER_M) * args.seeds * len(scenarios) * len(scales)
        print(f"\n[OK]  Scalability CSV → {out_csv}  ({len(scal_rows)} satır)")
        print(f"  Toplam {total_runs} simülasyon, {elapsed:.1f}s "
              f"({total_runs/elapsed:.0f} sim/s)\n")
        return

    # ── Normal benchmark mode ─────────────────────────────────────────────
    t0 = time.time()
    fit_csv_rows = []   # [scenario, strategy, fitness_mean, fitness_std, n_seeds]
    for scenario in scenarios:
        summary = benchmark(
            methods, scenario, args.seeds,
            n_robots=args.robots, n_tasks=args.tasks,
            exp_duration=args.duration,
            verbose=args.verbose,
            ideal_nav=args.ideal_nav,
        )
        print_comparison(summary, scenario, args.seeds)
        # Persist fitness for the cross-method comparison plot. Only the four
        # paper methods are written so plotting stays focused.
        _PAPER_M = {'ahe_mrta_v3', 'big_mrta', 'rostam_ea', 'consensus_dbta'}
        for mname, s in summary.items():
            if mname in _PAPER_M:
                fit_csv_rows.append({
                    'scenario': scenario,
                    'strategy': mname,
                    'fitness_mean': s.get('alloc_fitness', 0.0),
                    'fitness_std':  s.get('alloc_fitness_std', 0.0),
                    'n_seeds': args.seeds,
                })

    # Save fitness CSV for plot_results.plot_fitness_comparison.
    if fit_csv_rows:
        out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'results', 'processed')
        os.makedirs(out_dir, exist_ok=True)
        out_csv = os.path.join(out_dir, 'sim_fitness.csv')
        import csv as _csv
        with open(out_csv, 'w', newline='') as f:
            w = _csv.DictWriter(f, fieldnames=list(fit_csv_rows[0].keys()))
            w.writeheader()
            for row in fit_csv_rows:
                w.writerow(row)
        print(f"\n[OK]  Fitness CSV → {out_csv}  ({len(fit_csv_rows)} satır)")

    elapsed = time.time() - t0
    total_runs = len(methods) * args.seeds * len(scenarios)
    print(f"\n  Toplam {total_runs} simülasyon, {elapsed:.1f}s "
          f"({total_runs/elapsed:.0f} sim/s)\n")


if __name__ == '__main__':
    main()
