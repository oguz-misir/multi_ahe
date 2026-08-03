#!/usr/bin/env python3
"""Paired A/B for the geodesic-ETA cost oracle -- the title's second claim.

WHY THIS EXISTS
---------------
The title advertises two contributions: context-triggered overrides and the
geodesic ETA.  The pre-registered closed-loop ablation measures the first --
it varies the paradigm and deletes the override cascade -- but it exports
``AHE_F58_GEODESIC=1`` for *every* arm, so the geodesic oracle is on
everywhere and its own contribution is never isolated.  Section IV even
promises that the "Euclidean, repair-free reference [is] kept for ablation",
an ablation the paper then never reports.

The one existing Euclidean-vs-geodesic comparison
(``results/stats/f58_p1b_same_oracle/{f45,f58}``) is unusable: 20 seeds from
2026-06-30, run under the pre-alignment scenario parameters where deadline
budgets were U[200,400] s.  Fitness saturates at 1.000 in most of its cells,
so it cannot separate anything.

WHAT IS BEING MEASURED
----------------------
Only the allocator's *cost oracle* changes between arms:

  arm "on"   AHE_F58_GEODESIC=1   allocator prices pairs by geodesic ETA
                                  (the published campaign configuration)
  arm "off"  AHE_F58_GEODESIC=0   allocator prices pairs by Euclidean
                                  distance (the F45 reference)

The *execution* oracle is pinned to geodesic in both arms via
``AHE_SIM_GEODESIC_EXECUTION=1``, so both arms are scored against identical
ground truth and the only difference is what the allocator believes distances
to be.  ``simulate_and_tune._execution_distance`` separates the two gates
precisely so this comparison is possible.  Terminal load repair stays on in
both arms, so this isolates the ETA oracle and not the repair step.

BUILT-IN CORRECTNESS CHECK
--------------------------
``AHE_F58_GEODESIC`` is read only by ``AHEMRTAv3Allocator``; no baseline
module references it.  The three baselines must therefore come out
bit-identical between arms.  If one moves, the harness differs rather than the
oracle, and the run is void.  That is asserted, not assumed.

Usage:
    python3 scripts/validate_geodesic_eta_ab.py                # 500 seeds
    python3 scripts/validate_geodesic_eta_ab.py --seeds 20     # smoke test
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

# Held identical in both arms.  The execution oracle is the ground truth both
# arms are scored against; only the allocator's belief about distance moves.
PLANE_ENV = {
    "AHE_SIM_GEODESIC_EXECUTION": "1",
    "AHE_F58_FAIR_REPAIR": "1",
}


def run_arm(scale, seeds, seed_start, geodesic: bool):
    n_robots, n_tasks = scale
    keys = list(PLANE_ENV) + ["AHE_F58_GEODESIC"]
    saved = {k: os.environ.get(k) for k in keys}
    os.environ.update(PLANE_ENV)
    os.environ["AHE_F58_GEODESIC"] = "1" if geodesic else "0"
    try:
        out = {}
        for scenario in SCENARIOS:
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
    summary_path = processed_dir / f"ab_geodesic_{label}.csv"
    with open(summary_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "strategy", "fitness_mean", "fitness_std", "n_seeds"])
        for scenario in SCENARIOS:
            summary, runs = arm[scenario]
            for m in METHODS:
                w.writerow([scenario, m, summary[m]["alloc_fitness"],
                            summary[m]["alloc_fitness_std"], len(runs[m])])

    seed_path = processed_dir / f"ab_geodesic_{label}_seedwise.csv"
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


def cliffs_delta(a, b):
    """P(a>b) - P(a<b), computed without an O(n^2) blowup."""
    sa = sorted(b)
    import bisect
    gt = lt = 0
    n = len(sa)
    for x in a:
        lo = bisect.bisect_left(sa, x)
        hi = bisect.bisect_right(sa, x)
        gt += lo
        lt += n - hi
    tot = len(a) * n
    return (gt - lt) / tot if tot else 0.0


def magnitude(d):
    d = abs(d)
    return ("negligible" if d < 0.147 else "small" if d < 0.33
            else "medium" if d < 0.474 else "large")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=500)
    ap.add_argument("--seed-start", type=int, default=1)
    ap.add_argument("--robots", type=int, default=5)
    ap.add_argument("--tasks", type=int, default=25)
    ap.add_argument("--processed-dir", type=Path, default=Path("results/processed"))
    args = ap.parse_args()
    scale = (args.robots, args.tasks)

    print(f"A/B of the geodesic-ETA cost oracle: {args.seeds} seeds, "
          f"{args.robots}r/{args.tasks}t, stochastic navigation proxy.")
    print("Execution oracle pinned to geodesic in BOTH arms; only the "
          "allocator's cost oracle moves.\n")

    print('arm "on"  (AHE_F58_GEODESIC=1, published configuration):')
    arm_on = run_arm(scale, args.seeds, args.seed_start, True)
    print('\narm "off" (AHE_F58_GEODESIC=0, Euclidean F45 reference):')
    arm_off = run_arm(scale, args.seeds, args.seed_start, False)

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
                 "geodesic oracle -- fix the harness before reporting anything.")

    args.processed_dir.mkdir(parents=True, exist_ok=True)
    write_outputs(arm_on, "on", scale, args.seed_start, args.processed_dir)
    write_outputs(arm_off, "off", scale, args.seed_start, args.processed_dir)

    print(f"\n{'=' * 78}")
    print("PAIRED RESULT -- AHE-MRTA priority-weighted proxy fitness")
    print("geodesic minus Euclidean; positive = the geodesic ETA helps")
    print("=" * 78)
    print(f"  {'scenario':<20}{'geodesic':>10}{'euclidean':>11}"
          f"{'delta pp':>11}{'p':>10}{'cliff':>9}  magnitude")
    rows = []
    for scenario in SCENARIOS:
        on = [v for _, v in seedwise(arm_on, scenario, PROPOSED, args.seed_start)]
        off = [v for _, v in seedwise(arm_off, scenario, PROPOSED, args.seed_start)]
        m_on, m_off = sum(on) / len(on), sum(off) / len(off)
        delta_pp = (m_on - m_off) * 100.0
        p = 1.0 if on == off else wilcoxon(on, off).pvalue
        d = cliffs_delta(on, off)
        print(f"  {scenario:<20}{m_on:>10.4f}{m_off:>11.4f}{delta_pp:>+11.2f}"
              f"{p:>10.4f}{d:>+9.3f}  {magnitude(d)}")
        rows.append((scenario, m_on, m_off, delta_pp, p, d))

    print("\n" + "=" * 78)
    print("HOW TO READ THIS")
    print("=" * 78)
    big = [r for r in rows if r[4] < 0.05 and abs(r[5]) >= 0.147]
    if big:
        print("  The geodesic ETA separates on this plane. The title's second")
        print("  claim is earned; report this table next to tab:ablation and")
        print("  state that the closed-loop arms all held it on.")
    else:
        print("  The geodesic ETA does NOT separate on this plane. The title's")
        print("  second claim is then not supported by an ablation: either")
        print("  narrow the title, or present the oracle as an implementation")
        print("  choice rather than a measured contribution.")
    print("  Either way this plane charges nothing for congestion or recovery")
    print("  latency, so a closed-loop arm could still disagree (Sec. VII-D).")


if __name__ == "__main__":
    main()
