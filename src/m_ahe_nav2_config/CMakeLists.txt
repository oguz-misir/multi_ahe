cmake_minimum_required(VERSION 3.8)
project(m_ahe_nav2_config)

find_package(ament_cmake REQUIRED)

install(DIRECTORY maps/ DESTINATION share/${PROJECT_NAME}/maps)
install(DIRECTORY params/ DESTINATION share/${PROJECT_NAME}/params)
install(DIRECTORY urdf/ DESTINATION share/${PROJECT_NAME}/urdf)

ament_package()
