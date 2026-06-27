#!/usr/bin/env python3
"""
Statistical analysis for AHE-MRTA RA-L paper.

Outputs:
  results/stats/stat_tests.csv           — pairwise Mann-Whitney results
  results/stats/descriptive_stats.csv    — mean ± std per method × scenario × metric
  results/stats/latex_main_table.tex     — Table II: G2 main comparison
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

PROPOSED = "ahe_mrta_v3"
G1_BASELINES = ["big_mrta", "rostam_ea", "consensus_dbta"]
G2_BASELINES = G1_BASELINES   # robot_failure + mixed_stress
G3_BASELINES = ["big_mrta", "rostam_ea", "consensus_dbta"]  # deadline_pressure

# Primary Gazebo scale for the headline main/deadline tables (Table tab:scales).
# all_summary.csv pools every scale (3r/5r/10r); without this filter the
# descriptive means would mix scales and contradict the "5-robot primary" caption.
PRIMARY_ROBOTS = 5
PRIMARY_TASKS  = 25

METHOD_LABELS = {
    "ahe_mrta_v3":                  "AHE-MRTA*",
    "big_mrta":                     "BiG-MRTA",
    "rostam_ea":                    "RoSTAM-EA",
    "consensus_dbta":               "Cons-DBTA",
}

# (column, display_name, higher_is_better)
METRICS = [
    ("task_completion_rate",    "Completion Rate",      True),
    ("average_task_delay",      "Avg Task Delay (s)",   False),
    ("failure_recovery_time",   "Recovery Time (s)",    False),
    ("exec_preemptions",        "Exec Preemptions",     False),
    ("redispatch_per_task",     "Re-dispatch/Task",     False),
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
                    "p_adj":           min(1.0, p * n_tests) if not np.isnan(p) else np.nan,
                    "stars":           sig_stars(min(1.0, p * n_tests)) if not np.isnan(p) else "—",
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

def _tex_header(caption, label, col_headers, wide=False):
    # wide=True spans both columns (table*) — needed for wide cells like
    # "1.000 $\pm$ 0.000" with significance stars, which overflow a single
    # column.
    spec = "l" + "r" * len(col_headers)
    hrow = " & ".join(["\\textbf{Method}"] +
                      [f"\\textbf{{{h}}}" for h in col_headers])
    env = "table*" if wide else "table"
    return (
        f"\\begin{{{env}}}[t]\n\\centering\n"
        f"\\caption{{{caption}}}\n\\label{{{label}}}\n"
        f"\\small\n"
        + ("\\setlength{\\tabcolsep}{3pt}\n" if wide else "")
        + f"\\begin{{tabular}}{{{spec}}}\n\\toprule\n"
        f"{hrow} \\\\\n\\midrule\n"
    )


def _tex_footer(wide=False):
    env = "table*" if wide else "table"
    return f"\\bottomrule\n\\end{{tabular}}\n\\end{{{env}}}\n"


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


# higher-is-better direction per metric column (from METRICS)
HIGHER_BETTER = {col: hb for col, _, hb in METRICS}


def _best_set(sub, methods, col, dec):
    """Methods whose *displayed* value (rounded to `dec`) is best for `col`.

    Direction comes from HIGHER_BETTER. Bolding is by best value, not by
    method: the winning cell is emphasised even when it is a baseline. Returns
    an empty set when every method ties (nothing to distinguish) so we do not
    bold, e.g., an all-zero preemption column.
    """
    mn_col = f"{col}_mean"
    if mn_col not in sub.columns:
        return set()
    vals = {}
    for m in methods:
        r = sub[sub["strategy"] == m]
        if r.empty or pd.isna(r[mn_col].iloc[0]):
            continue
        vals[m] = round(float(r[mn_col].iloc[0]), dec)
    if len(set(vals.values())) <= 1:        # all equal / nothing to rank
        return set()
    tgt = max(vals.values()) if HIGHER_BETTER.get(col, True) else min(vals.values())
    return {m for m, v in vals.items() if v == tgt}


def build_main_table(desc, tests):
    metrics_show = [
        ("task_completion_rate",   "CR$\\uparrow$",    3),
        ("average_task_delay",     "Delay$\\downarrow$(s)", 1),
        ("failure_recovery_time",  "RecT$\\downarrow$(s)",  1),
        ("exec_preemptions",       "Preempt$\\downarrow$",  2),
        ("redispatch_per_task",    "Churn$\\downarrow$",    3),
    ]
    methods_g2 = [PROPOSED] + G2_BASELINES
    col_hdrs = [m[1] for m in metrics_show]
    caption = (
        "Main comparison at the primary 5-robot / 25-task scale; $n{=}5$ runs (seeds) per cell. "
        "Best value per column (within scenario) in \\textbf{bold}. "
        "Significance vs AHE-MRTA*: $^{*}p{<}0.05$, $^{**}p{<}0.01$, "
        "$^{***}p{<}0.001$ (Mann--Whitney U, Bonferroni-corrected within each scenario family of 21 tests)."
    )
    out = _tex_header(caption, "tab:main_comparison", col_hdrs, wide=True)

    scenarios = ["robot_failure", "mixed_stress"]
    for si, scenario in enumerate(scenarios):
        sc_label = scenario.replace("_", "\\_")
        ncols = 1 + len(metrics_show)
        out += (f"\\multicolumn{{{ncols}}}{{l}}"
                f"{{\\textit{{Scenario: {sc_label}}}}} \\\\\n")
        sub = desc[desc["scenario"] == scenario]
        best = {col: _best_set(sub, methods_g2, col, dec)
                for col, _, dec in metrics_show}
        for method in methods_g2:
            row = sub[sub["strategy"] == method]
            if row.empty:
                continue
            is_proposed = method == PROPOSED
            label = METHOD_LABELS.get(method, method)
            # method name stays bold for the proposed row (row highlight);
            # value bolding below is independent and tracks the best cell.
            cells = [f"\\textbf{{{label}}}" if is_proposed else label]
            for col, _, dec in metrics_show:
                mn_col = f"{col}_mean"
                sd_col = f"{col}_std"
                if mn_col not in row.columns:
                    cells.append("—")
                    continue
                mn = row[mn_col].iloc[0]
                sd = row[sd_col].iloc[0] if sd_col in row.columns else np.nan
                stars = "" if is_proposed else _get_stars(tests, scenario, method, col)
                cells.append(_cell(mn, sd, dec, method in best[col], stars))
            out += " & ".join(cells) + " \\\\\n"
        if si < len(scenarios) - 1:
            out += "\\midrule\n"

    out += _tex_footer(wide=True)
    return out


def build_deadline_table(desc, tests):
    metrics_show = [
        ("task_completion_rate",    "CR$\\uparrow$",         3),
        ("average_task_delay",      "Delay$\\downarrow$(s)", 1),
        ("deadline_violation_rate", "DVR$\\downarrow$",      3),
        ("exec_preemptions",        "Preempt$\\downarrow$",  2),
    ]
    methods = [PROPOSED] + G3_BASELINES
    scenario = "deadline_pressure"
    sub = desc[desc["scenario"] == scenario]
    col_hdrs = [m[1] for m in metrics_show]
    caption = (
        "Deadline scenario results (deadline\\_pressure) at the primary 5-robot / 25-task scale; $n{=}5$ runs (seeds) per cell. "
        "DVR: deadline violation rate. Best value per column in \\textbf{bold}. "
        "Significance vs AHE-MRTA* (Bonferroni-corrected Mann-Whitney U)."
    )
    out = _tex_header(caption, "tab:deadline", col_hdrs, wide=True)
    best = {col: _best_set(sub, methods, col, dec)
            for col, _, dec in metrics_show}
    for method in methods:
        row = sub[sub["strategy"] == method]
        if row.empty:
            continue
        is_proposed = method == PROPOSED
        label = METHOD_LABELS.get(method, method)
        cells = [f"\\textbf{{{label}}}" if is_proposed else label]
        for col, _, dec in metrics_show:
            mn_col, sd_col = f"{col}_mean", f"{col}_std"
            if mn_col not in row.columns:
                cells.append("—")
                continue
            mn = row[mn_col].iloc[0]
            sd = row[sd_col].iloc[0] if sd_col in row.columns else np.nan
            stars = "" if is_proposed else _get_stars(tests, scenario, method, col)
            cells.append(_cell(mn, sd, dec, method in best[col], stars))
        out += " & ".join(cells) + " \\\\\n"
    out += _tex_footer(wide=True)
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
    # LaTeX tables now live alongside the paper; CSV artefacts stay in --output-dir.
    parser.add_argument("--table-dir",      default="paper/table")
    args = parser.parse_args()

    processed_dir = Path(args.processed_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    table_dir = Path(args.table_dir)
    table_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(processed_dir / "all_summary.csv")
    print(f"Loaded {len(df)} experiments (all scales)")
    # Restrict the headline main/deadline tables to the primary scale.
    if {"robot_count", "target_count"}.issubset(df.columns):
        df = df[(df["robot_count"] == PRIMARY_ROBOTS) &
                (df["target_count"] == PRIMARY_TASKS)].copy()
    print(f"Primary scale {PRIMARY_ROBOTS}r/{PRIMARY_TASKS}t -> {len(df)} experiments  "
          f"({df['strategy'].nunique()} strategies, {df['scenario'].nunique()} scenarios)\n")

    # Descriptive stats
    desc = compute_descriptive(df)
    desc.to_csv(out_dir / "descriptive_stats.csv", index=False)
    print(f"[OK] descriptive_stats.csv  ({len(desc)} rows)")

    # Pairwise Mann-Whitney tests
    g2 = run_pairwise_tests(df, PROPOSED, G2_BASELINES, ["robot_failure", "mixed_stress"])
    g3 = run_pairwise_tests(df, PROPOSED, G3_BASELINES, ["deadline_pressure"])
    all_tests = pd.concat([g2, g3], ignore_index=True)
    all_tests.to_csv(out_dir / "stat_tests.csv", index=False)
    print(f"[OK] stat_tests.csv  ({len(all_tests)} tests)")

    # LaTeX tables (written to paper/table, \input by the papers)
    (table_dir / "latex_main_table.tex").write_text(build_main_table(desc, g2))
    print(f"[OK] {table_dir}/latex_main_table.tex")

    (table_dir / "latex_deadline_table.tex").write_text(build_deadline_table(desc, g3))
    print(f"[OK] {table_dir}/latex_deadline_table.tex")

    # Human-readable summary
    summary = build_summary(all_tests, desc)
    (out_dir / "stat_summary.txt").write_text(summary)
    print("[OK] stat_summary.txt\n")
    print(summary)


if __name__ == "__main__":
    main()
