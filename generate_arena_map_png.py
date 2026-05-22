#!/usr/bin/env python3
"""
Generate arena map PNG for AHE-MRTA paper.

Shows:
  - Occupancy grid (grey = obstacle, white = free)
  - Task grid points (_GRID from experiment_runner_node.py)
  - Robot spawn positions for S1 (5r), S2 (10r), S3 (15r)
  - Arena bounds and scale bar

Usage:
    python3 generate_arena_map_png.py [--output results/figures/arena_map.png]
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


# ── Task grid (from experiment_runner_node.py _GRID) ──────────────────────────
TASK_GRID = [
    (-5.0, -2.0), (5.0,  0.0), (-6.0,  1.5), (6.0, -4.0), (0.0,  7.0),
    ( 6.0, -6.0), (-2.0,  7.0), (-6.0, -6.0), (1.0, -6.0), (0.0, -7.0),
    (-6.0, -1.5), (6.0,  6.0), (1.0,  6.0), (-6.0,  6.0), (0.0, -2.0),
    ( 4.0, -6.0), (-5.0,  2.0), (3.0,  7.0), (-3.0,  7.0), (7.0,  0.0),
    (-7.0,  0.0), (0.0, -6.0), (6.0,  1.5), (-6.0,  4.0), (6.0, -1.5),
    (-4.0,  6.0), (4.0,  6.0), (-4.0, -6.0),
    # y=2.0 row  (added for S3)
    (-5.0,  2.0), (-3.0,  2.0), (0.0,  2.0), (3.0,  2.0), (5.0,  2.0),
    # y=-2.0 row
    (-5.0, -2.0), (-3.0, -2.0), (0.0, -2.0), (3.0, -2.0), (5.0, -2.0),
    # central verticals
    (0.0,  7.0), (0.0,  6.0), (0.0, -6.0), (0.0, -7.0),
]
# Deduplicate while preserving order
seen = set()
TASK_GRID_DEDUP = []
for p in TASK_GRID:
    if p not in seen:
        seen.add(p)
        TASK_GRID_DEDUP.append(p)


def spawn_positions(n):
    """Mirrors compute_spawn_positions from multi_robot_helpers.py."""
    ys = [-4.0, -2.0, 0.0, 2.0, 4.0]
    if n <= 0:
        return []
    if n == 1:
        return [(-4.0, 0.0)]
    if n == 2:
        return [(-4.0, 1.0), (-4.0, -1.0)]
    if n == 3:
        return [(-4.0, 0.0), (-4.0, 2.0), (-4.0, -2.0)]
    if n <= 5:
        return [(-4.0, y) for y in ys[:n]]
    if n <= 10:
        return [(-4.0, y) for y in ys] + [(-3.0, y) for y in ys[:n-5]]
    ys_c = ys[:n-10]
    return ([(-4.0, y) for y in ys] + [(-3.0, y) for y in ys]
            + [(-2.0, y) for y in ys_c])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='results/figures/arena_map.png')
    parser.add_argument('--map-pgm',
                        default='src/m_ahe_nav2_config/maps/obstacle_map.pgm')
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Load occupancy map
    img = Image.open(args.map_pgm).convert('L')
    arr = np.array(img, dtype=float)

    origin_x, origin_y = -10.0, -10.0
    resolution = 0.05  # m/pixel
    h, w = arr.shape
    extent = [origin_x, origin_x + w * resolution,
              origin_y, origin_y + h * resolution]

    # Build coloured map: obstacles → dark, free → white, unknown → grey
    rgb = np.ones((h, w, 3), dtype=float)
    occ_mask  = arr < 10      # occupied
    free_mask = arr > 200     # free
    unk_mask  = ~occ_mask & ~free_mask

    rgb[occ_mask]  = [0.20, 0.20, 0.20]   # dark charcoal
    rgb[free_mask] = [0.97, 0.97, 0.97]   # near-white
    rgb[unk_mask]  = [0.65, 0.65, 0.65]   # mid-grey

    fig, ax = plt.subplots(figsize=(9, 9))
    ax.imshow(rgb, extent=extent, origin='upper', interpolation='nearest')

    # ── Task grid ────────────────────────────────────────────────────────────
    tx, ty = zip(*TASK_GRID_DEDUP)
    ax.scatter(tx, ty, s=40, marker='s', color='#1f77b4', zorder=5,
               label='Task grid points', linewidths=0)

    # ── Spawn positions ───────────────────────────────────────────────────────
    colors = {5: '#d62728', 10: '#ff7f0e', 15: '#2ca02c'}
    markers = {5: 'o', 10: '^', 15: 'D'}
    labels  = {5: 'S1 spawn (5r)', 10: 'S2 spawn (10r)', 15: 'S3 spawn (15r)'}
    for n in [5, 10, 15]:
        pts = spawn_positions(n)
        sx, sy = zip(*pts)
        ax.scatter(sx, sy, s=80, marker=markers[n], color=colors[n], zorder=6,
                   label=labels[n], edgecolors='k', linewidths=0.5)

    # ── Arena boundary annotation ─────────────────────────────────────────────
    for side, pos, ha, va in [
        ('Right wall', (9.5, 0), 'left', 'center'),
        ('Left wall',  (-9.5, 0), 'right', 'center'),
    ]:
        ax.axvline(x=9.90 if 'Right' in side else -9.90,
                   color='#8B0000', lw=1.0, ls='--', alpha=0.6)

    # ── Formatting ────────────────────────────────────────────────────────────
    ax.set_xlim(-10.3, 10.3)
    ax.set_ylim(-10.3, 10.3)
    ax.set_xlabel('x (m)', fontsize=11)
    ax.set_ylabel('y (m)', fontsize=11)
    ax.set_title('AHE-MRTA Arena — Harita, Görev Noktaları ve Başlangıç Konumları',
                 fontsize=12, pad=10)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.legend(loc='upper right', fontsize=9, framealpha=0.85)

    # Scale bar: 2 m
    sb_x, sb_y = -9.5, -9.5
    ax.plot([sb_x, sb_x + 2], [sb_y, sb_y], 'k-', lw=2, zorder=7)
    ax.text(sb_x + 1, sb_y - 0.4, '2 m', ha='center', va='top', fontsize=8)

    plt.tight_layout()
    plt.savefig(args.output, dpi=150, bbox_inches='tight')
    print(f'Saved: {args.output}')


if __name__ == '__main__':
    main()
