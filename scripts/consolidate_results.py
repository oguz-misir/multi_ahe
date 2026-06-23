#!/usr/bin/env python3
"""
Phase 10 — Layer 2: Consolidate per-run raw CSVs into merged processed files.

Usage:
    python3 scripts/consolidate_results.py \
        --raw-dir results/raw/ \
        --processed-dir results/processed/
"""

import argparse
import os
import sys
import yaml
import pandas as pd
from pathlib import Path

# Reuse the physical (method-independent) stability metrics so all_summary.csv
# carries exec_preemptions / task_redispatch / redispatch_per_task instead of
# the flawed call-cadence counters (allocation_instability, replanning_frequency).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from recompute_stability_metrics import compute_for_exp  # noqa: E402

RAW_FILES = [
    "task_events.csv",
    "summary.csv",
    "robot_state_timeseries.csv",
    "robot_workload.csv",
    "allocation_events.csv",
    "method_runtime.csv",
    "communication_metrics.csv",
    "ecosystem_metrics.csv",
]

OUT_NAMES = {
    "task_events.csv":          "all_task_events.csv",
    "summary.csv":              "all_summary.csv",
    "robot_state_timeseries.csv": "all_robot_state_timeseries.csv",
    "robot_workload.csv":       "all_robot_workload.csv",
    "allocation_events.csv":    "all_allocation_events.csv",
    "method_runtime.csv":       "all_runtime.csv",
    "communication_metrics.csv": "all_communication.csv",
    "ecosystem_metrics.csv":    "all_ecosystem_metrics.csv",
}

REQUIRED_META_COLS = ["experiment_id", "scenario", "strategy", "seed",
                      "robot_count", "target_count"]


def load_metadata(exp_dir: Path) -> dict:
    meta_path = exp_dir / "metadata.yaml"
    if not meta_path.exists():
        return {}
    with open(meta_path) as f:
        return yaml.safe_load(f) or {}


def inject_meta(df: pd.DataFrame, meta: dict, exp_id: str) -> pd.DataFrame:
    for col in REQUIRED_META_COLS:
        if col not in df.columns:
            value = meta.get(col, exp_id if col == "experiment_id" else None)
            df.insert(0, col, value)
    return df


def consolidate(raw_dir: Path, processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)

    exp_dirs = sorted([d for d in raw_dir.iterdir() if d.is_dir()])
    if not exp_dirs:
        print(f"[WARN] No experiment directories found under {raw_dir}")

    frames: dict[str, list[pd.DataFrame]] = {f: [] for f in RAW_FILES}
    missing_report: dict[str, list[str]] = {}

    for exp_dir in exp_dirs:
        exp_id = exp_dir.name
        meta = load_metadata(exp_dir)

        for fname in RAW_FILES:
            fpath = exp_dir / fname
            if not fpath.exists():
                missing_report.setdefault(fname, []).append(exp_id)
                continue
            try:
                df = pd.read_csv(fpath)
                df = inject_meta(df, meta, exp_id)
                if fname == "summary.csv":
                    stab = compute_for_exp(exp_dir)
                    if stab:
                        df["exec_preemptions"] = stab["exec_preemptions"]
                        df["task_redispatch"] = stab["task_redispatch"]
                        df["redispatch_per_task"] = stab["redispatch_per_task"]
                frames[fname].append(df)
            except Exception as e:
                print(f"[ERROR] {exp_id}/{fname}: {e}")

    for fname, dfs in frames.items():
        out_path = processed_dir / OUT_NAMES[fname]
        if not dfs:
            print(f"[SKIP]  {OUT_NAMES[fname]} — no data collected")
            continue
        merged = pd.concat(dfs, ignore_index=True)
        merged.to_csv(out_path, index=False)
        print(f"[OK]    {out_path}  ({len(merged)} rows from {len(dfs)} experiments)")

    if missing_report:
        print("\n[Missing file report]")
        for fname, exps in missing_report.items():
            print(f"  {fname}: missing in {len(exps)} experiment(s)")
            for e in exps[:5]:
                print(f"    - {e}")
            if len(exps) > 5:
                print(f"    ... and {len(exps)-5} more")


def main() -> None:
    parser = argparse.ArgumentParser(description="Consolidate raw CSV files into processed merged files.")
    parser.add_argument("--raw-dir", default="results/raw", help="Directory containing per-run experiment folders")
    parser.add_argument("--processed-dir", default="results/processed", help="Output directory for merged CSVs")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    processed_dir = Path(args.processed_dir)

    if not raw_dir.exists():
        print(f"[ERROR] raw-dir does not exist: {raw_dir}")
        return

    consolidate(raw_dir, processed_dir)
    print("\n[DONE] Consolidation complete.")


if __name__ == "__main__":
    main()
