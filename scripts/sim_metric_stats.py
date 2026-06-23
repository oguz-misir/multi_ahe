#!/usr/bin/env python3
"""Plane-A (sim, Nav2-independent) per-metric SIGNIFICANCE probe.

For each scenario and metric, collects per-seed values for AHE and every
baseline, then reports AHE mean±std vs each baseline with Mann-Whitney p and
Cliff's delta. Verdict per (metric,scenario): is AHE significantly WORSE than
any baseline, or best-or-statistically-tied?

This decides whether the chosen target ("AHE best-or-tied on every metric") is
already met, vs needs algorithmic work — WITHOUT touching sim_fitness.csv.
"""
import sys
import numpy as np
from scipy.stats import mannwhitneyu
sys.path.insert(0, 'scripts')
import simulate_and_tune as S

SCENARIOS = ['robot_failure', 'mixed_stress', 'deadline_pressure']
AHE = 'ahe_mrta_v3'
BASE = ['big_mrta', 'rostam_ea', 'consensus_dbta']
# metric -> (label, higher_is_better)
METRICS = {
    'alloc_fitness':           ('Fit',   True),
    'avg_delay':               ('Delay', False),
    'deadline_violation_rate': ('DVR',   False),
    'workload_balance':        ('WLBal', True),
}
SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
ROBOTS, TASKS = 5, 25


def cliffs_delta(a, b):
    a, b = np.asarray(a), np.asarray(b)
    gt = sum((x > b).sum() for x in a)
    lt = sum((x < b).sum() for x in a)
    return (gt - lt) / (len(a) * len(b))


def collect():
    from simulate_and_tune import run_simulation, EcosystemSimulator, _make_allocators, _needs_eco
    reg = _make_allocators()
    # data[scen][method][metric] = list over seeds
    data = {sc: {m: {k: [] for k in METRICS} for m in [AHE] + BASE} for sc in SCENARIOS}
    for sc in SCENARIOS:
        for seed in range(1, SEEDS + 1):
            for m in [AHE] + BASE:
                eco = EcosystemSimulator() if _needs_eco(m) else None
                r = run_simulation(reg[m](), sc, seed, n_robots=ROBOTS,
                                   n_tasks=TASKS, eco=eco)
                for k in METRICS:
                    data[sc][m][k].append(r[k])
    return data


def main():
    data = collect()
    print(f"\nPlane-A significance probe  |  seeds={SEEDS}  {ROBOTS}r/{TASKS}t")
    worst_cases = []
    for sc in SCENARIOS:
        print(f"\n{'='*92}\n  {sc}\n{'='*92}")
        print(f"  {'Metric':<7}{'AHE(mean±std)':>18}  {'vs baseline':<14}"
              f"{'base(mean)':>11}{'p':>9}{'δ':>8}  verdict")
        for k, (lbl, hib) in METRICS.items():
            ahe_v = np.array(data[sc][AHE][k])
            ahe_m, ahe_s = ahe_v.mean(), ahe_v.std()
            sig_worse = []
            lines = []
            for b in BASE:
                bv = np.array(data[sc][b][k])
                try:
                    _, p = mannwhitneyu(ahe_v, bv, alternative='two-sided')
                except ValueError:
                    p = 1.0
                d = cliffs_delta(ahe_v, bv)
                # AHE better? higher_is_better → mean higher; else lower
                better = (ahe_m > bv.mean()) if hib else (ahe_m < bv.mean())
                worse_sig = (p < 0.05) and (not better)
                if worse_sig:
                    sig_worse.append(b)
                lines.append((b, bv.mean(), p, d, worse_sig))
            verdict = ('WORSE: ' + ','.join(s[:4] for s in sig_worse)) if sig_worse \
                else 'best-or-tied'
            if sig_worse:
                worst_cases.append((sc, lbl, sig_worse))
            print(f"  {lbl:<7}{ahe_m:>10.3f}±{ahe_s:<6.3f}")
            for (b, bm, p, d, ws) in lines:
                flag = '  <-- sig worse' if ws else ''
                print(f"           {'':16}{b:<14}{bm:>11.3f}{p:>9.3f}{d:>8.2f}{flag}")
            print(f"           => {verdict}")
    print(f"\n{'#'*92}")
    if worst_cases:
        print("  AHE SIGNIFICANTLY WORSE (p<0.05) on:")
        for sc, lbl, bs in worst_cases:
            print(f"    - {sc} / {lbl}  vs {','.join(bs)}")
    else:
        print("  AHE is BEST-OR-STATISTICALLY-TIED on ALL metrics in ALL scenarios.")
    print('#'*92)


if __name__ == '__main__':
    main()
