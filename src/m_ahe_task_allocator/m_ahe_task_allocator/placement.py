"""placement — obstacle-aware, deterministic, shared robot/task placement.

Single source of truth for WHERE robots spawn and WHERE tasks appear, used
identically by both evaluation planes:

  * the navigation-independent SIM   (scripts/simulate_and_tune.py)
  * the Gazebo ExperimentRunnerNode  (experiment_runner_node.py)
  * the SDF spawn / scenario maps     (multi_robot_helpers, generate_scenario_maps)

Why this module exists
----------------------
Previously the SIM placed tasks at purely random ``uniform(-5, 5)`` coordinates
with NO obstacle check (tasks could land inside shelves/walls), used a different
robot spawn layout than Gazebo, and the Gazebo runner filled tasks beyond the
curated grid with unchecked ``uniform(-8, 8)``. The two planes therefore saw
different, sometimes-infeasible positions for the same seed, breaking the
"same task pool" (R4) and SIM<->Gazebo cross-validation (R6) guarantees.

This module reads the real ``obstacle_map.pgm`` (the same map Nav2's global
costmap loads), inflates the obstacles, and returns collision-free positions
that are *identical* for a given ``(n, m, seed)`` across both planes.
"""

from __future__ import annotations

import os
import re
import random
from typing import List, Tuple

import numpy as np

Pos = Tuple[float, float]

# --- Map geometry (must match src/m_ahe_nav2_config/maps/obstacle_map.yaml) ---
ORIGIN_X, ORIGIN_Y = -10.0, -10.0
RESOLUTION = 0.05            # m / pixel  (400x400 -> 20x20 m)
OCC_THRESH = 50             # pgm value < this  => occupied cell

# --- Placement clearances -----------------------------------------------------
# Inflate obstacles by this radius so neither robots nor task goals sit inside
# the lethal+inflation zone (Nav2 inflation_radius 0.30 + robot footprint).
# 0.55 m comfortably exceeds the effective inflation while staying below the
# 0.72 m clearance the legacy curated grid already satisfies.
INFLATION_M = 0.55
ARENA_LIM = 9.3             # keep positions inside the perimeter walls
MIN_TASK_SEP = 0.55         # min spacing between task goals
MIN_ROBOT_SEP = 0.9         # min spacing between robot spawns
ROBOT_TASK_CLEAR = 1.0      # min spacing between a task goal and any robot spawn
                            # (keeps the inspection goals out of the robot depot)

# ---------------------------------------------------------------------------
# Curated obstacle-free inspection grid (single source of truth; moved here
# from experiment_runner_node._GRID). Hand-placed in corridors between the
# shelves / dividers; all points are re-validated against the inflated map at
# runtime, so a stale entry is simply dropped rather than used blindly.
# ---------------------------------------------------------------------------
GRID: List[Pos] = [
    (-6.0, 7.0), (-2.0, 7.0), (0.0, 7.0), (2.0, 7.0), (6.0, 7.0),
    (-6.0, 6.0), (-4.0, 6.0), (-1.0, 6.0), (0.0, 6.0), (1.0, 6.0), (4.0, 6.0), (6.0, 6.0),
    (-5.0, 2.0), (-3.0, 2.0), (0.0, 2.0), (3.0, 2.0), (5.0, 2.0),
    (-6.0, 1.5), (6.0, 1.5), (-5.0, 0.0), (5.0, 0.0),
    (-6.0, -1.5), (6.0, -1.5), (-4.0, 0.0), (4.0, 0.0),
    (-5.0, -2.0), (-3.0, -2.0), (0.0, -2.0), (3.0, -2.0), (5.0, -2.0),
    (-6.0, -4.0), (-2.0, -4.0), (2.0, -4.0), (6.0, -4.0),
    (-6.0, -6.0), (-4.0, -6.0), (-1.0, -6.0), (0.0, -6.0), (1.0, -6.0), (4.0, -6.0), (6.0, -6.0),
    (0.0, -7.0),
]


