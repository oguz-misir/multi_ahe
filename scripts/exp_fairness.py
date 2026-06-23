#!/usr/bin/env python3
"""Test a completion-fairness lever for the rf-WLBal gap (Plane A, sim).

Mechanism (self-contained, Gazebo-deployable): the allocator tracks per-robot
CUMULATIVE completions (inferred from tasks that left last cycle's published
queues and are no longer open), and adds a tie-break penalty in _cost for
robots whose cumulative completions exceed the fleet mean. Unlike the queue-
length load term (which was flat, it could not see throughput), this targets
the diagnosed cause: one productive robot completing a long chain.

Sweeps FAIR_W and reports WLBal / CR / Delay / DVR for all three scenarios so
any regression on the other metrics/scenarios is caught.  Monkeypatch only —
canonical allocator untouched until a value is chosen.
"""
import sys
import numpy as np
sys.path.insert(0, 'scripts')
import simulate_and_tune as S
from m_ahe_task_allocator.baselines import ahe_variants as AV

SCEN = ['robot_failure', 'mixed_stress', 'deadline_pressure']
BASE = ['big_mrta', 'rostam_ea', 'consensus_dbta']
SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 60
WS = [float(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else [0.05, 0.15, 0.3, 0.6]
R, T = 5, 25

_orig_alloc = AV.AHEMRTAv3Allocator.allocate
_orig_cost = AV.AHEMRTAv3Allocator._cost
FAIR_W = 0.0


def _alloc(self, robots, tasks, current_time, context=None):
    if not hasattr(self, '_rcomp'):
        self._rcomp, self._counted = {}, set()
    open_ids = {t.task_id for t in tasks}
    for rid, q in getattr(self, '_prev_queues', {}).items():
        for tid in q:
            if tid not in open_ids and tid not in self._counted:
                self._counted.add(tid)
                self._rcomp[rid] = self._rcomp.get(rid, 0) + 1
    for r in robots:
        self._rcomp.setdefault(r.robot_id, 0)
    return _orig_alloc(self, robots, tasks, current_time, context)


def _cost(self, robot, task, task_map, queues, weights, current_time,
          mean_q, cap, robot_cap):
    c = _orig_cost(self, robot, task, task_map, queues, weights, current_time,
                   mean_q, cap, robot_cap)
    if c >= 1e5 or FAIR_W <= 0:
        return c
    rc = getattr(self, '_rcomp', None)
    if rc:
        vals = list(rc.values())
        mean_rc = sum(vals) / max(1, len(vals))
        excess = max(0.0, rc.get(robot.robot_id, 0) - mean_rc)
        c += FAIR_W * excess
    return c


def bench(w):
    global FAIR_W
    FAIR_W = w
    AV.AHEMRTAv3Allocator.allocate = _alloc
    AV.AHEMRTAv3Allocator._cost = _cost
    try:
        out = {}
        for sc in SCEN:
            out[sc] = S.benchmark(['ahe_mrta_v3'] + BASE, sc, SEEDS,
                                  n_robots=R, n_tasks=T)
    finally:
        AV.AHEMRTAv3Allocator.allocate = _orig_alloc
        AV.AHEMRTAv3Allocator._cost = _orig_cost
    return out


def main():
    base = bench(0.0)
    print(f"seeds={SEEDS}  metrics: WLBal(^) CR(^) Delay(v) DVR(v)  "
          f"[best-baseline WLBal in brackets]")
    for w in [0.0] + WS:
        out = bench(w)
        tag = 'BASELINE' if w == 0.0 else f'FAIR_W={w}'
        print(f"\n== {tag} ==")
        for sc in SCEN:
            a = out[sc]['ahe_mrta_v3']
            bw = max(out[sc][b]['workload_balance'] for b in BASE)
            print(f"  {sc:<18} WLBal={a['workload_balance']:.3f}[{bw:.3f}]  "
                  f"CR={a['completion_rate']:.3f}  "
                  f"Delay={a['avg_delay']:.1f}  DVR={a['deadline_violation_rate']:.3f}")


if __name__ == '__main__':
    main()
