# 项目介绍：Fairino FR5 积木堆叠智能体（终版）

## 项目概述
### 项目名称
Fairino FR5 Block Stacking Agent

### 核心价值
本项目是一套面向**具身智能（Embodied AI）**的机器人控制中间件，通过**“视觉定位原料+内部世界模型维护已搭建结构”**的混合感知架构，解决从**非结构化自然语言指令**到**高精度工业机械臂执行**的映射问题。系统结合LLM推理、RAG增强规划与标准化技能库，实现复杂积木建筑的自主构建，同时保证“永不停止”的容错执行能力。

### 一句话简介
基于ROS 2 Humble与MoveIt 2，通过**视觉识别未搭建原料位姿**、**内部世界模型（Scene Graph）维护已搭建结构**，利用LLM+RAG将自然语言转化为建筑蓝图，由Fairino FR5机械臂通过标准化技能（Pick/Place）完成高容错堆叠。

### 系统工作流程
#### 1. 认知与规划（Cognitive Layer）
- **自然语言理解**：接收终端/前端指令（如“搭建稳固拱桥”），通过LLM解析意图。
- **建筑生成**：LLM结合RAG知识库（物理规则、结构案例、失败经验）生成JSON建筑蓝图，明确堆叠序列、颜色约束与结构稳定性要求。
- **可视化确认**：前端Three.js渲染蓝图，用户确认后下发执行指令。

#### 2. 感知与定位（Perception Layer）
- **仅视觉定位原料**：`vision_detector.py`通过YOLO/SAM识别**未搭建积木**的位姿（位置、姿态），输出`BlockPose.msg`；**已搭建部分**不依赖视觉，由`scene_graph.py`维护内部世界模型。
- **局部视觉修正（进阶容错）**：每层搭建后，对当前层积木进行局部视觉校准，修正微小滑动误差（≤2mm），更新`scene_graph`。

#### 3. 执行与控制（Execution Layer）
- **技能化封装**：调用标准化技能库（`skill_library`）执行原子动作：
  - `Pick Skill`：基于视觉提供的原料位姿，计算抓取点（含预抓取点、力控闭合）。
  - `Place Skill`：结合`geometry_calc.py`（几何推算）与`scene_graph`（已搭建结构），生成安全放置位姿，执行防碰撞路径规划与微退。
- **模型驱动放置**：根据积木尺寸与父物体高度自动计算放置位姿，避免结构失稳。

#### 4. 容错与恢复（Resilience）
- **永不停止机制**：技能层设软超时兜底（≤3次重试），失败后跳过并记录，继续执行后续任务。
- **误差累积抑制**：通过“内部模型+局部视觉修正”闭环，每层校准偏差，避免高层累积误差。

## 技术栈
- **框架**：ROS 2 Humble、MoveIt 2、ros2_control  
- **语言**：Python 3.10（业务逻辑）、C++（底层交互）  
- **工具链**：Ollama（LLM推理）、FAISS/Milvus（向量数据库）、Three.js（前端可视化）、YOLO/SAM（视觉识别）  
- **关键依赖**：fairino_hardware（官方驱动）、requests（HTTP通信）、pydantic（JSON校验）、rclpy（ROS 2接口）  

