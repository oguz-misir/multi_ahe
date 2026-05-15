# AHE-MRTA Experiment Report

Generated: 2026-05-15 17:44  |  Target: IEEE RA-L (Q1)

---

## Experiment Coverage

Total experiment runs: **1104**

| Strategy | Runs |
|----------|------|
| AHE-FC | 92 |
| AHE-NoCS | 92 |
| AHE-NoD | 92 |
| AHE-NoER | 92 |
| Auction | 92 |
| BiG-MRTA | 92 |
| Cons-DBTA | 92 |
| EDF | 92 |
| AHE-MRTA* | 92 |
| Greedy | 92 |
| RoSTAM-EA | 92 |
| SW | 92 |

| Scenario | Runs |
|----------|------|
| deadline_pressure | 276 |
| dynamic_task_arrival | 276 |
| mixed_stress | 276 |
| robot_failure | 276 |

Seeds used: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

| Scale (R/T) | Runs |
|-------------|------|
| 3R/15T | 144 |
| 5R/25T | 960 |

---

## Key Results (mean across all seeds and scenarios)

| Method | Task Completion Rate | Makespan S | Average Task Delay | Deadline Violation Rate | Workload Balance | Failure Recovery Time | Allocation Instability | Mean Decision Latency Ms |
|---|---|---|---|---|---|---|---|---|
| Greedy | 1.000±0.000 | 140.495±27.669 | 47.617±9.848 | 0.099±0.114 | 0.245±0.149 | 35.678±44.833 | 1.216±0.398 | 0.000±0.000 |
| EDF | 1.000±0.000 | 151.549±30.882 | 54.179±14.905 | 0.061±0.107 | 0.391±0.225 | 42.662±52.146 | 1.316±0.490 | 0.000±0.000 |
| Auction | 0.995±0.020 | 150.516±64.043 | 46.516±11.303 | 0.078±0.104 | 0.473±0.258 | 35.527±42.793 | 1.316±0.705 | 0.000±0.000 |
| SW | 1.000±0.000 | 126.435±19.938 | 44.828±10.290 | 0.079±0.112 | 0.396±0.211 | 30.999±36.207 | 1.101±0.366 | 0.000±0.000 |
| BiG-MRTA | 0.956±0.067 | 221.304±112.283 | 41.306±8.199 | 0.033±0.055 | 0.535±0.284 | 34.357±39.692 | 2.058±1.288 | 0.000±0.000 |
| RoSTAM-EA | 0.956±0.066 | 239.130±110.326 | 53.030±16.659 | 0.113±0.152 | 0.433±0.205 | 24.243±38.332 | 2.189±1.276 | 0.000±0.000 |
| Cons-DBTA | 1.000±0.000 | 142.402±24.383 | 50.053±11.005 | 0.108±0.128 | 0.539±0.325 | 41.109±44.981 | 1.228±0.370 | 0.000±0.000 |
| AHE-NoD | 1.000±0.000 | 133.554±20.114 | 48.553±11.166 | 0.098±0.127 | 0.458±0.269 | 37.681±42.439 | 1.156±0.349 | 0.000±0.000 |
| AHE-NoCS | 1.000±0.000 | 134.141±20.698 | 48.574±10.947 | 0.097±0.125 | 0.450±0.264 | 37.571±41.502 | 1.161±0.349 | 0.000±0.000 |
| AHE-NoER | 1.000±0.000 | 132.609±21.550 | 47.531±11.782 | 0.088±0.118 | 0.423±0.249 | 36.665±42.578 | 1.148±0.358 | 0.000±0.000 |
| AHE-FC | 1.000±0.000 | 133.788±20.465 | 48.469±11.027 | 0.098±0.125 | 0.448±0.262 | 38.022±41.900 | 1.158±0.349 | 0.000±0.000 |
| AHE-MRTA* | 1.000±0.000 | 132.609±21.550 | 47.531±11.782 | 0.088±0.118 | 0.423±0.249 | 36.665±42.578 | 1.148±0.358 | 0.000±0.000 |

*Higher is better: task_completion_rate, workload_balance.*
*Lower is better: makespan_s, average_task_delay, deadline_violation_rate, failure_recovery_time, allocation_instability, mean_decision_latency_ms.*

