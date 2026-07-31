#!/usr/bin/env python3
"""Pre-registered analysis of the matched Gazebo ablation (B5).

Implements paper/PREREGISTRATION.md exactly.  Written and committed before the
campaign finished, so the analysis choices cannot have been shaped by the
results -- that is the point of the pre-registration, and it only holds if the
code predates the data.

Primary endpoint:   effective on-time completion, CR x (1 - DVR), under
                    deadline_pressure; `full` against each other arm.
Secondary:          completion rate and censored recovery time under
                    robot_failure.
Test:               paired Wilcoxon signed-rank over common seeds, Cliff's
                    delta with a bootstrap 95% CI, Bonferroni inside each
                    scenario family.

Seeds missing from any arm are dropped from every arm so the pairing holds,
and the dropped seeds are printed -- the pre-registration requires them in the
deviations log.

Usage:
    python3 scripts/analyze_ablation.py [--root results/raw/gazebo_ablation]
"""

import argparse
import csv
import glob
import os
import random
import sys
from collections import defaultdict

try:
    from scipy.stats import wilcoxon
except ImportError:
    sys.exit("scipy is required: pip install scipy")

ARMS = ['full', 'no-override', 'fixed-EDF', 'fixed-orphan']
BASELINE_ARM = 'baselines-n20'
ALPHA = 0.05

# (column, label, higher_is_better) -- names are the summary.csv headers.
PRIMARY = ('effective_on_time', 'Effective on-time (CR x (1-DVR))', True)
SECONDARY = [('task_completion_rate', 'Completion rate', True),
             ('failure_recovery_time_censored', 'Recovery time (censored, s)', False)]
DESCRIPTIVE = [('average_task_delay', 'Avg task delay (s)', False),
               ('allocation_instability', 'Alloc. instability', False),
               ('replanning_frequency', 'Replanning freq.', False),
               ('workload_balance_active', 'Workload balance (active)', True),
               ('mean_decision_latency_ms', 'Decision latency (ms)', False)]


def load_runs(root):
    """arm -> scenario -> seed -> {metric: value}, from every DONE run."""
    data = defaultdict(lambda: defaultdict(dict))
    for path in glob.glob(os.path.join(root, '*', '*', 'summary.csv')):
        run_dir = os.path.dirname(path)
        if not os.path.exists(os.path.join(run_dir, 'DONE')):
            continue                      # never analyse a run without DONE
        arm = os.path.basename(os.path.dirname(run_dir))
        with open(path) as f:
            rows = list(csv.DictReader(f))
        if not rows:
            continue
        r = rows[0]
        rec = {}
        for k, v in r.items():
            try:
                rec[k] = float(v)
            except (TypeError, ValueError):
                rec[k] = v
        cr = rec.get('task_completion_rate')
        dvr = rec.get('deadline_violation_rate')
        if isinstance(cr, float) and isinstance(dvr, float):
            rec['effective_on_time'] = cr * (1.0 - dvr)
        key = (r['strategy'], int(float(r['seed'])))
        data[arm][r['scenario']][key] = rec
    return data


def common_seeds(data, scenario, arms, strategy='ahe_mrta_v3'):
    """Seeds present in every arm, plus the ones dropped to get there."""
    per_arm = []
    for a in arms:
        per_arm.append({s for (st, s) in data.get(a, {}).get(scenario, {})
                        if st == strategy})
    if not per_arm:
        return [], []
    keep = set.intersection(*per_arm)
    dropped = set.union(*per_arm) - keep
    return sorted(keep), sorted(dropped)


def cliffs_delta(x, y, n_boot=5000, seed=12345):
    """Cliff's delta of x over y, with a bootstrap 95% CI."""
    def _d(a, b):
        gt = sum(1 for i in a for j in b if i > j)
        lt = sum(1 for i in a for j in b if i < j)
        return (gt - lt) / float(len(a) * len(b)) if a and b else float('nan')
    d = _d(x, y)
    rng = random.Random(seed)
    boots = []
    n = len(x)
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        boots.append(_d([x[i] for i in idx], [y[i] for i in idx]))
    boots.sort()
    lo = boots[int(0.025 * n_boot)]
    hi = boots[int(0.975 * n_boot) - 1]
    return d, lo, hi


def magnitude(d):
    a = abs(d)
    return ('negligible' if a < 0.147 else 'small' if a < 0.33
            else 'medium' if a < 0.474 else 'large')


