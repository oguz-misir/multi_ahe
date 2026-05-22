"""
Gazebo Path Visualizer Node — draws Nav2 paths and task targets directly in Gazebo.

ros_gz_bridge in ROS2 Jazzy does not support visualization_msgs/MarkerArray ↔
gz.msgs.Marker_V. Instead this node calls the Gazebo /marker_array service
directly via gz.transport13 Python bindings, bypassing the bridge entirely.

Subscribes to:
  /robot_N/plan          (nav_msgs/Path)       — current planned path per robot
  /tasks/global_pool     (TaskPool)            — task positions
  /allocation/events     (AllocationEvent)     — assignment / completion status

Publishes to Gazebo (via gz.transport13 service):
  /marker_array          (gz.msgs.Marker_V)   — paths + task targets

Robot colour coding:
  robot_1 → blue  material
  robot_2 → green material
  robot_3 → red   material
"""

import sys

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from nav_msgs.msg import Path
from m_ahe_mrta_msgs.msg import AllocationEvent, TaskPool

# gz.transport13 + gz.msgs10 (Jazzy ships both)
try:
    sys.path.insert(0, '/opt/ros/jazzy/opt/gz_msgs_vendor/lib/python')
    import gz.transport13 as gz_transport
    from gz.msgs10 import marker_pb2 as _gz_marker
    from gz.msgs10 import marker_v_pb2 as _gz_marker_v
    from gz.msgs10 import boolean_pb2 as _gz_bool
    _GZ_OK = True
except Exception:
    _GZ_OK = False

ROBOTS = ['robot_1', 'robot_2', 'robot_3']

# Marker type constants (gz.msgs.Marker.Type)
_LINE_STRIP = 6
_CYLINDER   = 2

# Action constants
_ADD = 0
_DELETE_ALL = 3

# Robot RGBA colours as (r, g, b, a) in 0–1 range
ROBOT_RGBA = {
    'robot_1': (0.0,  0.47, 1.0,  0.9),
    'robot_2': (0.0,  0.78, 0.31, 0.9),
    'robot_3': (0.86, 0.20, 0.20, 0.9),
}

STATUS_RGBA = {
    'pending':   (0.5, 0.5, 0.5, 0.5),
    'active':    (1.0, 0.9, 0.0, 0.9),
    'assigned':  (0.0, 0.9, 1.0, 0.9),
    'completed': (0.0, 0.8, 0.2, 0.7),
    'failed':    (0.9, 0.1, 0.1, 0.9),
}


def _set_color(marker, r, g, b, a):
    marker.material.ambient.r = r
    marker.material.ambient.g = g
    marker.material.ambient.b = b
    marker.material.ambient.a = a
    marker.material.diffuse.r = r
    marker.material.diffuse.g = g
    marker.material.diffuse.b = b
    marker.material.diffuse.a = a


