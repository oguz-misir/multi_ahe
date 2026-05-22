"""
Phase 7 — Baseline Allocator Node  (strategy: static_weighted)

Allocation algorithm:
  Layer 1 — Global task-to-robot assignment
    For each active, unassigned task (sorted: priority desc, deadline asc)
    assign to the available robot with minimum weighted cost.
    Skip robots with CRITICAL battery or UNAVAILABLE state.

  Layer 2 — Per-robot task sequence ordering
    Adaptive (cheapest) insertion heuristic:
    for each robot's assigned task set, build a route by repeatedly
    inserting the task that causes the smallest tour-length increase.

Cost function (fixed weights W0):
  Cost(r_i, τ_j) = w_d·D + w_p·P + w_b·B + w_l·L + w_f·F + w_t·T + w_r·R

Publishes:  /robot_i/optimized_task_queue  (on allocation)
Subscribes: /tasks/global_pool, /robot_i/status_summary,
            /robot_i/task_feedback, /allocation/events

CSV output: results/raw/phase7_baseline/method_runtime.csv
            results/raw/phase7_baseline/allocation_events.csv
"""

import csv
import math
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Point
from m_ahe_mrta_msgs.msg import (
    AllocationEvent,
    OptimizedTaskQueue,
    RobotStatusSummary,
    TaskInfo,
    TaskPool,
    TaskWaypoint,
)
from std_msgs.msg import Header

# ---------------------------------------------------------------------------
# Fixed weights W0 = [w_d, w_p, w_b, w_l, w_f, w_t, w_r]
# ---------------------------------------------------------------------------
W0 = [0.40, 0.15, 0.10, 0.15, 0.05, 0.10, 0.05]

