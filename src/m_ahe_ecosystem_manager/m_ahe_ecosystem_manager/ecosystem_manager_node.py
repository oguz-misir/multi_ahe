"""
Phase 8 — AHE-MRTA Ecosystem Manager Node

Implements all five core AHE mechanisms:
  1. Context vector  C_t  (7 dimensions)
  2. Dominance vector  D(t)  (K=7 strategy agents)
  3. Context compatibility  K_i(C_t)
  4. Cooperation matrix  A  (7×7)
  5. Suppression matrix  S  (7×7)
  6. Dominance update equation
  7. Allocation weight generation  W(t) = softmax(M · D(t))

Publishes (debug/evaluation only — never sent to robots):
  /ecosystem/debug_state  (EcosystemState)

Subscribes:
  /tasks/global_pool, /robot_i/status_summary,
  /robot_i/local_execution_feedback, /robot_i/task_feedback,
  /allocation/events

EcosystemState is consumed only by the evaluation logger and the AHE allocator
(which acts as the central task-assignment module, not as a robot-side node).

IMPORTANT: this node NEVER publishes to any /robot_i/ topic.
Robots receive only their /robot_i/optimized_task_queue from the allocator.
"""

import csv
import math
import os
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node

from m_ahe_mrta_msgs.msg import (
    AllocationEvent,
    EcosystemState,
    LocalExecutionFeedback,
    RobotStatusSummary,
    TaskInfo,
    TaskPool,
)

# ---------------------------------------------------------------------------
# AHE constants
# ---------------------------------------------------------------------------

K = 5  # number of strategy agents (v4.6: energy/resource hormonları kaldırıldı)

HEURISTIC_NAMES = [
    'SpatialOpportunist',
    'CriticalityGuardian',
    'TemporalRegulator',
    'StabilityController',
    'RecoveryCoordinator',
]

# Indices (0-based)
H_SPATIAL = 0
H_CRIT = 1
H_TEMP = 2
H_STAB = 3
H_RECOV = 4

# Context vector dimensions (0-based) — 4-dim (battery/workload/instab kaldırıldı)
C_TASK_DENSITY = 0
C_ROBOT_AVAIL = 1
C_DEADLINE = 2
C_FAILURE = 3

# ---------------------------------------------------------------------------
# Cooperation matrix A  (A[i,j] > 0: h_j reinforces h_i)
# ---------------------------------------------------------------------------
A = np.zeros((K, K))
A[H_TEMP,  H_CRIT]   = 0.20   # Temporal  ← Criticality Guardian
A[H_RECOV, H_STAB]   = 0.20   # Recovery  ← Stability Controller

# ---------------------------------------------------------------------------
# Suppression matrix S  (S[i,j] > 0: h_j suppresses h_i)
# ---------------------------------------------------------------------------
S = np.zeros((K, K))
S[H_SPATIAL, H_TEMP]   = 0.30  # Spatial suppressed by Temporal (deadline)

# ---------------------------------------------------------------------------
# Context prototype vectors v_i  (K×K, row i = prototype for h_i)
# Each value in [0,1]; high = "h_i is effective in this context dimension"
# ---------------------------------------------------------------------------
V = np.array([
    # td   ra   dp   fr
    [0.7, 0.7, 0.1, 0.1],   # Spatial Opportunist
    [0.3, 0.5, 0.8, 0.2],   # Criticality Guardian
    [0.5, 0.5, 0.9, 0.1],   # Temporal Regulator
    [0.3, 0.3, 0.3, 0.8],   # Stability Controller
    [0.3, 0.2, 0.2, 0.9],   # Recovery Coordinator
])  # shape (K, 4_context_dims)

