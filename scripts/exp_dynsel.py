#!/usr/bin/env python3
"""TEMPORARY experiment: dynamic (online-learned) paradigm selection vs the
static F50 context-keyed map.

Reviewer concern: the per-context rule choices (and the V/threshold constants)
are set by the designer. This tests whether letting the system LEARN the rule
online — instead of hand-/data-fixing it — helps. Three outcomes:
  * dynamic converges to the static map and ties it -> static choice validated;
  * dynamic beats static -> adopt dynamic;
  * dynamic worse (exploration cost / noise) -> static justified.

Mechanism (clean per-context epsilon-greedy bandit, WITHIN-episode online):
  - context bucket b in {failure (c4>.05), deadline (c3>.5), default}
  - per bucket keep Q[b][rule] (running mean reward) over candidate rules
  - reward = net task completions since last decision (completions inferred
    from tasks that left the previously published queues and are now closed),
    attributed to the (bucket, rule) chosen last cycle
  - selection: epsilon-greedy; Q initialised NEUTRAL by default (no hand-set
    prior to justify) so convergence to F50_MAP is independent evidence. Set
    PRIOR_MODE='f50' to test prior-sensitivity. No cross-episode memory.

Monkeypatch only — canonical allocator untouched (this is provisional).
Run AFTER the Gazebo campaign finishes (no parallel CPU load).
"""
import sys, random
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
EPS = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
R, T = 5, 25
CANDS = [0, 1, 2, 3, 5, 6]   # spatial, priority, edf, load_bal, commit, orphan
# F50 data-derived map (for reference / optional prior / convergence target):
F50_MAP = {'deadline': 3, 'failure': 0, 'default': 2}
# PRIOR_MODE: 'neutral' = agnostic start (no hand-set prior to justify; if the
# learner converges to F50_MAP from neutral, that is INDEPENDENT evidence the
# rule choices are data-emergent, not designer-imposed). 'f50' = start from the
# data-derived map (tests prior-sensitivity: same convergence => prior-robust).
PRIOR_MODE = sys.argv[3] if len(sys.argv) > 3 else 'neutral'
METRICS = {'alloc_fitness': ('Fit', True), 'completion_rate': ('CR', True),
           'avg_delay': ('Delay', False), 'deadline_violation_rate': ('DVR', False),
           'workload_balance': ('WLBal', True)}

_orig_sel = AV.AHEMRTAv3Allocator._select_paradigm


def _bucket(c):
    if len(c) >= 5:
        if float(c[3]) > 0.50:
            return 'deadline'
        if float(c[4]) > 0.05:
            return 'failure'
    return 'default'


def dyn_sel(self, context):
    # lazy per-instance bandit state
    if not hasattr(self, '_bandit'):
        if PRIOR_MODE == 'f50':
            self._bandit = {b: {r: (5.0 if r == F50_MAP[b] else 0.0) for r in CANDS}
                            for b in F50_MAP}      # start from data-derived map
            self._bandit_n = {b: {r: (1 if r == F50_MAP[b] else 0) for r in CANDS}
                              for b in F50_MAP}
        else:                                       # neutral: no preference
            self._bandit = {b: {r: 0.0 for r in CANDS} for b in F50_MAP}
            self._bandit_n = {b: {r: 0 for r in CANDS} for b in F50_MAP}
        self._bandit_rng = random.Random(12345)
        self._last_bucket = None
        self._last_rule = None
        self._last_completed = 0
    c = context.context_vector if (context and context.context_vector) else []
    # --- reward attribution for the PREVIOUS decision -----------------------
    comp = getattr(self, '_obs_completed', 0)
    if self._last_bucket is not None:
        reward = comp - self._last_completed     # net new completions since last
        b, r = self._last_bucket, self._last_rule
        n = self._bandit_n[b][r] + 1
        self._bandit_n[b][r] = n
        self._bandit[b][r] += (reward - self._bandit[b][r]) / n
    self._last_completed = comp
    # --- epsilon-greedy selection for THIS decision ------------------------
    b = _bucket(c)
    if self._bandit_rng.random() < EPS:
        rule = self._bandit_rng.choice(CANDS)
    else:
        rule = max(CANDS, key=lambda rr: self._bandit[b][rr])
    self._last_bucket, self._last_rule = b, rule
    self._last_paradigm = rule
    return rule


