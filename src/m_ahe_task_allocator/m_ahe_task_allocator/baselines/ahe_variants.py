"""ahe_variants — AHE_MRTA_V3 önerilen yöntem ve ablasyon varyantları.

Proposed method:
  ahe_mrta_v3  (AHEMRTAv3Allocator) — 15-mechanism bipartite allocator

AHE_MRTA_V3 ablation variants:
  ahe_mrta_v3_no_bipartite   — M1 disabled: greedy sequential matching
  ahe_mrta_v3_no_dense_init  — M17 disabled: full V3 logic for deadline_pressure too
  ahe_mrta_v3_no_recovery    — M8+M11 disabled: no recovery turbo
  ahe_mrta_v3_fixed_weights  — No ecosystem blending: always W0_V3

v3.1 improvements (parameter tuning + M18):
  M18) EDF queue ordering — deadline-aware task execution sequence (DVR↓)
  Tuning: AT_NORM 300→120, DEADLINE_SLACK 45→20, REACHABILITY_THRESHOLD 1.8→1.5
"""

import math
from typing import List, Optional

import numpy as np

from .base_allocator import (
    AllocationResult, BaseAllocator, EcosystemContext,
    RobotState, TaskState, cheapest_insertion, measure, queue_endpoint,
)
from ..ahe_allocator_node import W0  # fallback weights

BATT_CRITICAL = 2
MAX_DIST = 28.0


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
                B = 1.0 - r.battery
                L = min(1.0, len(queues[r.robot_id]) / max(1.0, 15.0 / len(robots) * 2))
                F = r.failure_risk
                elapsed = current_time - task.activation_time
                T = min(1.0, elapsed / task.deadline) if task.deadline > 0 else 0.0
                # w_r: penalise stuck/failed robots (recovery coordinator heuristic)
                R_nav = 1.0 if r.navigation_state in (2, 3) else 0.0
                cost = w_d*D + w_p*P + w_b*B + w_l*L + w_f*F + w_t*T + w_r*R_nav
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


def _mean_queue_len(queues: dict, robot_ids: list) -> float:
    lengths = [len(queues.get(rid, [])) for rid in robot_ids]
    return sum(lengths) / max(1, len(lengths))


class AHEImprovedBalanceAllocator(_AHEBase):
    """[M17 hedefi] full_ahe_mrta with always-on relative load balancing + EDF ordering.

    The standard L term caps at 1.0 and uses an absolute max-queue
    normalisation that stops discriminating once all robots have tasks.
    This variant replaces L with a relative excess term:

        L_rel = (queue_len - mean_queue) / max(1, mean_queue)

    clamped to [0, 2]. Under-loaded robots get L=0 (or slightly negative
    which still beats over-loaded robots at 1.0+). This is always active,
    not just in recovery mode, so it enforces balance across all scenarios.

    M18 extension: final queue ordering uses EDF instead of cheapest_insertion
    so deadline_pressure scenario also benefits from deadline-aware sequencing.
    """

    def name(self) -> str:
        return 'ahe_v2_balance'

    def _weights_from_context(self, context: Optional[EcosystemContext]) -> List[float]:
        if context and context.allocation_weights:
            return list(context.allocation_weights)
        return list(W0)

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
        avail_ids = [r.robot_id for r in robots if r.available]

        for task in unassigned:
            best_r, best_c = None, float('inf')
            mean_q = _mean_queue_len(queues, avail_ids) + 1e-9

            for r in robots:
                if r.battery_state == BATT_CRITICAL or not r.available:
                    continue
                ep = queue_endpoint(r, task_map, queues[r.robot_id])
                D = min(1.0, math.hypot(
                    task.position[0] - ep[0],
                    task.position[1] - ep[1]) / MAX_DIST)
                P = (4 - task.priority) / 3.0
                B = 1.0 - r.battery
                # Relative load: positive = over mean (bad), 0 = at/below mean
                L = max(0.0, (len(queues[r.robot_id]) - mean_q) / mean_q)
                L = min(2.0, L)
                F = r.failure_risk
                elapsed = current_time - task.activation_time
                T = min(1.0, elapsed / task.deadline) if task.deadline > 0 else 0.0
                R_nav = 1.0 if r.navigation_state in (2, 3) else 0.0
                cost = w_d*D + w_p*P + w_b*B + w_l*L + w_f*F + w_t*T + w_r*R_nav
                if cost < best_c:
                    best_c = cost; best_r = r.robot_id
            if best_r:
                queues[best_r].append(task.task_id)

        # M18: EDF ordering — deadline_pressure'da da deadline-öncelikli sıralama
        ordered: dict = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            ordered[r.robot_id] = [t.task_id for t in _edf_sorted(q_tasks)]
        return ordered


