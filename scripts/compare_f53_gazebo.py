#!/usr/bin/env python3
"""Historical matched-run comparison for the rejected F53 campaign.

The historical summary files may contain the pre-v4.7 variance transform under
``workload_balance``.  This script therefore recomputes Jain indices directly
from each run's ``robot_workload.csv`` before making any comparison.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from recompute_stability_metrics import compute_for_exp


KEYS = ["scenario", "strategy", "seed", "robot_count", "target_count"]
METRICS = {
    "task_completion_rate": True,
    "makespan_s": False,
    "average_task_delay": False,
    "deadline_violation_rate": False,
    "total_travel_distance": False,
    "workload_balance": True,
    "workload_balance_active": True,
    "travel_distance_balance": True,
    "failure_recovery_time": False,
    "exec_preemptions": False,
    "redispatch_per_task": False,
    "mean_decision_latency_ms": False,
    "communication_messages": False,
}


def jain(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").dropna().clip(lower=0).to_numpy(float)
    denom = len(x) * float(np.square(x).sum())
    return float(x.sum() ** 2 / denom) if len(x) and denom > 0 else 0.0


def load_runs(raw_dir: Path, label: str) -> pd.DataFrame:
    rows: list[dict] = []
    for exp_dir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        summary_path = exp_dir / "summary.csv"
        workload_path = exp_dir / "robot_workload.csv"
        if not summary_path.exists() or not workload_path.exists():
            continue
        summary = pd.read_csv(summary_path)
        workload = pd.read_csv(workload_path)
        if summary.empty or "completed_tasks" not in workload:
            continue
        row = summary.iloc[0].to_dict()
        row["workload_balance"] = jain(workload["completed_tasks"])
        if "approx_distance_m" in workload:
            row["travel_distance_balance"] = jain(workload["approx_distance_m"])
        stability = compute_for_exp(exp_dir)
        if stability:
            row.update(stability)
        row["run_dir"] = str(exp_dir)
        rows.append(row)
    if not rows:
        raise SystemExit(f"No complete runs found in {raw_dir}")
    frame = pd.DataFrame(rows)
    missing = [key for key in KEYS if key not in frame]
    if missing:
        raise SystemExit(f"{label} runs lack matching columns: {', '.join(missing)}")
    return frame


def wilcoxon_p(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    if len(x) < 2 or np.allclose(x, 0.0):
        return np.nan
    try:
        return float(stats.wilcoxon(x, alternative="two-sided").pvalue)
    except ValueError:
        return np.nan


def bootstrap_ci(values: pd.Series, seed: int = 53) -> tuple[float, float]:
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    if len(x) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(10_000, len(x)), replace=True).mean(axis=1)
    return tuple(float(v) for v in np.quantile(means, [0.025, 0.975]))


def compare(reference: pd.DataFrame, candidate: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    keep = KEYS + [m for m in METRICS if m in reference]
    ref = reference[keep].rename(columns={m: f"reference_{m}" for m in METRICS if m in reference})
    keep = KEYS + [m for m in METRICS if m in candidate]
    cand = candidate[keep].rename(columns={m: f"candidate_{m}" for m in METRICS if m in candidate})
    paired = ref.merge(cand, on=KEYS, how="inner", validate="one_to_one")
    if paired.empty:
        raise SystemExit("No matched scenario/strategy/seed/scale runs were found")

    detail: list[pd.DataFrame] = []
    for metric, higher_is_better in METRICS.items():
        rc, cc = f"reference_{metric}", f"candidate_{metric}"
        if rc not in paired or cc not in paired:
            continue
        block = paired[KEYS].copy()
        block["metric"] = metric
        block["reference"] = pd.to_numeric(paired[rc], errors="coerce")
        block["candidate"] = pd.to_numeric(paired[cc], errors="coerce")
        block["raw_delta"] = block["candidate"] - block["reference"]
        block["improvement"] = block["raw_delta"] if higher_is_better else -block["raw_delta"]
        detail.append(block)
    details = pd.concat(detail, ignore_index=True)

    rows: list[dict] = []
    groups = ["scenario", "robot_count", "target_count", "metric"]
    for (scenario, robots, tasks, metric), group in details.groupby(groups, sort=True):
        lo, hi = bootstrap_ci(group["improvement"])
        n = len(group)
        mean_imp = float(group["improvement"].mean())
        rows.append({
            "scenario": scenario,
            "robot_count": robots,
            "target_count": tasks,
            "metric": metric,
            "n_matched": n,
            "reference_mean": group["reference"].mean(),
            "candidate_mean": group["candidate"].mean(),
            "raw_delta_mean": group["raw_delta"].mean(),
            "improvement_mean": mean_imp,
            "improvement_ci95_low": lo,
            "improvement_ci95_high": hi,
            "wilcoxon_p": wilcoxon_p(group["improvement"]),
            "direction": "improved" if mean_imp > 0 else "regressed" if mean_imp < 0 else "tied",
            "evidence": "pilot_only" if n < 3 else "multi_seed",
        })
    return details, pd.DataFrame(rows)


def acceptance_gates(summary: pd.DataFrame) -> pd.DataFrame:
    """Conservative promotion gate; it does not turn a pilot into evidence."""
    rows = []
    for keys, group in summary.groupby(["scenario", "robot_count", "target_count"]):
        scenario, robots, tasks = keys
        values = group.set_index("metric")["improvement_mean"].to_dict()
        n_matched = int(group["n_matched"].min())
        nonregression = (
            values.get("task_completion_rate", -np.inf) >= -0.01
            and values.get("deadline_violation_rate", -np.inf) >= -0.01
        )
        supporting = [
            values.get("workload_balance_active",
                       values.get("workload_balance", 0.0)) > 0.0,
            values.get("total_travel_distance", 0.0) > 0.0,
            values.get("redispatch_per_task", 0.0) > 0.0,
            values.get("average_task_delay", 0.0) > 0.0,
        ]
        support_count = sum(supporting)
        if n_matched < 3:
            status = "INSUFFICIENT"
        elif nonregression and support_count >= 2:
            status = "PASS"
        else:
            status = "FAIL"
        rows.append({
            "scenario": scenario,
            "robot_count": robots,
            "target_count": tasks,
            "n_matched": n_matched,
            "cr_dvr_nonregression": nonregression,
            "supporting_improvements": support_count,
            "status": status,
        })
    return pd.DataFrame(rows)


def fmt(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:.4f}"


def write_report(summary: pd.DataFrame, gates: pd.DataFrame, out_path: Path,
                 reference: Path, candidate: Path) -> None:
    lines = [
        "# F53 Gazebo matched-run comparison",
        "",
        f"Reference: `{reference}`  ",
        f"Candidate: `{candidate}`",
        "",
        "Positive `improvement` always means better; workload and distance balance are true Jain indices recomputed from `robot_workload.csv`.",
        "",
        "## Acceptance gate",
        "",
        "The gate requires at least three matched seeds, CR/DVR mean non-regression within 0.01, and improvement in at least two of Jain, distance, physical redispatch, and delay.",
        "",
        "| Scenario | Scale | n | CR/DVR safe | Supporting gains | Status |",
        "|---|---:|---:|---|---:|---|",
    ]
    for row in gates.itertuples(index=False):
        lines.append(
            f"| {row.scenario} | {row.robot_count}r/{row.target_count}t | "
            f"{row.n_matched} | {row.cr_dvr_nonregression} | "
            f"{row.supporting_improvements}/4 | **{row.status}** |"
        )
    lines += [
        "",
        "## Metric detail",
        "",
        "| Scenario | Scale | Metric | n | Reference | F53 | Improvement | 95% bootstrap CI | Wilcoxon p | Evidence |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.itertuples(index=False):
        ci = f"[{fmt(row.improvement_ci95_low)}, {fmt(row.improvement_ci95_high)}]"
        lines.append(
            f"| {row.scenario} | {row.robot_count}r/{row.target_count}t | "
            f"{row.metric} | {row.n_matched} | "
            f"{fmt(row.reference_mean)} | {fmt(row.candidate_mean)} | "
            f"{fmt(row.improvement_mean)} | {ci} | {fmt(row.wilcoxon_p)} | {row.evidence} |"
        )
    lines += [
        "",
        "> `pilot_only` rows must not replace paper claims. Promote results only after the planned multi-seed campaign is complete.",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", type=Path, default=Path("results/raw/gazebo"))
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    reference = load_runs(args.reference_dir, "reference")
    candidate = load_runs(args.candidate_dir, "candidate")
    details, summary = compare(reference, candidate)
    gates = acceptance_gates(summary)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    details.to_csv(args.output_dir / "matched_runs.csv", index=False)
    summary.to_csv(args.output_dir / "metric_comparison.csv", index=False)
    gates.to_csv(args.output_dir / "acceptance_gates.csv", index=False)
    write_report(summary, gates, args.output_dir / "REPORT.md",
                 args.reference_dir, args.candidate_dir)
    print(f"Matched runs: {len(details[KEYS].drop_duplicates())}")
    print(f"Report: {args.output_dir / 'REPORT.md'}")


if __name__ == "__main__":
    main()
