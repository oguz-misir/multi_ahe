#!/usr/bin/env python3
"""Historical sweep for rejected F53 exact-completion fairness.

The active reference is F45.  Use ``validate_f45_allocation.py`` for current
Nav2-independent evidence; this file remains only to reproduce the ablation.

The canonical allocator receives exact per-robot completion counters from the
execution layer.  F53 gives an under-served robot a bounded bonus only when:
  * the task is new (never an incumbent, so fairness cannot create churn),
  * the robot is healthy, and
  * its predicted arrival is within a small window of the fastest candidate.

This script patches only class constants and never writes result CSV files.
Config syntax: COST/SECONDS/SLACK/ANTI_IDLE(0|1)/ANTI_SLACK_M, comma separated.
Example:
  python3 scripts/exp_fairness.py 60 0/0/15/1/0.5,0.03/3/10/1/1.0
"""

import sys

sys.path.insert(0, 'scripts')
import simulate_and_tune as S
from m_ahe_task_allocator.baselines import ahe_variants as AV


SCENARIOS = ['robot_failure', 'mixed_stress', 'deadline_pressure']
BASELINES = ['big_mrta', 'rostam_ea', 'consensus_dbta']
SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 60
RAW_CONFIGS = (sys.argv[2] if len(sys.argv) > 2
               else '0/0/15/1/0.5,0/0/15/1/1.0,0.03/3/10/1/0.5')
CONFIGS = [tuple(float(v) for v in item.split('/'))
           for item in RAW_CONFIGS.split(',')]
AHE_ONLY = '--ahe-only' in sys.argv[3:]
if '--seed-start' in sys.argv:
    _idx = sys.argv.index('--seed-start')
    SEED_START = int(sys.argv[_idx + 1])
else:
    SEED_START = 1
R, T = 5, 25


def benchmark_ahe(cost: float, seconds: float, slack: float, anti_idle: float,
                  anti_slack: float):
    attrs = {
        'FAIR_COMPLETION_COST': cost,
        'FAIR_COMPLETION_SECONDS': seconds,
        'FAIR_ARRIVAL_SLACK_S': slack,
        'F53_FAIR_ANTI_IDLE': bool(anti_idle),
        'FAIR_ANTI_IDLE_SLACK_M': anti_slack,
    }
    old = {key: getattr(AV.AHEMRTAv3Allocator, key) for key in attrs}
    for key, value in attrs.items():
        setattr(AV.AHEMRTAv3Allocator, key, value)
    try:
        return {
            sc: S.benchmark(['ahe_mrta_v3'], sc, SEEDS,
                            n_robots=R, n_tasks=T,
                            seed_start=SEED_START)['ahe_mrta_v3']
            for sc in SCENARIOS
        }
    finally:
        for key, value in old.items():
            setattr(AV.AHEMRTAv3Allocator, key, value)


def baseline_reference():
    return {
        sc: S.benchmark(BASELINES, sc, SEEDS, n_robots=R, n_tasks=T,
                        seed_start=SEED_START)
        for sc in SCENARIOS
    }


def line(sc, ahe, base):
    best_wb = (max(base[b]['workload_balance'] for b in BASELINES)
               if base else None)
    wb_ref = f"[{best_wb:.3f}]" if best_wb is not None else ''
    return (
        f"  {sc:<18} Fit={ahe['alloc_fitness']:.3f} "
        f"WLB={ahe['workload_balance']:.3f}{wb_ref} "
        f"active={ahe['workload_balance_active']:.3f} "
        f"CR={ahe['completion_rate']:.3f} Delay={ahe['avg_delay']:.1f} "
        f"DVR={ahe['deadline_violation_rate']:.3f} "
        f"Dist={ahe['total_distance']:.1f} "
        f"Churn={ahe['instability']:.3f} Lat={ahe['mean_decision_latency_ms']:.3f}ms"
    )


def main():
    base = {} if AHE_ONLY else baseline_reference()
    configs = [(0.0, 0.0, 15.0, 0.0, 1.0)] + CONFIGS
    print(f'seeds={SEED_START}..{SEED_START + SEEDS - 1}; '
          'config=COST/SECONDS/SLACK/ANTI_IDLE/ANTI_SLACK_M; '
          'WLB=all-robot Jain [best baseline], active=serviceable-robot Jain')
    for cost, seconds, slack, anti_idle, anti_slack in configs:
        out = benchmark_ahe(cost, seconds, slack, anti_idle, anti_slack)
        label = ('CURRENT' if cost == seconds == anti_idle == 0.0
                 else f'{cost:g}/{seconds:g}/{slack:g}/{anti_idle:g}/{anti_slack:g}')
        print(f'\n== {label} ==')
        for sc in SCENARIOS:
            print(line(sc, out[sc], base.get(sc)))


if __name__ == '__main__':
    main()
