#!/usr/bin/env python3
"""Figure 7(b): executed ground-truth trajectories, four methods, one seed.

WHY THIS EXISTS
---------------
The published figure was a hand-assembled 2x2 montage with no build script,
and it was drawn from ``results/raw/gazebo/`` -- the pre-F58 campaign that
``results/README.md`` marks HISTORICAL and that the paper no longer reports.
The panel is qualitative, so no number was wrong, but a reviewer asking "which
run is this?" would have got "one we no longer report".

This script rebuilds the same figure from the canonical closed-loop campaign:

  AHE-MRTA*       raw/gazebo_ablation/full/exp_mixed_stress_ahe_mrta_v3_r5t25_seed01
  the baselines   raw/gazebo_ablation/baselines-n20/exp_mixed_stress_<m>_r5t25_seed01

which are exactly the runs behind the 5r/25t mixed-stress cells of
Table~\\ref{tab:main_comparison}.

FRAME HANDLING
--------------
``robot_state_timeseries.csv`` logs poses in each robot's **odom** frame, i.e.
relative to its spawn point, not in the map frame.  This was established by
anchoring traces to the absolute coordinates of the tasks each robot visited:
the resulting per-robot offsets reproduce ``compute_spawn_positions(5)`` to
within 0.2 m in every run.  Map pose is therefore ``odom pose + spawn``.

The spawn offset is applied from ``compute_spawn_positions`` -- the same single
source of truth the scenario-map figure uses -- rather than from the anchoring
estimate, because a robot that never leaves its spawn visits no task and so has
no anchoring estimate.  (Consensus-DBTA's robot 1 is exactly that case in this
seed.)  The anchoring estimate is still computed and printed as a cross-check;
a disagreement above the tolerance means the log frame changed and this script
must be revisited.

No reported metric is affected by the frame: travel distance is
translation-invariant, and the allocator's own belief was corrected separately.

Usage:
    python3 scripts/make_path_grid.py [-o paper/figure/grid_r5t25_mixed_stress.png]
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PGM = ROOT / 'src/m_ahe_nav2_config/maps/obstacle_map.pgm'
RES, ORG = 0.05, (-10.0, -10.0)

ABL = ROOT / 'results/raw/gazebo_ablation'
SEED, SCEN, SCALE = 'seed01', 'mixed_stress', 'r5t25'

# Reading order: top-left, top-right, bottom-left, bottom-right.
PANELS = [
    ('ahe_mrta_v3',    'AHE-MRTA*',      ABL / 'full'),
    ('consensus_dbta', 'Consensus-DBTA', ABL / 'baselines-n20'),
    ('big_mrta',       'BiG-MRTA',       ABL / 'baselines-n20'),
    ('rostam_ea',      'RoSTAM-EA',      ABL / 'baselines-n20'),
]

ROBOT_COLORS = ['#0072B2', '#009E73', '#D55E00', '#CC79A7', '#E69F00']

FS_TITLE = 8.5
FS_TICK = 6.0
FS_LEG = 7.0


def read_pgm(p):
    with open(p, 'rb') as f:
        assert f.readline().strip() == b'P5'
        line = f.readline()
        while line.startswith(b'#'):
            line = f.readline()
        w, h = map(int, line.split())
        int(f.readline())
        return np.frombuffer(f.read(w * h), dtype=np.uint8).reshape(h, w)


def load_rows(run: Path):
    f = run / 'robot_state_timeseries.csv'
    return list(csv.DictReader(open(f))) if f.exists() else []


def load_tasks(run: Path):
    f = run / 'task_positions.csv'
    out = {}
    if not f.exists():
        return out
    for r in csv.DictReader(open(f)):
        try:
            out[r['task_id']] = (float(r['x']), float(r['y']))
        except (KeyError, ValueError):
            pass
    return out


def auto_offset(rows_r, tasks):
    """Translation anchoring a robot's trace to the tasks it actually visited."""
    res, prev = [], ''
    for i, r in enumerate(rows_r):
        tid = (r.get('current_task_id') or '').strip()
        if prev and tid != prev and prev in tasks and i > 0:
            try:
                px, py = float(rows_r[i - 1]['x']), float(rows_r[i - 1]['y'])
                tx, ty = tasks[prev]
                res.append((tx - px, ty - py))
            except (ValueError, KeyError):
                pass
        prev = tid
    if not res:
        return (0.0, 0.0)
    return (statistics.median(o[0] for o in res),
            statistics.median(o[1] for o in res))


def spawn_offsets(robot_ids):
    """Map-frame spawn point per robot id, from the shared placement helper."""
    import sys
    sys.path.insert(0, str(ROOT / 'src/m_ahe_mrta_bringup/launch'))
    from multi_robot_helpers import compute_spawn_positions  # noqa: E402
    pos = compute_spawn_positions(len(robot_ids))
    return {rid: (float(pos[i][0]), float(pos[i][1]))
            for i, rid in enumerate(sorted(robot_ids))}


