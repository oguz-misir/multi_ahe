#!/usr/bin/env python3
"""
Generate the paper figure set from processed CSV files.

Produces exactly the figures referenced by paper/main.tex / main_tr.tex:

  fitness_comparison.png               (sim_fitness_seedwise.csv; fallback: sim_fitness.csv)
  scalability_panel.png                (sim_scalability.csv)
  baseline_comparison_multi_metric.png (all_summary.csv, 3r)
  baseline_comparison_10r.png          (gazebo_10r/all_summary.csv)
  failure_recovery.png                 (all_summary.csv, robot_failure)
  dominance_recovery_panel.png         (all_ecosystem_metrics.csv + summary)
  task_completion_timeline.png         (all_task_events.csv)
  communication_footprint.png          (all_communication.csv)

scenario_maps_panel.png is produced by scripts/generate_scenario_maps.py;
gazebo_rviz_combined.png is composed from Gazebo/RViz screen captures.
Figures 1 and 2 (fig1.drawio / fig2.drawio, + their .drawio.png exports) are
hand-authored draw.io assets under paper/figure/, edited directly here.

Usage:
    python3 scripts/plot_results.py \
        --processed-dir results/processed/ \
        --output-dir results/paper_figures/ \
        --dpi 300
"""

import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import MaxNLocator
from pathlib import Path
from typing import Optional

# ── Global publication style ───────────────────────────────────────────────────
plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.5,
    "axes.grid": True,
    "grid.linestyle": ":",
    "grid.linewidth": 0.5,
    "grid.alpha": 0.6,
    "axes.axisbelow": True,
})

SINGLE_COL_W = 3.5   # inches
DOUBLE_COL_W = 7.0   # inches

# ── Fixed method order (proposed method last) and colour-blind-safe palette ────
# Okabe–Ito palette: distinguishable under deuteranopia/protanopia and in
# greyscale print. The proposed method is always vermillion and drawn last.
METHOD_ORDER = [
    "big_mrta",
    "rostam_ea",
    "consensus_dbta",
    "ahe_mrta_v3",
]

METHOD_LABELS = {
    "big_mrta":       "BiG-MRTA",
    "rostam_ea":      "RoSTAM-EA",
    "consensus_dbta": "Cons-DBTA",
    "ahe_mrta_v3":    "AHE-MRTA*",
}

# Compact labels for narrow panels where rotated full names become unreadable.
METHOD_LABELS_SHORT = {
    "big_mrta":       "BiG",
    "rostam_ea":      "RoSTAM",
    "consensus_dbta": "Cons",
    "ahe_mrta_v3":    "AHE*",
}

METHOD_PALETTE = {
    "big_mrta":       "#0072B2",  # blue
    "rostam_ea":      "#009E73",  # bluish green
    "consensus_dbta": "#CC79A7",  # reddish purple
    "ahe_mrta_v3":    "#D55E00",  # vermillion (proposed)
}

PROPOSED = "ahe_mrta_v3"

# Okabe–Ito series colours for the seven hormones / line plots.
SERIES7 = ["#E69F00", "#56B4E9", "#009E73", "#F0E442",
           "#0072B2", "#D55E00", "#CC79A7"]

# Active 4-vector configuration: 5 reachable paradigms (d_0 spatial, d_1
# criticality, d_2 temporal, d_5 stability, d_6 recovery); d_3/d_4
# (resource/energy) are dormant under the zeroed battery/workload signals.
HEURISTIC_COLS = ["d_0", "d_1", "d_2", "d_3", "d_4"]
HEURISTIC_LABELS = [
    "Spatial", "Criticality", "Temporal", "Stability", "Recovery",
]

CONTEXT_COLS = ["task_density", "robot_availability",
                "deadline_pressure", "failure_rate"]
CONTEXT_LABELS = ["Task Density", "Robot Avail.",
                  "Deadline Press.", "Failure Rate"]


def _load(processed_dir: Path, fname: str) -> Optional[pd.DataFrame]:
    path = processed_dir / fname
    if not path.exists():
        return None
    df = pd.read_csv(path)
    return df if not df.empty else None


def _ordered_methods(df: pd.DataFrame, subset=None) -> list:
    available = df["strategy"].unique() if df is not None else []
    order = subset if subset else METHOD_ORDER
    return [m for m in order if m in available]


