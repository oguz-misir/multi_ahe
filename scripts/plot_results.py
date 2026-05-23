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
    "big_mrta",
    "rostam_ea",
    "consensus_dbta",
    "ahe_mrta_v3_no_bipartite",
    "ahe_mrta_v3_no_dense_init",
    "ahe_mrta_v3_no_recovery",
    "ahe_mrta_v3_fixed_weights",
    "ahe_mrta_v3",
]

METHOD_LABELS = {
    "big_mrta":                     "BiG-MRTA",
    "rostam_ea":                    "RoSTAM-EA",
    "consensus_dbta":               "Cons-DBTA",
    "ahe_mrta_v3_no_bipartite":     "AHE-NoBP",
    "ahe_mrta_v3_no_dense_init":    "AHE-NoDI",
    "ahe_mrta_v3_no_recovery":      "AHE-NoRec",
    "ahe_mrta_v3_fixed_weights":    "AHE-FW",
    "ahe_mrta_v3":                  "AHE-MRTA*",
}

PROPOSED = "ahe_mrta_v3"

# G1 — Main comparison: 3 baselines + proposed
BASELINE_COMPARISON_SET = [
    "big_mrta",
    "rostam_ea",
    "consensus_dbta",
    "ahe_mrta_v3",   # proposed — always last, highlighted red
]

# G2 — Ablation: 4 ablated variants + proposed reference
ABLATION_SET = [
    "ahe_mrta_v3_no_bipartite",
    "ahe_mrta_v3_no_dense_init",
    "ahe_mrta_v3_no_recovery",
    "ahe_mrta_v3_fixed_weights",
    "ahe_mrta_v3",   # reference — always last
]

HEURISTIC_COLS = ["d_0", "d_1", "d_2", "d_3", "d_4", "d_5", "d_6"]
HEURISTIC_LABELS = [
    "Spatial", "Criticality", "Temporal", "Resource",
    "Energy", "Stability", "Recovery",
]

