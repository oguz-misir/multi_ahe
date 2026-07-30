"""Stress-scenario definitions shared by both evaluation planes.

The paper evaluates on three layers that are supposed to differ *only* in how
navigation is modelled -- that is the whole basis for attributing the closed-loop
separation to navigation realism rather than to a different experiment.  For a
long time they did not: ``experiment_runner_node`` (Gazebo) and
``scripts/simulate_and_tune.py`` (allocation-only and stochastic proxy) each
carried their own copy of the scenario parameters, and the copies drifted.

The proxy's ``mixed_stress`` ended up differing from its ``robot_failure`` by
battery drain alone -- no extra arrival waves, no tightened deadline -- which is
how a seeded RoSTAM produced byte-identical results in the two scenarios across
all 500 seeds.  A previous fix (bcc7af2) aligned the Gazebo side with the paper
and left the proxy untouched, so a single-sided repair is exactly the failure
mode this module exists to prevent.

Everything a scenario means now lives here, and both planes read it.  The values
are the ones the Gazebo runner has been running and the paper documents in
"Stress Scenarios"; this module is an extraction, not a redesign.

Deadlines are anchored at run start for every task, including tasks that
activate in a later wave -- later waves therefore arrive with less slack, which
is the intended pressure.
"""

from typing import List, Tuple

# Run horizon.  A task still open at the horizon counts as unfinished.
HORIZON_S = 900.0

# Deadline budget: a per-task draw from the base range, scaled per scenario.
DEADLINE_BASE_RANGE_S = (90.0, 300.0)
DEADLINE_MULTIPLIERS = {
    'dynamic_task_arrival': 1.0,
    'robot_failure':        1.0,
    'mixed_stress':         0.5,   # halved budget
    'deadline_pressure':    0.4,   # tight; part of the set is unservable by design
}

# Per-task service time at the waypoint, and priority draw.
SERVICE_TIME_RANGE_S = (2.0, 8.0)
PRIORITY_RANGE = (1, 3)

# Staggered demand.  Scenarios not listed release all tasks at t0.
WAVE_SCENARIOS = ('dynamic_task_arrival', 'mixed_stress')
WAVE_OFFSETS_S = (0.0, 30.0, 60.0)

# Failure injection.  The target is a fixed robot index rather than a random
# one so that the recovery burden is identical across methods for a given seed.
FAILURE_SCENARIOS = ('robot_failure', 'mixed_stress')
FAILURE_TIME_OFFSET_S = 45.0
FAILURE_JITTER_S = 5.0
FAILURE_TARGET_INDEX = 2          # 1-based; 'robot_2'
FAILURE_TARGET_ID = 'robot_2'


def deadline_offset_s(scenario: str, rng) -> float:
    """Seconds from run start to this task's deadline."""
    lo, hi = DEADLINE_BASE_RANGE_S
    return rng.uniform(lo, hi) * DEADLINE_MULTIPLIERS.get(scenario, 1.0)


def service_time_s(rng) -> float:
    return float(rng.uniform(*SERVICE_TIME_RANGE_S))


def priority(rng) -> int:
    return rng.randint(*PRIORITY_RANGE)


def activation_batches(scenario: str, n_tasks: int) -> List[Tuple[float, int]]:
    """``[(offset_seconds, task_count), ...]`` for this scenario.

    Wave scenarios split the pool into three near-equal batches; the remainder
    goes to the last wave so the counts always sum to ``n_tasks``.
    """
    if scenario in WAVE_SCENARIOS:
        b = max(1, n_tasks // 3)
        return [(WAVE_OFFSETS_S[0], b),
                (WAVE_OFFSETS_S[1], b),
                (WAVE_OFFSETS_S[2], n_tasks - 2 * b)]
    return [(0.0, n_tasks)]


def failure_events(scenario: str, rng) -> List[Tuple[float, str]]:
    """``[(offset_seconds, robot_id)]``, or empty when the scenario has none."""
    if scenario in FAILURE_SCENARIOS:
        offset = FAILURE_TIME_OFFSET_S + rng.uniform(-FAILURE_JITTER_S,
                                                     FAILURE_JITTER_S)
        return [(offset, FAILURE_TARGET_ID)]
    return []
