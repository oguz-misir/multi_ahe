#!/usr/bin/env python3
"""
Paper-quality arena map figures for AHE-MRTA.

Generates two figures:
  1. Arena environment + task goal positions (numbered, priority-colored)
  2. Same + robot trajectory paths from experiment data

Usage:
    python3 scripts/plot_arena.py
    python3 scripts/plot_arena.py --exp-dir results/raw/gazebo/exp_robot_failure_full_ahe_mrta_r3t15_seed01
    python3 scripts/plot_arena.py --out-dir results/paper_figures/arena
"""

import argparse
import os
import struct
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import pandas as pd

# ── Map metadata (obstacle_map.yaml) ─────────────────────────────────────────
MAP_PGM   = os.path.join(os.path.dirname(__file__), '..', 'src',
                         'm_ahe_nav2_config', 'maps', 'obstacle_map.pgm')
RESOLUTION = 0.05    # m/pixel
ORIGIN     = (-10.0, -10.0)   # world coords of pixel (0,0) bottom-left
MAP_W_PX   = 400
MAP_H_PX   = 400
WORLD_EXTENT = [ORIGIN[0], ORIGIN[0] + MAP_W_PX * RESOLUTION,
                ORIGIN[1], ORIGIN[1] + MAP_H_PX * RESOLUTION]
# → [-10, 10, -10, 10]

# ── Robot start positions ─────────────────────────────────────────────────────
ROBOT_STARTS = {
    'robot_1': (0.0,  0.0),
    'robot_2': (0.0,  2.0),
    'robot_3': (0.0, -2.0),
}
ROBOT_COLORS = {
    'robot_1': '#2196F3',   # blue
    'robot_2': '#4CAF50',   # green
    'robot_3': '#F44336',   # red
}

# ── Priority color scheme ─────────────────────────────────────────────────────
PRIORITY_COLORS = {
    2: '#1565C0',   # blue — normal
    3: '#E65100',   # orange-red — high
}
PRIORITY_LABELS = {
    2: 'Priority 2 (Normal)',
    3: 'Priority 3 (High)',
}


def load_pgm(path: str) -> np.ndarray:
    """Load a binary P5 PGM file and return uint8 array (row=y, col=x)."""
    with open(path, 'rb') as f:
        def _readline():
            line = f.readline()
            while line.startswith(b'#'):
                line = f.readline()
            return line.decode().strip()
        magic = _readline()
        assert magic == 'P5', f"Not a P5 PGM: {magic}"
        w, h = map(int, _readline().split())
        maxval = int(_readline())
        raw = f.read(w * h)
    arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w))
    return arr


def world_to_px(x, y):
    """Convert world coords (m) to pixel (col, row). Row 0 is TOP of image."""
    col = (x - ORIGIN[0]) / RESOLUTION
    row = MAP_H_PX - (y - ORIGIN[1]) / RESOLUTION   # flip y for image coords
    return col, row


def setup_axes(ax, title: str):
    ax.set_title(title, fontsize=11, fontweight='bold', pad=8)
    ax.set_xlabel('x (m)', fontsize=10)
    ax.set_ylabel('y (m)', fontsize=10)
    ax.set_xlim(WORLD_EXTENT[0], WORLD_EXTENT[1])
    ax.set_ylim(WORLD_EXTENT[2], WORLD_EXTENT[3])
    ax.set_aspect('equal')
    ax.tick_params(labelsize=9)
    ax.grid(True, alpha=0.25, linewidth=0.5, color='gray')


def draw_map(ax, img: np.ndarray):
    """Draw PGM map as background. PGM row 0 = top, imshow origin='upper'."""
    # Convert occupancy: 0=obstacle(black), 254=free(white)
    # Show as light gray background, obstacles dark
    rgb = np.stack([img, img, img], axis=-1).astype(float) / 255.0
    # Tint free space very slightly warm
    ax.imshow(rgb, origin='upper',
              extent=WORLD_EXTENT,
              cmap='gray', vmin=0, vmax=1,
              interpolation='nearest', zorder=0)


def draw_robots(ax):
    for name, (rx, ry) in ROBOT_STARTS.items():
        c = ROBOT_COLORS[name]
        ax.plot(rx, ry, marker='^', markersize=10, color=c,
                markeredgecolor='white', markeredgewidth=0.8, zorder=4,
                label=name.replace('_', ' ').title())
        ax.annotate(name.split('_')[1],
                    xy=(rx, ry), xytext=(rx + 0.25, ry + 0.25),
                    fontsize=7, color=c, fontweight='bold', zorder=5)


def draw_tasks(ax, tasks: pd.DataFrame):
    for _, row in tasks.iterrows():
        tx, ty, pri = float(row['x']), float(row['y']), int(row['priority'])
        task_num = int(row['task_id'].split('_')[1])
        c = PRIORITY_COLORS.get(pri, 'gray')
        # Circle marker
        circle = plt.Circle((tx, ty), 0.35, color=c, alpha=0.85,
                             linewidth=1.0, zorder=3)
        ax.add_patch(circle)
        # Task number inside circle
        ax.text(tx, ty, str(task_num), ha='center', va='center',
                fontsize=6.5, color='white', fontweight='bold', zorder=4)


