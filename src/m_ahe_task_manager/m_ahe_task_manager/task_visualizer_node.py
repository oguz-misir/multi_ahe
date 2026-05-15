"""
Task Visualizer Node — publishes MarkerArray on /visualization/tasks.

Shows task waypoints as colored spheres in RViz:
  PENDING  → grey sphere
  ACTIVE   → yellow sphere + text label
  ASSIGNED → cyan sphere
  COMPLETED→ green sphere (small)
  FAILED   → red sphere

Subscribes to /tasks/global_pool (TaskPool) to know task positions/status.
Also subscribes to /allocation/events (AllocationEvent) to update assignment state.
"""

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration

from visualization_msgs.msg import Marker, MarkerArray
from m_ahe_mrta_msgs.msg import TaskPool, AllocationEvent


class TaskVisualizerNode(Node):

    def __init__(self):
        super().__init__('task_visualizer_node')

        self._tasks: dict = {}          # task_id -> {position, priority, status}
        self._assigned: dict = {}       # task_id -> robot_id

        self._pool_sub = self.create_subscription(
            TaskPool, '/tasks/global_pool', self._pool_cb, 10)
        self._event_sub = self.create_subscription(
            AllocationEvent, '/allocation/events', self._event_cb, 10)

        self._marker_pub = self.create_publisher(
            MarkerArray, '/visualization/tasks', 10)

        self.create_timer(0.5, self._publish_markers)

        self.get_logger().info('Task visualizer started')

    def _pool_cb(self, msg: TaskPool):
        for task in msg.tasks:
            existing = self._tasks.get(task.task_id, {})
            self._tasks[task.task_id] = {
                'x': task.target_pose.pose.position.x,
                'y': task.target_pose.pose.position.y,
                'priority': task.priority_level,
                'status': existing.get('status', 'pending'),
            }

    def _event_cb(self, msg: AllocationEvent):
        tid = msg.task_id
        if not tid:
            return
        if tid not in self._tasks:
            self._tasks[tid] = {'x': 0, 'y': 0, 'priority': 1, 'status': 'pending'}

        if msg.event_type == 'task_assigned':
            self._tasks[tid]['status'] = 'assigned'
            self._assigned[tid] = msg.robot_id
        elif msg.event_type == 'task_completed':
            self._tasks[tid]['status'] = 'completed'
        elif msg.event_type == 'task_failed':
            self._tasks[tid]['status'] = 'failed'
        elif msg.event_type == 'activated':
            self._tasks[tid]['status'] = 'active'

    def _publish_markers(self):
        if not self._tasks:
            return

        ma = MarkerArray()
        now = self.get_clock().now().to_msg()

        STATUS_COLORS = {
            'pending':   (0.5, 0.5, 0.5, 0.4),   # grey, semi-transparent
            'active':    (1.0, 0.9, 0.0, 0.9),   # yellow
            'assigned':  (0.0, 0.9, 1.0, 0.9),   # cyan
            'completed': (0.0, 0.8, 0.2, 0.6),   # green
            'failed':    (0.9, 0.1, 0.1, 0.9),   # red
        }
        STATUS_SCALE = {
            'pending': 0.35, 'active': 0.45, 'assigned': 0.45,
            'completed': 0.25, 'failed': 0.40,
        }

        for i, (tid, task) in enumerate(self._tasks.items()):
            status = task.get('status', 'pending')
            r, g, b, a = STATUS_COLORS.get(status, (0.5, 0.5, 0.5, 0.5))
            scale = STATUS_SCALE.get(status, 0.4)

            # Sphere marker
            m = Marker()
            m.header.frame_id = 'robot_1/map'
            m.header.stamp = now
            m.ns = 'task_spheres'
            m.id = i
            m.type = Marker.SPHERE
            m.action = Marker.ADD
            m.pose.position.x = task['x']
            m.pose.position.y = task['y']
            m.pose.position.z = 0.1
            m.pose.orientation.w = 1.0
            m.scale.x = m.scale.y = m.scale.z = scale
            m.color.r = r
            m.color.g = g
            m.color.b = b
            m.color.a = a
            m.lifetime = Duration(seconds=1).to_msg()
            ma.markers.append(m)

            # Text label
            t = Marker()
            t.header.frame_id = 'robot_1/map'
            t.header.stamp = now
            t.ns = 'task_labels'
            t.id = i + 1000
            t.type = Marker.TEXT_VIEW_FACING
            t.action = Marker.ADD
            t.pose.position.x = task['x']
            t.pose.position.y = task['y']
            t.pose.position.z = 0.5
            t.pose.orientation.w = 1.0
            t.scale.z = 0.18
            t.color.r = 1.0
            t.color.g = 1.0
            t.color.b = 1.0
            t.color.a = 0.9
            robot_lbl = self._assigned.get(tid, '')
            t.text = f'{tid}\n{status}\n{robot_lbl}'
            t.lifetime = Duration(seconds=1).to_msg()
            ma.markers.append(t)

        self._marker_pub.publish(ma)


def main(args=None):
    rclpy.init(args=args)
    node = TaskVisualizerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
