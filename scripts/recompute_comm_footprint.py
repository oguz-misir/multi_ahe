#!/usr/bin/env python3
"""Recompute AHE-MRTA's per-event communication footprint on the baselines' terms.

Why this exists
---------------
Every baseline logs an *analytic* payload estimate derived from what its protocol
actually puts on the wire at that event:

    BiG-MRTA        len(robots) * len(tasks) * 4      bid matrix, float32
    Consensus-DBTA  bids_sent * 16                    bid records
    RoSTAM-EA       generations * robots * tasks * 8  chromosome broadcast

``AHEMRTAv3Allocator`` instead returned the **constant 84**, which is the 3-robot
value of a different variant's weight-vector formula (``len(robots) * 7 * 4``)
frozen into the class.  It therefore did not describe AHE's own protocol and did
not move with fleet size, while every baseline number did -- so the published
cross-method comparison was not like-for-like.

AHE publishes one ordered task queue per robot.  The matching analytic payload is

    sum_r ( HEADER_BYTES + ID_BYTES * |queue_r| )

with an 8-byte per-robot header (robot-id hash + queue length) and a 4-byte task
id, the same field-size convention the baseline estimates use.

The campaign logs do not contain queue contents, so the queues are reconstructed
from the task-event stream: at an allocation event ``t`` robot ``r`` owns every
task whose most recent ``assigned`` event at or before ``t`` names ``r`` and that
has not yet completed or failed.  This reproduces the quantity the allocator
would have logged, without re-running any experiment.

Output: ``results/processed/ahe_comm_footprint.csv`` -- one row per AHE
allocation event, consumed by ``plot_results.py`` through
``comm_override.apply_comm_override``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

HEADER_BYTES = 8      # robot-id hash (u32) + queue length (u32)
ID_BYTES = 4          # task-id hash (u32) per queue entry
PROPOSED = 'ahe_mrta_v3'


def _queue_sizes_at(events: pd.DataFrame, stamps: pd.Series) -> list[int]:
    """Total queued task count over all robots at each stamp, in stamp order."""
    ev = events.sort_values('timestamp_s')
    assigned = ev[ev['event'] == 'assigned'][['timestamp_s', 'task_id', 'robot_id']]
    closed = ev[ev['event'].isin(('completed', 'failed'))][['timestamp_s', 'task_id']]
    close_at = closed.groupby('task_id')['timestamp_s'].min()

    out = []
    for t in stamps:
        owner: dict[str, str] = {}
        for _, row in assigned[assigned['timestamp_s'] <= t].iterrows():
            owner[row['task_id']] = row['robot_id']
        live = [tid for tid in owner
                if not (tid in close_at.index and close_at[tid] <= t)]
        out.append(len(live))
    return out


def recompute(processed_dir: Path) -> pd.DataFrame:
    comm = pd.read_csv(processed_dir / 'all_communication.csv')
    tasks = pd.read_csv(processed_dir / 'all_task_events.csv')

    ahe = comm[comm['strategy'] == PROPOSED].copy()
    rows = []
    for exp_id, grp in ahe.groupby('experiment_id'):
        ev = tasks[tasks['experiment_id'] == exp_id]
        grp = grp.sort_values('timestamp_s')
        queued = _queue_sizes_at(ev, grp['timestamp_s'])
        n_robots = int(grp['robot_count'].iloc[0])
        payload = [n_robots * HEADER_BYTES + ID_BYTES * q for q in queued]
        out = grp[['experiment_id', 'scenario', 'strategy', 'robot_count',
                   'target_count', 'seed', 'timestamp_s', 'alloc_num']].copy()
        out['queued_tasks'] = queued
        out['footprint_bytes'] = payload
        rows.append(out)

    return pd.concat(rows, ignore_index=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--processed-dir', default='results/processed', type=Path)
    args = ap.parse_args()

    df = recompute(args.processed_dir)
    dest = args.processed_dir / 'ahe_comm_footprint.csv'
    df.to_csv(dest, index=False)

    print(f'{len(df)} AHE allocation events rewritten -> {dest}')
    per_scale = df.groupby('robot_count')['footprint_bytes'].agg(['mean', 'min', 'max'])
    print('\nAHE-MRTA per-event payload by fleet size (bytes):')
    print(per_scale.round(1).to_string())
    print(f'\n(previous logged value was the constant 84 at every scale)')


if __name__ == '__main__':
    main()
