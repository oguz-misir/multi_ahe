#!/usr/bin/env python3
"""
Phase 10 — Layer 3: Generate paper figures from processed CSV files.

Usage:
    python3 scripts/plot_results.py \
        --processed-dir results/processed/ \
        --output-dir results/paper_figures/ \
        --dpi 300
"""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from pathlib import Path
from typing import Optional

# ── Global style ───────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.2,
})

SINGLE_COL_W = 3.5   # inches
DOUBLE_COL_W = 7.0   # inches

# ── Fixed method order (proposed method last, highlighted) ──────────────────────
METHOD_ORDER = [
    "greedy_nearest",
    "deadline_aware",
    "auction_based",
    "static_weighted",
    "big_mrta",
    "rostam_ea",
    "consensus_dbta",
    "ahe_no_dominance",
    "ahe_no_cooperation_suppression",
    "ahe_no_event_replanning",
    "ahe_fixed_context",
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

PROPOSED = "full_ahe_mrta"
ABLATION_SET = [
    "full_ahe_mrta", "ahe_no_dominance", "ahe_no_cooperation_suppression",
    "ahe_no_event_replanning", "ahe_fixed_context",
]

HEURISTIC_COLS = [
    "spatial_opportunist", "criticality_guardian", "temporal_regulator",
    "resource_distributor", "energy_conservator", "stability_controller",
    "recovery_coordinator",
]
HEURISTIC_LABELS = [
    "Spatial", "Criticality", "Temporal", "Resource",
    "Energy", "Stability", "Recovery",
]

WEIGHT_COLS = ["w_distance", "w_priority", "w_battery", "w_load",
               "w_failure", "w_deadline", "w_recovery"]
WEIGHT_LABELS = ["Dist", "Priority", "Battery", "Load", "Failure", "Deadline", "Recovery"]

CONTEXT_COLS = ["task_density", "robot_availability", "battery_risk",
                "deadline_pressure", "failure_rate", "workload_variance",
                "allocation_instability"]
CONTEXT_LABELS = ["Task Density", "Robot Avail.", "Battery Risk",
                  "Deadline Press.", "Failure Rate", "Workload Var.", "Alloc. Instab."]


def _load(processed_dir: Path, fname: str) -> Optional[pd.DataFrame]:
    path = processed_dir / fname
    if not path.exists():
        return None
    df = pd.read_csv(path)
    return df if not df.empty else None


def _method_color(method: str, n_methods: int, idx: int) -> str:
    if method == PROPOSED:
        return "#d62728"  # red highlight
    cmap = plt.get_cmap("tab10")
    return cmap(idx / max(n_methods - 1, 1))


def _bar_panel(ax, df, methods, metric, ylabel, higher_better: bool = True):
    """Draw grouped bar with std error bars for one metric."""
    valid_methods = [m for m in methods if m in df["strategy"].unique()]
    means, stds, colors = [], [], []
    for i, m in enumerate(valid_methods):
        vals = df[df["strategy"] == m][metric].dropna()
        means.append(vals.mean() if len(vals) else 0.0)
        stds.append(vals.std() if len(vals) > 1 else 0.0)
        colors.append(_method_color(m, len(valid_methods), i))

    x = np.arange(len(valid_methods))
    bars = ax.bar(x, means, yerr=stds, capsize=3, color=colors,
                  error_kw={"linewidth": 0.8})
    ax.set_xticks(x)
    ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in valid_methods],
                       rotation=45, ha="right")
    ax.set_ylabel(ylabel)
    direction = "↑ better" if higher_better else "↓ better"
    ax.set_title(f"{metric.replace('_', ' ').title()} ({direction})", fontsize=8)
    return bars


def _ordered_methods(df: pd.DataFrame, subset=None) -> list:
    available = df["strategy"].unique() if df is not None else []
    order = subset if subset else METHOD_ORDER
    return [m for m in order if m in available]


# ── Static architecture diagrams ────────────────────────────────────────────────

