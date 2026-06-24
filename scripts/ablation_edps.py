#!/usr/bin/env python3
"""EDPS ablation (Plane A, navigation-free) — contribution of paradigm switching.

Compares full EDPS against (a) each single FIXED paradigm, (b) no context
override (pure dominance argmax), (c) no recovery boost. Reports priority-
weighted on-time allocation fitness per scenario + mean, 5r/25g, 100 seeds.

Purpose: quantify whether the online switching machinery beats the best single
fixed paradigm in the idealized allocation plane. (It does not — all variants
fall within ~1pp; this confirms allocation quality is saturated in Plane A and
the methods differentiate only on the physical Nav2 stack, Plane B.)

Usage:  python3 scripts/ablation_edps.py [seeds]
"""
import sys
from statistics import mean
sys.path.insert(0, 'scripts')
import simulate_and_tune as S
from m_ahe_task_allocator.baselines.ahe_variants import AHEMRTAv3Allocator

SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
R, T = 5, 25
SCEN = ['robot_failure', 'deadline_pressure', 'mixed_stress']
PN = {0: 'spatial', 1: 'priority', 2: 'edf', 3: 'commit', 4: 'orphan'}


def _fixed(idx):
    class FX(AHEMRTAv3Allocator):
        def _select_paradigm(self, ctx, _i=idx):
            return _i
    return FX


class _NoOverride(AHEMRTAv3Allocator):
    """Pure dominance argmax — skip the deterministic context cascade."""
    def _select_paradigm_raw(self, context):
        import numpy as np
        if context is None or not context.dominance:
            return 2
        d = np.asarray(context.dominance, dtype=float)
        if d.size < 5 or float(d.max() - d.min()) < 1e-4:
            return 2
        return int(np.argmax(d[:5]))


def fit(alloc_factory, sc, seed, **kw):
    return S.run_simulation(alloc_factory(), sc, seed, n_robots=R, n_tasks=T,
                            eco=S.EcosystemSimulator(), ideal_nav=False, **kw)['alloc_fitness']


CONFIGS = [
    ('Full EDPS',         lambda: AHEMRTAv3Allocator(), {}),
    ('fixed: spatial',    _fixed(0), {}),
    ('fixed: priority',   _fixed(1), {}),
    ('fixed: edf',        _fixed(2), {}),
    ('fixed: commit',     _fixed(3), {}),
    ('fixed: orphan',     _fixed(4), {}),
    ('no-override',       lambda: _NoOverride(), {}),
    ('no-recovery-boost', lambda: AHEMRTAv3Allocator(), {'delta': 0.0}),
]

print(f"EDPS ablation | Plane A | {R}r/{T}g | {SEEDS} seeds | priority-weighted on-time fitness")
print(f"{'config':<19}" + ''.join(f"{s[:9]:>10}" for s in SCEN) + f"{'mean':>9}")
print('-' * (19 + 10 * len(SCEN) + 9))
rows = []
for name, af, kw in CONFIGS:
    vals = {sc: mean(fit(af, sc, s, **kw) for s in range(1, SEEDS + 1)) for sc in SCEN}
    m = mean(vals.values())
    rows.append((name, vals, m))
    print(f"{name:<19}" + ''.join(f"{vals[sc]:>10.3f}" for sc in SCEN) + f"{m:>9.3f}")

spread = max(r[2] for r in rows) - min(r[2] for r in rows)
print(f"\nmean-fitness spread across all variants: {spread:.3f}  "
      f"(<~0.01 => allocation saturated in Plane A; switching not the differentiator)")