def trajectories(run: Path):
    """Map-frame traces. Odom poses are shifted by the robot's spawn point."""
    rows = load_rows(run)
    tasks = load_tasks(run)
    byrobot = {}
    for r in rows:
        try:
            float(r['x']), float(r['y'])
        except (KeyError, ValueError):
            continue
        byrobot.setdefault(r['robot_id'], []).append(r)

    spawns = spawn_offsets(list(byrobot))
    traj, check = {}, {}
    for rid, rr in sorted(byrobot.items()):
        ox, oy = spawns[rid]
        pts = [(float(r['x']) + ox, float(r['y']) + oy) for r in rr]
        traj[rid] = pts
        # A robot that never moved carries no frame information: anchoring it
        # returns the coordinates of whatever tasks it was assigned while
        # standing still, which is not an offset estimate.  Gate the
        # cross-check on actual displacement, not on the estimate being zero.
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        span = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
        if span < 0.3:
            check[rid] = None
            continue
        ax_, ay_ = auto_offset([r for r in rows if r['robot_id'] == rid], tasks)
        check[rid] = (math.hypot(ax_ - ox, ay_ - oy)
                      if (ax_, ay_) != (0.0, 0.0) else None)
    return traj, tasks, check


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--out', type=Path,
                    default=ROOT / 'paper/figure/grid_r5t25_mixed_stress.png')
    ap.add_argument('--dpi', type=int, default=400)
    args = ap.parse_args()

    img = read_pgm(PGM)
    h, w = img.shape
    extent = [ORG[0], ORG[0] + w * RES, ORG[1], ORG[1] + h * RES]

    fig, axes = plt.subplots(2, 2, figsize=(4.7, 5.05))
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'pdf.fonttype': 42})

    handles = None
    for ax, (method, label, base) in zip(axes.ravel(), PANELS):
        run = base / f'exp_{SCEN}_{method}_{SCALE}_{SEED}'
        if not run.is_dir():
            raise SystemExit(f'missing canonical run: {run}')
        traj, tasks, check = trajectories(run)
        anchored = [v for v in check.values() if v is not None]
        worst = max(anchored) if anchored else 0.0
        static = [k for k, v in check.items() if v is None]
        if worst > 0.5:
            raise SystemExit(
                f'{run.name}: task-anchored offset disagrees with the spawn '
                f'point by {worst:.2f} m. The log frame changed; revisit this '
                f'script before trusting the figure.')
        print(f'{label:<16} robots={len(traj)}  tasks={len(tasks)}  '
              f'spawn-vs-anchor max {worst:.2f} m'
              + (f'  (never moved: {", ".join(static)})' if static else ''))

        ax.imshow(img, cmap='gray', extent=extent, origin='upper',
                  vmin=0, vmax=255, alpha=0.85, interpolation='nearest')
        if tasks:
            tx, ty = zip(*tasks.values())
            ax.scatter(tx, ty, marker='*', s=26, c='gold', edgecolors='k',
                       linewidths=0.35, zorder=5, label='waypoint')
        for i, (rid, pts) in enumerate(sorted(traj.items())):
            if len(pts) < 2:
                continue
            xs, ys = zip(*pts)
            c = ROBOT_COLORS[i % len(ROBOT_COLORS)]
            ax.plot(xs, ys, '-', color=c, lw=1.0, alpha=0.92, zorder=4,
                    label=f'robot {i + 1}')
            ax.scatter([xs[0]], [ys[0]], marker='s', s=16, color=c,
                       edgecolors='k', linewidths=0.4, zorder=6)
        ax.set_xlim(-10, 10)
        ax.set_ylim(-10, 10)
        ax.set_aspect('equal')
        ax.set_title(label, fontsize=FS_TITLE, fontweight='bold', pad=3)
        ax.tick_params(labelsize=FS_TICK, length=2, pad=1)
        ax.set_xticks([-10, -5, 0, 5, 10])
        ax.set_yticks([-10, -5, 0, 5, 10])
        if handles is None:
            handles, labels = ax.get_legend_handles_labels()

    for ax in axes[0]:
        ax.set_xticklabels([])
    for ax in axes[:, 1]:
        ax.set_yticklabels([])
    for ax in axes[1]:
        ax.set_xlabel('x [m]', fontsize=FS_TICK + 0.5, labelpad=1)
    for ax in axes[:, 0]:
        ax.set_ylabel('y [m]', fontsize=FS_TICK + 0.5, labelpad=1)

    fig.legend(handles, labels, loc='lower center', ncol=6, fontsize=FS_LEG,
               frameon=False, handlelength=1.4, columnspacing=1.1,
               bbox_to_anchor=(0.5, -0.005))
    fig.tight_layout(rect=(0, 0.045, 1, 1), h_pad=0.7, w_pad=0.6)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=args.dpi, facecolor='white')
    print(f'\n[OK] {args.out}')


if __name__ == '__main__':
    main()
