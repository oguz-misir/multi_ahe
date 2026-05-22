"""big_mrta — Online Weighted Bipartite Graph MRTA (Ghassemi & Chowdhury, 2022).

Adaptation for AHE-MRTA TurtleBot/Nav2 benchmark:
  - UAV range → simulated battery margin
  - repeated maximum weighted bipartite matching (scipy linear_sum_assignment)
  - local cheapest-insertion ordering per robot
"""

import math
from .base_allocator import (
    AllocationResult, BaseAllocator, EcosystemContext,
    RobotState, TaskState, cheapest_insertion, measure, queue_endpoint,
)

try:
    from scipy.optimize import linear_sum_assignment
    import numpy as np
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

SPEED = 0.26          # m/s
ALPHA = 60.0          # time scaling factor
EPSILON = 0.05        # battery safety margin
MAX_QUEUE = 5         # max tasks per robot per allocation round


class BigMRTAAllocator(BaseAllocator):

    def __init__(self, alpha: float = ALPHA, epsilon: float = EPSILON,
                 max_queue_size: int = MAX_QUEUE):
        self.alpha = alpha
        self.epsilon = epsilon
        self.max_queue_size = max_queue_size

    def name(self) -> str:
        return 'big_mrta'

    def _arrival_time(self, robot: RobotState, task: TaskState,
                      current_queue: list, task_map: dict,
                      current_time: float) -> float:
        endpoint = queue_endpoint(robot, task_map, current_queue)
        dist = math.hypot(task.position[0] - endpoint[0],
                          task.position[1] - endpoint[1])
        queue_delay = len(current_queue) * (8.0 + task.service_time)
        return current_time + queue_delay + dist / SPEED + task.service_time

    def _battery_margin(self, robot: RobotState, task: TaskState,
                        task_map: dict, current_queue: list) -> float:
        endpoint = queue_endpoint(robot, task_map, current_queue)
        dist = math.hypot(task.position[0] - endpoint[0],
                          task.position[1] - endpoint[1])
        energy_cost = 0.015 * dist  # drain per metre (calibrated to Phase 6)
        return robot.battery - energy_cost

    def _incentive(self, robot: RobotState, task: TaskState,
                   current_queue: list, task_map: dict,
                   current_time: float) -> float:
        if not robot.available or len(current_queue) >= self.max_queue_size:
            return 0.0
        arrival = self._arrival_time(robot, task, current_queue,
                                     task_map, current_time)
        if task.deadline > 0 and arrival > task.deadline:
            return 0.0
        margin = self._battery_margin(robot, task, task_map, current_queue)
        if margin <= self.epsilon:
            return 0.0
        priority_bonus = 1.0 + 0.1 * task.priority
        return (max(0.0, margin - self.epsilon)
                * math.exp(-arrival / self.alpha)
                * priority_bonus)

    def _greedy_assign(self, robots, remaining_tasks, queues, task_map, current_time):
        """Fallback when scipy is unavailable: greedy argmax per task."""
        assigned = set()
        for task in remaining_tasks:
            best_r, best_w = None, 0.0
            for r in robots:
                w = self._incentive(r, task, queues[r.robot_id], task_map, current_time)
                if w > best_w:
                    best_w = w
                    best_r = r.robot_id
            if best_r is not None:
                queues[best_r].append(task.task_id)
                assigned.add(task.task_id)
        return assigned

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
        assigned_global = {tid for q in queues.values() for tid in q}
        remaining = [t for t in tasks if t.task_id not in assigned_global]

        while remaining:
            if _HAS_SCIPY:
                W = np.zeros((len(robots), len(remaining)))
                for i, r in enumerate(robots):
                    for j, t in enumerate(remaining):
                        W[i, j] = self._incentive(
                            r, t, queues[r.robot_id], task_map, current_time)
                if W.max() <= 0.0:
                    break
                row_ind, col_ind = linear_sum_assignment(-W)
                newly_assigned = set()
                for ri, ti in zip(row_ind, col_ind):
                    if W[ri, ti] <= 0.0:
                        continue
                    r = robots[ri]
                    t = remaining[ti]
                    if len(queues[r.robot_id]) < self.max_queue_size:
                        queues[r.robot_id].append(t.task_id)
                        newly_assigned.add(t.task_id)
                if not newly_assigned:
                    break
                remaining = [t for t in remaining if t.task_id not in newly_assigned]
            else:
                newly = self._greedy_assign(robots, remaining, queues, task_map, current_time)
                if not newly:
                    break
                remaining = [t for t in remaining if t.task_id not in newly]

        ordered_queues: dict = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            ordered = cheapest_insertion(r.pose, q_tasks)
            ordered_queues[r.robot_id] = [t.task_id for t in ordered]

        # Communication: bid matrix size (robots × tasks × float32)
        comm = len(robots) * len(tasks) * 4
        return AllocationResult(
            queues=ordered_queues, latency_ms=0.0,
            communication_footprint_bytes=comm)
