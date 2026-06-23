#!/usr/bin/env python3
"""Audit + force AHE paradigms (Plane A, sim) to test the architecture itself.

Two modes:
  audit  : record which paradigm _select_paradigm actually returns, per
           scenario, over many seeds -> usage histogram. Dead rules = a
           "lighter method" opportunity; over-used single rule = EDPS may be
           redundant.
  force  : override _select_paradigm to a FIXED index (bypassing the dynamic
           ecosystem AND the hard context overrides) and measure the full
           metric set per scenario. Reveals each rule's standalone behaviour:
           which rule wins which metric, whether load_balance actually fixes
           WLBal when used, and whether a lighter fixed/subset design matches
           the full EDPS.

Usage:
  python3 scripts/paradigm_audit.py audit [seeds]
  python3 scripts/paradigm_audit.py force [seeds]
"""
import sys
import numpy as np
sys.path.insert(0, 'scripts')
import simulate_and_tune as S
from m_ahe_task_allocator.baselines import ahe_variants as AV

SCEN = ['robot_failure', 'mixed_stress', 'deadline_pressure']
SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 50
R, T = 5, 25
PNAME = {0: 'spatial', 1: 'priority', 2: 'edf/3PHA', 3: 'load_bal',
         4: 'battery', 5: 'commit', 6: 'orphan'}

_orig_sel = AV.AHEMRTAv3Allocator._select_paradigm
_orig_alloc = AV.AHEMRTAv3Allocator.allocate


def run_audit():
    log = {sc: [] for sc in SCEN}
    cur = {'sc': None}

    def sel_log(self, context):
        idx = _orig_sel(self, context)
        log[cur['sc']].append(idx)
        return idx
    AV.AHEMRTAv3Allocator._select_paradigm = sel_log
    try:
        from simulate_and_tune import (run_simulation, EcosystemSimulator)
        for sc in SCEN:
            cur['sc'] = sc
            for seed in range(1, SEEDS + 1):
                run_simulation(AV.AHEMRTAv3Allocator(), sc, seed, n_robots=R,
                               n_tasks=T, eco=EcosystemSimulator())
    finally:
        AV.AHEMRTAv3Allocator._select_paradigm = _orig_sel

    print(f"PARADIGM USAGE (selected idx frequency)  seeds={SEEDS}")
    for sc in SCEN:
        c = np.bincount(log[sc], minlength=7)
        tot = c.sum() or 1
        parts = [f"{PNAME[i]}={100*c[i]/tot:4.1f}%" for i in range(7) if c[i] > 0]
        print(f"  {sc:<18} " + "  ".join(parts))


def run_force(seeds):
    # baseline (full EDPS) + each forced paradigm
    def bench_fixed(fixed_idx):
        if fixed_idx is not None:
            AV.AHEMRTAv3Allocator._select_paradigm = \
                lambda self, ctx, _i=fixed_idx: _i
        try:
            out = {}
            for sc in SCEN:
                out[sc] = S.benchmark(['ahe_mrta_v3'], sc, seeds, n_robots=R,
                                      n_tasks=T)['ahe_mrta_v3']
        finally:
            AV.AHEMRTAv3Allocator._select_paradigm = _orig_sel
        return out

    configs = [('EDPS(full)', None)] + [(PNAME[i], i) for i in [0, 1, 2, 3, 5, 6]]
    print(f"FORCED-PARADIGM metrics  seeds={seeds}  (Fit^ CR^ Delay v DVR v WLBal^)")
    for sc in SCEN:
        print(f"\n== {sc} ==")
        print(f"  {'rule':<12}{'Fit':>7}{'CR':>7}{'Delay':>8}{'DVR':>7}{'WLBal':>7}")
        for name, idx in configs:
            r = bench_fixed(idx)[sc]
            print(f"  {name:<12}{r['alloc_fitness']:>7.3f}{r['completion_rate']:>7.3f}"
                  f"{r['avg_delay']:>8.1f}{r['deadline_violation_rate']:>7.3f}"
                  f"{r['workload_balance']:>7.3f}")


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'audit'
    if mode == 'audit':
        run_audit()
    else:
        run_force(SEEDS)
