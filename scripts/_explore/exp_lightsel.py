#!/usr/bin/env python3
"""Search a lightweight context-keyed selector vs the full EDPS (Plane A).

A candidate selector is a static map from the context signals to a paradigm
index, evaluated WITHOUT the ecosystem dominance dynamics:
    if c3 (deadline) > 0.5 -> DEADLINE_RULE
    elif c4 (failure) > 0.05 -> FAILURE_RULE
    else -> DEFAULT_RULE
We monkeypatch _select_paradigm to this map (canonical code untouched) and
report, per scenario, AHE's Fit/CR/Delay/DVR/WLBal next to the best baseline,
plus a verdict (is AHE >= every baseline, statistically, via Mann-Whitney).
The winning map is the one that is best-or-tied on all metrics in all scenarios.
"""
import sys
import numpy as np
from scipy.stats import mannwhitneyu
sys.path.insert(0, 'scripts')
import simulate_and_tune as S
from simulate_and_tune import (run_simulation, EcosystemSimulator,
                               _make_allocators, _needs_eco)
from m_ahe_task_allocator.baselines import ahe_variants as AV

SCEN = ['robot_failure', 'mixed_stress', 'deadline_pressure']
BASE = ['big_mrta', 'rostam_ea', 'consensus_dbta']
SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 60
R, T = 5, 25
PIDX = {'spatial': 0, 'priority': 1, 'edf': 2, 'load_bal': 3, 'commit': 5, 'orphan': 6}
METRICS = {'alloc_fitness': ('Fit', True), 'completion_rate': ('CR', True),
           'avg_delay': ('Delay', False), 'deadline_violation_rate': ('DVR', False),
           'workload_balance': ('WLBal', True)}

_orig_sel = AV.AHEMRTAv3Allocator._select_paradigm

# candidate maps: (failure_rule, deadline_rule, default_rule)
# Focus: deadline-bucket variants (failure=spatial fixed) to clean dp-WLBal.
MAPS = {
    'spatial/loadbal':   ('spatial',  'load_bal', 'edf'),   # current F50
    'spatial/priority':  ('spatial',  'priority', 'edf'),
    'spatial/commit':    ('spatial',  'commit',   'edf'),
    'spatial/spatial':   ('spatial',  'spatial',  'edf'),
}


def make_sel(fr, dr, df):
    fi, di, dfi = PIDX[fr], PIDX[dr], PIDX[df]

    def sel(self, context):
        c = context.context_vector if (context and context.context_vector) else []
        if len(c) >= 5:
            if float(c[3]) > 0.5:   # deadline pressure
                return di
            if float(c[4]) > 0.05:  # failure
                return fi
        return dfi
    return sel


def collect(mapspec):
    if mapspec is None:
        AV.AHEMRTAv3Allocator._select_paradigm = _orig_sel
    else:
        AV.AHEMRTAv3Allocator._select_paradigm = make_sel(*mapspec)
    reg = _make_allocators()
    data = {sc: {m: {k: [] for k in METRICS} for m in ['ahe_mrta_v3'] + BASE}
            for sc in SCEN}
    try:
        for sc in SCEN:
            for seed in range(1, SEEDS + 1):
                for m in ['ahe_mrta_v3'] + BASE:
                    eco = EcosystemSimulator() if _needs_eco(m) else None
                    r = run_simulation(reg[m](), sc, seed, n_robots=R, n_tasks=T, eco=eco)
                    for k in METRICS:
                        data[sc][m][k].append(r[k])
    finally:
        AV.AHEMRTAv3Allocator._select_paradigm = _orig_sel
    return data


def main():
    print(f"LIGHTWEIGHT SELECTOR SEARCH  seeds={SEEDS}  (vs best baseline; "
          f"x=sig worse p<.05)")
    for name, spec in MAPS.items():
        data = collect(spec)
        worse = []
        print(f"\n== {name} ==")
        for sc in SCEN:
            cells = []
            for k, (lbl, hib) in METRICS.items():
                av = np.array(data[sc]['ahe_mrta_v3'][k])
                sig_w = False
                for b in BASE:
                    bv = np.array(data[sc][b][k])
                    better = (av.mean() > bv.mean()) if hib else (av.mean() < bv.mean())
                    try:
                        _, p = mannwhitneyu(av, bv, alternative='two-sided')
                    except ValueError:
                        p = 1.0
                    if p < 0.05 and not better:
                        sig_w = True
                flag = 'x' if sig_w else '.'
                if sig_w:
                    worse.append(f"{sc[:2]}/{lbl}")
                cells.append(f"{lbl}={av.mean():.3f}{flag}")
            print(f"  {sc:<18} " + "  ".join(cells))
        print(f"  -> sig-worse cells: {worse if worse else 'NONE (best-or-tied all)'}")


if __name__ == '__main__':
    main()
