# interaction_layer — 交互层

负责自然语言指令解析、合法性校验及与前端 UI 的双向通信。

## 模块

- **LLM 解析节点** (`llm_parser_node.py`)：通过 LLM 进行 JSON 模板匹配，将自然语言转化为建筑蓝图
- **指令校验** (`command_validator.py`)：指令合法性校验，防止非法参数传入执行层
- **UI 桥接** (`ui_bridge_node.py`)：WebSocket 转发指令与状态，连接 ROS 系统与前端界面

## 数据流

```
用户指令 → llm_parser → command_validator → ui_bridge → 执行层
前端确认 ← ui_bridge ← agent_status ← 执行层
```
