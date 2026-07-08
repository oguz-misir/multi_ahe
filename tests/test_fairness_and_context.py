#!/usr/bin/env python3
"""Focused regression tests for fairness and Plane-A/Plane-B context parity."""

import os
import sys
import unittest
import math
from types import SimpleNamespace


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src', 'm_ahe_task_allocator'))
sys.path.insert(0, os.path.join(ROOT, 'src', 'm_ahe_ecosystem_manager'))

from m_ahe_task_allocator.baselines.ahe_variants import AHEMRTAv3Allocator
from m_ahe_task_allocator.baselines.base_allocator import (
    RobotState,
    TaskState,
    jain_index,
)
from m_ahe_task_allocator.geodesic_cost import (
    clear_geodesic_cache, geodesic_cache_info, geodesic_distance,
)
from m_ahe_ecosystem_manager.ecosystem_manager_node import (
    EcosystemManagerNode,
    _deadline_pressure,
)


def robot(robot_id, x, completed, distance=0.0):
    return RobotState(
        robot_id=robot_id,
        pose=(x, 0.0),
        battery=1.0,
        available=True,
        current_task_id='',
        queue=[],
        completed_tasks=completed,
        travel_distance=distance,
    )


def task(task_id, x):
    return TaskState(
        task_id=task_id,
        position=(x, 0.0),
        priority=2,
        activation_time=0.0,
        deadline=100.0,
        service_time=2.0,
    )


