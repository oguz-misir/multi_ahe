#!/usr/bin/env python3
"""
Phase 10 — Layer 3: Statistical analysis of experiment results.

Outputs:
  results/reports/statistical_tables.md
    Table S1: Descriptive statistics (mean ± std, median, 95% CI)
    Table S2: Normality tests (Shapiro-Wilk)
    Table S3: Pairwise p-values (ANOVA/Kruskal-Wallis + Dunn/Tukey HSD)
    Table S4: Effect sizes (Cohen's d or Cliff's delta)

Usage:
    python3 scripts/statistical_analysis.py \
        --processed-dir results/processed/ \
        --output results/reports/statistical_tables.md \
        --group-by strategy scenario
"""

import argparse
import sys
from pathlib import Path
from itertools import combinations
from typing import Optional

import numpy as np
import pandas as pd

# Optional scipy/pingouin imports — gracefully degrade if unavailable
try:
    from scipy import stats as scipy_stats
    from scipy.stats import shapiro, f_oneway, kruskal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    HAS_TUKEY = True
except ImportError:
    HAS_TUKEY = False

try:
    import scikit_posthocs as sp
    HAS_DUNN = True
except ImportError:
    HAS_DUNN = False

METRICS = [
    "task_completion_rate",
    "makespan_s",
    "average_task_delay",
    "deadline_violation_rate",
    "workload_balance",
    "failure_recovery_time",
    "allocation_instability",
    "mean_decision_latency_ms",
]

