#!/usr/bin/env python3
"""Paired A/B for the F59 priority cost factor -- Limitation (xii).

WHAT IS BEING MEASURED
----------------------
``AHEMRTAv3Allocator._cost`` ends with

    cost *= (1 - F59_PRIORITY_COST_SCALE * (priority - 1))

which reads as a discount for urgent work.  A 23k-evaluation replay showed the
shaped cost is negative at that point for every feasible pair (the deadline-
capability bonus dominates the weighted features), so the factor in fact
charges priority 3 about 0.50 MORE than priority 1 -- roughly seven times the
0.07 advantage the additive w_p*P term grants it.  The paper reports the
artefact rather than silently repairing it, and quantifies what it costs with
this A/B.

  arm "on"   default F59_PRIORITY_COST_SCALE = 0.10  (the published campaign)
  arm "off"  AHE_PRIORITY_COST_SCALE=0               (factor disabled)

Same seeds, same scenarios, same everything else, so the arms pair per seed.

WHY THIS SCRIPT EXISTS
----------------------
The numbers in Limitation (xii) came from an ad-hoc run on 2026-07-30 that was
never committed as code, and that run predates the scenario-definition fix
(deadline budgets were U[200,400] s where the design specifies U[36,120] s).
Its outputs -- results/processed/ab_prio_*.csv -- are therefore stale in
exactly the way tab:allocation is: `ab_prio_on.csv` still carries the
superseded proxy values (AHE 0.484 / 0.487 / 0.438).  Scripting it means the
next scenario change can regenerate it instead of stranding it again.

BUILT-IN CORRECTNESS CHECK
--------------------------
The flag is read only by AHEMRTAv3Allocator.__init__, so the three baselines
must come out bit-identical between the arms.  If they do not, the harness --
not the factor -- is what differs, and the run is void.  That is asserted, not
assumed.

Usage:
    python3 scripts/validate_priority_cost_ab.py                 # 500 seeds
    python3 scripts/validate_priority_cost_ab.py --seeds 20      # smoke test
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simulate_and_tune as sim  # noqa: E402

try:
    from scipy.stats import wilcoxon
except ImportError:
    sys.exit("scipy is required: pip install scipy")

METHODS = ["ahe_mrta_v3", "big_mrta", "rostam_ea", "consensus_dbta"]
BASELINES = [m for m in METHODS if m != "ahe_mrta_v3"]
SCENARIOS = ["robot_failure", "mixed_stress", "deadline_pressure"]
PROPOSED = "ahe_mrta_v3"

# The proxy plane must be measured on the geodesic oracle, or the run silently
# falls back to Euclidean distance and is not comparable with anything else in
# the paper.  Set here rather than left to the caller's shell.
PLANE_ENV = {
    "AHE_F58_GEODESIC": "1",
    "AHE_F58_FAIR_REPAIR": "1",
    "AHE_SIM_GEODESIC_EXECUTION": "1",
}


def run_arm(scale, seeds, seed_start, priority_scale):
    """One arm of the A/B. `priority_scale=None` keeps the class default."""
    n_robots, n_tasks = scale
    saved = {k: os.environ.get(k) for k in list(PLANE_ENV) + ["AHE_PRIORITY_COST_SCALE"]}
    os.environ.update(PLANE_ENV)
    if priority_scale is None:
        os.environ.pop("AHE_PRIORITY_COST_SCALE", None)
    else:
        os.environ["AHE_PRIORITY_COST_SCALE"] = str(priority_scale)
    try:
        out = {}
        for scenario in SCENARIOS:
            # Allocators are constructed inside benchmark(), once per seed, and
            # __init__ is where the flag is read -- so setting it here is enough.
            summary, runs = sim.benchmark(
                METHODS, scenario, seeds,
                n_robots=n_robots, n_tasks=n_tasks,
                seed_start=seed_start, ideal_nav=False, retain_runs=True,
            )
            out[scenario] = (summary, runs)
            print(f"  [{scenario}] done", flush=True)
        return out
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def seedwise(arm, scenario, method, seed_start):
    _, runs = arm[scenario]
    return [(seed_start + i, r["alloc_fitness"]) for i, r in enumerate(runs[method])]


def write_outputs(arm, label, scale, seed_start, processed_dir):
    n_robots, n_tasks = scale
    summary_path = processed_dir / f"ab_prio_{label}.csv"
    with open(summary_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "strategy", "fitness_mean", "fitness_std", "n_seeds"])
        for scenario in SCENARIOS:
            summary, runs = arm[scenario]
            for m in METHODS:
                w.writerow([scenario, m, summary[m]["alloc_fitness"],
                            summary[m]["alloc_fitness_std"], len(runs[m])])

    seed_path = processed_dir / f"ab_prio_{label}_seedwise.csv"
    with open(seed_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "strategy", "seed", "robot_count", "task_count",
                    "duration_s", "ideal_nav", "alloc_fitness"])
        for scenario in SCENARIOS:
            for m in METHODS:
                for seed, fit in seedwise(arm, scenario, m, seed_start):
                    w.writerow([scenario, m, seed, n_robots, n_tasks,
                                900.0, False, fit])
    return summary_path, seed_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=500)
    ap.add_argument("--seed-start", type=int, default=1)
    ap.add_argument("--robots", type=int, default=5)
    ap.add_argument("--tasks", type=int, default=25)
    ap.add_argument("--processed-dir", type=Path, default=Path("results/processed"))
    args = ap.parse_args()
    scale = (args.robots, args.tasks)

    print(f"A/B of the F59 priority cost factor: {args.seeds} seeds, "
          f"{args.robots}r/{args.tasks}t, stochastic navigation proxy.\n")

    print('arm "on"  (default scale 0.10):')
    arm_on = run_arm(scale, args.seeds, args.seed_start, None)
    print('\narm "off" (AHE_PRIORITY_COST_SCALE=0):')
    arm_off = run_arm(scale, args.seeds, args.seed_start, 0)

    # ── Correctness check: the flag must not reach the baselines ─────────────
    print("\nbaseline invariance check (the flag touches only AHE):")
    void = False
    for scenario in SCENARIOS:
        for m in BASELINES:
            on = [v for _, v in seedwise(arm_on, scenario, m, args.seed_start)]
            off = [v for _, v in seedwise(arm_off, scenario, m, args.seed_start)]
            same = on == off
            print(f"  {scenario:<20}{m:<16}{'identical' if same else 'DIFFERS'}")
            if not same:
                void = True
    if void:
        sys.exit("\nVOID: a baseline moved between arms. The difference is not the "
                 "priority factor -- fix the harness before reporting anything.")

    # ── Paired test on the proposed method ──────────────────────────────────
    args.processed_dir.mkdir(parents=True, exist_ok=True)
    write_outputs(arm_on, "on", scale, args.seed_start, args.processed_dir)
    write_outputs(arm_off, "off", scale, args.seed_start, args.processed_dir)

    print(f"\n{'=' * 72}")
    print("PAIRED RESULT -- AHE-MRTA priority-weighted proxy fitness")
    print("off minus on; positive = removing the factor helps")
    print("=" * 72)
    print(f"  {'scenario':<20}{'on':>9}{'off':>9}{'delta pp':>11}{'p':>9}")
    quotes = []
    for scenario in SCENARIOS:
        on = [v for _, v in seedwise(arm_on, scenario, PROPOSED, args.seed_start)]
        off = [v for _, v in seedwise(arm_off, scenario, PROPOSED, args.seed_start)]
        mean_on = sum(on) / len(on)
        mean_off = sum(off) / len(off)
        delta_pp = (mean_off - mean_on) * 100.0
        p = 1.0 if on == off else wilcoxon(on, off).pvalue
        print(f"  {scenario:<20}{mean_on:>9.4f}{mean_off:>9.4f}"
              f"{delta_pp:>+11.2f}{p:>9.4f}")
        quotes.append((scenario, delta_pp, p))

    worst = max(abs(d) for _, d, _ in quotes)
    print(f"\n  largest |delta| = {worst:.2f} pp")
    print("\nSentence for Limitation (xii), both languages:")
    print("  a paired {}-seed A/B with the factor removed leaves the "
          "priority-weighted".format(args.seeds))
    print(f"  proxy fitness within {worst:.1f} pp in every scenario (" + "; ".join(
        f"{d:+.2f} pp {s.replace('_', ' ')}, p={p:.2f}" for s, d, p in quotes) + ").")
    print("\nIf any |delta| is now large or any p is small, the limitation's claim")
    print("that the artefact is 'not measurable in the reported outcomes' no longer")
    print("holds and the paragraph has to say so instead.")


if __name__ == "__main__":
    main()
