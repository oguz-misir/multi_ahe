#!/usr/bin/env python3
"""
Statistical analysis for AHE-MRTA RA-L paper.

Outputs:
  results/stats/stat_tests.csv           — pairwise Mann-Whitney results
  results/stats/descriptive_stats.csv    — mean ± std per method × scenario × metric
  results/stats/latex_main_table.tex     — Table II: G2 main comparison
  results/stats/latex_ablation_table.tex — Table III: G4 ablation
  results/stats/latex_deadline_table.tex — Table IV: G3 deadline scenario
  results/stats/stat_summary.txt         — human-readable summary

Usage:
    python3 scripts/statistical_analysis.py \
        --processed-dir results/processed/ \
        --output-dir results/stats/
"""

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────

PROPOSED = "full_ahe_mrta"
G2_BASELINES = ["big_mrta", "rostam_ea", "static_weighted", "consensus_dbta"]
G3_BASELINES = ["big_mrta", "static_weighted"]
G4_ABLATIONS = ["ahe_no_dominance", "ahe_no_event_replanning", "ahe_fixed_context"]

METHOD_LABELS = {
    "full_ahe_mrta":           "AHE-MRTA*",
    "big_mrta":                "BiG-MRTA",
    "rostam_ea":               "RoSTAM-EA",
    "static_weighted":         "SW",
    "consensus_dbta":          "Cons-DBTA",
    "ahe_no_dominance":        "AHE-NoD",
    "ahe_no_event_replanning": "AHE-NoER",
    "ahe_fixed_context":       "AHE-FC",
}

# (column, display_name, higher_is_better)
METRICS = [
    ("task_completion_rate",    "Completion Rate",      True),
    ("average_task_delay",      "Avg Task Delay (s)",   False),
    ("failure_recovery_time",   "Recovery Time (s)",    False),
    ("replanning_frequency",    "Replanning Freq.",     False),
    ("allocation_instability",  "Alloc. Instability",   False),
    ("mean_decision_latency_ms","Decision Latency (ms)",False),
    ("deadline_violation_rate", "Deadline Viol. Rate",  False),
]

ALPHA = 0.05


# ── Helpers ───────────────────────────────────────────────────────────────────

def sig_stars(p: float) -> str:
    if np.isnan(p): return "—"
    if p < 0.001:   return "***"
    if p < 0.01:    return "**"
    if p < 0.05:    return "*"
    return "ns"


