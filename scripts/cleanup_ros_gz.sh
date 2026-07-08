#!/usr/bin/env bash
# Scoped cleanup for interrupted AHE ROS 2 / Gazebo experiment processes.
set -u

patterns=(
  "run_f58_gazebo_validation.sh" "run_experiments_robust.sh"
  "timeout .*phase9_experiments"
  "gz sim" "gz_server" "gz_client" "gzserver" "gzclient"
  "ros2 launch" "experiment_runner_node" "ecosystem_manager"
  "robot_interface_node" "parameter_bridge" "ros_gz_bridge"
  "amcl" "bt_navigator" "controller_server" "planner_server" "map_server"
  "robot_state_publisher" "lifecycle_manager"
)

for pattern in "${patterns[@]}"; do
  pkill -TERM -f "$pattern" 2>/dev/null || true
done
sleep 10
for pattern in "${patterns[@]}"; do
  pkill -KILL -f "$pattern" 2>/dev/null || true
done
ros2 daemon stop >/dev/null 2>&1 || true
echo "ROS 2 / Gazebo experiment processes cleaned."
