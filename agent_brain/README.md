# agent_brain — 认知层

负责 LLM 推理、RAG 检索与建筑蓝图规划生成，是整个系统的"大脑"。

## 职责

- **LLM 接口封装** (`llm_core.py`)：调用 Ollama 等推理服务，解析自然语言指令
- **RAG 管理** (`rag_manager.py`)：向量数据库管理，检索物理规则、结构案例与失败经验
- **提示词模板** (`prompt_templates/`)：系统提示词，注入物理约束、FR5 参数与容错策略
- **规划合成** (`plan_synthesizer.py`)：将 LLM 输出解析为技能执行链（Pick → Place → Check）

## 依赖

- Ollama / 其他 LLM 推理服务
- FAISS / Milvus 向量数据库
- pydantic（JSON 校验）
