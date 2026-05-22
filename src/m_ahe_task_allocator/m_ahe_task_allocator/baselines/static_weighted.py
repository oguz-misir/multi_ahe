"""static_weighted — Fixed-weight multi-criteria cost allocator (strong baseline).

Same algorithm as Phase 7 baseline_allocator_node but wrapped in BaseAllocator.
W0 = [w_d, w_p, w_b, w_l, w_f, w_t, w_r]
"""

import math
from .base_allocator import (
    AllocationResult, BaseAllocator, EcosystemContext,
    RobotState, TaskState, cheapest_insertion, measure, queue_endpoint,
)

W0 = [0.40, 0.15, 0.10, 0.15, 0.05, 0.10, 0.05]
BATT_CRITICAL = 2
AVAIL_UNAVAILABLE = 2
MAX_DIST = 28.0


class StaticWeightedAllocator(BaseAllocator):

    def name(self) -> str:
        return 'static_weighted'

    def _cost(self, robot: RobotState, task: TaskState,
               task_map: dict, current_queue: list,
               current_time: float, robot_count: int) -> float:
        w_d, w_p, w_b, w_l, w_f, w_t, w_r = W0
        endpoint = queue_endpoint(robot, task_map, current_queue)
        D = min(1.0, math.hypot(
            task.position[0] - endpoint[0],
            task.position[1] - endpoint[1],
        ) / MAX_DIST)
        P = (4 - task.priority) / 3.0
        B = 1.0 - robot.battery
        L = min(1.0, len(current_queue) / max(1.0, 15.0 / robot_count * 2))
        F = robot.failure_risk
        elapsed = current_time - task.activation_time
        T = min(1.0, elapsed / task.deadline) if task.deadline > 0 else 0.0
        R_nav = 1.0 if robot.navigation_state in (2, 3) else 0.0
        return w_d * D + w_p * P + w_b * B + w_l * L + w_f * F + w_t * T + w_r * R_nav

    @measure
    def allocate(
        self,
        robots: list,
        tasks: list,
        current_time: float,
        context: EcosystemContext = None,
    ) -> AllocationResult:
        task_map = {t.task_id: t for t in tasks}
        queues = {r.robot_id: list(r.queue) for r in robots}
        assigned = {tid for q in queues.values() for tid in q}

        unassigned = sorted(
            [t for t in tasks if t.task_id not in assigned],
            key=lambda t: (-t.priority, t.deadline),
        )

        for task in unassigned:
            best_robot = None
            best_cost = float('inf')
            for r in robots:
                if r.battery_state == BATT_CRITICAL or not r.available:
                    continue
                c = self._cost(r, task, task_map, queues[r.robot_id],
                               current_time, len(robots))
                if c < best_cost:
                    best_cost = c
                    best_robot = r.robot_id
            if best_robot is not None:
                queues[best_robot].append(task.task_id)
                assigned.add(task.task_id)

        ordered_queues: dict = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            ordered = cheapest_insertion(r.pose, q_tasks)
            ordered_queues[r.robot_id] = [t.task_id for t in ordered]

        return AllocationResult(queues=ordered_queues, latency_ms=0.0)
