"""
Phase 9 — Experiment Runner Node (v2: Gazebo-ready)

Orchestrates one full experiment:
  strategy × scenario × seed × robot_count × task_count

When run inside a Gazebo launch (phase9_experiments.launch.py), set the
``gazebo_startup_delay_sec`` parameter to allow Gazebo + Nav2 to initialise
before the experiment begins.  The standalone runner uses the default (0.0).

Parameters
----------
strategy        : str   — allocator key from ALLOCATOR_REGISTRY
scenario        : str   — dynamic_task_arrival | deadline_pressure |
                          robot_failure | mixed_stress
robot_count     : int   — 3 (MVP) or 5 (paper scale)
task_count      : int   — 15 (MVP) or 25 (paper scale)
seed            : int   — experiment seed
experiment_id   : str   — used as directory name (auto-generated if empty)
results_base    : str   — parent of results/raw/
gazebo_startup_delay_sec : float — seconds to wait before starting (default 0.0)

Lifecycle
---------
STARTING (waiting Nav2) → RUNNING → DONE (all tasks finished or timeout)

After DONE the node writes a ``DONE`` sentinel file and sends SIGTERM so
the enclosing launch process exits gracefully.

CSV outputs  (under results/raw/<experiment_id>/)
---------
metadata.yaml, task_events.csv, robot_state_timeseries.csv,
robot_workload.csv, allocation_events.csv, method_runtime.csv,
communication_metrics.csv, [ecosystem_metrics.csv], summary.csv, DONE
"""

import csv
import math
import os
import random
import signal
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import rclpy
from rclpy.node import Node

import yaml

from geometry_msgs.msg import PoseStamped
from m_ahe_mrta_msgs.msg import (
    AllocationEvent, EcosystemState, LocalExecutionFeedback,
    OptimizedTaskQueue, RobotStatusSummary, TaskInfo, TaskPool, TaskWaypoint,
)

