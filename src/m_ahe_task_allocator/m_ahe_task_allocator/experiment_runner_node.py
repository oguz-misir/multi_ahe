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
from rclpy.action import ActionClient
from rcl_interfaces.msg import ParameterDescriptor
from nav2_msgs.action import NavigateToPose
from lifecycle_msgs.msg import State, Transition
from lifecycle_msgs.srv import ChangeState, GetState

import yaml

from geometry_msgs.msg import PoseStamped
from m_ahe_mrta_msgs.msg import (
    AllocationEvent, EcosystemState, LocalExecutionFeedback,
    OptimizedTaskQueue, RobotStatusSummary, TaskInfo, TaskPool, TaskWaypoint,
)

from .baselines.base_allocator import (
    AllocationResult, EcosystemContext, RobotState as RS, TaskState as TS,
    cheapest_insertion, jain_index,
)
from .baselines.greedy_nearest import GreedyNearestAllocator
from .baselines.deadline_aware import DeadlineAwareAllocator
from .baselines.auction_based import AuctionBasedAllocator
from .baselines.static_weighted import StaticWeightedAllocator
from .baselines.big_mrta import BigMRTAAllocator
from .baselines.rostam_ea import RoSTAMEAAllocator
from .baselines.consensus_dbta import ConsensusDBTAAllocator
from .baselines.ahe_variants import AHEMRTAv3Allocator
from .placement import task_positions as _free_task_positions

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
}

AHE_STRATEGIES = {'ahe_mrta_v3'}

# ---------------------------------------------------------------------------
# Scenario parameters
# ---------------------------------------------------------------------------

_DEADLINE_MULTIPLIERS = {
    'dynamic_task_arrival': 1.0,
    'deadline_pressure':    0.4,  # tight deadlines
    'robot_failure':        1.0,
    'mixed_stress':         0.5,
}

# Task goal positions come from the shared obstacle-aware placement module
# (m_ahe_task_allocator.placement). The legacy hand-curated _GRID now lives
# there as placement.GRID, re-validated against the inflated obstacle map.

EXPERIMENT_TIMEOUT_SEC      = 900.0   # 15 min max per experiment (sim-time)
EXPERIMENT_WALL_TIMEOUT_SEC = 1200.0  # 20 min wall-clock safety net
# With heavy 10r simulations, Gazebo can run at 0.3-0.5× real-time, so the
# sim-time timeout may fire at 2000-3000s wall-time — well past the shell
# runner's TIMEOUT_SEC=1800s.  The wall-clock backup ensures DONE is always
# written within 20 minutes of task start regardless of sim speed.
ALLOC_PERIOD_SEC       = 5.0
TIMESERIES_PERIOD_SEC  = 2.0
FAILURE_TIME_OFFSET    = 45.0    # seconds after experiment start before injecting failure