---

## Figure Checklist

| Status | File | Label |
|--------|------|-------|
| ✅ Ready | `system_overview.png` | **Fig. 1 — System Architecture** (mandatory) |
| ✅ Ready | `adaptive_ecosystem_mechanism.png` | **Fig. 2 — AHE Mechanism** (mandatory) |
| ✅ Ready | `baseline_comparison_multi_metric.png` | **Fig. 3 — Baseline Comparison** (mandatory) |
| ✅ Ready | `ablation_comparison.png` | **Fig. 4 — Ablation Study** (mandatory) |
| ✅ Ready | `dominance_recovery_panel.png` | **Fig. 5 — Dominance & Recovery** (mandatory) |
| ✅ Ready | `communication_scalability_panel.png` | **Fig. 6 — Communication & Scalability** (mandatory) |
| ✅ Ready | `dominance_evolution.png` | Dominance Evolution (supplementary) |
| ✅ Ready | `failure_recovery.png` | Failure Recovery (supplementary) |
| ✅ Ready | `communication_footprint.png` | Communication Footprint (supplementary) |
| ✅ Ready | `allocation_instability.png` | Allocation Instability (supplementary) |
| ✅ Ready | `decision_latency.png` | Decision Latency (supplementary) |
| ✅ Ready | `task_completion_timeline.png` | Task Completion Timeline (supplementary) |
| ✅ Ready | `workload_distribution.png` | Workload Distribution (supplementary) |
| ✅ Ready | `compact_scalability_sanity.png` | Compact Scalability (optional) |

---

## Statistical Analysis (excerpt)

# AHE-MRTA Statistical Analysis Report

Generated from: `results/processed/all_summary.csv`

Strategies found: greedy_nearest, deadline_aware, auction_based, static_weighted, big_mrta, rostam_ea, consensus_dbta, ahe_no_dominance, ahe_no_cooperation_suppression, ahe_no_event_replanning, ahe_fixed_context, full_ahe_mrta

Metrics analysed: task_completion_rate, makespan_s, average_task_delay, deadline_violation_rate, workload_balance, failure_recovery_time, allocation_instability, mean_decision_latency_ms

---

## Table S1 — Descriptive Statistics

Mean ± Std, Median, and 95% CI per metric per strategy (all scenarios combined).


### Task Completion Rate

| Method | N | Mean | Std | Median | 95% CI |
|--------|---|------|-----|--------|--------|
| Greedy | 92 | 1.0000 | 0.0000 | 1.0000 | ±0.0000 |
| EDF | 92 | 1.0000 | 0.0000 | 1.0000 | ±0.0000 |
| Auction | 92 | 0.9951 | 0.0195 | 1.0000 | ±0.0040 |
| SW | 92 | 1.0000 | 0.0000 | 1.0000 | ±0.0000 |
| BiG-MRTA | 92 | 0.9559 | 0.0675 | 1.0000 | ±0.0138 |
| RoSTAM-EA | 92 | 0.9557 | 0.0656 | 1.0000 | ±0.0134 |
| Cons-DBTA | 92 | 1.0000 | 0.0000 | 1.0000 | ±0.0000 |
| AHE-NoD | 92 | 1.0000 | 0.0000 | 1.0000 | ±0.0000 |
| AHE-NoCS | 92 | 1.0000 | 0.0000 | 1.0000 | ±0.0000 |
| AHE-NoER | 92 | 1.0000 | 0.0000 | 1.0000 | ±0.0000 |
| AHE-FC | 92 | 1.0000 | 0.0000 | 1.0000 | ±0.0000 |
| AHE-MRTA* | 92 | 1.0000 | 0.0000 | 1.0000 | ±0.0000 |

### Makespan S

