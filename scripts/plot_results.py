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
    "ahe_mrta_v3",
]

METHOD_LABELS = {
    "big_mrta":                     "BiG-MRTA",
    "rostam_ea":                    "RoSTAM-EA",
    "consensus_dbta":               "Cons-DBTA",
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
                fontsize=6.8, color=color)


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
                fontsize=6.8, color=color)


def plot_system_overview(out_dir: Path, dpi: int) -> None:
    # Wide, short layout intended to span both columns (figure*).
    fig, ax = plt.subplots(figsize=(DOUBLE_COL_W, 2.9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 7.2)
    ax.axis("off")

    BLUE, GREEN, ORANGE, PURPLE, YELLOW, GREY = (
        "#cfe2f3", "#d9ead3", "#ffe0b2", "#e1bee7", "#fff2cc", "#efefef")

    # Top row: control plane (left to right pipeline)
    _orect(ax, 0.3, 4.2, 3.2, 1.5,
           "Task Manager\n(goal pool, batch\nrelease, deadlines)", BLUE, 7.2)
    _orect(ax, 4.4, 4.2, 3.6, 1.5,
           "Ecosystem Manager\ncontext $c(t)$ $\\rightarrow$ dominance\n$D(t)$ $\\rightarrow$ paradigm $p^*$",
           GREEN, 7.2)
    _orect(ax, 8.9, 4.2, 3.2, 1.5,
           "AHE Allocator\nrun $p^*$, build\nper-robot queues", ORANGE, 7.2)

    # control-plane arrows (straight, same row)
    _harrow(ax, 3.5, 4.4, 4.95, lbl="tasks")
    _harrow(ax, 8.0, 8.9, 4.95, lbl="$D(t)$")

    # Distribution bus: allocator drops down to a horizontal bus,
    # then one straight arrow per robot (no crossing fan).
    bus_y = 3.1
    _varrow(ax, 10.5, 4.2, bus_y + 0.05, color="#c0392b",
            lbl="queues", side="right")
    ax.plot([1.4, 10.5], [bus_y, bus_y], color="#c0392b", lw=1.3)

    robots_x = [1.4, 4.6, 7.8]
    for rx in robots_x:
        _orect(ax, rx - 1.1, 1.5, 2.2, 1.2,
               "Robot Iface\n(Nav2 client)", PURPLE, 6.9)
        ax.annotate("", xy=(rx, 2.7), xytext=(rx, bus_y),
                    arrowprops=dict(arrowstyle="-|>", color="#c0392b", lw=1.2,
                                    shrinkA=0, shrinkB=0))

    # Execution layer
    _orect(ax, 0.3, 0.1, 11.8, 0.9,
           "Nav2 + Gazebo Harmonic   (TurtleBot3 Waffle Pi, headless)",
           YELLOW, 7.2)
    for rx in robots_x:
        _varrow(ax, rx, 1.5, 1.0, color="#555", two_way=True)

    # Feedback path (execution feedback -> context): clean top route that
    # touches no box. right side up, across the very top, down into EM.
    GR = "#2e7d32"
    ax.annotate("", xy=(15.3, 2.1), xytext=(8.9, 2.1),
                arrowprops=dict(arrowstyle="-", color=GR, lw=1.2))
    ax.plot([15.3, 15.3], [2.1, 6.7], color=GR, lw=1.2)
    ax.annotate("", xy=(6.2, 6.7), xytext=(15.3, 6.7),
                arrowprops=dict(arrowstyle="-", color=GR, lw=1.2))
    ax.annotate("", xy=(6.2, 5.7), xytext=(6.2, 6.7),
                arrowprops=dict(arrowstyle="-|>", color=GR, lw=1.2))
    ax.text(15.45, 4.2, "execution\nfeedback", fontsize=6.8,
            color=GR, ha="left", va="center")

    # Logger (separate, bottom-right)
    _orect(ax, 12.9, 0.1, 3.0, 0.9, "Evaluation\nLogger (CSV)", GREY, 7.0)
    ax.annotate("", xy=(12.9, 0.55), xytext=(12.1, 0.55),
                arrowprops=dict(arrowstyle="-|>", color="#555", lw=1.0))

    fig.tight_layout(pad=0.2)
    out_path = out_dir / "system_overview.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_adaptive_ecosystem_mechanism(out_dir: Path, dpi: int) -> None:
    # Wide, short left-to-right pipeline intended to span both columns
    # (figure*). Notation matches Eq. (2) in the paper.
    fig, ax = plt.subplots(figsize=(DOUBLE_COL_W, 2.7))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 6.4)
    ax.axis("off")

    BLUE, PINK, YELLOW, GREEN, RED = (
        "#cfe2f3", "#fde0ec", "#fff2cc", "#d9ead3", "#f4cccc")

    row_y, row_h = 2.7, 1.7
    cy = row_y + row_h / 2  # vertical center of the pipeline

    # 1. Context vector
    _orect(ax, 0.2, row_y, 2.9, row_h,
           "Context $c(t)\\in[0,1]^7$\nspatial, crit., temporal,\nresource, energy, stab., recov.",
           BLUE, 6.8)
    # 2. Dominance update (Eq. 2)
    _orect(ax, 4.0, row_y, 4.3, row_h,
           "Dominance update\n"
           r"$D_{k{+}1}{=}\mathrm{clip}_{[0,1]}[(1{-}\alpha)D_k$" + "\n"
           r"$+\,\alpha A c - S D_k c^{\top}]$",
           YELLOW, 7.0)
    # 3. Argmax selector
    _orect(ax, 9.2, row_y, 2.7, row_h,
           "Select paradigm\n$p^*=\\arg\\max_i D_i$", GREEN, 7.2)
    # 4. Allocator
    _orect(ax, 12.8, row_y, 3.0, row_h,
           "AHE Allocator\nrun $p^*$, publish\nper-robot queues", RED, 7.0, ec="#c0392b")

    # pipeline arrows (straight, single row)
    _harrow(ax, 3.1, 4.0, cy, lbl="$c(t)$")
    _harrow(ax, 8.3, 9.2, cy, lbl="$D_{k+1}$")
    _harrow(ax, 11.9, 12.8, cy, lbl="$p^*$", color="#c0392b")

    # Fixed matrices feed the dominance box from below (orthogonal, no cross)
    _orect(ax, 4.0, 0.2, 4.3, 1.3,
           "Fixed matrices: cooperation $A_{7\\times7}$, suppression $S_{7\\times7}$",
           PINK, 6.8)
    _varrow(ax, 6.15, 1.5, row_y, lbl="$A,S$", side="right")

    # Event trigger feeds the context box from above (orthogonal, no cross)
    _orect(ax, 0.2, 5.0, 2.9, 1.2,
           "Event trigger\n(failure / new task / deadline)", "#fce5cd", 6.8,
           ec="#e69138")
    _varrow(ax, 1.65, 5.0, row_y + row_h, color="#e69138", side="left")

    # 7 paradigms listed under the selector (label only, no extra arrows)
    ax.text(10.55, 1.4,
            "greedy · priority-LSA · EDF ·\nload-LSA · battery · sticky · rescue",
            ha="center", va="center", fontsize=6.3, color="#38761d", style="italic")
    _varrow(ax, 10.55, row_y, 1.9, color="#38761d", side="right", lbl="")

    fig.tight_layout(pad=0.2)
    out_path = out_dir / "adaptive_ecosystem_mechanism.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK]  {out_path}")


