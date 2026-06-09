"""
Phase 6 — Robot Interface Node

One instance per robot (launched with robot_id:=robot_N).

State machine:
  IDLE ──send_goal──► NAVIGATING ──result──► REACHED / FAILED ──reset──► IDLE

Publishes:
  /robot_N/status_summary          (RobotStatusSummary, 2 Hz)
  /robot_N/local_execution_feedback (LocalExecutionFeedback, 2 Hz)
  /robot_N/task_feedback            (AllocationEvent, on task done/failed)

Subscribes:
  /robot_N/odom                    (nav_msgs/Odometry)
  /robot_N/optimized_task_queue    (OptimizedTaskQueue)

Action client:
  /robot_N/navigate_to_pose        (nav2_msgs/action/NavigateToPose)
"""

from enum import IntEnum

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.node import Node

from m_ahe_mrta_msgs.msg import (
    AllocationEvent,
    LocalExecutionFeedback,
    OptimizedTaskQueue,
    RobotStatusSummary,
    TaskWaypoint,
)


class NavState(IntEnum):
    IDLE = 0
    NAVIGATING = 1
    STUCK = 2
    FAILED = 3
    REACHED = 4


class AvailState(IntEnum):
    AVAILABLE = 0
    BUSY = 1
    UNAVAILABLE = 2


class BattState(IntEnum):
    NORMAL = 0
    LOW = 1
    CRITICAL = 2