def draw_trajectories(ax, traj: pd.DataFrame):
    for robot_id, grp in traj.groupby('robot_id'):
        grp = grp.sort_values('timestamp_s')
        xs, ys = grp['x'].values, grp['y'].values
        c = ROBOT_COLORS.get(robot_id, 'purple')
        ax.plot(xs, ys, '-', color=c, linewidth=1.2, alpha=0.7, zorder=2)
        # Direction arrows every N points
        n = max(1, len(xs) // 8)
        for i in range(n, len(xs), n):
            dx = xs[i] - xs[i-1]
            dy = ys[i] - ys[i-1]
            dist = np.hypot(dx, dy)
            if dist > 0.05:
                ax.annotate('',
                    xy=(xs[i], ys[i]),
                    xytext=(xs[i] - dx*0.3/dist, ys[i] - dy*0.3/dist),
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.0),
                    zorder=2)


def build_legend_handles(with_traj=False):
    handles = []
    # Task priorities
    for pri, label in sorted(PRIORITY_LABELS.items()):
        handles.append(mpatches.Patch(color=PRIORITY_COLORS[pri], label=label))
    # Robots
    for name, c in ROBOT_COLORS.items():
        marker = 'v' if with_traj else '^'
        lbl = name.replace('_', ' ').title() + (' (start)' if with_traj else '')
        handles.append(Line2D([0], [0], marker='^', color='w',
                               markerfacecolor=c, markersize=8,
                               markeredgecolor='white',
                               label=name.replace('_', ' ').title()
                               + (' start' if with_traj else '')))
    if with_traj:
        for name, c in ROBOT_COLORS.items():
            handles.append(Line2D([0], [0], color=c, linewidth=1.5,
                                   label=name.replace('_', ' ').title() + ' path'))
    return handles


def make_figure_env(img, tasks, out_path):
    fig, ax = plt.subplots(figsize=(6.5, 6.5), dpi=200)
    setup_axes(ax, 'AHE-MRTA Arena — Task Goal Positions')
    draw_map(ax, img)
    draw_tasks(ax, tasks)
    draw_robots(ax)
    ax.legend(handles=build_legend_handles(False),
              loc='lower right', fontsize=7.5, framealpha=0.9,
              edgecolor='gray', fancybox=False)
    fig.tight_layout(pad=1.0)
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'[OK] {out_path}')


def make_figure_paths(img, tasks, traj, out_path):
    fig, ax = plt.subplots(figsize=(6.5, 6.5), dpi=200)
    setup_axes(ax, 'AHE-MRTA Arena — Robot Trajectories & Task Goals')
    draw_map(ax, img)
    draw_trajectories(ax, traj)
    draw_tasks(ax, tasks)
    draw_robots(ax)
    ax.legend(handles=build_legend_handles(True),
              loc='lower right', fontsize=7.0, framealpha=0.9,
              edgecolor='gray', fancybox=False)
    fig.tight_layout(pad=1.0)
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'[OK] {out_path}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exp-dir', default=
        'results/raw/gazebo/exp_robot_failure_full_ahe_mrta_r3t15_seed01')
    parser.add_argument('--out-dir', default='results/paper_figures/arena')
    parser.add_argument('--map', default=None,
        help='Override PGM map path')
    args = parser.parse_args()

    repo = os.path.join(os.path.dirname(__file__), '..')
    exp_dir  = os.path.join(repo, args.exp_dir)
    out_dir  = os.path.join(repo, args.out_dir)
    map_path = args.map or os.path.join(repo, MAP_PGM)

    os.makedirs(out_dir, exist_ok=True)

    # Load map
    img = load_pgm(map_path)
    print(f'[OK] Map loaded: {img.shape}  ({MAP_W_PX*RESOLUTION:.0f}×{MAP_H_PX*RESOLUTION:.0f} m)')

    # Load tasks
    task_csv = os.path.join(exp_dir, 'task_positions.csv')
    tasks = pd.read_csv(task_csv)
    print(f'[OK] Tasks: {len(tasks)} goals')

    # Figure 1: env + tasks
    fig1_path = os.path.join(out_dir, 'arena_task_goals.pdf')
    fig1_png  = os.path.join(out_dir, 'arena_task_goals.png')
    make_figure_env(img, tasks, fig1_path)
    make_figure_env(img, tasks, fig1_png)

    # Figure 2: env + tasks + trajectories
    traj_csv = os.path.join(exp_dir, 'robot_state_timeseries.csv')
    if os.path.exists(traj_csv):
        traj = pd.read_csv(traj_csv)
        print(f'[OK] Trajectory: {len(traj)} rows, {traj["robot_id"].nunique()} robots')
        fig2_path = os.path.join(out_dir, 'arena_trajectories.pdf')
        fig2_png  = os.path.join(out_dir, 'arena_trajectories.png')
        make_figure_paths(img, tasks, traj, fig2_path)
        make_figure_paths(img, tasks, traj, fig2_png)
    else:
        print(f'[WARN] No trajectory file: {traj_csv}')

    print(f'[DONE] Figures saved to {out_dir}/')


if __name__ == '__main__':
    main()
