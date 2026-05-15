cmake_minimum_required(VERSION 3.8)
project(m_ahe_mrta_bringup)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(nav2_goal_sender src/nav2_goal_sender.cpp)
ament_target_dependencies(nav2_goal_sender rclcpp rclcpp_action nav2_msgs geometry_msgs)
install(TARGETS nav2_goal_sender DESTINATION lib/${PROJECT_NAME})

install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
  OPTIONAL
)

install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
  OPTIONAL
)

ament_package()