def _bar_panel(ax, df, methods, metric, ylabel, higher_better: bool = True,
               log_y: bool = False, clip_zero: bool = False):
    """Grouped bar with std error bars for one metric; proposed emphasised.

    clip_zero truncates the lower whisker at the axis origin for metrics
    that cannot be negative (times, rates), where a full ±std whisker
    would extend into a physically impossible range.
    """
    valid_methods = [m for m in methods if m in df["strategy"].unique()]
    means, stds = [], []
    for m in valid_methods:
        vals = df[df["strategy"] == m][metric].dropna()
        means.append(vals.mean() if len(vals) else 0.0)
        stds.append(vals.std() if len(vals) > 1 else 0.0)

    x = np.arange(len(valid_methods))
    yerr = np.asarray(stds)
    if clip_zero:
        yerr = np.vstack([np.minimum(stds, means), stds])
    colors = [METHOD_PALETTE.get(m, "#999999") for m in valid_methods]
    edge_w = [1.4 if m == PROPOSED else 0.6 for m in valid_methods]
    bars = ax.bar(x, means, yerr=yerr, capsize=3, color=colors,
                  edgecolor="black", error_kw={"linewidth": 0.8})
    for b, w in zip(bars, edge_w):
        b.set_linewidth(w)
    # numeric value label above each bar (above the error-bar cap)
    for b, mn, sd in zip(bars, means, stds):
        ax.annotate(f"{mn:.3g}", xy=(b.get_x() + b.get_width() / 2.0, mn + sd),
                    xytext=(0, 2), textcoords="offset points",
                    ha="center", va="bottom", fontsize=6.5, fontweight="bold")
    ax.margins(y=0.18)  # headroom so the top label is not clipped
    ax.set_xticks(x)
    ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in valid_methods],
                       rotation=45, ha="right")
    if log_y:
        ax.set_yscale("log")
        ylabel += " (log)"
    ax.set_ylabel(ylabel)
    arrow = "$\\uparrow$" if higher_better else "$\\downarrow$"
    # The metric name already lives on the (vertical) y-axis label; keeping it
    # in the title too made the title wider than the narrow panel and collided
    # with the neighbouring column. Title now carries only the optimisation
    # direction, so adjacent panels never overlap.
    ax.set_title(f"{arrow} better", fontsize=9)
    return bars


def _event_count_panel(ax, df, methods, metric, ylabel,
                       higher_better: bool = False):
    """Integer event-total bars for rare discrete events; proposed emphasised.

    A mean±std rate bar misleads for a metric like re-dispatches: most
    runs are exactly zero (invisible bars), a single seed can carry the
    whole mean, and the std whisker dips below zero although the metric
    cannot. The raw event total, annotated with how many seeds contribute
    it, states the finding directly.
    """
    valid = [m for m in methods if m in df["strategy"].unique()]
    colors = [METHOD_PALETTE.get(m, "#999999") for m in valid]
    totals, seeds_hit, n_runs = [], [], 0
    for m in valid:
        vals = df[df["strategy"] == m][metric].dropna()
        totals.append(int(vals.sum()))
        seeds_hit.append(int((vals > 0).sum()))
        n_runs = max(n_runs, len(vals))

    x = np.arange(len(valid))
    edge_w = [1.4 if m == PROPOSED else 0.6 for m in valid]
    bars = ax.bar(x, totals, color=colors, edgecolor="black")
    for b, w in zip(bars, edge_w):
        b.set_linewidth(w)
    for i, (tot, hit) in enumerate(zip(totals, seeds_hit)):
        note = str(tot) if tot == 0 else \
            f"{tot} ({hit} seed{'s' if hit > 1 else ''})"
        ax.annotate(note, xy=(i, tot), xytext=(0, 2),
                    textcoords="offset points", ha="center", va="bottom",
                    fontsize=6.5, fontweight="bold")
    ax.margins(y=0.18)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xticks(x)
    ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in valid],
                       rotation=45, ha="right")
    ax.set_ylabel(f"{ylabel} ({n_runs} seeds)")
    arrow = "$\\uparrow$" if higher_better else "$\\downarrow$"
    ax.set_title(f"{arrow} better", fontsize=9)


def _box_panel(ax, df, methods, metric, ylabel, log_y: bool = False):
    """Per-method boxplot with jittered raw points; proposed emphasised.

    Box = IQR, line = median, whiskers = 1.5*IQR; every individual run is
    overlaid as a point so the reader sees the full distribution (n per cell
    is small enough that points stay legible). Use log_y when methods differ
    by orders of magnitude, otherwise the small boxes collapse near zero.
    """
    valid = [m for m in methods if m in df["strategy"].unique()]
    data = [df[df["strategy"] == m][metric].dropna().values for m in valid]
    colors = [METHOD_PALETTE.get(m, "#999999") for m in valid]

    bp = ax.boxplot(data, positions=range(len(valid)), widths=0.58,
                    patch_artist=True, showfliers=False,
                    medianprops=dict(color="black", linewidth=1.5),
                    whiskerprops=dict(linewidth=1.0, color="#444444"),
                    capprops=dict(linewidth=1.0, color="#444444"))
    for patch, m, c in zip(bp["boxes"], valid, colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.45)
        patch.set_edgecolor("black")
        patch.set_linewidth(1.6 if m == PROPOSED else 0.8)

    rng = np.random.default_rng(7)
    for i, (vals, c) in enumerate(zip(data, colors)):
        jitter = rng.uniform(-0.14, 0.14, size=len(vals))
        ax.scatter(i + jitter, vals, s=13, color=c, edgecolor="black",
                   linewidth=0.4, zorder=3)

    # numeric median label (white background so it stays readable over the
    # box and the jittered points)
    for i, vals in enumerate(data):
        if len(vals):
            med = float(np.median(vals))
            ax.text(i, med, f"{med:.3g}", ha="center", va="bottom",
                    fontsize=6.5, fontweight="bold", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.1", fc="white",
                              ec="none", alpha=0.78))

    ax.set_xticks(range(len(valid)))
    ax.set_xticklabels([METHOD_LABELS_SHORT.get(m, m) for m in valid],
                       fontsize=9)
    if log_y:
        ax.set_yscale("log")
        ylabel += " (log)"
    ax.set_ylabel(ylabel)