| Method | N | Mean | Std | Median | 95% CI |
|--------|---|------|-----|--------|--------|
| Greedy | 92 | 140.4946 | 27.6690 | 135.7500 | ±5.6540 |
| EDF | 92 | 151.5489 | 30.8823 | 147.2500 | ±6.3106 |
| Auction | 92 | 150.5163 | 64.0431 | 130.2500 | ±13.0868 |
| SW | 92 | 126.4348 | 19.9384 | 127.0000 | ±4.0743 |
| BiG-MRTA | 92 | 221.3043 | 112.2833 | 143.2500 | ±22.9444 |
| RoSTAM-EA | 92 | 239.1304 | 110.3259 | 171.0000 | ±22.5445 |
| Cons-DBTA | 92 | 142.4022 | 24.3831 | 139.2500 | ±4.9825 |
| AHE-NoD | 92 | 133.5543 | 20.1138 | 131.2500 | ±4.1101 |
| AHE-NoCS | 92 | 134.1413 | 20.6983 | 131.2500 | ±4.2296 |
| AHE-NoER | 92 | 132.6087 | 21.5502 | 128.7500 | ±4.4037 |
| AHE-FC | 92 | 133.7880 | 20.4650 | 131.0000 | ±4.1819 |
| AHE-MRTA* | 92 | 132.6087 | 21.5502 | 128.7500 | ±4.4037 |

### Average Task Delay

| Method | N | Mean | Std | Median | 95% CI |
|--------|---|------|-----|--------|--------|
| Greedy | 92 | 47.6168 | 9.8478 | 47.5000 | ±2.0123 |
| EDF | 92 | 54.1787 | 14.9047 | 56.9400 | ±3.0457 |
| Auction | 92 | 46.5162 | 11.3027 | 48.7700 | ±2.3096 |
| SW | 92 | 44.8280 | 10.2897 | 49.3200 | ±2.1026 |
| BiG-MRTA | 92 | 41.3058 | 8.1986 | 40.2300 | ±1.6753 |
| RoSTAM-EA | 92 | 53.0298 | 16.6586 | 52.2700 | ±3.4041 |
| Cons-DBTA | 92 | 50.0525 | 11.0048 | 50.5000 | ±2.2488 |
| AHE-NoD | 92 | 48.5527 | 11.1659 | 52.0150 | ±2.2817 |
| AHE-NoCS | 92 | 48.5740 | 10.9467 | 52.0150 | ±2.2369 |
| AHE-NoER | 92 | 47.5309 | 11.7820 | 51.3700 | ±2.4076 |
| AHE-FC | 92 | 48.4690 | 11.0273 | 52.0150 | ±2.2534 |
| AHE-MRTA* | 92 | 47.5309 | 11.7820 | 51.3700 | ±2.4076 |

### Deadline Violation Rate

| Method | N | Mean | Std | Median | 95% CI |
|--------|---|------|-----|--------|--------|
| Greedy | 92 | 0.0993 | 0.1143 | 0.0533 | ±0.0234 |
| EDF | 92 | 0.0614 | 0.1075 | 0.0000 | ±0.0220 |
| Auction | 92 | 0.0781 | 0.1044 | 0.0400 | ±0.0213 |
| SW | 92 | 0.0793 | 0.1124 | 0.0000 | ±0.0230 |
| BiG-MRTA | 92 | 0.0331 | 0.0555 | 0.0000 | ±0.0113 |
| RoSTAM-EA | 92 | 0.1131 | 0.1519 | 0.0417 | ±0.0310 |
| Cons-DBTA | 92 | 0.1077 | 0.1283 | 0.0400 | ±0.0262 |
| AHE-NoD | 92 | 0.0980 | 0.1267 | 0.0400 | ±0.0259 |
| AHE-NoCS | 92 | 0.0971 | 0.1249 | 0.0400 | ±0.0255 |
| AHE-NoER | 92 | 0.0875 | 0.1176 | 0.0400 | ±0.0240 |

_(Full tables in statistical_tables.md)_


---

## Mandatory Output Checklist

| Item | Status |
|------|--------|
| results/paper_figures/system_overview.png | ✅ |
| results/paper_figures/adaptive_ecosystem_mechanism.png | ✅ |
| results/paper_figures/baseline_comparison_multi_metric.png | ✅ |
| results/paper_figures/ablation_comparison.png | ✅ |
| results/paper_figures/dominance_recovery_panel.png | ✅ |
| results/paper_figures/communication_scalability_panel.png | ✅ |
| results/reports/statistical_tables.md | ✅ |
| results/reports/summary_report.md | ✅ (this file) |
