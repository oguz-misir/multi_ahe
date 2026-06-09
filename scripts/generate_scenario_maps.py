#!/usr/bin/env python3
"""
Generate per-scale scenario maps for AHE-MRTA paper / ana_method.md.

For each evaluation scale (robot_count, task_count) it renders the inspection
arena occupancy map overlaid with:
  - the candidate inspection grid (faint, all _GRID points)
  - the M task points actually sampled for that scale (seed=1, faithful to
    ExperimentRunnerNode._generate_tasks)
  - the N robot spawn positions (compute_spawn_positions)

Single source of truth:
  - task grid   : parsed from experiment_runner_node._GRID
  - spawn layout: imported from multi_robot_helpers.compute_spawn_positions

Outputs (results/figures/):
  scenario_map_3r15t.png, scenario_map_5r25t.png, scenario_map_10r50t.png
  scenario_maps_panel.png  (combined 1x3 panel for the paper)

Usage:
    python3 scripts/generate_scenario_maps.py
"""

import os
import random
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src/m_ahe_mrta_bringup/launch'))
from multi_robot_helpers import compute_spawn_positions  # noqa: E402

MAP_PGM = os.path.join(ROOT, 'src/m_ahe_nav2_config/maps/obstacle_map.pgm')
RUNNER = os.path.join(
    ROOT,
    'src/m_ahe_task_allocator/m_ahe_task_allocator/experiment_runner_node.py')
OUTDIR = os.path.join(ROOT, 'results/figures')

ORIGIN_X, ORIGIN_Y = -10.0, -10.0
RESOLUTION = 0.05  # m/pixel

# Evaluation scales (robot_count, task_count) — §5.2 of ana_method.md
SCALES = [(3, 15), (5, 25), (10, 50)]


def load_grid():
    """Curated obstacle-free inspection grid (single source: placement.GRID)."""
    from m_ahe_task_allocator.placement import GRID
    return list(GRID)


def sample_tasks(grid, task_count, seed=1, n_robots=0):
    """Obstacle-aware task goals, identical to the SIM and Gazebo runner."""
    from m_ahe_task_allocator.placement import task_positions
    return task_positions(task_count, seed, n_robots)


def load_map_rgb():
    img = Image.open(MAP_PGM).convert('L')
    arr = np.array(img, dtype=float)
    h, w = arr.shape
    extent = [ORIGIN_X, ORIGIN_X + w * RESOLUTION,
              ORIGIN_Y, ORIGIN_Y + h * RESOLUTION]
    rgb = np.ones((h, w, 3), dtype=float)
    occ = arr < 10
    free = arr > 200
    unk = ~occ & ~free
    rgb[occ] = [0.20, 0.20, 0.20]
    rgb[free] = [0.97, 0.97, 0.97]
    rgb[unk] = [0.78, 0.78, 0.78]
    return rgb, extent


def draw_scene(ax, rgb, extent, grid, n_robots, n_tasks, title):
    ax.imshow(rgb, extent=extent, origin='upper', interpolation='nearest')

    # faint candidate grid
    gx, gy = zip(*grid)
    ax.scatter(gx, gy, s=14, marker='.', color='#9ecae1', zorder=3,
               label=f'Aday inspection grid ({len(grid)})', linewidths=0)

    # sampled tasks for this scale
    tasks = sample_tasks(grid, n_tasks, seed=1, n_robots=n_robots)
    tx, ty = zip(*tasks)
    ax.scatter(tx, ty, s=42, marker='s', color='#1f77b4', zorder=5,
               edgecolors='white', linewidths=0.4,
               label=f'Görev noktaları (M={n_tasks})')

    # robot spawns
    sp = compute_spawn_positions(n_robots)
    sx, sy = zip(*sp)
    ax.scatter(sx, sy, s=110, marker='^', color='#d62728', zorder=6,
               edgecolors='k', linewidths=0.6,
               label=f'Robot başlangıç (N={n_robots})')

    ax.set_xlim(-10.3, 10.3)
    ax.set_ylim(-10.3, 10.3)
    ax.set_xlabel('x (m)', fontsize=9)
    ax.set_ylabel('y (m)', fontsize=9)
    ax.set_title(title, fontsize=11, pad=8)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.25, linewidth=0.4)
    ax.legend(loc='upper right', fontsize=7, framealpha=0.9)

    # 2 m scale bar
    ax.plot([-9.4, -7.4], [-9.6, -9.6], 'k-', lw=2, zorder=7)
    ax.text(-8.4, -9.95, '2 m', ha='center', va='top', fontsize=7)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    grid = load_grid()
    rgb, extent = load_map_rgb()
    print(f'Loaded {len(grid)} grid points, map {rgb.shape[1]}x{rgb.shape[0]}')

    # Individual figures
    for n, m in SCALES:
        fig, ax = plt.subplots(figsize=(5.2, 5.2))
        draw_scene(ax, rgb, extent, grid, n, m,
                   f'Senaryo ölçeği {n}r/{m}g  (~{m/n:.0f} görev/robot)')
        plt.tight_layout()
        out = os.path.join(OUTDIR, f'scenario_map_{n}r{m}t.png')
        fig.savefig(out, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'Saved: {out}')

    # Combined panel
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    for ax, (n, m) in zip(axes, SCALES):
        draw_scene(ax, rgb, extent, grid, n, m,
                   f'{n}r/{m}g  (~{m/n:.0f} görev/robot)')
    fig.suptitle('AHE-MRTA — Ortam senaryo haritaları (robot × görev ölçekleri)',
                 fontsize=13, y=1.02)
    plt.tight_layout()
    out = os.path.join(OUTDIR, 'scenario_maps_panel.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {out}')


if __name__ == '__main__':
    main()