class JainIndexTests(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(jain_index([0, 0, 0]), 0.0)
        self.assertAlmostEqual(jain_index([3, 3, 3]), 1.0)
        self.assertAlmostEqual(jain_index([1, 0]), 0.5)

    def test_scale_invariance(self):
        self.assertAlmostEqual(jain_index([1, 2, 3]),
                               jain_index([10, 20, 30]))


class ContextTests(unittest.TestCase):
    def test_deadline_pressure_uses_remaining_time(self):
        tasks = [
            SimpleNamespace(active=True, completed=False, deadline=150.0),
            SimpleNamespace(active=True, completed=False, deadline=170.0),
            SimpleNamespace(active=True, completed=False, deadline=0.0),
            SimpleNamespace(active=False, completed=False, deadline=120.0),
        ]
        self.assertAlmostEqual(_deadline_pressure(tasks, now=100.0), 1.0 / 3.0)

    def test_expired_deadline_remains_pressure(self):
        tasks = [SimpleNamespace(active=True, completed=False, deadline=90.0)]
        self.assertEqual(_deadline_pressure(tasks, now=100.0), 1.0)

    def test_injected_failure_is_persisted_in_context_state(self):
        state = SimpleNamespace(_externally_failed=set(),
                                _reassigned_this_cycle=0)
        event = SimpleNamespace(event_type='robot_failure', robot_id='robot_2',
                                trigger_replan=True)
        EcosystemManagerNode._event_cb(state, event)
        self.assertEqual(state._externally_failed, {'robot_2'})
        self.assertEqual(state._reassigned_this_cycle, 1)

    def test_external_failure_affects_availability_and_failure_context(self):
        healthy_busy = SimpleNamespace(availability_state=1,
                                       navigation_state=1,
                                       failure_flag=False)
        state = SimpleNamespace(
            _robot_count=3,
            _robots=['robot_1', 'robot_2', 'robot_3'],
            _pool=[],
            _robot_states={
                'robot_1': healthy_busy,
                'robot_2': healthy_busy,
                'robot_3': healthy_busy,
            },
            _externally_failed={'robot_2'},
            get_clock=lambda: SimpleNamespace(
                now=lambda: SimpleNamespace(nanoseconds=int(100e9))),
        )
        ctx = EcosystemManagerNode._compute_context(state)
        self.assertAlmostEqual(ctx[1], 2.0 / 3.0)  # BUSY robots still available
        self.assertAlmostEqual(ctx[3], 1.0 / 3.0)


class FairAntiIdleTests(unittest.TestCase):
    def setUp(self):
        self.alloc = AHEMRTAv3Allocator()
        self.alloc.F53_FAIR_ANTI_IDLE = True
        self.alloc.FAIR_ANTI_IDLE_SLACK_M = 2.0

    def test_under_served_near_robot_wins(self):
        robots = [robot('r_busy', 0.0, completed=5),
                  robot('r_fair', 1.0, completed=1)]
        pending = task('t1', 0.0)
        result = self.alloc._anti_idle_dispatch(
            {'r_busy': [], 'r_fair': []}, robots, [pending],
            {'t1': pending}, current_time=0.0)
        self.assertEqual(result['r_fair'], ['t1'])

    def test_fairness_never_crosses_distance_window(self):
        robots = [robot('r_near', 0.0, completed=5),
                  robot('r_far', 5.0, completed=0)]
        pending = task('t1', 0.0)
        result = self.alloc._anti_idle_dispatch(
            {'r_near': [], 'r_far': []}, robots, [pending],
            {'t1': pending}, current_time=0.0)
        self.assertEqual(result['r_near'], ['t1'])

    def test_tie_break_is_deterministic(self):
        robots = [robot('r2', -1.0, completed=1, distance=3.0),
                  robot('r1', 1.0, completed=1, distance=3.0)]
        pending = task('t1', 0.0)
        result = self.alloc._anti_idle_dispatch(
            {'r2': [], 'r1': []}, robots, [pending],
            {'t1': pending}, current_time=0.0)
        self.assertEqual(result['r1'], ['t1'])


class PairReachabilityMemoryTests(unittest.TestCase):
    def setUp(self):
        self.alloc = AHEMRTAv3Allocator()
        self.alloc.F57_PAIR_MEMORY_ENABLED = True
        self.alloc.F57_QUARANTINE_AFTER = 2
        self.robots = [robot('r_bad', 0.0, completed=0),
                       robot('r_good', 1.0, completed=0)]

    def test_repeatedly_failing_pair_is_quarantined(self):
        pending = task('t1', 0.0)
        pending.failure_by_robot = {'r_bad': 2}
        self.assertTrue(self.alloc._pair_is_quarantined(
            self.robots[0], pending, self.robots))
        self.assertFalse(self.alloc._pair_is_quarantined(
            self.robots[1], pending, self.robots))

    def test_equal_failure_evidence_does_not_lock_task(self):
        pending = task('t1', 0.0)
        pending.failure_by_robot = {'r_bad': 2, 'r_good': 2}
        self.assertFalse(self.alloc._pair_is_quarantined(
            self.robots[0], pending, self.robots))
        self.assertFalse(self.alloc._pair_is_quarantined(
            self.robots[1], pending, self.robots))

    def test_no_failure_has_zero_cost(self):
        pending = task('t1', 0.0)
        self.assertEqual(
            self.alloc._pair_failure_cost(self.robots[0], pending, self.robots),
            0.0)


class F58GeodesicRepairTests(unittest.TestCase):
    def test_geodesic_respects_obstacles(self):
        start, goal = (-6.0, 7.0), (6.0, -6.0)
        direct = math.dist(start, goal)
        routed = geodesic_distance(start, goal, 0.10)
        self.assertTrue(math.isfinite(routed))
        self.assertGreater(routed, direct + 5.0)

    def test_moving_starts_share_static_goal_distance_field(self):
        clear_geodesic_cache()
        goal = (6.0, -6.0)
        self.assertTrue(math.isfinite(
            geodesic_distance((-6.0, 7.0), goal, 0.10)))
        self.assertTrue(math.isfinite(
            geodesic_distance((-5.5, 7.0), goal, 0.10)))
        info = geodesic_cache_info()['fields']
        self.assertEqual(info.misses, 1)
        self.assertEqual(info.hits, 1)

    def test_disabled_oracle_is_exact_euclidean(self):
        alloc = AHEMRTAv3Allocator()
        alloc.F58_GEODESIC_ENABLED = False
        self.assertEqual(alloc._travel_distance((0.0, 0.0), (3.0, 4.0)), 5.0)

    def test_epsilon_repair_reduces_max_burden_without_extra_distance(self):
        alloc = AHEMRTAv3Allocator()
        alloc.F58_FAIR_REPAIR_ENABLED = True
        alloc._prev_robot_for_task = {}
        r1 = robot('r1', 0.0, completed=0)
        r2 = robot('r2', 2.0, completed=0)
        t1, t2 = task('t1', 1.0), task('t2', 2.0)
        queues = {'r1': ['t1', 't2'], 'r2': []}
        repaired = alloc._epsilon_fair_repair(
            queues, {'t1': t1, 't2': t2}, [r1, r2], 0.0,
            {'r1': 2, 'r2': 2})
        self.assertEqual(len(repaired['r1']), 1)
        self.assertEqual(len(repaired['r2']), 1)

    def test_completed_service_remains_in_realised_burden(self):
        alloc = AHEMRTAv3Allocator()
        alloc.F58_FAIR_REPAIR_ENABLED = True
        alloc.F58_GEODESIC_ENABLED = False
        alloc._prev_robot_for_task = {}
        alloc._assign_history = {}
        r1 = robot('r1', 0.0, completed=3)
        r2 = robot('r2', 1.0, completed=0)
        r2.travel_distance = 2.0
        pending = task('t1', 1.0)
        repaired = alloc._epsilon_fair_repair(
            {'r1': ['t1'], 'r2': []}, {'t1': pending}, [r1, r2], 0.0,
            {'r1': 2, 'r2': 2})
        self.assertEqual(repaired, {'r1': [], 'r2': ['t1']})

    def test_jain_gain_may_trade_burden_only_inside_distance_envelope(self):
        alloc = AHEMRTAv3Allocator()
        alloc.F58_FAIR_REPAIR_ENABLED = True
        alloc.F58_GEODESIC_ENABLED = False
        alloc.F58_FAIR_EPSILON = 0.02
        alloc.F58_MAX_BURDEN_NONREGRESSION = False
        alloc._prev_robot_for_task = {}
        alloc._assign_history = {}
        busy = robot('busy', 0.0, completed=4)
        idle = robot('idle', 1.0, completed=0)
        # Moving this new task raises the max travel burden at the idle robot,
        # but leaves total route distance unchanged and strongly raises Jain.
        idle.travel_distance = 20.0
        pending = task('t1', 0.5)
        repaired = alloc._epsilon_fair_repair(
            {'busy': ['t1'], 'idle': []}, {'t1': pending}, [busy, idle], 0.0,
            {'busy': 2, 'idle': 2})
        self.assertEqual(repaired, {'busy': [], 'idle': ['t1']})

    def test_current_call_task_is_movable_after_core_history_update(self):
        alloc = AHEMRTAv3Allocator()
        alloc.F58_FAIR_REPAIR_ENABLED = True
        alloc.F58_GEODESIC_ENABLED = False
        alloc._prev_robot_for_task = {}
        # Simulate _allocate_core recording a task before the outer repair.
        alloc._assign_history = {'t1': 'busy'}
        busy = robot('busy', 0.0, completed=4)
        idle = robot('idle', 1.0, completed=0)
        pending = task('t1', 0.5)
        repaired = alloc._epsilon_fair_repair(
            {'busy': ['t1'], 'idle': []}, {'t1': pending}, [busy, idle], 0.0,
            {'busy': 2, 'idle': 2}, movable_task_ids={'t1'})
        self.assertEqual(repaired, {'busy': [], 'idle': ['t1']})

    def test_underworked_robot_gets_one_fair_reservation_slot(self):
        alloc = AHEMRTAv3Allocator()
        alloc.F58_FAIR_REPAIR_ENABLED = True
        alloc.F58_GEODESIC_ENABLED = False
        alloc.F58_FAIR_EPSILON = 0.20
        # Isolate the reservation mechanism; P1R's production guard is tested
        # separately below.
        alloc.F58_REMAINING_MAKESPAN_NONREGRESSION = False
        alloc._prev_robot_for_task = {}
        alloc._assign_history = {}
        busy = robot('busy', 0.0, completed=7)
        low = robot('low', 0.0, completed=4)
        tasks = {name: task(name, 0.0) for name in ('new', 'a', 'b')}
        repaired = alloc._epsilon_fair_repair(
            {'busy': ['new'], 'low': ['a', 'b']}, tasks, [busy, low], 0.0,
            {'busy': 2, 'low': 2}, movable_task_ids={'new'})
        self.assertEqual(repaired['busy'], [])
        self.assertEqual(repaired['low'], ['a', 'b', 'new'])

    def test_fair_move_cannot_increase_remaining_makespan(self):
        alloc = AHEMRTAv3Allocator()
        alloc.F58_FAIR_REPAIR_ENABLED = True
        alloc.F58_GEODESIC_ENABLED = False
        alloc.F58_FAIR_EPSILON = 0.20
        alloc._prev_robot_for_task = {}
        alloc._assign_history = {}
        busy = robot('busy', 0.0, completed=7)
        low = robot('low', 0.0, completed=4)
        tasks = {name: task(name, 0.0) for name in ('new', 'a', 'b')}
        queues = {'busy': ['new'], 'low': ['a', 'b']}
        repaired = alloc._epsilon_fair_repair(
            queues, tasks, [busy, low], 0.0,
            {'busy': 2, 'low': 2}, movable_task_ids={'new'})
        self.assertEqual(repaired, queues)

    def test_orphan_from_unhealthy_owner_is_explicitly_movable(self):
        alloc = AHEMRTAv3Allocator()
        history_before = {'orphan': 'failed'}
        alloc._unhealthy_rids = {'failed'}
        queues = {'healthy': ['orphan']}
        movable = {
            tid for q in queues.values() for tid in q
            if (tid not in history_before
                or history_before.get(tid) in alloc._unhealthy_rids)
        }
        self.assertEqual(movable, {'orphan'})

    def test_inflight_task_has_one_locked_owner(self):
        alloc = AHEMRTAv3Allocator()
        r1 = robot('r1', 0.0, completed=0)
        r2 = robot('r2', 2.0, completed=0)
        r1.current_task_id = 't1'
        r1.navigation_state = 1
        clean = alloc._enforce_unique_assignments(
            {'r1': [], 'r2': ['t1', 't2', 't2']}, [r1, r2])
        self.assertEqual(clean['r1'], ['t1'])
        self.assertEqual(clean['r2'], ['t2'])

    def test_reached_task_is_not_resurrected_from_stale_status(self):
        alloc = AHEMRTAv3Allocator()
        reached = robot('reached', 0.0, completed=1)
        reached.current_task_id = 'already_done'
        reached.navigation_state = 4
        clean = alloc._enforce_unique_assignments({'reached': []}, [reached])
        self.assertEqual(clean['reached'], [])

    def test_closed_task_is_pruned_from_persistent_queue(self):
        alloc = AHEMRTAv3Allocator()
        clean = alloc._prune_closed_tasks(
            {'r1': ['completed', 'open', 'open']},
            {'open': task('open', 1.0)})
        self.assertEqual(clean, {'r1': ['open']})

    def test_terminal_repair_threshold_defaults_to_p1r_window(self):
        alloc = AHEMRTAv3Allocator()
        self.assertEqual(alloc.F58_FAIR_TERMINAL_TASKS_PER_ROBOT, 3.0)


if __name__ == '__main__':
    unittest.main()