# ── Static architecture diagrams ────────────────────────────────────────────────

def _orect(ax, x, y, w, h, lbl, fc, fs=8.0, ec="#444"):
    """Rounded box with centered label."""
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.10",
        facecolor=fc, edgecolor=ec, linewidth=1.0, mutation_aspect=0.6)
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, lbl, ha="center", va="center", fontsize=fs)


def _harrow(ax, x1, x2, y, color="#444", lw=1.3, lbl="", lbl_dy=0.18,
            two_way=False):
    """Straight horizontal arrow with optional label above the midpoint."""
    style = "<|-|>" if two_way else "-|>"
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                shrinkA=0, shrinkB=0))
    if lbl:
        ax.text((x1 + x2) / 2, y + lbl_dy, lbl, ha="center", va="bottom",
                fontsize=7.2, color=color)


def _varrow(ax, x, y1, y2, color="#444", lw=1.3, lbl="", side="right",
            two_way=False):
    """Straight vertical arrow with optional label beside it."""
    style = "<|-|>" if two_way else "-|>"
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                shrinkA=0, shrinkB=0))
    if lbl:
        dx = 0.12 if side == "right" else -0.12
        ha = "left" if side == "right" else "right"
        ax.text(x + dx, (y1 + y2) / 2, lbl, ha=ha, va="center",
                fontsize=7.2, color=color)


# ── Data-driven figures ─────────────────────────────────────────────────────────

