#!/usr/bin/env python3
"""Regression tests for the F58 fairness-first Gazebo promotion gate."""

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compare_f58_gazebo import acceptance_gates, completion_resurrections


def make_summary(*, jain: float = 0.001, latency: float = 20.0) -> pd.DataFrame:
    improvements = {
        "task_completion_rate": 0.0,
        "deadline_violation_rate": 0.01,
        "workload_balance_active": jain,
        "total_travel_distance": 1.0,
        "redispatch_per_task": 0.0,
        "average_task_delay": 1.0,
        "makespan_s": 0.0,
        "mean_decision_latency_ms": -latency,
    }
    return pd.DataFrame([
        {
            "scenario": "deadline_pressure",
            "robot_count": 5,
            "target_count": 25,
            "metric": metric,
            "n_matched": 5,
            "improvement_mean": value,
            "candidate_mean": latency if metric == "mean_decision_latency_ms" else 0.0,
        }
        for metric, value in improvements.items()
    ])


def test_gate_passes_only_when_fairness_and_latency_are_safe():
    assert acceptance_gates(make_summary()).status.iloc[0] == "PASS"
    assert acceptance_gates(make_summary(jain=-0.001)).status.iloc[0] == "FAIL"
    assert acceptance_gates(make_summary(latency=51.0)).status.iloc[0] == "FAIL"


def test_completed_task_reassignment_is_hard_gate_failure(tmp_path):
    run = tmp_path / "r5t25" / "exp_seed01"
    run.mkdir(parents=True)
    (run / "task_events.csv").write_text(
        "timestamp_s,task_id,event,robot_id,strategy,scenario,seed\n"
        "10,t1,completed,r1,ahe,deadline_pressure,1\n"
        "15,t1,assigned,r1,ahe,deadline_pressure,1\n",
        encoding="utf-8")
    ghosts = completion_resurrections(tmp_path)
    gates = acceptance_gates(make_summary(), {}, ghosts)
    assert not gates.event_integrity.iloc[0]
    assert gates.status.iloc[0] == "FAIL"