def mann_whitney(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return np.nan, np.nan
    try:
        stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        return stat, p
    except Exception:
        return np.nan, np.nan


def effect_r(u_stat, n1, n2):
    if np.isnan(u_stat) or n1 == 0 or n2 == 0:
        return np.nan
    return 1 - (2 * u_stat) / (n1 * n2)


def cliffs_delta(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if len(a) == 0 or len(b) == 0:
        return np.nan
    greater = sum(ai > bi for ai in a for bi in b)
    less    = sum(ai < bi for ai in a for bi in b)
    return (greater - less) / (len(a) * len(b))


# ── Core analysis ─────────────────────────────────────────────────────────────

def run_pairwise_tests(df, proposed, baselines, scenarios):
    rows = []
    for scenario in scenarios:
        sub = df[df["scenario"] == scenario]
        prop_df = sub[sub["strategy"] == proposed]
        n_tests = len(baselines) * sum(1 for m, _, _ in METRICS if m in sub.columns)
        corrected_alpha = ALPHA / max(n_tests, 1)

        for baseline in baselines:
            base_df = sub[sub["strategy"] == baseline]
            for col, name, hib in METRICS:
                if col not in sub.columns:
                    continue
                a = prop_df[col].dropna().values
                b = base_df[col].dropna().values
                u, p = mann_whitney(a, b)
                r = effect_r(u, len(a), len(b))
                cd = cliffs_delta(a, b)
                a_mean = np.nanmean(a) if len(a) > 0 else np.nan
                b_mean = np.nanmean(b) if len(b) > 0 else np.nan
                delta = a_mean - b_mean
                direction = "better" if (hib and delta > 0) or (not hib and delta < 0) else "worse"
                rows.append({
                    "scenario":        scenario,
                    "metric":          col,
                    "metric_label":    name,
                    "baseline":        baseline,
                    "baseline_label":  METHOD_LABELS.get(baseline, baseline),
                    "proposed_mean":   a_mean,
                    "proposed_std":    np.nanstd(a, ddof=1) if len(a) > 1 else np.nan,
                    "baseline_mean":   b_mean,
                    "baseline_std":    np.nanstd(b, ddof=1) if len(b) > 1 else np.nan,
                    "delta":           delta,
                    "direction":       direction,
                    "U_stat":          u,
                    "p_value":         p,
                    "effect_r":        r,
                    "cliffs_delta":    cd,
                    "stars":           sig_stars(p) if not np.isnan(p) else "—",
                    "significant_bonferroni": (not np.isnan(p)) and (p < corrected_alpha),
                    "corrected_alpha": corrected_alpha,
                })
    return pd.DataFrame(rows)


def compute_descriptive(df):
    rows = []
    for (scenario, strategy), grp in df.groupby(["scenario", "strategy"]):
        row = {
            "scenario": scenario,
            "strategy": strategy,
            "label":    METHOD_LABELS.get(strategy, strategy),
            "n":        len(grp),
        }
        for col, _, _ in METRICS:
            if col in grp.columns:
                v = grp[col].dropna()
                row[f"{col}_mean"] = v.mean()    if len(v) > 0 else np.nan
                row[f"{col}_std"]  = v.std(ddof=1) if len(v) > 1 else np.nan
                row[f"{col}_med"]  = v.median() if len(v) > 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


# ── LaTeX helpers ─────────────────────────────────────────────────────────────

def _tex_header(caption, label, col_headers):
    ncols = 1 + len(col_headers)
    spec = "l" + "r" * len(col_headers)
    hrow = " & ".join(["\\textbf{Method}"] +
                      [f"\\textbf{{{h}}}" for h in col_headers])
    return (
        f"\\begin{{table}}[t]\n\\centering\n"
        f"\\caption{{{caption}}}\n\\label{{{label}}}\n"
        f"\\begin{{tabular}}{{{spec}}}\n\\toprule\n"
        f"{hrow} \\\\\n\\midrule\n"
    )


def _tex_footer():
    return "\\bottomrule\n\\end{tabular}\n\\end{table}\n"


def _cell(val, std, dec, bold=False, stars=""):
    if np.isnan(val):
        return "—"
    star_sup = f"$^{{{stars}}}$" if stars and stars not in ("ns", "—") else ""
    s = f"{val:.{dec}f}{star_sup} $\\pm$ {std:.{dec}f}" if not np.isnan(std) else f"{val:.{dec}f}{star_sup}"
    return f"\\textbf{{{s}}}" if bold else s


def _get_stars(tests, scenario, baseline, metric):
    t = tests[(tests["scenario"] == scenario) &
              (tests["baseline"] == baseline) &
              (tests["metric"] == metric)]
    if t.empty:
        return ""
    s = t["stars"].iloc[0]
    return "" if s in ("ns", "—") else s


def build_main_table(desc, tests):
    metrics_show = [
        ("task_completion_rate",   "CR$\\uparrow$",    3),
        ("average_task_delay",     "Delay$\\downarrow$(s)", 1),
        ("failure_recovery_time",  "RecT$\\downarrow$(s)",  1),
        ("replanning_frequency",   "RePlan$\\downarrow$",   2),
        ("allocation_instability", "Instab$\\downarrow$",   2),
    ]
    methods_g2 = [PROPOSED] + G2_BASELINES
    col_hdrs = [m[1] for m in metrics_show]
    caption = (
        "Main comparison (3 robots, 15 tasks, 5 seeds). "
        "Significance vs AHE-MRTA*: $^{*}p{<}0.05$, $^{**}p{<}0.01$, "
        "$^{***}p{<}0.001$ (Bonferroni-corrected Mann-Whitney U)."
    )
    out = _tex_header(caption, "tab:main_comparison", col_hdrs)

    for scenario in ["robot_failure", "mixed_stress"]:
        sc_label = scenario.replace("_", "\\_")
        ncols = 1 + len(metrics_show)
        out += (f"\\multicolumn{{{ncols}}}{{l}}"
                f"{{\\textit{{Scenario: {sc_label}}}}} \\\\\n")
        sub = desc[desc["scenario"] == scenario]
        for method in methods_g2:
            row = sub[sub["strategy"] == method]
            if row.empty:
                continue
            bold = method == PROPOSED
            label = METHOD_LABELS.get(method, method)
            cells = [f"\\textbf{{{label}}}" if bold else label]
            for col, _, dec in metrics_show:
                mn_col = f"{col}_mean"
                sd_col = f"{col}_std"
                if mn_col not in row.columns:
                    cells.append("—")
                    continue
                mn = row[mn_col].iloc[0]
                sd = row[sd_col].iloc[0] if sd_col in row.columns else np.nan
                stars = "" if bold else _get_stars(tests, scenario, method, col)
                cells.append(_cell(mn, sd, dec, bold, stars))
            out += " & ".join(cells) + " \\\\\n"
        out += "\\midrule\n"

    out += _tex_footer()
    return out


def build_ablation_table(desc, tests):
    metrics_show = [
        ("task_completion_rate",   "CR$\\uparrow$",         3),
        ("average_task_delay",     "Delay$\\downarrow$(s)",  1),
        ("replanning_frequency",   "RePlan$\\downarrow$",    2),
        ("allocation_instability", "Instab$\\downarrow$",    2),
    ]
    methods = [PROPOSED] + G4_ABLATIONS
    scenario = "robot_failure"
    sub = desc[desc["scenario"] == scenario]
    col_hdrs = [m[1] for m in metrics_show]
    caption = (
        "Ablation study (robot\\_failure, 3 robots, 15 tasks, 5 seeds). "
        "Significance vs AHE-MRTA* (Bonferroni-corrected Mann-Whitney U)."
    )
    out = _tex_header(caption, "tab:ablation", col_hdrs)
    for method in methods:
        row = sub[sub["strategy"] == method]
        if row.empty:
            continue
        bold = method == PROPOSED
        label = METHOD_LABELS.get(method, method)
        cells = [f"\\textbf{{{label}}}" if bold else label]
        for col, _, dec in metrics_show:
            mn_col, sd_col = f"{col}_mean", f"{col}_std"
            if mn_col not in row.columns:
                cells.append("—")
                continue
            mn = row[mn_col].iloc[0]
            sd = row[sd_col].iloc[0] if sd_col in row.columns else np.nan
            stars = "" if bold else _get_stars(tests, scenario, method, col)
            cells.append(_cell(mn, sd, dec, bold, stars))
        out += " & ".join(cells) + " \\\\\n"
    out += _tex_footer()
    return out


def build_deadline_table(desc, tests):
    metrics_show = [
        ("task_completion_rate",    "CR$\\uparrow$",         3),
        ("average_task_delay",      "Delay$\\downarrow$(s)", 1),
        ("deadline_violation_rate", "DVR$\\downarrow$",      3),
        ("replanning_frequency",    "RePlan$\\downarrow$",   2),
    ]
    methods = [PROPOSED] + G3_BASELINES
    scenario = "deadline_pressure"
    sub = desc[desc["scenario"] == scenario]
    col_hdrs = [m[1] for m in metrics_show]
    caption = (
        "Deadline scenario results (deadline\\_pressure, 3 robots, 15 tasks, 5 seeds). "
        "DVR: deadline violation rate. "
        "Significance vs AHE-MRTA* (Bonferroni-corrected Mann-Whitney U)."
    )
    out = _tex_header(caption, "tab:deadline", col_hdrs)
    for method in methods:
        row = sub[sub["strategy"] == method]
        if row.empty:
            continue
        bold = method == PROPOSED
        label = METHOD_LABELS.get(method, method)
        cells = [f"\\textbf{{{label}}}" if bold else label]
        for col, _, dec in metrics_show:
            mn_col, sd_col = f"{col}_mean", f"{col}_std"
            if mn_col not in row.columns:
                cells.append("—")
                continue
            mn = row[mn_col].iloc[0]
            sd = row[sd_col].iloc[0] if sd_col in row.columns else np.nan
            stars = "" if bold else _get_stars(tests, scenario, method, col)
            cells.append(_cell(mn, sd, dec, bold, stars))
        out += " & ".join(cells) + " \\\\\n"
    out += _tex_footer()
    return out


# ── Summary text ──────────────────────────────────────────────────────────────

def build_summary(tests, desc):
    lines = ["=" * 70,
             "AHE-MRTA Statistical Analysis Summary",
             "=" * 70, ""]

    for scenario in ["robot_failure", "mixed_stress", "deadline_pressure"]:
        t = tests[tests["scenario"] == scenario]
        if t.empty:
            continue
        lines.append(f"Scenario: {scenario}")
        lines.append("-" * 50)
        for col, name, hib in METRICS:
            tc = t[t["metric"] == col]
            if tc.empty:
                continue
            lines.append(f"  {name}:")
            if len(tc) > 0:
                lines.append(f"    AHE-MRTA*: {tc['proposed_mean'].iloc[0]:.4f}")
            for _, row in tc.iterrows():
                if np.isnan(row["p_value"]):
                    continue
                arrow = "↑" if row["direction"] == "better" else "↓"
                denom = abs(row["baseline_mean"]) if abs(row["baseline_mean"]) > 1e-9 else 1
                pct = abs(row["delta"]) / denom * 100
                lines.append(
                    f"    vs {row['baseline_label']:12s}: "
                    f"Δ={row['delta']:+.4f} ({arrow}{pct:.1f}%)  "
                    f"p={row['p_value']:.4f} {row['stars']}  "
                    f"r={row['effect_r']:.3f}  δ={row['cliffs_delta']:.3f}"
                )
        lines.append("")

    sig = tests[tests["significant_bonferroni"]]
    lines.append(f"Bonferroni-corrected significant results: {len(sig)} / {len(tests)}")
    lines.append(f"  AHE-MRTA* better: {len(sig[sig['direction']=='better'])}")
    lines.append(f"  AHE-MRTA* worse:  {len(sig[sig['direction']=='worse'])}")
    lines.append("")
    lines.append("Raw p<0.05 (uncorrected):")
    raw_sig = tests[tests["p_value"] < 0.05]
    lines.append(f"  Total: {len(raw_sig)} / {len(tests)}")
    lines.append(f"  Better: {len(raw_sig[raw_sig['direction']=='better'])}")
    lines.append(f"  Worse:  {len(raw_sig[raw_sig['direction']=='worse'])}")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-dir", default="results/processed")
    parser.add_argument("--output-dir",    default="results/stats")
    args = parser.parse_args()

    processed_dir = Path(args.processed_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(processed_dir / "all_summary.csv")
    print(f"Loaded {len(df)} experiments  "
          f"({df['strategy'].nunique()} strategies, {df['scenario'].nunique()} scenarios)\n")

    # Descriptive stats
    desc = compute_descriptive(df)
    desc.to_csv(out_dir / "descriptive_stats.csv", index=False)
    print(f"[OK] descriptive_stats.csv  ({len(desc)} rows)")

    # Pairwise Mann-Whitney tests
    g2 = run_pairwise_tests(df, PROPOSED, G2_BASELINES, ["robot_failure", "mixed_stress"])
    g3 = run_pairwise_tests(df, PROPOSED, G3_BASELINES, ["deadline_pressure"])
    g4 = run_pairwise_tests(df, PROPOSED, G4_ABLATIONS, ["robot_failure"])
    all_tests = pd.concat([g2, g3, g4], ignore_index=True)
    all_tests.to_csv(out_dir / "stat_tests.csv", index=False)
    print(f"[OK] stat_tests.csv  ({len(all_tests)} tests)")

    # LaTeX tables
    (out_dir / "latex_main_table.tex").write_text(build_main_table(desc, g2))
    print("[OK] latex_main_table.tex")

    (out_dir / "latex_ablation_table.tex").write_text(build_ablation_table(desc, g4))
    print("[OK] latex_ablation_table.tex")

    (out_dir / "latex_deadline_table.tex").write_text(build_deadline_table(desc, g3))
    print("[OK] latex_deadline_table.tex")

    # Human-readable summary
    summary = build_summary(all_tests, desc)
    (out_dir / "stat_summary.txt").write_text(summary)
    print("[OK] stat_summary.txt\n")
    print(summary)


if __name__ == "__main__":
    main()
