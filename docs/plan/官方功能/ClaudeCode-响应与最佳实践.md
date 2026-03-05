# Claude Code 响应与最佳实践

本文档介绍 Claude Code 的响应数据和最佳实践。

## 1. 响应数据

### 1.1 任务统计信息

每次任务完成后返回详细统计：

```json
{
    "success": true,
    "message": "任务完成响应",
    "session_id": "session_abc123",
    "cost_usd": 0.0525,
    "duration_ms": 3500,
    "files_changed": [
        "/path/to/file1.py",
        "/path/to/file2.py"
    ],
    "tools_used": [
        "Read",
        "Grep",
        "Edit"
    ]
}
```

### 1.2 费用计算

费用基于输入和输出的 token 数量计算：

```
总费用 = (输入 token 数 × 输入单价 + 输出 token 数 × 输出单价) / 1,000,000
```

---

## 2. 最佳实践

### 2.1 工具选择

根据任务需求选择合适的工具：

- **只读任务**：使用 Read、Glob、Grep
- **需要修改**：添加 Write、Edit
- **需要执行**：添加 Bash
- **需要搜索**：添加 WebSearch、WebFetch

### 2.2 权限模式选择

| 场景 | 推荐模式 |
|------|---------|
| 交互式开发 | `acceptEdits` |
| 审查/分析任务 | `default` |
| 复杂重构 | `plan` |
| CI/CD 自动化 | `bypassPermissions` |

### 2.3 错误处理

```python
try:
    async for msg in client.run_stream(prompt):
        if msg.type == MessageType.ERROR:
            logger.error(f"执行错误: {msg.content}")
        elif msg.type == MessageType.COMPLETE:
            if msg.metadata.get("is_error"):
                logger.warning("任务执行失败")
except Exception as e:
    logger.exception("Unexpected error")
```
