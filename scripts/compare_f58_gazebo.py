#!/usr/bin/env python3
"""Matched fresh-F45 versus F58 Gazebo comparison and promotion gate."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re

from compare_f53_gazebo import (
    KEYS, compare, fmt, load_runs,
)


def completion_resurrections(raw_dir: Path) -> dict:
    """Count assignments emitted after exact completion by scenario/scale."""
    counts = {}
    for path in raw_dir.rglob("task_events.csv"):
        scale = next((p for p in path.parts
                      if re.fullmatch(r"r\d+t\d+", p)), None)
        if scale is None:
            continue
        match = re.fullmatch(r"r(\d+)t(\d+)", scale)
        completed = set()
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                tid = row.get("task_id", "")
                event = row.get("event", row.get("event_type", ""))
                scenario = row.get("scenario", "")
                key = (scenario, int(match.group(1)), int(match.group(2)))
                if event == "completed":
                    completed.add(tid)
                elif event == "assigned" and tid in completed:
                    counts[key] = counts.get(key, 0) + 1
    return counts


def acceptance_gates(summary, reference_ghosts=None, candidate_ghosts=None):
    """F58 promotion gate aligned with its fairness-first design contract."""
    rows = []
    for keys, group in summary.groupby(
            ["scenario", "robot_count", "target_count"]):
        scenario, robots, tasks = keys
        metrics = group.set_index("metric")
        improvement = metrics["improvement_mean"].to_dict()
        candidate = metrics["candidate_mean"].to_dict()
        n_matched = int(group["n_matched"].min())
        cr_dvr_safe = (
            improvement.get("task_completion_rate", float("-inf")) >= -0.01
            and improvement.get("deadline_violation_rate", float("-inf")) >= -0.01
        )
        # F58 is explicitly a fairness-preserving repair.  A gain in distance
        # or delay must therefore not buy a lower active-robot Jain index.
        fairness_safe = improvement.get(
            "workload_balance_active", float("-inf")) >= 0.0
        latency_safe = candidate.get(
            "mean_decision_latency_ms", float("inf")) <= 50.0
        physical_gains = [
            improvement.get("total_travel_distance", 0.0) > 0.0,
            improvement.get("redispatch_per_task", 0.0) > 0.0,
            improvement.get("average_task_delay", 0.0) > 0.0,
            improvement.get("makespan_s", 0.0) > 0.0,
        ]
        gain_count = sum(physical_gains)
        event_integrity = (
            (reference_ghosts or {}).get(keys, 0) == 0
            and (candidate_ghosts or {}).get(keys, 0) == 0)
        if not event_integrity:
            status = "FAIL"
        elif n_matched < 3:
            status = "INSUFFICIENT"
        elif cr_dvr_safe and fairness_safe and latency_safe and gain_count >= 2:
            status = "PASS"
        else:
            status = "FAIL"
        rows.append({
            "scenario": scenario,
            "robot_count": robots,
            "target_count": tasks,
            "n_matched": n_matched,
            "cr_dvr_nonregression": cr_dvr_safe,
            "fairness_nonregression": fairness_safe,
            "latency_within_50ms": latency_safe,
            "supporting_improvements": gain_count,
            "event_integrity": event_integrity,
            "status": status,
        })
    return type(summary)(rows)


def write_report(summary, gates, out_path: Path,
                 reference: Path, candidate: Path) -> None:
    lines = [
        "# F58 Gazebo+Nav2 matched-run comparison",
        "",
        f"Fresh F45 reference: `{reference}`  ",
        f"F58 candidate: `{candidate}`",
        "",
        "Positive improvement means better. Workload and distance balance are true Jain indices recomputed from each run's robot_workload.csv.",
        "",
        "## Acceptance gate",
        "",
        "At least three matched seeds are required. CR/DVR may regress by at most 0.01; active-robot Jain must not regress; mean decision latency must stay within 50 ms; and at least two of distance, physical redispatch, delay and makespan must improve.",
        "",
        "| Scenario | Scale | n | CR/DVR safe | Jain safe | <=50 ms | Event integrity | Physical gains | Status |",
        "|---|---:|---:|---|---|---|---|---:|---|",
    ]
    for row in gates.itertuples(index=False):
        lines.append(
            f"| {row.scenario} | {row.robot_count}r/{row.target_count}t | "
            f"{row.n_matched} | {row.cr_dvr_nonregression} | "
            f"{row.fairness_nonregression} | {row.latency_within_50ms} | "
            f"{row.event_integrity} | "
            f"{row.supporting_improvements}/4 | **{row.status}** |"
        )
    lines += [
        "", "## Metric detail", "",
        "| Scenario | Scale | Metric | n | F45 | F58 | Improvement | 95% bootstrap CI | Wilcoxon p | Evidence |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.itertuples(index=False):
        ci = f"[{fmt(row.improvement_ci95_low)}, {fmt(row.improvement_ci95_high)}]"
        lines.append(
            f"| {row.scenario} | {row.robot_count}r/{row.target_count}t | "
            f"{row.metric} | {row.n_matched} | {fmt(row.reference_mean)} | "
            f"{fmt(row.candidate_mean)} | {fmt(row.improvement_mean)} | "
            f"{ci} | {fmt(row.wilcoxon_p)} | {row.evidence} |"
        )
    lines += [
        "",
        "> Smoke/pilot-only rows must not replace paper claims. F58 is promoted to the physical method only after the multi-seed gate passes.",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    reference = load_runs(args.reference_dir, "fresh F45")
    candidate = load_runs(args.candidate_dir, "F58")
    details, summary = compare(reference, candidate)
    gates = acceptance_gates(
        summary, completion_resurrections(args.reference_dir),
        completion_resurrections(args.candidate_dir))
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