## 项目目录结构（分层解耦版）
~/Fairino_agent_ws/
├── agent_brain/                 # 认知层：LLM推理、RAG检索、规划生成
│   ├── llm_core.py              # LLM接口封装（API调用、JSON解析）
│   ├── rag_manager.py           # 向量数据库管理（物理规则/失败经验/物体属性）
│   ├── prompt_templates/        # 系统提示词（物理约束、FR5参数、容错策略）
│   └── plan_synthesizer.py      # LLM输出解析为技能执行链（Pick→Place→Check）
│
├── skill_library/               # 技能层：原子动作封装（ROS 2 Action Server）
│   ├── pick_skill/              # 抓取技能（视觉修正原料位姿、力控闭合）
│   │   ├── Pick.action          # 动作定义（原料ID、抓取策略、容差）
│   │   └── pick_server.py       # 实现：计算抓取点→MoveIt规划→执行→反馈
│   ├── place_skill/             # 放置技能（内部模型+几何推算位姿）
│   │   ├── Place.action         # 动作定义（目标层ID、稳定阈值、父块ID）
│   │   └── place_server.py      # 实现：路径规划→放置→微退→触发局部校准
│   └── base_move_skill/         # 基座位姿移动（预留避障逻辑）
│
├── execution_layer/             # 执行层：硬件与MoveIt接口
│   ├── fr5_commander.py         # MoveIt 2封装（轨迹规划、执行、取消）
│   ├── gripper_controller.py    # 夹爪控制（开合、力反馈读取）
│   └── hardware_switch.py       # 仿真/真机切换（mock_components ↔ fairino_hardware）
│
├── perception_layer/            # 感知层：仅视觉定位原料
│   ├── vision_detector.py       # 识别未搭建积木位姿（YOLO/SAM），输出BlockPose.msg
│   └── scene_calibrator.py      # 局部视觉修正（每层搭建后校准当前层积木位姿）
│
├── interaction_layer/           # 交互层：自然语言解析与指令分发
│   ├── llm_parser_node.py       # LLM JSON解析（模板匹配→生成建筑蓝图）
│   ├── command_validator.py     # 指令合法性校验（防非法参数）
│   └── ui_bridge_node.py        # 前端接口（WebSocket转发指令/状态）
│
├── memory_layer/                # 记忆层：内部世界模型与日志
│   ├── scene_graph.py           # 维护已搭建结构（块ID-位姿-属性映射，含视觉校准标记）
│   └── session_log.py           # 任务日志（含失败案例，用于RAG入库）
│
├── ui_integration/              # 前端集成：可视化与人工确认
│   ├── websocket_bridge.py      # ROS↔Web双向通信（转发/tf、/agent_status）
│   └── threejs_visualizer/      # Three.js前端（渲染scene_graph数据，实时更新堆叠效果）
│
├── config/                      # 配置层
│   ├── moveit_controllers.yaml  # MoveIt控制器配置
│   └── skill_params.yaml        # 技能参数（容差、重试次数、力控阈值）
│
├── launch/                      # 启动层
│   ├── sim_agent.launch.py      # 仿真启动（加载mock_components）
│   ├── real_agent.launch.py     # 真机启动（加载fairino_hardware）
│   └── agent_system.launch.py   # 全系统启动
│
├── rag_data/                    # RAG知识库（物理规则、结构案例、失败经验）
│
├── msg/                         # 自定义消息
│   ├── AgentTask.msg            # 任务指令（含建筑蓝图、确认状态）
│   ├── AgentStatus.msg          # 状态日志（执行进度、错误码、传感器数据）
│   └── BlockPose.msg            # 积木位姿（ID、位置、姿态、尺寸、校准标记）
│
└── README.md                    # 项目说明（含架构图、开发指南）

## 核心功能
1. **混合感知定位**  
   - **原料视觉定位**：`vision_detector.py`仅识别未搭建积木位姿，输出`BlockPose.msg`。  
   - **已搭建结构维护**：`scene_graph.py`通过内部模型记录已搭建积木位姿，每层搭建后由`scene_calibrator.py`进行局部视觉校准（修正≤2mm偏差）。  

2. **具身智能规划（LLM+RAG+Skill）**  
   - **LLM角色**：自然语言解析（生成建筑蓝图）+ 规划推理（检索RAG约束结构稳定性）。  
   - **RAG增强**：检索`knowledge_base`中物理规则（如拱桥配重要求），避免LLM生成失稳方案。  
   - **技能调度**：`plan_synthesizer.py`将蓝图转为技能链（Pick原料→Place到scene_graph指定层→校准），通过`skill_library`原子动作执行。  

3. **人机协同与容错执行**  
   - **前端确认**：Three.js渲染蓝图，用户确认后触发执行（`/user_command`含确认标志）。  
   - **永不停止机制**：技能失败重试（≤3次）→跳过并记录→继续执行，日志实时推送前端。  

4. **分布式架构**  
   LLM推理部署于独立服务器（Ollama），ROS 2节点通过HTTP API调用，解析时去除Markdown标记。  

## 关键特性
| 特性                | 描述                                                                 |
|---------------------|----------------------------------------------------------------------|
| **混合感知架构**    | 仅视觉定位原料，已搭建结构用内部模型+局部修正，平衡精度与算力效率。   |
| **LLM+RAG增强规划** | 检索物理规则库约束LLM生成稳定方案，避免结构失稳与幻觉。               |
| **标准化技能库**    | Pick/Place封装为ROS 2 Action Server，支持独立调试与复用。             |
| **永不停止容错**    | 多层重试+跳过机制，确保主流程不中断，日志全量记录。                   |
| **人机协同可视化**  | 前端实时渲染scene_graph数据，支持蓝图预览与执行监控。                 |

## 运行与开发
- **环境要求**：Ubuntu 22.04、ROS 2 Humble、MoveIt 2、相机（视觉识别）。  
- **安装步骤**：  
  1. 克隆仓库至`~/Fairino_agent_ws`；  
  2. `rosdep install --from-paths . --ignore-src -r -y`安装依赖；  
  3. `colcon build --symlink-install`编译；  
  4. `python rag_manager.py init --data rag_data/`部署RAG库。  
- **启动方式**：  
  - 仿真：`ros2 launch block_stacking_agent sim_agent.launch.py`  
  - 真机：`ros2 launch block_stacking_agent real_agent.launch.py`  

## 注意事项
- **视觉校准**：`scene_calibrator.py`仅在每层搭建后触发，避免过度算力消耗。  
- **TF同步**：视觉识别坐标需转换至机械臂基坐标系（TF广播同步）。  
- **命名约定**：Python snake_case，ROS Topic lowercase，常量UPPER_CASE。