#!/usr/bin/env python3
"""
Phase 10 — Layer 3: Generate summary report from figures and statistical tables.

Usage:
    python3 scripts/report_generator.py \
        --processed-dir results/processed/ \
        --figures-dir results/paper_figures/ \
        --stats results/reports/statistical_tables.md \
        --output results/reports/summary_report.md
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

MANDATORY_FIGS = [
    ("system_overview.png",                  "Fig. 1 — System Architecture"),
    ("adaptive_ecosystem_mechanism.png",      "Fig. 2 — AHE Mechanism"),
    ("baseline_comparison_multi_metric.png",  "Fig. 3 — Baseline Comparison"),
    ("ablation_comparison.png",              "Fig. 4 — Ablation Study"),
    ("dominance_recovery_panel.png",         "Fig. 5 — Dominance & Recovery"),
    ("communication_scalability_panel.png",  "Fig. 6 — Communication & Scalability"),
]

OPTIONAL_FIGS = [
    ("dominance_evolution.png",     "Dominance Evolution (supplementary)"),
    ("failure_recovery.png",        "Failure Recovery (supplementary)"),
    ("communication_footprint.png", "Communication Footprint (supplementary)"),
    ("allocation_instability.png",  "Allocation Instability (supplementary)"),
    ("decision_latency.png",        "Decision Latency (supplementary)"),
    ("task_completion_timeline.png","Task Completion Timeline (supplementary)"),
    ("workload_distribution.png",   "Workload Distribution (supplementary)"),
    ("compact_scalability_sanity.png", "Compact Scalability (optional)"),
]

METHOD_LABELS = {
    "greedy_nearest":               "Greedy",
    "deadline_aware":               "EDF",
    "auction_based":                "Auction",
    "static_weighted":              "SW",
    "big_mrta":                     "BiG-MRTA",
    "rostam_ea":                    "RoSTAM-EA",
    "consensus_dbta":               "Cons-DBTA",
    "ahe_no_dominance":             "AHE-NoD",
    "ahe_no_cooperation_suppression": "AHE-NoCS",
    "ahe_no_event_replanning":      "AHE-NoER",
    "ahe_fixed_context":            "AHE-FC",
    "full_ahe_mrta":                "AHE-MRTA*",
}

HIGHER_BETTER = {"task_completion_rate", "workload_balance"}
METRICS = [
    "task_completion_rate", "makespan_s", "average_task_delay",
    "deadline_violation_rate", "workload_balance", "failure_recovery_time",
    "allocation_instability", "mean_decision_latency_ms",
]


def figure_checklist(figures_dir: Path) -> str:
    lines = ["## Figure Checklist\n"]
    lines.append("| Status | File | Label |")
    lines.append("|--------|------|-------|")

    for fname, label in MANDATORY_FIGS:
        exists = (figures_dir / fname).exists()
        status = "✅ Ready" if exists else "❌ Missing"
        lines.append(f"| {status} | `{fname}` | **{label}** (mandatory) |")

    for fname, label in OPTIONAL_FIGS:
        exists = (figures_dir / fname).exists()
        status = "✅ Ready" if exists else "○ Not yet"
        lines.append(f"| {status} | `{fname}` | {label} |")

    return "\n".join(lines)


def key_results_table(processed_dir: Path) -> str:
    csv_path = processed_dir / "all_summary.csv"
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return "## Key Results\n\n> No experiment data found yet.\n"

    df = pd.read_csv(csv_path)
    if df.empty or "strategy" not in df.columns:
        return "## Key Results\n\n> all_summary.csv is empty or missing required columns.\n"

    methods_ordered = [m for m in [
        "greedy_nearest", "deadline_aware", "auction_based", "static_weighted",
        "big_mrta", "rostam_ea", "consensus_dbta",
        "ahe_no_dominance", "ahe_no_cooperation_suppression",
        "ahe_no_event_replanning", "ahe_fixed_context",
        "full_ahe_mrta",
    ] if m in df["strategy"].unique()]

    present = [m for m in METRICS if m in df.columns]
    if not present:
        return "## Key Results\n\n> No metric columns found in all_summary.csv.\n"

    lines = ["## Key Results (mean across all seeds and scenarios)\n"]
    header = "| Method | " + " | ".join(m.replace("_", " ").title() for m in present) + " |"
    sep = "|---|" + "|".join(["---"] * len(present)) + "|"
    lines += [header, sep]

    for m in methods_ordered:
        sub = df[df["strategy"] == m]
        cells = []
        for metric in present:
            if metric not in sub.columns:
                cells.append("—")
            else:
                vals = sub[metric].dropna()
                if vals.empty:
                    cells.append("—")
                else:
                    mean = vals.mean()
                    std = vals.std()
                    cells.append(f"{mean:.3f}±{std:.3f}" if len(vals) > 1 else f"{mean:.3f}")
        lines.append(f"| {METHOD_LABELS.get(m, m)} | " + " | ".join(cells) + " |")

    # Highlight directions
    lines.append("\n*Higher is better: task_completion_rate, workload_balance.*")
    lines.append("*Lower is better: makespan_s, average_task_delay, deadline_violation_rate, "
                 "failure_recovery_time, allocation_instability, mean_decision_latency_ms.*")

    return "\n".join(lines)


def experiment_count_summary(processed_dir: Path) -> str:
    csv_path = processed_dir / "all_summary.csv"
    if not csv_path.exists():
        return "## Experiment Coverage\n\n> No data.\n"

    df = pd.read_csv(csv_path)
    if df.empty:
        return "## Experiment Coverage\n\n> Empty dataset.\n"

    lines = ["## Experiment Coverage\n"]
    total = len(df)
    lines.append(f"Total experiment runs: **{total}**\n")

    if "strategy" in df.columns:
        strat_counts = df["strategy"].value_counts()
        lines.append("| Strategy | Runs |")
        lines.append("|----------|------|")
        for strat, cnt in strat_counts.items():
            lines.append(f"| {METHOD_LABELS.get(strat, strat)} | {cnt} |")

    if "scenario" in df.columns:
        lines.append("\n| Scenario | Runs |")
        lines.append("|----------|------|")
        for scen, cnt in df["scenario"].value_counts().items():
            lines.append(f"| {scen} | {cnt} |")

    if "seed" in df.columns:
        seeds = sorted(df["seed"].unique())
        lines.append(f"\nSeeds used: {seeds}")

    if "robot_count" in df.columns and "target_count" in df.columns:
        scales = df.groupby(["robot_count", "target_count"]).size().reset_index(name="runs")
        lines.append("\n| Scale (R/T) | Runs |")
        lines.append("|-------------|------|")
        for _, row in scales.iterrows():
            lines.append(f"| {int(row.robot_count)}R/{int(row.target_count)}T | {row.runs} |")

    return "\n".join(lines)


def read_stats_excerpt(stats_path: Path) -> str:
    if not stats_path.exists():
        return "## Statistical Analysis\n\n> statistical_tables.md not found yet.\n"
    text = stats_path.read_text()
    # include first 80 lines as excerpt
    lines = text.split("\n")[:80]
    return "## Statistical Analysis (excerpt)\n\n" + "\n".join(lines) + "\n\n_(Full tables in statistical_tables.md)_\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 10 summary report.")
    parser.add_argument("--processed-dir", default="results/processed")
    parser.add_argument("--figures-dir", default="results/paper_figures")
    parser.add_argument("--stats", default="results/reports/statistical_tables.md")
    parser.add_argument("--output", default="results/reports/summary_report.md")
    args = parser.parse_args()

    processed_dir = Path(args.processed_dir)
    figures_dir = Path(args.figures_dir)
    stats_path = Path(args.stats)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    sections = [
        f"# AHE-MRTA Experiment Report\n",
        f"Generated: {now}  |  Target: IEEE RA-L (Q1)\n",
        "---\n",
        experiment_count_summary(processed_dir),
        "\n---\n",
        key_results_table(processed_dir),
        "\n---\n",
        figure_checklist(figures_dir),
        "\n---\n",
        read_stats_excerpt(stats_path),
        "\n---\n",
        "## Mandatory Output Checklist\n",
        "| Item | Status |",
        "|------|--------|",
        f"| results/paper_figures/system_overview.png | {'✅' if (figures_dir / 'system_overview.png').exists() else '❌'} |",
        f"| results/paper_figures/adaptive_ecosystem_mechanism.png | {'✅' if (figures_dir / 'adaptive_ecosystem_mechanism.png').exists() else '❌'} |",
        f"| results/paper_figures/baseline_comparison_multi_metric.png | {'✅' if (figures_dir / 'baseline_comparison_multi_metric.png').exists() else '❌'} |",
        f"| results/paper_figures/ablation_comparison.png | {'✅' if (figures_dir / 'ablation_comparison.png').exists() else '❌'} |",
        f"| results/paper_figures/dominance_recovery_panel.png | {'✅' if (figures_dir / 'dominance_recovery_panel.png').exists() else '❌'} |",
        f"| results/paper_figures/communication_scalability_panel.png | {'✅' if (figures_dir / 'communication_scalability_panel.png').exists() else '❌'} |",
        f"| results/reports/statistical_tables.md | {'✅' if stats_path.exists() else '❌'} |",
        f"| results/reports/summary_report.md | ✅ (this file) |",
        "",
    ]

    with open(out_path, "w") as f:
        f.write("\n".join(sections))

    print(f"[OK] Summary report written to {out_path}")


if __name__ == "__main__":
    main()
