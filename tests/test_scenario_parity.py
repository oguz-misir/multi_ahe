"""Both evaluation planes must mean the same thing by a scenario name.

The paper attributes the closed-loop separation to navigation realism, which is
only valid if the layers differ in navigation and nothing else.  They did not:
the Gazebo runner and the proxy each carried their own scenario parameters, and
the proxy's ``mixed_stress`` drifted until battery drain was the only thing
separating it from ``robot_failure``.

These tests pin the shared definitions against the Gazebo runner, which is the
reference implementation and the one the published campaign ran.  If either
side is edited alone, this fails.
"""

import os
import random
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, 'src', 'm_ahe_task_allocator'))

from m_ahe_task_allocator import scenarios  # noqa: E402

ALL_SCENARIOS = ('robot_failure', 'mixed_stress', 'deadline_pressure',
                 'dynamic_task_arrival')


def _runner_module():
    """Import the Gazebo runner, skipping when ROS is unavailable."""
    try:
        from m_ahe_task_allocator import experiment_runner_node as ern
    except Exception as exc:                       # rclpy / msgs not installed
        pytest.skip(f'Gazebo runner not importable here: {exc}')
    return ern


# --- the values the runner has been running -------------------------------

def test_deadline_multipliers_match_runner():
    ern = _runner_module()
    assert ern._DEADLINE_MULTIPLIERS == scenarios.DEADLINE_MULTIPLIERS


def test_failure_offset_matches_runner():
    ern = _runner_module()
    assert ern.FAILURE_TIME_OFFSET == scenarios.FAILURE_TIME_OFFSET_S


def test_horizon_matches_runner():
    ern = _runner_module()
    assert ern.EXPERIMENT_TIMEOUT_SEC == scenarios.HORIZON_S


# --- the properties the paper states --------------------------------------

@pytest.mark.parametrize('scenario', ALL_SCENARIOS)
@pytest.mark.parametrize('n_tasks', [9, 15, 24, 25, 50])
def test_batches_cover_every_task(scenario, n_tasks):
    batches = scenarios.activation_batches(scenario, n_tasks)
    assert sum(count for _, count in batches) == n_tasks
    assert all(count >= 0 for _, count in batches)


def test_wave_scenarios_stagger_and_others_do_not():
    assert len(scenarios.activation_batches('mixed_stress', 25)) == 3
    assert scenarios.activation_batches('mixed_stress', 25)[0][0] == 0.0
    assert [o for o, _ in scenarios.activation_batches('mixed_stress', 25)] \
        == list(scenarios.WAVE_OFFSETS_S)
    # robot_failure and deadline_pressure release everything at t0
    for sc in ('robot_failure', 'deadline_pressure'):
        assert scenarios.activation_batches(sc, 25) == [(0.0, 25)]


def test_mixed_stress_is_not_robot_failure():
    """The regression that started this: the two must differ structurally.

    In the proxy they had become identical apart from battery drain, which a
    seeded RoSTAM exposed by scoring byte-identically in both across 500 seeds.
    """
    assert (scenarios.activation_batches('mixed_stress', 25)
            != scenarios.activation_batches('robot_failure', 25))
    assert (scenarios.DEADLINE_MULTIPLIERS['mixed_stress']
            < scenarios.DEADLINE_MULTIPLIERS['robot_failure'])


def test_deadline_budgets_are_ordered_as_documented():
    m = scenarios.DEADLINE_MULTIPLIERS
    assert m['deadline_pressure'] < m['mixed_stress'] < m['robot_failure']


@pytest.mark.parametrize('scenario', ALL_SCENARIOS)
def test_deadline_draw_stays_in_the_documented_range(scenario):
    rng = random.Random(1)
    lo, hi = scenarios.DEADLINE_BASE_RANGE_S
    mult = scenarios.DEADLINE_MULTIPLIERS[scenario]
    for _ in range(500):
        d = scenarios.deadline_offset_s(scenario, rng)
        assert lo * mult <= d <= hi * mult


def test_failure_targets_a_fixed_robot_within_jitter():
    rng = random.Random(7)
    for sc in scenarios.FAILURE_SCENARIOS:
        for _ in range(200):
            (offset, target), = scenarios.failure_events(sc, rng)
            assert target == scenarios.FAILURE_TARGET_ID
            assert abs(offset - scenarios.FAILURE_TIME_OFFSET_S) \
                <= scenarios.FAILURE_JITTER_S
    assert scenarios.failure_events('deadline_pressure', rng) == []


def test_service_time_and_priority_ranges():
    rng = random.Random(3)
    lo, hi = scenarios.SERVICE_TIME_RANGE_S
    for _ in range(500):
        assert lo <= scenarios.service_time_s(rng) <= hi
        assert scenarios.priority(rng) in (1, 2, 3)
