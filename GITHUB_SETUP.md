# GitHub 推送配置记录

> 配置日期: 2026-06-13

## 仓库信息

| 项目 | 值 |
|------|-----|
| 用户名 | Csj18 |
| 仓库名 | Fr5_blocks_agent |
| 远程地址 | `https://github.com/Csj18/Fr5_blocks_agent.git` |
| 默认分支 | `main` |

## 认证方式

- **方式**: Personal Access Token (经典令牌)
- **存储位置**: `.git/config` 中的 remote URL
- **格式**: `https://Csj18:<PAT>@github.com/Csj18/Fr5_blocks_agent.git`

## 自动推送

- **频率**: 每天一次
- **时间**: 上午 9:57
- **命令**: `cd /home/csj/Fairino_agent_ws && git push origin main`
- **配置文件**: `.claude/scheduled_tasks.json`

> ⚠️ 定时任务 7 天后过期，需重新创建。

## 手动推送

```bash
git push origin main
```

## 更新 PAT

如果令牌过期，执行以下命令更新：

```bash
git remote set-url origin "https://Csj18:<NEW_PAT>@github.com/Csj18/Fr5_blocks_agent.git"
```

## 重新创建定时任务

定时任务过期后，在 Claude Code 中输入：

> 帮我重新创建每天推送到 GitHub 的定时任务
