#!/usr/bin/env python3
"""Replay the EDPS selector over logged ecosystem states.

Regenerates the numbers quoted in limitation (viii): which branch of the
cascade actually decides, how often each paradigm is selected, and how much the
Lotka--Volterra dominance tier changes relative to a constant.

The replay mirrors ``AHEMRTAv3Allocator._select_paradigm_raw``::

    failure_rate > 0.05          -> 4  H_RECOV   orphan_first
    deadline_pressure > 0.50     -> 2  H_TEMP    edf_strict
    near-uniform dominance       -> 2  H_TEMP    (default)
    otherwise                    -> argmax(D[:5])

Two caveats, both stated in the paper:
  * These are ecosystem-manager samples (~2 s cadence), not the exact
    allocation instants.  They are the selector's input distribution.
  * ``_select_paradigm`` adds dwell hysteresis on top, which returns the
    *previous* paradigm while a switch is pending.  It can only make switching
    rarer -- it can never introduce a paradigm the raw selector did not emit --
    so the reachability conclusion is unaffected.

Usage:
    python3 scripts/audit_paradigm_selection.py
"""

from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV = os.path.join(REPO, 'results', 'processed', 'all_ecosystem_metrics.csv')

PARADIGMS = {
    0: 'H_SPATIAL  spatial_greedy',
    1: 'H_CRIT     priority_first',
    2: 'H_TEMP     edf_strict',
    3: 'H_STAB     commit_once',
    4: 'H_RECOV    orphan_first',
}


def replay(df: pd.DataFrame):
    """Return (selected paradigm, deciding branch) for every logged state."""
    dominance = df[['d_0', 'd_1', 'd_2', 'd_3', 'd_4']].to_numpy(float)
    failure = df.context_failure_rate.to_numpy(float)
    deadline = df.context_deadline.to_numpy(float)

    selected = np.full(len(df), -1)
    branch = np.empty(len(df), dtype=object)

    override_fail = failure > 0.05
    selected[override_fail] = 4
    branch[override_fail] = 'override:failure'

    override_dl = (selected < 0) & (deadline > 0.50)
    selected[override_dl] = 2
    branch[override_dl] = 'override:deadline'

    rest = selected < 0
    flat = rest & ((dominance.max(1) - dominance.min(1)) < 1e-4)
    selected[flat] = 2
    branch[flat] = 'fallback:near-uniform'

    dyn = rest & ~flat
    selected[dyn] = dominance[dyn].argmax(1)
    branch[dyn] = 'fallback:dominance'
    return selected, branch, dyn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', default=DEFAULT_CSV)
    parser.add_argument('--strategy', default='ahe_mrta_v3')
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    df = df[df.strategy == args.strategy].reset_index(drop=True)
    if df.empty:
        print(f'no rows for strategy={args.strategy}')
        return

    selected, branch, dyn = replay(df)
    total = len(df)
    print(f'{total} logged ecosystem states across '
          f'{df.experiment_id.nunique()} {args.strategy} runs\n')

    print('paradigm selected')
    for idx, name in PARADIGMS.items():
        n = int((selected == idx).sum())
        print(f'  {idx}  {name:<28}{n:>6}  {100 * n / total:6.2f}%')

    print('\ndeciding branch')
    for name, n in pd.Series(branch).value_counts().items():
        print(f'  {name:<24}{n:>6}  {100 * n / total:6.2f}%')

    if dyn.any():
        sub = selected[dyn]
        top = np.bincount(sub, minlength=5).argmax()
        share = 100 * (sub == top).mean()
        print(f'\nwhen the dominance tier runs ({dyn.sum()} states) it returns '
              f'{PARADIGMS[top].split()[1]} in {share:.1f}% of cases')

    constant = selected.copy()
    constant[dyn] = 0                      # dominance tier -> fixed spatial_greedy
    changed = int((constant != selected).sum())
    print(f'\ncounterfactual: replacing the dominance tier with a constant '
          f'changes {changed} of {total} states ({100 * changed / total:.3f}%)')

    print('\nparadigm share (%) by scenario')
    table = pd.crosstab(df.scenario, selected, normalize='index').mul(100).round(1)
    table.columns = [PARADIGMS[c].split()[1] for c in table.columns]
    print(table.to_string())


if __name__ == '__main__':
    main()
