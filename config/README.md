# config — 配置层

集中管理系统各层级的配置参数。

## 配置文件

| 文件 | 描述 |
|------|------|
| `moveit_controllers.yaml` | MoveIt 控制器配置（轨迹规划器、关节限位、碰撞检测参数） |
| `skill_params.yaml` | 技能参数（容差阈值、重试次数、力控阈值、超时时间） |

## 设计原则

- 参数与代码分离，调整参数无需重新编译
- 仿真与真机通过 `hardware_switch` 加载不同的配置覆盖
- 命名约定：Python snake_case，常量 UPPER_CASE