class GzPathVisualizerNode(Node):

    def __init__(self):
        super().__init__('gz_path_visualizer_node')

        self._paths: dict = {}   # robot_id → [(x, y), ...]
        self._tasks: dict = {}   # task_id  → {x, y, status, robot_id}
        self._mid = 0            # running marker ID counter

        if _GZ_OK:
            self._gz_node = gz_transport.Node()
            self.get_logger().info('gz.transport13 OK — markers sent via /marker_array service')
        else:
            self._gz_node = None
            self.get_logger().warn('gz.transport13 not available — Gazebo markers disabled')

        for robot in ROBOTS:
            self.create_subscription(
                Path, f'/{robot}/plan',
                lambda msg, r=robot: self._path_cb(r, msg), 10)

        self.create_subscription(TaskPool, '/tasks/global_pool', self._pool_cb, 10)
        self.create_subscription(AllocationEvent, '/allocation/events', self._event_cb, 10)

        self.create_timer(0.5, self._publish)

        self.get_logger().info('Gazebo path visualizer started')

    # ── Callbacks ──────────────────────────────────────────────────────────────

    def _path_cb(self, robot_id: str, msg: Path) -> None:
        self._paths[robot_id] = [
            (p.pose.position.x, p.pose.position.y) for p in msg.poses
        ]

    def _pool_cb(self, msg: TaskPool) -> None:
        for task in msg.tasks:
            existing = self._tasks.get(task.task_id, {})
            self._tasks[task.task_id] = {
                'x': task.target_pose.pose.position.x,
                'y': task.target_pose.pose.position.y,
                'status': existing.get('status', 'pending'),
                'robot_id': existing.get('robot_id', ''),
            }

    def _event_cb(self, msg: AllocationEvent) -> None:
        tid = msg.task_id
        if not tid:
            return
        if tid not in self._tasks:
            self._tasks[tid] = {'x': 0.0, 'y': 0.0, 'status': 'pending', 'robot_id': ''}
        ev = msg.event_type
        if ev == 'task_assigned':
            self._tasks[tid]['status'] = 'assigned'
            self._tasks[tid]['robot_id'] = msg.robot_id
        elif ev == 'task_completed':
            self._tasks[tid]['status'] = 'completed'
        elif ev == 'task_failed':
            self._tasks[tid]['status'] = 'failed'
        elif ev == 'activated':
            self._tasks[tid]['status'] = 'active'

    # ── Publisher ──────────────────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._mid += 1
        return self._mid

    def _publish(self) -> None:
        if self._gz_node is None:
            return
        if not self._paths and not self._tasks:
            return

        mv = _gz_marker_v.Marker_V()

        # Path line strips — one per robot
        for robot_id, pts in self._paths.items():
            if len(pts) < 2:
                continue
            r, g, b, a = ROBOT_RGBA.get(robot_id, (1.0, 1.0, 0.0, 0.8))
            m = _gz_marker.Marker()
            m.ns = f'gz_path_{robot_id}'
            m.id = 1
            m.action = _ADD
            m.type = _LINE_STRIP
            m.lifetime.sec = 1
            m.scale.x = 0.05
            m.scale.y = 0.05
            m.scale.z = 0.05
            _set_color(m, r, g, b, a)
            for x, y in pts:
                p = m.point.add()
                p.x = x; p.y = y; p.z = 0.04
            mv.marker.append(m)

        # Task cylinders
        for i, (tid, task) in enumerate(self._tasks.items()):
            r, g, b, a = STATUS_RGBA.get(task.get('status', 'pending'), (0.5, 0.5, 0.5, 0.5))

            # Tall cylinder
            cyl = _gz_marker.Marker()
            cyl.ns = 'gz_targets'
            cyl.id = i * 2 + 1
            cyl.action = _ADD
            cyl.type = _CYLINDER
            cyl.lifetime.sec = 1
            cyl.pose.position.x = task['x']
            cyl.pose.position.y = task['y']
            cyl.pose.position.z = 0.25
            cyl.pose.orientation.w = 1.0
            cyl.scale.x = 0.30
            cyl.scale.y = 0.30
            cyl.scale.z = 0.50
            _set_color(cyl, r, g, b, a)
            mv.marker.append(cyl)

            # Ground disc
            disc = _gz_marker.Marker()
            disc.ns = 'gz_target_disc'
            disc.id = i * 2 + 2
            disc.action = _ADD
            disc.type = _CYLINDER
            disc.lifetime.sec = 1
            disc.pose.position.x = task['x']
            disc.pose.position.y = task['y']
            disc.pose.position.z = 0.005
            disc.pose.orientation.w = 1.0
            disc.scale.x = 0.50
            disc.scale.y = 0.50
            disc.scale.z = 0.01
            _set_color(disc, r, g, b, min(a + 0.1, 1.0))
            mv.marker.append(disc)

        if mv.marker:
            try:
                self._gz_node.request(
                    '/marker_array', mv,
                    _gz_marker_v.Marker_V, _gz_bool.Boolean,
                    50)   # 50 ms timeout — non-blocking if Gazebo down
            except Exception:
                pass   # Gazebo not running yet, skip silently

    def destroy_node(self):
        # Send DELETE_ALL to clean up markers on shutdown
        if self._gz_node is not None:
            try:
                mv = _gz_marker_v.Marker_V()
                for ns in ('gz_path_robot_1', 'gz_path_robot_2', 'gz_path_robot_3',
                           'gz_targets', 'gz_target_disc'):
                    m = mv.marker.add()
                    m.ns = ns
                    m.action = _DELETE_ALL
                self._gz_node.request(
                    '/marker_array', mv,
                    _gz_marker_v.Marker_V, _gz_bool.Boolean, 100)
            except Exception:
                pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = GzPathVisualizerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
