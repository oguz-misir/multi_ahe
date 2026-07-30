#!/usr/bin/env python3
"""Recompute failure-recovery time without the survivorship discount.

``experiment_runner_node`` maxes recovery over *completed* failure-related
tasks only::

    recovery_times = [self._task_completion_wall.get(tid, ...)
                      for tid in self._failure_related_tasks
                      if tid in self._task_completion_wall]

A method that never finishes an orphaned task therefore drops it from the max
and posts a lower recovery time.  The same file already rejects exactly this
bias for ``average_task_delay`` -- unfinished tasks are censored at the
experiment horizon so that "dropping is penalised, not rewarded" -- and for the
deadline violation rate.  Recovery time is the one metric left out.

This script recomputes both variants from the event logs, so every existing
campaign gains the censored figure without being re-run.  It writes an extra
column rather than replacing anything: the published number stays auditable.

Reconstruction fidelity: the ``as_coded`` column reproduces the runner's own
``failure_recovery_time`` to within 0.5 s on 190 of 191 canonical runs.  The
single outlier (exp_robot_failure_consensus_dbta_r10t50_seed04) has a task
whose completion event was logged after the summary snapshot was taken -- an
end-of-experiment race in the runner, not a reconstruction error.

Usage:
    python3 scripts/recompute_recovery_censored.py                # report
    python3 scripts/recompute_recovery_censored.py --write        # + CSV
"""

from __future__ import annotations

import argparse
import os

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(REPO, 'results', 'processed')


def _failure_related(events: pd.DataFrame, inject_t: float, failed_robot: str,
                     completions: dict) -> set:
    """Mirror the runner's ``_failure_related_tasks``.

    Two sources: work the failed robot still held when it went down (the last
    assignment before injection wins, already-completed work excluded), plus
    every task that later reported ``task_failed``.
    """
    assigned = events[(events.event == 'assigned')
                      & (events.timestamp_s <= inject_t)].sort_values('timestamp_s')
    holder = dict(zip(assigned.task_id, assigned.robot_id))   # last write wins
    held = {tid for tid, rid in holder.items()
            if rid == failed_robot
            and not (tid in completions and completions[tid] <= inject_t)}
    return held | set(events[events.event == 'failed'].task_id)


def recompute(processed_dir: str = PROCESSED) -> pd.DataFrame:
    events = pd.read_csv(os.path.join(processed_dir, 'all_task_events.csv'))
    allocs = pd.read_csv(os.path.join(processed_dir, 'all_allocation_events.csv'))
    summary = pd.read_csv(os.path.join(processed_dir, 'all_summary.csv')).set_index(
        'experiment_id')

    injections = allocs[allocs.event_type == 'robot_failure'][
        ['experiment_id', 'timestamp_s', 'robot_id']].groupby('experiment_id').first()

    rows = []
    for exp_id, injection in injections.iterrows():
        if exp_id not in summary.index:
            continue
        meta = summary.loc[exp_id]
        ev = events[events.experiment_id == exp_id]
        if ev.empty:
            continue
        completions = dict(zip(ev[ev.event == 'completed'].task_id,
                               ev[ev.event == 'completed'].timestamp_s))
        inject_t = injection.timestamp_s
        horizon = ev.timestamp_s.min() + meta.makespan_s
        if horizon <= inject_t:
            continue
        related = _failure_related(ev, inject_t, injection.robot_id, completions)
        if not related:
            continue
        finished = [completions[t] for t in related if t in completions]
        rows.append({
            'experiment_id': exp_id,
            'scenario': meta.scenario,
            'strategy': meta.strategy,
            'robot_count': meta.robot_count,
            'seed': meta.seed,
            'related_tasks': len(related),
            'unfinished': sum(1 for t in related if t not in completions),
            'recovery_as_coded': (max(finished) - inject_t) if finished else 0.0,
            'recovery_censored': max(completions.get(t, horizon)
                                     for t in related) - inject_t,
            'recovery_reported': meta.failure_recovery_time,
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--processed-dir', default=PROCESSED)
    parser.add_argument('--write', action='store_true',
                        help='write recovery_censored.csv next to the inputs')
    args = parser.parse_args()

    df = recompute(args.processed_dir)
    if df.empty:
        print('no runs with a logged robot_failure injection')
        return

    err = (df.recovery_as_coded - df.recovery_reported).abs()
    print(f'reconstructed {len(df)} runs; '
          f'{(err < 0.5).sum()}/{len(df)} reproduce the runner within 0.5 s')

    for scenario in sorted(df.scenario.unique()):
        for robots in sorted(df.robot_count.unique()):
            cell = df[(df.scenario == scenario) & (df.robot_count == robots)]
            if cell.empty:
                continue
            table = cell.groupby('strategy').agg(
                runs=('related_tasks', 'size'),
                unfinished=('unfinished', 'mean'),
                as_coded=('recovery_as_coded', 'mean'),
                censored=('recovery_censored', 'mean'))
            table['rank_as_coded'] = table.as_coded.rank().astype(int)
            table['rank_censored'] = table.censored.rank().astype(int)
            print(f'\n=== {scenario} @ {robots} robots ===')
            print(table.round(1).to_string())

    if args.write:
        out = os.path.join(args.processed_dir, 'recovery_censored.csv')
        df.to_csv(out, index=False)
        print(f'\nwrote {out}  ({len(df)} rows)')


if __name__ == '__main__':
    main()