class RobotInterfaceNode(Node):
    def __init__(self) -> None:
        super().__init__('robot_interface_node')

        self.declare_parameter('robot_id', 'robot_1')
        # B1 (congestion-aware recovery): stuck detection thresholds.
        # If the robot makes < stuck_min_move_m net displacement for
        # stuck_no_progress_sec while NAVIGATING, it is declared STUCK; the
        # goal is cancelled and the task re-enters allocation early. STUCK is
        # reported for stuck_report_hold_sec so the ecosystem failure_rate
        # rises and the recovery paradigm (orphan_first) engages.
        self.declare_parameter('stuck_no_progress_sec', 12.0)
        self.declare_parameter('stuck_min_move_m', 0.15)
        self.declare_parameter('stuck_report_hold_sec', 6.0)

        self._robot_id: str = self.get_parameter('robot_id').value
        self._stuck_no_progress_sec: float = float(
            self.get_parameter('stuck_no_progress_sec').value)
        self._stuck_min_move_m: float = float(
            self.get_parameter('stuck_min_move_m').value)
        self._stuck_report_hold_sec: float = float(
            self.get_parameter('stuck_report_hold_sec').value)

        # Navigation state
        self._nav_state = NavState.IDLE
        self._avail_state = AvailState.AVAILABLE
        self._battery_state = BattState.NORMAL
        self._battery_level: float = 1.0
        self._current_pose = PoseStamped()
        self._current_task_id: str = ''
        self._last_completed_task_id: str = ''
        self._failure_flag: bool = False
        self._task_progress: float = 0.0
        self._distance_remaining: float = 0.0

        # B1: Nav2 goal handle (so cancel actually cancels) + stuck tracking
        self._goal_handle = None
        self._active: bool = False              # guards single finalize per task
        self._last_move_time: float = 0.0
        self._last_move_xy: tuple[float, float] = (0.0, 0.0)
        self._stuck_report_until: float = 0.0   # report STUCK until this time
        # Local execution feedback signals (set by stuck detector)
        self._congestion_indicator: int = 0
        self._goal_reachability: int = 0
        self._request_replan: bool = False

        # Task queue
        self._waypoint_queue: list[TaskWaypoint] = []
        self._queue_version: int = 0
        self._dispatching: bool = False

        ns = self._robot_id

        # Subscribers
        self.create_subscription(Odometry, f'/{ns}/odom', self._odom_cb, 10)
        self.create_subscription(
            OptimizedTaskQueue,
            f'/{ns}/optimized_task_queue',
            self._queue_cb,
            10,
        )

        # Publishers
        self._status_pub = self.create_publisher(
            RobotStatusSummary, f'/{ns}/status_summary', 10
        )
        self._feedback_pub = self.create_publisher(
            LocalExecutionFeedback, f'/{ns}/local_execution_feedback', 10
        )
        self._task_feedback_pub = self.create_publisher(
            AllocationEvent, f'/{ns}/task_feedback', 10
        )

        # Nav2 action client
        self._nav_client = ActionClient(self, NavigateToPose, f'/{ns}/navigate_to_pose')

        # Timers
        self.create_timer(0.5, self._publish_status)
        self.create_timer(0.5, self._publish_feedback)
        self.create_timer(0.2, self._maybe_dispatch)
        self.create_timer(5.0, self._drain_battery)
        self.create_timer(1.0, self._check_stuck)   # B1: congestion stuck detector

        self.get_logger().info(f'{self._robot_id} interface node started')

    # ------------------------------------------------------------------
    # Subscribers
    # ------------------------------------------------------------------

    def _odom_cb(self, msg: Odometry) -> None:
        self._current_pose.header = msg.header
        self._current_pose.pose = msg.pose.pose

    def _queue_cb(self, msg: OptimizedTaskQueue) -> None:
        if msg.robot_id and msg.robot_id != self._robot_id:
            return  # not for us
        if msg.queue_version < self._queue_version:
            return  # stale

        self._queue_version = msg.queue_version
        self._waypoint_queue = list(msg.waypoints)

        self.get_logger().info(
            f'{self._robot_id}: received queue v{msg.queue_version} '
            f'({len(self._waypoint_queue)} waypoints)'
        )

        if msg.replan_required and self._nav_state == NavState.NAVIGATING:
            self._cancel_current_goal()

    # ------------------------------------------------------------------
    # Task dispatch
    # ------------------------------------------------------------------

    def _maybe_dispatch(self) -> None:
        if self._dispatching:
            return
        if self._nav_state != NavState.IDLE:
            return
        if not self._waypoint_queue:
            return
        if not self._nav_client.server_is_ready():
            return

        self._dispatching = True
        waypoint = self._waypoint_queue.pop(0)
        self._send_goal(waypoint)

    def _send_goal(self, waypoint: TaskWaypoint) -> None:
        self._current_task_id = waypoint.task_id
        self._task_progress = 0.0
        self._distance_remaining = 0.0

        goal_pose = PoseStamped()
        goal_pose.header.frame_id = f'{self._robot_id}/map'
        goal_pose.header.stamp = self.get_clock().now().to_msg()
        goal_pose.pose = waypoint.target_pose.pose

        goal = NavigateToPose.Goal()
        goal.pose = goal_pose

        self._nav_state = NavState.NAVIGATING
        self._avail_state = AvailState.BUSY
        self._failure_flag = False

        # B1: arm stuck tracking for this task
        self._active = True
        self._goal_handle = None
        self._last_move_time = self._now_sec()
        self._last_move_xy = self._get_xy()
        self._congestion_indicator = 0
        self._goal_reachability = 0

        self.get_logger().info(
            f'{self._robot_id}: sending {waypoint.task_id} → '
            f'({goal_pose.pose.position.x:.1f}, {goal_pose.pose.position.y:.1f})'
        )

        future = self._nav_client.send_goal_async(
            goal, feedback_callback=self._nav_feedback_cb
        )
        future.add_done_callback(self._goal_response_cb)

    def _goal_response_cb(self, future) -> None:
        handle = future.result()
        if not handle.accepted:
            self.get_logger().warning(
                f'{self._robot_id}: goal rejected for {self._current_task_id}'
            )
            self._on_task_done(success=False)
            return

        self._goal_handle = handle      # B1: store so we can actually cancel
        result_future = handle.get_result_async()
        result_future.add_done_callback(self._result_cb)

    def _nav_feedback_cb(self, feedback_msg) -> None:
        fb = feedback_msg.feedback
        if hasattr(fb, 'distance_remaining') and fb.distance_remaining >= 0.0:
            self._distance_remaining = fb.distance_remaining
            # Rough progress: assume 10 m max distance
            self._task_progress = max(
                self._task_progress,
                min(0.99, 1.0 - fb.distance_remaining / 10.0),
            )

    def _result_cb(self, future) -> None:
        result = future.result()
        success = result.status == GoalStatus.STATUS_SUCCEEDED
        if success:
            self.get_logger().info(
                f'{self._robot_id}: reached {self._current_task_id}'
            )
        else:
            self.get_logger().warning(
                f'{self._robot_id}: failed {self._current_task_id} (status={result.status})'
            )
        self._on_task_done(success=success)

    def _on_task_done(self, *, success: bool) -> None:
        # B1: finalize once per task (a stuck-cancel and the subsequent
        # CANCELED result must not both fire task_failed).
        if not self._active:
            return
        self._active = False
        self._goal_handle = None

        task_id = self._current_task_id
        event_type = 'task_completed' if success else 'task_failed'

        self._task_progress = 1.0 if success else self._task_progress
        self._last_completed_task_id = task_id if success else ''
        self._nav_state = NavState.REACHED if success else NavState.FAILED
        self._failure_flag = not success

        msg = AllocationEvent()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.event_type = event_type
        msg.robot_id = self._robot_id
        msg.task_id = task_id
        msg.severity = 0 if success else 1
        msg.trigger_replan = not success
        self._task_feedback_pub.publish(msg)

        # Reset for next task
        self._current_task_id = ''
        self._task_progress = 0.0
        self._nav_state = NavState.IDLE
        self._avail_state = AvailState.AVAILABLE
        self._failure_flag = False
        self._dispatching = False

    def _cancel_current_goal(self) -> None:
        self.get_logger().info(f'{self._robot_id}: cancelling current goal for replan')
        # B1: actually cancel the Nav2 goal so the robot stops chasing the old
        # target. _active=False so the resulting CANCELED callback is ignored.
        self._active = False
        if self._goal_handle is not None:
            try:
                self._goal_handle.cancel_goal_async()
            except Exception:  # noqa: BLE001 - best-effort cancel
                pass
            self._goal_handle = None
        self._nav_state = NavState.IDLE
        self._avail_state = AvailState.AVAILABLE
        self._dispatching = False

    # ------------------------------------------------------------------
    # B1 — Stuck detection (congestion-aware recovery)
    # ------------------------------------------------------------------

    def _now_sec(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _get_xy(self) -> tuple[float, float]:
        p = self._current_pose.pose.position
        return (p.x, p.y)

    def _check_stuck(self) -> None:
        if self._nav_state != NavState.NAVIGATING or not self._active:
            return
        x, y = self._get_xy()
        lx, ly = self._last_move_xy
        moved = ((x - lx) ** 2 + (y - ly) ** 2) ** 0.5
        if moved >= self._stuck_min_move_m:
            self._last_move_xy = (x, y)
            self._last_move_time = self._now_sec()
            return
        if self._now_sec() - self._last_move_time >= self._stuck_no_progress_sec:
            self._handle_stuck()

    def _handle_stuck(self) -> None:
        self.get_logger().warning(
            f'{self._robot_id}: STUCK on {self._current_task_id} '
            f'(no progress for {self._stuck_no_progress_sec:.0f}s) → cancel + replan'
        )
        # Expose congestion so the ecosystem failure_rate rises and the recovery
        # paradigm engages; report STUCK for a short hold window.
        self._congestion_indicator = 3       # high
        self._goal_reachability = 1          # uncertain
        self._request_replan = True
        self._stuck_report_until = self._now_sec() + self._stuck_report_hold_sec
        # Cancel the Nav2 goal (don't leave the robot grinding in place).
        if self._goal_handle is not None:
            try:
                self._goal_handle.cancel_goal_async()
            except Exception:  # noqa: BLE001 - best-effort cancel
                pass
        # Finalize as a soft failure → task re-enters allocation immediately
        # (instead of waiting for Nav2's long failure timeout). _on_task_done
        # resets the robot to IDLE/AVAILABLE so it can take other work.
        self._on_task_done(success=False)

    # ------------------------------------------------------------------
    # Publishers
    # ------------------------------------------------------------------

    def _publish_status(self) -> None:
        msg = RobotStatusSummary()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = f'{self._robot_id}/map'
        msg.robot_id = self._robot_id
        msg.current_pose = self._current_pose
        msg.current_task_id = self._current_task_id
        msg.availability_state = int(self._avail_state)
        msg.battery_state = int(self._battery_state)
        # B1: report STUCK during the post-stuck hold so the ecosystem
        # failure_rate reflects congestion and the recovery paradigm engages.
        reported_nav = int(self._nav_state)
        if self._now_sec() < self._stuck_report_until:
            reported_nav = int(NavState.STUCK)
        msg.navigation_state = reported_nav
        msg.failure_flag = self._failure_flag
        msg.task_completed = bool(self._last_completed_task_id)
        msg.completed_task_id = self._last_completed_task_id
        # Clear the "just completed" flag after one publish cycle
        self._last_completed_task_id = ''
        self._status_pub.publish(msg)

    def _publish_feedback(self) -> None:
        msg = LocalExecutionFeedback()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.robot_id = self._robot_id
        msg.current_task_id = self._current_task_id
        msg.task_progress = float(self._task_progress)
        msg.local_delay = 0.0
        msg.congestion_indicator = int(self._congestion_indicator)
        msg.goal_reachability = int(self._goal_reachability)
        msg.navigation_effort = float(self._distance_remaining)
        msg.temporary_failure = self._now_sec() < self._stuck_report_until
        msg.request_replan = self._request_replan
        self._feedback_pub.publish(msg)
        self._request_replan = False   # one-shot replan request

    # ------------------------------------------------------------------
    # Battery simulation
    # ------------------------------------------------------------------

    def _drain_battery(self) -> None:
        drain = 0.015 if self._nav_state == NavState.NAVIGATING else 0.003
        self._battery_level = max(0.0, self._battery_level - drain)

        if self._battery_level < 0.1:
            self._battery_state = BattState.CRITICAL
        elif self._battery_level < 0.3:
            self._battery_state = BattState.LOW
        else:
            self._battery_state = BattState.NORMAL


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RobotInterfaceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
