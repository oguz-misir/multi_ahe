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


TEX_HEADER = r"""% GENERATED by scripts/analyze_ablation.py -- do not edit by hand.
% Regenerate after any change to results/raw/gazebo_ablation/.
\begin{table}[t]
\centering
\caption{Matched closed-loop ablation at the primary 5-robot / 25-task scale:
four arms over NSEEDS common seeds per scenario, pre-registered before the campaign
(\texttt{paper/PREREGISTRATION.md}). Primary endpoint is effective on-time
completion $\mathrm{CR}\times(1-\mathrm{DVR})$ under \textit{deadline\_pressure};
$p$ is a paired Wilcoxon signed-rank test against \emph{full}, Bonferroni-corrected
within the scenario family, and $\delta$ is Cliff's delta with a bootstrap 95\% CI.
The other two scenarios are descriptive.}
\label{tab:gazebo-ablation}
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{l cccc}
\toprule
& \textbf{full} & \textbf{no-override} & \textbf{fixed-EDF} & \textbf{fixed-orphan} \\
\midrule
"""


TEX_HEADER_TR = r"""% ÜRETİLEN dosya: scripts/analyze_ablation.py -- elle düzenleme.
% results/raw/gazebo_ablation/ değişince yeniden üret.
\begin{table}[t]
\centering
\caption{Eşleşmiş kapalı-çevrim ablasyonu, birincil 5-robot / 25-görev ölçeği:
senaryo başına NSEEDS ortak tohumda dört kol; kampanyadan önce kayıt altına
alındı (\texttt{paper/PREREGISTRATION.md}). Birincil uç nokta, zamanında-etkin
tamamlama $\mathrm{CR}\times(1-\mathrm{DVR})$ (\textit{deadline\_pressure}
senaryosunda); $p$, \emph{full}'e karşı eşli Wilcoxon işaretli-sıra testidir ve
senaryo ailesi içinde Bonferroni ile düzeltilmiştir; $\delta$ bootstrap \%95
GA'lı Cliff deltasıdır. Diğer iki senaryo betimleyicidir.}
\label{tab:gazebo-ablation}
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{l cccc}
\toprule
& \textbf{full} & \textbf{no-override} & \textbf{fixed-EDF} & \textbf{fixed-orphan} \\
\midrule
"""

# EN label -> TR label, so both tables come from one pass over the data.
TR = {'primary endpoint': 'birincil uç nokta', 'descriptive': 'betimleyici',
      'effective on-time': 'zamanında-etkin tamamlama',
      'completion rate': 'tamamlama oranı',
      'recovery time (s)': 'toparlanma süresi (s)',
      "Cliff's $\\delta$ vs full": "Cliff $\\delta$ (full'e karşı)"}


def write_tex(data, out_path):
    """Emit tab:gazebo-ablation so the paper cannot drift from the analysis."""
    seeds, _ = common_seeds(data, 'deadline_pressure', ARMS)
    lines = [TEX_HEADER.replace('NSEEDS', str(len(seeds)))]

    def row(label, scenario, metric, fmt='%.3f'):
        cells = []
        for arm in ARMS:
            vals = [data[arm][scenario][('ahe_mrta_v3', s)].get(metric)
                    for s in common_seeds(data, scenario, ARMS)[0]]
            vals = [v for v in vals if isinstance(v, float)]
            cells.append(fmt % (sum(vals) / len(vals)) if vals else '--')
        return f"{label} & " + " & ".join(cells) + r" \\" + "\n"

    lines.append(r"\multicolumn{5}{l}{\textit{deadline\_pressure} -- primary endpoint} \\" + "\n")
    lines.append(row(r"\quad effective on-time", 'deadline_pressure', 'effective_on_time'))
    rows, _, _ = compare(data, 'deadline_pressure', 'effective_on_time', True, ARMS, 3)
    pcell = ['--']
    dcell = ['--']
    for r in rows:
        pcell.append('$<$0.005' if r['p_bonf'] < 0.005 else ('%.3f' % r['p_bonf']
                     if r['p_bonf'] < 1 else '1.000'))
        dcell.append('%+.2f' % r['delta'])
    lines.append(r"\quad $p$ (Bonferroni) & " + " & ".join(pcell) + r" \\" + "\n")
    lines.append(r"\quad Cliff's $\delta$ vs full & " + " & ".join(dcell) + r" \\" + "\n")
    lines.append(r"\midrule" + "\n")
    lines.append(r"\multicolumn{5}{l}{\textit{robot\_failure} -- descriptive} \\" + "\n")
    lines.append(row(r"\quad effective on-time", 'robot_failure', 'effective_on_time'))
    lines.append(row(r"\quad completion rate", 'robot_failure', 'task_completion_rate'))
    lines.append(row(r"\quad recovery time (s)", 'robot_failure',
                     'failure_recovery_time_censored', '%.1f'))
    lines.append(r"\midrule" + "\n")
    lines.append(r"\multicolumn{5}{l}{\textit{mixed\_stress} -- descriptive} \\" + "\n")
    lines.append(row(r"\quad effective on-time", 'mixed_stress', 'effective_on_time'))
    lines.append(r"\bottomrule" + "\n" + r"\end{tabular}" + "\n" + r"\end{table}" + "\n")
    body = "".join(lines)
    with open(out_path, 'w') as f:
        f.write(body)
    print(f"\n[OK]  LaTeX table -> {out_path}")

    # The Turkish paper must not drift from the English one, so it is emitted
    # here rather than translated by hand after the fact.
    tr_body = body.split(r'\midrule', 1)[1]
    for en, tr in TR.items():
        tr_body = tr_body.replace(en, tr)
    tr_path = out_path.replace('.tex', '_tr.tex')
    with open(tr_path, 'w') as f:
        f.write(TEX_HEADER_TR.replace('NSEEDS', str(len(seeds))) + tr_body)
    print(f"[OK]  LaTeX table -> {tr_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='results/raw/gazebo_ablation')
    ap.add_argument('--tex', default='paper/table/gazebo_ablation.tex',
                    help='write the LaTeX results table here')
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

    if not missing and args.tex:
        write_tex(data, args.tex)


if __name__ == '__main__':
    main()
