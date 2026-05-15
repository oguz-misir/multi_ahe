"""
Phase 6 — Task Manager Node

Publishes /tasks/global_pool (TaskPool) at 1 Hz.
Activates tasks in three batches (immediate / 30 s / 60 s).
Subscribes to /robot_i/task_feedback (AllocationEvent) to mark tasks done/failed.

Success criterion (Phase 6 gate):
  3 robots, 15 tasks — simple task execution runs; task_events.csv produced.
"""

import random

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from m_ahe_mrta_msgs.msg import AllocationEvent, TaskInfo, TaskPool


# Pre-defined inspection waypoints (x, y) within the 20 x 20 m world.
# Arranged as five rows of four columns, avoiding the robot spawn area (0, 0).
_INSPECTION_GRID = [
    (-6.0, 7.0), (-2.0, 7.0), (2.0, 7.0), (6.0, 7.0),
    (-6.0, 4.0), (-2.0, 4.0), (2.0, 4.0), (6.0, 4.0),
    (-6.0, 1.0), (6.0, 1.0),
    (-6.0, -3.0), (-2.0, -3.0), (2.0, -3.0), (6.0, -3.0),
    (-6.0, -6.0), (-2.0, -6.0), (2.0, -6.0), (6.0, -6.0),
    (-4.0, -1.0), (4.0, -1.0),
]

_BATCH_DELAYS_SEC = [0.0, 30.0, 60.0]


class TaskManagerNode(Node):
    def __init__(self) -> None:
        super().__init__('task_manager_node')

        self.declare_parameter('robot_count', 3)
        self.declare_parameter('task_count', 15)
        self.declare_parameter('seed', 1)

        self._robot_count: int = self.get_parameter('robot_count').value
        self._task_count: int = self.get_parameter('task_count').value
        self._seed: int = self.get_parameter('seed').value

        self._rng = random.Random(self._seed)

        self._tasks: list[TaskInfo] = self._generate_tasks()
        # task_id -> 'pending' | 'active' | 'completed' | 'failed'
        self._task_state: dict[str, str] = {
            t.task_id: 'pending' for t in self._tasks
        }
        self._pool_version: int = 0

        # Publisher
        self._pool_pub = self.create_publisher(TaskPool, '/tasks/global_pool', 10)

        # Feedback subscribers — one per robot
        for i in range(1, self._robot_count + 1):
            self.create_subscription(
                AllocationEvent,
                f'/robot_{i}/task_feedback',
                self._task_feedback_cb,
                10,
            )

        # Publish at 1 Hz
        self.create_timer(1.0, self._publish_pool)

        # Activate batches
        tasks_per_batch = max(1, self._task_count // len(_BATCH_DELAYS_SEC))
        self._batches: list[list[str]] = []
        ids = [t.task_id for t in self._tasks]
        for i, delay in enumerate(_BATCH_DELAYS_SEC):
            batch = ids[i * tasks_per_batch: (i + 1) * tasks_per_batch]
            if not batch:
                break
            if delay == 0.0:
                self._activate_batch(batch)
            else:
                self.create_timer(delay, lambda b=batch: self._activate_batch(b))
            self._batches.append(batch)

        self.get_logger().info(
            f'TaskManager ready: {self._task_count} tasks, '
            f'robot_count={self._robot_count}, seed={self._seed}'
        )

    # ------------------------------------------------------------------
    # Task generation
    # ------------------------------------------------------------------

    def _generate_tasks(self) -> list[TaskInfo]:
        grid = list(_INSPECTION_GRID)
        self._rng.shuffle(grid)
        # Pad with random points if task_count exceeds grid size
        while len(grid) < self._task_count:
            grid.append((
                self._rng.uniform(-8.0, 8.0),
                self._rng.uniform(-8.0, 8.0),
            ))

        tasks: list[TaskInfo] = []
        for idx in range(self._task_count):
            x, y = grid[idx]
            task = TaskInfo()
            task.task_id = f'task_{idx + 1:03d}'

            pose = PoseStamped()
            pose.header.frame_id = 'map'
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = float(x)
            pose.pose.position.y = float(y)
            pose.pose.position.z = 0.0
            pose.pose.orientation.w = 1.0
            task.target_pose = pose

            task.priority_level = self._rng.randint(1, 3)
            task.service_time = float(self._rng.uniform(2.0, 8.0))
            task.deadline = float(self._rng.uniform(90.0, 300.0))
            task.active = False
            task.completed = False
            tasks.append(task)

        return tasks

    # ------------------------------------------------------------------
    # Batch activation
    # ------------------------------------------------------------------

    def _activate_batch(self, task_ids: list[str]) -> None:
        for task in self._tasks:
            if task.task_id in task_ids and self._task_state[task.task_id] == 'pending':
                task.active = True
                self._task_state[task.task_id] = 'active'
                self.get_logger().info(f'Activated {task.task_id}')
        self._pool_version += 1

    # ------------------------------------------------------------------
    # Feedback subscriber
    # ------------------------------------------------------------------

    def _task_feedback_cb(self, msg: AllocationEvent) -> None:
        tid = msg.task_id
        if tid not in self._task_state:
            return

        if msg.event_type == 'task_completed':
            self._task_state[tid] = 'completed'
            for task in self._tasks:
                if task.task_id == tid:
                    task.completed = True
                    task.active = False
                    break
            self.get_logger().info(f'{tid} completed by {msg.robot_id}')

        elif msg.event_type == 'task_failed':
            self._task_state[tid] = 'failed'
            for task in self._tasks:
                if task.task_id == tid:
                    task.active = False
                    break
            self.get_logger().warning(f'{tid} failed (robot={msg.robot_id})')

    # ------------------------------------------------------------------
    # Publisher
    # ------------------------------------------------------------------

    def _publish_pool(self) -> None:
        msg = TaskPool()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.tasks = self._tasks
        msg.pool_version = self._pool_version
        self._pool_pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TaskManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
