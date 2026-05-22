"""greedy_nearest — Nearest-target greedy allocator (classical baseline)."""

from .base_allocator import (
    AllocationResult, BaseAllocator, EcosystemContext,
    RobotState, TaskState, cheapest_insertion, measure, queue_endpoint,
)

BATT_CRITICAL = 2
AVAIL_UNAVAILABLE = 2


class GreedyNearestAllocator(BaseAllocator):
    """For each unassigned task (priority desc), assign to the nearest available robot."""

    def name(self) -> str:
        return 'greedy_nearest'

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

        unassigned = sorted(
            [t for t in tasks if t.task_id not in assigned],
            key=lambda t: (-t.priority, t.deadline),
        )

        for task in unassigned:
            best_robot = None
            best_dist = float('inf')
            for r in robots:
                if r.battery_state == BATT_CRITICAL or not r.available:
                    continue
                endpoint = queue_endpoint(r, task_map, queues[r.robot_id])
                d = abs(endpoint[0] - task.position[0]) + abs(endpoint[1] - task.position[1])
                if d < best_dist:
                    best_dist = d
                    best_robot = r.robot_id
            if best_robot is not None:
                queues[best_robot].append(task.task_id)
                assigned.add(task.task_id)

        # Order each robot's queue by cheapest insertion
        ordered_queues: dict = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            ordered = cheapest_insertion(r.pose, q_tasks)
            ordered_queues[r.robot_id] = [t.task_id for t in ordered]

        return AllocationResult(queues=ordered_queues, latency_ms=0.0)
