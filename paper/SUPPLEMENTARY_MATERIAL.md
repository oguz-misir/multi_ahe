# Supplementary Material: AHE-MRTA

This document holds configuration, execution, audit, and secondary-analysis
details removed from the main manuscript for concision. The manuscript revision
uses commit `e72f98a75358a7185425a43ff6044c5e1b9b2401` as its reference state.

## S1. Method configuration

The dominance update uses `alpha=0.65`, `beta=0.40`, `gamma=0.20`,
`eta=lambda=0.12`, and `delta=0.20`. The weight softmax temperature is `0.3`
and the paradigm dwell is four allocation events. Context is refreshed every
2 s; the deadline horizon is 60 s. The failure and deadline overrides fire at
`c4>0.05` and `c3>0.50`, respectively.

The static and recovery reference weights, ordered as distance, priority,
battery, load, failure, deadline, and recovery, are

```text
w0   = (0.34, 0.10, 0.04, 0.16, 0.10, 0.22, 0.04)
wrec = (0.55, 0.04, 0.03, 0.22, 0.09, 0.05, 0.02)
```

The ecosystem contribution is blended with weight `0.70`. During recovery,
the recovery vector weight is `min(0.80, 0.50 + 0.60*c4)`; deadline pressure
multiplies the urgency channel by `1.50`. The battery feature is zero in the
reported stack.

The context prototypes are:

| Paradigm | task density | availability | deadline pressure | failure rate |
|---|---:|---:|---:|---:|
| spatial-greedy | 0.7 | 0.7 | 0.1 | 0.1 |
| priority-first | 0.3 | 0.5 | 0.8 | 0.2 |
| EDF-strict | 0.5 | 0.5 | 0.9 | 0.1 |
| commit-once | 0.3 | 0.3 | 0.3 | 0.8 |
| orphan-first | 0.3 | 0.2 | 0.2 | 0.9 |

The nonzero interaction entries are `A[priority-first, EDF-strict]=0.20`,
`A[commit-once, orphan-first]=0.20`, and
`S[spatial-greedy, EDF-strict]=0.30`. The full seven-by-five paradigm-to-cost
map is defined in
`src/m_ahe_ecosystem_manager/m_ahe_ecosystem_manager/ecosystem_manager_node.py`;
the manuscript-ready prototype and interaction tables are retained as
`paper/table/proto_vectors.tex` and `paper/table/as_matrices.tex`.

The arrival feature is normalized by 220 s. The geodesic oracle uses an
eight-connected grid and a 0.55 m inflated occupancy mask. ETA uses effective
speed 0.22 m/s and queue overhead 22 s. Healthy incumbents move only when the
predicted-arrival improvement is at least 10%. Terminal repair permits at most
10% additional geodesic distance, operates when active tasks do not exceed
three per healthy robot, and never cancels an executing goal.

## S2. Evaluated implementation and baselines

The reported AHE-MRTA configuration enables geodesic ETA and terminal repair
with the following campaign flags:

```bash
AHE_F58_GEODESIC=1
AHE_F58_FAIR_REPAIR=1
AHE_F58_FAIR_RESERVATION_GAP=2
AHE_F58_FAIR_EXTRA_QUEUE=1
AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3
```

The exact campaign environment and the distinction from the historical class
defaults are recorded in `results/raw/gazebo_benchmark_f58/CONFIG.md`.

| Method | Event policy | Ownership and failure response | Distance/queue policy |
|---|---|---|---|
| AHE-MRTA | selected masked LSA plus bounded backfill and repair | in-flight lock; unhealthy queues become orphan work | geodesic ETA; queue cap 2 plus one repair slot |
| BiG-MRTA | maximum-weight bipartite matching | stable existing ownership; remaining work rematched | endpoint ETA; queue cap 5 |
| RoSTAM-EA | evolutionary search over unassigned tasks at each event | existing queued work retained; new candidate vector after events | population search; event-local unbounded queue |
| Consensus-DBTA | two-best-task bidding and simulated maximum consensus | limited rebidding after state changes | bid-based endpoint ETA; queue cap 5 |

These rows document the benchmark adaptations; they are not claims of complete
independent reproduction of the source systems.

## S3. Execution environment and run contract

Gazebo Harmonic, ROS 2 Jazzy, and Nav2 ran on Ubuntu 24.04 using an Intel
i7-11800H (8 cores/16 threads), 16 GiB RAM, and Mesa llvmpipe CPU rendering.
Each TurtleBot3 instance used an independent namespace and Nav2 stack.
Ground-truth-anchored localization isolated allocation from localization drift.

The closed-loop campaign contains 480 completed runs: 180 across the three
3-robot densities, 240 at 5 robots/25 tasks, and 60 at 10 robots/50 tasks.
Every experiment has a 900 s simulated-time horizon. The runner also uses a
1200 s wall-clock safety limit after task start; scale-specific shell and Nav2
startup limits are operational safeguards, not evaluation horizons. Per-run
`metadata.yaml` files are authoritative for robot count, task count, scenario,
seed, startup delay, and timeout.

The normal launch path is `run_experiments_robust.sh`. Task events, allocation
events, ecosystem states, robot time series, workload, runtime, communication,
metadata, and scalar summaries are stored under `results/raw/`; consolidated
analysis inputs are described in `results/README.md`. Lifecycle race handling,
namespace bridges, cleanup, and readiness checks remain in the launch and batch
scripts instead of the main paper.

## S4. Secondary analyses

The communication analysis counts only fields transmitted at an allocation
event. AHE-MRTA publishes one header per robot and 4 bytes per queued task, so
its reconstructed payload is 40, 71, and 137 bytes at 3, 5, and 10 robots.
Pooled payloads are 63 bytes for AHE-MRTA, 134 for BiG-MRTA, 239 for
Consensus-DBTA, and approximately 17 kB for RoSTAM-EA. The latter includes its
population exchange. `scripts/recompute_comm_footprint.py` and
`scripts/comm_override.py` contain the reconstruction.

Secondary efficiency, effect-size, trajectory, recovery, dominance, timeline,
and scalability tables and figures remain under `paper/table/`, `paper/figure/`,
and `results/figures/`. They are excluded from the main manuscript because they
do not change the primary completion/deadline claim.

## S5. Audit and revision provenance

The implemented priority multiplier rescales a negative shaped-cost bracket
and can therefore reverse its intended urgency ordering. The paired proxy audit
found a sub-percentage-point effect and no ranking change; the evaluated form
was retained to avoid post hoc retuning. Recovery-time missingness, latency
warm-up replacement, and communication reconstruction are documented in the
analysis scripts and `results/raw/gazebo_benchmark_f58/CONFIG.md`.

Preregistration and revision provenance are retained separately in
`paper/PREREGISTRATION.md`, `paper/REVISION_PLAN.md`,
`paper/REVISION_STATUS.md`, `SECTION_AUDIT_2026_08_03.md`,
`FIGURE_TABLE_AUDIT.md`, and `STALE_NUMBERS_AUDIT.md`. These files document
decision history and error correction; they are not part of the inferential
evidence presented in the main manuscript.
