# Claude Code 代理类型

Claude Code 内置多种专业代理，可通过 Task 工具调用。

## 代理概览

| 代理类型 | 用途 | 说明 |
|----------|------|------|
| **general-purpose** | 通用任务 | 处理各种编程任务 |
| **explore** | 代码库探索 | 快速了解代码库结构 |
| **code-explorer** | 代码分析 | 深入分析代码逻辑 |
| **code-architect** | 架构设计 | 设计系统架构方案 |
| **code-reviewer** | 代码审查 | 审查代码质量和安全 |
| **agent-creator** | 插件创建 | 辅助开发 Claude Code 插件 |
| **plugin-validator** | 插件验证 | 验证插件结构 |
| **skill-reviewer** | 技能审查 | 审查技能定义 |
| **conversation-analyzer** | 对话分析 | 分析对话模式 |

---

## 调用代理

```python
{
    "name": "Task",
    "input": {
        "prompt": "分析这个项目的错误处理模式",
        "agent": "code-explorer",
        "model": "sonnet"
    }
}
```

### 参数说明

- `prompt`（必需）：子任务描述
- `agent`（可选）：代理类型（general-purpose/explore/code-explorer 等）
- `model`（可选）：使用的模型（sonnet/haiku）