def collect(dynamic):
    AV.AHEMRTAv3Allocator._select_paradigm = (dyn_sel if dynamic else _orig_sel)
    reg = _make_allocators()
    data = {sc: {m: {k: [] for k in METRICS} for m in ['ahe_mrta_v3'] + BASE}
            for sc in SCEN}
    conv = {sc: [] for sc in SCEN}   # converged rule per bucket (diagnostic)
    try:
        for sc in SCEN:
            for seed in range(1, SEEDS + 1):
                for m in ['ahe_mrta_v3'] + BASE:
                    eco = EcosystemSimulator() if _needs_eco(m) else None
                    alloc = reg[m]()
                    # feed completion count into the bandit via a hook
                    if dynamic and m == 'ahe_mrta_v3':
                        _wrap_completion_hook(alloc)
                    r = run_simulation(alloc, sc, seed, n_robots=R, n_tasks=T, eco=eco)
                    for k in METRICS:
                        data[sc][m][k].append(r[k])
                    if dynamic and m == 'ahe_mrta_v3' and hasattr(alloc, '_bandit'):
                        conv[sc].append({b: max(CANDS, key=lambda rr: alloc._bandit[b][rr])
                                         for b in F50_MAP})
    finally:
        AV.AHEMRTAv3Allocator._select_paradigm = _orig_sel
    return data, conv


def _wrap_completion_hook(alloc):
    """Make alloc._obs_completed track cumulative completions inferred from
    tasks leaving the published queues (proxy reward signal)."""
    orig_alloc = alloc.allocate
    alloc._obs_completed = 0
    alloc._seen = set()

    def allocate_hook(robots, tasks, current_time, context=None):
        open_ids = {t.task_id for t in tasks}
        for rid, q in getattr(alloc, '_prev_queues', {}).items():
            for tid in q:
                if tid not in open_ids and tid not in alloc._seen:
                    alloc._seen.add(tid)
                    alloc._obs_completed += 1
        return orig_alloc(robots, tasks, current_time, context)
    alloc.allocate = allocate_hook


def main():
    print(f"DYNAMIC vs STATIC selector  seeds={SEEDS}  eps={EPS}")
    dataD, conv = collect(True)
    dataS, _ = collect(False)
    for label, data in [('STATIC(F50)', dataS), ('DYNAMIC(bandit)', dataD)]:
        print(f"\n== {label} ==")
        worse = []
        for sc in SCEN:
            cells = []
            for k, (lbl, hib) in METRICS.items():
                av = np.array(data[sc]['ahe_mrta_v3'][k])
                sigw = False
                for b in BASE:
                    bv = np.array(data[sc][b][k])
                    better = (av.mean() > bv.mean()) if hib else (av.mean() < bv.mean())
                    try:
                        _, p = mannwhitneyu(av, bv, alternative='two-sided')
                    except ValueError:
                        p = 1.0
                    if p < 0.05 and not better:
                        sigw = True
                cells.append(f"{lbl}={av.mean():.3f}{'x' if sigw else '.'}")
                if sigw:
                    worse.append(f"{sc[:2]}/{lbl}")
            print(f"  {sc:<18} " + "  ".join(cells))
        print(f"  -> sig-worse: {worse if worse else 'NONE'}")
    # convergence diagnostic
    print("\nDYNAMIC converged rule per bucket (mode over seeds):")
    rn = {0: 'spatial', 1: 'priority', 2: 'edf', 3: 'load_bal', 5: 'commit', 6: 'orphan'}
    for sc in SCEN:
        from collections import Counter
        agg = {b: Counter(d[b] for d in conv[sc]) for b in F50_MAP}
        s = "  ".join(f"{b}:{rn[agg[b].most_common(1)[0][0]]}" for b in F50_MAP if agg[b])
        print(f"  {sc:<18} {s}   (F50 prior: failure:spatial deadline:load_bal default:edf)")


if __name__ == '__main__':
    main()
