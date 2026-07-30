#!/usr/bin/env python3
"""Regression tests for the geodesic warm-up path and F58 profile arity.

Both defects covered here are silent: the arity bug only fires when a leg is
geodesically unreachable (which depends on where Nav2 happens to leave a robot),
and a warm-up regression shows up as a latency number rather than a wrong
answer.  Neither is caught by the outcome-level tests.
"""

import ast
import inspect
import os
import sys
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src', 'm_ahe_task_allocator'))

from m_ahe_task_allocator.baselines.ahe_variants import AHEMRTAv3Allocator
from m_ahe_task_allocator.geodesic_cost import (
    clear_geodesic_cache, geodesic_distance, precompute,
)
from m_ahe_task_allocator.placement import is_free


def _free_points(n, seed=7):
    import numpy as np
    rng = np.random.default_rng(seed)
    pts = []
    while len(pts) < n:
        x, y = rng.uniform(-9.5, 9.5, 2)
        if is_free(x, y):
            pts.append((float(x), float(y)))
    return pts


class PlanProfileArityTest(unittest.TestCase):
    """Every return path must yield the 4-tuple both call sites unpack."""

    def test_all_return_paths_have_four_elements(self):
        src = textwrap.dedent(
            inspect.getsource(AHEMRTAv3Allocator._f58_plan_profile))
        arities = {
            len(node.value.elts)
            for node in ast.walk(ast.parse(src))
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple)
        }
        self.assertEqual(
            arities, {4},
            'unreachable-leg early return once yielded 3 values and crashed '
            'experiment_runner_node inside _epsilon_fair_repair')


class WarmupTest(unittest.TestCase):
    """Warm-up may change timing only -- never a distance."""

    def test_precompute_matches_on_demand_distances(self):
        pts = _free_points(30)
        tasks, robots = pts[:20], pts[20:]

        clear_geodesic_cache()
        reference = [[geodesic_distance(r, t) for t in tasks] for r in robots]

        clear_geodesic_cache()
        precompute(tasks)
        warmed = [[geodesic_distance(r, t) for t in tasks] for r in robots]

        self.assertEqual(reference, warmed)

    def test_precompute_reports_anchor_count_and_is_idempotent(self):
        pts = _free_points(12)
        clear_geodesic_cache()
        self.assertEqual(precompute(pts), len(set(pts)))
        self.assertEqual(precompute(pts), 0, 'anchors must not be recomputed')

    def test_warmup_hook_is_a_noop_without_geodesic_mode(self):
        allocator = AHEMRTAv3Allocator()
        previous = os.environ.pop('AHE_F58_GEODESIC', None)
        try:
            self.assertEqual(allocator.warmup(_free_points(5)), 0)
        finally:
            if previous is not None:
                os.environ['AHE_F58_GEODESIC'] = previous

    def test_warmup_hook_can_be_disabled_for_ablation(self):
        allocator = AHEMRTAv3Allocator()
        env = dict(AHE_F58_GEODESIC=os.environ.get('AHE_F58_GEODESIC'),
                   AHE_WARMUP=os.environ.get('AHE_WARMUP'))
        os.environ['AHE_F58_GEODESIC'] = '1'
        os.environ['AHE_WARMUP'] = '0'
        try:
            self.assertEqual(allocator.warmup(_free_points(5)), 0)
        finally:
            for key, value in env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == '__main__':
    unittest.main()
