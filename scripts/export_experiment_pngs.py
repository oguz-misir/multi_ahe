#!/usr/bin/env python3
"""
Export per-experiment trajectory PNGs.

For each completed experiment directory under results/raw/ (or a supplied path),
reads:
  task_positions.csv   — task target coordinates
  task_events.csv      — activated / completed / failed events
  allocation_events.csv — robot–task assignments
  robot_state_timeseries.csv — robot trajectories
  metadata.yaml        — strategy / scenario / seed

Outputs one PNG per experiment to results/paper_figures/trajectories/
coloured by robot (blue / green / red) with task status overlay.

Separate figures are saved for:
  baseline/   — SW, BiG-MRTA, RoSTAM-EA, AHE-MRTA* (main comparison)
  ablation/   — AHE-MRTA*, AHE-NoER, AHE-NoD, AHE-FC
  all/        — everything else

Usage:
    python3 scripts/export_experiment_pngs.py
    python3 scripts/export_experiment_pngs.py --raw-dir results/raw/gazebo --scenario robot_failure
"""

import argparse
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import yaml

try:
    import pandas as pd
    from PIL import Image as PILImage
    _PIL = True
except ImportError:
    _PIL = False
    import csv

# ── Constants ──────────────────────────────────────────────────────────────────

MAP_YAML = Path(__file__).parent.parent / 'src/m_ahe_nav2_config/maps/obstacle_map.yaml'
MAP_PGM  = Path(__file__).parent.parent / 'src/m_ahe_nav2_config/maps/obstacle_map.pgm'

# Robot start positions (from SDF)
ROBOT_STARTS = {
    'robot_1': (0.0,  0.0),
    'robot_2': (0.0,  2.0),
    'robot_3': (0.0, -2.0),
}

ROBOT_COLOR = {
    'robot_1': '#1e78c8',   # blue
    'robot_2': '#27c84f',   # green
    'robot_3': '#dc3232',   # red
}
ROBOT_LABEL = {
    'robot_1': 'Robot 1',
    'robot_2': 'Robot 2',
    'robot_3': 'Robot 3',
}

STATUS_COLOR = {
    'pending':   '#888888',
    'active':    '#f5c518',
    'assigned':  '#00ccdd',
    'completed': '#22cc44',
    'failed':    '#ee2222',
}

METHOD_LABEL = {
    'greedy_nearest':               'Greedy',
    'deadline_aware':               'EDF',
    'auction_based':                'Auction',
    'static_weighted':              'SW',
    'big_mrta':                     'BiG-MRTA',
    'rostam_ea':                    'RoSTAM-EA',
    'consensus_dbta':               'Cons-DBTA',
    'ahe_no_dominance':             'AHE-NoD',
    'ahe_no_cooperation_suppression': 'AHE-NoCS',
    'ahe_no_event_replanning':      'AHE-NoER',
    'ahe_fixed_context':            'AHE-FC',
    'full_ahe_mrta':                'AHE-MRTA*',
}

BASELINE_METHODS = {'static_weighted', 'big_mrta', 'rostam_ea', 'full_ahe_mrta'}
ABLATION_METHODS = {'full_ahe_mrta', 'ahe_no_event_replanning',
                    'ahe_no_dominance', 'ahe_fixed_context', 'ahe_no_cooperation_suppression'}


def _subfolder(strategy: str) -> str:
    if strategy in BASELINE_METHODS and strategy in ABLATION_METHODS:
        return 'baseline'   # full_ahe_mrta goes in both; primary is baseline
    if strategy in BASELINE_METHODS:
        return 'baseline'
    if strategy in ABLATION_METHODS:
        return 'ablation'
    return 'all'


def _load_map():
    """Return (image_array, extent) for imshow, or (None, None) on failure."""
    try:
        if _PIL:
            img = PILImage.open(MAP_PGM).convert('L')
            arr = np.array(img)
        else:
            with open(MAP_PGM, 'rb') as f:
                magic = f.readline()
                assert magic.strip() == b'P5'
                while True:
                    line = f.readline()
                    if not line.startswith(b'#'):
                        break
                w, h = map(int, line.split())
                maxval = int(f.readline())
                raw = f.read(w * h)
            arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, w)

        with open(MAP_YAML) as f:
            meta = yaml.safe_load(f)
        res = float(meta.get('resolution', 0.05))
        ox, oy = meta.get('origin', [-10.0, -10.0])[:2]
        h, w = arr.shape
        extent = [ox, ox + w * res, oy, oy + h * res]
        return arr, extent
    except Exception as e:
        print(f'  [WARN] Could not load map: {e}', file=sys.stderr)
        return None, None


def _read_csv(path):
    if not path.exists():
        return []
    if _PIL:
        import pandas as pd
        try:
            return pd.read_csv(path).to_dict('records')
        except Exception:
            return []
    rows = []
    with open(path, newline='') as f:
        reader = __import__('csv').DictReader(f)
        rows = list(reader)
    return rows