# ---------------------------------------------------------------------------
# Obstacle map loading + inflation (cached at module level)
# ---------------------------------------------------------------------------
def _find_map_pgm() -> str:
    """Locate obstacle_map.pgm in the installed share or the source tree."""
    # 1) ament installed share
    try:
        from ament_index_python.packages import get_package_share_directory
        share = get_package_share_directory('m_ahe_nav2_config')
        cand = os.path.join(share, 'maps', 'obstacle_map.pgm')
        if os.path.exists(cand):
            return cand
    except Exception:
        pass
    # 2) walk up from this file to the repo root, then src/
    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    for _ in range(8):
        cand = os.path.join(d, 'src', 'm_ahe_nav2_config', 'maps', 'obstacle_map.pgm')
        if os.path.exists(cand):
            return cand
        d = os.path.dirname(d)
    raise FileNotFoundError('obstacle_map.pgm not found (placement module)')


_INFLATED = None  # tuple(np.ndarray[bool] HxW, W, H)


def _occ():
    """Return (inflated_occupancy[H,W] bool, W, H), loading + caching once."""
    global _INFLATED
    if _INFLATED is None:
        data = open(_find_map_pgm(), 'rb').read()
        m = re.match(rb'P5\s+(\d+)\s+(\d+)\s+(\d+)\s', data)
        if not m:
            raise ValueError('Unsupported PGM (expected binary P5)')
        hdr = m.end()
        w, h = int(m.group(1)), int(m.group(2))
        arr = np.frombuffer(data[hdr:hdr + w * h], dtype=np.uint8).reshape(h, w)
        occ = arr < OCC_THRESH
        rad = int(round(INFLATION_M / RESOLUTION))
        yy, xx = np.ogrid[-rad:rad + 1, -rad:rad + 1]
        se = (xx * xx + yy * yy) <= rad * rad
        try:
            from scipy.ndimage import binary_dilation
            inflated = binary_dilation(occ, structure=se)
        except Exception:
            # numpy-only fallback dilation (shift-OR over the disk offsets)
            inflated = occ.copy()
            offs = list(zip(*np.where(se)))
            for dy, dx in offs:
                sy, sx = dy - rad, dx - rad
                inflated |= np.roll(np.roll(occ, sy, axis=0), sx, axis=1)
        _INFLATED = (inflated, w, h)
    return _INFLATED


def _world_to_rc(x: float, y: float, h: int) -> Tuple[int, int]:
    col = int((x - ORIGIN_X) / RESOLUTION)
    row = h - 1 - int((y - ORIGIN_Y) / RESOLUTION)
    return row, col


def is_free(x: float, y: float) -> bool:
    """True if (x, y) is inside the arena and outside every inflated obstacle."""
    if abs(x) > ARENA_LIM or abs(y) > ARENA_LIM:
        return False
    occ, w, h = _occ()
    r, c = _world_to_rc(x, y, h)
    if 0 <= r < h and 0 <= c < w:
        return not bool(occ[r, c])
    return False


# ---------------------------------------------------------------------------
# Robot spawns (deterministic, seed-independent — match the SDF spawn exactly)
# ---------------------------------------------------------------------------
# Centre-left obstacle-free columns; same layout the legacy
# compute_spawn_positions used, but every point is map-validated here.
_SPAWN_COLS = (-4.0, -3.0, -2.0)
_SPAWN_YS = (-4.0, -2.0, 0.0, 2.0, 4.0)


def _left_column_layout(n: int) -> List[Pos]:
    if n <= 0:
        return []
    if n == 1:
        return [(-4.0, 0.0)]
    if n == 2:
        return [(-4.0, 1.0), (-4.0, -1.0)]
    if n == 3:
        return [(-4.0, 0.0), (-4.0, 2.0), (-4.0, -2.0)]
    out: List[Pos] = []
    for col in _SPAWN_COLS:
        for y in _SPAWN_YS:
            if len(out) >= n:
                return out
            out.append((col, y))
    return out