WEIGHT_COLS = ["w_d", "w_p", "w_b", "w_l", "w_f", "w_t", "w_r"]
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
    """Main comparison: SW vs BiG-MRTA vs RoSTAM-EA vs AHE-MRTA* (proposed)."""
    metrics = [
        ("task_completion_rate",    "Task Completion Rate",   True),
        ("tasks_completed",         "Tasks Completed",         True),
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
        # Filter to robot_failure + mixed_stress (common scenarios) for fair comparison
        common = df_summary[df_summary["scenario"].isin(["robot_failure", "mixed_stress"])] \
            if "scenario" in df_summary.columns else df_summary
        methods = _ordered_methods(common, BASELINE_COMPARISON_SET)
        for ax, (metric, ylabel, higher_better) in zip(axes, metrics):
            if metric not in common.columns:
                ax.text(0.5, 0.5, f"{metric}\ncolumn missing",
                        ha="center", va="center", transform=ax.transAxes)
                continue
            _bar_panel(ax, common, methods, metric, ylabel, higher_better)
        fig.suptitle(
            "Fig. 3 — AHE-MRTA* vs Baselines: SW · BiG-MRTA · RoSTAM-EA"
            "  (mean ± std, robot_failure + mixed_stress)", fontsize=9)

    fig.tight_layout()
    out_path = out_dir / "baseline_comparison_multi_metric.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_ablation_comparison(df_summary: Optional[pd.DataFrame], out_dir: Path, dpi: int) -> None:
    """Ablation: AHE-NoD vs AHE-NoER vs AHE-FC vs AHE-MRTA* (full reference)."""
    metrics = [
        ("task_completion_rate",  "Task Completion Rate",  True),
        ("average_task_delay",    "Avg Task Delay (s)",    False),
        ("workload_balance",      "Workload Balance",       True),
        ("failure_recovery_time", "Failure Recovery (s)",  False),
        ("deadline_violation_rate","Deadline Violation",   False),
        ("allocation_instability","Alloc. Instability",    False),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(DOUBLE_COL_W, 4.5))
    axes = axes.flatten()

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
        fig.suptitle(
            "Fig. 4 — AHE Ablation: AHE-NoD · AHE-NoER · AHE-FC vs AHE-MRTA*"
            "  (mean ± std across seeds)", fontsize=9)

    fig.tight_layout()
    out_path = out_dir / "ablation_comparison.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_dominance_evolution(df_eco: Optional[pd.DataFrame],
                             df_alloc: Optional[pd.DataFrame],
                             out_dir: Path, dpi: int) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(DOUBLE_COL_W, 4.2), sharex=True)

    if df_eco is None or df_eco.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No ecosystem data yet", ha="center", va="center",
                    transform=ax.transAxes)
        axes[0].set_title("Fig. 5a — Dominance Evolution (no data)", fontsize=9)
    else:
        subset = df_eco[df_eco["strategy"] == PROPOSED]
        if "scenario" in subset.columns:
            rf = subset[subset["scenario"] == "robot_failure"]
            if not rf.empty:
                subset = rf
        if "seed" in subset.columns:
            subset = subset[subset["seed"] == subset["seed"].min()]

        t_col = next((c for c in ["timestamp_s", "time", "t"] if c in subset.columns), None)
        t = subset[t_col].values if t_col else np.arange(len(subset))

        colors = plt.get_cmap("tab10")(np.linspace(0, 0.9, len(HEURISTIC_COLS)))

        # Panel (a) — dominance D(t)
        ax = axes[0]
        for col, lbl, c in zip(HEURISTIC_COLS, HEURISTIC_LABELS, colors):
            if col in subset.columns:
                ax.plot(t, subset[col], label=lbl, color=c)
        ax.set_ylabel("Dominance D(t)")
        ax.set_title("(a) Strategy agent dominance over time", fontsize=8)
        ax.legend(loc="upper right", ncol=4, fontsize=6.5)

        # Panel (b) — allocation weights W(t)
        ax = axes[1]
        for col, lbl, c in zip(WEIGHT_COLS, WEIGHT_LABELS, colors):
            if col in subset.columns:
                ax.plot(t, subset[col], label=lbl, color=c)
        ax.set_ylabel("Weight W(t)")
        ax.set_title("(b) Allocation weight evolution", fontsize=8)
        ax.legend(loc="upper right", ncol=4, fontsize=6.5)
        ax.set_xlabel("Time (s)")

        # Event markers on both panels
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
        # Filter to robot_failure scenario only for fair comparison
        rf = df_summary[df_summary["scenario"] == "robot_failure"] \
            if "scenario" in df_summary.columns else df_summary
        if rf.empty:
            rf = df_summary
        methods = _ordered_methods(rf)
        _bar_panel(axes[0], rf, methods, "failure_recovery_time",
                   "Recovery Time (s)", False)
        if "task_completion_rate" in rf.columns:
            _bar_panel(axes[1], rf, methods, "task_completion_rate",
                       "Completion Rate\n(robot_failure)", True)
        _bar_panel(axes[2], rf, methods, "replanning_frequency",
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
    fig = plt.figure(figsize=(DOUBLE_COL_W + 1.5, 6.0))
    gs = fig.add_gridspec(3, 2, hspace=0.65, wspace=0.55,
                          left=0.08, right=0.97, top=0.92, bottom=0.08)

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
        t_col2 = next((c for c in ["timestamp_s", "time", "t"] if c in subset.columns), None)
        t = subset[t_col2].values if t_col2 else np.arange(len(subset))
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
        if not any(col in subset.columns for col in CONTEXT_COLS):
            ax_ctx.text(0.5, 0.5, "Not logged\nseparately",
                        ha="center", va="center", transform=ax_ctx.transAxes,
                        fontsize=8, color="gray", style="italic")
        else:
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

    # Right: recovery metrics — filter to robot_failure only
    if df_summary is not None and not df_summary.empty:
        rf_sum = df_summary[df_summary["scenario"] == "robot_failure"] \
            if "scenario" in df_summary.columns else df_summary
        if rf_sum.empty:
            rf_sum = df_summary
        methods = _ordered_methods(rf_sum)
        _bar_panel(ax_rec, rf_sum, methods, "failure_recovery_time",
                   "Recovery Time (s)", False)
        ax_rec.set_title("(c) Failure recovery time", fontsize=8)
        ax_rec.tick_params(axis='x', labelsize=6.5)
        _bar_panel(ax_replan, rf_sum, methods, "replanning_frequency",
                   "Replanning Freq.", False)
        ax_replan.set_title("(d) Replanning frequency", fontsize=8)
        ax_replan.tick_params(axis='x', labelsize=6.5)
        _bar_panel(ax_inst, rf_sum, methods, "allocation_instability",
                   "Alloc. Instability", False)
        ax_inst.set_title("(e) Allocation instability", fontsize=8)
        ax_inst.tick_params(axis='x', labelsize=6.5)
    else:
        for ax, lbl in [(ax_rec, "(c)"), (ax_replan, "(d)"), (ax_inst, "(e)")]:
            ax.text(0.5, 0.5, f"{lbl}\nNo data", ha="center", va="center", transform=ax.transAxes)

    fig.suptitle("Fig. 5 — Interpretable Adaptation & Failure Recovery", fontsize=9, fontweight="bold")
    out_path = out_dir / "dominance_recovery_panel.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_communication_footprint(df_comm: Optional[pd.DataFrame], out_dir: Path, dpi: int) -> None:
    col = next((c for c in ["footprint_bytes", "bytes_transmitted", "communication_bytes"]
                if df_comm is not None and c in df_comm.columns), None)

    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE_COL_W, 3.2))

    if df_comm is None or df_comm.empty or col is None:
        for ax in axes:
            ax.text(0.5, 0.5, "No comm data", ha="center", va="center",
                    transform=ax.transAxes)
        fig.suptitle("Communication Footprint per Allocation Round", fontsize=9)
        fig.tight_layout()
        fig.savefig(out_dir / "communication_footprint.png", dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        return

    methods = _ordered_methods(df_comm)
    labels  = [METHOD_LABELS.get(m, m) for m in methods]
    colors  = [_method_color(m, len(methods), i) for i, m in enumerate(methods)]
    means   = [df_comm[df_comm["strategy"] == m][col].mean() for m in methods]
    errs    = [df_comm[df_comm["strategy"] == m][col].std(ddof=1) for m in methods]

    # Panel (a): log scale — all methods, shows RoSTAM-EA dominance
    ax = axes[0]
    bars = ax.bar(labels, means, color=colors, yerr=errs, capsize=3, error_kw={"linewidth": 0.8})
    ax.set_yscale("log")
    ax.set_ylabel("Bytes / Round (log scale)")
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_title("(a) All methods — log scale", fontsize=8)
    # annotate RoSTAM-EA value
    for bar, m, mean in zip(bars, methods, means):
        if m == "rostam_ea" and not np.isnan(mean):
            ax.text(bar.get_x() + bar.get_width() / 2, mean * 1.15,
                    f"{mean:.0f}", ha="center", va="bottom", fontsize=6.5, fontweight="bold")

    # Panel (b): linear scale — exclude RoSTAM-EA to show detail among others
    ax = axes[1]
    methods2 = [m for m in methods if m != "rostam_ea"]
    labels2  = [METHOD_LABELS.get(m, m) for m in methods2]
    colors2  = [_method_color(m, len(methods), methods.index(m)) for m in methods2]
    means2   = [df_comm[df_comm["strategy"] == m][col].mean() for m in methods2]
    errs2    = [df_comm[df_comm["strategy"] == m][col].std(ddof=1) for m in methods2]
    ax.bar(labels2, means2, color=colors2, yerr=errs2, capsize=3, error_kw={"linewidth": 0.8})
    ax.set_ylabel("Bytes / Round")
    ax.set_xticklabels(labels2, rotation=45, ha="right", fontsize=7)
    ax.set_title("(b) Excluding RoSTAM-EA — linear scale", fontsize=8)
    for i, (mean, err) in enumerate(zip(means2, errs2)):
        if not np.isnan(mean):
            ax.text(i, mean + (err if not np.isnan(err) else 0) + max(means2) * 0.02,
                    f"{mean:.0f}", ha="center", va="bottom", fontsize=6.5)

    fig.suptitle("Communication Footprint per Allocation Round", fontsize=9)
    fig.tight_layout()
    out_path = out_dir / "communication_footprint.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_communication_scalability_panel(df_comm: Optional[pd.DataFrame],
                                         df_summary: Optional[pd.DataFrame],
                                         df_runtime: Optional[pd.DataFrame],
                                         out_dir: Path, dpi: int) -> None:
    """Fig. 6 — communication efficiency + decision latency (3 panels, only non-empty)."""
    fig, axes = plt.subplots(1, 3, figsize=(DOUBLE_COL_W, 2.8))

    # Panel (a): communication footprint — use first available numeric column
    if df_comm is not None and not df_comm.empty:
        methods = _ordered_methods(df_comm)
        footprint_col = next((c for c in ["footprint_bytes", "message_count",
                                           "bytes_transmitted", "communication_bytes"]
                               if c in df_comm.columns), None)
        if footprint_col:
            _bar_panel(axes[0], df_comm, methods, footprint_col,
                       "Footprint Bytes", False)
            axes[0].set_title("(a) Communication footprint", fontsize=8)
        else:
            axes[0].text(0.5, 0.5, "No comm data", ha="center", va="center",
                         transform=axes[0].transAxes)
            axes[0].set_title("(a) Communication footprint", fontsize=8)
    else:
        axes[0].text(0.5, 0.5, "No comm data", ha="center", va="center",
                     transform=axes[0].transAxes)
        axes[0].set_title("(a) Communication footprint", fontsize=8)

    # Panel (b): task completion rate at 3R/15T
    if df_summary is not None and not df_summary.empty:
        sub = df_summary.copy()
        if "robot_count" in sub.columns and "target_count" in sub.columns:
            sub = sub[(sub["robot_count"] == 3) & (sub["target_count"] == 15)]
        if not sub.empty and "task_completion_rate" in sub.columns:
            methods = _ordered_methods(sub)
            _bar_panel(axes[1], sub, methods, "task_completion_rate", "Completion Rate", True)
        else:
            axes[1].text(0.5, 0.5, "No summary data", ha="center", va="center",
                         transform=axes[1].transAxes)
        axes[1].set_title("(b) Completion Rate — 3R/15T", fontsize=8)
    else:
        axes[1].text(0.5, 0.5, "No summary data", ha="center", va="center",
                     transform=axes[1].transAxes)
        axes[1].set_title("(b) Completion Rate — 3R/15T", fontsize=8)

    # Panel (c): decision latency (runtime)
    if df_runtime is not None and not df_runtime.empty:
        methods = _ordered_methods(df_runtime)
        runtime_col = "runtime_ms" if "runtime_ms" in df_runtime.columns else "latency_ms"
        means = [df_runtime[df_runtime["strategy"] == m][runtime_col].mean() for m in methods]
        labels = [METHOD_LABELS.get(m, m) for m in methods]
        colors = [_method_color(m, len(methods), i) for i, m in enumerate(methods)]
        axes[2].bar(labels, means, color=colors)
        axes[2].set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        axes[2].set_ylabel("Runtime (ms)")
        axes[2].set_title("(c) Decision latency", fontsize=8)
    else:
        axes[2].text(0.5, 0.5, "No runtime data", ha="center", va="center",
                     transform=axes[2].transAxes)
        axes[2].set_title("(c) Decision latency", fontsize=8)

    fig.suptitle("Fig. 6 — Communication Efficiency & Decision Latency", fontsize=9, fontweight="bold")
    fig.tight_layout()
    out_path = out_dir / "communication_scalability_panel.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_allocation_instability(df_summary: Optional[pd.DataFrame],
                                df_alloc: Optional[pd.DataFrame],
                                out_dir: Path, dpi: int) -> None:
    # Build list of available panels
    panels = []
    if df_summary is not None and not df_summary.empty and "allocation_instability" in df_summary.columns:
        panels.append(("summary", "allocation_instability", "Alloc. Instability (↓ better)"))
    if df_summary is not None and not df_summary.empty and "replanning_frequency" in df_summary.columns:
        panels.append(("summary", "replanning_frequency", "Replanning Frequency (↓ better)"))
    if df_alloc is not None and not df_alloc.empty:
        rf_cnt = df_alloc[df_alloc["event_type"] == "robot_failure"].groupby("strategy").size().reset_index()
        rf_cnt.columns = ["strategy", "failure_events"]
        if not rf_cnt.empty:
            panels.append(("rf_cnt", rf_cnt, "Robot Failure Events"))

    n = max(len(panels), 1)
    fig, axes = plt.subplots(1, n, figsize=(min(DOUBLE_COL_W, 3.5 * n), 2.8), squeeze=False)
    axes = axes.flatten()

    if not panels:
        axes[0].text(0.5, 0.5, "No data", ha="center", va="center", transform=axes[0].transAxes)
    else:
        methods = _ordered_methods(df_summary) if df_summary is not None else []
        for ax, panel in zip(axes, panels):
            src, metric, ylabel = panel
            if src == "summary":
                _bar_panel(ax, df_summary, methods, metric, ylabel, False)
            else:
                _bar_panel(ax, metric, methods, "failure_events", ylabel, False)

    fig.suptitle("Allocation Stability Analysis", fontsize=9)
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
        _rt_col = "runtime_ms" if "runtime_ms" in df_runtime.columns else "latency_ms"
        data = [df_runtime[df_runtime["strategy"] == m][_rt_col].dropna().values
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
    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE_COL_W, 3.0))

    event_col = "event" if df_task is not None and "event" in df_task.columns else "status"
    time_col = next((c for c in ["timestamp_s", "completed_rel", "time_s"]
                     if df_task is not None and c in df_task.columns), None)

    for ax, scenario in zip(axes, ["robot_failure", "mixed_stress"]):
        ax.set_title(f"({chr(97 + list(['robot_failure','mixed_stress']).index(scenario))}) "
                     f"{scenario.replace('_', ' ').title()}", fontsize=8)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Avg Cumul. Completed Tasks")

        if df_task is None or df_task.empty or time_col is None:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            continue

        scen_df = df_task[df_task["scenario"] == scenario] \
            if "scenario" in df_task.columns else df_task
        if scen_df.empty:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            continue

        methods = _ordered_methods(scen_df)
        colors = plt.get_cmap("tab10")(np.linspace(0, 0.9, len(methods)))
        for method, c in zip(methods, colors):
            mdf = scen_df[(scen_df["strategy"] == method) & (scen_df[event_col] == "completed")]
            if mdf.empty:
                continue
            n_exp = mdf["experiment_id"].nunique() if "experiment_id" in mdf.columns else 1
            t_sorted = np.sort(mdf[time_col].dropna().values)
            cumulative = np.arange(1, len(t_sorted) + 1) / max(n_exp, 1)
            lw = 1.8 if method == PROPOSED else 1.0
            ls = "-" if method == PROPOSED else "-"
            ax.plot(t_sorted, cumulative, label=METHOD_LABELS.get(method, method),
                    color=c, linewidth=lw, linestyle=ls)

    axes[1].legend(fontsize=6.5, ncol=2, loc="lower right")
    fig.suptitle("Task Completion Timeline — per scenario (avg across seeds)", fontsize=9)
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
            ("task_completion_rate", "Completion Rate", True),
            ("average_task_delay", "Avg Task Delay (s)", False),
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

    fig.suptitle("Scalability Check (3R/15T)", fontsize=9)
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
