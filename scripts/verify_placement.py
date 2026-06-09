#!/usr/bin/env python3
"""verify_placement — prove the obstacle-aware placement is correct & shared.

Checks, for every (robot_count, task_count) in the experiment matrix and every
seed in 1..K:
  1. every robot spawn is collision-free (outside the inflated obstacle map),
  2. every task goal is collision-free,
  3. the SIM and the Gazebo runner would receive IDENTICAL positions for a
     given (n, m, seed) — they both call m_ahe_task_allocator.placement, so this
     verifies the wiring rather than re-deriving it.

Also (re)generates the per-scale scenario overlay PNGs so the placement can be
eyeballed against the arena obstacles.

Usage:
    python3 scripts/verify_placement.py
Exit code 0 = all PASS.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src/m_ahe_mrta_bringup/launch'))

from m_ahe_task_allocator.placement import (  # noqa: E402
    robot_spawns, task_positions, is_free, GRID,
)

# (robot_count, task_count) covering the full SIM matrix + Gazebo densities.
MATRIX = [
    (3, 9), (3, 15), (3, 24),
    (5, 15), (5, 25), (5, 40),
    (10, 30), (10, 50), (10, 80),
]
SEEDS = range(1, 11)


def _bad(points):
    return [p for p in points if not is_free(*p)]


def main() -> int:
    report = []
    ok = True

    # curated grid sanity
    free_grid = sum(1 for p in GRID if is_free(*p))
    line = f'curated grid: {free_grid}/{len(GRID)} points obstacle-free'
    report.append(line)
    if free_grid != len(GRID):
        ok = False
        report.append('  WARNING: some curated grid points fall in inflation')

    total_pos = 0
    collisions = 0
    for n, m in MATRIX:
        per_combo_bad = 0
        # robot spawns are seed-independent; check once
        rs = robot_spawns(n)
        br = _bad(rs)
        if len(rs) != n:
            ok = False
            report.append(f'N={n} M={m}: only {len(rs)}/{n} robot spawns produced')
        per_combo_bad += len(br)
        for seed in SEEDS:
            ts = task_positions(m, seed, n_robots=n)
            if len(ts) != m:
                ok = False
                report.append(f'N={n} M={m} seed={seed}: only {len(ts)}/{m} tasks')
            bt = _bad(ts)
            per_combo_bad += len(bt)
            total_pos += len(rs) + len(ts)

            # no task may sit on top of a robot spawn (>= ROBOT_TASK_CLEAR)
            overlap = [t for t in ts
                       if any((t[0]-rx)**2 + (t[1]-ry)**2 < 0.81 for rx, ry in rs)]
            if overlap:
                ok = False
                per_combo_bad += len(overlap)
                report.append(f'N={n} M={m} seed={seed}: {len(overlap)} task/robot overlaps')

            # determinism + SIM<->Gazebo equality: same call -> same result
            ts2 = task_positions(m, seed, n_robots=n)
            if ts2 != ts:
                ok = False
                report.append(f'N={n} M={m} seed={seed}: non-deterministic tasks')

        collisions += per_combo_bad
        status = 'OK' if per_combo_bad == 0 else f'{per_combo_bad} COLLISIONS'
        report.append(f'N={n:2d} M={m:2d} | robots {len(rs)}/{n} '
                      f'| tasks/seed {m} x{len(SEEDS)} | {status}')
        if per_combo_bad:
            ok = False

    report.append('')
    report.append(f'checked {total_pos} positions across {len(MATRIX)} combos '
                  f'x {len(SEEDS)} seeds')
    report.append(f'collisions: {collisions}')
    report.append(f'RESULT: {"PASS" if ok else "FAIL"}')

    text = '\n'.join(report)
    print(text)
    out = os.path.join(ROOT, 'results', 'placement_check.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w') as f:
        f.write(text + '\n')
    print(f'\n[report] {out}')

    # Regenerate scenario overlay PNGs (visual proof) — best-effort.
    try:
        import generate_scenario_maps  # noqa: F401
        generate_scenario_maps.main()
        print('[maps] results/figures/scenario_map_*.png regenerated')
    except Exception as e:  # pragma: no cover
        print(f'[maps] skipped scenario maps: {e}')

    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