# Nav2-independent allocation fitness is reported only from the navigation-free
# SIM (scripts/simulate_and_tune.py), where it equals priority-weighted on-time
# completion. Gazebo runs measure the Nav2-confounded reality instead.


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
        # dynamic_typing so the launch may pass "120" (int) or "120.0" (float);
        # we cast to float on read. Avoids InvalidParameterTypeException.
        self.declare_parameter('gazebo_startup_delay_sec', 0.0,
                               ParameterDescriptor(dynamic_typing=True))

        self._strategy: str = self.get_parameter('strategy').value
        self._scenario: str = self.get_parameter('scenario').value
        self._robot_count: int = self.get_parameter('robot_count').value
        self._task_count: int = self.get_parameter('task_count').value
        self._seed: int = self.get_parameter('seed').value
        self._results_base: str = self.get_parameter('results_base').value
        self._startup_delay: float = float(
            self.get_parameter('gazebo_startup_delay_sec').value or 0.0)

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
        self._start_time: Optional[float] = None         # sim-time, set when experiment begins
        self._wall_experiment_start: float = time.monotonic()  # overwritten in _start_experiment

        # Readiness-gated startup: sabit _startup_delay'i beklemek yerine her
        # robotun NavigateToPose action server'ını (= bt_navigator ACTIVE) yokla.
        # Hepsi hazır olunca min-settle sonrası başla; _startup_delay artık MAX
        # timeout — o ana kadar hazır olmayan robot varsa startup FAILURE: DONE
        # YAZMA, çöp veri kaydetme, kapan (driver yeniden koşar). Bu, yük/DDS
        # kaynaklı bozuk startup'ları (gece batch'inde 9 çöp koşu) eler.
        self._nav_ready_clients: Dict[str, ActionClient] = {}
        self._startup_min_settle: float = 15.0
        self._startup_all_ready_since: Optional[float] = None
        self._startup_failed: bool = False
        if self._startup_delay > 0.0:
            for r in self._robots:
                self._nav_ready_clients[r] = ActionClient(
                    self, NavigateToPose, f'/{r}/navigate_to_pose')

        # Nav2 bring-up öz-iyileştirme: eşzamanlı configure fırtınasında
        # lifecycle manager'ın change_state yanıt penceresi (Jazzy'de sabit,
        # parametrik değil — nav2_params.yaml'daki service_client_timeout_sec
        # okunmuyor) aşılınca manager pes ediyor ve robot süresiz INACTIVE
        # kalıyor. _startup_delay'in %60'ında hazır olmayan robotların Nav2
        # düğümlerini get_state ile yoklayıp eksik configure/activate
        # geçişlerini runner kendisi sürer. Runner'ın servis istemcisi yanıt
        # için süresiz bekler; iyileşme olmazsa STARTUP FAILED yolu aynen
        # işler (çöp veri riski yok).
        self._rekick_nodes: List[str] = [
            'map_server', 'controller_server', 'planner_server',
            'behavior_server', 'bt_navigator']
        self._rekick_at: float = 0.6 * self._startup_delay
        self._rekick_rounds: int = 0
        self._rekick_max_rounds: int = 2
        self._rekick_round_gap: float = 90.0
        self._rekick_clients: Dict[str, object] = {}

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
        self._robot_navigation_effort: Dict[str, float] = {
            r: 0.0 for r in self._robots}

        # Task failure backoff: skip permanently-stuck tasks
        self._task_fail_count:  Dict[str, int]   = {}
        self._pair_fail_count:  Dict[tuple, int] = {}
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
            self.create_subscription(
                LocalExecutionFeedback, f'/{r}/local_execution_feedback',
                lambda msg, rr=r: self._execution_feedback_cb(rr, msg), 10)

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
        if self._startup_done or self._startup_failed:
            return
        elapsed_wall = time.monotonic() - self._node_start_time
        ready = [r for r, c in self._nav_ready_clients.items() if c.server_is_ready()]
        n_ready, n_total = len(ready), len(self._robots)

        if n_ready >= n_total:
            # Tüm Nav2 server'ları hazır → min-settle sonra başla
            if self._startup_all_ready_since is None:
                self._startup_all_ready_since = time.monotonic()
                self.get_logger().info(
                    f'Nav2: {n_ready}/{n_total} robot hazır ({elapsed_wall:.0f}s) — '
                    f'{self._startup_min_settle:.0f}s settle...')
            elif time.monotonic() - self._startup_all_ready_since >= self._startup_min_settle:
                self._startup_done = True
                self.get_logger().info(
                    f'Nav2 startup complete ({n_ready}/{n_total} ready, '
                    f'{elapsed_wall:.0f}s) — starting experiment.')
                self._start_experiment()
            return

        # Henüz hepsi hazır değil — önce öz-iyileştirme dene
        if (self._startup_delay > 0.0
                and self._rekick_rounds < self._rekick_max_rounds
                and elapsed_wall >= (self._rekick_at
                                     + self._rekick_round_gap * self._rekick_rounds)):
            self._rekick_rounds += 1
            not_ready = [r for r in self._robots if r not in ready]
            self.get_logger().warning(
                f'REKICK tur {self._rekick_rounds}: {elapsed_wall:.0f}s geçti, '
                f'hazır olmayan: {not_ready} — lifecycle geçişleri elle sürülüyor.')
            for r in not_ready:
                self._rekick_step(r, 0)

        # MAX timeout'a kadar bekle
        if elapsed_wall >= self._startup_delay:
            not_ready = [r for r in self._robots if r not in ready]
            self.get_logger().error(
                f'STARTUP FAILED: {n_ready}/{n_total} Nav2 hazır, '
                f'{self._startup_delay:.0f}s sonra hazır olmayan: {not_ready}. '
                f'DONE yazılmıyor (çöp veri yok) — kapanıyor.')
            self._write_startup_failed(not_ready)
            self._startup_failed = True
            self._experiment_done = True
            self.create_timer(2.0, self._shutdown_self)

    def _write_startup_failed(self, not_ready: List[str]) -> None:
        """Bozuk startup işareti — DONE DEĞİL. Driver bunu görür, hücreyi
        DONE saymaz → yeniden koşar (çöp 0/50 DONE artık üretilmez)."""
        try:
            path = os.path.join(self._results_dir, 'STARTUP_FAILED')
            with open(path, 'w') as f:
                f.write(f'not_ready={",".join(not_ready)}\n')
        except OSError:
            pass

    # --- Nav2 bring-up öz-iyileştirme (REKICK) ---------------------------
    # Robot başına sıralı zincir: her düğüm için get_state → gerekirse
    # configure → activate → sonraki düğüm. Sıra nav2 bring-up sırasıyla
    # aynı (map_server → ... → bt_navigator). Tüm çağrılar async; tek
    # thread'li executor'da timer'ları bloklamaz. Başarısız/yanıtsız adım
    # zinciri durdurursa robot hazır olamaz ve mevcut STARTUP FAILED yolu
    # değişmeden devreye girer.

    def _rekick_client(self, srv_name: str, srv_type):
        if srv_name not in self._rekick_clients:
            self._rekick_clients[srv_name] = self.create_client(srv_type, srv_name)
        return self._rekick_clients[srv_name]

    def _rekick_step(self, robot: str, idx: int) -> None:
        if idx >= len(self._rekick_nodes):
            self.get_logger().info(f'REKICK {robot}: zincir tamamlandı.')
            return
        node = self._rekick_nodes[idx]
        gs = self._rekick_client(f'/{robot}/{node}/get_state', GetState)
        if not gs.service_is_ready():
            self.get_logger().warning(
                f'REKICK {robot}/{node}: get_state servisi yok — atlanıyor.')
            self._rekick_step(robot, idx + 1)
            return
        fut = gs.call_async(GetState.Request())
        fut.add_done_callback(
            lambda f, r=robot, i=idx: self._rekick_on_state(r, i, f))

    def _rekick_on_state(self, robot: str, idx: int, fut) -> None:
        node = self._rekick_nodes[idx]
        try:
            state = fut.result().current_state.id
        except Exception as exc:  # noqa: BLE001 — zincir devam etmeli
            self.get_logger().warning(
                f'REKICK {robot}/{node}: get_state hatası ({exc}) — atlanıyor.')
            self._rekick_step(robot, idx + 1)
            return
        if state == State.PRIMARY_STATE_ACTIVE:
            self._rekick_step(robot, idx + 1)
        elif state == State.PRIMARY_STATE_INACTIVE:
            self._rekick_transition(
                robot, idx, Transition.TRANSITION_ACTIVATE, then_next=True)
        elif state == State.PRIMARY_STATE_UNCONFIGURED:
            self._rekick_transition(
                robot, idx, Transition.TRANSITION_CONFIGURE, then_next=False)
        else:
            self.get_logger().warning(
                f'REKICK {robot}/{node}: beklenmedik durum id={state} — atlanıyor.')
            self._rekick_step(robot, idx + 1)

    def _rekick_transition(self, robot: str, idx: int,
                           transition: int, then_next: bool) -> None:
        node = self._rekick_nodes[idx]
        cs = self._rekick_client(f'/{robot}/{node}/change_state', ChangeState)
        if not cs.service_is_ready():
            self.get_logger().warning(
                f'REKICK {robot}/{node}: change_state servisi yok — atlanıyor.')
            self._rekick_step(robot, idx + 1)
            return
        req = ChangeState.Request()
        req.transition.id = transition
        label = ('activate' if transition == Transition.TRANSITION_ACTIVATE
                 else 'configure')
        self.get_logger().warning(f'REKICK {robot}/{node}: {label} gönderiliyor...')
        fut = cs.call_async(req)
        fut.add_done_callback(
            lambda f, r=robot, i=idx, t=transition, n=then_next:
            self._rekick_on_transition(r, i, t, n, f))

    def _rekick_on_transition(self, robot: str, idx: int, transition: int,
                              then_next: bool, fut) -> None:
        node = self._rekick_nodes[idx]
        try:
            ok = bool(fut.result().success)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warning(
                f'REKICK {robot}/{node}: change_state hatası ({exc}).')
            ok = False
        if not ok:
            # Yarış: başka bir tur/manager geçişi yapmış olabilir — durumu
            # yeniden yoklamak yerine zinciri sonraki düğümden sürdür.
            self.get_logger().warning(
                f'REKICK {robot}/{node}: geçiş id={transition} başarısız — '
                f'sonraki düğüme geçiliyor.')
            self._rekick_step(robot, idx + 1)
            return
        if then_next:
            self.get_logger().warning(f'REKICK {robot}/{node}: AKTİF.')
            self._rekick_step(robot, idx + 1)
        else:
            self._rekick_transition(
                robot, idx, Transition.TRANSITION_ACTIVATE, then_next=True)

    def _start_experiment(self) -> None:
        now = self.get_clock().now().nanoseconds / 1e9
        self._start_time = now
        self._wall_experiment_start = time.monotonic()
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
        # Obstacle-aware, deterministic positions shared with the SIM plane
        # (same (task_count, seed) -> same goals) so R4/R6 hold and no task
        # lands inside a shelf/wall/cylinder.
        grid = _free_task_positions(self._task_count, self._seed, self._robot_count)
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
        current_task_id = msg.current_task_id
        # Task feedback and periodic RobotStatusSummary are independent ROS
        # streams.  A completion can therefore be processed while the newest
        # status still carries the old goal id (occasionally even with
        # NAVIGATING).  Never let that stale id cross back into the allocator:
        # it would resurrect completed work through the in-progress lock.
        current_task = self._task_map.get(current_task_id)
        if current_task is not None and current_task.completed:
            current_task_id = ''
        state = RS(
            robot_id=robot_id,
            pose=pose,
            battery=1.0 - msg.battery_state * 0.33,
            available=(msg.availability_state != 2
                       and robot_id not in self._failed_robots),
            current_task_id=current_task_id,
            queue=list(self._queues.get(robot_id, [])),
            failure_risk=1.0 if msg.failure_flag else 0.0,
            navigation_state=msg.navigation_state,
            failure_flag=msg.failure_flag,
            battery_state=msg.battery_state,
            completed_tasks=self._robot_tasks_completed.get(robot_id, 0),
            failed_tasks=self._robot_tasks_failed.get(robot_id, 0),
            travel_distance=self._robot_distances.get(robot_id, 0.0),
            navigation_effort=self._robot_navigation_effort.get(robot_id, 0.0),
        )
        self._robot_states[robot_id] = state

        last = self._robot_last_pose.get(robot_id)
        if last is not None:
            self._robot_distances[robot_id] += math.hypot(
                pose[0] - last[0], pose[1] - last[1])
        self._robot_last_pose[robot_id] = pose

    def _execution_feedback_cb(
            self, robot_id: str, msg: LocalExecutionFeedback) -> None:
        """Cache Nav2's current global-path distance for allocator ETA use."""
        self._robot_navigation_effort[robot_id] = max(
            0.0, float(msg.navigation_effort))

    def _task_feedback_cb(self, msg: AllocationEvent) -> None:
        tid = msg.task_id
        task = self._task_map.get(tid)
        if task is None:
            return
        now = self.get_clock().now().nanoseconds / 1e9

        if msg.event_type == 'task_completed':
            # Duplicate completion guard: a task can only be completed once.
            # Aggressive re-navigation (e.g. BiG) re-sends goals to an already
            # finished task, firing redundant 'completed' signals that inflated
            # tasks_completed_total → CR > 1.0. Count each task exactly once.
            if task.completed:
                return
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
            # Make exact feedback authoritative immediately, without waiting
            # for the robot's next periodic status publication.
            robot_state = self._robot_states.get(msg.robot_id)
            if (robot_state is not None
                    and robot_state.current_task_id == tid):
                robot_state.current_task_id = ''
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
            pair = (msg.robot_id, tid)
            self._pair_fail_count[pair] = self._pair_fail_count.get(pair, 0) + 1
            if self._task_fail_count[tid] >= self._max_task_retries:
                skip_until = self.get_clock().now().nanoseconds / 1e9 + self._task_backoff_sec
                self._task_skip_until[tid] = skip_until
                self.get_logger().warn(
                    f'[Runner] Task {tid} failed {self._task_fail_count[tid]}x — '
                    f'backing off {self._task_backoff_sec}s'
                )
            else:
                # PAKET A3 GERİ ALINDI (dp deadline'ları için kritik): her nav-fail'de
                # immediate _force_realloc — eski davranış.
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
                # Runner-owned counters are fresher than the periodic status
                # message and provide exact feedback to fairness-aware policies.
                state.completed_tasks = self._robot_tasks_completed.get(r, 0)
                state.failed_tasks = self._robot_tasks_failed.get(r, 0)
                state.travel_distance = self._robot_distances.get(r, 0.0)
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
        self._force_realloc = False
        self._run_allocation()

    def _run_allocation(self) -> None:
        robots = self._get_robots_for_alloc()
        now_s = self.get_clock().now().nanoseconds / 1e9
        tasks = [t for t in self._tasks if t.active and not t.completed
                 and now_s >= self._task_skip_until.get(t.task_id, 0.0)]
        if not tasks:
            return
        for task in tasks:
            task.failure_by_robot = {
                rid: self._pair_fail_count.get((rid, task.task_id), 0)
                for rid in self._robots
                if self._pair_fail_count.get((rid, task.task_id), 0) > 0
            }

        result: AllocationResult = self._allocator.allocate(
            robots, tasks,
            current_time=self.get_clock().now().nanoseconds / 1e9,
            context=self._eco_context,
        )
        self._alloc_count += 1
        self._alloc_latencies.append(result.latency_ms)

        # Final integration boundary: never publish a waypoint that exact task
        # feedback has already closed, even if a third-party allocator returns
        # stale internal state.  This also keeps assignment-event metrics
        # semantically exact.
        open_ids = {t.task_id for t in self._tasks if t.active and not t.completed}
        result.queues = {
            rid: [tid for tid in tids if tid in open_ids]
            for rid, tids in result.queues.items()
        }

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
        elapsed_wall = time.monotonic() - self._wall_experiment_start
        if elapsed > EXPERIMENT_TIMEOUT_SEC:
            self.get_logger().warning(
                f'Experiment sim-time timeout ({elapsed:.0f}s sim) — writing summary.')
            self._finish()
            return
        if elapsed_wall > EXPERIMENT_WALL_TIMEOUT_SEC:
            self.get_logger().warning(
                f'Experiment wall-clock timeout ({elapsed_wall:.0f}s wall, '
                f'{elapsed:.0f}s sim) — writing summary.')
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
            'context_task_density', 'context_robot_avail',
            'context_deadline', 'context_failure_rate',
            'w_d', 'w_p', 'w_b', 'w_l', 'w_f', 'w_t', 'w_r',
        ] + [f'd_{i}' for i in range(5)])

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
        names = list(msg.heuristic_names) if msg.heuristic_names else [str(i) for i in range(5)]
        dom_name = names[dom_idx] if dom_idx < len(names) else str(dom_idx)
        dom_val = msg.dominance_values[dom_idx] if msg.dominance_values else 0.0
        weights = list(msg.allocation_weights) if msg.allocation_weights else [0.0] * 7
        context = list(msg.context_vector) if msg.context_vector else [0.0] * 4
        doms = list(msg.dominance_values) if msg.dominance_values else [0.0] * 5
        self._eco_writer.writerow(
            [f'{ts:.3f}', dom_name, f'{dom_val:.4f}']
            + [f'{c:.4f}' for c in context[:4]]
            + [f'{w:.4f}' for w in weights[:7]]
            + [f'{d:.4f}' for d in doms[:5]]
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

        # Average task delay — FAIR (all-task, survivorship-bias-free). A method
        # that DROPS hard tasks would otherwise post an artificially low delay
        # because dropped tasks never enter the completed-only denominator. Every
        # uncompleted task is censored at makespan (the experiment horizon) so
        # dropping is penalised, not rewarded. Applied uniformly to all methods.
        # Completed-only delay is retained alongside for transparency.
        delays_all = []
        delays_completed = []
        for task in self._tasks:
            act_t = self._task_activation_wall.get(task.task_id, self._start_time or 0.0)
            if task.completed:
                cmp_t = self._task_completion_wall.get(task.task_id, makespan)
                d = max(0.0, cmp_t - act_t)
                delays_all.append(d)
                delays_completed.append(d)
            else:
                delays_all.append(max(0.0, makespan - act_t))  # never finished → censored
        avg_delay = sum(delays_all) / len(delays_all) if delays_all else 0.0
        avg_delay_completed = (sum(delays_completed) / len(delays_completed)
                               if delays_completed else 0.0)

        # Deadline violation rate — FAIR: an unfinished task that carried a
        # deadline counts as a violation; denominator = all deadline-bearing
        # tasks (not just completed ones).
        dl_tasks = 0
        dl_violated = 0
        dl_violated_completed = 0
        for task in self._tasks:
            deadline = self._task_deadline_wall.get(task.task_id, float('inf'))
            has_dl = deadline != float('inf')
            if has_dl:
                dl_tasks += 1
            if task.completed:
                cmp_t = self._task_completion_wall.get(task.task_id, 0.0)
                if has_dl and cmp_t > deadline:
                    dl_violated += 1
                    dl_violated_completed += 1
            elif has_dl:
                dl_violated += 1  # unfinished deadline task → missed
        dl_viol_rate = dl_violated / max(1, dl_tasks)
        dl_viol_rate_completed = dl_violated_completed / max(1, completed)

        # Workload balance: true Jain index, identical to Plane A.  Preserve
        # the historical variance transform under an explicit legacy name so
        # previous campaigns remain auditable without calling it Jain.
        workload = [self._robot_tasks_completed.get(r, 0) for r in self._robots]
        mean_w = sum(workload) / max(1, len(workload))
        wv = sum((w - mean_w) ** 2 for w in workload) / max(1, len(workload))
        wb_legacy = 1.0 / (1.0 + wv)
        wb = jain_index(workload)
        active_workload = [self._robot_tasks_completed.get(r, 0)
                           for r in self._robots if r not in self._failed_robots]
        wb_active = jain_index(active_workload)
        distance_balance = jain_index(
            self._robot_distances.get(r, 0.0) for r in self._robots)

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
            'average_task_delay_completed': f'{avg_delay_completed:.2f}',
            'deadline_violation_rate': f'{dl_viol_rate:.4f}',
            'deadline_violation_rate_completed': f'{dl_viol_rate_completed:.4f}',
            'total_travel_distance': f'{total_dist:.2f}',
            'workload_balance': f'{wb:.4f}',
            'workload_balance_active': f'{wb_active:.4f}',
            'workload_balance_legacy_variance': f'{wb_legacy:.4f}',
            'travel_distance_balance': f'{distance_balance:.4f}',
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