def plot_gazebo_arena(out_dir: Path, dpi: int) -> None:
    """Top-down schematic of the 20x20 m Gazebo inspection arena.

    Geometry mirrors src/m_ahe_mrta_gazebo/worlds/ahe_inspection_arena.sdf:
    perimeter walls, pillar rows near the side walls, two horizontal divider
    walls (with a central passage) partitioning the space into three lanes,
    four cylinders, three robot spawn poses and the 20 candidate inspection
    waypoints (15 sampled per run).
    """
    out_path = out_dir / "gazebo_arena.png"

    WALL = "#555555"
    OBST = "#888888"
    CYL = "#a6761d"

    # Candidate inspection waypoints (must match task_manager_node._INSPECTION_GRID)
    waypoints = [
        (-6.0, 7.0), (-2.0, 7.0), (2.0, 7.0), (6.0, 7.0),
        (-6.0, 4.0), (-2.0, 4.0), (2.0, 4.0), (6.0, 4.0),
        (-6.0, 1.0), (6.0, 1.0),
        (-4.0, -1.0), (4.0, -1.0),
        (-6.0, -5.0), (-4.0, -5.0), (4.0, -5.0), (6.0, -5.0),
        (-2.0, -7.5), (0.0, -8.0), (2.0, -7.5), (6.0, -7.5),
    ]
    # Pillar centres (0.3 x 2.0 boxes)
    pillars = [(x, y) for x in (-7.5, -5.0, 5.0, 7.5)
               for y in (-7.5, -4.5, 4.5, 7.5)]
    # Horizontal divider walls (7.0 x 0.2 boxes), centred -> central gap
    dividers = [(-5.0, 3.0), (5.0, 3.0), (-5.0, -3.0), (5.0, -3.0)]
    # Cylinders
    cyls = [(-2.5, 5.5), (2.5, 5.5), (-2.5, -5.5), (2.5, -5.5)]
    # Robot spawn poses: (x, y, colour, label)
    robots = [(0.0, 0.0, "#1f5fd0", "R1"),
              (0.0, 2.0, "#1a9641", "R2"),
              (0.0, -2.0, "#d7191c", "R3")]

    fig, ax = plt.subplots(figsize=(3.4, 3.5))

    # Perimeter walls (inner face ~ +/-9.9)
    ax.add_patch(mpatches.Rectangle((-10, -10), 20, 20, fill=False,
                                    edgecolor=WALL, lw=2.2))

    for (cx, cy) in pillars:
        ax.add_patch(mpatches.Rectangle((cx - 0.15, cy - 1.0), 0.3, 2.0,
                                        facecolor=OBST, edgecolor="none"))
    for (cx, cy) in dividers:
        ax.add_patch(mpatches.Rectangle((cx - 3.5, cy - 0.1), 7.0, 0.2,
                                        facecolor=OBST, edgecolor="none"))
    for (cx, cy) in cyls:
        ax.add_patch(mpatches.Circle((cx, cy), 0.2, facecolor=CYL,
                                     edgecolor="none"))

    wp = np.array(waypoints)
    ax.scatter(wp[:, 0], wp[:, 1], marker="*", s=55, c="#fdae61",
               edgecolors="#b8860b", linewidths=0.4, zorder=3)

    for (rx, ry, rc, rl) in robots:
        ax.scatter([rx], [ry], marker="o", s=70, c=rc, edgecolors="black",
                   linewidths=0.7, zorder=4)
        ax.annotate(rl, (rx, ry), textcoords="offset points", xytext=(6, 4),
                    fontsize=7, fontweight="bold", color=rc)

    # Lane annotations
    for ly, lt in [(6.0, "upper lane"), (0.0, "central passage"),
                   (-6.0, "lower lane")]:
        ax.text(-9.3, ly, lt, fontsize=6.0, color="#777777",
                rotation=90, va="center", ha="center")

    legend = [
        mlines.Line2D([], [], marker="*", color="none", markerfacecolor="#fdae61",
                      markeredgecolor="#b8860b", markersize=9,
                      label="inspection waypoint"),
        mlines.Line2D([], [], marker="o", color="none", markerfacecolor="#888888",
                      markersize=9, label="robot start"),
        mpatches.Patch(facecolor=OBST, label="wall / pillar"),
        mpatches.Patch(facecolor=CYL, label="cylinder"),
    ]
    ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.08),
              ncol=2, frameon=False, fontsize=6.5, handletextpad=0.3,
              columnspacing=0.9)

    ax.set_xlim(-10.6, 10.6)
    ax.set_ylim(-10.6, 10.6)
    ax.set_aspect("equal")
    ax.set_xticks([-10, -5, 0, 5, 10])
    ax.set_yticks([-10, -5, 0, 5, 10])
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.spines[:].set_visible(True)
    ax.tick_params(labelsize=7)

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


