"""deadline_aware — Earliest-Deadline-First allocator (classical baseline)."""

from .base_allocator import (
    AllocationResult, BaseAllocator, EcosystemContext,
    RobotState, TaskState, cheapest_insertion, measure, queue_endpoint,
)

BATT_CRITICAL = 2


class DeadlineAwareAllocator(BaseAllocator):
    """Sort tasks by deadline (EDF), assign each to the robot with minimum travel time."""

    def name(self) -> str:
        return 'deadline_aware'

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

        # EDF ordering: earliest deadline first; break ties by priority desc
        unassigned = sorted(
            [t for t in tasks if t.task_id not in assigned],
            key=lambda t: (t.deadline, -t.priority),
        )

        SPEED = 0.26  # m/s TurtleBot3 Waffle Pi nominal

        for task in unassigned:
            best_robot = None
            best_score = float('inf')
            for r in robots:
                if r.battery_state == BATT_CRITICAL or not r.available:
                    continue
                endpoint = queue_endpoint(r, task_map, queues[r.robot_id])
                dist = abs(endpoint[0] - task.position[0]) + abs(endpoint[1] - task.position[1])
                travel_time = dist / SPEED
                # Estimate arrival: current_time + queue delay + travel
                queue_delay = len(queues[r.robot_id]) * 8.0
                arrival = current_time + queue_delay + travel_time
                # Prefer tasks we can finish before deadline; score = arrival
                score = arrival
                if score < best_score:
                    best_score = score
                    best_robot = r.robot_id
            if best_robot is not None:
                queues[best_robot].append(task.task_id)
                assigned.add(task.task_id)

        ordered_queues: dict = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            # Keep EDF order rather than cheapest-insertion for this baseline
            q_tasks.sort(key=lambda t: (t.deadline, -t.priority))
            ordered_queues[r.robot_id] = [t.task_id for t in q_tasks]

        return AllocationResult(queues=ordered_queues, latency_ms=0.0)
