cmake_minimum_required(VERSION 3.8)
project(m_ahe_mrta_bringup)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2_ros REQUIRED)

add_executable(nav2_goal_sender src/nav2_goal_sender.cpp)
ament_target_dependencies(nav2_goal_sender rclcpp rclcpp_action nav2_msgs geometry_msgs)
install(TARGETS nav2_goal_sender DESTINATION lib/${PROJECT_NAME})

add_executable(odom_to_tf src/odom_to_tf.cpp)
ament_target_dependencies(odom_to_tf rclcpp nav_msgs geometry_msgs tf2_ros)
install(TARGETS odom_to_tf DESTINATION lib/${PROJECT_NAME})

install(PROGRAMS
  m_ahe_mrta_bringup/tf_relay_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME tf_relay_node
)

install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
  OPTIONAL
)

install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
  OPTIONAL
)

ament_package()
