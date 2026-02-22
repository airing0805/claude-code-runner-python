# AskUserQuestion tool_result 格式问题记录

## 问题描述

用户选择 AskUserQuestion 多选对话框的选项后，前端应该显示对应的结果（如"背唐诗"），但实际上前端又输出了"我已经弹出了一个多选对话框"，同时又弹出了一个对话框。

## 根因分析

从日志中发现关键线索：
```
[SDK Raw] ★★★ 消息内容: [ToolResultBlock(..., content='Answer questions?', is_error=True)]
```

SDK 返回了 `is_error=True`，说明 CLI 认为我们的 tool_result 响应有问题，因此没有正确处理用户答案。

## 问题根因

### 关键发现：SDK 格式 vs JSONL 格式

**JSONL 文件**（由 Claude Code CLI 生成）使用的格式：
```json
{
  "parentUuid": "88d67c5d-aaff-49d0-8f8d-1812c57415e4",  // 消息的 uuid
  "uuid": "159cdd44-2c9f-47d1-ae3d-92e6fa758053",
  "timestamp": "2026-02-22T03:58:19.997Z",
  "toolUseResult": {...},
  "sourceToolAssistantUUID": "88d67c5d-aaff-49d0-8f8d-1812c57415e4"
}
```

**Python SDK** 期望的格式：
```python
{
    "type": "user",
    "message": {"role": "user", "content": [...]},
    "parent_tool_use_id": "call_function_xxx",  # 注意：不是 parentUuid！
}
```

### 错误原因

我们之前使用了 JSONL 格式（`parentUuid`、`uuid`、`timestamp`、`sourceToolAssistantUUID`），但这不是 Python SDK 期望的格式。

从 SDK 的 `query` 方法源码中可以看到：
```python
async def query(self, prompt: str | AsyncIterable[dict[str, Any]], session_id: str = "default") -> None:
    if isinstance(prompt, str):
        message = {
            "type": "user",
            "message": {"role": "user", "content": prompt},
            "parent_tool_use_id": None,  # 使用 parent_tool_use_id 字段
            "session_id": session_id,
        }
        await self._transport.write(json.dumps(message) + "\n")
    else:
        # AsyncIterable - 直接写入消息
        async for msg in prompt:
            if "session_id" not in msg:
                msg["session_id"] = session_id
            await self._transport.write(json.dumps(msg) + "\n")
```

### 问题总结

| 问题 | 描述 |
|------|------|
| 字段名错误 | 使用 `parentUuid` 而不是 SDK 期望的 `parent_tool_use_id` |
| 缺少 toolUseResult | 虽然添加了，但字段名格式不对 |
| 消息 uuid 不可用 | SDK 的 `AssistantMessage` 类没有 uuid 字段 |

## 解决方案

### 使用 SDK 内部格式

修改 `_send_tool_result_via_query` 方法，使用 SDK 期望的格式：

```python
message = {
    "type": "user",
    "message": {
        "role": "user",
        "content": [tool_result_dict],
    },
    "parent_tool_use_id": tool_id,  # 使用 SDK 内部字段名
}

# 添加 toolUseResult（如果有的话）
if tool_use_result:
    message["toolUseResult"] = tool_use_result
```

### 关键点

1. **使用 `parent_tool_use_id` 字段**：这是 SDK 期望的字段名
2. **保留 `toolUseResult` 字段**：这个字段对 CLI 处理答案很重要
3. **移除不必要的字段**：`parentUuid`、`uuid`、`timestamp`、`sourceToolAssistantUUID` 不是必需的

## 修改文件

### app/claude_runner/client.py

```python
async def _send_tool_result_via_query(
    self,
    client: "ClaudeSDKClient",
    tool_id: str,
    content: str,
    question_data: Optional[Any] = None,
    answer: Optional[dict] = None,
) -> None:
    # 构建工具结果字典
    tool_result_dict = {
        "type": "tool_result",
        "content": content,
        "tool_use_id": tool_id,
    }

    # 构建 toolUseResult
    tool_use_result = None
    if answer:
        raw_question_data = answer.get("raw_question_data")
        # ... 构建 toolUseResult ...

    # 使用 SDK 内部格式
    message = {
        "type": "user",
        "message": {
            "role": "user",
            "content": [tool_result_dict],
        },
        "parent_tool_use_id": tool_id,  # 关键：使用 SDK 字段名
    }

    if tool_use_result:
        message["toolUseResult"] = tool_use_result

    async def message_generator():
        yield message

    await client.query(message_generator())
```

## 验证方法

1. 重启服务
2. 执行任务：使用 ask_user_question 工具，弹出一个多选对话框
3. 选择任意选项（如"背唐诗"）
4. 验证：
   - 前端应该显示对应的结果内容
   - SDK 应该正确处理用户答案，不再返回 `is_error=True`

## 参考资料

- `docs/samples/多轮对话AskUserQuestion会话记录格式.jsonl` - CLI 记录格式（仅供参考）
- SDK 源码：`claude_code_sdk/client.py` 中的 `query` 方法

## 更新历史

- 2026-02-22：初始分析，发现 `parentUuid` vs `parent_tool_use_id` 的问题
- 2026-02-22：修复方案 - 使用 SDK 内部格式
