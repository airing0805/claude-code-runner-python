# Claude Code 消息与执行

本文档介绍 Claude Code 的消息类型和执行模式。

## 1. 消息类型

Claude Code 通过流式响应返回多种消息类型：

| 消息类型 | 说明 | 包含内容 |
|---------|------|---------|
| **text** | 文本响应 | Claude 的文本输出 |
| **thinking** | 思考过程 | 内部推理过程（可选） |
| **tool_use** | 工具调用 | 工具名称和参数 |
| **tool_result** | 工具结果 | 工具执行结果 |
| **error** | 错误信息 | 错误描述 |
| **complete** | 任务完成 | 最终结果和统计信息 |

### 1.1 消息结构

```python
@dataclass
class StreamMessage:
    type: MessageType           # 消息类型
    content: str                # 消息内容
    timestamp: str              # 时间戳
    tool_name: str | None       # 工具名称（tool_use 时）
    tool_input: dict | None     # 工具输入参数
    metadata: dict              # 附加元数据
```

### 1.2 完整响应示例

```json
{
    "type": "complete",
    "content": "任务完成",
    "metadata": {
        "session_id": "session_abc123",
        "cost_usd": 0.0525,
        "duration_ms": 3500,
        "is_error": false
    }
}
```

---

## 2. 执行模式

### 2.1 同步执行

等待任务完成后返回完整结果。

```python
client = ClaudeCodeClient(working_dir="/path/to/project")
result = await client.run("分析这个项目的结构")

# result 类型
@dataclass
class TaskResult:
    success: bool                # 是否成功
    message: str                 # 响应消息
    session_id: str | None       # 会话 ID
    cost_usd: float              # 费用（美元）
    duration_ms: int             # 耗时（毫秒）
    files_changed: list[str]     # 变更的文件列表
    tools_used: list[str]        # 使用的工具列表
```

### 2.2 流式执行

实时获取执行过程中的消息。

```python
client = ClaudeCodeClient(working_dir="/path/to/project")

async for msg in client.run_stream("阅读 main.py"):
    if msg.type == MessageType.TEXT:
        print(f"文本: {msg.content}")
    elif msg.type == MessageType.TOOL_USE:
        print(f"调用工具: {msg.tool_name}")
    elif msg.type == MessageType.COMPLETE:
        print(f"完成 - 费用: ${msg.metadata['cost_usd']}")
```

---

## 3. 错误处理

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