def plot_system_overview(out_dir: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(DOUBLE_COL_W, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_title("AHE-MRTA System Architecture", fontsize=10, fontweight="bold", pad=8)

    boxes = [
        # (x, y, w, h, label, facecolor)
        (0.3, 5.5, 3.2, 1.0, "Task Manager\n(goal pool, batch release, deadlines)", "#aec6cf"),
        (3.9, 5.5, 3.2, 1.0, "Ecosystem Manager\n(context vector, dominance, W(t))", "#c8e6c9"),
        (7.1, 5.5, 2.5, 1.0, "AHE Allocator\n(reads W(t), assigns tasks)", "#ffe0b2"),
        (0.3, 3.2, 2.2, 1.0, "Robot Interface 1\n(Nav2 client, state machine)", "#e1bee7"),
        (3.0, 3.2, 2.2, 1.0, "Robot Interface 2\n(Nav2 client, state machine)", "#e1bee7"),
        (5.7, 3.2, 2.2, 1.0, "Robot Interface 3\n(Nav2 client, state machine)", "#e1bee7"),
        (7.9, 3.2, 1.8, 1.0, "...", "#e1bee7"),
        (1.0, 0.8, 7.5, 1.0, "Nav2 + Gazebo Harmonic (TurtleBot3 Waffle Pi, headless)", "#fff9c4"),
        (0.3, -0.5, 9.4, 1.0, "Evaluation Logger  →  results/raw/<exp_id>/*.csv", "#f5f5f5"),
    ]

    for (x, y, w, h, lbl, fc) in boxes:
        rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                                       facecolor=fc, edgecolor="#555", linewidth=0.8)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, lbl, ha="center", va="center",
                fontsize=7.5, wrap=True)

    # Arrows
    arrow_kw = dict(arrowstyle="-|>", color="#333", lw=0.9,
                    connectionstyle="arc3,rad=0.0")
    # Task Manager → Robot Interfaces (global_pool)
    for rx in [1.4, 4.1, 6.8]:
        ax.annotate("", xy=(rx, 4.2), xytext=(rx, 5.5),
                    arrowprops=dict(arrowstyle="-|>", color="#555", lw=0.8))
    ax.text(2.2, 4.85, "/tasks/\nglobal_pool", fontsize=6.5, color="#333", ha="center")
    # AHE Allocator → Robot Interfaces (optimized_task_queue)
    for rx in [1.4, 4.1, 6.8]:
        ax.annotate("", xy=(rx + 0.5, 4.2), xytext=(8.35, 5.5),
                    arrowprops=dict(arrowstyle="-|>", color="#d62728", lw=0.8))
    ax.text(5.8, 4.6, "/robot_N/\noptimized_task_queue", fontsize=6.5, color="#d62728", ha="center")
    # Robot Interfaces → Nav2
    for rx in [1.4, 4.1, 6.8]:
        ax.annotate("", xy=(rx, 1.8), xytext=(rx, 3.2),
                    arrowprops=dict(arrowstyle="<->", color="#555", lw=0.8))
    # Note: EcosystemState NOT sent to robots
    ax.text(8.4, 4.95, "EcosystemState\n(debug only, NOT\nsent to robots)",
            fontsize=6.0, color="#888", ha="center", style="italic")

    fig.tight_layout()
    out_path = out_dir / "system_overview.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_adaptive_ecosystem_mechanism(out_dir: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(DOUBLE_COL_W, 5.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title("AHE Adaptive Ecosystem Mechanism", fontsize=10, fontweight="bold", pad=8)

    def box(x, y, w, h, lbl, fc, fs=7.5):
        rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                       facecolor=fc, edgecolor="#555", linewidth=0.8)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, lbl, ha="center", va="center", fontsize=fs)

    def arrow(x1, y1, x2, y2, lbl="", color="#555"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=0.9))
        if lbl:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my, lbl, fontsize=6.5, color=color, ha="center")

    # Context vector
    box(0.2, 6.2, 2.8, 1.3,
        "Context Vector C(t)\n" + r"$\tau$, $\rho$, $\beta$, $\delta$, $\phi$, $\omega$, $\alpha$",
        "#dceefb")

    # K strategy agents
    box(3.8, 6.2, 3.0, 1.3,
        "K=7 Strategy Agents\nSpatial · Criticality · Temporal\nResource · Energy · Stability · Recovery",
        "#e8f5e9")

    # Dominance update
    box(3.5, 4.0, 3.6, 1.5,
        "Dominance Update\n" +
        r"$D(t+1)=\mathrm{clip}[\alpha D+\beta P+\gamma K(C)$" + "\n" +
        r"$+\eta A\cdot D - \lambda S\cdot D - \delta F]$",
        "#fff8e1", fs=7)

    # Cooperation/Suppression
    box(0.2, 4.0, 2.8, 1.5,
        "Cooperation A (7×7)\nSuppression S (7×7)\n(fixed interaction matrices)",
        "#fce4ec")

    # Weight generation
    box(3.8, 1.8, 3.0, 1.5,
        "Weight Generation\n" +
        r"$W(t)=\mathrm{softmax}(M \cdot D(t))$" + "\n(heuristic-to-weight map M)",
        "#ede7f6")

    # Event-triggered replanning
    box(7.2, 3.0, 2.5, 1.2,
        "Event-Triggered\nReplanning\n(failure, new task, deadline)",
        "#fff3e0")

    # Allocator output
    box(3.8, 0.2, 3.0, 1.1,
        "AHE Allocator\nassigns tasks with W(t)",
        "#d62728", fs=7.5)
    ax.findobj(mpatches.FancyBboxPatch)[-1].set_edgecolor("#d62728")
    ax.findobj(mpatches.FancyBboxPatch)[-1].set_facecolor("#ffcdd2")

    # Arrows
    arrow(3.0, 6.85, 3.8, 6.85, "K(C)")
    arrow(3.0, 4.75, 3.5, 4.75, "A, S")
    arrow(5.3, 6.2, 5.3, 5.5, "D(t)")
    arrow(5.3, 4.0, 5.3, 3.3, "D(t+1)")
    arrow(5.3, 1.8, 5.3, 1.3, "W(t)", color="#d62728")
    arrow(7.2, 3.6, 6.9, 4.6, "replan trigger", color="#e65100")
    arrow(1.4, 6.2, 1.4, 5.5, "C(t)")
    arrow(1.4, 4.0, 1.4, 3.3, "to D update")

    # EcosystemState debug note
    ax.text(0.25, 0.3, "EcosystemState → /ecosystem/debug_state  (NOT sent to robots)",
            fontsize=6.5, color="#888", style="italic")

    fig.tight_layout()
    out_path = out_dir / "adaptive_ecosystem_mechanism.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


