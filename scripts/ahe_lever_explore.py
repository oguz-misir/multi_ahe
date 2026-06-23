#!/usr/bin/env python3
"""AHE lever exploration (Plane A / sim, Nav2-independent).

Patches AHEMRTAv3Allocator class attributes / W0_V3 weight vector and measures
the full per-metric impact (fitness, delay, DVR, WLBal) vs the BEST baseline per
metric, across all three scenarios. Prints whether AHE meets a >=margin% lead.

Non-destructive: restores sim_fitness.csv is NOT touched here (benchmark() does
not write the CSV; only main() does). We import benchmark() directly.
"""
import sys, argparse, importlib
import numpy as np
sys.path.insert(0, 'scripts')
import simulate_and_tune as S
from m_ahe_task_allocator.baselines import ahe_variants as AV

SCENARIOS = ['robot_failure', 'mixed_stress', 'deadline_pressure']
BASELINES = ['big_mrta', 'rostam_ea', 'consensus_dbta']
# metric key -> (label, higher_is_better)
METRICS = {
    'alloc_fitness':            ('Fit',   True),
    'avg_delay':                ('Delay', False),
    'deadline_violation_rate':  ('DVR',   False),
    'workload_balance':         ('WLBal', True),
}


def _install_quadratic_load(coef):
    """Wrap _cost to add a distance-gated quadratic load penalty.

    Principled WLBal lever (NOT F45): the penalty is proportional to the SQUARE
    of the robot's current queue length, scaled small (coef) so it only breaks
    near-cost ties between feasible robots — it never pulls a task to a far robot
    (that was F45's makespan-breaking mistake). Returns the original _cost.
    """
    orig_cost = AV.AHEMRTAv3Allocator._cost

    def _cost_lb(self, robot, task, task_map, queues, weights,
                 current_time, mean_q, cap, robot_cap):
        c = orig_cost(self, robot, task, task_map, queues, weights,
                      current_time, mean_q, cap, robot_cap)
        if c >= 1e5:           # infeasible — leave as-is
            return c
        qlen = len(queues[robot.robot_id])
        return c + coef * (qlen * qlen)

    AV.AHEMRTAv3Allocator._cost = _cost_lb
    return orig_cost


def run_config(label, patches, seeds, robots=5, tasks=25, load_coef=0.0):
    """patches: dict of (target, attr) -> value. target 'cls' or 'W0'."""
    # apply patches
    orig = {}
    orig_cost = _install_quadratic_load(load_coef) if load_coef else None
    for (tgt, attr), val in patches.items():
        if tgt == 'W0':
            orig[(tgt, attr)] = list(AV.W0_V3)
            AV.W0_V3[attr] = val          # attr = index
        else:
            orig[(tgt, attr)] = getattr(AV.AHEMRTAv3Allocator, attr)
            setattr(AV.AHEMRTAv3Allocator, attr, val)
    try:
        rows = {}
        for scen in SCENARIOS:
            summ = S.benchmark(['ahe_mrta_v3'] + BASELINES, scen, seeds,
                               n_robots=robots, n_tasks=tasks)
            rows[scen] = summ
    finally:
        for (tgt, attr), val in orig.items():
            if tgt == 'W0':
                AV.W0_V3[:] = val
            else:
                setattr(AV.AHEMRTAv3Allocator, attr, val)
        if orig_cost is not None:
            AV.AHEMRTAv3Allocator._cost = orig_cost
    return rows


def report(label, rows, margin=0.05):
    print(f"\n{'='*78}\n  CONFIG: {label}   (margin target = {margin*100:.0f}%)\n{'='*78}")
    for scen in SCENARIOS:
        summ = rows[scen]
        ahe = summ['ahe_mrta_v3']
        print(f"-- {scen}")
        for k, (lbl, hib) in METRICS.items():
            av = ahe[k]
            base_vals = {b: summ[b][k] for b in BASELINES}
            best_b = (max if hib else min)(base_vals, key=base_vals.get)
            best_v = base_vals[best_b]
            # advantage of AHE over best baseline (positive = AHE better)
            if hib:
                adv = (av - best_v) / abs(best_v) if best_v else 0.0
            else:
                adv = (best_v - av) / abs(best_v) if best_v else 0.0
            ok = '✓5%' if adv >= margin else ('=' if adv >= -0.005 else 'x')
            print(f"    {lbl:<6} AHE={av:8.3f}  bestBase={best_v:8.3f}({best_b[:4]})  "
                  f"adv={adv*100:+6.1f}%  {ok}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, default=30)
    ap.add_argument('--robots', type=int, default=5)
    ap.add_argument('--tasks', type=int, default=25)
    ap.add_argument('--config', type=str, default='baseline')
    ap.add_argument('--wl', type=float, default=None, help='override W0_V3[3] (w_l)')
    ap.add_argument('--eco-blend', type=float, default=None)
    ap.add_argument('--load-coef', type=float, default=0.0,
                    help='quadratic load tie-break coefficient added to _cost')
    ap.add_argument('--fair-lambda', type=float, default=None,
                    help='FAIR_LAMBDA_S for greedy paths (spatial/battery)')
    args = ap.parse_args()

    patches = {}
    label = args.config
    if args.wl is not None:
        patches[('W0', 3)] = args.wl
        label += f" w_l={args.wl}"
    if args.eco_blend is not None:
        patches[('cls', 'ECO_BLEND_NORMAL')] = args.eco_blend
        label += f" eco_blend={args.eco_blend}"
    if args.fair_lambda is not None:
        patches[('cls', 'FAIR_LAMBDA_S')] = args.fair_lambda
        label += f" fair_lambda={args.fair_lambda}"
    if args.load_coef:
        label += f" load_coef={args.load_coef}"

    rows = run_config(label, patches, args.seeds, args.robots, args.tasks,
                      load_coef=args.load_coef)
    report(label, rows)


if __name__ == '__main__':
    main()