# ---------------------------------------------------------------------------
# Heuristic-to-cost-weight mapping matrix M  (7_weights × K)
# W(t) = softmax(M · D(t))
# Row = cost weight dimension, Col = heuristic
# ---------------------------------------------------------------------------
M = np.array([
    # so    cg    tr    sc    rc
    [0.9,  0.1,  0.1,  0.3,  0.3],  # w_d (distance)
    [0.1,  0.9,  0.5,  0.5,  0.1],  # w_p (priority)
    [0.1,  0.1,  0.1,  0.3,  0.3],  # w_b (battery)
    [0.1,  0.1,  0.1,  0.1,  0.3],  # w_l (load)
    [0.1,  0.1,  0.1,  0.9,  0.9],  # w_f (failure)
    [0.1,  0.5,  0.9,  0.1,  0.1],  # w_t (deadline)
    [0.1,  0.1,  0.1,  0.3,  0.9],  # w_r (recovery)
])  # shape (7_weights, K)

# Dominance update hyperparameters (sim + makale §III ile AYNI; α/β'nın
# tahsis sonucuna etkisi sub-noise — override cascade akut rejimleri çözüyor)
ALPHA = 0.65  # memory of previous dominance
BETA  = 0.40  # performance contribution
GAMMA = 0.20  # context compatibility contribution
ETA   = 0.12  # cooperation effect
LMBDA = 0.12  # suppression effect
DELTA = 0.20  # failure recovery boost magnitude

# Softmax temperature: T < 1 sharpens weight distribution.
# T=1.0 (default) with near-uniform D produces near-uniform W.
# T=0.3 amplifies small dominance differences into actionable weight contrasts.
SOFTMAX_TEMP = 0.3


