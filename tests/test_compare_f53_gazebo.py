#!/usr/bin/env python3
"""Regression tests for matched F53 Gazebo reporting."""

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compare_f53_gazebo import acceptance_gates, compare, load_runs
from validate_f53_sim import holm_adjust


def write_run(root: Path, name: str, *, balance_value: float,
              completed: list[int], distance: float, delay: float) -> None:
    run = root / name
    run.mkdir(parents=True)
    pd.DataFrame([{
        "scenario": "deadline_pressure",
        "strategy": "ahe_mrta_v3",
        "seed": 1,
        "robot_count": 3,
        "target_count": 15,
        "task_completion_rate": 1.0,
        "deadline_violation_rate": 0.2,
        "average_task_delay": delay,
        "total_travel_distance": distance,
        "workload_balance": balance_value,
    }]).to_csv(run / "summary.csv", index=False)
    pd.DataFrame({
        "robot_id": [f"robot_{i}" for i in range(len(completed))],
        "completed_tasks": completed,
        "approx_distance_m": [distance / len(completed)] * len(completed),
    }).to_csv(run / "robot_workload.csv", index=False)


def test_recomputes_jain_and_orients_lower_is_better(tmp_path):
    reference_dir = tmp_path / "reference"
    candidate_dir = tmp_path / "candidate"
    reference_dir.mkdir()
    candidate_dir.mkdir()
    name = "exp_deadline_pressure_ahe_mrta_v3_r3t15_seed01"
    write_run(reference_dir, name, balance_value=1.0,
              completed=[6, 6, 3], distance=120.0, delay=100.0)
    write_run(candidate_dir, name, balance_value=0.1,
              completed=[5, 5, 5], distance=100.0, delay=90.0)

    reference = load_runs(reference_dir, "reference")
    candidate = load_runs(candidate_dir, "candidate")
    assert reference.workload_balance.iloc[0] < 1.0
    assert candidate.workload_balance.iloc[0] == 1.0

    _, summary = compare(reference, candidate)
    metrics = summary.set_index("metric")
    assert metrics.loc["workload_balance", "improvement_mean"] > 0
    assert metrics.loc["total_travel_distance", "improvement_mean"] == 20.0
    assert metrics.loc["average_task_delay", "improvement_mean"] == 10.0
    assert acceptance_gates(summary).status.iloc[0] == "INSUFFICIENT"


def test_holm_adjustment_is_monotone():
    adjusted = holm_adjust(pd.Series([0.01, 0.02, 0.04]))
    assert adjusted.tolist() == [0.03, 0.04, 0.04]
