cmake_minimum_required(VERSION 3.8)
project(fr5_description)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 寻找 ament 编译依赖
find_package(ament_cmake REQUIRED)
find_package(urdf REQUIRED)
find_package(xacro REQUIRED)

# 核心：安装你的文件夹到 share 目录下，这样 MoveIt 才能找到 package://
install(DIRECTORY
  launch
  meshes
  urdf
  DESTINATION share/${PROJECT_NAME}
)

ament_package()