def plot_baseline_comparison(df_summary: Optional[pd.DataFrame], out_dir: Path,
                             dpi: int, out_name: str,
                             scenarios: Optional[list] = None) -> None:
    """Six-panel multi-metric comparison of the four methods.

    Used twice: 3-robot primary scale (robot_failure + mixed_stress pooled)
    and the 10-robot scale (all scenarios pooled).
    """
    metrics = [
        ("task_completion_rate",    "Task Completion Rate",   True,  False),
        ("tasks_completed",         "Tasks Completed",         True,  False),
        ("average_task_delay",      "Avg Task Delay (s)",      False, False),
        ("workload_balance",        "Workload Balance",        True,  False),
        ("deadline_violation_rate", "Deadline Violation Rate", False, False),
        ("mean_decision_latency_ms","Decision Latency (ms)",   False, True),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(DOUBLE_COL_W + 0.6, 5.2))
    axes = axes.flatten()

    if df_summary is None or df_summary.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No data yet", ha="center", va="center",
                    transform=ax.transAxes)
    else:
        sub = df_summary
        if scenarios and "scenario" in sub.columns:
            sub = sub[sub["scenario"].isin(scenarios)]
        methods = _ordered_methods(sub)
        for ax, (metric, ylabel, higher_better, log_y) in zip(axes, metrics):
            if metric not in sub.columns:
                ax.text(0.5, 0.5, f"{metric}\ncolumn missing",
                        ha="center", va="center", transform=ax.transAxes)
                continue
            _bar_panel(ax, sub, methods, metric, ylabel, higher_better,
                       log_y=log_y)

    fig.tight_layout(w_pad=1.6, h_pad=2.0)
    out_path = out_dir / out_name
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_failure_recovery(df_summary: Optional[pd.DataFrame],
                          out_dir: Path, dpi: int) -> None:
    """Recovery time / CR / replanning under robot_failure (3-panel)."""
    fig, axes = plt.subplots(1, 3, figsize=(DOUBLE_COL_W, 2.9))

    if df_summary is None or df_summary.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No data yet", ha="center", va="center",
                    transform=ax.transAxes)
    else:
        rf = df_summary[df_summary["scenario"] == "robot_failure"] \
            if "scenario" in df_summary.columns else df_summary
        if rf.empty:
            rf = df_summary
        methods = _ordered_methods(rf)
        _bar_panel(axes[0], rf, methods, "failure_recovery_time",
                   "Recovery Time (s)", False, clip_zero=True)
        if "task_completion_rate" in rf.columns:
            _bar_panel(axes[1], rf, methods, "task_completion_rate",
                       "Completion Rate", True)
        # Execution preemptions are 0 for every method at this scale (no method
        # interrupts an in-flight task), so that panel cannot discriminate;
        # show corrected re-dispatches instead (Sec. discussion). Re-dispatch
        # is a rare discrete event (17 of 20 runs are exactly zero; one seed
        # carries all of Consensus-DBTA's events), so report raw event totals
        # rather than a mean±std rate bar.
        _event_count_panel(axes[2], rf, methods, "task_redispatch",
                           "Total Re-dispatches")

    fig.tight_layout()
    out_path = out_dir / "failure_recovery.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_dominance_recovery_panel(df_eco: Optional[pd.DataFrame],
                                  df_alloc: Optional[pd.DataFrame],
                                  df_summary: Optional[pd.DataFrame],
                                  df_task: Optional[pd.DataFrame],
                                  out_dir: Path, dpi: int) -> None:
    """Dominance evolution + cumulative completion (left), recovery bars (right).

    Panel (a): one representative robot_failure run (3r/15t, lowest seed).
    Panel (b): cumulative task completion under robot_failure, all methods.
    Panels (c-e): recovery-time / replanning / instability bars.
    """
    fig = plt.figure(figsize=(DOUBLE_COL_W + 2.5, 7.0))
    gs = fig.add_gridspec(3, 2, hspace=0.85, wspace=0.30,
                          width_ratios=[1.25, 1.0],
                          left=0.07, right=0.98, top=0.96, bottom=0.06)

    ax_dom = fig.add_subplot(gs[0:2, 0])
    ax_cum = fig.add_subplot(gs[2, 0])
    ax_rec = fig.add_subplot(gs[0, 1])
    ax_replan = fig.add_subplot(gs[1, 1])
    ax_inst = fig.add_subplot(gs[2, 1])

    for ax in [ax_dom, ax_cum, ax_rec, ax_replan, ax_inst]:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fail_t = None  # failure injection time, reused as marker in (a) and (b)

    # (a) dominance of one representative run (single experiment, single seed)
    if df_eco is not None and not df_eco.empty:
        subset = df_eco[df_eco["strategy"] == PROPOSED]
        if "scenario" in subset.columns:
            rf = subset[subset["scenario"] == "robot_failure"]
            if not rf.empty:
                subset = rf
        if "target_count" in subset.columns and (subset["target_count"] == 15).any():
            subset = subset[subset["target_count"] == 15]
        if "experiment_id" in subset.columns:
            subset = subset[subset["experiment_id"] == sorted(subset["experiment_id"].unique())[0]]
        elif "seed" in subset.columns:
            subset = subset[subset["seed"] == subset["seed"].min()]
        subset = subset.sort_values("timestamp_s") if "timestamp_s" in subset.columns else subset
        t_col2 = next((c for c in ["timestamp_s", "time", "t"] if c in subset.columns), None)
        t = subset[t_col2].values if t_col2 else np.arange(len(subset))
        for col, lbl, c in zip(HEURISTIC_COLS, HEURISTIC_LABELS, SERIES7):
            if col in subset.columns:
                ax_dom.plot(t, subset[col], label=lbl, color=c, linewidth=1.2)
        ax_dom.set_ylabel("Dominance $D(t)$")
        ax_dom.set_title("(a) Dominance evolution (robot failure, AHE-MRTA*)",
                         fontsize=9)

        # Failure injection time of THIS representative run. The event is logged
        # in df_alloc with column 'timestamp_s' (not 'time'); read it for the
        # selected experiment_id rather than falling back to a hard-coded value.
        if (df_alloc is not None and not df_alloc.empty
                and "experiment_id" in subset.columns):
            rep_eid = subset["experiment_id"].iloc[0]
            rf_events = df_alloc[(df_alloc["experiment_id"] == rep_eid) &
                                 df_alloc["event_type"].astype(str)
                                 .str.contains("robot_failure", na=False)]
            if not rf_events.empty:
                fail_t = float(rf_events["timestamp_s"].iloc[0])
        if fail_t is not None:
            ax_dom.axvline(fail_t, color="black", linestyle=":", alpha=0.8,
                           linewidth=1.2, label="Failure injection")
        ax_dom.legend(loc="upper right", ncol=2, fontsize=7)
    else:
        ax_dom.text(0.5, 0.5, "No ecosystem data", ha="center", va="center",
                    transform=ax_dom.transAxes)

    # (b) cumulative completion under robot_failure, per method
    drew_cum = False
    if df_task is not None and not df_task.empty:
        event_col = "event" if "event" in df_task.columns else "status"
        time_col = next((c for c in ["timestamp_s", "completed_rel", "time_s"]
                         if c in df_task.columns), None)
        scen_df = df_task[df_task["scenario"] == "robot_failure"] \
            if "scenario" in df_task.columns else df_task
        if "target_count" in scen_df.columns and (scen_df["target_count"] == 15).any():
            scen_df = scen_df[scen_df["target_count"] == 15]
        if time_col and not scen_df.empty:
            t0_map = scen_df[scen_df[event_col] == "activated"].groupby("experiment_id")[time_col].min()
            t0_map = t0_map.combine_first(scen_df.groupby("experiment_id")[time_col].min())
            scen_df = scen_df.copy()
            scen_df["time_rel"] = scen_df.apply(lambda r: r[time_col] - t0_map.get(r["experiment_id"], 0.0), axis=1)

            max_t = scen_df["time_rel"].max()
            for method in _ordered_methods(scen_df):
                mdf = scen_df[(scen_df["strategy"] == method)
                              & (scen_df[event_col] == "completed")]
                if mdf.empty:
                    continue
                n_exp = mdf["experiment_id"].nunique() if "experiment_id" in mdf.columns else 1
                t_sorted = np.sort(mdf["time_rel"].dropna().values)
                cumulative = np.arange(1, len(t_sorted) + 1) / max(n_exp, 1)
                t_sorted = np.insert(t_sorted, 0, 0.0)
                cumulative = np.insert(cumulative, 0, 0.0)
                
                # Extend to max_t so the line doesn't abruptly end
                if len(t_sorted) > 0 and t_sorted[-1] < max_t:
                    t_sorted = np.append(t_sorted, max_t)
                    cumulative = np.append(cumulative, cumulative[-1])

                ax_cum.step(t_sorted, cumulative, where='post',
                            label=METHOD_LABELS.get(method, method),
                            color=METHOD_PALETTE.get(method, "#999999"),
                            linewidth=2.0 if method == PROPOSED else 1.2)
                drew_cum = True
    if drew_cum:
        # (b) pools several runs whose injection times differ; mark the median
        # injection time rather than the single representative run used in (a).
        fail_t_b = fail_t
        if df_alloc is not None and not df_alloc.empty:
            rf_b = df_alloc[df_alloc["event_type"].astype(str)
                            .str.contains("robot_failure", na=False)]
            if "scenario" in rf_b.columns:
                rf_b = rf_b[rf_b["scenario"] == "robot_failure"]
            if "target_count" in rf_b.columns and (rf_b["target_count"] == 15).any():
                rf_b = rf_b[rf_b["target_count"] == 15]
            if not rf_b.empty:
                fail_t_b = float(rf_b.groupby("experiment_id")["timestamp_s"]
                                 .min().median())
        if fail_t_b is not None:
            ax_cum.axvline(fail_t_b, color="black", linestyle=":", alpha=0.8,
                           linewidth=1.2)
        ax_cum.set_ylabel("Avg cumul. tasks")
        ax_cum.set_xlabel("Time (s)")
        ax_cum.set_title("(b) Cumulative completion (robot failure)", fontsize=9)
        ax_cum.legend(loc="lower right", ncol=2, fontsize=7)
    else:
        ax_cum.text(0.5, 0.5, "No task-event data", ha="center", va="center",
                    transform=ax_cum.transAxes)

    # Right: recovery metrics at the 3-robot scale (all three densities pooled →
    # n=15 per method, matching the caption). Filtering to a single density gave
    # n=5, where boxes degenerate into solid blocks; pooling all scales instead
    # leaks 10-robot runs. robot_count==3 is the correct "3-robot scale, n=15".
    if df_summary is not None and not df_summary.empty:
        rf_sum = df_summary[df_summary["scenario"] == "robot_failure"] \
            if "scenario" in df_summary.columns else df_summary
        if "robot_count" in rf_sum.columns and (rf_sum["robot_count"] == 3).any():
            rf_sum = rf_sum[rf_sum["robot_count"] == 3]
        if rf_sum.empty:
            rf_sum = df_summary
        methods = _ordered_methods(rf_sum)
        _box_panel(ax_rec, rf_sum, methods, "failure_recovery_time",
                   "Recovery Time (s)")
        ax_rec.set_title("(c) Failure recovery time ($\\downarrow$ better)",
                         fontsize=10)
        # Execution preemptions are 0 for every method at 3r/5r; show average
        # task delay (a discriminating cost metric) instead of an empty panel.
        _box_panel(ax_replan, rf_sum, methods, "average_task_delay",
                   "Avg Task Delay (s)", log_y=False)
        ax_replan.set_title("(d) Avg task delay ($\\downarrow$ better)",
                            fontsize=10)
        _box_panel(ax_inst, rf_sum, methods, "redispatch_per_task",
                   "Re-dispatch / Task", log_y=False)
        ax_inst.set_title("(e) Task re-dispatch rate ($\\downarrow$ better)",
                          fontsize=10)
    else:
        for ax, lbl in [(ax_rec, "(c)"), (ax_replan, "(d)"), (ax_inst, "(e)")]:
            ax.text(0.5, 0.5, f"{lbl}\nNo data", ha="center", va="center",
                    transform=ax.transAxes)

    out_path = out_dir / "dominance_recovery_panel.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_communication_footprint(df_comm: Optional[pd.DataFrame],
                                 out_dir: Path, dpi: int) -> None:
    col = next((c for c in ["footprint_bytes", "bytes_transmitted", "communication_bytes"]
                if df_comm is not None and c in df_comm.columns), None)

    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE_COL_W, 3.0))

    if df_comm is None or df_comm.empty or col is None:
        for ax in axes:
            ax.text(0.5, 0.5, "No comm data", ha="center", va="center",
                    transform=ax.transAxes)
        fig.tight_layout()
        fig.savefig(out_dir / "communication_footprint.png", dpi=dpi,
                    bbox_inches="tight")
        plt.close(fig)
        return

    methods = _ordered_methods(df_comm)
    labels  = [METHOD_LABELS.get(m, m) for m in methods]
    colors  = [METHOD_PALETTE.get(m, "#999999") for m in methods]
    means   = [df_comm[df_comm["strategy"] == m][col].mean() for m in methods]
    errs    = [df_comm[df_comm["strategy"] == m][col].std(ddof=1) for m in methods]

    # Panel (a): log scale — all methods, shows RoSTAM-EA dominance
    ax = axes[0]
    bars = ax.bar(labels, means, color=colors, yerr=errs, capsize=3,
                  edgecolor="black", linewidth=0.6,
                  error_kw={"linewidth": 0.8})
    ax.set_yscale("log")
    ax.set_ylabel("Bytes / event (log)")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_title("(a) All methods, log scale", fontsize=9)
    for bar, m, mean in zip(bars, methods, means):
        if m == "rostam_ea" and not np.isnan(mean):
            ax.text(bar.get_x() + bar.get_width() / 2, mean * 1.15,
                    f"{mean:.0f}", ha="center", va="bottom", fontsize=7.5,
                    fontweight="bold")

    # Panel (b): linear scale — exclude RoSTAM-EA to show detail among others
    ax = axes[1]
    methods2 = [m for m in methods if m != "rostam_ea"]
    labels2  = [METHOD_LABELS.get(m, m) for m in methods2]
    colors2  = [METHOD_PALETTE.get(m, "#999999") for m in methods2]
    means2   = [df_comm[df_comm["strategy"] == m][col].mean() for m in methods2]
    errs2    = [df_comm[df_comm["strategy"] == m][col].std(ddof=1) for m in methods2]
    ax.bar(labels2, means2, color=colors2, yerr=errs2, capsize=3,
           edgecolor="black", linewidth=0.6, error_kw={"linewidth": 0.8})
    ax.set_ylabel("Bytes / event")
    ax.set_xticks(range(len(labels2)))
    ax.set_xticklabels(labels2, rotation=45, ha="right")
    ax.set_title("(b) Excluding RoSTAM-EA, linear", fontsize=9)
    for i, (mean, err) in enumerate(zip(means2, errs2)):
        if not np.isnan(mean):
            ax.text(i, mean + (err if not np.isnan(err) else 0) + max(means2) * 0.02,
                    f"{mean:.0f}", ha="center", va="bottom", fontsize=7.5)

    fig.tight_layout()
    out_path = out_dir / "communication_footprint.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_fitness_comparison(processed_dir: Path, out_dir: Path, dpi: int) -> None:
    """Stochastic-navigation fitness, grouped distributions per scenario.

    A genuine box plot requires one fitness observation per seed.  The
    seed-wise CSV is therefore preferred; the legacy aggregate CSV retains
    the mean±SD bar-chart fallback for older result bundles.
    """
    raw_path = processed_dir / "sim_fitness_seedwise.csv"
    fpath = processed_dir / "sim_fitness.csv"
    raw_df = pd.read_csv(raw_path) if raw_path.exists() else None
    if raw_df is None and not fpath.exists():
        print(f"[skip] sim_fitness_seedwise.csv yok — fitness karşılaştırma çizilmedi "
              "(önce: python3 scripts/simulate_and_tune.py --seeds 100 --scenario all "
              "--save-fitness-runs)")
        return
    df = pd.read_csv(fpath) if fpath.exists() else None
    scen_order = ["robot_failure", "mixed_stress", "deadline_pressure"]
    scen_labels = {"robot_failure": "Robot Failure",
                   "mixed_stress": "Mixed Stress",
                   "deadline_pressure": "Deadline Pressure"}

    fig, ax = plt.subplots(figsize=(DOUBLE_COL_W, 3.55))
    n_m = len(METHOD_ORDER)
    x_pos = np.arange(len(scen_order))

    required = {"scenario", "strategy", "seed", "alloc_fitness"}
    has_seedwise = raw_df is not None and required.issubset(raw_df.columns)
    if has_seedwise:
        raw_df = raw_df[raw_df["scenario"].isin(scen_order) &
                        raw_df["strategy"].isin(METHOD_ORDER)].copy()
        offsets = (np.arange(n_m) - (n_m - 1) / 2) * 0.21
        for i, m in enumerate(METHOD_ORDER):
            samples = [raw_df.loc[(raw_df["scenario"] == s) &
                                  (raw_df["strategy"] == m), "alloc_fitness"].to_numpy()
                       for s in scen_order]
            if not all(len(v) for v in samples):
                raise ValueError(f"Eksik tohum-verisi: {m}")
            positions = x_pos + offsets[i]
            bp = ax.boxplot(
                samples, positions=positions, widths=0.17, patch_artist=True,
                showmeans=True, showfliers=True, manage_ticks=False,
                boxprops={"facecolor": METHOD_PALETTE[m], "alpha": 0.72,
                          "edgecolor": "black", "linewidth": 1.3 if m == PROPOSED else 0.7},
                medianprops={"color": "black", "linewidth": 1.1},
                whiskerprops={"color": "black", "linewidth": 0.7},
                capprops={"color": "black", "linewidth": 0.7},
                meanprops={"marker": "D", "markerfacecolor": "white",
                           "markeredgecolor": "black", "markersize": 4},
                flierprops={"marker": "o", "markerfacecolor": METHOD_PALETTE[m],
                            "markeredgecolor": "none", "markersize": 2, "alpha": 0.35},
            )
            for box in bp["boxes"]:
                box.set_linewidth(1.3 if m == PROPOSED else 0.7)
        legend_handles = [
            mpatches.Patch(facecolor=METHOD_PALETTE[m], edgecolor="black",
                           linewidth=1.3 if m == PROPOSED else 0.7,
                           label=METHOD_LABELS[m])
            for m in METHOD_ORDER
        ]
        ax.legend(handles=legend_handles, loc="lower center",
                  bbox_to_anchor=(0.5, 1.01), ncol=4, frameon=False,
                  columnspacing=1.4, handlelength=2.0)
    else:
        # Backward-compatible summary view; this deliberately is not labelled
        # as a box plot because means and standard deviations do not identify
        # a distribution or its quartiles.
        bar_w = 0.8 / n_m
        for i, m in enumerate(METHOD_ORDER):
            vals, errs = [], []
            for s in scen_order:
                sel = df[(df["scenario"] == s) & (df["strategy"] == m)]
                vals.append(float(sel["fitness_mean"].iloc[0]) if len(sel) else 0.0)
                errs.append(float(sel["fitness_std"].iloc[0]) if len(sel) else 0.0)
            offset = (i - (n_m - 1) / 2) * bar_w
            ax.bar(x_pos + offset, vals, bar_w, yerr=errs,
                   label=METHOD_LABELS[m], color=METHOD_PALETTE[m],
                   edgecolor="black", linewidth=1.2 if m == PROPOSED else 0.5,
                   error_kw={"linewidth": 0.6, "capsize": 2})
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01),
                  ncol=4, frameon=False, columnspacing=1.4, handlelength=2.0)

    ax.set_xticks(x_pos)
    ax.set_xticklabels([scen_labels[s] for s in scen_order])
    ax.set_ylabel("Allocation fitness ($\\uparrow$ better)")
    ax.set_ylim(0, 0.78)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fpath_out = out_dir / "fitness_comparison.png"
    fig.savefig(fpath_out, dpi=dpi)
    plt.close(fig)
    print(f"[OK]  {fpath_out}")


