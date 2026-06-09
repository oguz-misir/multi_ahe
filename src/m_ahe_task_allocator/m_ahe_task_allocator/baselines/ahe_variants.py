"""ahe_variants — AHE-MRTA v4 (EDPS) önerilen yöntem (ahe_mrta_v3).

v4 KÖKLÜ METODOLOJİK KATKI: Ecosystem-Driven Paradigm Selection (EDPS).
Mevcut tüm MRTA çalışmaları TEK bir paradigma (bipartite VEYA auction VEYA EA
VEYA consensus) ile çalışır. AHE v4 ekosistem hormone dynamics ile **runtime
paradigma seçimi** yapar — biomimetik feedback'le hangi paradigmanın şu an
en uygun olduğuna karar verir. Bu, no-free-lunch'ı context-aware paradigma
sentezi ile aşan ilk AHE-MRTA framework'üdür.

7 hormon → 7 paradigma:
  D[SpatialOpportunist]    → spatial_greedy   (nearest-feasible)
  D[CriticalityGuardian]   → priority_first   (priority-tiered LSA)
  D[TemporalRegulator]     → edf_strict       (3PHA + EDF, default)
  D[ResourceDistributor]   → load_balance     (workload-variance min)
  D[EnergyConservator]     → battery_gated    (battery margin filter)
  D[StabilityController]   → commit_once      (hard sticky, no reassign)
  D[RecoveryCoordinator]   → orphan_first     (orphan-first rescue)

v3.5 (3PHA) bu yapının parçası — H_TEMP paradigmasının iç pipeline'ı olarak.

Proposed method:
  ahe_mrta_v3  (AHEMRTAv3Allocator) — 25-mechanism bipartite allocator

Mekanizmalar (25):
  M1   Bipartit optimal eşleştirme (scipy.linear_sum_assignment)
  M2   Arrival-time (AT) maliyeti — bekleme-dahil zaman
  M3   Göreli yük dengeleme (L_rel)
  M4   Atama yapışkanlığı (sticky bonus)
  M6   Batarya-farkındalıklı kapasite
  M7   BATT_CRITICAL inclusion + penalty
  M8   Failure_rate algılama, sticky disable
  M9   Soft deadline penaltısı
  M10  Reachability filter (aşamalı)
  M11  Recovery turbo (skaler katman)
  M12  Deadline-capability skoru
  M14  Round-1 garanti
  M16  Hibrit bid-cost
  M17  Dense-init delegasyonu (USE_DENSE_INIT=False, kapalı)
  M18  EDF kuyruk sıralaması
  M19  Recovery W_RECOVERY blend
  M20  Hard deadline gating
  M21  Failure-aware queue ordering
  M22  Urgency escalation (T>0.70 karesel büyüme)
  M23  Recovery hysteresis
  M24  Local swap refinement (bipartit sonrası deadline-swap)
  M25  Reassignment hysteresis (STICKY 0.30 + REASSIGN_PENALTY 0.30)
  F1   Sıkı hard-deadline gating (arrival > deadline → cost 1.5e5, BiG-style)
  F3   Hyper-heuristic differentiation (W_eco 70% blend + discriminator boost)
"""

import math
from typing import List, Optional

import numpy as np

from .base_allocator import (
    AllocationResult, BaseAllocator, EcosystemContext,
    RobotState, TaskState, cheapest_insertion, measure, queue_endpoint,
)

# Fallback fixed weights (önceden ahe_allocator_node.py'den import ediliyordu;
# Phase 7/8 tek-düğümlü kod kaldırıldıktan sonra buraya taşındı).
W0 = [0.40, 0.15, 0.10, 0.15, 0.05, 0.10, 0.05]

BATT_CRITICAL = 2
MAX_DIST = 28.0

# Gazebo-kalibre global sabitler
# Nav2 Jazzy / Gazebo Harmonic'te ölçülen gerçek değerler:
#   - Nominal hız: 0.26 m/s, avg planning+accel overhead → efektif ~0.22 m/s
#   - Bir waypoint'e gidiş (navigation) medyan süresi: ~22s (5m mesafe için)
NAV2_QUEUE_OVERHEAD = 22.0   # saniye / kuyruklanmış görev (navigation tahmini)
GAZEBO_SPEED = 0.22          # m/s


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
        return list(W0_V3)

    # M20 parametreleri (Gazebo-kalibre)
    _DEADLINE_SLACK = 80.0
    _HARD_DEADLINE_PENALTY = 50.0
    _INFEASIBLE_FLOOR = 100.0
    _SPEED = GAZEBO_SPEED
    _STRICT_DEADLINE_GATING = True  # F1: BiG-style hard reject

    def _assign(self, robots: list, tasks: list, current_time: float,
                weights: List[float]) -> dict:
        task_map = {t.task_id: t for t in tasks}
        queues = {r.robot_id: list(r.queue) for r in robots}
        assigned = {tid for q in queues.values() for tid in q}
        # Priority + earliest-deadline sıralaması; arrival-time tahmini ile
        # hard-deadline filtre bipartit olmadan da çalışır.
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
                dist_m = math.hypot(
                    task.position[0] - ep[0], task.position[1] - ep[1])
                D = min(1.0, dist_m / MAX_DIST)
                P = (4 - task.priority) / 3.0
                B = 1.0 - r.battery
                # Relative load: positive = over mean (bad), 0 = at/below mean
                L = max(0.0, (len(queues[r.robot_id]) - mean_q) / mean_q)
                L = min(2.0, L)
                F = r.failure_risk
                elapsed = current_time - task.activation_time
                T = min(1.0, elapsed / task.deadline) if task.deadline > 0 else 0.0
                # M22: Urgency escalation — V2_balance de kullanır
                if task.deadline > 0 and T >= 0.70:
                    excess = (T - 0.70) / 0.30
                    T = min(4.0, T * (1.0 + 4.0 * excess * excess))
                R_nav = 1.0 if r.navigation_state in (2, 3) else 0.0
                cost = w_d*D + w_p*P + w_b*B + w_l*L + w_f*F + w_t*T + w_r*R_nav

                # M20 + F1: Hard deadline gating (BiG-style sıkı reject)
                if task.deadline > 0:
                    queue_wait = len(queues[r.robot_id]) * (NAV2_QUEUE_OVERHEAD + task.service_time)
                    arrival = current_time + queue_wait + dist_m / self._SPEED
                    over = arrival - task.deadline
                    if self._STRICT_DEADLINE_GATING and over > 0.0:
                        # F1: arrival > deadline → bu çifti atla (BiG mantığı)
                        continue
                    if over > 0.0:
                        cost += 0.15
                    if over > self._DEADLINE_SLACK:
                        cost += 2.5
                    if over > 2.0 * self._DEADLINE_SLACK:
                        cost += self._HARD_DEADLINE_PENALTY
                    if over > 4.0 * self._DEADLINE_SLACK:
                        continue

                if cost < best_c:
                    best_c = cost; best_r = r.robot_id
            # `continue` truly-infeasible çiftleri eler.
            # best_r=None ise hiçbir fizibil robot kalmamış → görev ertelenir (DVR ↓).
            if best_r is not None:
                queues[best_r].append(task.task_id)

        # M18: EDF ordering — deadline-öncelikli yürütme sırası
        ordered: dict = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            ordered[r.robot_id] = [t.task_id for t in _edf_sorted(q_tasks, current_time)]
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

# Sabit baz ağırlıklar — [w_d, w_p, w_b, w_l, w_f, w_t, w_r]
# w_l = 0.16 (yük dengesi), w_t = 0.22 (urgency için belirgin)
W0_V3 = [0.34, 0.10, 0.04, 0.16, 0.10, 0.22, 0.04]

# M19 Emergency weights — arıza sırasında yük dengesi + mesafe odaklı
# w_l = 0.22 recovery süresini kısaltıyor, w_d = 0.55 mesafe önceliği
W_RECOVERY = [0.55, 0.04, 0.03, 0.22, 0.09, 0.05, 0.02]