METHOD_ORDER = [
    "greedy_nearest", "deadline_aware", "auction_based", "static_weighted",
    "big_mrta", "rostam_ea", "consensus_dbta",
    "ahe_no_dominance", "ahe_no_cooperation_suppression",
    "ahe_no_event_replanning", "ahe_fixed_context",
    "full_ahe_mrta",
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


def ci95(values: np.ndarray) -> float:
    n = len(values)
    if n < 2:
        return float("nan")
    return 1.96 * np.std(values, ddof=1) / np.sqrt(n)


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    pooled_std = np.sqrt(((na - 1) * np.var(a, ddof=1) + (nb - 1) * np.var(b, ddof=1)) / (na + nb - 2))
    if pooled_std == 0:
        return 0.0
    return (np.mean(a) - np.mean(b)) / pooled_std


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    greater = sum(ai > bi for ai in a for bi in b)
    less = sum(ai < bi for ai in a for bi in b)
    return (greater - less) / (len(a) * len(b))


def table_s1(df: pd.DataFrame, metrics: list, methods: list) -> str:
    lines = ["## Table S1 — Descriptive Statistics\n"]
    lines.append("Mean ± Std, Median, and 95% CI per metric per strategy (all scenarios combined).\n")

    for metric in metrics:
        if metric not in df.columns:
            continue
        lines.append(f"\n### {metric.replace('_', ' ').title()}\n")
        header = "| Method | N | Mean | Std | Median | 95% CI |"
        sep    = "|--------|---|------|-----|--------|--------|"
        lines += [header, sep]
        for m in methods:
            vals = df[df["strategy"] == m][metric].dropna().values
            if len(vals) == 0:
                lines.append(f"| {METHOD_LABELS.get(m, m)} | 0 | — | — | — | — |")
            else:
                lines.append(
                    f"| {METHOD_LABELS.get(m, m)} | {len(vals)} "
                    f"| {np.mean(vals):.4f} | {np.std(vals, ddof=1):.4f} "
                    f"| {np.median(vals):.4f} | ±{ci95(vals):.4f} |"
                )
    return "\n".join(lines)


def table_s2(df: pd.DataFrame, metrics: list, methods: list) -> str:
    lines = ["## Table S2 — Normality Tests (Shapiro-Wilk)\n"]
    lines.append("p < 0.05 → reject normality assumption.\n")

    if not HAS_SCIPY:
        return "\n".join(lines) + "\n> scipy not available — skipped.\n"

    for metric in metrics:
        if metric not in df.columns:
            continue
        lines.append(f"\n### {metric.replace('_', ' ').title()}\n")
        header = "| Method | N | W-stat | p-value | Normal? |"
        sep    = "|--------|---|--------|---------|---------|"
        lines += [header, sep]
        for m in methods:
            vals = df[df["strategy"] == m][metric].dropna().values
            if len(vals) < 3:
                lines.append(f"| {METHOD_LABELS.get(m, m)} | {len(vals)} | N/A | N/A | N/A (n<3) |")
                continue
            try:
                w, p = shapiro(vals)
                normal = "Yes" if p >= 0.05 else "**No**"
                lines.append(f"| {METHOD_LABELS.get(m, m)} | {len(vals)} | {w:.4f} | {p:.4f} | {normal} |")
            except Exception as e:
                lines.append(f"| {METHOD_LABELS.get(m, m)} | {len(vals)} | ERR | ERR | {e} |")
    return "\n".join(lines)


def table_s3(df: pd.DataFrame, metrics: list, methods: list) -> str:
    lines = ["## Table S3 — Pairwise p-values\n"]
    lines.append(
        "Strategy with n≥3 samples tested. If all groups normal (S2) → ANOVA + Tukey HSD; "
        "else Kruskal-Wallis + Dunn post-hoc. "
        "Bold p < 0.05.\n"
    )

    if not HAS_SCIPY:
        return "\n".join(lines) + "\n> scipy not available — skipped.\n"

    for metric in metrics:
        if metric not in df.columns:
            continue
        groups = {m: df[df["strategy"] == m][metric].dropna().values
                  for m in methods if m in df["strategy"].unique()}
        valid = {m: v for m, v in groups.items() if len(v) >= 3}
        if len(valid) < 2:
            lines.append(f"\n### {metric.replace('_', ' ').title()}\n")
            lines.append("> Insufficient data for testing.\n")
            continue

        all_normal = all(shapiro(v)[1] >= 0.05 for v in valid.values() if len(v) >= 3)

        if all_normal and HAS_TUKEY:
            lines.append(f"\n### {metric.replace('_', ' ').title()} (ANOVA + Tukey HSD)\n")
            try:
                long_vals = np.concatenate(list(valid.values()))
                long_grps = np.concatenate([[m] * len(v) for m, v in valid.items()])
                tukey = pairwise_tukeyhsd(long_vals, long_grps, alpha=0.05)
                lines.append("```")
                lines.append(str(tukey.summary()))
                lines.append("```")
            except Exception as e:
                lines.append(f"> Tukey HSD failed: {e}")
        else:
            try:
                stat, kw_p = kruskal(*valid.values())
                lines.append(f"\n### {metric.replace('_', ' ').title()} "
                              f"(Kruskal-Wallis H={stat:.3f}, p={kw_p:.4f})\n")
            except Exception as e:
                lines.append(f"\n### {metric.replace('_', ' ').title()}\n")
                lines.append(f"> Kruskal-Wallis failed: {e}\n")
                continue

            if HAS_DUNN:
                try:
                    long_vals = np.concatenate(list(valid.values()))
                    long_grps = np.concatenate([[m] * len(v) for m, v in valid.items()])
                    dunn_df = sp.posthoc_dunn(
                        pd.DataFrame({"val": long_vals, "grp": long_grps}),
                        val_col="val", group_col="grp", p_adjust="bonferroni"
                    )
                    lines.append("\nDunn post-hoc p-values (Bonferroni):\n")
                    lines.append("| | " + " | ".join(METHOD_LABELS.get(m, m) for m in dunn_df.columns) + " |")
                    lines.append("|---|" + "|".join(["---"] * len(dunn_df.columns)) + "|")
                    for row_m in dunn_df.index:
                        row_lbl = METHOD_LABELS.get(row_m, row_m)
                        cells = []
                        for col_m in dunn_df.columns:
                            p = dunn_df.loc[row_m, col_m]
                            p_str = f"**{p:.3f}**" if p < 0.05 else f"{p:.3f}"
                            cells.append(p_str)
                        lines.append(f"| {row_lbl} | " + " | ".join(cells) + " |")
                except Exception as e:
                    lines.append(f"> Dunn post-hoc failed: {e}")
            else:
                # Manual pairwise Mann-Whitney
                lines.append("\nPairwise Mann-Whitney U p-values (no Dunn available):\n")
                m_list = list(valid.keys())
                header = "| | " + " | ".join(METHOD_LABELS.get(m, m) for m in m_list) + " |"
                sep = "|---|" + "|".join(["---"] * len(m_list)) + "|"
                lines += [header, sep]
                for m1 in m_list:
                    cells = []
                    for m2 in m_list:
                        if m1 == m2:
                            cells.append("—")
                        else:
                            try:
                                _, p = scipy_stats.mannwhitneyu(valid[m1], valid[m2],
                                                                alternative="two-sided")
                                cells.append(f"**{p:.3f}**" if p < 0.05 else f"{p:.3f}")
                            except Exception:
                                cells.append("N/A")
                    lines.append(f"| {METHOD_LABELS.get(m1, m1)} | " + " | ".join(cells) + " |")

    return "\n".join(lines)


def table_s4(df: pd.DataFrame, metrics: list, methods: list) -> str:
    lines = ["## Table S4 — Effect Sizes\n"]
    lines.append(
        "Cohen's d (normal data) or Cliff's delta (non-normal) comparing each baseline "
        "against the proposed method (AHE-MRTA\\*).\n"
    )
    lines.append("Interpretation: small |d|<0.5, medium 0.5≤|d|<0.8, large |d|≥0.8\n")

    proposed_label = "full_ahe_mrta"
    if proposed_label not in df["strategy"].unique():
        return "\n".join(lines) + "\n> Proposed method not found in data.\n"

    proposed_vals_all = {}
    for metric in metrics:
        if metric in df.columns:
            proposed_vals_all[metric] = df[df["strategy"] == proposed_label][metric].dropna().values

    for metric in metrics:
        if metric not in df.columns or metric not in proposed_vals_all:
            continue
        prop = proposed_vals_all[metric]
        if len(prop) < 2:
            continue

        lines.append(f"\n### {metric.replace('_', ' ').title()}\n")
        header = "| vs AHE-MRTA* | N | Effect Size | Type | Interpretation |"
        sep    = "|---|---|---|---|---|"
        lines += [header, sep]

        for m in methods:
            if m == proposed_label:
                continue
            vals = df[df["strategy"] == m][metric].dropna().values
            if len(vals) < 2:
                continue

            normal = False
            if HAS_SCIPY and len(vals) >= 3 and len(prop) >= 3:
                try:
                    normal = (shapiro(vals)[1] >= 0.05 and shapiro(prop)[1] >= 0.05)
                except Exception:
                    pass

            if normal:
                eff = cohens_d(prop, vals)
                eff_type = "Cohen's d"
            else:
                eff = cliffs_delta(prop, vals)
                eff_type = "Cliff's δ"

            if np.isnan(eff):
                interp = "N/A"
            elif abs(eff) < 0.2:
                interp = "negligible"
            elif abs(eff) < 0.5:
                interp = "small"
            elif abs(eff) < 0.8:
                interp = "medium"
            else:
                interp = "**large**"

            sign = "+" if eff > 0 else ""
            lines.append(
                f"| {METHOD_LABELS.get(m, m)} | {len(vals)} "
                f"| {sign}{eff:.3f} | {eff_type} | {interp} |"
            )

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Statistical analysis of AHE-MRTA experiments.")
    parser.add_argument("--processed-dir", default="results/processed")
    parser.add_argument("--output", default="results/reports/statistical_tables.md")
    parser.add_argument("--group-by", nargs="+", default=["strategy", "scenario"])
    args = parser.parse_args()

    processed_dir = Path(args.processed_dir)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    csv_path = processed_dir / "all_summary.csv"
    if not csv_path.exists():
        print(f"[WARN] {csv_path} not found. Writing placeholder report.")
        with open(out_path, "w") as f:
            f.write("# AHE-MRTA Statistical Analysis\n\n")
            f.write("> No experiment data found. Run experiments and consolidate first.\n")
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print("[WARN] all_summary.csv is empty.")

    present_metrics = [m for m in METRICS if m in df.columns]
    available_methods = [m for m in METHOD_ORDER if m in df.get("strategy", pd.Series(dtype=str)).unique()]

    if not HAS_SCIPY:
        print("[WARN] scipy not installed — statistical tests will be skipped.")

    sections = [
        "# AHE-MRTA Statistical Analysis Report\n",
        f"Generated from: `{csv_path}`\n",
        f"Strategies found: {', '.join(available_methods) or 'none'}\n",
        f"Metrics analysed: {', '.join(present_metrics) or 'none'}\n",
        "---\n",
        table_s1(df, present_metrics, available_methods),
        "\n---\n",
        table_s2(df, present_metrics, available_methods),
        "\n---\n",
        table_s3(df, present_metrics, available_methods),
        "\n---\n",
        table_s4(df, present_metrics, available_methods),
    ]

    with open(out_path, "w") as f:
        f.write("\n".join(sections))

    print(f"[OK] Statistical tables written to {out_path}")


if __name__ == "__main__":
    main()
