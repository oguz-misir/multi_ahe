"""AHE v3.1 vs v3 classic karşılaştırması (300 seed, DVR dahil)."""
import sys, os, math, random
from statistics import mean
from typing import Optional, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'm_ahe_task_allocator'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'm_ahe_ecosystem_manager'))

import importlib.util
_sim_path = os.path.join(os.path.dirname(__file__), 'simulate_and_tune.py')
spec = importlib.util.spec_from_file_location("sim", _sim_path)
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

from m_ahe_task_allocator.baselines.ahe_variants import (
    AHEMRTAv3Allocator, W0_V3
)


class AHEMRTAv3Classic(AHEMRTAv3Allocator):
    """Orijinal v3 parametreleri — iyileştirmelerden önce."""
    AT_NORM = 300.0
    DEADLINE_SLACK = 45.0
    REACHABILITY_THRESHOLD = 1.8
    USE_EDF_ORDER = False

    def _weights_from_context(self, context):
        failure_rate = 0.0
        if context and context.context_vector and len(context.context_vector) > 4:
            failure_rate = float(context.context_vector[4])
        self._failure_active = failure_rate > 0.05
        if context and context.allocation_weights:
            eco_w = list(context.allocation_weights)
            w = [0.5 * a + 0.5 * b for a, b in zip(W0_V3, eco_w)]
        else:
            w = list(W0_V3)
        if self.RECOVERY_TURBO and self._failure_active:
            w = list(w)
            w[0] = min(0.65, w[0] * 1.20)
            w[4] = min(0.20, w[4] + 0.05)
            w[5] = min(0.15, w[5] + 0.03)
        return w

    def name(self):
        return 'ahe_v3_classic'


registry = {
    'ahe_v3.1 (yeni)':    lambda: AHEMRTAv3Allocator(),
    'ahe_v3 (klasik)':    lambda: AHEMRTAv3Classic(),
    'big_mrta':            sim._make_allocators()['big_mrta'],
    'rostam_ea':           sim._make_allocators()['rostam_ea'],
    'consensus_dbta':      sim._make_allocators()['consensus_dbta'],
}

N_SEEDS = 300
print(f"\n{'':=<80}")
print(f"  AHE-MRTA v3.1 (M18+M19+tuning) vs klasik v3 — {N_SEEDS} seed")
print(f"{'':=<80}")
print(f"  {'Senaryo':<20} {'Yöntem':<22} {'CR':>6} {'Delay':>7} {'RecT':>7} {'DVR':>7}")
print(f"  {'-'*70}")

for scenario in ['robot_failure', 'mixed_stress', 'deadline_pressure']:
    for mname, make_fn in registry.items():
        cr_l, delay_l, rect_l, dvr_l = [], [], [], []
        needs_eco = 'ahe' in mname
        for seed in range(1, N_SEEDS + 1):
            alloc = make_fn()
            eco = sim.EcosystemSimulator() if needs_eco else None
            r = sim.run_simulation(alloc, scenario, seed, n_robots=3, n_tasks=15, eco=eco)
            cr_l.append(r['completion_rate'])
            delay_l.append(r['avg_delay'])
            rect_l.append(r['failure_recovery_time'])
            dvr_l.append(r['deadline_violations'] / 15.0)
        rect_v = [x for x in rect_l if x > 0]
        rectime = mean(rect_v) if rect_v else 0.0
        print(f"  {scenario:<20} {mname:<22} {mean(cr_l):6.3f} {mean(delay_l):7.1f} "
              f"{rectime:7.1f} {mean(dvr_l):7.3f}")
    print()