def export_experiment(exp_dir: Path, out_root: Path, dpi: int = 200) -> None:
    meta_path = exp_dir / 'metadata.yaml'
    if not meta_path.exists():
        return

    with open(meta_path) as f:
        meta = yaml.safe_load(f)

    strategy = meta.get('strategy', 'unknown')
    scenario  = meta.get('scenario', 'unknown')
    seed      = meta.get('seed', 0)
    exp_id    = meta.get('experiment_id', exp_dir.name)

    task_pos_rows    = _read_csv(exp_dir / 'task_positions.csv')
    task_event_rows  = _read_csv(exp_dir / 'task_events.csv')
    alloc_rows       = _read_csv(exp_dir / 'allocation_events.csv')
    timeseries_rows  = _read_csv(exp_dir / 'robot_state_timeseries.csv')

    # Build task status map (last known status)
    task_status: dict = {}
    task_robot:  dict = {}
    for row in task_event_rows:
        tid = row.get('task_id', '')
        ev  = row.get('event', '')
        rid = row.get('robot_id', '')
        if ev in ('activated', 'task_assigned', 'task_completed', 'task_failed', 'completed', 'failed'):
            task_status[tid] = ev.replace('task_', '')
        if rid:
            task_robot[tid] = rid
    for row in alloc_rows:
        ev  = row.get('event_type', '')
        tid = row.get('task_id', '')
        rid = row.get('robot_id', '')
        if ev == 'task_assigned' and tid:
            task_status[tid] = 'assigned'
            task_robot[tid] = rid
        elif ev == 'task_completed' and tid:
            task_status[tid] = 'completed'
        elif ev == 'task_failed' and tid:
            task_status[tid] = 'failed'

    # Robot trajectories
    robot_traj: dict = {r: ([], []) for r in ROBOT_COLOR}
    for row in timeseries_rows:
        rid = row.get('robot_id', '')
        if rid in robot_traj:
            try:
                robot_traj[rid][0].append(float(row['x']))
                robot_traj[rid][1].append(float(row['y']))
            except (KeyError, ValueError):
                pass

    # ── Plot ─────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(6, 6))

    map_arr, extent = _load_map()
    if map_arr is not None:
        ax.imshow(map_arr, cmap='gray', origin='lower', extent=extent,
                  alpha=0.35, vmin=0, vmax=255)

    # Robot trajectories
    for rid, (xs, ys) in robot_traj.items():
        if xs:
            ax.plot(xs, ys, color=ROBOT_COLOR[rid], linewidth=1.2,
                    alpha=0.8, zorder=3)

    # Robot start positions
    for rid, (sx, sy) in ROBOT_STARTS.items():
        ax.plot(sx, sy, marker='D', color=ROBOT_COLOR[rid], markersize=8,
                zorder=5, markeredgecolor='white', markeredgewidth=0.6)
        ax.text(sx + 0.3, sy + 0.3, ROBOT_LABEL[rid], fontsize=6,
                color=ROBOT_COLOR[rid], zorder=6)

    # Task targets
    for row in task_pos_rows:
        tid = row.get('task_id', '')
        try:
            tx, ty = float(row['x']), float(row['y'])
        except (KeyError, ValueError):
            continue
        status = task_status.get(tid, 'pending')
        color  = STATUS_COLOR.get(status, STATUS_COLOR['pending'])
        rid    = task_robot.get(tid, '')
        marker_color = ROBOT_COLOR.get(rid, color) if status == 'completed' else color
        ax.scatter(tx, ty, s=60, c=marker_color, zorder=4,
                   edgecolors='white', linewidths=0.4, alpha=0.9)
        ax.text(tx + 0.15, ty + 0.15, tid.replace('task_', 'T'),
                fontsize=4.5, color='#333', zorder=5)

    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.set_aspect('equal')
    ax.set_xlabel('x (m)', fontsize=8)
    ax.set_ylabel('y (m)', fontsize=8)

    method_lbl = METHOD_LABEL.get(strategy, strategy)
    ax.set_title(f'{method_lbl} | {scenario} | seed {seed}', fontsize=9, fontweight='bold')

    # Legend — robots
    robot_patches = [
        mpatches.Patch(color=ROBOT_COLOR[r], label=ROBOT_LABEL[r])
        for r in sorted(ROBOT_COLOR)
    ]
    status_patches = [
        mpatches.Patch(color=c, label=s.capitalize())
        for s, c in STATUS_COLOR.items()
        if s not in ('pending',)
    ]
    ax.legend(handles=robot_patches + status_patches,
              loc='lower right', fontsize=6, framealpha=0.7,
              ncol=2, handlelength=1.2)

    fig.tight_layout()

    subfolder = _subfolder(strategy)
    out_dir = out_root / subfolder
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{exp_id}.png'
    fig.savefig(out_path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f'[OK]  {out_path}')


def main():
    parser = argparse.ArgumentParser(description='Export per-experiment trajectory PNGs')
    parser.add_argument('--raw-dir', default='results/raw',
                        help='Root directory containing experiment subdirectories')
    parser.add_argument('--output-dir', default='results/paper_figures/trajectories',
                        help='Output directory for PNG files')
    parser.add_argument('--dpi', type=int, default=200,
                        help='PNG resolution (default: 200)')
    parser.add_argument('--strategy', default='',
                        help='Filter by strategy (optional)')
    parser.add_argument('--scenario', default='',
                        help='Filter by scenario (optional)')
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    if not raw_dir.exists():
        print(f'[WARN] raw_dir not found: {raw_dir}', file=sys.stderr)
        return

    exp_dirs = sorted(
        d for d in raw_dir.rglob('metadata.yaml')
        if d.parent.is_dir()
    )

    if not exp_dirs:
        print(f'[WARN] No experiment directories found under {raw_dir}', file=sys.stderr)
        return

    count = 0
    for meta_path in exp_dirs:
        exp_dir = meta_path.parent
        with open(meta_path) as f:
            meta = yaml.safe_load(f)
        if args.strategy and meta.get('strategy') != args.strategy:
            continue
        if args.scenario and meta.get('scenario') != args.scenario:
            continue
        export_experiment(exp_dir, out_root, dpi=args.dpi)
        count += 1

    print(f'\n[DONE] Exported {count} experiment PNG(s) → {out_root}/')


if __name__ == '__main__':
    main()
