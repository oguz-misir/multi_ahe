#!/usr/bin/env python3
"""Historical paired validation of rejected AHE v4.7/F53.

Each seed is run twice with identical simulator inputs: historical anti-idle
dispatch (reference) and F53 opportunity-constrained fair backfill (candidate).
Positive ``improvement`` always means better.

F53 is not the active method. Use ``validate_f45_allocation.py`` for current
allocation-only evidence.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate_and_tune import EcosystemSimulator, run_simulation  # noqa: E402
from m_ahe_task_allocator.baselines.ahe_variants import (  # noqa: E402
    AHEMRTAv3Allocator,
)


SCENARIOS = ["robot_failure", "mixed_stress", "deadline_pressure"]
METRICS = {
    "alloc_fitness": True,
    "workload_balance": True,
    "workload_balance_active": True,
    "completion_rate": True,
    "avg_delay": False,
    "deadline_violation_rate": False,
    "total_distance": False,
    "allocation_instability": False,
    "mean_decision_latency_ms": False,
}


def paired_p(values: np.ndarray) -> float:
    if len(values) < 2 or np.allclose(values, 0.0):
        return 1.0
    try:
        return float(wilcoxon(values).pvalue)
    except ValueError:
        return np.nan


def holm_adjust(p_values: pd.Series) -> pd.Series:
    """Holm family-wise correction, preserving the input index."""
    valid = p_values.dropna().sort_values()
    adjusted = pd.Series(np.nan, index=p_values.index, dtype=float)
    running = 0.0
    m = len(valid)
    for rank, (idx, value) in enumerate(valid.items()):
        running = max(running, min(1.0, float(value) * (m - rank)))
        adjusted.loc[idx] = running
    return adjusted


def run(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    records = []
    original_enabled = AHEMRTAv3Allocator.F53_FAIR_ANTI_IDLE
    original_slack = AHEMRTAv3Allocator.FAIR_ANTI_IDLE_SLACK_M
    try:
        AHEMRTAv3Allocator.FAIR_ANTI_IDLE_SLACK_M = args.slack_m
        for scenario in SCENARIOS:
            for seed in range(args.seed_start, args.seed_start + args.seeds):
                for variant, enabled in (("reference", False), ("f53", True)):
                    AHEMRTAv3Allocator.F53_FAIR_ANTI_IDLE = enabled
                    result = run_simulation(
                        AHEMRTAv3Allocator(), scenario, seed,
                        n_robots=args.robots, n_tasks=args.tasks,
                        eco=EcosystemSimulator(),
                    )
                    row = {"scenario": scenario, "seed": seed, "variant": variant}
                    row.update({metric: result[metric] for metric in METRICS})
                    records.append(row)
    finally:
        AHEMRTAv3Allocator.F53_FAIR_ANTI_IDLE = original_enabled
        AHEMRTAv3Allocator.FAIR_ANTI_IDLE_SLACK_M = original_slack

    runs = pd.DataFrame(records)
    rows = []
    rng = np.random.default_rng(53)
    for scenario in SCENARIOS:
        block = runs[runs.scenario == scenario]
        ref = block[block.variant == "reference"].set_index("seed")
        f53 = block[block.variant == "f53"].set_index("seed")
        for metric, higher_is_better in METRICS.items():
            raw_delta = f53[metric] - ref[metric]
            improvement = raw_delta if higher_is_better else -raw_delta
            values = improvement.to_numpy(float)
            means = rng.choice(values, size=(10_000, len(values)), replace=True).mean(axis=1)
            lo, hi = np.quantile(means, [0.025, 0.975])
            rows.append({
                "scenario": scenario,
                "metric": metric,
                "n": len(values),
                "reference_mean": ref[metric].mean(),
                "f53_mean": f53[metric].mean(),
                "raw_delta_mean": raw_delta.mean(),
                "improvement_mean": improvement.mean(),
                "improvement_ci95_low": lo,
                "improvement_ci95_high": hi,
                "wilcoxon_p": paired_p(values),
            })
    summary = pd.DataFrame(rows)
    summary["holm_p"] = holm_adjust(summary["wilcoxon_p"])
    return runs, summary


def report(summary: pd.DataFrame, args: argparse.Namespace) -> str:
    lines = [
        "# F53 Nav2-independent paired validation",
        "",
        f"Scale: {args.robots} robots / {args.tasks} tasks; seeds: "
        f"{args.seed_start}--{args.seed_start + args.seeds - 1}; slack: {args.slack_m:g} m.",
        "Positive improvement means better. Confidence intervals are paired-seed bootstrap intervals; p-values use paired Wilcoxon and Holm correction over the full metric family.",
        "",
        "| Scenario | Metric | Reference | F53 | Improvement | 95% CI | Holm p |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.scenario} | {row.metric} | {row.reference_mean:.5f} | "
            f"{row.f53_mean:.5f} | {row.improvement_mean:+.5f} | "
            f"[{row.improvement_ci95_low:+.5f}, {row.improvement_ci95_high:+.5f}] | "
            f"{row.holm_p:.4g} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robots", type=int, default=5)
    parser.add_argument("--tasks", type=int, default=25)
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=201)
    parser.add_argument("--slack-m", type=float, default=2.0)
    parser.add_argument("--output-dir", type=Path,
                        default=Path("results/stats/f53_sim_holdout"))
    args = parser.parse_args()

    runs, summary = run(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.output_dir / "paired_runs.csv", index=False)
    summary.to_csv(args.output_dir / "metric_summary.csv", index=False)
    (args.output_dir / "REPORT.md").write_text(report(summary, args), encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"\nReport: {args.output_dir / 'REPORT.md'}")


if __name__ == "__main__":
    main()
