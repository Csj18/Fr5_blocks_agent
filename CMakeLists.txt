cmake_minimum_required(VERSION 3.8)
project(block_stacking_agent)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Install directories
install(DIRECTORY config launch msg rag_data
  DESTINATION share/${PROJECT_NAME}
)

# Install scripts as executables (ROS 2 libexec)
install(PROGRAMS
  scripts/block_tf_bridge.py
  scripts/block_collision_updater.py
  scripts/block_visual_marker.py
  scripts/table_marker.py
  scripts/pick_place_server.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY agent_brain skill_library execution_layer
  perception_layer interaction_layer memory_layer ui_integration
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
