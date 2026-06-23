#!/usr/bin/env python3
"""Diagnose robot_failure WLBal gap: AHE vs BiG per-robot completion shape.

Prints, per method, the mean sorted per-robot completion counts (descending),
the failed robot's mean completions, Jain index, and how concentrated the top
robots are. Tells us WHERE AHE's imbalance comes from (failed-robot drag vs
survivor over-concentration), so the fix can be targeted, not blind.
"""
import sys
import numpy as np
sys.path.insert(0, 'scripts')
from simulate_and_tune import (run_simulation, EcosystemSimulator,
                               _make_allocators, _needs_eco)

SCEN = 'robot_failure'
SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 60
R, T = 5, 25
reg = _make_allocators()


def jain(x):
    x = np.asarray(x, float)
    return (x.sum() ** 2) / (len(x) * (x ** 2).sum()) if x.sum() > 0 else 0.0


for m in ['ahe_mrta_v3', 'big_mrta', 'consensus_dbta', 'rostam_ea']:
    sorted_counts = []          # per-seed sorted desc completion counts
    failed_counts = []
    survivor_jain = []
    full_jain = []
    for seed in range(1, SEEDS + 1):
        eco = EcosystemSimulator() if _needs_eco(m) else None
        r = run_simulation(reg[m](), SCEN, seed, n_robots=R, n_tasks=T, eco=eco)
        rc = r['robot_completed']
        frid = r['failed_robot']
        vals = sorted(rc.values(), reverse=True)
        sorted_counts.append(vals)
        if frid is not None:
            failed_counts.append(rc.get(frid, 0))
            surv = [v for k, v in rc.items() if k != frid]
            survivor_jain.append(jain(surv))
        full_jain.append(jain(list(rc.values())))
    mean_sorted = np.mean(sorted_counts, axis=0)
    print(f"{m:<16} full_jain={np.mean(full_jain):.3f}  "
          f"surv_jain={np.mean(survivor_jain):.3f}  "
          f"failed_done={np.mean(failed_counts):.2f}  "
          f"sorted_per_robot=[{', '.join(f'{v:.1f}' for v in mean_sorted)}]")
