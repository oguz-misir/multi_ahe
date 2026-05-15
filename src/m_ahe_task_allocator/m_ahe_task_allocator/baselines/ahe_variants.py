"""ahe_variants — AHE-MRTA ablation and full variants.

All variants share the same greedy assignment + cheapest-insertion ordering.
They differ only in how allocation weights W(t) are derived.

Variants:
  full_ahe_mrta              — uses W(t) = softmax(M·D) from EcosystemContext
  ahe_no_dominance           — uniform D → uniform W (dominance disabled)
  ahe_no_cooperation_suppression — dominance updated without A and S matrices
  ahe_no_event_replanning    — allocates only on first call, ignores replan flag
  ahe_fixed_context          — uses a fixed "neutral" context vector (no adaptation)
"""

import math
from typing import List, Optional

import numpy as np

from .base_allocator import (
    AllocationResult, BaseAllocator, EcosystemContext,
    RobotState, TaskState, cheapest_insertion, measure, queue_endpoint,
)
from ..ahe_allocator_node import W0  # fallback weights

# AHE ecosystem constants (mirrored from ecosystem_manager_node)
K = 7
ALPHA, BETA, GAMMA, ETA, LMBDA, DELTA = 0.6, 0.2, 0.15, 0.10, 0.10, 0.15
BATT_CRITICAL = 2
MAX_DIST = 28.0


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na > 1e-9 and nb > 1e-9 else 0.0


class _AHEBase(BaseAllocator):
    """Shared greedy assignment logic for all AHE variants."""

    def _weights_from_context(self, context: Optional[EcosystemContext]) -> List[float]:
        raise NotImplementedError

    def _assign(self, robots: list, tasks: list, current_time: float,
                weights: List[float]) -> dict:
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
                if r.battery_state == BATT_CRITICAL or not r.available:
                    continue
                ep = queue_endpoint(r, task_map, queues[r.robot_id])
                D = min(1.0, math.hypot(
                    task.position[0] - ep[0],
                    task.position[1] - ep[1]) / MAX_DIST)
                P = (4 - task.priority) / 3.0
                B = r.battery_state / 2.0
                L = min(1.0, len(queues[r.robot_id]) / max(1.0, 15.0 / len(robots) * 2))
                F = 1.0 if r.failure_flag else 0.0
                elapsed = current_time - task.activation_time
                T = min(1.0, elapsed / task.deadline) if task.deadline > 0 else 0.0
                cost = w_d*D + w_p*P + w_b*B + w_l*L + w_f*F + w_t*T
                if cost < best_c:
                    best_c = cost; best_r = r.robot_id
            if best_r:
                queues[best_r].append(task.task_id)

        ordered: dict = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            ins = cheapest_insertion(r.pose, q_tasks)
            ordered[r.robot_id] = [t.task_id for t in ins]
        return ordered

    @measure
    def allocate(self, robots: list, tasks: list, current_time: float,
                 context: Optional[EcosystemContext] = None) -> AllocationResult:
        weights = self._weights_from_context(context)
        queues = self._assign(robots, tasks, current_time, weights)
        comm = len(robots) * 7 * 4  # weights vector per robot
        return AllocationResult(
            queues=queues, latency_ms=0.0,
            communication_footprint_bytes=comm)


# ---------------------------------------------------------------------------
# Full AHE-MRTA  (uses weights from EcosystemManager)
# ---------------------------------------------------------------------------

class FullAHEAllocator(_AHEBase):

    def name(self) -> str:
        return 'full_ahe_mrta'

    def _weights_from_context(self, context: Optional[EcosystemContext]) -> List[float]:
        if context and context.allocation_weights:
            return list(context.allocation_weights)
        return list(W0)


# ---------------------------------------------------------------------------
# AHE without dominance  (uniform dominance → W via softmax(M · [1/K]^K))
# ---------------------------------------------------------------------------

from m_ahe_ecosystem_manager.ecosystem_manager_node import M as _M


class AHENoDominanceAllocator(_AHEBase):

    def name(self) -> str:
        return 'ahe_no_dominance'

    def _weights_from_context(self, context: Optional[EcosystemContext]) -> List[float]:
        D_uniform = np.full(K, 1.0 / K)
        W = _softmax(_M @ D_uniform)
        return W.tolist()


# ---------------------------------------------------------------------------
# AHE without cooperation/suppression  (skip A and S in dominance update)
# ---------------------------------------------------------------------------

from m_ahe_ecosystem_manager.ecosystem_manager_node import (
    V as _V, ALPHA as _A, BETA as _B, GAMMA as _G, DELTA as _D,
)


class AHENoCoopSuppAllocator(_AHEBase):
    """Dominance updated with P and K only; A and S matrices zeroed."""

    def __init__(self):
        self._dominance = np.full(K, 1.0 / K)

    def name(self) -> str:
        return 'ahe_no_cooperation_suppression'

    def _weights_from_context(self, context: Optional[EcosystemContext]) -> List[float]:
        if context is None:
            return list(W0)
        ctx = np.array(context.context_vector)
        compat = np.array([_cosine_sim(_V[i], ctx) for i in range(K)])
        # No cooperation, no suppression, no failure penalty term
        D_new = np.clip(_A * self._dominance + _B * compat + _G * compat, 0.0, 1.0)
        total = D_new.sum()
        self._dominance = D_new / total if total > 1e-9 else np.full(K, 1.0 / K)
        W = _softmax(_M @ self._dominance)
        return W.tolist()


# ---------------------------------------------------------------------------
# AHE without event-triggered replanning  (ignores trigger_replan; periodic only)
# ---------------------------------------------------------------------------

class AHENoEventReplanningAllocator(FullAHEAllocator):
    """Same as FullAHE but the experiment runner must NOT pass replan=True events.
    Marker class — the runner checks isinstance(allocator, AHENoEventReplanningAllocator)
    and skips event-based allocation calls."""

    def name(self) -> str:
        return 'ahe_no_event_replanning'


# ---------------------------------------------------------------------------
# AHE with fixed context  (context vector frozen at neutral values)
# ---------------------------------------------------------------------------

_FIXED_CTX = np.array([0.5, 0.5, 0.1, 0.1, 0.0, 0.2, 0.0])  # neutral baseline


class AHEFixedContextAllocator(_AHEBase):
    """Context vector is fixed; only dominance memory (alpha term) evolves."""

    def __init__(self):
        self._dominance = np.full(K, 1.0 / K)

    def name(self) -> str:
        return 'ahe_fixed_context'

    def _weights_from_context(self, context: Optional[EcosystemContext]) -> List[float]:
        ctx = _FIXED_CTX
        compat = np.array([_cosine_sim(_V[i], ctx) for i in range(K)])
        D_new = np.clip(_A * self._dominance + _G * compat, 0.0, 1.0)
        total = D_new.sum()
        self._dominance = D_new / total if total > 1e-9 else np.full(K, 1.0 / K)
        W = _softmax(_M @ self._dominance)
        return W.tolist()
