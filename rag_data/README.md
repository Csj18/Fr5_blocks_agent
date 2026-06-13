# rag_data — RAG 知识库

存放用于检索增强生成（RAG）的知识数据，供 agent_brain 中的 rag_manager 索引与检索。

## 内容类型

- **物理规则**：重心公式、摩擦系数、稳定条件等物理约束
- **结构案例**：典型建筑结构（拱桥、塔楼等）的搭建方案与参数
- **失败经验**：历史执行失败案例，用于避免重复错误

## 使用

```bash
# 初始化 RAG 向量库
python rag_manager.py init --data rag_data/

# 添加新知识条目
python rag_manager.py add --file rag_data/new_case.json
```

## 格式

知识条目以 JSON 格式存储，含标题、类型、内容、标签等字段，便于向量检索。