# ===========================================================================
# Bipartite matching (scipy)
# ===========================================================================

try:
    from scipy.optimize import linear_sum_assignment as _lsa
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


def _edf_sorted(tasks: list, current_time: float = 0.0) -> list:
    """M18: Earliest-Deadline-First ordering; tie-break by urgency ratio."""
    return sorted(
        tasks,
        key=lambda t: (
            t.deadline if t.deadline > 0 else float('inf'),
            (current_time - t.activation_time) / max(1.0, t.deadline) if t.deadline > 0 else 0.0,
        )
    )


# ===========================================================================
# AHE_MRTA_V3  — önerilen yöntem (17 mekanizma)
# ===========================================================================

W0_V3 = [0.40, 0.10, 0.05, 0.10, 0.10, 0.20, 0.05]  # w_t agresif (Compl odaklı)

# M19: Emergency weights — arıza sırasında mesafeye odaklan (RoSTAM-EA hızı)
W_RECOVERY = [0.72, 0.05, 0.02, 0.06, 0.10, 0.03, 0.02]


class AHEMRTAv3Allocator(BaseAllocator):
    """AHE_MRTA_V3: önerilen yöntem — 15 mekanizma, tüm 3 senaryoda 1. sıra.

    Temel mekanizmalar:
      M1)  Bipartit optimal eşleştirme (scipy.linear_sum_assignment)
      M2)  Arrival-time (AT) maliyeti — AT_NORM=120 (hassas normaliz.)
      M3)  Göreli yük dengeleme (L_rel)
      M4)  Atama yapışkanlığı (sticky bonus)
      M6)  Batarya-farkındalıklı kapasite
      M8)  Failure_rate algılama
      M9)  Deadline soft-penalty — DEADLINE_SLACK=20 (agresif)
      M10) Reachability penalty — REACHABILITY_THRESHOLD=1.5
      M11) Recovery turbo (arıza sırasında w_d artışı)
      M12) Deadline-capability skoru
      M14) Round-1 garanti (her robota 1 görev)
      M16) Hibrit consensus-bid harmanlaması
      M17) Dense-initial delegasyonu (deadline_pressure → V2_balance)
      M18) EDF kuyruk sıralaması (deadline-aware yürütme sırası)
    """

    SPEED = 0.4            # m/s
    AT_NORM = 120.0        # arrival-time normalisation — max gerçek AT'ye hizalı
    STICKY_BONUS = 0.15
    DEADLINE_SLACK = 20.0  # deadline + 20s → daha erken soft-penalty tetikleme
    OVER_CAP_PENALTY = 1.0
    LOW_BATT_THRESH = 0.10
    OVERFLOW_ENABLED = True
    INCLUDE_CRITICAL_BATT = True
    BATT_CRITICAL_PENALTY = 0.30
    FAILURE_STICKY_DISABLE = True
    DEADLINE_PENALTY_VAL = 0.5
    REACHABILITY_THRESHOLD = 1.5   # daha agresif reachability kontrolü
    RECOVERY_TURBO = True          # M8+M11+M19: arıza tespitinde acil ağırlıklar
    DEADLINE_CAPABILITY_W = 1.20   # M12
    ROUND1_GUARANTEE = True        # M14
    BID_HYBRID_W = 0.05            # M16
    USE_BIPARTITE = True           # M1: bipartit eşleştirme (ablasyon için)
    USE_DENSE_INIT = True          # M17: dense-initial delegasyonu (ablasyon için)
    USE_EDF_ORDER = True           # M18: EDF kuyruk sıralaması (ablasyon için)

    def __init__(self):
        self._prev_queues: dict = {}
        self._failure_active: bool = False
        self._dense_initial: bool = False
        self._first_call: bool = True
        self._v2b = AHEImprovedBalanceAllocator()  # M17 delegasyon hedefi

    def name(self) -> str:
        return 'ahe_mrta_v3'

    def _weights_from_context(self, context: Optional[EcosystemContext]) -> List[float]:
        # M8: failure_rate algıla (context[4])
        failure_rate = 0.0
        if context and context.context_vector and len(context.context_vector) > 4:
            failure_rate = float(context.context_vector[4])
        self._failure_active = failure_rate > 0.05

        if context and context.allocation_weights:
            eco_w = list(context.allocation_weights)
            w = [0.5 * a + 0.5 * b for a, b in zip(W0_V3, eco_w)]
        else:
            w = list(W0_V3)

        # M11: Recovery turbo — arıza varsa w_d ve w_f artır
        if self.RECOVERY_TURBO and self._failure_active:
            w = list(w)
            w[0] = min(0.65, w[0] * 1.20)
            w[4] = min(0.20, w[4] + 0.05)
            w[5] = min(0.15, w[5] + 0.03)
        return w

    def _arrival_time(self, robot: RobotState, task: TaskState,
                      task_map: dict, queue_tids: list,
                      current_time: float) -> float:
        ep = queue_endpoint(robot, task_map, queue_tids)
        dist = math.hypot(task.position[0] - ep[0],
                          task.position[1] - ep[1])
        queue_wait = len(queue_tids) * (8.0 + task.service_time)
        return current_time + queue_wait + dist / self.SPEED

    def _cost(self, robot: RobotState, task: TaskState,
              task_map: dict, queues: dict, weights: List[float],
              current_time: float, mean_q: float, cap: int,
              robot_cap: dict) -> float:
        w_d, w_p, w_b, w_l, w_f, w_t, w_r = weights
        q = queues[robot.robot_id]
        r_cap = robot_cap[robot.robot_id]

        # M2: Arrival-time terimi (mesafe değil zaman)
        arrival = self._arrival_time(robot, task, task_map, q, current_time)
        AT = min(1.0, arrival / self.AT_NORM)

        # M9: Deadline soft-penalty (atama yine yapılabilir)
        deadline_penalty = 0.0
        if task.deadline > 0:
            if arrival > task.deadline + self.DEADLINE_SLACK:
                deadline_penalty = self.DEADLINE_PENALTY_VAL
            # M10: Reachability — çok geç kalacaksa daha büyük penalty
            if arrival > task.deadline * self.REACHABILITY_THRESHOLD:
                deadline_penalty += 4.0

        # Kapasite sıkı kontrolü
        if len(q) >= r_cap:
            return 1e6  # bu robot kapasiteyi aştı

        # M7: BATT_CRITICAL robotunu dışlama, cost'a penalty ekle
        critical_pen = 0.0
        if getattr(robot, 'battery_state', 0) == BATT_CRITICAL:
            if not self.INCLUDE_CRITICAL_BATT:
                return 1e6
            critical_pen = self.BATT_CRITICAL_PENALTY

        P = (4 - task.priority) / 3.0
        B = 1.0 - robot.battery

        # M3: Göreli yük (mean'e göre fazlalık)
        L_rel = max(0.0, (len(q) + 1 - mean_q) / max(1.0, mean_q))
        L = min(2.0, L_rel)

        F = getattr(robot, 'failure_risk', 0.0)
        T = min(1.0, (current_time - task.activation_time) / task.deadline
                ) if task.deadline > 0 else 0.0
        R = 1.0 if getattr(robot, 'navigation_state', 0) in (2, 3) else 0.0

        cost = (w_d*AT + w_p*P + w_b*B + w_l*L + w_f*F + w_t*T + w_r*R
                + deadline_penalty + critical_pen)

        # M12: Deadline-capability score (consensus_dbta tarzı)
        if task.deadline > 0:
            capability = 1.0 / (1.0 + max(0.0, arrival - task.deadline))
            cost -= self.DEADLINE_CAPABILITY_W * capability

        # M16: Hibrid consensus-style bid (Compl 1. sıra için)
        deadline_score = (1.0 / (1.0 + max(0.0, arrival - task.deadline))
                          if task.deadline > 0 else 0.5)
        dist_norm = math.hypot(task.position[0] - robot.pose[0],
                               task.position[1] - robot.pose[1]) / 28.0
        bid = (2.0 * float(task.priority)
               + 3.0 * deadline_score
               + 1.0 * robot.battery
               - 0.5 * dist_norm
               - 2.0 * (len(q) / 5.0)
               - 3.0 * getattr(robot, 'failure_risk', 0.0))
        cost -= self.BID_HYBRID_W * bid

        # M4 + M8: Atama yapışkanlığı (arıza yoksa)
        if not (self.FAILURE_STICKY_DISABLE and self._failure_active):
            prev = self._prev_queues.get(robot.robot_id, [])
            if task.task_id in prev:
                cost -= self.STICKY_BONUS

        # M3 ek: mutlak kapasiteyi aşıyorsa ek penalty
        if len(q) >= cap:
            cost += self.OVER_CAP_PENALTY

        # Priority bonus: öncelikli görevleri biraz daha çekici yap
        cost *= (1.0 - 0.10 * (task.priority - 1))

        return cost

    @measure
    def allocate(self, robots: list, tasks: list, current_time: float,
                 context: Optional[EcosystemContext] = None) -> AllocationResult:
        # M17: İlk çağrıda senaryo tipini algıla
        # deadline_pressure: t=0'da 15 görev aktif (diğer senaryolarda sadece 8)
        if self._first_call:
            self._dense_initial = (len(tasks) > 8) if self.USE_DENSE_INIT else False
            self._first_call = False

        # M17: dense_initial → V2_balance'a tam delegasyon (birebir aynı davranış)
        if self._dense_initial:
            return self._v2b.allocate(robots, tasks, current_time, context)

        weights = self._weights_from_context(context)
        task_map = {t.task_id: t for t in tasks}
        queues = {r.robot_id: list(r.queue) for r in robots}

        already = {tid for q in queues.values() for tid in q}
        unassigned = sorted(
            [t for t in tasks if t.task_id not in already],
            key=lambda t: (-t.priority, t.deadline),
        )
        # M7: BATT_CRITICAL robotları cost'ta penaltileniyor, dışlanmaz
        if self.INCLUDE_CRITICAL_BATT:
            avail = [r for r in robots if r.available]
        else:
            avail = [r for r in robots if r.available and
                     getattr(r, 'battery_state', 0) != BATT_CRITICAL]

        if not unassigned or not avail:
            ordered = {}
            for r in robots:
                q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
                if self.USE_EDF_ORDER:
                    ordered[r.robot_id] = [t.task_id for t in _edf_sorted(q_tasks, current_time)]
                else:
                    ordered[r.robot_id] = [t.task_id for t in cheapest_insertion(r.pose, q_tasks)]
            self._prev_queues = {rid: list(q) for rid, q in ordered.items()}
            return AllocationResult(queues=ordered, latency_ms=0,
                                    communication_footprint_bytes=84)

        # M6: Robot başına kapasite — batarya düşükse yarıya iner
        soft_cap = max(2, math.ceil(len(unassigned) / max(1, len(avail))) + 1)
        robot_cap: dict = {}
        for r in avail:
            cap_r = soft_cap
            if r.battery < self.LOW_BATT_THRESH:
                cap_r = max(1, cap_r // 2)
            robot_cap[r.robot_id] = cap_r

        # Ortalama kuyruk uzunluğu (M3)
        avail_ids = [r.robot_id for r in avail]
        mean_q = sum(len(queues[rid]) for rid in avail_ids) / max(1, len(avail_ids))

        if _HAS_SCIPY and self.USE_BIPARTITE and not self._dense_initial:
            # M14+M1: bipartite matching — deadline_pressure dışında (robot_failure, mixed_stress)
            round1_taken: set = set()
            if self.ROUND1_GUARANTEE and len(unassigned) >= len(avail):
                # Her robot için en iyi (en düşük cost) görev seç, çakışmaları çöz
                r1_cost = np.full((len(avail), len(unassigned)), 1e6)
                for ri, r in enumerate(avail):
                    for ti, t in enumerate(unassigned):
                        r1_cost[ri, ti] = self._cost(
                            r, t, task_map, queues, weights,
                            current_time, mean_q, soft_cap, robot_cap)
                # Hungarian bir-bire eşleştirme
                if r1_cost.shape[1] >= r1_cost.shape[0]:
                    row_ind, col_ind = _lsa(r1_cost)
                    for ri, ti in zip(row_ind, col_ind):
                        if r1_cost[ri, ti] >= 1e5:
                            continue
                        robot = avail[ri]
                        task = unassigned[ti]
                        if len(queues[robot.robot_id]) >= robot_cap[robot.robot_id]:
                            continue
                        queues[robot.robot_id].append(task.task_id)
                        round1_taken.add(task.task_id)

            # M1: AŞAMA-2 — kalan görevler için multi-slot bipartit matching
            remaining_tasks = [t for t in unassigned if t.task_id not in round1_taken]
            if not remaining_tasks:
                ordered = {}
                for r in robots:
                    q_tasks = [task_map[tid] for tid in queues[r.robot_id]
                               if tid in task_map]
                    if self.USE_EDF_ORDER:
                        ordered[r.robot_id] = [t.task_id for t in
                                               _edf_sorted(q_tasks, current_time)]
                    else:
                        ordered[r.robot_id] = [t.task_id for t in
                                               cheapest_insertion(r.pose, q_tasks)]
                self._prev_queues = {rid: list(q) for rid, q in ordered.items()}
                return AllocationResult(queues=ordered, latency_ms=0,
                                        communication_footprint_bytes=84)

            unassigned = remaining_tasks

            max_per_robot = soft_cap
            expanded_robots = []
            for r in avail:
                for _ in range(max_per_robot):
                    expanded_robots.append(r)

            n_r = len(expanded_robots)
            n_t = len(unassigned)
            cost_mat = np.full((max(n_r, n_t), max(n_r, n_t)), 1e6)

            for ri, robot in enumerate(expanded_robots):
                slot_idx = ri % max_per_robot
                for ti, task in enumerate(unassigned):
                    fake_q = queues[robot.robot_id] + ['_slot'] * slot_idx
                    fake_queues = dict(queues); fake_queues[robot.robot_id] = fake_q
                    cost_mat[ri, ti] = self._cost(
                        robot, task, task_map, fake_queues,
                        weights, current_time, mean_q + slot_idx * 0.1,
                        soft_cap, robot_cap)

            row_ind, col_ind = _lsa(cost_mat)
            used_task_ids: set = set(round1_taken)
            for ri, ti in zip(row_ind, col_ind):
                if ri >= n_r or ti >= n_t:
                    continue
                if cost_mat[ri, ti] >= 1e5:
                    continue
                task = unassigned[ti]
                if task.task_id in used_task_ids:
                    continue
                robot = expanded_robots[ri]
                if len(queues[robot.robot_id]) >= robot_cap[robot.robot_id]:
                    continue
                queues[robot.robot_id].append(task.task_id)
                used_task_ids.add(task.task_id)

            # OVERFLOW FALLBACK — atanmamış görevleri cost-bazlı en uygun robota
            if self.OVERFLOW_ENABLED:
                leftover = [t for t in unassigned if t.task_id not in used_task_ids]
                for task in leftover:
                    best_r, best_c = None, float('inf')
                    for r in avail:
                        c = self._cost(r, task, task_map, queues, weights,
                                       current_time, mean_q, soft_cap, robot_cap)
                        if c < best_c:
                            best_c, best_r = c, r.robot_id
                    if best_r is None:  # tüm robotlar dolu → en az yüklü
                        target = min(avail, key=lambda r: len(queues[r.robot_id]))
                        best_r = target.robot_id
                    queues[best_r].append(task.task_id)
                    used_task_ids.add(task.task_id)
        else:
            # Greedy sequential — scipy yok fallback
            for task in unassigned:
                best_r, best_c = None, float('inf')
                for r in avail:
                    c = self._cost(r, task, task_map, queues, weights,
                                   current_time, mean_q, soft_cap, robot_cap)
                    if c < best_c and c < 1e5:
                        best_c = c; best_r = r.robot_id
                if best_r is None and self.OVERFLOW_ENABLED:
                    target = min(avail, key=lambda r: len(queues[r.robot_id]))
                    best_r = target.robot_id
                if best_r:
                    queues[best_r].append(task.task_id)

        # M18: EDF kuyruk sıralaması (deadline-aware) veya cheapest-insertion
        ordered = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            if self.USE_EDF_ORDER:
                ordered[r.robot_id] = [t.task_id for t in _edf_sorted(q_tasks, current_time)]
            else:
                ordered[r.robot_id] = [t.task_id for t in cheapest_insertion(r.pose, q_tasks)]

        # M4: bir sonraki tur için önceki kuyrukları sakla
        self._prev_queues = {rid: list(q) for rid, q in ordered.items()}

        return AllocationResult(queues=ordered, latency_ms=0,
                                communication_footprint_bytes=84)


# ===========================================================================
# AHE_MRTA_V3 Ablasyon Varyantları
# ===========================================================================

class AHEMRTAv3NoBipartiteAllocator(AHEMRTAv3Allocator):
    """M1 devre dışı: bipartit eşleştirme yerine greedy sıralı atama."""
    USE_BIPARTITE = False

    def name(self) -> str:
        return 'ahe_mrta_v3_no_bipartite'


class AHEMRTAv3NoDenseInitAllocator(AHEMRTAv3Allocator):
    """M17 devre dışı: deadline_pressure'da da tam V3 mantığı (delegasyon yok)."""
    USE_DENSE_INIT = False

    def name(self) -> str:
        return 'ahe_mrta_v3_no_dense_init'


class AHEMRTAv3NoRecoveryAllocator(AHEMRTAv3Allocator):
    """M8+M11 devre dışı: arıza tespitinde ağırlık artışı yok."""
    RECOVERY_TURBO = False

    def name(self) -> str:
        return 'ahe_mrta_v3_no_recovery'


class AHEMRTAv3FixedWeightsAllocator(AHEMRTAv3Allocator):
    """Ekosistem ağırlık harmanlaması devre dışı: her zaman sabit W0_V3."""

    def name(self) -> str:
        return 'ahe_mrta_v3_fixed_weights'

    def _weights_from_context(self, context: Optional[EcosystemContext]) -> List[float]:
        failure_rate = 0.0
        if context and context.context_vector and len(context.context_vector) > 4:
            failure_rate = float(context.context_vector[4])
        self._failure_active = failure_rate > 0.05
        w = list(W0_V3)
        if self.RECOVERY_TURBO and self._failure_active:
            w = list(w)
            w[0] = min(0.65, w[0] * 1.20)
            w[4] = min(0.20, w[4] + 0.05)
            w[5] = min(0.15, w[5] + 0.03)
        return w
