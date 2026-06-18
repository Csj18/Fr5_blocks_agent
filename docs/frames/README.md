# frames — TF 树快照

由 `ros2 run tf2_tools view_frames` 生成，按开发阶段保留 3 份代表性快照：

| 文件 | 日期 | 状态 |
|------|------|------|
| `tf_broken_2026-06-11.pdf` | 06-11 | ❌ TF 完全断开，"No tf data received" |
| `tf_partial_2026-06-12.pdf` | 06-12 | ⚠️ 部分恢复（base_link 链正常，缺少 world） |
| `tf_working_2026-06-15.pdf` | 06-15 | ✅ 完整 TF 树（world→robot→gripper + blocks） |

> 当前准确的 TF 树文档见 [../simulation_data_flow.md](../simulation_data_flow.md) 第一章。
