"""consensus_dbta — Consensus-Based DBTA2 (Mahato et al., 2023).

Each robot generates top-k bids; simulated consensus selects max bid per task.
Priority-1 then Priority-2 allocation rule avoids per-robot conflicts.
Communication footprint = robot_count × top_k × bid_size_bytes.
"""

import math
from dataclasses import dataclass
from typing import Dict, List

from .base_allocator import (
    AllocationResult, BaseAllocator, EcosystemContext,
    RobotState, TaskState, cheapest_insertion, measure, queue_endpoint,
)

SPEED = 0.26
MAX_QUEUE = 5
BID_SIZE_BYTES = 16   # (robot_id hash, task_id hash, value f32, rank u8 + padding)


@dataclass
class _Bid:
    robot_id: str
    task_id: str
    value: float
    priority_rank: int   # 1 = top bid, 2 = second bid


class ConsensusDBTAAllocator(BaseAllocator):

    def __init__(self, top_k: int = 2, max_queue_size: int = MAX_QUEUE):
        self.top_k = top_k
        self.max_queue_size = max_queue_size

    def name(self) -> str:
        return 'consensus_dbta'

    def _bid_value(self, robot: RobotState, task: TaskState,
                   current_queue: list, task_map: dict,
                   current_time: float) -> float:
        if not robot.available or len(current_queue) >= self.max_queue_size:
            return float('-inf')

        endpoint = queue_endpoint(robot, task_map, current_queue)
        dist = math.hypot(task.position[0] - endpoint[0],
                          task.position[1] - endpoint[1])
        queue_delay = len(current_queue) * (8.0 + task.service_time)
        arrival = current_time + queue_delay + dist / SPEED

        priority_score = float(task.priority)
        deadline_score = 1.0 / (1.0 + max(0.0, arrival - task.deadline))
        battery_score = robot.battery
        load_penalty = len(current_queue) / max(1, self.max_queue_size)
        failure_penalty = 1.0 if robot.failure_flag else 0.0

        return (2.0 * priority_score
                + 3.0 * deadline_score
                + 1.0 * battery_score
                - 0.5 * dist / 28.0
                - 2.0 * load_penalty
                - 3.0 * failure_penalty)

    def _generate_top_bids(self, robots: list, tasks: list,
                           queues: dict, task_map: dict,
                           current_time: float) -> List[_Bid]:
        all_bids: List[_Bid] = []
        for r in robots:
            robot_bids = []
            for t in tasks:
                v = self._bid_value(r, t, queues[r.robot_id], task_map, current_time)
                if v != float('-inf'):
                    robot_bids.append((t.task_id, v))
            robot_bids.sort(key=lambda x: x[1], reverse=True)
            for rank, (tid, val) in enumerate(robot_bids[:self.top_k], start=1):
                all_bids.append(_Bid(r.robot_id, tid, val, rank))
        return all_bids

    def _consensus_max(self, bids: List[_Bid]) -> Dict[str, _Bid]:
        winners: Dict[str, _Bid] = {}
        for b in bids:
            if b.task_id not in winners or b.value > winners[b.task_id].value:
                winners[b.task_id] = b
        return winners

    def _round_allocate(self, winners: Dict[str, _Bid]) -> Dict[str, List[str]]:
        allocation: Dict[str, List[str]] = {}
        used_robots: set = set()
        used_tasks: set = set()

        for rank in (1, 2):
            for tid, bid in sorted(winners.items(),
                                   key=lambda x: (-x[1].priority_rank == rank,
                                                  x[1].value),
                                   reverse=True):
                if bid.priority_rank != rank:
                    continue
                if bid.robot_id in used_robots or tid in used_tasks:
                    continue
                allocation.setdefault(bid.robot_id, []).append(tid)
                used_robots.add(bid.robot_id)
                used_tasks.add(tid)
        return allocation

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
        remaining = [t for t in tasks if t.task_id not in assigned]

        total_bids_sent = 0

        while remaining:
            bids = self._generate_top_bids(
                robots, remaining, queues, task_map, current_time)
            total_bids_sent += len(bids)
            if not bids:
                break
            winners = self._consensus_max(bids)
            round_alloc = self._round_allocate(winners)
            if not round_alloc:
                break

            newly_assigned: set = set()
            for rid, tids in round_alloc.items():
                for tid in tids:
                    if len(queues[rid]) < self.max_queue_size:
                        queues[rid].append(tid)
                        newly_assigned.add(tid)
            if not newly_assigned:
                break
            remaining = [t for t in remaining if t.task_id not in newly_assigned]

        ordered_queues: dict = {}
        for r in robots:
            q_tasks = [task_map[tid] for tid in queues[r.robot_id] if tid in task_map]
            ordered = cheapest_insertion(r.pose, q_tasks)
            ordered_queues[r.robot_id] = [t.task_id for t in ordered]

        comm = total_bids_sent * BID_SIZE_BYTES
        return AllocationResult(
            queues=ordered_queues, latency_ms=0.0,
            communication_footprint_bytes=comm)