def plot_fitness_comparison(processed_dir: Path, out_dir: Path, dpi: int) -> None:
    """Nav2-bağımsız fitness'ı 4 yöntem için 3 senaryoda gruplu bar olarak çiz.

    Kaynak: scripts/simulate_and_tune.py'nin yazdığı sim_fitness.csv (idealize
    stokastik-stres simülasyonu, 300 seed). Gazebo verisinden bağımsızdır;
    AHE'nin algoritmik üstünlüğünü navigasyon gürültüsünden yalıtılmış olarak
    gösterir. Eksik CSV → uyarı ve atla.
    """
    fpath = processed_dir / "sim_fitness.csv"
    if not fpath.exists():
        print(f"[skip] {fpath.name} yok — fitness karşılaştırma çizilmedi "
              "(önce: python3 scripts/simulate_and_tune.py --seeds 100 --scenario all)")
        return
    df = pd.read_csv(fpath)
    scen_order = ["robot_failure", "mixed_stress", "deadline_pressure"]
    scen_labels = {"robot_failure": "Robot Failure",
                   "mixed_stress": "Mixed Stress",
                   "deadline_pressure": "Deadline Pressure"}
    methods = ["ahe_mrta_v3", "big_mrta", "rostam_ea", "consensus_dbta"]
    mlabels = {"ahe_mrta_v3": "AHE-MRTA",
               "big_mrta": "BiG-MRTA",
               "rostam_ea": "RoSTAM-EA",
               "consensus_dbta": "Cons-DBTA"}
    palette = {"ahe_mrta_v3": "#d62728",
               "big_mrta": "#1f77b4",
               "rostam_ea": "#2ca02c",
               "consensus_dbta": "#9467bd"}

    fig, ax = plt.subplots(figsize=(DOUBLE_COL_W, 3.4))
    n_g = len(scen_order)
    n_m = len(methods)
    bar_w = 0.8 / n_m
    x_pos = np.arange(n_g)

    for i, m in enumerate(methods):
        vals, errs = [], []
        for s in scen_order:
            sel = df[(df["scenario"] == s) & (df["strategy"] == m)]
            vals.append(float(sel["fitness_mean"].iloc[0]) if len(sel) else 0.0)
            errs.append(float(sel["fitness_std"].iloc[0]) if len(sel) else 0.0)
        offset = (i - (n_m - 1) / 2) * bar_w
        bars = ax.bar(x_pos + offset, vals, bar_w, yerr=errs,
                      label=mlabels[m], color=palette[m],
                      edgecolor="black", linewidth=0.4,
                      error_kw={"linewidth": 0.6, "capsize": 2})
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.015,
                    f"{v:.3f}", ha="center", va="bottom",
                    fontsize=6.5, rotation=0)

    ax.set_xticks(x_pos)
    ax.set_xticklabels([scen_labels[s] for s in scen_order])
    ax.set_ylabel("Allocation Fitness (Nav2-independent) ↑")
    ax.set_ylim(0, 1.05)
    ax.set_title("Cross-Method Fitness — Idealised Stochastic-Stress SIM "
                 "(higher is better)", fontsize=9)
    ax.grid(axis="y", linestyle=":", linewidth=0.4, alpha=0.6)
    ax.legend(loc="lower right", ncol=4, fontsize=7, frameon=False)
    fig.tight_layout()
    fpath_out = out_dir / "fitness_comparison.png"
    fig.savefig(fpath_out, dpi=dpi)
    plt.close(fig)
    print(f"[OK]  {fpath_out}")