# ── Data-driven figures ─────────────────────────────────────────────────────────

def plot_baseline_comparison(df_summary: Optional[pd.DataFrame], out_dir: Path, dpi: int) -> None:
    metrics = [
        ("task_completion_rate",    "Task Completion Rate",   True),
        ("makespan_s",              "Makespan (s)",            False),
        ("average_task_delay",      "Avg Task Delay (s)",      False),
        ("workload_balance",        "Workload Balance",        True),
        ("deadline_violation_rate", "Deadline Violation Rate", False),
        ("mean_decision_latency_ms","Decision Latency (ms)",   False),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(DOUBLE_COL_W, 4.5))
    axes = axes.flatten()

    if df_summary is None or df_summary.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No data yet", ha="center", va="center", transform=ax.transAxes)
        fig.suptitle("Fig. 3 — Baseline Comparison (no data)", fontsize=9)
    else:
        methods = _ordered_methods(df_summary)
        for ax, (metric, ylabel, higher_better) in zip(axes, metrics):
            if metric not in df_summary.columns:
                ax.text(0.5, 0.5, f"{metric}\ncolumn missing",
                        ha="center", va="center", transform=ax.transAxes)
                continue
            _bar_panel(ax, df_summary, methods, metric, ylabel, higher_better)
        fig.suptitle("Fig. 3 — Baseline Comparison (mean ± std across seeds)", fontsize=9)

    fig.tight_layout()
    out_path = out_dir / "baseline_comparison_multi_metric.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_ablation_comparison(df_summary: Optional[pd.DataFrame], out_dir: Path, dpi: int) -> None:
    metrics = [
        ("average_task_delay",    "Avg Task Delay (s)",    False),
        ("workload_balance",      "Workload Balance",       True),
        ("failure_recovery_time", "Failure Recovery (s)",  False),
        ("allocation_instability","Alloc. Instability",     False),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(DOUBLE_COL_W, 2.8))

    if df_summary is None or df_summary.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No data yet", ha="center", va="center", transform=ax.transAxes)
        fig.suptitle("Fig. 4 — Ablation Study (no data)", fontsize=9)
    else:
        methods = _ordered_methods(df_summary, ABLATION_SET)
        for ax, (metric, ylabel, higher_better) in zip(axes, metrics):
            if metric not in df_summary.columns:
                ax.text(0.5, 0.5, f"{metric}\nmissing", ha="center", va="center",
                        transform=ax.transAxes)
                continue
            _bar_panel(ax, df_summary, methods, metric, ylabel, higher_better)
        fig.suptitle("Fig. 4 — AHE Ablation Study (mean ± std across seeds)", fontsize=9)

    fig.tight_layout()
    out_path = out_dir / "ablation_comparison.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_dominance_evolution(df_eco: Optional[pd.DataFrame],
                             df_alloc: Optional[pd.DataFrame],
                             out_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(DOUBLE_COL_W, 5.5), sharex=True)

    if df_eco is None or df_eco.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No ecosystem data yet", ha="center", va="center",
                    transform=ax.transAxes)
        axes[0].set_title("Fig. 5a — Dominance Evolution (no data)", fontsize=9)
    else:
        # Use first seed of full_ahe_mrta robot_failure scenario as representative run
        subset = df_eco[df_eco["strategy"] == PROPOSED]
        if "scenario" in subset.columns:
            rf = subset[subset["scenario"] == "robot_failure"]
            if not rf.empty:
                subset = rf
        if "seed" in subset.columns:
            subset = subset[subset["seed"] == subset["seed"].min()]

        t = subset["time"] if "time" in subset.columns else np.arange(len(subset))

        # Panel (a) — dominance values
        ax = axes[0]
        colors = plt.get_cmap("tab10")(np.linspace(0, 0.9, len(HEURISTIC_COLS)))
        for col, lbl, c in zip(HEURISTIC_COLS, HEURISTIC_LABELS, colors):
            if col in subset.columns:
                ax.plot(t, subset[col], label=lbl, color=c)
        ax.set_ylabel("Dominance D(t)")
        ax.set_title("(a) Strategy agent dominance over time", fontsize=8)
        ax.legend(loc="upper right", ncol=4, fontsize=6.5)

        # Panel (b) — context vector
        ax = axes[1]
        for col, lbl, c in zip(CONTEXT_COLS, CONTEXT_LABELS, colors):
            if col in subset.columns:
                ax.plot(t, subset[col], label=lbl, color=c, linestyle="--")
        ax.set_ylabel("Context C(t)")
        ax.set_title("(b) Context vector evolution", fontsize=8)
        ax.legend(loc="upper right", ncol=4, fontsize=6.5)

        # Panel (c) — weights
        ax = axes[2]
        for col, lbl, c in zip(WEIGHT_COLS, WEIGHT_LABELS, colors):
            if col in subset.columns:
                ax.plot(t, subset[col], label=lbl, color=c)
        ax.set_ylabel("Weight W(t)")
        ax.set_title("(c) Allocation weight evolution", fontsize=8)
        ax.legend(loc="upper right", ncol=4, fontsize=6.5)
        ax.set_xlabel("Time (s)")

        # Event markers
        if df_alloc is not None and not df_alloc.empty:
            ae = df_alloc[df_alloc["strategy"] == PROPOSED]
            for event_type, color, label in [
                ("robot_failure",    "#d62728", "Robot Failure"),
                ("critical_task",    "#ff7f0e", "Critical Task"),
                ("deadline_pressure","#2ca02c", "Deadline ↑"),
            ]:
                events = ae[ae["event_type"].str.contains(event_type, na=False)]
                for _, row in events.head(3).iterrows():
                    for ax in axes:
                        ax.axvline(row.get("time", 0), color=color,
                                   linestyle=":", alpha=0.7, linewidth=0.9)
                if not events.empty:
                    axes[0].axvline(events.iloc[0].get("time", 0), color=color,
                                    linestyle=":", alpha=0.7, linewidth=0.9,
                                    label=label)
            axes[0].legend(loc="upper right", ncol=3, fontsize=6.0)

    fig.tight_layout()
    out_path = out_dir / "dominance_evolution.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_failure_recovery(df_summary: Optional[pd.DataFrame],
                          df_alloc: Optional[pd.DataFrame],
                          out_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(DOUBLE_COL_W, 2.8))

    if df_summary is None or df_summary.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No data yet", ha="center", va="center", transform=ax.transAxes)
    else:
        methods = _ordered_methods(df_summary)
        _bar_panel(axes[0], df_summary, methods, "failure_recovery_time",
                   "Recovery Time (s)", False)

        # Recovery success rate (tasks_completed / tasks_total in robot_failure scenario)
        ax = axes[1]
        rf = df_summary[df_summary.get("scenario", pd.Series(dtype=str)) == "robot_failure"] \
            if "scenario" in df_summary.columns else df_summary
        if not rf.empty and "task_completion_rate" in rf.columns:
            _bar_panel(ax, rf, methods, "task_completion_rate",
                       "Completion Rate\n(robot_failure)", True)
        else:
            ax.text(0.5, 0.5, "robot_failure\nscenario N/A",
                    ha="center", va="center", transform=ax.transAxes)

        _bar_panel(axes[2], df_summary, methods, "replanning_frequency",
                   "Replanning Frequency", False)

    fig.suptitle("Failure Recovery Behavior", fontsize=9)
    fig.tight_layout()
    out_path = out_dir / "failure_recovery.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_dominance_recovery_panel(df_eco: Optional[pd.DataFrame],
                                  df_alloc: Optional[pd.DataFrame],
                                  df_summary: Optional[pd.DataFrame],
                                  out_dir: Path, dpi: int) -> None:
    """Fig. 5 — combined dominance evolution + failure recovery."""
    fig = plt.figure(figsize=(DOUBLE_COL_W, 5.5))
    gs = fig.add_gridspec(3, 2, hspace=0.45, wspace=0.4)

    ax_dom = fig.add_subplot(gs[0:2, 0])
    ax_ctx = fig.add_subplot(gs[2, 0])
    ax_rec = fig.add_subplot(gs[0, 1])
    ax_replan = fig.add_subplot(gs[1, 1])
    ax_inst = fig.add_subplot(gs[2, 1])

    for ax in [ax_dom, ax_ctx, ax_rec, ax_replan, ax_inst]:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Left: dominance (representative run)
    if df_eco is not None and not df_eco.empty:
        subset = df_eco[df_eco["strategy"] == PROPOSED]
        if "scenario" in subset.columns:
            rf = subset[subset["scenario"] == "robot_failure"]
            if not rf.empty:
                subset = rf
        if "seed" in subset.columns:
            subset = subset[subset["seed"] == subset["seed"].min()]
        t = subset["time"] if "time" in subset.columns else np.arange(len(subset))
        colors = plt.get_cmap("tab10")(np.linspace(0, 0.9, len(HEURISTIC_COLS)))
        for col, lbl, c in zip(HEURISTIC_COLS, HEURISTIC_LABELS, colors):
            if col in subset.columns:
                ax_dom.plot(t, subset[col], label=lbl, color=c, linewidth=1.0)
        ax_dom.set_ylabel("Dominance D(t)")
        ax_dom.set_title("(a) Dominance evolution\n(robot_failure, AHE-MRTA)", fontsize=8)
        ax_dom.legend(loc="upper right", ncol=2, fontsize=6)

        for col, lbl, c in zip(CONTEXT_COLS[:4], CONTEXT_LABELS[:4], colors):
            if col in subset.columns:
                ax_ctx.plot(t, subset[col], label=lbl, color=c, linestyle="--", linewidth=0.9)
        ax_ctx.set_ylabel("Context C(t)")
        ax_ctx.set_xlabel("Time (s)")
        ax_ctx.set_title("(b) Context vector", fontsize=8)
        ax_ctx.legend(loc="upper right", ncol=2, fontsize=6)

        if df_alloc is not None and not df_alloc.empty:
            ae = df_alloc[df_alloc["strategy"] == PROPOSED]
            rf_events = ae[ae["event_type"].str.contains("robot_failure", na=False)]
            for _, row in rf_events.head(1).iterrows():
                for ax in [ax_dom, ax_ctx]:
                    ax.axvline(row.get("time", 0), color="#d62728",
                               linestyle=":", alpha=0.8, linewidth=0.9, label="Robot Failure")
    else:
        ax_dom.text(0.5, 0.5, "No ecosystem data", ha="center", va="center",
                    transform=ax_dom.transAxes)
        ax_ctx.text(0.5, 0.5, "No context data", ha="center", va="center",
                    transform=ax_ctx.transAxes)

    # Right: recovery metrics
    if df_summary is not None and not df_summary.empty:
        methods = _ordered_methods(df_summary)
        _bar_panel(ax_rec, df_summary, methods, "failure_recovery_time",
                   "Recovery Time (s)", False)
        ax_rec.set_title("(c) Failure recovery time", fontsize=8)
        _bar_panel(ax_replan, df_summary, methods, "replanning_frequency",
                   "Replanning Freq.", False)
        ax_replan.set_title("(d) Replanning frequency", fontsize=8)
        _bar_panel(ax_inst, df_summary, methods, "allocation_instability",
                   "Alloc. Instability", False)
        ax_inst.set_title("(e) Allocation instability", fontsize=8)
    else:
        for ax, lbl in [(ax_rec, "(c)"), (ax_replan, "(d)"), (ax_inst, "(e)")]:
            ax.text(0.5, 0.5, f"{lbl}\nNo data", ha="center", va="center", transform=ax.transAxes)

    fig.suptitle("Fig. 5 — Interpretable Adaptation & Failure Recovery", fontsize=9, fontweight="bold")
    out_path = out_dir / "dominance_recovery_panel.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_communication_footprint(df_comm: Optional[pd.DataFrame], out_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(DOUBLE_COL_W, 2.8))

    if df_comm is None or df_comm.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No comm data yet", ha="center", va="center", transform=ax.transAxes)
    else:
        methods = _ordered_methods(df_comm)
        comm_bytes_col = "bytes_transmitted" if "bytes_transmitted" in df_comm.columns else "communication_bytes"
        _bar_panel(axes[0], df_comm, methods, "message_count", "Message Count", False)
        if comm_bytes_col in df_comm.columns:
            _bar_panel(axes[1], df_comm, methods, comm_bytes_col, "Bytes Transmitted", False)
        else:
            axes[1].text(0.5, 0.5, "bytes\nN/A", ha="center", va="center", transform=axes[1].transAxes)
        if "topic_count" in df_comm.columns:
            _bar_panel(axes[2], df_comm, methods, "topic_count", "Topic Count", False)
        else:
            axes[2].text(0.5, 0.5, "topic_count\nN/A", ha="center", va="center", transform=axes[2].transAxes)

    fig.suptitle("Communication Footprint", fontsize=9)
    fig.tight_layout()
    out_path = out_dir / "communication_footprint.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_communication_scalability_panel(df_comm: Optional[pd.DataFrame],
                                         df_summary: Optional[pd.DataFrame],
                                         df_runtime: Optional[pd.DataFrame],
                                         out_dir: Path, dpi: int) -> None:
    """Fig. 6 — communication efficiency + compact scalability sanity."""
    fig, axes = plt.subplots(2, 3, figsize=(DOUBLE_COL_W, 4.5))

    # Row 0: communication
    if df_comm is not None and not df_comm.empty:
        methods = _ordered_methods(df_comm)
        comm_bytes_col = "bytes_transmitted" if "bytes_transmitted" in df_comm.columns else "communication_bytes"
        _bar_panel(axes[0, 0], df_comm, methods, "message_count", "Message Count", False)
        axes[0, 0].set_title("(a) Messages per allocation round", fontsize=8)
        if comm_bytes_col in df_comm.columns:
            _bar_panel(axes[0, 1], df_comm, methods, comm_bytes_col, "Bytes Tx", False)
        axes[0, 1].set_title("(b) Bytes transmitted", fontsize=8)
        if "topic_count" in df_comm.columns:
            _bar_panel(axes[0, 2], df_comm, methods, "topic_count", "Topic Count", False)
        axes[0, 2].set_title("(c) Topic count", fontsize=8)
    else:
        for ax in axes[0]:
            ax.text(0.5, 0.5, "No comm data", ha="center", va="center", transform=ax.transAxes)

    # Row 1: scalability (3/15 vs 5/25)
    if df_summary is not None and not df_summary.empty and "robot_count" in df_summary.columns:
        for scale_idx, (rc, tc) in enumerate([(3, 15), (5, 25)]):
            sub = df_summary[(df_summary["robot_count"] == rc) & (df_summary["target_count"] == tc)]
            if sub.empty:
                continue
            methods = _ordered_methods(sub)
            ax = axes[1, scale_idx]
            _bar_panel(ax, sub, methods, "makespan_s", "Makespan (s)", False)
            ax.set_title(f"({chr(100+scale_idx)}) Makespan — {rc}R/{tc}T scale", fontsize=8)

        if df_runtime is not None and not df_runtime.empty and "robot_count" in df_runtime.columns:
            ax = axes[1, 2]
            for rc, tc, ls in [(3, 15, "-"), (5, 25, "--")]:
                sub = df_runtime[(df_runtime["robot_count"] == rc) & (df_runtime["target_count"] == tc)]
                if sub.empty:
                    continue
                methods = _ordered_methods(sub)
                means = [sub[sub["strategy"] == m]["runtime_ms"].mean() for m in methods]
                ax.plot([METHOD_LABELS.get(m, m) for m in methods], means,
                        marker="o", linestyle=ls, markersize=4, label=f"{rc}R/{tc}T")
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
            ax.set_ylabel("Runtime (ms)")
            ax.set_title("(f) Decision latency scalability", fontsize=8)
            ax.legend(fontsize=7)
        else:
            axes[1, 2].text(0.5, 0.5, "Runtime scalability\nN/A",
                            ha="center", va="center", transform=axes[1, 2].transAxes)
    else:
        for ax in axes[1]:
            ax.text(0.5, 0.5, "No scalability data", ha="center", va="center", transform=ax.transAxes)

    fig.suptitle("Fig. 6 — Communication Efficiency & Scalability", fontsize=9, fontweight="bold")
    fig.tight_layout()
    out_path = out_dir / "communication_scalability_panel.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_allocation_instability(df_summary: Optional[pd.DataFrame],
                                df_alloc: Optional[pd.DataFrame],
                                out_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(DOUBLE_COL_W, 2.8))

    if df_summary is None or df_summary.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
    else:
        methods = _ordered_methods(df_summary)
        _bar_panel(axes[0], df_summary, methods, "allocation_instability",
                   "Alloc. Instability", False)
        if df_alloc is not None and not df_alloc.empty:
            reassign = df_alloc[df_alloc["event_type"].str.contains("reassign", na=False)]
            reassign_cnt = reassign.groupby("strategy")["task_id"].count().reset_index()
            reassign_cnt.columns = ["strategy", "reassignment_count"]
            _bar_panel(axes[1], reassign_cnt, methods, "reassignment_count",
                       "Reassignment Count", False)
            qv = df_alloc.groupby("strategy")["queue_version"].max().reset_index()
            qv.columns = ["strategy", "max_queue_version"]
            _bar_panel(axes[2], qv, methods, "max_queue_version",
                       "Queue Version Changes", False)
        else:
            for ax in axes[1:]:
                ax.text(0.5, 0.5, "No alloc events", ha="center", va="center", transform=ax.transAxes)

    fig.suptitle("Allocation Instability Analysis", fontsize=9)
    fig.tight_layout()
    out_path = out_dir / "allocation_instability.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_decision_latency(df_runtime: Optional[pd.DataFrame],
                          df_summary: Optional[pd.DataFrame],
                          out_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE_COL_W, 2.8))

    if df_runtime is None or df_runtime.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No runtime data", ha="center", va="center", transform=ax.transAxes)
    else:
        methods = _ordered_methods(df_runtime)
        data = [df_runtime[df_runtime["strategy"] == m]["runtime_ms"].dropna().values
                for m in methods]
        labels = [METHOD_LABELS.get(m, m) for m in methods]
        colors = [_method_color(m, len(methods), i) for i, m in enumerate(methods)]
        bp = axes[0].boxplot(data, labels=labels, patch_artist=True,
                             medianprops={"color": "black", "linewidth": 1.2})
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c)
        axes[0].set_xticklabels(labels, rotation=45, ha="right")
        axes[0].set_ylabel("Runtime (ms)")
        axes[0].set_title("(a) Decision latency distribution (boxplot)", fontsize=8)

    if df_summary is not None and not df_summary.empty and "mean_decision_latency_ms" in df_summary.columns:
        methods = _ordered_methods(df_summary)
        _bar_panel(axes[1], df_summary, methods, "mean_decision_latency_ms",
                   "Mean Latency (ms)", False)
        axes[1].set_title("(b) Mean decision latency", fontsize=8)
    else:
        axes[1].text(0.5, 0.5, "mean_decision_latency_ms\nN/A",
                     ha="center", va="center", transform=axes[1].transAxes)

    fig.suptitle("Decision Latency", fontsize=9)
    fig.tight_layout()
    out_path = out_dir / "decision_latency.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_task_completion_timeline(df_task: Optional[pd.DataFrame], out_dir: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(DOUBLE_COL_W, 3.0))

    if df_task is None or df_task.empty or "completed_rel" not in df_task.columns:
        ax.text(0.5, 0.5, "No task event data", ha="center", va="center", transform=ax.transAxes)
    else:
        methods = _ordered_methods(df_task)
        colors = plt.get_cmap("tab10")(np.linspace(0, 0.9, len(methods)))
        for method, c in zip(methods, colors):
            sub = df_task[(df_task["strategy"] == method) &
                          (df_task["status"] == "completed")]["completed_rel"].dropna()
            if sub.empty:
                continue
            t_sorted = np.sort(sub.values)
            cumulative = np.arange(1, len(t_sorted) + 1)
            lw = 1.8 if method == PROPOSED else 1.0
            ax.plot(t_sorted, cumulative, label=METHOD_LABELS.get(method, method),
                    color=c, linewidth=lw)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Cumulative Completed Tasks")
    ax.set_title("Task Completion Timeline (supplementary)", fontsize=9)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    out_path = out_dir / "task_completion_timeline.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_workload_distribution(df_workload: Optional[pd.DataFrame], out_dir: Path, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(DOUBLE_COL_W, 3.0))

    if df_workload is None or df_workload.empty or "completed_tasks" not in df_workload.columns:
        ax.text(0.5, 0.5, "No workload data", ha="center", va="center", transform=ax.transAxes)
    else:
        methods = _ordered_methods(df_workload)
        data = [df_workload[df_workload["strategy"] == m]["completed_tasks"].dropna().values
                for m in methods]
        labels = [METHOD_LABELS.get(m, m) for m in methods]
        colors = [_method_color(m, len(methods), i) for i, m in enumerate(methods)]
        bp = ax.boxplot(data, labels=labels, patch_artist=True,
                        medianprops={"color": "black", "linewidth": 1.2})
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c)
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_ylabel("Completed Tasks per Robot")
        ax.set_title("Workload Distribution per Robot (supplementary)", fontsize=9)

    fig.tight_layout()
    out_path = out_dir / "workload_distribution.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_compact_scalability(df_summary: Optional[pd.DataFrame],
                             df_runtime: Optional[pd.DataFrame],
                             out_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE_COL_W, 3.0))

    if df_summary is None or df_summary.empty or "robot_count" not in df_summary.columns:
        for ax in axes:
            ax.text(0.5, 0.5, "No scalability data", ha="center", va="center", transform=ax.transAxes)
    else:
        for i, (metric, ylabel, hb) in enumerate([
            ("makespan_s", "Makespan (s)", False),
            ("task_completion_rate", "Completion Rate", True),
        ]):
            ax = axes[i]
            for rc, tc, ls, marker in [(3, 15, "-", "o"), (5, 25, "--", "s")]:
                sub = df_summary[(df_summary["robot_count"] == rc) & (df_summary["target_count"] == tc)]
                if sub.empty or metric not in sub.columns:
                    continue
                methods = _ordered_methods(sub)
                means = [sub[sub["strategy"] == m][metric].mean() for m in methods]
                ax.plot([METHOD_LABELS.get(m, m) for m in methods], means,
                        marker=marker, linestyle=ls, markersize=4, label=f"{rc}R/{tc}T")
            ax.set_xticklabels([METHOD_LABELS.get(m, m) for m in _ordered_methods(df_summary)],
                                rotation=45, ha="right") if ax.get_xticklabels() else None
            ax.set_ylabel(ylabel)
            ax.set_title(f"{'↑' if hb else '↓'} {metric.replace('_',' ').title()}", fontsize=8)
            ax.legend(fontsize=7)

    fig.suptitle("Compact Scalability Sanity Check (3/15 vs 5/25)", fontsize=9)
    fig.tight_layout()
    out_path = out_dir / "compact_scalability_sanity.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate paper figures from processed CSVs.")
    parser.add_argument("--processed-dir", default="results/processed")
    parser.add_argument("--output-dir", default="results/paper_figures")
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
    df_workload = _load(processed_dir, "all_robot_workload.csv")
    df_alloc    = _load(processed_dir, "all_allocation_events.csv")
    df_runtime  = _load(processed_dir, "all_runtime.csv")
    df_comm     = _load(processed_dir, "all_communication.csv")
    df_eco      = _load(processed_dir, "all_ecosystem_metrics.csv")

    # Mandatory static diagrams (always generated)
    plot_system_overview(out_dir, dpi)
    plot_adaptive_ecosystem_mechanism(out_dir, dpi)

    # Data-driven mandatory figures (robust to missing data)
    plot_baseline_comparison(df_summary, out_dir, dpi)
    plot_ablation_comparison(df_summary, out_dir, dpi)
    plot_dominance_evolution(df_eco, df_alloc, out_dir, dpi)
    plot_failure_recovery(df_summary, df_alloc, out_dir, dpi)
    plot_dominance_recovery_panel(df_eco, df_alloc, df_summary, out_dir, dpi)
    plot_communication_footprint(df_comm, out_dir, dpi)
    plot_communication_scalability_panel(df_comm, df_summary, df_runtime, out_dir, dpi)

    # Optional/supplementary figures
    plot_allocation_instability(df_summary, df_alloc, out_dir, dpi)
    plot_decision_latency(df_runtime, df_summary, out_dir, dpi)
    plot_task_completion_timeline(df_task, out_dir, dpi)
    plot_workload_distribution(df_workload, out_dir, dpi)
    plot_compact_scalability(df_summary, df_runtime, out_dir, dpi)

    print(f"\n[DONE] All figures written to {out_dir}")


if __name__ == "__main__":
    main()
