# Claude Code 会话管理

本文档介绍 Claude Code 的会话管理和配置选项。

## 1. 会话管理

### 1.1 继续对话

在同一会话中继续对话。

```python
client = ClaudeCodeClient(
    working_dir="/path/to/project",
    continue_conversation=True
)

# 第一轮
result1 = await client.run("阅读 auth.py")

# 第二轮 - 继续同一会话
result2 = await client.run("现在添加登录功能")
```

### 1.2 恢复会话

通过会话 ID 恢复历史会话。

```python
client = ClaudeCodeClient(
    working_dir="/path/to/project",
    resume="session_abc123"  # 之前返回的 session_id
)

result = await client.run("继续之前的任务")
```

---

## 2. 配置选项

### 2.1 ClaudeCodeOptions

```python
@dataclass
class ClaudeCodeOptions:
    permission_mode: str         # 权限模式
    cwd: str                    # 工作目录
    continue_conversation: bool # 继续对话
    resume: str | None          # 恢复的会话 ID
    allowed_tools: list[str] | None  # 允许的工具列表
    max_tokens: int | None      # 最大输出 token
    model: str | None           # 使用的模型
```

### 2.2 认证方式

| 方式 | 说明 |
|------|------|
| `claude login` | CLI 登录认证（推荐） |
| `hasCompletedOnboarding` | 配置跳过登录（见下方说明） |
| `ANTHROPIC_API_KEY` | 环境变量（SDK 调用时使用） |

**跳过登录配置**：在 `~/.claude/settings.json` 中设置：
```json
{
  "hasCompletedOnboarding": true
}
```

**注意**：使用 `claude login` 登录是最推荐的方式。配置 `hasCompletedOnboarding` 可跳过登录流程，适用于特殊场景。仅在使用 SDK 编程调用时才需要设置 `ANTHROPIC_API_KEY` 环境变量。

## 3. 会话完整性保证

### 3.1 问题说明

**调度任务会话不完整问题**:

在任务调度场景下，SDK 的 `ResultMessage` 发出时间可能早于 Claude Code 会话记录的完整写入时间，导致：

1. 会话停留在 Assistant 的 "thinking" 阶段
2. 任务被标记为 `completed`，但实际输出不完整
3. 日志显示成功，但 `result.message` 为空

### 3.2 解决方案

**在 `client.py` 的 `run()` 方法中添加延迟**:

```python
async def run(self, prompt: str) -> TaskResult:
    texts: list[str] = []
    ...

    async for msg in self.run_stream(prompt):
        if msg.type == MessageType.COMPLETE:
            # 记录完成信息
            ...
            # 等待会话记录写入完成（20秒延迟）
            await asyncio.sleep(20)
            break
```

### 3.3 业务规则

**规则 ID**: SR-SESSION-001
**规则名称**: 调度任务会话完整性保证
**规则描述**: 在收到 SDK 的 COMPLETE 消息后，等待 20 秒让 Claude Code 会话记录完成写入
**规则来源**: 2026-03-05 会话不完整问题分析
**优先级**: 高
**适用场景**: 调度任务执行