def plot_scalability_panel(processed_dir: Path, out_dir: Path, dpi: int) -> None:
    """Fig. 6 — Çoklu-ölçek panel: robot sayısına karşı (a) fitness (b) CR
    (c) recovery_time (d) latency. Yöntem başına bir çizgi (3 senaryo ortalaması).

    Kaynak: simulate_and_tune.py --robot-counts 3,5,10 → sim_scalability.csv
    (Nav2-bağımsız sim). Eksik CSV → uyarı ve atla.
    """
    fpath = processed_dir / "sim_scalability.csv"
    if not fpath.exists():
        print(f"[skip] {fpath.name} yok — ölçek paneli çizilmedi "
              "(önce: python3 scripts/simulate_and_tune.py --seeds 100 "
              "--scenario all --robot-counts 3,5,10)")
        return
    df = pd.read_csv(fpath)
    methods = ["ahe_mrta_v3", "big_mrta", "rostam_ea", "consensus_dbta"]
    mlabels = {"ahe_mrta_v3": "AHE-MRTA", "big_mrta": "BiG-MRTA",
               "rostam_ea": "RoSTAM-EA", "consensus_dbta": "Cons-DBTA"}
    palette = {"ahe_mrta_v3": "#d62728", "big_mrta": "#1f77b4",
               "rostam_ea": "#2ca02c", "consensus_dbta": "#9467bd"}
    panels = [("fitness", "Allocation Fitness ↑"), ("cr", "Completion Rate ↑"),
              ("recovery", "Recovery Time (s) ↓"), ("latency", "Decision Latency (ms) ↓")]
    robots = sorted(df["robot_count"].unique())

    fig, axes = plt.subplots(2, 2, figsize=(DOUBLE_COL_W, 5.0))
    axes = axes.flatten()
    for ax, (col, ylabel) in zip(axes, panels):
        for m in methods:
            ys = []
            for r in robots:
                sel = df[(df["robot_count"] == r) & (df["strategy"] == m)]
                # recovery == -1 → veri yok; ortalamada dışla
                vals = sel[col][sel[col] > -1] if col == "recovery" else sel[col]
                ys.append(float(vals.mean()) if len(vals) else np.nan)
            ax.plot(robots, ys, marker="o", markersize=4, linewidth=1.4,
                    label=mlabels[m], color=palette[m],
                    markeredgecolor="black", markeredgewidth=0.3)
        ax.set_xlabel("Robot count (N)")
        ax.set_ylabel(ylabel)
        ax.set_xticks(robots)
        ax.grid(True, linestyle=":", linewidth=0.4, alpha=0.6)
    axes[0].legend(loc="best", fontsize=7, frameon=False, ncol=2)
    fig.suptitle("Fig. 6 — Scalability vs robot count (Nav2-independent SIM, "
                 "mean over 3 scenarios)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fpath_out = out_dir / "scalability_panel.png"
    fig.savefig(fpath_out, dpi=dpi)
    plt.close(fig)
    print(f"[OK]  {fpath_out}")


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
    plot_gazebo_arena(out_dir, dpi)

    # Nav2-independent fitness (from SIM CSV, if present)
    plot_fitness_comparison(processed_dir, out_dir, dpi)

    # Scalability panel (from sim_scalability.csv, if present) — Fig. 6
    plot_scalability_panel(processed_dir, out_dir, dpi)

    # Data-driven mandatory figures (robust to missing data)
    plot_baseline_comparison(df_summary, out_dir, dpi)
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