def _softmax(x: np.ndarray, temp: float = SOFTMAX_TEMP) -> np.ndarray:
    x_scaled = x / max(temp, 1e-6)
    e = np.exp(x_scaled - x_scaled.max())
    return e / e.sum()


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class EcosystemManagerNode(Node):
    """Full AHE-MRTA ecosystem manager (Phase 8)."""

    def __init__(self) -> None:
        super().__init__('ecosystem_manager_node')

        self.declare_parameter('robot_count', 3)
        self.declare_parameter('update_period_sec', 2.0)
        self.declare_parameter('results_dir',
                               os.path.expanduser('~/multi_ahe/results/raw/phase8_ahe'))

        self._robot_count: int = self.get_parameter('robot_count').value
        self._period: float = self.get_parameter('update_period_sec').value
        self._results_dir: str = self.get_parameter('results_dir').value
        self._robots = [f'robot_{i + 1}' for i in range(self._robot_count)]

        # AHE state
        self._dominance: np.ndarray = np.full(K, 1.0 / K)  # uniform init
        self._perf: np.ndarray = np.zeros(K)                # performance accumulator
        self._allocation_weights: np.ndarray = np.full(7, 1.0 / 7)

        # Context state
        self._pool: list[TaskInfo] = []
        self._robot_states: dict[str, Optional[RobotStatusSummary]] = {
            r: None for r in self._robots
        }
        self._feedback: dict[str, Optional[LocalExecutionFeedback]] = {
            r: None for r in self._robots
        }

        # Tracking for instability
        self._completed_this_cycle: int = 0
        self._failed_this_cycle: int = 0
        self._reassigned_this_cycle: int = 0

        # CSV
        self._setup_csv()

        # Subscribers
        self.create_subscription(TaskPool, '/tasks/global_pool', self._pool_cb, 10)
        self.create_subscription(AllocationEvent, '/allocation/events', self._event_cb, 10)
        for r in self._robots:
            self.create_subscription(
                RobotStatusSummary, f'/{r}/status_summary',
                lambda msg, rr=r: self._status_cb(rr, msg), 10,
            )
            self.create_subscription(
                LocalExecutionFeedback, f'/{r}/local_execution_feedback',
                lambda msg, rr=r: self._feedback_cb(rr, msg), 10,
            )
            self.create_subscription(
                AllocationEvent, f'/{r}/task_feedback',
                self._task_feedback_cb, 10,
            )

        # Publisher (debug / evaluation only — not consumed by robot nodes)
        self._debug_pub = self.create_publisher(EcosystemState, '/ecosystem/debug_state', 10)

        # Periodic update
        self.create_timer(self._period, self._update_ecosystem)

        self.get_logger().info(
            f'EcosystemManager started '
            f'(K={K}, robots={self._robot_count}, period={self._period}s)'
        )

    # ------------------------------------------------------------------
    # CSV setup
    # ------------------------------------------------------------------

    def _setup_csv(self) -> None:
        os.makedirs(self._results_dir, exist_ok=True)
        path = os.path.join(self._results_dir, 'ecosystem_metrics.csv')
        self._csv_file = open(path, 'w', newline='')
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow(
            ['timestamp_s',
             'dominant_heuristic', 'dominant_value',
             'context_task_density', 'context_robot_avail',
             'context_deadline', 'context_failure_rate',
             'w_d', 'w_p', 'w_b', 'w_l', 'w_f', 'w_t', 'w_r']
            + [f'd_{h.lower()}' for h in HEURISTIC_NAMES]
        )

    # ------------------------------------------------------------------
    # Subscribers
    # ------------------------------------------------------------------

    def _pool_cb(self, msg: TaskPool) -> None:
        self._pool = list(msg.tasks)

    def _status_cb(self, robot_id: str, msg: RobotStatusSummary) -> None:
        self._robot_states[robot_id] = msg

    def _feedback_cb(self, robot_id: str, msg: LocalExecutionFeedback) -> None:
        self._feedback[robot_id] = msg

    def _task_feedback_cb(self, msg: AllocationEvent) -> None:
        if msg.event_type == 'task_completed':
            self._completed_this_cycle += 1
        elif msg.event_type == 'task_failed':
            self._failed_this_cycle += 1

    def _event_cb(self, msg: AllocationEvent) -> None:
        if msg.trigger_replan:
            self._reassigned_this_cycle += 1

    # ------------------------------------------------------------------
    # Core AHE update
    # ------------------------------------------------------------------

    def _update_ecosystem(self) -> None:
        ctx = self._compute_context()
        compat = self._compute_compatibility(ctx)
        perf = self._compute_performance(compat)
        failure_boost = self._compute_failure_penalty()

        # Dominance update equation
        D_new = (
            ALPHA * self._dominance
            + BETA  * perf
            + GAMMA * compat
            + ETA   * A @ self._dominance
            - LMBDA * S @ self._dominance
            + DELTA * failure_boost   # positive: boosts Recovery/Stability on failure
        )
        D_new = np.clip(D_new, 0.0, 1.0)
        total = D_new.sum()
        if total > 1e-9:
            D_new /= total
        else:
            D_new = np.full(K, 1.0 / K)
        self._dominance = D_new

        # Weight generation
        raw_weights = M @ self._dominance
        self._allocation_weights = _softmax(raw_weights)

        # Publish debug state
        self._publish_debug(ctx)

        # Log
        self._log_csv(ctx)

        # Reset cycle counters
        self._completed_this_cycle = 0
        self._failed_this_cycle = 0
        self._reassigned_this_cycle = 0
        self._perf = np.zeros(K)

    # ------------------------------------------------------------------
    # Context vector
    # ------------------------------------------------------------------

    def _compute_context(self) -> np.ndarray:
        # 4-boyutlu context: [td, ra, dp, fr]. battery/workload/instab boyutları
        # ablasyonda gereksiz çıktı (Δfitness=0) → kaldırıldı (makale §III-A).
        ctx = np.zeros(4)
        robot_count = max(1, self._robot_count)

        active_tasks = [t for t in self._pool if t.active and not t.completed]
        active_count = len(active_tasks)

        # c1: task_density
        ctx[C_TASK_DENSITY] = min(1.0, active_count / robot_count)

        # c2: robot_availability
        avail = sum(
            1 for r in self._robots
            if (s := self._robot_states.get(r)) is not None
            and s.availability_state == 0
        )
        ctx[C_ROBOT_AVAIL] = avail / robot_count

        # c3: deadline_pressure (fraction of active tasks near their deadline)
        near_deadline = sum(
            1 for t in active_tasks
            if t.deadline > 0 and t.deadline < 60.0
        )
        ctx[C_DEADLINE] = near_deadline / max(1, active_count)

        # c4: failure_rate
        failed_stuck = sum(
            1 for r in self._robots
            if (s := self._robot_states.get(r)) is not None
            and (s.failure_flag or s.navigation_state in (2, 3))  # STUCK or FAILED
        )
        ctx[C_FAILURE] = failed_stuck / robot_count

        return ctx

    # ------------------------------------------------------------------
    # Context compatibility
    # ------------------------------------------------------------------

    def _compute_compatibility(self, ctx: np.ndarray) -> np.ndarray:
        compat = np.array([_cosine_similarity(V[i], ctx) for i in range(K)])
        return compat

    # ------------------------------------------------------------------
    # Performance feedback
    # ------------------------------------------------------------------

    def _compute_performance(self, compat: np.ndarray) -> np.ndarray:
        """Context-aware performance signal.

        Rewards heuristics whose context compatibility is high when tasks are
        completing, and penalises them when tasks fail. This breaks the circular
        dependency of the old dominance-weighted reward.
        """
        total = max(1, self._completed_this_cycle + self._failed_this_cycle)
        completion_gain = self._completed_this_cycle / total
        failure_loss    = self._failed_this_cycle / total
        # Reward the heuristics that fit the current context
        perf = (completion_gain - failure_loss) * compat
        return perf

    def _compute_failure_penalty(self) -> np.ndarray:
        """Boost Recovery/Stability heuristics during robot failures.

        Previously this penalised Recovery on failure (wrong direction).
        Now it returns a positive boost vector: added to dominance via +DELTA term.
        """
        boost = np.zeros(K)
        failure_rate = sum(
            1 for r in self._robots
            if (s := self._robot_states.get(r)) is not None
            and s.failure_flag
        ) / max(1, self._robot_count)

        # Boost Recovery and Stability when failures are active
        boost[H_RECOV] = failure_rate * 0.6
        boost[H_STAB]  = failure_rate * 0.4
        # Suppress spatially-greedy heuristics during failure (they ignore robot state)
        boost[H_SPATIAL] = -failure_rate * 0.3

        return boost

    # ------------------------------------------------------------------
    # Publisher
    # ------------------------------------------------------------------

    def _publish_debug(self, ctx: np.ndarray) -> None:
        msg = EcosystemState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.dominance_values = self._dominance.tolist()
        msg.cooperation_values = (A @ self._dominance).tolist()
        msg.suppression_values = (S @ self._dominance).tolist()
        msg.context_vector = ctx.tolist()
        msg.heuristic_names = HEURISTIC_NAMES
        msg.allocation_weights = self._allocation_weights.tolist()
        self._debug_pub.publish(msg)

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    def _log_csv(self, ctx: np.ndarray) -> None:
        ts = self.get_clock().now().nanoseconds / 1e9
        dom_idx = int(np.argmax(self._dominance))
        row = (
            [f'{ts:.3f}',
             HEURISTIC_NAMES[dom_idx],
             f'{self._dominance[dom_idx]:.4f}']
            + [f'{v:.4f}' for v in ctx]
            + [f'{w:.4f}' for w in self._allocation_weights]
            + [f'{d:.4f}' for d in self._dominance]
        )
        self._csv_writer.writerow(row)
        self._csv_file.flush()

    def destroy_node(self) -> None:
        self._csv_file.close()
        super().destroy_node()

    # ------------------------------------------------------------------
    # Property: current weights (for AHE allocator co-location if needed)
    # ------------------------------------------------------------------

    @property
    def allocation_weights(self) -> list[float]:
        return self._allocation_weights.tolist()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EcosystemManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
