"""auction_based — Sequential Single-Item (SSI) auction baseline."""

import math
from .base_allocator import (
    AllocationResult, BaseAllocator, EcosystemContext,
    RobotState, TaskState, cheapest_insertion, measure, queue_endpoint,
)

BATT_CRITICAL = 2
SPEED = 0.26  # m/s


class AuctionBasedAllocator(BaseAllocator):
    """SSI auction: for each task (priority-desc) every eligible robot bids;
    highest bidder wins. Bid = marginal cost reduction from adding the task."""

    def name(self) -> str:
        return 'auction_based'

    def _bid(self, robot: RobotState, task: TaskState,
             task_map: dict, current_queue: list, current_time: float) -> float:
        """Higher bid = stronger preference. Returns -inf if ineligible."""
        if robot.battery_state == BATT_CRITICAL or not robot.available:
            return float('-inf')

        endpoint = queue_endpoint(robot, task_map, current_queue)
        dist = math.hypot(
            task.position[0] - endpoint[0],
            task.position[1] - endpoint[1],
        )
        queue_delay = len(current_queue) * 8.0
        arrival = current_time + queue_delay + dist / SPEED

        # Feasibility: skip if we can't make the deadline
        if task.deadline > 0 and arrival > task.deadline:
            return float('-inf')

        # Bid components (higher = better for this robot-task pair)
        proximity_score = 1.0 / (1.0 + dist)
        deadline_score = max(0.0, task.deadline - arrival) / max(task.deadline, 1.0)
        priority_score = task.priority / 3.0
        load_penalty = len(current_queue) * 0.1
        batt_penalty = robot.battery_state * 0.2

        return proximity_score + deadline_score + priority_score - load_penalty - batt_penalty

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
        robot_map = {r.robot_id: r for r in robots}
        assigned = {tid for q in queues.values() for tid in q}

        # Run SSI rounds: highest-priority task first
        unassigned = sorted(
            [t for t in tasks if t.task_id not in assigned],
            key=lambda t: (-t.priority, t.deadline),
        )

        for task in unassigned:
            best_robot = None
            best_bid = float('-inf')
            for r in robots:
                bid = self._bid(r, task, task_map, queues[r.robot_id], current_time)
                if bid > best_bid:
                    best_bid = bid
                    best_robot = r.robot_id
            if best_robot is not None:
                queues[best_robot].append(task.task_id)
                assigned.add(task.task_id)

        ordered_queues: dict = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            ordered = cheapest_insertion(r.pose, q_tasks)
            ordered_queues[r.robot_id] = [t.task_id for t in ordered]

        # Communication: one bid message per robot per task (bid_size=32 bytes)
        comm = len(robots) * len(unassigned) * 32

        return AllocationResult(
            queues=ordered_queues,
            latency_ms=0.0,
            communication_footprint_bytes=comm,
        )