def plot_scalability_panel(processed_dir: Path, out_dir: Path, dpi: int) -> None:
    """Robot-count sweep: (a) fitness (b) CR (c) recovery (d) latency.

    Source: simulate_and_tune.py --robot-counts 3,5,10 → sim_scalability.csv
    (Nav2-independent sim, mean over the three scenarios).
    """
    fpath = processed_dir / "sim_scalability.csv"
    if not fpath.exists():
        print(f"[skip] {fpath.name} yok — ölçek paneli çizilmedi "
              "(önce: python3 scripts/simulate_and_tune.py --seeds 100 "
              "--scenario all --robot-counts 3,5,10)")
        return
    df = pd.read_csv(fpath)
    panels = [("fitness", "Allocation Fitness $\\uparrow$"),
              ("cr", "Completion Rate $\\uparrow$"),
              ("recovery", "Recovery Time (s) $\\downarrow$"),
              ("latency", "Decision Latency (ms) $\\downarrow$")]
    robots = sorted(df["robot_count"].unique())

    fig, axes = plt.subplots(2, 2, figsize=(DOUBLE_COL_W, 5.2))
    axes = axes.flatten()
    for k, (ax, (col, ylabel)) in enumerate(zip(axes, panels)):
        for m in METHOD_ORDER:
            ys = []
            for r in robots:
                sel = df[(df["robot_count"] == r) & (df["strategy"] == m)]
                # recovery == -1 → no failure data; exclude from the mean
                vals = sel[col][sel[col] > -1] if col == "recovery" else sel[col]
                ys.append(float(vals.mean()) if len(vals) else np.nan)
            ax.plot(robots, ys, marker="o", markersize=5,
                    linewidth=1.8 if m == PROPOSED else 1.4,
                    label=METHOD_LABELS[m], color=METHOD_PALETTE[m],
                    markeredgecolor="black", markeredgewidth=0.4)
        ax.set_xlabel("Robot count $N$")
        ax.set_ylabel(ylabel)
        ax.set_xticks(robots)
        if col == "latency":
            ax.set_yscale("log")
            ax.set_ylabel(ylabel + " (log)")
        ax.set_title(f"({chr(97 + k)})", fontsize=9, loc="left")
    # Shared legend below all four panels so it never overlaps the curves.
    handles, labels = axes[0].get_legend_handles_labels()
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False,
               fontsize=8, bbox_to_anchor=(0.5, 0.0))
    fpath_out = out_dir / "scalability_panel.png"
    fig.savefig(fpath_out, dpi=dpi)
    plt.close(fig)
    print(f"[OK]  {fpath_out}")


