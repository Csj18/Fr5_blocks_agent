# launch — 启动层

ROS 2 launch 文件，管理全系统节点的启动与生命周期。

## 启动文件

| 文件 | 描述 |
|------|------|
| `sim_agent.launch.py` | 仿真启动：加载 mock_components，用于开发与测试 |
| `real_agent.launch.py` | 真机启动：加载 fairino_hardware 驱动，连接实际机械臂 |
| `agent_system.launch.py` | 全系统启动：一键拉起所有节点（认知→感知→执行→交互） |

## 启动方式

```bash
# 仿真
ros2 launch block_stacking_agent sim_agent.launch.py

# 真机
ros2 launch block_stacking_agent real_agent.launch.py
```
