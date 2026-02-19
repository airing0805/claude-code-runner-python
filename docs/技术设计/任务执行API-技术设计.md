# 任务执行 API 技术设计

## 概述

任务执行 API 是 Claude Code Runner 的核心功能，提供同步和流式两种任务执行方式。

---

## 同步任务执行

### POST /api/task

同步执行任务，等待完整结果返回。

**请求体**:

```json
{
  "prompt": "列出当前目录下的所有 Python 文件",
  "working_dir": "/path/to/project",
  "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
  "continue_conversation": false,
  "resume": "session-id-optional"
}
```

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 任务描述 |
| working_dir | string | 否 | 工作目录，默认使用环境变量 WORKING_DIR |
| tools | string[] | 否 | 允许的工具列表，默认常用工具 |
| continue_conversation | boolean | 否 | 是否延续最近会话，默认 false |
| resume | string | 否 | 恢复指定会话 ID |

**响应**:

```json
{
  "success": true,
  "message": "找到以下 Python 文件：\n- main.py\n- utils.py",
  "session_id": "abc123def456",
  "cost_usd": 0.0025,
  "duration_ms": 3500,
  "files_changed": [],
  "tools_used": ["Glob"]
}
```

---

## 流式任务执行

### POST /api/task/stream

SSE 流式执行任务，实时推送执行过程。

**请求体**: 同 `/api/task`

**响应**: Server-Sent Events

```
data: {"type": "text", "content": "正在查找...", "timestamp": "2026-02-18T10:00:00"}

data: {"type": "tool_use", "content": "调用工具: Glob", "tool_name": "Glob", "tool_input": {"pattern": "*.py"}, "timestamp": "2026-02-18T10:00:01"}

data: {"type": "complete", "content": "任务完成", "metadata": {"session_id": "abc123", "cost_usd": 0.0025, "duration_ms": 3500, "is_error": false}, "timestamp": "2026-02-18T10:00:02"}
```

**消息类型**:

| type | 说明 |
|------|------|
| text | 文本内容 |
| tool_use | 工具调用 |
| tool_result | 工具结果 |
| thinking | 思考过程 |
| error | 错误信息 |
| complete | 任务完成 |

---

## 使用示例

### cURL

```bash
# 同步执行任务
curl -X POST http://127.0.0.1:8000/api/task \
  -H "Content-Type: application/json" \
  -d '{"prompt": "列出所有 Python 文件"}'

# 流式执行任务
curl -X POST http://127.0.0.1:8000/api/task/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "分析项目结构"}'
```

### JavaScript

```javascript
// 流式请求
const response = await fetch('/api/task/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ prompt: '列出 Python 文件' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  const lines = text.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      console.log(data);
    }
  }
}
```

### Python

```python
import httpx

# 同步请求
response = httpx.post('http://127.0.0.1:8000/api/task', json={
    'prompt': '列出所有 Python 文件'
})
print(response.json())

# 流式请求
with httpx.stream('POST', 'http://127.0.0.1:8000/api/task/stream', json={
    'prompt': '分析项目结构'
}) as response:
    for line in response.iter_lines():
        if line.startswith('data: '):
            print(line[6:])
```