def compare(data, scenario, metric, higher_better, arms, n_tests):
    """`full` against each other arm on one metric, Bonferroni over n_tests."""
    seeds, dropped = common_seeds(data, scenario, arms)
    rows = []
    if len(seeds) < 3:
        return rows, seeds, dropped
    base = [data['full'][scenario][('ahe_mrta_v3', s)].get(metric) for s in seeds]
    for arm in arms[1:]:
        other = [data[arm][scenario][('ahe_mrta_v3', s)].get(metric) for s in seeds]
        pairs = [(a, b) for a, b in zip(base, other)
                 if isinstance(a, float) and isinstance(b, float)]
        if len(pairs) < 3:
            continue
        a_vals = [p[0] for p in pairs]
        b_vals = [p[1] for p in pairs]
        if all(a == b for a, b in pairs):
            p = 1.0                       # identical arms: Wilcoxon undefined
        else:
            p = wilcoxon(a_vals, b_vals).pvalue
        d, lo, hi = cliffs_delta(a_vals, b_vals)
        mean_a = sum(a_vals) / len(a_vals)
        mean_b = sum(b_vals) / len(b_vals)
        better = (mean_a > mean_b) == higher_better
        rows.append({'arm': arm, 'n': len(pairs), 'full': mean_a, 'other': mean_b,
                     'p': p, 'p_bonf': min(1.0, p * n_tests), 'delta': d,
                     'ci': (lo, hi), 'favours_full': better,
                     'significant': p * n_tests < ALPHA})
    return rows, seeds, dropped


def print_family(title, scenario, metrics, data, n_tests):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")
    for metric, label, hib in metrics:
        rows, seeds, dropped = compare(data, scenario, metric, hib, ARMS, n_tests)
        print(f"\n{label}   [{scenario}]   n={len(seeds)} common seeds"
              f"   alpha={ALPHA}/{n_tests}={ALPHA / n_tests:.4f}")
        if dropped:
            print(f"  dropped seeds (missing in >=1 arm): {dropped}")
        if not rows:
            print("  not enough paired data yet")
            continue
        print(f"  {'arm':<14}{'full':>9}{'arm':>9}{'p':>9}{'p_bonf':>9}"
              f"{'delta':>8}  {'95% CI':<18}verdict")
        for r in rows:
            verdict = ('full better' if r['significant'] and r['favours_full']
                       else 'arm better' if r['significant']
                       else 'no difference')
            print(f"  {r['arm']:<14}{r['full']:>9.3f}{r['other']:>9.3f}"
                  f"{r['p']:>9.4f}{r['p_bonf']:>9.4f}{r['delta']:>8.3f}  "
                  f"[{r['ci'][0]:+.2f},{r['ci'][1]:+.2f}]{'':<5}"
                  f"{verdict} ({magnitude(r['delta'])})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='results/raw/gazebo_ablation')
    args = ap.parse_args()

    data = load_runs(args.root)
    print(f"\nRuns found under {args.root}:")
    total = 0
    for arm in ARMS + [BASELINE_ARM]:
        n = sum(len(v) for v in data.get(arm, {}).values())
        total += n
        print(f"  {arm:<16}{n:>4}")
    print(f"  {'TOTAL':<16}{total:>4} / 420")

    missing = [a for a in ARMS if sum(len(v) for v in data.get(a, {}).values()) < 60]
    if missing:
        print(f"\n*** INTERIM: arms not yet complete: {', '.join(missing)}.")
        print("*** Pre-registration allows looking at progress, but no arm, seed")
        print("*** count or endpoint may be changed on the basis of what is here.")

    print_family("PRIMARY FAMILY -- deadline_pressure (3 tests, Bonferroni)",
                 'deadline_pressure', [PRIMARY], data, n_tests=3)
    print_family("SECONDARY FAMILY -- robot_failure (6 tests, Bonferroni)",
                 'robot_failure', SECONDARY, data, n_tests=6)

    print(f"\n{'=' * 78}\nDESCRIPTIVE (reported, not tested; no correction)\n{'=' * 78}")
    for scenario in ('deadline_pressure', 'robot_failure', 'mixed_stress'):
        seeds, _ = common_seeds(data, scenario, ARMS)
        if not seeds:
            continue
        print(f"\n{scenario}  (n={len(seeds)})")
        print(f"  {'metric':<28}" + "".join(f"{a:>14}" for a in ARMS))
        for metric, label, _ in [PRIMARY] + SECONDARY + DESCRIPTIVE:
            cells = []
            for arm in ARMS:
                vals = [data[arm][scenario][('ahe_mrta_v3', s)].get(metric)
                        for s in seeds]
                vals = [v for v in vals if isinstance(v, float)]
                cells.append(f"{sum(vals) / len(vals):>14.3f}" if vals
                             else f"{'--':>14}")
            print(f"  {label:<28}" + "".join(cells))


if __name__ == '__main__':
    main()
