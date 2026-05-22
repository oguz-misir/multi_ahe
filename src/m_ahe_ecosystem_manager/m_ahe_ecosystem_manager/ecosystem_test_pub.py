"""
Phase 2 test node — publishes EcosystemState (debug/offline only) and AllocationEvent.

Topics:
  pub  /ecosystem/debug_state   (EcosystemState) — debug only, never consumed by robots
  pub  /allocation/events       (AllocationEvent)

EcosystemState is intentionally NOT published to any robot topic.
In Phase 8 (Full AHE-MRTA), this topic is consumed only by the evaluation logger.

Strategy agents (7 total, Phase 8):
  0: Spatial Opportunist
  1: Criticality Guardian
  2: Temporal Regulator
  3: Resource Distributor
  4: Energy Conservator
  5: Stability Controller
  6: Recovery Coordinator

Context vector (7 components, Phase 8):
  [task_density, robot_availability, battery_risk, deadline_pressure,
   failure_rate, workload_variance, allocation_instability]
"""

import rclpy
from rclpy.node import Node

from m_ahe_mrta_msgs.msg import EcosystemState, AllocationEvent

_HEURISTIC_NAMES = [
    'spatial_opportunist',
    'criticality_guardian',
    'temporal_regulator',
    'resource_distributor',
    'energy_conservator',
    'stability_controller',
    'recovery_coordinator',
]
_K = len(_HEURISTIC_NAMES)
_INIT_DOMINANCE = 1.0 / _K   # uniform initialization per §4.4


class EcosystemTestPub(Node):

    PUBLISH_HZ = 1.0

    def __init__(self) -> None:
        super().__init__('ecosystem_test_pub')

        self._eco_pub = self.create_publisher(
            EcosystemState, '/ecosystem/debug_state', 10)
        self._event_pub = self.create_publisher(
            AllocationEvent, '/allocation/events', 10)

        self._timer = self.create_timer(1.0 / self.PUBLISH_HZ, self._publish)
        self._tick = 0
        self.get_logger().info(
            'ecosystem_test_pub started — /ecosystem/debug_state (debug only, not sent to robots)')

    def _publish(self) -> None:
        self._tick += 1
        now = self.get_clock().now().to_msg()

        eco = EcosystemState()
        eco.header.stamp = now
        eco.header.frame_id = ''
        eco.heuristic_names = _HEURISTIC_NAMES
        eco.dominance_values = [_INIT_DOMINANCE] * _K
        # cooperation_values and suppression_values: K*K flattened, all zero for test
        eco.cooperation_values = [0.0] * (_K * _K)
        eco.suppression_values = [0.0] * (_K * _K)
        # context vector: [task_density, robot_availability, battery_risk,
        #                  deadline_pressure, failure_rate, workload_variance,
        #                  allocation_instability]
        eco.context_vector = [0.2, 1.0, 0.0, 0.1, 0.0, 0.0, 0.0]
        eco.allocation_weights = [1.0 / 7.0] * 7   # uniform placeholder
        self._eco_pub.publish(eco)

        if self._tick % 5 == 0:
            event = AllocationEvent()
            event.header.stamp = now
            event.event_type = 'test_event'
            event.robot_id = 'robot_1'
            event.task_id = 'task_001'
            event.severity = 1
            event.trigger_replan = False
            self._event_pub.publish(event)
            self.get_logger().debug('Published test AllocationEvent')

        self.get_logger().debug(f'Published EcosystemState tick={self._tick}')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EcosystemTestPub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