from .baselines.base_allocator import (
    AllocationResult, EcosystemContext, RobotState as RS, TaskState as TS,
    cheapest_insertion,
)
from .baselines.greedy_nearest import GreedyNearestAllocator
from .baselines.deadline_aware import DeadlineAwareAllocator
from .baselines.auction_based import AuctionBasedAllocator
from .baselines.static_weighted import StaticWeightedAllocator
from .baselines.big_mrta import BigMRTAAllocator
from .baselines.rostam_ea import RoSTAMEAAllocator
from .baselines.consensus_dbta import ConsensusDBTAAllocator
from .baselines.ahe_variants import (
    AHEMRTAv3Allocator,
    AHEMRTAv3NoBipartiteAllocator,
    AHEMRTAv3NoDenseInitAllocator,
    AHEMRTAv3NoRecoveryAllocator,
    AHEMRTAv3FixedWeightsAllocator,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALLOCATOR_REGISTRY = {
    'greedy_nearest':               GreedyNearestAllocator,
    'deadline_aware':               DeadlineAwareAllocator,
    'auction_based':                AuctionBasedAllocator,
    'static_weighted':              StaticWeightedAllocator,
    'big_mrta':                     BigMRTAAllocator,
    'rostam_ea':                    RoSTAMEAAllocator,
    'consensus_dbta':               ConsensusDBTAAllocator,
    'ahe_mrta_v3':                  AHEMRTAv3Allocator,
    'ahe_mrta_v3_no_bipartite':     AHEMRTAv3NoBipartiteAllocator,
    'ahe_mrta_v3_no_dense_init':    AHEMRTAv3NoDenseInitAllocator,
    'ahe_mrta_v3_no_recovery':      AHEMRTAv3NoRecoveryAllocator,
    'ahe_mrta_v3_fixed_weights':    AHEMRTAv3FixedWeightsAllocator,
}

AHE_STRATEGIES = {
    'ahe_mrta_v3', 'ahe_mrta_v3_no_bipartite', 'ahe_mrta_v3_no_dense_init',
    'ahe_mrta_v3_no_recovery', 'ahe_mrta_v3_fixed_weights',
}

# ---------------------------------------------------------------------------
# Scenario parameters
# ---------------------------------------------------------------------------

_DEADLINE_MULTIPLIERS = {
    'dynamic_task_arrival': 1.0,
    'deadline_pressure':    0.4,  # tight deadlines
    'robot_failure':        1.0,
    'mixed_stress':         0.5,
}

_GRID = [
    # Upper half  (y > 3.0, above divider wall) — kept at y=7 to avoid map-edge AMCL drift
    (-6.0, 7.0), (-2.0, 7.0), (0.0, 7.0), (2.0, 7.0), (6.0, 7.0),
    # Inter-shelf corridor (y=6.0, between shelf tops at y=5.5 and shelf bottoms at y=6.5)
    # Moved from (-2,6),(2,6) and (-3,5),(3,5) — those were 0.71m from cylinders at (±2.5,5.5),
    # inside the inflation zone (min safe = 0.72m).
    (-6.0, 6.0), (-4.0, 6.0), (-1.0, 6.0), (0.0, 6.0), (1.0, 6.0), (4.0, 6.0), (6.0, 6.0),
    # Above-divider mid-row (y=2.0) — far from divider wall (y=3) and shelves (y=±4.5)
    # x in {-5, -3, 0, 3, 5} avoids shelf x columns (±5 column has gap at |y|<3.5) and
    # leaves x∈[-9,-7] reserved for robot spawn area.
    (-5.0, 2.0), (-3.0, 2.0), (0.0, 2.0), (3.0, 2.0), (5.0, 2.0),
    # Central corridor  (y ∈ [-1.5, 1.5])
    (-6.0, 1.5), (6.0, 1.5), (-5.0, 0.0), (5.0, 0.0),
    (-6.0, -1.5), (6.0, -1.5), (-4.0, 0.0), (4.0, 0.0),
    # Below-divider mid-row (y=-2.0) — symmetric mirror of y=2.0 row
    (-5.0, -2.0), (-3.0, -2.0), (0.0, -2.0), (3.0, -2.0), (5.0, -2.0),
    # Lower half  (y < -3.0, below divider wall)
    (-6.0, -4.0), (-2.0, -4.0), (2.0, -4.0), (6.0, -4.0),
    # Inter-shelf corridor (y=-6.0, between shelf tops at y=-5.5 and shelf bottoms at y=-6.5)
    (-6.0, -6.0), (-4.0, -6.0), (-1.0, -6.0), (0.0, -6.0), (1.0, -6.0), (4.0, -6.0), (6.0, -6.0),
    # Lower edge row (y=-7.0) — symmetric mirror of y=7.0
    (0.0, -7.0),
]

EXPERIMENT_TIMEOUT_SEC = 900.0   # 15 minutes max per experiment
ALLOC_PERIOD_SEC       = 5.0
TIMESERIES_PERIOD_SEC  = 2.0
FAILURE_TIME_OFFSET    = 45.0    # seconds after experiment start before injecting failure


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class ExperimentRunnerNode(Node):

    def __init__(self) -> None:
        super().__init__('experiment_runner_node')

        # Parameters
        self.declare_parameter('strategy', 'static_weighted')
        self.declare_parameter('scenario', 'dynamic_task_arrival')
        self.declare_parameter('robot_count', 3)
        self.declare_parameter('task_count', 15)
        self.declare_parameter('seed', 1)
        self.declare_parameter('experiment_id', '')
        self.declare_parameter('results_base',
                               os.path.expanduser('~/multi_ahe/results/raw'))
        self.declare_parameter('gazebo_startup_delay_sec', 0.0)

        self._strategy: str = self.get_parameter('strategy').value
        self._scenario: str = self.get_parameter('scenario').value
        self._robot_count: int = self.get_parameter('robot_count').value
        self._task_count: int = self.get_parameter('task_count').value
        self._seed: int = self.get_parameter('seed').value
        self._results_base: str = self.get_parameter('results_base').value
        self._startup_delay: float = self.get_parameter('gazebo_startup_delay_sec').value

        exp_id = self.get_parameter('experiment_id').value
        if not exp_id:
            exp_id = (f'exp_{self._scenario}_{self._strategy}'
                      f'_r{self._robot_count}t{self._task_count}'
                      f'_seed{self._seed:02d}')
        self._exp_id = exp_id
        self._results_dir = os.path.join(self._results_base, exp_id)

        self._robots = [f'robot_{i + 1}' for i in range(self._robot_count)]
        self._rng = random.Random(self._seed)

        # Allocator
        if self._strategy not in ALLOCATOR_REGISTRY:
            raise ValueError(f'Unknown strategy: {self._strategy}. '
                             f'Valid: {list(ALLOCATOR_REGISTRY)}')
        alloc_cls = ALLOCATOR_REGISTRY[self._strategy]
        self._allocator = alloc_cls()
        if hasattr(self._allocator, 'seed'):
            self._allocator.seed(self._seed)

        # Startup state
        self._node_start_time: float = time.monotonic()
        self._startup_done: bool = (self._startup_delay <= 0.0)
        self._start_time: Optional[float] = None  # set when experiment begins

        # Experiment state
        self._tasks: List[TS] = []
        self._task_map: Dict[str, TS] = {}
        self._robot_states: Dict[str, Optional[RS]] = {r: None for r in self._robots}
        self._eco_context: Optional[EcosystemContext] = None
        self._assigned: Dict[str, str] = {}        # task_id -> robot_id
        self._queues: Dict[str, List[str]] = {r: [] for r in self._robots}
        self._failed_robots: Set[str] = set()
        self._pool_version: int = 0
        self._alloc_count: int = 0
        self._alloc_latencies: List[float] = []
        self._force_realloc: bool = False
        self._experiment_done: bool = False

        # Batch / failure schedules (populated after startup)
        self._activation_batches: List[tuple] = []
        self._next_batch_idx: int = 0
        self._failure_events: List[tuple] = []
        self._failures_injected: Set[str] = set()
        self._failure_inject_time: Optional[float] = None
        self._failure_related_tasks: Set[str] = set()

        # Per-task timing for summary metrics
        self._task_activation_wall: Dict[str, float] = {}  # task_id -> wall clock
        self._task_completion_wall: Dict[str, float] = {}  # task_id -> wall clock
        self._task_deadline_wall: Dict[str, float] = {}    # task_id -> abs deadline

        # Workload tracking
        self._robot_tasks_completed: Dict[str, int] = {r: 0 for r in self._robots}
        self._robot_tasks_failed:    Dict[str, int] = {r: 0 for r in self._robots}
        self._tasks_completed_total: int = 0   # direct counter, resilient to dict key issues
        self._tasks_failed_total: int = 0
        self._robot_distances:       Dict[str, float] = {r: 0.0 for r in self._robots}
        self._robot_last_pose:       Dict[str, Optional[tuple]] = {r: None for r in self._robots}

        # Task failure backoff: skip permanently-stuck tasks
        self._task_fail_count:  Dict[str, int]   = {}
        self._task_skip_until:  Dict[str, float] = {}
        self._max_task_retries: int   = 5
        self._task_backoff_sec: float = 30.0

        # CSV setup
        os.makedirs(self._results_dir, exist_ok=True)
        self._setup_csv()
        self._write_metadata()

        # Publishers
        self._pool_pub = self.create_publisher(TaskPool, '/tasks/global_pool', 10)
        self._alloc_event_pub = self.create_publisher(
            AllocationEvent, '/allocation/events', 10)
        self._queue_pubs = {
            r: self.create_publisher(OptimizedTaskQueue,
                                     f'/{r}/optimized_task_queue', 10)
            for r in self._robots
        }

        # Subscribers
        self.create_subscription(EcosystemState, '/ecosystem/debug_state',
                                 self._eco_cb, 10)
        for r in self._robots:
            self.create_subscription(
                RobotStatusSummary, f'/{r}/status_summary',
                lambda msg, rr=r: self._status_cb(rr, msg), 10)
            self.create_subscription(
                AllocationEvent, f'/{r}/task_feedback',
                self._task_feedback_cb, 10)

        # Timers
        self.create_timer(1.0, self._publish_pool)
        self.create_timer(ALLOC_PERIOD_SEC, self._maybe_allocate)
        self.create_timer(TIMESERIES_PERIOD_SEC, self._log_timeseries)
        self.create_timer(1.0, self._check_batch_schedule)
        self.create_timer(1.0, self._check_failure_schedule)
        self.create_timer(2.0, self._check_done)
        self.create_timer(1.0, self._check_startup)

        if self._startup_done:
            self._start_experiment()
        else:
            self.get_logger().info(
                f'ExperimentRunner: waiting {self._startup_delay:.0f}s for Nav2 to initialise...'
            )

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def _check_startup(self) -> None:
        if self._startup_done:
            return
        elapsed_wall = time.monotonic() - self._node_start_time
        if elapsed_wall >= self._startup_delay:
            self._startup_done = True
            self.get_logger().info('Nav2 startup complete — starting experiment.')
            self._start_experiment()

    def _start_experiment(self) -> None:
        now = self.get_clock().now().nanoseconds / 1e9
        self._start_time = now
        self._tasks = self._generate_tasks(now)
        self._task_map = {t.task_id: t for t in self._tasks}
        self._activation_batches = self._plan_batches()
        self._failure_events = self._plan_failures()
        self._write_task_positions()
        self._activate_next_batch()
        self.get_logger().info(
            f'ExperimentRunner started: strategy={self._strategy}, '
            f'scenario={self._scenario}, seed={self._seed}, '
            f'robots={self._robot_count}, tasks={self._task_count}\n'
            f'Results → {self._results_dir}'
        )

    # ------------------------------------------------------------------
    # Task generation
    # ------------------------------------------------------------------

    def _generate_tasks(self, now: float) -> List[TS]:
        deadline_mult = _DEADLINE_MULTIPLIERS.get(self._scenario, 1.0)
        grid = list(_GRID)
        self._rng.shuffle(grid)
        while len(grid) < self._task_count:
            grid.append((self._rng.uniform(-8.0, 8.0),
                         self._rng.uniform(-8.0, 8.0)))
        tasks = []
        for i in range(self._task_count):
            x, y = grid[i]
            raw_deadline = self._rng.uniform(90.0, 300.0) * deadline_mult
            deadline_abs = now + raw_deadline
            task = TS(
                task_id=f'task_{i + 1:03d}',
                position=(float(x), float(y)),
                priority=self._rng.randint(1, 3),
                activation_time=now,
                deadline=deadline_abs,
                service_time=float(self._rng.uniform(2.0, 8.0)),
                active=False,
                completed=False,
            )
            self._task_deadline_wall[task.task_id] = deadline_abs
            tasks.append(task)
        return tasks

    def _plan_batches(self) -> List[tuple]:
        n = self._task_count
        b = max(1, n // 3)
        if self._scenario in ('dynamic_task_arrival', 'mixed_stress'):
            return [(0.0, b), (30.0, b), (60.0, n - 2 * b)]
        else:
            return [(0.0, n)]

    def _plan_failures(self) -> List[tuple]:
        if self._scenario in ('robot_failure', 'mixed_stress'):
            offset = FAILURE_TIME_OFFSET + self._rng.uniform(-5.0, 5.0)
            return [(offset, 'robot_2')]
        return []

    # ------------------------------------------------------------------
    # Batch / failure schedule
    # ------------------------------------------------------------------

    def _activate_next_batch(self) -> None:
        if self._next_batch_idx >= len(self._activation_batches):
            return
        _, count = self._activation_batches[self._next_batch_idx]
        now = self.get_clock().now().nanoseconds / 1e9
        activated = 0
        for task in self._tasks:
            if activated >= count:
                break
            if not task.active and not task.completed:
                task.active = True
                task.activation_time = now
                self._task_activation_wall[task.task_id] = now
                activated += 1
                self._log_task_event(task.task_id, 'activated', '')
        self._pool_version += 1
        self._next_batch_idx += 1
        self._force_realloc = True

    def _check_batch_schedule(self) -> None:
        if not self._startup_done or self._experiment_done:
            return
        if self._start_time is None:
            return
        now = self.get_clock().now().nanoseconds / 1e9
        elapsed = now - self._start_time
        if self._next_batch_idx < len(self._activation_batches):
            offset, _ = self._activation_batches[self._next_batch_idx]
            if elapsed >= offset:
                self._activate_next_batch()

    def _check_failure_schedule(self) -> None:
        if not self._startup_done or self._experiment_done:
            return
        if self._start_time is None:
            return
        now = self.get_clock().now().nanoseconds / 1e9
        elapsed = now - self._start_time
        for offset, robot_id in self._failure_events:
            if robot_id not in self._failures_injected and elapsed >= offset:
                self._inject_failure(robot_id)
                self._failures_injected.add(robot_id)

    def _inject_failure(self, robot_id: str) -> None:
        self._failed_robots.add(robot_id)
        now = self.get_clock().now().nanoseconds / 1e9
        self._failure_inject_time = now
        self.get_logger().warning(f'[FAILURE INJECTED] {robot_id} at t={self._elapsed():.1f}s')
        # Track tasks assigned to failed robot for recovery-time computation
        failed_tasks = [tid for tid, rid in self._assigned.items() if rid == robot_id]
        for tid in failed_tasks:
            self._failure_related_tasks.add(tid)
            self._assigned.pop(tid, None)
            for q in self._queues.values():
                if tid in q:
                    q.remove(tid)
        ev = AllocationEvent()
        ev.header.stamp = self.get_clock().now().to_msg()
        ev.event_type = 'robot_failure'
        ev.robot_id = robot_id
        ev.task_id = ''
        ev.severity = 2
        ev.trigger_replan = True
        self._alloc_event_pub.publish(ev)
        self._force_realloc = True
        self._log_alloc_event('robot_failure', robot_id, '', 0.0)

    # ------------------------------------------------------------------
    # Subscribers
    # ------------------------------------------------------------------

    def _status_cb(self, robot_id: str, msg: RobotStatusSummary) -> None:
        pose = (msg.current_pose.pose.position.x,
                msg.current_pose.pose.position.y)
        state = RS(
            robot_id=robot_id,
            pose=pose,
            battery=1.0 - msg.battery_state * 0.33,
            available=(msg.availability_state != 2
                       and robot_id not in self._failed_robots),
            current_task_id=msg.current_task_id,
            queue=list(self._queues.get(robot_id, [])),
            failure_risk=1.0 if msg.failure_flag else 0.0,
            navigation_state=msg.navigation_state,
            failure_flag=msg.failure_flag,
            battery_state=msg.battery_state,
        )
        self._robot_states[robot_id] = state

        last = self._robot_last_pose.get(robot_id)
        if last is not None:
            self._robot_distances[robot_id] += math.hypot(
                pose[0] - last[0], pose[1] - last[1])
        self._robot_last_pose[robot_id] = pose

    def _task_feedback_cb(self, msg: AllocationEvent) -> None:
        tid = msg.task_id
        task = self._task_map.get(tid)
        if task is None:
            return
        now = self.get_clock().now().nanoseconds / 1e9

        if msg.event_type == 'task_completed':
            task.completed = True
            task.active = False
            self._task_completion_wall[tid] = now
            self._assigned.pop(tid, None)
            self._task_fail_count.pop(tid, None)
            self._task_skip_until.pop(tid, None)
            for q in self._queues.values():
                if tid in q:
                    q.remove(tid)
            self._robot_tasks_completed[msg.robot_id] = (
                self._robot_tasks_completed.get(msg.robot_id, 0) + 1)
            self._tasks_completed_total += 1
            self._log_task_event(tid, 'completed', msg.robot_id)

        elif msg.event_type == 'task_failed':
            self._failure_related_tasks.add(tid)
            self._assigned.pop(tid, None)
            for q in self._queues.values():
                if tid in q:
                    q.remove(tid)
            self._robot_tasks_failed[msg.robot_id] = (
                self._robot_tasks_failed.get(msg.robot_id, 0) + 1)
            self._tasks_failed_total += 1
            self._task_fail_count[tid] = self._task_fail_count.get(tid, 0) + 1
            if self._task_fail_count[tid] >= self._max_task_retries:
                skip_until = self.get_clock().now().nanoseconds / 1e9 + self._task_backoff_sec
                self._task_skip_until[tid] = skip_until
                self.get_logger().warn(
                    f'[Runner] Task {tid} failed {self._task_fail_count[tid]}x — '
                    f'backing off {self._task_backoff_sec}s'
                )
            else:
                self._force_realloc = True
            self._log_task_event(tid, 'failed', msg.robot_id)

    def _eco_cb(self, msg: EcosystemState) -> None:
        if self._strategy not in AHE_STRATEGIES:
            return
        self._eco_context = EcosystemContext(
            dominance=list(msg.dominance_values),
            context_vector=list(msg.context_vector),
            allocation_weights=list(msg.allocation_weights),
            cooperation_matrix=[list(msg.cooperation_values)],
            suppression_matrix=[list(msg.suppression_values)],
            heuristic_names=list(msg.heuristic_names),
        )
        if msg.dominance_values:
            dom = list(msg.dominance_values)
            dom_idx = dom.index(max(dom))
            self._log_ecosystem(msg, dom_idx)

    # ------------------------------------------------------------------
    # Allocation
    # ------------------------------------------------------------------

    def _get_robots_for_alloc(self) -> List[RS]:
        robots = []
        for r in self._robots:
            state = self._robot_states.get(r)
            if state is not None:
                robots.append(state)
            else:
                robots.append(RS(
                    robot_id=r, pose=(0.0, 0.0),
                    battery=1.0, available=(r not in self._failed_robots),
                    current_task_id='', queue=[],
                ))
        return robots

    def _get_tasks_for_alloc(self) -> List[TS]:
        now_s = self.get_clock().now().nanoseconds / 1e9
        return [t for t in self._tasks if t.active and not t.completed
                and t.task_id not in self._assigned
                and now_s >= self._task_skip_until.get(t.task_id, 0.0)]

    def _maybe_allocate(self) -> None:
        if not self._startup_done or self._experiment_done:
            return
        unassigned = self._get_tasks_for_alloc()
        if not self._force_realloc and not unassigned:
            return
        if (self._force_realloc
                and isinstance(self._allocator, AHEMRTAv3NoRecoveryAllocator)
                and self._alloc_count > 0):
            self._force_realloc = False
            return
        self._force_realloc = False
        self._run_allocation()

    def _run_allocation(self) -> None:
        robots = self._get_robots_for_alloc()
        now_s = self.get_clock().now().nanoseconds / 1e9
        tasks = [t for t in self._tasks if t.active and not t.completed
                 and now_s >= self._task_skip_until.get(t.task_id, 0.0)]
        if not tasks:
            return

        result: AllocationResult = self._allocator.allocate(
            robots, tasks,
            current_time=self.get_clock().now().nanoseconds / 1e9,
            context=self._eco_context,
        )
        self._alloc_count += 1
        self._alloc_latencies.append(result.latency_ms)

        for rid, tids in result.queues.items():
            self._queues[rid] = list(tids)
            for tid in tids:
                if tid not in self._assigned:
                    self._assigned[tid] = rid
                    self._log_task_event(tid, 'assigned', rid)

        for r in self._robots:
            self._publish_queue(r, result.queues.get(r, []))

        ts = self.get_clock().now().nanoseconds / 1e9
        self._rt_writer.writerow([
            f'{ts:.3f}', self._strategy, self._alloc_count,
            sum(len(q) for q in result.queues.values()),
            f'{result.latency_ms:.2f}',
        ])
        self._rt_file.flush()
        self._comm_writer.writerow([
            f'{ts:.3f}', self._strategy, self._alloc_count,
            result.communication_footprint_bytes,
        ])
        self._comm_file.flush()
        self._log_alloc_event('allocation_run', '', '', result.latency_ms)

    # ------------------------------------------------------------------
    # Publisher helpers
    # ------------------------------------------------------------------

    def _publish_pool(self) -> None:
        if self._experiment_done or not self._startup_done:
            return
        msg = TaskPool()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.pool_version = self._pool_version
        for task in self._tasks:
            info = TaskInfo()
            info.task_id = task.task_id
            pose = PoseStamped()
            pose.header.frame_id = 'map'
            pose.pose.position.x = task.position[0]
            pose.pose.position.y = task.position[1]
            pose.pose.orientation.w = 1.0
            info.target_pose = pose
            info.priority_level = task.priority
            info.service_time = task.service_time
            info.deadline = task.deadline
            info.active = task.active
            info.completed = task.completed
            msg.tasks.append(info)
        self._pool_pub.publish(msg)

    def _publish_queue(self, robot_id: str, task_ids: List[str]) -> None:
        msg = OptimizedTaskQueue()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = f'{robot_id}/map'
        msg.robot_id = robot_id
        msg.queue_version = self._alloc_count
        msg.execution_mode = 'sequential'
        msg.replan_required = False
        for tid in task_ids:
            task = self._task_map.get(tid)
            if task is None:
                continue
            wp = TaskWaypoint()
            wp.task_id = tid
            pose = PoseStamped()
            pose.header.frame_id = f'{robot_id}/map'
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = task.position[0]
            pose.pose.position.y = task.position[1]
            pose.pose.orientation.w = 1.0
            wp.target_pose = pose
            wp.priority_level = task.priority
            wp.service_time = task.service_time
            wp.is_critical = task.priority >= 3
            wp.allow_skip = not wp.is_critical
            msg.waypoints.append(wp)
        self._queue_pubs[robot_id].publish(msg)

    # ------------------------------------------------------------------
    # Experiment termination
    # ------------------------------------------------------------------

    def _check_done(self) -> None:
        if not self._startup_done or self._experiment_done:
            return
        elapsed = self._elapsed()
        if elapsed > EXPERIMENT_TIMEOUT_SEC:
            self.get_logger().warning('Experiment timeout — writing summary.')
            self._finish()
            return
        # All tasks either completed or inactive (unactivated tasks don't count)
        if self._tasks:
            active_incomplete = [t for t in self._tasks if t.active and not t.completed]
            all_activated = (self._next_batch_idx >= len(self._activation_batches))
            if all_activated and not active_incomplete:
                self.get_logger().info(f'All tasks done at t={elapsed:.1f}s')
                self._finish()

    def _finish(self) -> None:
        self._experiment_done = True
        self._write_workload_csv()
        self._write_summary_csv()
        # Write DONE sentinel so the shell script can detect completion
        done_path = os.path.join(self._results_dir, 'DONE')
        with open(done_path, 'w') as f:
            f.write(f'{self._elapsed():.1f}\n')
        self.get_logger().info(
            f'Experiment {self._exp_id} complete. '
            f'Results: {self._results_dir}'
        )
        # Self-terminate after 2 seconds (allow CSV flush)
        self.create_timer(2.0, self._shutdown_self)

    def _shutdown_self(self) -> None:
        self.get_logger().info('Sending SIGTERM to terminate launch process.')
        os.kill(os.getpid(), signal.SIGTERM)

    def _elapsed(self) -> float:
        now = self.get_clock().now().nanoseconds / 1e9
        return now - (self._start_time or now)

    # ------------------------------------------------------------------
    # CSV setup and logging
    # ------------------------------------------------------------------

    def _setup_csv(self) -> None:
        def _open(name, header):
            f = open(os.path.join(self._results_dir, name), 'w', newline='')
            w = csv.writer(f)
            w.writerow(header)
            return f, w

        self._te_file, self._te_writer = _open('task_events.csv', [
            'timestamp_s', 'task_id', 'event', 'robot_id',
            'strategy', 'scenario', 'seed',
        ])
        self._tp_file, self._tp_writer = _open('task_positions.csv', [
            'task_id', 'x', 'y', 'priority', 'strategy', 'scenario', 'seed',
        ])
        self._ts_file, self._ts_writer = _open('robot_state_timeseries.csv', [
            'timestamp_s', 'robot_id', 'x', 'y', 'battery_state',
            'nav_state', 'avail_state', 'current_task_id', 'failure_flag',
        ])
        self._ae_file, self._ae_writer = _open('allocation_events.csv', [
            'timestamp_s', 'event_type', 'robot_id', 'task_id',
            'strategy', 'latency_ms',
        ])
        self._rt_file, self._rt_writer = _open('method_runtime.csv', [
            'timestamp_s', 'strategy', 'alloc_num',
            'tasks_in_queues', 'latency_ms',
        ])
        self._comm_file, self._comm_writer = _open('communication_metrics.csv', [
            'timestamp_s', 'strategy', 'alloc_num', 'footprint_bytes',
        ])
        eco_path = os.path.join(self._results_dir, 'ecosystem_metrics.csv')
        self._eco_file = open(eco_path, 'w', newline='')
        self._eco_writer = csv.writer(self._eco_file)
        self._eco_writer.writerow([
            'timestamp_s', 'dominant_heuristic', 'dominant_value',
            'w_d', 'w_p', 'w_b', 'w_l', 'w_f', 'w_t', 'w_r',
        ] + [f'd_{i}' for i in range(7)])

    def _write_metadata(self) -> None:
        meta = {
            'experiment_id': self._exp_id,
            'strategy': self._strategy,
            'scenario': self._scenario,
            'robot_count': self._robot_count,
            'task_count': self._task_count,
            'target_count': self._task_count,  # alias for consolidate_results
            'seed': self._seed,
            'timeout_sec': EXPERIMENT_TIMEOUT_SEC,
            'gazebo_startup_delay_sec': self._startup_delay,
        }
        with open(os.path.join(self._results_dir, 'metadata.yaml'), 'w') as f:
            yaml.dump(meta, f)

    def _write_task_positions(self) -> None:
        for task in self._tasks:
            self._tp_writer.writerow([
                task.task_id, f'{task.position[0]:.3f}', f'{task.position[1]:.3f}',
                task.priority, self._strategy, self._scenario, self._seed,
            ])
        self._tp_file.flush()

    def _log_task_event(self, task_id: str, event: str, robot_id: str) -> None:
        ts = self.get_clock().now().nanoseconds / 1e9
        self._te_writer.writerow([
            f'{ts:.3f}', task_id, event, robot_id,
            self._strategy, self._scenario, self._seed,
        ])
        self._te_file.flush()

    def _log_alloc_event(self, event_type: str, robot_id: str,
                         task_id: str, latency_ms: float) -> None:
        ts = self.get_clock().now().nanoseconds / 1e9
        self._ae_writer.writerow([
            f'{ts:.3f}', event_type, robot_id, task_id,
            self._strategy, f'{latency_ms:.2f}',
        ])
        self._ae_file.flush()

    def _log_timeseries(self) -> None:
        if not self._startup_done or self._experiment_done:
            return
        ts = self.get_clock().now().nanoseconds / 1e9
        for r in self._robots:
            state = self._robot_states.get(r)
            if state is None:
                continue
            self._ts_writer.writerow([
                f'{ts:.3f}', r,
                f'{state.pose[0]:.3f}', f'{state.pose[1]:.3f}',
                state.battery_state, state.navigation_state,
                0 if state.available else 2,
                state.current_task_id,
                int(state.failure_flag),
            ])
        self._ts_file.flush()

    def _log_ecosystem(self, msg: EcosystemState, dom_idx: int) -> None:
        ts = self.get_clock().now().nanoseconds / 1e9
        names = list(msg.heuristic_names) if msg.heuristic_names else [str(i) for i in range(7)]
        dom_name = names[dom_idx] if dom_idx < len(names) else str(dom_idx)
        dom_val = msg.dominance_values[dom_idx] if msg.dominance_values else 0.0
        weights = list(msg.allocation_weights) if msg.allocation_weights else [0.0] * 7
        doms = list(msg.dominance_values) if msg.dominance_values else [0.0] * 7
        self._eco_writer.writerow(
            [f'{ts:.3f}', dom_name, f'{dom_val:.4f}']
            + [f'{w:.4f}' for w in weights[:7]]
            + [f'{d:.4f}' for d in doms[:7]]
        )
        self._eco_file.flush()

    def _write_workload_csv(self) -> None:
        path = os.path.join(self._results_dir, 'robot_workload.csv')
        with open(path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['experiment_id', 'scenario', 'strategy', 'seed',
                        'robot_count', 'robot_id',
                        'assigned_tasks', 'completed_tasks', 'failed_tasks',
                        'approx_distance_m'])
            for r in self._robots:
                completed = self._robot_tasks_completed.get(r, 0)
                failed = self._robot_tasks_failed.get(r, 0)
                w.writerow([
                    self._exp_id, self._scenario, self._strategy, self._seed,
                    self._robot_count, r,
                    completed + failed,
                    completed,
                    failed,
                    f"{self._robot_distances.get(r, 0.0):.2f}",
                ])

    def _write_summary_csv(self) -> None:
        total = len(self._tasks)
        completed_obj = sum(1 for t in self._tasks if t.completed)
        completed = max(self._tasks_completed_total, completed_obj)
        # tasks_failed = permanently abandoned tasks (0 in this system — all
        # nav failures trigger reallocation, counted separately as nav_retries).
        failed_tasks = 0
        active_remaining = total - completed
        comp_rate = completed / max(1, total)

        # Makespan: from experiment start to last completion (or timeout)
        makespan = self._elapsed()
        if makespan > EXPERIMENT_TIMEOUT_SEC:
            makespan = EXPERIMENT_TIMEOUT_SEC

        # Average task delay (completion - activation per task)
        delays = []
        for task in self._tasks:
            if task.completed:
                act_t = self._task_activation_wall.get(task.task_id, self._start_time or 0.0)
                cmp_t = self._task_completion_wall.get(task.task_id, makespan)
                delays.append(cmp_t - act_t)
        avg_delay = sum(delays) / len(delays) if delays else 0.0

        # Deadline violation rate
        dl_violated = 0
        for task in self._tasks:
            if task.completed:
                cmp_t = self._task_completion_wall.get(task.task_id, 0.0)
                deadline = self._task_deadline_wall.get(task.task_id, float('inf'))
                if cmp_t > deadline:
                    dl_violated += 1
        dl_viol_rate = dl_violated / max(1, completed)

        # Workload balance: 1 / (1 + variance)
        workload = [self._robot_tasks_completed.get(r, 0) for r in self._robots]
        mean_w = sum(workload) / max(1, len(workload))
        wv = sum((w - mean_w) ** 2 for w in workload) / max(1, len(workload))
        wb = 1.0 / (1.0 + wv)

        # Failure recovery time
        fail_rec_time = 0.0
        if self._failure_inject_time is not None and self._failure_related_tasks:
            recovery_times = [
                self._task_completion_wall.get(tid, self._failure_inject_time)
                for tid in self._failure_related_tasks
                if tid in self._task_completion_wall
            ]
            if recovery_times:
                fail_rec_time = max(recovery_times) - self._failure_inject_time
                fail_rec_time = max(0.0, fail_rec_time)

        # Allocation instability
        alloc_inst = self._alloc_count / max(1, completed + 1)

        # Mean decision latency
        mean_latency = (sum(self._alloc_latencies) / len(self._alloc_latencies)
                        if self._alloc_latencies else 0.0)

        # Replanning frequency (allocations per minute)
        replan_freq = self._alloc_count / max(1, makespan / 60.0)

        # Total travel distance
        total_dist = sum(self._robot_distances.get(r, 0.0) for r in self._robots)

        # Communication (from comm file if available)
        comm_msgs = self._alloc_count
        comm_bytes = 0

        row = {
            'experiment_id': self._exp_id,
            'scenario': self._scenario,
            'strategy': self._strategy,
            'seed': self._seed,
            'robot_count': self._robot_count,
            'target_count': self._task_count,
            'tasks_total': total,
            'tasks_completed': completed,
            'tasks_failed': failed_tasks,
            'tasks_remaining': active_remaining,
            'task_completion_rate': f'{comp_rate:.4f}',
            'makespan_s': f'{makespan:.1f}',
            'average_task_delay': f'{avg_delay:.2f}',
            'deadline_violation_rate': f'{dl_viol_rate:.4f}',
            'total_travel_distance': f'{total_dist:.2f}',
            'workload_balance': f'{wb:.4f}',
            'failure_recovery_time': f'{fail_rec_time:.2f}',
            'replanning_frequency': f'{replan_freq:.2f}',
            'allocation_instability': f'{alloc_inst:.4f}',
            'mean_decision_latency_ms': f'{mean_latency:.2f}',
            'communication_messages': comm_msgs,
            'communication_bytes': comm_bytes,
            'rosbag_size_mb': 0.0,
            'source': 'gazebo',
        }

        path = os.path.join(self._results_dir, 'summary.csv')
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            w.writeheader()
            w.writerow(row)

    def destroy_node(self) -> None:
        for f in (self._te_file, self._ts_file, self._ae_file,
                  self._rt_file, self._comm_file, self._eco_file):
            try:
                f.close()
            except Exception:
                pass
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ExperimentRunnerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
