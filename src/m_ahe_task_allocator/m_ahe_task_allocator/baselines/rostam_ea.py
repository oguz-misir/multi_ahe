"""rostam_ea — RoSTAM-EA: self-adaptive evolutionary MRTA (Arif & Haider, 2024).

Two-part chromosome: [task_permutation | robot_partition_counts]
Fitness: makespan + penalty*deadline_violations + workload_variance_weight
Online reformulation after failures / new task arrivals.
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

from .base_allocator import (
    AllocationResult, BaseAllocator, EcosystemContext,
    RobotState, TaskState, cheapest_insertion, measure,
)

SPEED = 0.26


@dataclass
class _Candidate:
    permutation: List[str]
    partitions: List[int]
    fitness: float = float('inf')


class RoSTAMEAAllocator(BaseAllocator):

    def __init__(self, population_size: int = 40, generations: int = 40,
                 elite_count: int = 2, diversity_rate: float = 0.20,
                 initial_penalty: float = 100.0,
                 mu: Tuple = (1.0, 0.5, 0.2, 0.3, 50.0, 10.0)):
        self.pop_size = population_size
        self.generations = generations
        self.elite = elite_count
        self.div_rate = diversity_rate
        self.penalty = initial_penalty
        self.mu = mu          # fitness weights
        self._last_pop: List[_Candidate] = []
        self._rng = random.Random()  # seeded per experiment

    def name(self) -> str:
        return 'rostam_ea'

    def seed(self, s: int) -> None:
        self._rng.seed(s)

    # ------------------------------------------------------------------
    # Chromosome helpers
    # ------------------------------------------------------------------

    def _random_partitions(self, n_tasks: int, n_robots: int) -> List[int]:
        counts = [0] * n_robots
        for _ in range(n_tasks):
            counts[self._rng.randrange(n_robots)] += 1
        return counts

    def _build(self, task_ids: List[str], n_robots: int) -> _Candidate:
        perm = task_ids[:]
        self._rng.shuffle(perm)
        return _Candidate(perm, self._random_partitions(len(perm), n_robots))

    def _decode(self, c: _Candidate, robot_ids: List[str]) -> Dict[str, List[str]]:
        q: Dict[str, List[str]] = {r: [] for r in robot_ids}
        idx = 0
        for r, cnt in zip(robot_ids, c.partitions):
            q[r] = c.permutation[idx: idx + cnt]
            idx += cnt
        return q

    # ------------------------------------------------------------------
    # Fitness
    # ------------------------------------------------------------------

    def _evaluate(self, c: _Candidate, robot_ids: List[str],
                  task_map: Dict[str, TaskState],
                  robot_map: Dict[str, RobotState],
                  current_time: float) -> float:
        mu1, mu2, mu3, mu4, mu5, mu6 = self.mu
        q = self._decode(c, robot_ids)
        tour_costs, completed, deadline_viol, delays = [], [], 0, []

        for rid, tids in q.items():
            robot = robot_map[rid]
            pos = robot.pose
            elapsed = current_time
            cost = 0.0
            for tid in tids:
                t = task_map.get(tid)
                if t is None:
                    continue
                d = math.hypot(t.position[0] - pos[0], t.position[1] - pos[1])
                cost += d
                elapsed += d / SPEED + t.service_time
                if t.deadline > 0 and elapsed > t.deadline:
                    deadline_viol += 1
                    delays.append(elapsed - t.deadline)
                pos = t.position
            tour_costs.append(cost)
            completed.append(len(tids))

        makespan = max(tour_costs) if tour_costs else 0.0
        avg_delay = sum(delays) / max(1, len(delays))
        dvr = deadline_viol / max(1, sum(len(v) for v in q.values()))
        wv = _variance(completed)
        fail_pen = sum(1 for r in robot_map.values() if r.failure_flag) * self.penalty
        return (mu1 * makespan + mu2 * avg_delay + mu3 * dvr * self.penalty
                + mu4 * wv + mu5 * fail_pen + mu6 * deadline_viol)

    # ------------------------------------------------------------------
    # Genetic operators
    # ------------------------------------------------------------------

    def _crossover(self, p1: _Candidate, p2: _Candidate) -> _Candidate:
        n = len(p1.permutation)
        if n < 2:
            return _Candidate(p1.permutation[:], p1.partitions[:])
        a, b = sorted(self._rng.sample(range(n), 2))
        child = [None] * n
        child[a:b] = p1.permutation[a:b]
        fill = [x for x in p2.permutation if x not in child]
        ptr = 0
        for i in range(n):
            if child[i] is None:
                child[i] = fill[ptr]; ptr += 1
        parts = (p1.partitions[:] if self._rng.random() < 0.5
                 else p2.partitions[:])
        return _Candidate(child, parts)

    def _mutate(self, c: _Candidate) -> None:
        n = len(c.permutation)
        if n >= 2 and self._rng.random() < 0.4:
            i, j = self._rng.sample(range(n), 2)
            c.permutation[i], c.permutation[j] = c.permutation[j], c.permutation[i]
        if n >= 4 and self._rng.random() < 0.2:
            i, j = sorted(self._rng.sample(range(n), 2))
            c.permutation[i:j] = c.permutation[i:j][::-1]
        if len(c.partitions) >= 2 and self._rng.random() < 0.3:
            src = self._rng.randrange(len(c.partitions))
            dst = self._rng.randrange(len(c.partitions))
            if src != dst and c.partitions[src] > 0:
                c.partitions[src] -= 1; c.partitions[dst] += 1

    def _update_penalty(self, feasible_flags: List[bool]) -> None:
        if len(feasible_flags) < 10:
            return
        last = feasible_flags[-10:]
        if all(not f for f in last):
            self.penalty = min(self.penalty * 1.15, 1e4)
        elif all(f for f in last):
            self.penalty = max(self.penalty * 0.85, 1.0)

    def _reformulate(self, task_ids: List[str], n_robots: int) -> List[_Candidate]:
        active = set(task_ids)
        repaired = []
        for c in self._last_pop:
            perm = [t for t in c.permutation if t in active]
            missing = [t for t in task_ids if t not in perm]
            self._rng.shuffle(missing)
            perm.extend(missing)
            parts = self._random_partitions(len(perm), n_robots)
            repaired.append(_Candidate(perm, parts))
        return repaired[:self.pop_size]

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------

    @measure
    def allocate(
        self,
        robots: list,
        tasks: list,
        current_time: float,
        context: EcosystemContext = None,
    ) -> AllocationResult:
        task_map = {t.task_id: t for t in tasks}
        robot_map = {r.robot_id: r for r in robots}
        robot_ids = [r.robot_id for r in robots]
        task_ids = [t.task_id for t in tasks]

        pre_assigned = {tid for r in robots for tid in r.queue}
        unassigned_ids = [t for t in task_ids if t not in pre_assigned]

        if not unassigned_ids:
            return AllocationResult(
                queues={r.robot_id: list(r.queue) for r in robots},
                latency_ms=0.0, strategy=self.name())

        # Population initialisation (use reformulation if prior pop exists)
        if self._last_pop:
            pop = self._reformulate(unassigned_ids, len(robots))
        else:
            pop = []
        while len(pop) < self.pop_size:
            pop.append(self._build(unassigned_ids, len(robots)))

        feasible_hist: List[bool] = []
        for _ in range(self.generations):
            for c in pop:
                c.fitness = self._evaluate(
                    c, robot_ids, task_map, robot_map, current_time)
            pop.sort(key=lambda c: c.fitness)
            feasible_hist.append(pop[0].fitness < self.penalty)
            self._update_penalty(feasible_hist)

            next_pop = pop[:self.elite]
            while len(next_pop) < self.pop_size:
                p1, p2 = self._rng.sample(
                    pop[:max(5, self.pop_size // 2)], 2)
                child = self._crossover(p1, p2)
                self._mutate(child)
                next_pop.append(child)

            inject = int(self.div_rate * self.pop_size)
            for _ in range(inject):
                idx = self._rng.randrange(self.elite, self.pop_size)
                next_pop[idx] = self._build(unassigned_ids, len(robots))
            pop = next_pop

        pop.sort(key=lambda c: c.fitness)
        self._last_pop = pop
        best_queues = self._decode(pop[0], robot_ids)

        # Merge with already-running tasks
        ordered_queues: dict = {}
        for r in robots:
            existing = list(r.queue)
            new_tids = best_queues.get(r.robot_id, [])
            all_tasks = [task_map[t] for t in existing + new_tids if t in task_map]
            ordered = cheapest_insertion(r.pose, all_tasks)
            ordered_queues[r.robot_id] = [t.task_id for t in ordered]

        # Communication: full chromosome broadcast per generation (approx)
        comm = self.generations * len(robots) * len(unassigned_ids) * 8
        return AllocationResult(
            queues=ordered_queues, latency_ms=0.0,
            communication_footprint_bytes=comm)


def _variance(vals: list) -> float:
    if not vals:
        return 0.0
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals) / len(vals)
