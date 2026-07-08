#!/usr/bin/env python3
"""Reproducible F45/F58 allocation-only and navigation-proxy validation.

``allocation-only`` uses perfect execution and is the actual Nav2-independent
plane. ``navigation-proxy`` retains the legacy stochastic wall/timeout model as
a separate robustness diagnostic; it must not be presented as pure allocation.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simulate_and_tune as sim  # noqa: E402
from m_ahe_task_allocator.baselines.ahe_variants import (  # noqa: E402
    AHEMRTAv3Allocator,
)


METHODS = ["ahe_mrta_v3", "big_mrta", "rostam_ea", "consensus_dbta"]
SCENARIOS = ["robot_failure", "mixed_stress", "deadline_pressure"]
METRICS = [
    "alloc_fitness", "completion_rate", "avg_delay",
    "deadline_violation_rate", "workload_balance",
    "workload_balance_active", "travel_distance_balance",
    "total_distance", "instability", "mean_decision_latency_ms",
]


def run(args: argparse.Namespace) -> pd.DataFrame:
    ideal_nav = args.mode == "allocation-only"
    old_f53 = AHEMRTAv3Allocator.F53_FAIR_ANTI_IDLE
    old_env = os.environ.get("AHE_FAIR_ANTI_IDLE")
    old_geo = os.environ.get("AHE_F58_GEODESIC")
    old_repair = os.environ.get("AHE_F58_FAIR_REPAIR")
    old_execution_geo = os.environ.get("AHE_SIM_GEODESIC_EXECUTION")
    AHEMRTAv3Allocator.F53_FAIR_ANTI_IDLE = False
    os.environ["AHE_FAIR_ANTI_IDLE"] = "0"
    enabled = "1" if args.variant == "f58" else "0"
    geo = enabled if args.f58_geodesic == "auto" else str(
        int(args.f58_geodesic == "on"))
    repair = enabled if args.f58_fair_repair == "auto" else str(
        int(args.f58_fair_repair == "on"))
    os.environ["AHE_F58_GEODESIC"] = geo
    os.environ["AHE_F58_FAIR_REPAIR"] = repair
    # Measurement ground truth must not change with the candidate feature
    # gate.  Both F45 and F58 execute on the same obstacle-aware path oracle;
    # only the allocator's knowledge/repair differs between variants.
    os.environ["AHE_SIM_GEODESIC_EXECUTION"] = "1"
    rows = []
    try:
        for scenario in SCENARIOS:
            summary = sim.benchmark(
                METHODS, scenario, args.seeds,
                n_robots=args.robots, n_tasks=args.tasks,
                seed_start=args.seed_start, ideal_nav=ideal_nav,
            )
            for method in METHODS:
                row = {
                    "mode": args.mode,
                    "variant": args.variant,
                    "scenario": scenario,
                    "strategy": method,
                    "seed_start": args.seed_start,
                    "n_seeds": args.seeds,
                    "robot_count": args.robots,
                    "task_count": args.tasks,
                }
                row.update({metric: summary[method][metric] for metric in METRICS})
                rows.append(row)
    finally:
        AHEMRTAv3Allocator.F53_FAIR_ANTI_IDLE = old_f53
        if old_env is None:
            os.environ.pop("AHE_FAIR_ANTI_IDLE", None)
        else:
            os.environ["AHE_FAIR_ANTI_IDLE"] = old_env
        for name, value in (("AHE_F58_GEODESIC", old_geo),
                            ("AHE_F58_FAIR_REPAIR", old_repair),
                            ("AHE_SIM_GEODESIC_EXECUTION", old_execution_geo)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    return pd.DataFrame(rows)


def make_report(frame: pd.DataFrame, args: argparse.Namespace) -> str:
    lines = [
        f"# {args.variant.upper()} validation",
        "",
        f"Mode: `{args.mode}`; scale: {args.robots} robots / {args.tasks} tasks; "
        f"seeds: {args.seed_start}--{args.seed_start + args.seeds - 1}.",
        "",
        f"F53 is forced off; F58 P0/P1 is {'on' if args.variant == 'f58' else 'off'}. "
        "Both variants are measured with the same geodesic execution oracle. "
        "In `allocation-only`, navigation always succeeds; "
        "an injected fleet robot failure remains part of failure scenarios.",
        "",
        "| Scenario | Method | Fitness | CR | Delay | DVR | Jain(all) | Jain(active) | Distance Jain | Distance | Churn |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in frame.itertuples(index=False):
        lines.append(
            f"| {row.scenario} | {row.strategy} | {row.alloc_fitness:.3f} | "
            f"{row.completion_rate:.3f} | {row.avg_delay:.1f} | "
            f"{row.deadline_violation_rate:.3f} | {row.workload_balance:.3f} | "
            f"{row.workload_balance_active:.3f} | {row.travel_distance_balance:.3f} | "
            f"{row.total_distance:.1f} | {row.instability:.3f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["allocation-only", "navigation-proxy"],
                        default="allocation-only")
    parser.add_argument("--variant", choices=["f45", "f58"], default="f45")
    parser.add_argument("--f58-geodesic", choices=["auto", "on", "off"],
                        default="auto")
    parser.add_argument("--f58-fair-repair", choices=["auto", "on", "off"],
                        default="auto")
    parser.add_argument("--robots", type=int, default=5)
    parser.add_argument("--tasks", type=int, default=25)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--output-dir", type=Path,
                        default=Path("results/stats/f45_allocation_only"))
    args = parser.parse_args()

    frame = run(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output_dir / "summary.csv", index=False)
    (args.output_dir / "REPORT.md").write_text(
        make_report(frame, args), encoding="utf-8")
    print(frame.to_string(index=False))
    print(f"\nReport: {args.output_dir / 'REPORT.md'}")


if __name__ == "__main__":
    main()