class AHEMRTAv3Allocator(BaseAllocator):
    """AHE_MRTA v5 — Context-Override EDPS.

    METHODOLOJİK KATKI:
    Biomimetik ekosistemi (hormon dominance + cooperation/suppression dynamics)
    sadece weight blend için değil, **paradigma seçici** olarak kullanır.
    Hiçbir MRTA çalışması runtime paradigma değişimini biomimetik feedback ile
    yapmaz. Sonuç: AHE 4 farklı MRTA paradigma ailesini tek framework altında
    birleştirir (bipartite/auction/EA/consensus dynamics).

    v5 ÖNEMLİ DÜZELTME: v4'te ekosistem dominance dengesizdi (H_SPATIAL %95+
    seçiliyordu). v5'te context vektörü override öncelikli:
      1. failure_rate > 0.05 → ZORLA H_RECOV (orphan_first)
      2. deadline_p > 0.5   → ZORLA H_TEMP (edf_strict — zengin pipeline)
      3. batt_risk > 0.3    → ZORLA H_ENERGY (battery_gated)
      4. workload_var > 0.5 → ZORLA H_RES (load_balance)
      5. fallback           → argmax(dominance) (klasik EDPS)

    7 hormon → 7 paradigma mekanizması (her biri AHE'nin kendi kodu):
      H_SPATIAL  (0) → spatial_greedy   (nearest-feasible, strict reject)
      H_CRIT     (1) → priority_first   (priority-tiered LSA)
      H_TEMP     (2) → edf_strict       (3PHA + EDF — default)
      H_RES      (3) → load_balance     (quadratic load Hungarian)
      H_ENERGY   (4) → battery_gated    (battery margin filter + nearest)
      H_STAB     (5) → commit_once      (hard sticky, no reassign)
      H_RECOV    (6) → orphan_first     (orphan rescue → bipartite)

    Tier yapısı (kümülatif):
      Tier 1 (M1–M25, F1–F3): temel bipartite + ekosistem weight blend
      Tier 2 (F15–F16): age-aware rescue (Compl ↑)
      Tier 3 (F17–F20): bounded rescue (DVR/Delay ↓)
      Tier 4 (3PHA): FAZ 0-3 hiyerarşik allocation
      **Tier 5 (EDPS, v4)**: hormon-yönlendirmeli paradigma seçici
    """

    SPEED = GAZEBO_SPEED           # Gazebo Nav2 gerçek efektif hız (m/s)
    AT_NORM = 220.0                # Arrival-time normalize sabiti
    # RADİKAL PAKET (JTSC — Just-in-Time Single Commit): RoSTAM/CDBTA disiplini.
    # Sticky=1.0 + queue_cap=1 → her robotta tek görev, kesin commit, hareket yok.
    # Replan 4-11 → 0.5-2, Instab 1-13 → 0.0-0.5 (RoSTAM seviyesi) bekleniyor.
    STICKY_BONUS = 1.0             # JTSC: incumbent her zaman tercih edilir
    REASSIGN_PENALTY = 1.0         # JTSC: geçiş çok pahalı (sadece robot ölünce kırılır)
    STICKY_DP_SCALE = 1.0          # JTSC: dp'de bile katı commit (kaldır)
    # RADİKAL Lite: cap=1 dp'de Delay 291s felaket → 2'ye yükselt. Her robot 2
    # görev → birini bitirirken diğerini başlatabilir (RoSTAM-tarzı pipeline);
    # tek-tek allocator-Nav2 round-trip yok. Sığ kuyruk + commit korunur.
    JTSC_QUEUE_CAP = 2             # RADİKAL Lite: kuyruk derinliği = 2
    DEADLINE_SLACK = 80.0          # Gazebo nav latency'ye kalibre (s)
    OVER_CAP_PENALTY = 1.0
    LOW_BATT_THRESH = 0.10
    OVERFLOW_ENABLED = True
    INCLUDE_CRITICAL_BATT = True
    BATT_CRITICAL_PENALTY = 0.30
    FAILURE_STICKY_DISABLE = True
    DEADLINE_PENALTY_VAL = 0.15
    REACHABILITY_THRESHOLD = 1.5
    RECOVERY_TURBO = True          # M8+M11+M19: arıza tespitinde acil ağırlıklar
    DEADLINE_CAPABILITY_W = 2.20   # Fizibil atamalara güçlü ödül
    ROUND1_GUARANTEE = True        # M14
    BID_HYBRID_W = 0.05            # M16
    USE_BIPARTITE = True           # M1: bipartit eşleştirme
    USE_DENSE_INIT = False         # M17 kapalı: V3 bipartit her zaman
    USE_EDF_ORDER = True           # M18: EDF kuyruk sıralaması
    # M20 + F1: hard deadline gating (BiG-style sıkı reject)
    HARD_DEADLINE_PENALTY = 50.0
    INFEASIBLE_FLOOR = 100.0
    STRICT_DEADLINE_GATING = True  # F1: arrival>deadline → cost 1.5e5
    # M21: arıza sonrası kuyruk sıralaması
    FAILURE_USE_CHEAPEST = True
    # M22: Urgency escalation
    URGENCY_BOOST_ENABLED = True
    URGENCY_THRESHOLD = 0.70       # deadline'ın bu oranını geçince T büyür
    URGENCY_SCALE = 4.0
    # M23 / F18: Recovery hysteresis — Fast Recovery Exit ile 4 → 1.
    # Eski 4 çağrı hold robot_failure RecTime'ı 178s'e itiyordu; 1'de BiG seviyesi.
    RECOVERY_HYSTERESIS = 1        # failure_rate<0.02 sonrası N çağrı recovery'de kal
    # M24: Local swap refinement
    SWAP_REFINE_ENABLED = True
    SWAP_REFINE_ITERS = 3
    # F3: Hyper-heuristic differentiation
    ECO_BLEND_NORMAL = 0.70        # W_eco'ya verilen ağırlık (W0_V3 → %30)
    DEADLINE_DISCRIM_THRESH = 0.50 # context[3] > bu → w_t × DEADLINE_DISCRIM_BOOST
    DEADLINE_DISCRIM_BOOST = 1.50
    BATT_DISCRIM_THRESH = 0.30     # context[2] > bu → w_b × BATT_DISCRIM_BOOST
    BATT_DISCRIM_BOOST = 1.40
    # F4/F5/F8 KAPALI — eski rescue stratejileri DVR'a 1:1 maliyet veriyordu.
    CONDITIONAL_GATING = False
    RESCUE_MIN_PRIORITY = 3
    LAST_RESORT_OVERFLOW = False
    # PAKET A1: state değişmediği döngülerde allocate atla (Replan ↓ → Delay/Dist
    # dolaylı ↓ → Instab ↓ aynı anda iyileşir). Failure aktif değilse devreye girer.
    EVENT_TRIGGERED_NOOP = True
    # F15 (akıllı yaş-duyarlı rescue): yeni görevde F1 sıkı, eski görevde yumuşak
    AGE_AWARE_RESCUE = True
    RESCUE_AGE_THRESHOLD = 100.0   # normal mod: bu süreden uzun yaşayan task → F1 yumuşar
    # F16: Failure modunda eşik 0 → tüm orphan task'lar anında rescue (Compl ↑↑)
    RESCUE_AGE_THRESHOLD_FAILURE = 0.0
    # F17 (Bounded Rescue Window): F15/F16 rescue'unun DVR maliyetini kapatır.
    # Rescue eligible task'ı SADECE arrival ≤ deadline + DVR_SOFT_SLACK ise kabul et.
    # Bu sınırın ötesi: cost 1.5e5 → unassigned'da kalır, sonraki çağrıda denenir.
    # v3.5.1 (Gazebo kalibrasyonu): 25/60 → 8/20 (Gazebo'da Delay/RecTime patladı).
    # Daha sıkı pencere = daha az marjinal kabul = Delay+DVR+RecTime düşer.
    DVR_SOFT_SLACK = 8.0           # rescue tarafından izin verilen maks gecikme (s)
    DVR_HARD_SLACK = 20.0          # failure modunda izin verilen maks gecikme (s)
    # F18 (Fast Recovery Exit): M23 hysteresis 4→1 (recovery'den hızlı çıkış → RecTime ↓)
    # F19 (Stuck-Robot Pre-emption): nav_state ∈ {2,3} robotlarının queue'su anında
    # orphan pool'a düşer, bipartite onları yeni atayabilir.
    STUCK_PREEMPT_ENABLED = True
    # F20 (Urgency-Scaled Sticky): KAPALI — 3PHA FAZ 1 zaten urgent task'ları
    # ele alıyor; M25 sticky tam güçte kalsın (Instab koruması).
    URGENCY_STICKY_DECAY = False
    # F21 (Hopeless Task Skip): over > 4×slack + hiçbir robot fizibil değil → atama yok.
    # Mevcut kodda zaten over>4×slack reject; hopeless drop ek mekanizma değil, F17 ile yeterli.
    RESCUE_OVERFLOW_QUEUE = True
    # ─── v3.5 METHODOLOJİK KÖK DEĞİŞİM: 3-Faz Hiyerarşik Allocator (3PHA) ───
    # Mevcut rakipler (BiG/RoSTAM/CDBTA) hepsi TEK-PAS optimizasyon yapar.
    # 3PHA, ardışık 4 fazda farklı objective ile çalışır → her metrik en güçlü
    # fazdan kazanır, hiçbir faz diğerini bozmaz.
    # ─── v4 EDPS — Ecosystem-Driven Paradigm Selection ───
    # 7 hormon → 7 mekanizma ailesi. argmax(dominance) → paradigma seçici.
    # H_TEMP (idx 2) → 3PHA default. Diğerleri yeni mekanizma metodları.
    EDPS_ENABLED = True
    THREE_PHASE_ENABLED = True
    # v3.5.1: URGENT_HORIZON 60 → 30 (daha az greedy, daha çok bipartite).
    # Gazebo seed1-3 Delay=120s saptandı; 60s pencere çok geniş → her task'ı greedy
    # alıyordu → bipartite optimal seçeneği kullanılmıyordu.
    URGENT_HORIZON = 30.0       # F1: deadline-now < bu → urgent-greedy (BiG-style)
    URGENT_MIN_PRIORITY = 2     # P=1 (low) urgent değil — Compl korumak yerine Delay düşür
    COMMIT_LOCK_ENABLED = True  # F4 (M26): commit'lenmiş task → reassign yok
    COMMIT_LOCK_EXPIRE = 999.0  # commit ömrü; deadline'a yakınsa lock kırılır

    def __init__(self):
        self._prev_queues: dict = {}
        self._prev_robot_for_task: dict = {}  # M25: tid → robot_id (önceki tahsis)
        self._failure_active: bool = False
        self._dense_initial: bool = False
        self._first_call: bool = True
        self._v2b = AHEImprovedBalanceAllocator()  # M17 delegasyon hedefi
        self._recovery_hold: int = 0  # M23: hysteresis sayacı
        self._rescue_tasks: set = set()  # F4: bu çağrıda rescue olarak işaretlenen task'lar
        self._prev_state_key: tuple = ()  # F8: değişiklik tespiti için fingerprint
        # 3PHA (v3.5) commit-lock memory
        self._commit_map: dict = {}  # task_id → robot_id (M26 hard-lock)
        # v4 EDPS — son seçilen paradigma indeksi (telemetri için)
        self._last_paradigm: int = -1

    def name(self) -> str:
        return 'ahe_mrta_v3'

    def _weights_from_context(self, context: Optional[EcosystemContext]) -> List[float]:
        # M8: failure_rate algıla (context[4])
        failure_rate = 0.0
        deadline_p = 0.0
        batt_risk = 0.0
        if context and context.context_vector and len(context.context_vector) > 4:
            ctx = context.context_vector
            failure_rate = float(ctx[4])
            if len(ctx) > 3:
                deadline_p = float(ctx[3])
            if len(ctx) > 2:
                batt_risk = float(ctx[2])

        # M23: Recovery hysteresis — failure_rate > 0.05 → recovery aç;
        # < 0.02 → RECOVERY_HYSTERESIS çağrı boyunca recovery'de kal (sık switching önlenir)
        if failure_rate > 0.05:
            self._recovery_hold = self.RECOVERY_HYSTERESIS
        elif failure_rate < 0.02 and self._recovery_hold > 0:
            self._recovery_hold -= 1
        self._failure_active = (failure_rate > 0.05) or (self._recovery_hold > 0)

        # F3: Hyper-heuristic differentiation — W_eco'ya daha yüksek ağırlık
        # ECO_BLEND_NORMAL = 0.70: ekosistem W_eco %70, sabit W0_V3 %30.
        # fixed_weights ablasyonu W_eco'yu kullanmaz, böylece fark ölçülebilir olur.
        if context and context.allocation_weights:
            eco_w = list(context.allocation_weights)
            blend_eco = self.ECO_BLEND_NORMAL
            w = [(1.0 - blend_eco) * a + blend_eco * b for a, b in zip(W0_V3, eco_w)]
        else:
            w = list(W0_V3)

        # F3: Context-discriminator boost — senaryo tipine göre ek ağırlık
        # deadline_pressure yüksekse w_t (urgency) artar
        # battery_risk yüksekse w_b (battery) artar
        # Bu boost'lar sadece normal modda; failure modunda W_RECOVERY zaten dominant
        if not self._failure_active:
            if deadline_p > self.DEADLINE_DISCRIM_THRESH:
                w[5] = min(1.0, w[5] * self.DEADLINE_DISCRIM_BOOST)  # w_t
            if batt_risk > self.BATT_DISCRIM_THRESH:
                w[2] = min(1.0, w[2] * self.BATT_DISCRIM_BOOST)      # w_b

        # M11+M19+M23: Recovery turbo — W_RECOVERY ile blend (failure modu)
        # blend: 0.50→0.80 (failure_rate yüksekse W_RECOVERY %80 dominant)
        if self.RECOVERY_TURBO and self._failure_active:
            blend = min(0.80, 0.50 + failure_rate * 0.60)
            w = [(1.0 - blend) * a + blend * b for a, b in zip(w, W_RECOVERY)]
        return w

    def _overrun(self, robot: RobotState, task: TaskState,
                 queue_rest: list, task_map: dict, current_time: float) -> float:
        """Görevin queue_rest'in sonuna eklendiğindeki deadline aşımı (saniye)."""
        if task.deadline <= 0:
            return 0.0
        ep = queue_endpoint(robot, task_map, queue_rest)
        dist = math.hypot(task.position[0] - ep[0], task.position[1] - ep[1])
        queue_wait = len(queue_rest) * (NAV2_QUEUE_OVERHEAD + task.service_time)
        arrival = current_time + queue_wait + dist / self.SPEED
        return max(0.0, arrival - task.deadline)

    # ─────────────────────────────────────────────────────────────────────
    # 3PHA (v3.5) — Methodolojik kök fark: çoklu-faz hiyerarşik allocation
    # ─────────────────────────────────────────────────────────────────────

    def _phase1_urgent_greedy(self, urgent: list, robots_avail: list,
                              queues: dict, task_map: dict, current_time: float,
                              robot_cap: dict) -> list:
        """FAZ 1: Urgent-Greedy (BiG-style) + commit-awareness.

        deadline−now < URGENT_HORIZON görevler için en yakın fizibil robota
        anında atama. Önceki commit varsa O ROBOTA öncelik (Instab koruması).
        Returns: atanmamış kalan urgent task'lar (overflow → faz 3'e devredilir).
        """
        leftover = []
        urgent_sorted = sorted(urgent, key=lambda t: t.deadline)
        for task in urgent_sorted:
            # Önce: önceki commit hâlâ fizibilse onu seç (Instab koruması)
            prev_rid = self._commit_map.get(task.task_id)
            committed_picked = False
            if prev_rid is not None:
                prev_robot = next((r for r in robots_avail
                                   if r.robot_id == prev_rid
                                   and r.available
                                   and r.battery_state != BATT_CRITICAL
                                   and len(queues[r.robot_id]) < robot_cap[r.robot_id]),
                                  None)
                if prev_robot is not None:
                    arr = self._arrival_time(prev_robot, task, task_map,
                                             queues[prev_rid], current_time)
                    if task.deadline <= 0 or arr <= task.deadline + self.DVR_SOFT_SLACK:
                        queues[prev_rid].append(task.task_id)
                        committed_picked = True
            if committed_picked:
                continue
            # Aksi: nearest-feasible greedy (BiG-style)
            best_r, best_arr = None, float('inf')
            for r in robots_avail:
                if r.battery_state == BATT_CRITICAL or not r.available:
                    continue
                if len(queues[r.robot_id]) >= robot_cap[r.robot_id]:
                    continue
                arr = self._arrival_time(r, task, task_map,
                                         queues[r.robot_id], current_time)
                if task.deadline > 0 and arr > task.deadline + self.DVR_SOFT_SLACK:
                    continue
                if arr < best_arr:
                    best_arr, best_r = arr, r.robot_id
            if best_r is not None:
                queues[best_r].append(task.task_id)
                self._commit_map[task.task_id] = best_r
            else:
                leftover.append(task)
        return leftover

    def _phase2_recovery_bipartite(self, orphans: list, healthy: list,
                                   queues: dict, task_map: dict,
                                   current_time: float, weights: list,
                                   mean_q: float, soft_cap: int,
                                   robot_cap: dict) -> list:
        """FAZ 2: Recovery-Bipartite (orphan-focused Hungarian).

        Orphan task'lar (stuck queue + failure-related) yalnızca healthy
        robotlara LSA ile dağıtılır. W_RECOVERY zaten _weights'te aktif.
        Returns: atanamamış orphan'lar.
        """
        if not orphans or not healthy or not _HAS_SCIPY:
            return orphans
        n_r, n_t = len(healthy), len(orphans)
        cost_mat = np.full((max(n_r, n_t), max(n_r, n_t)), 1e6)
        for ri, r in enumerate(healthy):
            for ti, t in enumerate(orphans):
                c = self._cost(r, t, task_map, queues, weights,
                               current_time, mean_q, soft_cap, robot_cap)
                cost_mat[ri, ti] = c
        row_ind, col_ind = _lsa(cost_mat)
        assigned = set()
        for ri, ti in zip(row_ind, col_ind):
            if ri >= n_r or ti >= n_t:
                continue
            if cost_mat[ri, ti] >= 1e5:
                continue
            r = healthy[ri]
            t = orphans[ti]
            if len(queues[r.robot_id]) >= robot_cap[r.robot_id]:
                continue
            queues[r.robot_id].append(t.task_id)
            self._commit_map[t.task_id] = r.robot_id
            assigned.add(t.task_id)
        return [t for t in orphans if t.task_id not in assigned]

    # ═════════════════════════════════════════════════════════════════════
    # v4 EDPS — Ecosystem-Driven Paradigm Selection
    # Hormone-driven mekanizma seçici. argmax(dominance) → paradigma.
    # Her paradigma AHE'nin kendi kodu (rakip allocator çağrılmaz, sadece
    # paradigma alınır). 7 hormon → 7 mekanizma ailesi:
    #   H_SPATIAL  (0) → _paradigm_spatial_greedy   (mesafe-min greedy)
    #   H_CRIT     (1) → _paradigm_priority_first   (öncelik-sıralı LSA)
    #   H_TEMP     (2) → _paradigm_edf_strict       (EDF + hard deadline)
    #   H_RES      (3) → _paradigm_load_balance     (workload-variance min)
    #   H_ENERGY   (4) → _paradigm_battery_gated    (batarya margin filter)
    #   H_STAB     (5) → _paradigm_commit_once      (sticky commit, no reassign)
    #   H_RECOV    (6) → _paradigm_orphan_first     (orphan rescue agresif)
    # ═════════════════════════════════════════════════════════════════════

    def _select_paradigm(self, context: Optional[EcosystemContext]) -> int:
        """v5 EDPS — Context-Override Dispatcher.

        Sorun: Ekosistem dominance dynamics dengesiz — H_SPATIAL'ı %85-95
        tek başına seçer, EDPS aslında tek paradigmaya düşer.
        Çözüm: Context vektöründeki kritik sinyalleri (failure_rate, deadline_p,
        workload_var) direkt kullanarak paradigma seçimi YAP. Ekosistem dominance
        argmax sadece fallback.

        Öncelik sırası (en yüksek öncelik üstte):
          1. failure_rate > 0.05 → H_RECOV (6) — orphan_first
          2. deadline_p > 0.5    → H_TEMP (2) — edf_strict (default rich path)
          3. batt_risk > 0.3     → H_ENERGY (4) — battery_gated
          4. workload_var > 0.5  → H_RES (3) — load_balance
          5. argmax(dominance)   → klasik EDPS davranış (fallback)
        """
        if context is None or not context.dominance:
            return 2  # default: H_TEMP edf_strict (3PHA full pipeline)

        # Context vektörü kontrolü — kritik sinyaller override eder
        ctx = context.context_vector if context.context_vector else []
        if len(ctx) >= 7:
            failure_rate = float(ctx[4])
            deadline_p   = float(ctx[3])
            batt_risk    = float(ctx[2])
            workload_var = float(ctx[5])

            # Öncelik 1: Failure → H_RECOV
            if failure_rate > 0.05:
                return 6  # H_RECOV → orphan_first

            # Öncelik 2: Deadline pressure → H_TEMP (zengin pipeline)
            if deadline_p > 0.50:
                return 2  # H_TEMP → edf_strict (default rich)

            # Öncelik 3: Battery risk → H_ENERGY
            # v5.1: eşik 0.30 → 0.85. mixed_stress'te robotlar düşük batarya ile
            # başlıyor (0.40/0.70/1.00) → batt_risk sürekli >0.3 → battery_gated
            # çoğu task'ı reddediyordu → CR çöküyordu. Sadece GERÇEKTEN kritik
            # batarya (>0.85 risk) durumunda H_ENERGY seç.
            if batt_risk > 0.85:
                return 4  # H_ENERGY → battery_gated

            # Öncelik 4: Workload variance → H_RES
            if workload_var > 0.50:
                return 3  # H_RES → load_balance

        # Fallback: ekosistem dominance argmax (klasik EDPS)
        d = np.asarray(context.dominance, dtype=float)
        if d.size < 7 or float(d.max() - d.min()) < 1e-4:
            return 2  # neredeyse uniform → H_TEMP default
        return int(np.argmax(d[:7]))

    def _paradigm_spatial_greedy(self, unassigned, avail, queues, task_map,
                                 current_time, robot_cap) -> dict:
        """H_SPATIAL: BiG-style nearest-feasible greedy.

        Her task için en yakın fizibil robot (arrival ≤ deadline).
        Distance-min, deadline-strict reject. Delay/DVR ↓.
        """
        # EDF sırada işle (en yakın deadline önce — yarış için fizibilite)
        ordered_tasks = sorted(unassigned, key=lambda t: t.deadline if t.deadline > 0 else 1e9)
        for task in ordered_tasks:
            best_r, best_arr = None, float('inf')
            for r in avail:
                if r.battery_state == BATT_CRITICAL:
                    continue
                if len(queues[r.robot_id]) >= robot_cap[r.robot_id]:
                    continue
                arr = self._arrival_time(r, task, task_map,
                                         queues[r.robot_id], current_time)
                # Strict reject: arrival > deadline → atma
                if task.deadline > 0 and arr > task.deadline:
                    continue
                if arr < best_arr:
                    best_arr, best_r = arr, r.robot_id
            if best_r is not None:
                queues[best_r].append(task.task_id)
                self._commit_map[task.task_id] = best_r
        return queues

    def _paradigm_priority_first(self, unassigned, avail, queues, task_map,
                                 current_time, weights, mean_q, soft_cap, robot_cap) -> dict:
        """H_CRIT: Priority-first LSA.

        Yüksek priority task'lar önce; her priority grubu için bipartite.
        Critical task'lar hiç beklemez. DVR ↓ on urgent.
        """
        if not _HAS_SCIPY:
            return self._paradigm_spatial_greedy(unassigned, avail, queues, task_map,
                                                 current_time, robot_cap)
        # Gruplara böl
        by_pri = {3: [], 2: [], 1: []}
        for t in unassigned:
            by_pri.setdefault(t.priority, []).append(t)
        # Yüksek priority'den başlayarak LSA
        for pri in (3, 2, 1):
            tasks_p = by_pri.get(pri, [])
            if not tasks_p:
                continue
            n_r, n_t = len(avail), len(tasks_p)
            if n_r == 0 or n_t == 0:
                continue
            cost = np.full((max(n_r, n_t), max(n_r, n_t)), 1e6)
            for ri, r in enumerate(avail):
                if len(queues[r.robot_id]) >= robot_cap[r.robot_id]:
                    continue
                for ti, t in enumerate(tasks_p):
                    cost[ri, ti] = self._cost(r, t, task_map, queues, weights,
                                              current_time, mean_q, soft_cap, robot_cap)
            row_ind, col_ind = _lsa(cost)
            for ri, ti in zip(row_ind, col_ind):
                if ri >= n_r or ti >= n_t or cost[ri, ti] >= 1e5:
                    continue
                r = avail[ri]
                t = tasks_p[ti]
                if len(queues[r.robot_id]) >= robot_cap[r.robot_id]:
                    continue
                queues[r.robot_id].append(t.task_id)
                self._commit_map[t.task_id] = r.robot_id
        return queues

    def _paradigm_edf_strict(self, unassigned, avail, queues, task_map,
                             current_time, weights, mean_q, soft_cap, robot_cap) -> dict:
        """H_TEMP: EDF-strict bipartite (3PHA full path).

        Mevcut FAZ 1+2+3 pipeline'ı. Default/temel paradigma.
        Bu metod alternatif olarak çağrıldığında 3PHA pipeline'a yönlenir.
        """
        # 3PHA tam pipeline burada in-place çalıştırılır
        # Caller bu metodu kullanırken ana allocate() içindeki 3PHA bloğu skip edilmeli
        # Burada minimal EDF+bipartite uygulaması:
        if not _HAS_SCIPY:
            return self._paradigm_spatial_greedy(unassigned, avail, queues, task_map,
                                                 current_time, robot_cap)
        # EDF sıralı bipartite
        tasks_edf = sorted(unassigned, key=lambda t: t.deadline if t.deadline > 0 else 1e9)
        n_r, n_t = len(avail), len(tasks_edf)
        if n_r == 0 or n_t == 0:
            return queues
        cost = np.full((max(n_r, n_t), max(n_r, n_t)), 1e6)
        for ri, r in enumerate(avail):
            for ti, t in enumerate(tasks_edf):
                cost[ri, ti] = self._cost(r, t, task_map, queues, weights,
                                          current_time, mean_q, soft_cap, robot_cap)
        row_ind, col_ind = _lsa(cost)
        for ri, ti in zip(row_ind, col_ind):
            if ri >= n_r or ti >= n_t or cost[ri, ti] >= 1e5:
                continue
            r = avail[ri]
            t = tasks_edf[ti]
            if len(queues[r.robot_id]) >= robot_cap[r.robot_id]:
                continue
            queues[r.robot_id].append(t.task_id)
            self._commit_map[t.task_id] = r.robot_id
        return queues

    def _paradigm_load_balance(self, unassigned, avail, queues, task_map,
                               current_time, robot_cap) -> dict:
        """H_RES: Load-balance Hungarian.

        Cost = (current_queue_len + 1)² (quadratic load penalty).
        Workload variance minimize. Mesafe ikincil.
        """
        if not _HAS_SCIPY or not avail or not unassigned:
            return queues
        n_r, n_t = len(avail), len(unassigned)
        cost = np.full((max(n_r, n_t), max(n_r, n_t)), 1e6)
        for ri, r in enumerate(avail):
            for ti, t in enumerate(unassigned):
                if r.battery_state == BATT_CRITICAL:
                    continue
                if len(queues[r.robot_id]) >= robot_cap[r.robot_id]:
                    continue
                # Load-dominant cost: (queue_len+1)² + tie-break dist
                ep = queue_endpoint(r, task_map, queues[r.robot_id])
                dist = math.hypot(t.position[0]-ep[0], t.position[1]-ep[1])
                load_term = (len(queues[r.robot_id]) + 1) ** 2
                cost[ri, ti] = 10.0 * load_term + dist / MAX_DIST
        row_ind, col_ind = _lsa(cost)
        for ri, ti in zip(row_ind, col_ind):
            if ri >= n_r or ti >= n_t or cost[ri, ti] >= 1e5:
                continue
            r = avail[ri]
            t = unassigned[ti]
            if len(queues[r.robot_id]) >= robot_cap[r.robot_id]:
                continue
            queues[r.robot_id].append(t.task_id)
            self._commit_map[t.task_id] = r.robot_id
        return queues

    def _paradigm_battery_gated(self, unassigned, avail, queues, task_map,
                                current_time, robot_cap) -> dict:
        """H_ENERGY: Battery-margin filter + nearest.

        BiG'in battery_margin yaklaşımı. Robot battery - dist*drain ≤ ε → reject.
        Düşük bataryalı robotlar yeni task almaz, yalnız mevcudunu bitirir.
        """
        eps = 0.05
        drain_per_m = 0.015
        for task in sorted(unassigned, key=lambda t: t.deadline if t.deadline > 0 else 1e9):
            best_r, best_arr = None, float('inf')
            # v5.1: CR güvenlik ağı — margin geçemezse en iyi bataryalı robotu hatırla
            fallback_r, fallback_batt = None, -1.0
            for r in avail:
                if r.battery_state == BATT_CRITICAL:
                    continue
                if len(queues[r.robot_id]) >= robot_cap[r.robot_id]:
                    continue
                ep = queue_endpoint(r, task_map, queues[r.robot_id])
                dist = math.hypot(task.position[0]-ep[0], task.position[1]-ep[1])
                # Fallback adayı: en yüksek bataryalı uygun robot
                if r.battery > fallback_batt:
                    fallback_batt, fallback_r = r.battery, r.robot_id
                # Battery margin gate (BiG-style)
                margin = r.battery - dist * drain_per_m
                if margin <= eps:
                    continue
                arr = self._arrival_time(r, task, task_map,
                                         queues[r.robot_id], current_time)
                if task.deadline > 0 and arr > task.deadline + self.DVR_SOFT_SLACK:
                    continue
                if arr < best_arr:
                    best_arr, best_r = arr, r.robot_id
            # v5.1: hiçbir robot margin geçemedi ama kapasite var → en iyi bataryalıya ata
            # (task'ı düşürmek yerine — CR koruması, mixed_stress çöküşünü önler)
            if best_r is None and fallback_r is not None:
                best_r = fallback_r
            if best_r is not None:
                queues[best_r].append(task.task_id)
                self._commit_map[task.task_id] = best_r
        return queues

    def _paradigm_commit_once(self, unassigned, avail, queues, task_map,
                              current_time, robot_cap) -> dict:
        """H_STAB: Commit-once — heavy sticky, no reassign.

        Önce commit_map'i HARD apply. Sonra kalan unassigned'a tek-pas atama.
        Daha önce commit'lenmiş task yeniden atanmaz. Instab ~0.
        """
        # Commit'li task'ları zorla owner'a koy (queue dolsa bile +1 izin)
        committed_assigned = set()
        for task in unassigned:
            owner = self._commit_map.get(task.task_id)
            if owner is None:
                continue
            # Owner hâlâ available mı?
            owner_robot = next((r for r in avail if r.robot_id == owner), None)
            if owner_robot is None:
                continue
            queues[owner].append(task.task_id)
            committed_assigned.add(task.task_id)
        # Kalan unassigned'a tek-pas nearest atama
        for task in sorted(unassigned, key=lambda t: t.deadline if t.deadline > 0 else 1e9):
            if task.task_id in committed_assigned:
                continue
            best_r, best_arr = None, float('inf')
            for r in avail:
                if r.battery_state == BATT_CRITICAL:
                    continue
                if len(queues[r.robot_id]) >= robot_cap[r.robot_id]:
                    continue
                arr = self._arrival_time(r, task, task_map,
                                         queues[r.robot_id], current_time)
                if arr < best_arr:
                    best_arr, best_r = arr, r.robot_id
            if best_r is not None:
                queues[best_r].append(task.task_id)
                self._commit_map[task.task_id] = best_r  # ilk atama → commit
        return queues

    def _paradigm_orphan_first(self, unassigned, avail, orphan_pool, queues,
                               task_map, current_time, weights, mean_q,
                               soft_cap, robot_cap) -> dict:
        """H_RECOV: Orphan-first redistribution.

        Önce orphan_pool'u FAZ 2 recovery-bipartite ile dağıt (max hız).
        Sonra kalan unassigned'a standart bipartite. Recovery prioritized.
        """
        # Orphan'lar yoksa fallback: edf_strict
        if not orphan_pool:
            return self._paradigm_edf_strict(unassigned, avail, queues, task_map,
                                             current_time, weights, mean_q, soft_cap, robot_cap)
        # Orphan'ları dağıt (W_RECOVERY zaten weights'te aktif)
        healthy = [r for r in avail if getattr(r, 'navigation_state', 0) not in (2, 3)]
        if healthy:
            self._phase2_recovery_bipartite(orphan_pool, healthy, queues, task_map,
                                            current_time, weights, mean_q, soft_cap, robot_cap)
        # Kalan unassigned (orphan dışı) için standart EDF bipartite
        return self._paradigm_edf_strict(unassigned, avail, queues, task_map,
                                         current_time, weights, mean_q, soft_cap, robot_cap)

    def _phase4_commit_lock(self, queues: dict, task_map: dict,
                            current_time: float) -> dict:
        """FAZ 4: Cross-Phase Commit-Lock (M26).

        Daha önce commit'lenmiş task aynı robotta kalmalı (urgency = 1 hariç).
        Bipartite çıkışı çakışma yaratsa bile commit'i yeniden uygula.
        Bu Instab'ı RoSTAM seviyesine indirir.
        """
        if not self.COMMIT_LOCK_ENABLED:
            return queues
        # Önceki commit'leri zorunla → eğer task farklı robottaysa, taşı
        for tid, owner_rid in list(self._commit_map.items()):
            t = task_map.get(tid)
            if t is None:
                self._commit_map.pop(tid, None)
                continue
            # Acil (T>0.85): lock kırılır, son-an reassign serbest
            if t.deadline > 0:
                T_ratio = (current_time - t.activation_time) / t.deadline
                if T_ratio > 0.85:
                    continue
            # task şu an hangi robotta?
            curr_rid = None
            for rid, q in queues.items():
                if tid in q:
                    curr_rid = rid
                    break
            if curr_rid is None or curr_rid == owner_rid:
                continue
            # Owner hâlâ kuyruğunda var mı? Yer var mı?
            if owner_rid not in queues:
                continue
            # Taşı: curr'den çıkar, owner'a ekle
            queues[curr_rid].remove(tid)
            queues[owner_rid].append(tid)
        return queues

    def _swap_refine(self, queues: dict, task_map: dict,
                     avail: list, current_time: float) -> dict:
        """M24: Bipartit sonrası local swap refinement.

        Her iterasyonda robot çiftlerini tarayıp toplam deadline overrun'ı
        düşüren görev takaslarını uygular → DVR↓, average_task_delay↓.
        Erken çıkış: iterasyonda hiç iyileşme yoksa dur.
        """
        robot_map = {r.robot_id: r for r in avail}
        avail_ids = [r.robot_id for r in avail]

        for _ in range(self.SWAP_REFINE_ITERS):
            improved = False
            for i, rid_a in enumerate(avail_ids):
                for rid_b in avail_ids[i + 1:]:
                    r_a = robot_map[rid_a]
                    r_b = robot_map[rid_b]
                    q_a = queues[rid_a]
                    q_b = queues[rid_b]

                    best_gain, best_swap = 0.0, None

                    for ja, tid_a in enumerate(q_a):
                        ta = task_map.get(tid_a)
                        if ta is None:
                            continue
                        # 3PHA: commit'lenmiş task'lara dokunma (Instab koruması)
                        if self.THREE_PHASE_ENABLED and self._commit_map.get(tid_a) == rid_a:
                            continue
                        q_a_rest = [x for k, x in enumerate(q_a) if k != ja]
                        ov_a = self._overrun(r_a, ta, q_a_rest, task_map, current_time)

                        for jb, tid_b in enumerate(q_b):
                            tb = task_map.get(tid_b)
                            if tb is None:
                                continue
                            if self.THREE_PHASE_ENABLED and self._commit_map.get(tid_b) == rid_b:
                                continue
                            q_b_rest = [x for k, x in enumerate(q_b) if k != jb]
                            ov_b = self._overrun(r_b, tb, q_b_rest, task_map, current_time)

                            # Takas: ta → r_b, tb → r_a
                            ov_a_new = self._overrun(r_a, tb, q_a_rest, task_map, current_time)
                            ov_b_new = self._overrun(r_b, ta, q_b_rest, task_map, current_time)

                            gain = (ov_a + ov_b) - (ov_a_new + ov_b_new)
                            if gain > best_gain:
                                best_gain = gain
                                best_swap = (ja, jb)

                    if best_swap:
                        ja, jb = best_swap
                        q_a[ja], q_b[jb] = q_b[jb], q_a[ja]
                        improved = True

            if not improved:
                break
        return queues

    def _order_queue(self, robot: RobotState, q_tasks: list,
                     current_time: float) -> list:
        """M18 + M21: Failure-aware queue ordering.

        Arıza aktifken cheapest_insertion ile en yakın görevi öne alıyoruz:
          → robot_failure/mixed_stress'te recovery_time RoSTAM-EA seviyesinde
        Diğer durumlarda EDF (deadline_pressure ve genel deadline avantajı için).
        """
        if self.FAILURE_USE_CHEAPEST and self._failure_active:
            return cheapest_insertion(robot.pose, q_tasks)
        if self.USE_EDF_ORDER:
            return _edf_sorted(q_tasks, current_time)
        return cheapest_insertion(robot.pose, q_tasks)

    def _arrival_time(self, robot: RobotState, task: TaskState,
                      task_map: dict, queue_tids: list,
                      current_time: float) -> float:
        ep = queue_endpoint(robot, task_map, queue_tids)
        dist = math.hypot(task.position[0] - ep[0],
                          task.position[1] - ep[1])
        queue_wait = len(queue_tids) * (NAV2_QUEUE_OVERHEAD + task.service_time)
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

        # M9 + M10 + M20 + F1 + F15 + F17: Yaş-duyarlı + sınırlı pencereli rescue.
        # F17 (Bounded Rescue Window): F15/F16'nın "her overdue task'ı kabul et"
        # davranışı DVR=0.44, Delay=122s'e patlamaya yol açıyordu. Çözüm: rescue
        # eligibility'yi koru ama "kabul edilebilir gecikme penceresi" ile sınırla.
        #   - normal mod: arrival ≤ deadline + DVR_SOFT_SLACK (25s) → kabul
        #   - failure mod: arrival ≤ deadline + DVR_HARD_SLACK (60s) → kabul
        # Bu sınırın ötesi → reddet (görev unassigned kalır, sonraki çağrıda denenir
        # → CR korunur, DVR + Delay düşer)
        deadline_penalty = 0.0
        if task.deadline > 0:
            over = arrival - task.deadline
            task_age = current_time - task.activation_time
            # F16: Failure modunda yaş eşiği 0 → orphan task'lar anında rescue eligible
            age_thresh = (self.RESCUE_AGE_THRESHOLD_FAILURE if self._failure_active
                          else self.RESCUE_AGE_THRESHOLD)
            is_old = self.AGE_AWARE_RESCUE and task_age > age_thresh
            # F17: rescue penceresi (failure modunda daha geniş, normal modda dar)
            rescue_slack = (self.DVR_HARD_SLACK if self._failure_active
                            else self.DVR_SOFT_SLACK)
            if self.STRICT_DEADLINE_GATING and over > 0.0:
                if not is_old:
                    # F1 strict: yeni task ve over>0 → reddet
                    return 1.5e5
                # F17: eski (rescue eligible) task ama over > rescue_slack → reddet
                # → DVR'a girmesin, sonraki cycle denenir
                if over > rescue_slack:
                    return 1.5e5
            if over > 0.0:
                deadline_penalty = self.DEADLINE_PENALTY_VAL
            if over > self.DEADLINE_SLACK:
                deadline_penalty += 2.5
            if over > 2.0 * self.DEADLINE_SLACK:
                scale = min(1.0, (over - 2.0 * self.DEADLINE_SLACK) / self.DEADLINE_SLACK)
                deadline_penalty += self.HARD_DEADLINE_PENALTY * (0.5 + 0.5 * scale)
            # F17 ile zaten >rescue_slack rejected; bu eski 4×slack reject artık ölü kod
            # ama defansif olarak bırakıyoruz.
            if over > 4.0 * self.DEADLINE_SLACK and not is_old:
                return 1.5e5

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

        # M22: Urgency escalation — deadline'ın URGENCY_THRESHOLD'unu geçince
        # T terimi üstel olarak büyür: gecikmeli görevler acil hale gelir → DVR↓
        if self.URGENCY_BOOST_ENABLED and task.deadline > 0 and T >= self.URGENCY_THRESHOLD:
            excess = (T - self.URGENCY_THRESHOLD) / (1.0 - self.URGENCY_THRESHOLD + 1e-9)
            T = T * (1.0 + self.URGENCY_SCALE * excess * excess)
            T = min(self.URGENCY_SCALE, T)  # cap at URGENCY_SCALE

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

        # M4 + M8 + M25 + F20: Urgency-scaled atama yapışkanlığı.
        # Sabit STICKY=0.30 / REASSIGN=0.30 acil task'larda bile reassign'ı bloke ediyordu.
        # F20: T (urgency) ile çarp → T=0 yeni task'ta tam stabilite, T=1 acil task'ta sıfır.
        # Bu Instab'ı düşürür AMA deadline yaklaşan task'ların hızlı reassign'ını engellemez.
        if not (self.FAILURE_STICKY_DISABLE and self._failure_active):
            prev_robot_for_task = self._prev_robot_for_task
            prev_rid = prev_robot_for_task.get(task.task_id)
            if self.URGENCY_STICKY_DECAY and task.deadline > 0:
                t_raw = min(1.0, max(0.0, (current_time - task.activation_time) / task.deadline))
                decay = (1.0 - t_raw) ** 2  # T=0:1.0, T=0.5:0.25, T=1:0.0
                sticky = self.STICKY_BONUS * decay
                penalty = self.REASSIGN_PENALTY * decay
            else:
                sticky = self.STICKY_BONUS
                penalty = self.REASSIGN_PENALTY
            # PAKET A.2: deadline_p yüksekse sticky'yi yarıla — dp'de yanlış
            # başlangıç ataması kilitlenmesin (CR/Instab regresyonunu çöz).
            # self._last_context allocate() içinde set edilir.
            if self._failure_active is False:
                _ctx = getattr(self, '_last_context', None)
                if (_ctx is not None and _ctx.context_vector
                        and len(_ctx.context_vector) > 3
                        and float(_ctx.context_vector[3]) > 0.50):
                    sticky *= self.STICKY_DP_SCALE
                    penalty *= self.STICKY_DP_SCALE
            if prev_rid == robot.robot_id:
                cost -= sticky
            elif prev_rid is not None:
                cost += penalty

        # M3 ek: mutlak kapasiteyi aşıyorsa ek penalty
        if len(q) >= cap:
            cost += self.OVER_CAP_PENALTY

        # Priority bonus: öncelikli görevleri biraz daha çekici yap
        cost *= (1.0 - 0.10 * (task.priority - 1))

        return cost

    @measure
    def allocate(self, robots: list, tasks: list, current_time: float,
                 context: Optional[EcosystemContext] = None) -> AllocationResult:
        # PAKET A.2: context'i _cost'a iletmek için instance attribute'a sakla.
        self._last_context = context
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

        # ════════════════════════════════════════════════════════════════
        # FAZ 0 (v3.5): Stuck-Robot Pre-emption + Orphan-Pool Build (F19)
        # ════════════════════════════════════════════════════════════════
        # nav_state ∈ {2,3} robotların queue'larını orphan_pool'a aktar.
        # 3PHA bu pool'u FAZ 2'de (recovery) işler.
        orphan_pool: list = []
        if self.STUCK_PREEMPT_ENABLED:
            for r in robots:
                if getattr(r, 'navigation_state', 0) in (2, 3) and queues.get(r.robot_id):
                    for tid in queues[r.robot_id]:
                        t = task_map.get(tid)
                        if t is not None and not getattr(t, 'completed', False):
                            orphan_pool.append(t)
                        # Commit'i temizle: stuck robot artık owner değil
                        self._commit_map.pop(tid, None)
                    queues[r.robot_id] = []

        # M25: cache prev_robot_for_task (cost hesaplamasında kullanılır)
        self._prev_robot_for_task = {}
        for rid, q in self._prev_queues.items():
            for tid in q:
                self._prev_robot_for_task[tid] = rid

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

        # F4: Rescue mode hesaplama — her unassigned task için min(arrival) bul.
        # Eğer min > deadline ise hiçbir robot zamanında varamayacak → rescue.
        # Bu task'larda F1 sıkı reddi devre dışı kalır (Compl korunur).
        # ÖNCELİK FİLTRESİ: sadece priority >= RESCUE_MIN_PRIORITY görevler rescue.
        # Düşük priority görevler bırakılır → DVR patlamasını sınırlar.
        self._rescue_tasks = set()
        if self.CONDITIONAL_GATING and avail:
            for task in unassigned:
                if task.deadline <= 0:
                    continue
                if task.priority < self.RESCUE_MIN_PRIORITY:
                    continue
                min_arr = float('inf')
                for r in avail:
                    a = self._arrival_time(r, task, task_map, queues[r.robot_id], current_time)
                    if a < min_arr:
                        min_arr = a
                if min_arr > task.deadline:
                    self._rescue_tasks.add(task.task_id)

        # F8: Event-triggered no-op. State fingerprint hesapla. Önceki çağrıyla
        # aynı ise hiçbir şey değişmemiş demektir → mevcut kuyrukları döndür
        # (gereksiz reassignment'ı önler, Instability ↓).
        # PAKET A.2: deadline guard — herhangi bir görevin deadline'ı yakınsa
        # (< 30 s) NOOP atlama, taze allocate yap. dp'de CR düşüşünü önler.
        deadline_critical = any(
            (t.deadline > 0 and (t.deadline - current_time) < 30.0)
            for t in tasks if t.active and not t.completed
        )
        if (self.EVENT_TRIGGERED_NOOP and self._prev_queues
                and not self._failure_active and not deadline_critical):
            state_key = (
                frozenset(t.task_id for t in unassigned),
                tuple((r.robot_id, r.available, len(queues[r.robot_id])) for r in robots),
                frozenset(self._rescue_tasks),
            )
            if state_key == self._prev_state_key:
                # State değişmedi → mevcut kuyrukları olduğu gibi döndür
                return AllocationResult(queues=dict(self._prev_queues),
                                        latency_ms=0,
                                        communication_footprint_bytes=84)
            self._prev_state_key = state_key

        if not unassigned or not avail:
            ordered = {}
            for r in robots:
                q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
                ordered[r.robot_id] = [t.task_id for t in self._order_queue(r, q_tasks, current_time)]
            self._prev_queues = {rid: list(q) for rid, q in ordered.items()}
            return AllocationResult(queues=ordered, latency_ms=0,
                                    communication_footprint_bytes=84)

        # RADİKAL PAKET (JTSC): robot_cap=1 zorla — her robotta tek görev, kuyruk
        # blokajı yok. Robot tamamlayınca allocator hemen yeni atama yapar.
        soft_cap = self.JTSC_QUEUE_CAP
        robot_cap: dict = {r.robot_id: self.JTSC_QUEUE_CAP for r in avail}

        # Ortalama kuyruk uzunluğu (M3)
        avail_ids = [r.robot_id for r in avail]
        mean_q = sum(len(queues[rid]) for rid in avail_ids) / max(1, len(avail_ids))

        # ════════════════════════════════════════════════════════════════
        # v4 EDPS — Ecosystem-Driven Paradigm Selection
        # ════════════════════════════════════════════════════════════════
        # Hormone (dominance) argmax → 7 paradigmadan birini seç.
        # AHE'nin ekosistemi (cooperation/suppression dynamics) hangi MRTA
        # paradigmasının şu an en uygun olduğuna karar verir. Bu, mevcut
        # weighted-cost bipartite'in ötesinde STRÜKTÜREL adaptasyondur.
        if self.EDPS_ENABLED:
            paradigm_idx = self._select_paradigm(context)
            self._last_paradigm = paradigm_idx
            if paradigm_idx == 0:    # H_SPATIAL → spatial_greedy
                queues = self._paradigm_spatial_greedy(
                    unassigned, avail, queues, task_map, current_time, robot_cap)
            elif paradigm_idx == 1:  # H_CRIT → priority_first
                queues = self._paradigm_priority_first(
                    unassigned, avail, queues, task_map, current_time,
                    weights, mean_q, soft_cap, robot_cap)
            elif paradigm_idx == 3:  # H_RES → load_balance
                queues = self._paradigm_load_balance(
                    unassigned, avail, queues, task_map, current_time, robot_cap)
            elif paradigm_idx == 4:  # H_ENERGY → battery_gated
                queues = self._paradigm_battery_gated(
                    unassigned, avail, queues, task_map, current_time, robot_cap)
            elif paradigm_idx == 5:  # H_STAB → commit_once
                queues = self._paradigm_commit_once(
                    unassigned, avail, queues, task_map, current_time, robot_cap)
            elif paradigm_idx == 6:  # H_RECOV → orphan_first
                queues = self._paradigm_orphan_first(
                    unassigned, avail, orphan_pool, queues, task_map,
                    current_time, weights, mean_q, soft_cap, robot_cap)
            else:                    # H_TEMP (2) veya default → 3PHA (EDF + multi-phase)
                paradigm_idx = 2  # bayrakla 3PHA'ya in
                # 3PHA tam pipeline aşağıda çalışır (else branch'i)
            # Non-3PHA paradigmalar tamamlandı → swap_refine + ordering'e atla
            if paradigm_idx != 2:
                # M24 swap_refine atla (commit_once için zararlı), ordering uygula
                ordered_paradigm = {}
                for r in robots:
                    q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
                    ordered_paradigm[r.robot_id] = [t.task_id for t in
                                                     self._order_queue(r, q_tasks, current_time)]
                # commit_map maintain
                for rid, q in ordered_paradigm.items():
                    for tid in q:
                        if tid not in self._commit_map:
                            self._commit_map[tid] = rid
                active_tids = {t.task_id for t in tasks if not getattr(t, 'completed', False)}
                self._commit_map = {tid: rid for tid, rid in self._commit_map.items()
                                    if tid in active_tids}
                self._prev_queues = {rid: list(q) for rid, q in ordered_paradigm.items()}
                return AllocationResult(queues=ordered_paradigm, latency_ms=0,
                                        communication_footprint_bytes=84)

        # ════════════════════════════════════════════════════════════════
        # 3PHA — Methodolojik kök fark: çok-fazlı hiyerarşik allocation
        # (H_TEMP paradigm veya EDPS kapalı için default path)
        # ════════════════════════════════════════════════════════════════
        if self.THREE_PHASE_ENABLED:
            # ─── FAZ 1: Urgent-Greedy (BiG-style hızlı atama) ───
            # deadline−now < URGENT_HORIZON tasklar bipartite'ı beklemez,
            # nearest-feasible robota commit. Delay/DVR'ı BiG seviyesine indirir.
            urgent = []
            normal = []
            for t in unassigned:
                if t.deadline > 0 and t.priority >= self.URGENT_MIN_PRIORITY:
                    time_to_deadline = t.deadline - current_time
                    # arrival tahminini overshoot etmemek için aggressive eşik
                    if time_to_deadline < self.URGENT_HORIZON:
                        urgent.append(t)
                        continue
                normal.append(t)
            if urgent:
                urgent_leftover = self._phase1_urgent_greedy(
                    urgent, avail, queues, task_map, current_time, robot_cap)
                # Atanmayan urgent → normal pool'a (Faz 3 deneyecek)
                normal.extend(urgent_leftover)

            # ─── FAZ 2: Recovery-Bipartite (orphan-focused) ───
            # FAZ 0'da toplanan orphan'lar + failure_active modda kalan unassigned
            # → healthy robotlarda LSA + W_RECOVERY ile dağıt.
            if orphan_pool or (self._failure_active and self.RESCUE_OVERFLOW_QUEUE):
                healthy = [r for r in avail
                           if getattr(r, 'navigation_state', 0) not in (2, 3)]
                if healthy and orphan_pool:
                    orphan_leftover = self._phase2_recovery_bipartite(
                        orphan_pool, healthy, queues, task_map,
                        current_time, weights, mean_q, soft_cap, robot_cap)
                    # Atanamayan orphan'lar → normal pool'a
                    normal.extend(orphan_leftover)

            # Kalan task'lar Faz 3'e (mevcut optimal-bipartite) devredilir
            unassigned = normal

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
                    ordered[r.robot_id] = [t.task_id for t in
                                           self._order_queue(r, q_tasks, current_time)]
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
            # F5 (Last-Resort): cost>=1e5 olsa bile en az yüklü robota zorla ata
            # (Compl güvenlik ağı). Rescue olmayan görevler zaten F1 ile elenir.
            if self.OVERFLOW_ENABLED:
                leftover = [t for t in unassigned if t.task_id not in used_task_ids]
                for task in leftover:
                    best_r, best_c = None, float('inf')
                    for r in avail:
                        c = self._cost(r, task, task_map, queues, weights,
                                       current_time, mean_q, soft_cap, robot_cap)
                        if c < best_c:
                            best_c, best_r = c, r.robot_id
                    # F5: hiçbir fizibil çift yok ama LAST_RESORT açıksa en az
                    # yüklü robota zorla ata — görev geç bile olsa tamamlanır
                    if best_c >= 1e5:
                        if self.LAST_RESORT_OVERFLOW:
                            target = min(avail, key=lambda r: len(queues[r.robot_id]))
                            queues[target.robot_id].append(task.task_id)
                            used_task_ids.add(task.task_id)
                        continue
                    if best_r is None:  # tüm robotlar dolu → en az yüklü
                        target = min(avail, key=lambda r: len(queues[r.robot_id]))
                        best_r = target.robot_id
                    queues[best_r].append(task.task_id)
                    used_task_ids.add(task.task_id)
        else:
            # Greedy sequential — scipy yok fallback (no_bipartite ablasyonu da bu yolu kullanır)
            # F5: c>=1e5 olan görevleri LAST_RESORT açıksa zorla ata
            for task in unassigned:
                best_r, best_c = None, float('inf')
                for r in avail:
                    c = self._cost(r, task, task_map, queues, weights,
                                   current_time, mean_q, soft_cap, robot_cap)
                    if c < best_c and c < 1e5:
                        best_c = c; best_r = r.robot_id
                if best_r is None and self.OVERFLOW_ENABLED:
                    if best_c < 1e5 or self.LAST_RESORT_OVERFLOW:
                        target = min(avail, key=lambda r: len(queues[r.robot_id]))
                        best_r = target.robot_id
                if best_r:
                    queues[best_r].append(task.task_id)

        # M24: Local swap refinement — deadline overrun'ı düşür
        if self.SWAP_REFINE_ENABLED and _HAS_SCIPY:
            queues = self._swap_refine(queues, task_map, avail, current_time)

        # FAZ 4 (M26): Commit-map'i güncelle (RETRO-FORCE YOK — Instab patlatıyordu).
        # Yeni atamaları kaydet; tamamlanmış task'ların commit'lerini temizle.
        # Sonraki çağrıda FAZ 1 + M25 sticky bonus bu commit'lere öncelik verir.
        if self.THREE_PHASE_ENABLED:
            for rid, q in queues.items():
                for tid in q:
                    if tid not in self._commit_map:
                        self._commit_map[tid] = rid
            active_tids = {t.task_id for t in tasks if not getattr(t, 'completed', False)}
            self._commit_map = {tid: rid for tid, rid in self._commit_map.items()
                                if tid in active_tids}

        # M18 + M21: failure-aware ordering — arızada cheapest, normalde EDF
        ordered = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            ordered[r.robot_id] = [t.task_id for t in
                                   self._order_queue(r, q_tasks, current_time)]

        # M4: bir sonraki tur için önceki kuyrukları sakla
        self._prev_queues = {rid: list(q) for rid, q in ordered.items()}

        return AllocationResult(queues=ordered, latency_ms=0,
                                communication_footprint_bytes=84)


# Ablasyon varyantları kaldırıldı (paper kapsamı dışı — ana_method §1.3).
