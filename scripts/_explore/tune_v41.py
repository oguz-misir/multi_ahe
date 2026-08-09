#!/usr/bin/env python3
"""v4.1 iyileştirme paketi (F22-F24) parametre araması.

AHEMRTAv3Allocator sınıf özniteliklerini geçici olarak değiştirip
simulate_and_tune.benchmark ile 3 senaryoda fitness ölçer.
1D süpürmeler → en iyi kombinasyon → 100-seed doğrulama.

Kullanım:
  python3 scripts/tune_v41.py --seeds 50
  python3 scripts/tune_v41.py --validate K=60 DWELL=4 LAMBDA=10 --seeds 100
"""
import argparse
import sys
import os

_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_repo, 'src', 'm_ahe_task_allocator'))
sys.path.insert(0, os.path.join(_repo, 'src', 'm_ahe_ecosystem_manager'))
sys.path.insert(0, os.path.join(_repo, 'scripts'))

import simulate_and_tune as st
from m_ahe_task_allocator.baselines.ahe_variants import AHEMRTAv3Allocator as A

SCENARIOS = ['robot_failure', 'mixed_stress', 'deadline_pressure']

PARAMS = {
    'K':      'ADAPTIVE_SLACK_K',
    'DWELL':  'PARADIGM_DWELL',
    'LAMBDA': 'FAIR_LAMBDA_S',
    'SLACK':  'DVR_SOFT_SLACK',
    'HORIZON': 'URGENT_HORIZON',
}


def evaluate(seeds: int, overrides: dict) -> dict:
    saved = {attr: getattr(A, attr) for attr in PARAMS.values()}
    try:
        for key, val in overrides.items():
            setattr(A, PARAMS[key], val)
        out = {}
        for scen in SCENARIOS:
            s = st.benchmark(['ahe_mrta_v3'], scen, seeds)['ahe_mrta_v3']
            out[scen] = s
        return out
    finally:
        for attr, val in saved.items():
            setattr(A, attr, val)


def report(tag: str, res: dict):
    fits = [res[s]['alloc_fitness'] for s in SCENARIOS]
    avg = sum(fits) / 3
    row = " | ".join(
        f"{s.split('_')[0]}: fit={res[s]['alloc_fitness']:.3f} "
        f"CR={res[s]['completion_rate']:.3f} DVR={res[s]['deadline_violation_rate']:.3f} "
        f"Dly={res[s]['avg_delay']:.0f} In={res[s]['instability']:.1f} "
        f"WLB={res[s]['workload_balance']:.2f}"
        for s in SCENARIOS)
    print(f"{tag:28s} AVG={avg:.4f} || {row}", flush=True)
    return avg


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--seeds', type=int, default=50)
    p.add_argument('--validate', nargs='*', default=None,
                   help='örn: K=60 DWELL=4 LAMBDA=10 — tek konfig, tam metrik')
    args = p.parse_args()

    if args.validate is not None:
        ov = {}
        for item in args.validate:
            k, v = item.split('=')
            ov[k] = float(v) if '.' in v else int(v)
        res = evaluate(args.seeds, ov)
        report(f"VALIDATE {ov}", res)
        return

    print(f"=== 1D süpürmeler ({args.seeds} seed) ===")
    base = evaluate(args.seeds, {})
    base_avg = report("baseline", base)

    sweeps = {
        'K':      [15, 30, 60, 120],
        'DWELL':  [2, 4, 8],
        'LAMBDA': [5, 11, 22],
        'SLACK':  [20, 40],
        'HORIZON': [60],
    }
    best = {}
    for key, vals in sweeps.items():
        best_v, best_avg = None, base_avg
        for v in vals:
            avg = report(f"{key}={v}", evaluate(args.seeds, {key: v}))
            if avg > best_avg + 1e-4:
                best_avg, best_v = avg, v
        if best_v is not None:
            best[key] = best_v
        print(f"  -> {key}: en iyi {best_v if best_v is not None else 'baseline'}")

    if best:
        print(f"\n=== Kombinasyon: {best} ===")
        report(f"COMBO {best}", evaluate(args.seeds, best))


if __name__ == '__main__':
    main()