def plot_task_completion_timeline(df_task: Optional[pd.DataFrame],
                                  out_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE_COL_W, 3.0))

    if df_task is not None and "robot_count" in df_task.columns:
        df_task = df_task[df_task["robot_count"] == 3]

    event_col = "event" if df_task is not None and "event" in df_task.columns else "status"
    time_col = next((c for c in ["timestamp_s", "completed_rel", "time_s"]
                     if df_task is not None and c in df_task.columns), None)

    for k, (ax, scenario) in enumerate(zip(axes, ["robot_failure", "mixed_stress"])):
        ax.set_title(f"({chr(97 + k)}) {scenario.replace('_', ' ').title()} (3-Robot)",
                     fontsize=9)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Avg cumul. completed tasks")

        if df_task is None or df_task.empty or time_col is None:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes)
            continue

        scen_df = df_task[df_task["scenario"] == scenario] \
            if "scenario" in df_task.columns else df_task
        if scen_df.empty:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes)
            continue

        t0_map = scen_df[scen_df[event_col] == "activated"].groupby("experiment_id")[time_col].min()
        t0_map = t0_map.combine_first(scen_df.groupby("experiment_id")[time_col].min())
        scen_df = scen_df.copy()
        scen_df["time_rel"] = scen_df.apply(lambda r: r[time_col] - t0_map.get(r["experiment_id"], 0.0), axis=1)

        methods = _ordered_methods(scen_df)
        max_t = scen_df["time_rel"].max()
        for method in methods:
            mdf = scen_df[(scen_df["strategy"] == method) & (scen_df[event_col] == "completed")]
            if mdf.empty:
                continue
            n_exp = mdf["experiment_id"].nunique() if "experiment_id" in mdf.columns else 1
            t_sorted = np.sort(mdf["time_rel"].dropna().values)
            cumulative = np.arange(1, len(t_sorted) + 1) / max(n_exp, 1)
            t_sorted = np.insert(t_sorted, 0, 0.0)
            cumulative = np.insert(cumulative, 0, 0.0)
            
            # Extend to max_t so the line doesn't abruptly end
            if len(t_sorted) > 0 and t_sorted[-1] < max_t:
                t_sorted = np.append(t_sorted, max_t)
                cumulative = np.append(cumulative, cumulative[-1])

            ax.step(t_sorted, cumulative, where='post',
                    label=METHOD_LABELS.get(method, method),
                    color=METHOD_PALETTE.get(method, "#999999"),
                    linewidth=2.0 if method == PROPOSED else 1.3)

    axes[1].legend(fontsize=8, ncol=2, loc="lower right")
    fig.tight_layout()
    out_path = out_dir / "task_completion_timeline.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate paper figures from processed CSVs.")
    parser.add_argument("--processed-dir", default="results/processed")
    parser.add_argument("--output-dir", default="paper/figure")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    processed_dir = Path(args.processed_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dpi = args.dpi

    print(f"Reading from:  {processed_dir}")
    print(f"Writing to:    {out_dir}")
    print(f"DPI:           {dpi}\n")

    df_summary  = _load(processed_dir, "all_summary.csv")
    df_task     = _load(processed_dir, "all_task_events.csv")
    df_alloc    = _load(processed_dir, "all_allocation_events.csv")
    df_comm     = _load(processed_dir, "all_communication.csv")
    df_eco      = _load(processed_dir, "all_ecosystem_metrics.csv")
    df_10r      = _load(processed_dir / "gazebo_10r", "all_summary.csv")

    # Figures 1 and 2 (fig1.drawio / fig2.drawio) are hand-authored draw.io
    # assets under paper/figure/, edited directly rather than generated here.

    # Nav2-independent simulator figures
    plot_fitness_comparison(processed_dir, out_dir, dpi)
    plot_scalability_panel(processed_dir, out_dir, dpi)

    # Gazebo benchmark figures. The multi-metric and failure-recovery figures
    # are reported at the PRIMARY 5-robot / 25-task scale; all_summary.csv pools
    # all scales, so filter here to match the captions (otherwise 3r/5r/10r mix).
    df_primary = df_summary
    if (df_summary is not None and
            {"robot_count", "target_count"}.issubset(df_summary.columns)):
        df_primary = df_summary[(df_summary["robot_count"] == 5) &
                                (df_summary["target_count"] == 25)]
    plot_baseline_comparison(df_primary, out_dir, dpi,
                             "baseline_comparison_multi_metric.png",
                             scenarios=["robot_failure", "mixed_stress"])
    plot_baseline_comparison(df_10r, out_dir, dpi,
                             "baseline_comparison_10r.png")
    plot_failure_recovery(df_primary, out_dir, dpi)
    plot_dominance_recovery_panel(df_eco, df_alloc, df_summary, df_task, out_dir, dpi)
    plot_communication_footprint(df_comm, out_dir, dpi)
    plot_task_completion_timeline(df_task, out_dir, dpi)

    print(f"\n[DONE] All figures written to {out_dir}")


if __name__ == "__main__":
    main()
