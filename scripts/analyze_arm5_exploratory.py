#!/usr/bin/env python3
"""Exploratory analysis of the fifth ablation arm: fixed spatial-greedy.

WHY THIS IS A SEPARATE SCRIPT, NOT AN ENTRY IN analyze_ablation.py's ARMS
------------------------------------------------------------------------
analyze_ablation.py implements paper/PREREGISTRATION.md exactly and was
committed before the campaign produced data.  That is its entire evidential
value.  Adding 'fixed-spatial' to its ARMS list would silently:

  * change the common-seed intersection (5 arms instead of 4), so the
    registered numbers could move because of an arm that was never registered;
  * change the Bonferroni family in the primary scenario from 3 comparisons
    to 4, altering the corrected p-values of the registered arms; and
  * make the analysis code no longer predate the data it analyses.

So the registered four-arm analysis stays untouched and this arm is reported
separately, as scripts/_campaigns/run_ablation_arm5.sh says it must be.  The statistics helpers
are imported from analyze_ablation.py rather than copied, so the two analyses
cannot drift apart in how they compute a delta or pair a seed.

WHAT THIS ARM IS FOR
--------------------
Re-running the proxy ablation on the corrected scenario definitions put fixed
spatial-greedy AHEAD of the full selector (0.348 vs 0.329 mean fitness).  The
registered arms covered only the two paradigms the overrides target (H_TEMP,
H_RECOV), not the one the dominance fallback returns in 99.9% of the states it
decides -- which is exactly spatial-greedy.  If the closed loop agrees with the
proxy here, the paper's portfolio claim needs narrowing again; if it does not,
the claim survives a real challenge.

Reported as exploratory: raw p-values, with the correction it *would* need
shown alongside, and no promotion into the registered family.

Usage:
    python3 scripts/analyze_arm5_exploratory.py
    python3 scripts/analyze_arm5_exploratory.py --root results/raw/gazebo_ablation
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_ablation as reg  # noqa: E402

ARM = 'fixed-spatial'
FULL = 'full'
SCENARIOS = ['deadline_pressure', 'robot_failure', 'mixed_stress']
PRIMARY_SCENARIO = 'deadline_pressure'
EXPECTED_PER_SCENARIO = 20

# The registered fixed arms, for context: is fixed-spatial merely another bad
# fixed paradigm, or is it the one that competes with the selector?
CONTEXT_ARMS = ['fixed-EDF', 'fixed-orphan', 'no-override']

METRICS = [reg.PRIMARY] + reg.SECONDARY + reg.DESCRIPTIVE


def arm_counts(data, arm):
    return {sc: len(data.get(arm, {}).get(sc, {})) for sc in SCENARIOS}


def pair_full_vs(data, scenario, other_arm, metric, higher_better):
    """One paired comparison, `full` against `other_arm`, on common seeds."""
    arms = [FULL, other_arm]
    rows, seeds, dropped = reg.compare(data, scenario, metric, higher_better,
                                       arms, n_tests=1)
    return (rows[0] if rows else None), seeds, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='results/raw/gazebo_ablation')
    ap.add_argument('--out', default='results/arm5_exploratory.txt',
                    help='also write this report to a file, so the prose in '
                         'sec:gazebo-ablation can be checked against it')
    args = ap.parse_args()

    data = reg.load_runs(args.root)
    lines = []

    def say(s=''):
        print(s)
        lines.append(s)

    say('=' * 78)
    say('EXPLORATORY FIFTH ARM -- fixed spatial-greedy (AHE_FORCE_PARADIGM=0)')
    say('NOT pre-registered. Not part of the primary Bonferroni family.')
    say('=' * 78)

    counts = arm_counts(data, ARM)
    total = sum(counts.values())
    say(f'\nRuns with DONE, by scenario (target {EXPECTED_PER_SCENARIO} each):')
    for sc in SCENARIOS:
        flag = '' if counts[sc] >= EXPECTED_PER_SCENARIO else '   <-- INCOMPLETE'
        say(f'  {sc:<20}{counts[sc]:>4}{flag}')
    say(f'  {"TOTAL":<20}{total:>4} / {EXPECTED_PER_SCENARIO * len(SCENARIOS)}')

    if counts[PRIMARY_SCENARIO] < EXPECTED_PER_SCENARIO:
        say('')
        say('*** INTERIM: the primary-endpoint scenario is not complete.')
        say('*** deadline_pressure runs LAST in scripts/_campaigns/run_ablation_arm5.sh, so this')
        say('*** is expected until the very end of the campaign. Numbers below')
        say('*** are provisional; do not write them into the paper yet.')

    # ── Primary comparison ───────────────────────────────────────────────────
    metric, label, hib = reg.PRIMARY
    say(f'\n{"=" * 78}')
    say(f'PRIMARY COMPARISON -- {label}')
    say('=' * 78)
    for sc in SCENARIOS:
        r, seeds, dropped = pair_full_vs(data, sc, ARM, metric, hib)
        tag = ' (primary endpoint scenario)' if sc == PRIMARY_SCENARIO else ' (descriptive)'
        say(f'\n{sc}{tag}   n={len(seeds)} common seeds')
        if dropped:
            say(f'  seeds dropped to keep the pairing: {dropped}')
        if r is None:
            say('  not enough paired data yet')
            continue
        # Exploratory: report raw p, and what a 3-test correction would do to it,
        # without folding this arm into the registered family.
        p_if_corrected = min(1.0, r['p'] * 3)
        direction = 'full ahead' if (r['full'] > r['other']) == hib else f'{ARM} ahead'
        say(f'  full          {r["full"]:.3f}')
        say(f'  {ARM:<14}{r["other"]:.3f}')
        say(f'  difference    {r["full"] - r["other"]:+.3f}  ({direction})')
        say(f'  raw p         {r["p"]:.4f}'
            f'   [x3 would be {p_if_corrected:.4f}]')
        say(f"  Cliff's delta {r['delta']:+.3f}  "
            f"95% CI [{r['ci'][0]:+.2f},{r['ci'][1]:+.2f}]  "
            f'({reg.magnitude(r["delta"])})')
        if r['p'] >= reg.ALPHA:
            say('  -> no separation even before correction')
        elif p_if_corrected >= reg.ALPHA:
            say('  -> separates raw, would NOT survive a 3-test correction')
        else:
            say('  -> separates, and would survive a 3-test correction')

    # ── Where this arm sits among the others ─────────────────────────────────
    say(f'\n{"=" * 78}')
    say('CONTEXT -- all arms on the primary endpoint, same common seeds')
    say('=' * 78)
    for sc in SCENARIOS:
        arms = [FULL, ARM] + CONTEXT_ARMS
        seeds, _ = reg.common_seeds(data, sc, arms)
        if not seeds:
            say(f'\n{sc}: no seeds common to all five arms yet')
            continue
        say(f'\n{sc}  (n={len(seeds)} common to all five arms)')
        for a in arms:
            vals = [data[a][sc][('ahe_mrta_v3', s)].get(metric) for s in seeds]
            vals = [v for v in vals if isinstance(v, float)]
            if vals:
                say(f'  {a:<16}{sum(vals) / len(vals):.3f}')

    # ── Secondary/descriptive metrics, full vs this arm ──────────────────────
    say(f'\n{"=" * 78}')
    say(f'OTHER METRICS -- full vs {ARM} (descriptive, untested)')
    say('=' * 78)
    for sc in SCENARIOS:
        seeds, _ = reg.common_seeds(data, sc, [FULL, ARM])
        if not seeds:
            continue
        say(f'\n{sc}  (n={len(seeds)})')
        say(f'  {"metric":<30}{"full":>10}{ARM:>16}')
        for m, lab, _ in METRICS:
            cells = []
            for a in (FULL, ARM):
                vals = [data[a][sc][('ahe_mrta_v3', s)].get(m) for s in seeds]
                vals = [v for v in vals if isinstance(v, float)]
                cells.append(f'{sum(vals) / len(vals):.3f}' if vals else '--')
            say(f'  {lab:<30}{cells[0]:>10}{cells[1]:>16}')

    say('')
    say('=' * 78)
    say('HOW TO REPORT THIS')
    say('=' * 78)
    say('sec:ablation already forward-references this arm in BOTH languages:')
    say('  "Fixed spatial-greedy, which this table promotes, was not part of')
    say('   the registered design; Section~\\ref{sec:gazebo-ablation} reports')
    say('   it separately as an exploratory arm."')
    say('That reference is currently dangling. Add a short paragraph at the end')
    say('of sec:gazebo-ablation, in EN and TR, that:')
    say('  - names it exploratory and says why it was added (proxy put it ahead)')
    say('  - gives the primary-endpoint numbers above')
    say('  - says plainly which way it went, including if it went against us')
    say('  - does NOT enter tab:gazebo-ablation, which is the registered four')
    say('Then recompile both PDFs.')

    if args.out:
        os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
        with open(args.out, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        print(f'\n[OK]  report -> {args.out}')


if __name__ == '__main__':
    main()
