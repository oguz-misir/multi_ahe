cmake_minimum_required(VERSION 3.8)
project(m_ahe_mrta_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY worlds/
  DESTINATION share/${PROJECT_NAME}/worlds
  OPTIONAL
)

install(DIRECTORY config/
  DESTINATION share/${PROJECT_NAME}/config
  OPTIONAL
)

install(DIRECTORY models/
  DESTINATION share/${PROJECT_NAME}/models
  OPTIONAL
)

install(DIRECTORY launch/
  DESTINATION share/${PROJECT_NAME}/launch
  OPTIONAL
)

ament_package()
