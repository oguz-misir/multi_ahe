"""
Common interface and data structures for all AHE-MRTA baseline allocators.

All allocators receive RobotState/TaskState (simple dataclasses adapted from
ROS messages) and return an AllocationResult. Keeping allocators ROS-free lets
the experiment runner swap strategies with a single line.

Fairness guarantees enforced at this layer:
  - All methods see the same robots, tasks, and current_time.
  - Nav2 path cost (Euclidean proxy) is computed identically in all methods.
  - Communication footprint is estimated per-call and logged.
"""

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Shared data structures
# ---------------------------------------------------------------------------

@dataclass
class RobotState:
    robot_id: str
    pose: tuple               # (x, y)
    battery: float            # 0.0–1.0  (simulated)
    available: bool           # availability_state != UNAVAILABLE
    current_task_id: str      # '' if idle
    queue: list               # list[str] of currently assigned task_ids
    failure_risk: float = 0.0
    navigation_state: int = 0   # 0=idle, 1=navigating, 2=stuck, 3=failed, 4=reached
    failure_flag: bool = False
    battery_state: int = 0      # 0=normal, 1=low, 2=critical
    # Exact execution feedback. Inferring completion from a task disappearing
    # from the open pool is unsafe because retry backoff has the same symptom.
    completed_tasks: int = 0
    failed_tasks: int = 0
    travel_distance: float = 0.0
    # Nav2 feedback: remaining distance on the currently followed global path.
    # Zero means unavailable/not navigating.
    navigation_effort: float = 0.0


@dataclass
class TaskState:
    task_id: str
    position: tuple           # (x, y)
    priority: int             # 1=low, 2=normal, 3=high
    activation_time: float    # sim seconds when task became active
    deadline: float           # absolute deadline in sim seconds
    service_time: float       # seconds to "service" the task at the waypoint
    active: bool = True
    completed: bool = False
    # Execution feedback keyed by robot_id.  This represents pair-specific
    # reachability evidence; it is not a global robot competence score.
    failure_by_robot: dict = field(default_factory=dict)


@dataclass
class EcosystemContext:
    """Passed only to AHE-based allocators; None for classical baselines."""
    dominance: list             # list[float], len=K
    context_vector: list        # list[float], len=4
    allocation_weights: list    # list[float], len=7  W(t) = softmax(M·D)
    cooperation_matrix: list    # list[list[float]] 5×5 A
    suppression_matrix: list    # list[list[float]] 5×5 S
    heuristic_names: list       # list[str], len=K


@dataclass
class AllocationResult:
    queues: dict              # dict[robot_id, list[task_id]] — ordered queue per robot
    latency_ms: float
    communication_footprint_bytes: int = 0
    strategy: str = ''


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def euclid(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(bx - ax, by - ay)


def robot_task_distance(robot: RobotState, task: TaskState) -> float:
    return euclid(robot.pose[0], robot.pose[1],
                  task.position[0], task.position[1])


def jain_index(values) -> float:
    """Return Jain's fairness index for non-negative resource shares."""
    xs = [max(0.0, float(v)) for v in values]
    total = sum(xs)
    if not xs or total <= 0.0:
        return 0.0
    sum_sq = sum(v * v for v in xs)
    return (total * total) / (len(xs) * sum_sq) if sum_sq > 0.0 else 0.0


def queue_endpoint(
    robot: RobotState,
    task_map: dict,  # dict[task_id, TaskState]
    pending_queue: list,  # list[str] in order
) -> tuple:
    """Last (x, y) in robot's planned route (current pose if queue empty)."""
    if pending_queue:
        last = task_map.get(pending_queue[-1])
        if last:
            return last.position
    return robot.pose


def cheapest_insertion(
    start: tuple,
    tasks: list,  # list[TaskState]
    distance_fn=None,
) -> list:
    """Cheapest-insertion ordering returning a list of TaskState."""
    if not tasks:
        return []
    if distance_fn is None:
        distance_fn = lambda a, b: euclid(a[0], a[1], b[0], b[1])
    route_pts = [start]
    route_tasks = []
    remaining = list(tasks)

    nearest = min(remaining, key=lambda t: distance_fn(start, t.position))
    remaining.remove(nearest)
    route_pts.append(nearest.position)
    route_tasks.append(nearest)

    while remaining:
        best_task = None
        best_pos = 0
        best_inc = float('inf')
        for task in remaining:
            tx, ty = task.position
            for pos in range(1, len(route_pts) + 1):
                prev = route_pts[pos - 1]
                nxt = route_pts[pos] if pos < len(route_pts) else None
                if nxt is None:
                    inc = distance_fn(prev, (tx, ty))
                else:
                    old = distance_fn(prev, nxt)
                    inc = (distance_fn(prev, (tx, ty))
                           + distance_fn((tx, ty), nxt) - old)
                if inc < best_inc:
                    best_inc = inc
                    best_task = task
                    best_pos = pos
        remaining.remove(best_task)
        route_pts.insert(best_pos, best_task.position)
        route_tasks.insert(best_pos - 1, best_task)

    return route_tasks


def measure(fn):
    """Decorator that wraps allocate() and sets result.latency_ms."""
    def wrapper(self, *args, **kwargs) -> AllocationResult:
        t0 = time.monotonic()
        result = fn(self, *args, **kwargs)
        result.latency_ms = (time.monotonic() - t0) * 1000.0
        result.strategy = self.name()
        return result
    return wrapper


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseAllocator(ABC):
    """All Phase 9 allocators implement this interface."""

    @abstractmethod
    def allocate(
        self,
        robots: list,          # list[RobotState]
        tasks: list,           # list[TaskState] — active, not completed
        current_time: float,
        context: Optional[EcosystemContext] = None,
    ) -> AllocationResult:
        ...

    @abstractmethod
    def name(self) -> str:
        ...
