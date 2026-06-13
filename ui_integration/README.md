# ui_integration — 前端集成

负责系统与前端可视化界面之间的通信与数据渲染。

## 模块

- **WebSocket 桥接** (`websocket_bridge.py`)：ROS ↔ Web 双向通信，转发 `/tf`、`/agent_status` 等话题数据
- **Three.js 可视化** (`threejs_visualizer/`)：前端预览界面，渲染 scene_graph 数据，实时更新堆叠效果，支持蓝图预览与执行监控

## 功能

- 蓝图预览：Three.js 渲染建筑蓝图，用户确认后触发执行
- 实时监控：执行过程中实时显示机械臂状态与积木位置
- 人工确认：`/user_command` 话题含确认标志，确保关键步骤经过人工审核
