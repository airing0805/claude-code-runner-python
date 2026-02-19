# Claude Code Runner API 文档

## 基础信息

- **Base URL**: `http://127.0.0.1:8000`
- **Content-Type**: `application/json`

---

## 页面路由

### GET /

返回 Web 界面主页。

**响应**: HTML 页面

---

## 任务执行

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

## 状态查询

### GET /api/status

获取服务状态。

**响应**:

```json
{
  "status": "running",
  "working_dir": "/path/to/project",
  "active_tasks": 0
}
```

### GET /api/tools

获取可用工具列表。

**响应**:

```json
{
  "tools": [
    {"name": "Read", "description": "读取文件内容"},
    {"name": "Write", "description": "创建新文件"},
    {"name": "Edit", "description": "编辑现有文件"},
    {"name": "Bash", "description": "运行终端命令"},
    {"name": "Glob", "description": "按模式查找文件"},
    {"name": "Grep", "description": "搜索文件内容"},
    {"name": "WebSearch", "description": "搜索网络"},
    {"name": "WebFetch", "description": "获取网页内容"},
    {"name": "Task", "description": "启动子代理任务"}
  ]
}
```

---

## API 拆分架构 (v0.2.1+)

```
app/
├── main.py              # 应用入口
└── routers/
    ├── task.py          # 任务执行 API
    ├── session.py       # 会话历史 API
    └── status.py        # 状态和工具 API
```

---

## 项目列表

### GET /api/projects

获取所有项目列表（含工具汇总）。

**响应**:

```json
{
  "projects": [
    {
      "encoded_name": "E--workspaces-2026-python",
      "path": "E:\\workspaces_2026_python\\project",
      "session_count": 5,
      "tools": ["Read", "Write", "Edit", "Bash"]
    }
  ]
}
```

---

## 会话历史

### GET /api/projects

获取所有项目列表。

**响应**:

```json
{
  "projects": [
    {
      "encoded_name": "E--workspaces-2026-python-claude-code-runner",
      "path": "E:\\workspaces_2026_python\\claude-code-runner",
      "session_count": 5
    }
  ]
}
```

### GET /api/projects/{project_name}/sessions

获取指定项目的会话列表。

**参数**:
- `project_name`: 项目编码名称（URL 编码）

**响应**:

```json
{
  "project_name": "E--workspaces-2026-python-claude-code-runner",
  "project_path": "E:\\workspaces_2026_python\\claude-code-runner",
  "sessions": [
    {
      "id": "abc123def456",
      "title": "列出当前目录下所有 Python 文件",
      "timestamp": "2026-02-18T10:00:00",
      "message_count": 10,
      "size": 5000
    }
  ]
}
```

### GET /api/sessions/{session_id}/messages

获取会话的消息历史。

**参数**:
- `session_id`: 会话 ID

**响应** (v0.2.1+, v0.2.11+ 内容块扩展):

```json
{
  "session_id": "abc123...",
  "project_path": "E:\\workspaces_2026_python\\project",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "任务描述"
        },
        {
          "type": "tool_result",
          "tool_use_id": "call_xxx",
          "content": "工具返回结果",
          "is_error": false
        }
      ],
      "timestamp": "2024-01-01T00:00:00Z",
      "uuid": "消息UUID"
    },
    {
      "role": "assistant",
      "content": [
        {
          "type": "thinking",
          "thinking": "思考过程内容..."
        },
        {
          "type": "text",
          "text": "AI 响应文本"
        },
        {
          "type": "tool_use",
          "tool_name": "Read",
          "tool_input": {"file_path": "xxx"},
          "tool_use_id": "call_yyy"
        }
      ],
      "timestamp": "2024-01-01T00:00:01Z",
      "uuid": "消息UUID",
      "stop_reason": "tool_use",
      "usage": {
        "input_tokens": 1500,
        "output_tokens": 300
      }
    }
  ]
}
```

---

## 错误响应

所有 API 在出错时返回统一格式：

```json
{
  "detail": "错误描述信息"
}
```

常见错误码：

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

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