AVAIL_UNAVAILABLE = 2
BATT_CRITICAL = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _euclid(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(bx - ax, by - ay)


def _tour_length(pts: list[tuple[float, float]]) -> float:
    return sum(_euclid(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
               for i in range(len(pts) - 1))


def _cheapest_insertion_order(
    start: tuple[float, float],
    tasks: list[TaskInfo],
) -> list[TaskInfo]:
    """Build an ordered task list via cheapest insertion.

    Starts from robot's current position (start) and inserts each remaining
    task at the position in the current route that minimises route length increase.
    """
    if not tasks:
        return []

    # Route is a list of (x, y) points; tasks is parallel
    route_pts: list[tuple[float, float]] = [start]
    route_tasks: list[TaskInfo] = []
    remaining = list(tasks)

    # Seed: pick nearest task to start first
    nearest = min(remaining, key=lambda t: _euclid(
        start[0], start[1],
        t.target_pose.pose.position.x,
        t.target_pose.pose.position.y,
    ))
    remaining.remove(nearest)
    route_pts.append((
        nearest.target_pose.pose.position.x,
        nearest.target_pose.pose.position.y,
    ))
    route_tasks.append(nearest)

    while remaining:
        best_task = None
        best_pos = 0
        best_increase = float('inf')

        for task in remaining:
            tx = task.target_pose.pose.position.x
            ty = task.target_pose.pose.position.y
            for pos in range(1, len(route_pts) + 1):
                # Insert at pos: cost before insertion at edge (pos-1)->pos replaced by (pos-1)->new->pos
                prev = route_pts[pos - 1]
                nxt = route_pts[pos] if pos < len(route_pts) else None
                if nxt is None:
                    increase = _euclid(prev[0], prev[1], tx, ty)
                else:
                    old_edge = _euclid(prev[0], prev[1], nxt[0], nxt[1])
                    new_edges = (_euclid(prev[0], prev[1], tx, ty)
                                 + _euclid(tx, ty, nxt[0], nxt[1]))
                    increase = new_edges - old_edge

                if increase < best_increase:
                    best_increase = increase
                    best_task = task
                    best_pos = pos

        remaining.remove(best_task)
        route_pts.insert(best_pos, (
            best_task.target_pose.pose.position.x,
            best_task.target_pose.pose.position.y,
        ))
        route_tasks.insert(best_pos - 1, best_task)

    return route_tasks


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class BaselineAllocatorNode(Node):
    """Static-weighted baseline allocator (Phase 7)."""

    def __init__(self) -> None:
        super().__init__('baseline_allocator_node')

        self.declare_parameter('robot_count', 3)
        self.declare_parameter('alloc_period_sec', 5.0)
        self.declare_parameter('results_dir',
                               os.path.expanduser('~/multi_ahe/results/raw/phase7_baseline'))

        self._robot_count: int = self.get_parameter('robot_count').value
        self._period: float = self.get_parameter('alloc_period_sec').value
        self._results_dir: str = self.get_parameter('results_dir').value

        self._robots = [f'robot_{i + 1}' for i in range(self._robot_count)]

        # State
        self._pool: list[TaskInfo] = []
        self._pool_version: int = -1
        self._robot_states: dict[str, RobotStatusSummary] = {r: None for r in self._robots}
        # task_id → robot_id (current assignment)
        self._assigned: dict[str, str] = {}
        # robot_id → ordered list of TaskInfo currently queued
        self._robot_queue_tasks: dict[str, list[TaskInfo]] = {r: [] for r in self._robots}
        self._queue_version: int = 0
        self._force_realloc: bool = False
        # Track task start timestamps for deadline urgency
        self._task_activated_at: dict[str, float] = {}

        # Publishers (one per robot)
        self._queue_pubs: dict[str, any] = {
            r: self.create_publisher(OptimizedTaskQueue, f'/{r}/optimized_task_queue', 10)
            for r in self._robots
        }

        # Subscribers
        self.create_subscription(TaskPool, '/tasks/global_pool', self._pool_cb, 10)
        self.create_subscription(AllocationEvent, '/allocation/events', self._event_cb, 10)
        for r in self._robots:
            self.create_subscription(
                RobotStatusSummary, f'/{r}/status_summary',
                lambda msg, rr=r: self._status_cb(rr, msg), 10,
            )
            self.create_subscription(
                AllocationEvent, f'/{r}/task_feedback',
                self._task_feedback_cb, 10,
            )

        # CSV setup
        self._setup_csv()

        # Timer
        self.create_timer(self._period, self._maybe_allocate)

        self.get_logger().info(
            f'BaselineAllocator ready (strategy=static_weighted, '
            f'robots={self._robot_count}, period={self._period}s)'
        )

    # ------------------------------------------------------------------
    # CSV setup
    # ------------------------------------------------------------------

    def _setup_csv(self) -> None:
        os.makedirs(self._results_dir, exist_ok=True)

        rt_path = os.path.join(self._results_dir, 'method_runtime.csv')
        self._rt_file = open(rt_path, 'w', newline='')
        self._rt_writer = csv.writer(self._rt_file)
        self._rt_writer.writerow([
            'timestamp_s', 'strategy', 'pool_version',
            'tasks_assigned', 'total_queue_cost', 'latency_ms',
        ])

        ev_path = os.path.join(self._results_dir, 'allocation_events.csv')
        self._ev_file = open(ev_path, 'w', newline='')
        self._ev_writer = csv.writer(self._ev_file)
        self._ev_writer.writerow([
            'timestamp_s', 'event_type', 'robot_id', 'task_id',
            'strategy', 'pool_version',
        ])

    # ------------------------------------------------------------------
    # Subscribers
    # ------------------------------------------------------------------

    def _pool_cb(self, msg: TaskPool) -> None:
        if msg.pool_version == self._pool_version:
            return
        self._pool_version = msg.pool_version
        self._pool = list(msg.tasks)

        now_s = self.get_clock().now().nanoseconds / 1e9
        for task in self._pool:
            if task.active and task.task_id not in self._task_activated_at:
                self._task_activated_at[task.task_id] = now_s

        self._force_realloc = True

    def _status_cb(self, robot_id: str, msg: RobotStatusSummary) -> None:
        self._robot_states[robot_id] = msg

    def _task_feedback_cb(self, msg: AllocationEvent) -> None:
        tid = msg.task_id
        if msg.event_type == 'task_completed':
            self._assigned.pop(tid, None)
            for r in self._robots:
                self._robot_queue_tasks[r] = [
                    t for t in self._robot_queue_tasks[r] if t.task_id != tid
                ]
            self._log_event('task_completed', msg.robot_id, tid)

        elif msg.event_type == 'task_failed':
            self._assigned.pop(tid, None)
            for r in self._robots:
                self._robot_queue_tasks[r] = [
                    t for t in self._robot_queue_tasks[r] if t.task_id != tid
                ]
            self._force_realloc = True
            self._log_event('task_failed', msg.robot_id, tid)

    def _event_cb(self, msg: AllocationEvent) -> None:
        if msg.trigger_replan:
            self._force_realloc = True

    # ------------------------------------------------------------------
    # Allocation
    # ------------------------------------------------------------------

    def _maybe_allocate(self) -> None:
        if not self._force_realloc:
            # Check for new unassigned active tasks
            unassigned = self._get_unassigned_active_tasks()
            if not unassigned:
                return
        self._force_realloc = False
        self._run_allocation()

    def _get_unassigned_active_tasks(self) -> list[TaskInfo]:
        return [
            t for t in self._pool
            if t.active and not t.completed
            and t.task_id not in self._assigned
        ]

    def _run_allocation(self) -> None:
        t0 = time.monotonic()

        # Active, not completed, not currently being executed
        unassigned = self._get_unassigned_active_tasks()
        if not unassigned:
            return

        # Sort: priority desc, deadline asc
        now_s = self.get_clock().now().nanoseconds / 1e9
        unassigned.sort(key=lambda t: (-t.priority_level, t.deadline))

        total_cost = 0.0
        newly_assigned = 0

        for task in unassigned:
            best_robot = None
            best_cost = float('inf')

            for robot_id in self._robots:
                state = self._robot_states.get(robot_id)
                if state is None:
                    continue
                if state.availability_state == AVAIL_UNAVAILABLE:
                    continue
                if state.battery_state == BATT_CRITICAL:
                    continue

                cost = self._compute_cost(robot_id, task, state, now_s)
                if cost < best_cost:
                    best_cost = cost
                    best_robot = robot_id

            if best_robot is not None:
                self._assigned[task.task_id] = best_robot
                self._robot_queue_tasks[best_robot].append(task)
                total_cost += best_cost
                newly_assigned += 1
                self._log_event('task_assigned', best_robot, task.task_id)

        if newly_assigned == 0:
            return

        # Reorder each robot's queue via cheapest insertion
        self._queue_version += 1
        for robot_id in self._robots:
            tasks = self._robot_queue_tasks[robot_id]
            if not tasks:
                continue

            state = self._robot_states.get(robot_id)
            if state is not None:
                start = (
                    state.current_pose.pose.position.x,
                    state.current_pose.pose.position.y,
                )
            else:
                start = (0.0, 0.0)

            # Don't reorder tasks already being executed (first task if navigating)
            if (state is not None
                    and state.navigation_state == 1  # NAVIGATING
                    and tasks):
                executing = tasks[0]
                remaining = tasks[1:]
                ordered = [executing] + _cheapest_insertion_order(start, remaining)
            else:
                ordered = _cheapest_insertion_order(start, tasks)

            self._robot_queue_tasks[robot_id] = ordered
            self._publish_queue(robot_id, ordered)

        latency_ms = (time.monotonic() - t0) * 1000.0
        ts = self.get_clock().now().nanoseconds / 1e9
        self._rt_writer.writerow([
            f'{ts:.3f}', 'static_weighted', self._pool_version,
            newly_assigned, f'{total_cost:.4f}', f'{latency_ms:.2f}',
        ])
        self._rt_file.flush()

        self.get_logger().info(
            f'Allocated {newly_assigned} tasks in {latency_ms:.1f} ms '
            f'(pool_v={self._pool_version})'
        )

    # ------------------------------------------------------------------
    # Cost computation
    # ------------------------------------------------------------------

    def _compute_cost(
        self,
        robot_id: str,
        task: TaskInfo,
        state: RobotStatusSummary,
        now_s: float,
    ) -> float:
        w_d, w_p, w_b, w_l, w_f, w_t, w_r = W0

        # D: distance from robot's last queue endpoint to task
        queue = self._robot_queue_tasks[robot_id]
        if queue:
            last = queue[-1].target_pose.pose.position
            D = _euclid(
                last.x, last.y,
                task.target_pose.pose.position.x,
                task.target_pose.pose.position.y,
            )
        else:
            rx = state.current_pose.pose.position.x
            ry = state.current_pose.pose.position.y
            D = _euclid(
                rx, ry,
                task.target_pose.pose.position.x,
                task.target_pose.pose.position.y,
            )
        # Normalize: assume world ~20 m, max distance ~28 m diagonal
        D_norm = min(1.0, D / 28.0)

        # P: priority penalty (lower priority = higher cost)
        P = (4 - task.priority_level) / 3.0

        # B: battery risk
        B = float(state.battery_state) / 2.0  # 0, 0.5, 1.0

        # L: load balance (current queue length normalised)
        L = len(queue) / max(1.0, 15.0 / self._robot_count * 2)
        L = min(1.0, L)

        # F: failure flag
        F = 1.0 if state.failure_flag else 0.0

        # T: deadline urgency
        activated = self._task_activated_at.get(task.task_id, now_s)
        elapsed = now_s - activated
        if task.deadline > 0.0:
            T = min(1.0, elapsed / task.deadline)
        else:
            T = 0.0

        # R: reallocation penalty
        R = (1.0 if (task.task_id in self._assigned
                     and self._assigned[task.task_id] != robot_id) else 0.0)

        return w_d * D_norm + w_p * P + w_b * B + w_l * L + w_f * F + w_t * T + w_r * R

    # ------------------------------------------------------------------
    # Publisher
    # ------------------------------------------------------------------

    def _publish_queue(self, robot_id: str, ordered_tasks: list[TaskInfo]) -> None:
        msg = OptimizedTaskQueue()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.robot_id = robot_id
        msg.queue_version = self._queue_version
        msg.execution_mode = 'sequential'
        msg.replan_required = False

        waypoints: list[TaskWaypoint] = []
        total_cost = 0.0
        for task in ordered_tasks:
            wp = TaskWaypoint()
            wp.task_id = task.task_id
            wp.target_pose = task.target_pose
            wp.priority_level = task.priority_level
            wp.service_time = task.service_time
            wp.expected_arrival_time = 0.0
            wp.local_cost = 0.0
            wp.is_critical = task.priority_level >= 3
            wp.allow_skip = not wp.is_critical
            waypoints.append(wp)
            total_cost += task.priority_level  # simple proxy

        msg.waypoints = waypoints
        msg.queue_cost = total_cost
        self._queue_pubs[robot_id].publish(msg)
        self.get_logger().info(
            f'Published queue v{self._queue_version} to {robot_id}: '
            f'{len(waypoints)} waypoints'
        )

    # ------------------------------------------------------------------
    # CSV helpers
    # ------------------------------------------------------------------

    def _log_event(self, event_type: str, robot_id: str, task_id: str) -> None:
        ts = self.get_clock().now().nanoseconds / 1e9
        self._ev_writer.writerow([
            f'{ts:.3f}', event_type, robot_id, task_id,
            'static_weighted', self._pool_version,
        ])
        self._ev_file.flush()

    def destroy_node(self) -> None:
        self._rt_file.close()
        self._ev_file.close()
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = BaselineAllocatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