def robot_spawns(n: int, seed: int = 1) -> List[Pos]:
    """N collision-free robot spawn positions (deterministic, seed-independent
    so SIM and the Gazebo SDF spawn agree). For counts beyond the curated
    columns, fill from obstacle-free rejection sampling on the left half."""
    base = [p for p in _left_column_layout(n) if is_free(*p)]
    out = base[:n]
    if len(out) < n:
        rng = random.Random(99991)  # fixed -> seed-independent extension
        out += _rejection(n - len(out), out, rng,
                          xr=(-9.0, -1.0), yr=(-9.0, 9.0), sep=MIN_ROBOT_SEP)
    return out[:n]


# ---------------------------------------------------------------------------
# Task positions (deterministic per seed; identical in SIM and Gazebo)
# ---------------------------------------------------------------------------
def task_positions(m: int, seed: int = 1, n_robots: int = 0) -> List[Pos]:
    """M collision-free task goals: shuffle the validated curated grid first,
    then top up with map-validated rejection sampling. Deterministic for a
    given (m, seed, n_robots).

    When ``n_robots`` is given the goals are also kept ``ROBOT_TASK_CLEAR`` m
    away from every robot spawn, so inspection targets never sit on top of the
    robot depot (fixes robot/target overlap at high robot counts)."""
    rng = random.Random(seed)
    robots = robot_spawns(n_robots) if n_robots else []

    def _clear_of_robots(p: Pos) -> bool:
        return all((p[0] - rx) ** 2 + (p[1] - ry) ** 2 >= ROBOT_TASK_CLEAR ** 2
                   for rx, ry in robots)

    grid = [p for p in GRID if is_free(*p) and _clear_of_robots(p)]
    rng.shuffle(grid)
    pts = grid[:m]
    if len(pts) < m:
        pts = list(pts) + _rejection(m - len(pts), pts, rng,
                                     xr=(-9.0, 9.0), yr=(-9.0, 9.0), sep=MIN_TASK_SEP,
                                     avoid=robots, avoid_sep=ROBOT_TASK_CLEAR)
    return pts[:m]


def _rejection(k: int, existing: List[Pos], rng: random.Random,
               xr: Tuple[float, float], yr: Tuple[float, float],
               sep: float, avoid: List[Pos] = (), avoid_sep: float = 0.0) -> List[Pos]:
    """Sample k obstacle-free points at least `sep` from each other/existing and
    at least `avoid_sep` from every point in `avoid` (e.g. robot spawns)."""
    def _ok_avoid(x, y):
        return all((x - ax) ** 2 + (y - ay) ** 2 >= avoid_sep * avoid_sep
                   for ax, ay in avoid)

    pts: List[Pos] = []
    have = list(existing)
    tries = 0
    max_tries = 20000 + 4000 * k
    while len(pts) < k and tries < max_tries:
        tries += 1
        x = rng.uniform(*xr)
        y = rng.uniform(*yr)
        if not is_free(x, y) or not _ok_avoid(x, y):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < sep * sep for px, py in have):
            continue
        pts.append((round(x, 3), round(y, 3)))
        have.append((x, y))
    # if separation can't be met (dense), relax task-task sep but still avoid
    # obstacles and the robot depot.
    while len(pts) < k and tries < max_tries * 2:
        tries += 1
        x = rng.uniform(*xr); y = rng.uniform(*yr)
        if is_free(x, y) and _ok_avoid(x, y):
            pts.append((round(x, 3), round(y, 3)))
    return pts


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    occ, w, h = _occ()
    print(f'map {w}x{h}, inflated occupied cells: {int(occ.sum())}')
    print(f'curated grid: {len(GRID)} pts, free after inflation: '
          f'{sum(1 for p in GRID if is_free(*p))}')
    for n, m in [(3, 9), (3, 15), (3, 24), (5, 25), (10, 50), (10, 80)]:
        rs = robot_spawns(n)
        ts = task_positions(m, seed=1)
        bad_r = [p for p in rs if not is_free(*p)]
        bad_t = [p for p in ts if not is_free(*p)]
        print(f'N={n:2d} M={m:2d} | robots free {len(rs)-len(bad_r)}/{len(rs)} '
              f'| tasks free {len(ts)-len(bad_t)}/{len(ts)}'
              + ('  <-- COLLISION' if bad_r or bad_t else ''))
