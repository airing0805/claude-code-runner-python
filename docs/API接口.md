# API 接口文档

> Claude Code Runner API 接口文档
> **版本**: v9.0.3
> **最后更新**: 2026-03-06

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [任务执行 API](#任务执行-api)
4. [会话历史 API](#会话历史-api)
5. [任务调度 API](#任务调度-api)
6. [其他 API](#其他-api)
7. [错误响应](#错误响应)
8. [使用示例](#使用示例)

---

## 概述

### Base URL

```
http://127.0.0.1:8000
```

### 认证方式

所有 API 支持可选的 OAuth2 认证。可通过 `Authorization` header 传递 Bearer token：

```
Authorization: Bearer <token>
```

### 请求头

| Header | 说明 |
|--------|------|
| Content-Type | application/json |
| Authorization | 可选，Bearer token |

---

## 快速开始

### cURL 快速示例

```bash
# 同步执行任务
curl -X POST http://127.0.0.1:8000/api/task \
  -H "Content-Type: application/json" \
  -d '{"prompt": "列出当前目录的文件"}'

# 流式执行任务（实时获取输出）
curl -X POST http://127.0.0.1:8000/api/task/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "分析项目结构"}'
```

### Python 快速示例

```python
import httpx

# 同步执行
response = httpx.post('http://127.0.0.1:8000/api/task', json={
    'prompt': '你好，请介绍一下自己'
})
print(response.json())
```

### JavaScript 快速示例

```javascript
// 同步请求
const response = await fetch('http://127.0.0.1:8000/api/task', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ prompt: '你好' })
});
const data = await response.json();
console.log(data);
```

---

## 任务执行 API

### 1. 同步执行任务

执行任务并等待结果返回。

**端点**: `POST /api/task`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 任务描述/提示词 |
| working_dir | string | 否 | 工作目录，默认为 "." |
| tools | array[string] | 否 | 允许使用的工具列表 |
| permission_mode | string | 否 | 权限模式："read" / "write" / "bypassPermissions" / "acceptEdits" |
| resume | string | 否 | 会话 ID，用于恢复会话 |

**请求示例**:

```bash
curl -X POST http://127.0.0.1:8000/api/task \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "列出当前目录的 Python 文件",
    "working_dir": "E:/workspace",
    "tools": ["Read", "Write", "Bash", "Glob"]
  }'
```

**响应示例**:

```json
{
  "success": true,
  "message": "任务执行完成",
  "session_id": "abc-123-def",
  "cost_usd": 0.0234,
  "duration_ms": 45000,
  "files_changed": ["src/main.py"],
  "tools_used": ["Bash", "Glob"]
}
```

---

### 2. 流式执行任务 (SSE)

执行任务并通过 Server-Sent Events 流式返回结果。

**端点**: `POST /api/task/stream`

**请求参数**: 同 [同步执行任务](#1-同步执行任务)

**请求示例**:

```bash
curl -X POST http://127.0.0.1:8000/api/task/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "分析项目结构"}'
```

**响应**: SSE 流，每条消息格式如下：

```json
{
  "type": "text|thinking|tool_use|tool_result|complete|error|question",
  "content": "消息内容",
  "timestamp": "2026-03-06T10:30:00",
  "tool_name": "Bash",
  "tool_input": {"command": "ls"},
  "session_id": "abc-123-def",
  "metadata": {},
  "question": {
    "question_id": "q-001",
    "question_text": "请选择...",
    "type": "selection",
    "options": [...]
  }
}
```

---

### 3. 提交问答答案

当任务执行过程中需要用户回答问题时，通过此接口提交答案。

**端点**: `POST /api/task/answer`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 是 | 会话 ID |
| question_id | string | 是 | 问题 ID |
| answer | string | 是 | 用户答案 |

**请求示例**:

```bash
curl -X POST http://127.0.0.1:8000/api/task/answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123-def",
    "question_id": "q-001",
    "answer": "选择选项 A"
  }'
```

**响应示例**:

```json
{
  "success": true,
  "message": "答案已提交",
  "session_id": "abc-123-def"
}
```

---

### 4. 获取会话状态

获取指定会话的当前状态。

**端点**: `GET /api/task/session/{session_id}/status`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话 ID |

**响应示例**:

```json
{
  "session_id": "abc-123-def",
  "is_waiting": false,
  "message_count": 15,
  "created_at": "2026-03-06T10:00:00",
  "working_dir": "E:/workspace"
}
```

---

### 5. 获取会话列表

获取所有活动会话的列表。

**端点**: `GET /api/task/sessions`

**响应示例**:

```json
{
  "sessions": [
    {
      "session_id": "abc-123-def",
      "is_waiting": true,
      "message_count": 10,
      "created_at": "2026-03-06T10:00:00"
    }
  ]
}
```

---

### 6. 创建新会话

创建新会话，可选择结束现有会话。

**端点**: `POST /api/task/new-session`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | string | 否 | 如果指定，只结束该会话；否则结束所有会话 |

**响应示例**:

```json
{
  "success": true,
  "message": "新会话已创建",
  "ended_sessions": ["abc-123-def"]
}
```

---

### 7. 检查会话是否存在

检查指定会话 ID 是否存在。

**端点**: `GET /api/task/session/{session_id}/exists`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话 ID |

**响应示例**:

```json
{
  "exists": true,
  "session_id": "abc-123-def"
}
```

---

## 会话历史 API

### 1. 获取会话列表

获取历史会话列表。

**端点**: `GET /api/session/sessions`

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| working_dir | string | "." | 工作目录 |

**响应示例**:

```json
{
  "sessions": [
    {
      "session_id": "abc-123-def",
      "timestamp": "2026-03-06T10:00:00",
      "message_count": 15,
      "tools": ["Bash", "Glob", "Read"]
    }
  ]
}
```

---

### 2. 获取项目列表

获取所有项目列表（分页）。

**端点**: `GET /api/session/projects`

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| limit | int | 20 | 每页数量 |

**响应示例**:

```json
{
  "projects": [
    {
      "encoded_name": "E--workspace-project",
      "path": "E:/workspace/project",
      "session_count": 10,
      "tools": ["Bash", "Glob", "Read", "Write"]
    }
  ],
  "total": 5,
  "page": 1,
  "limit": 20,
  "pages": 1
}
```

---

### 3. 获取项目会话列表

获取指定项目的会话列表（分页）。

**端点**: `GET /api/session/projects/{project_name}/sessions`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| project_name | string | 编码后的项目名 |

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| limit | int | 20 | 每页数量 |

---

### 4. 获取会话消息

获取指定会话的消息历史。

**端点**: `GET /api/session/sessions/{session_id}/messages`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话 ID |

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | int | 100 | 消息数量限制 |

**响应示例**:

```json
{
  "session_id": "abc-123-def",
  "messages": [
    {
      "type": "user",
      "content": "帮我分析代码",
      "timestamp": "2026-03-06T10:00:00"
    },
    {
      "type": "assistant",
      "content": "好的，我来分析...",
      "timestamp": "2026-03-06T10:00:01"
    }
  ]
}
```

---

### 5. 提交消息到会话

向指定会话提交新消息。

**端点**: `POST /api/session/sessions/{session_id}/messages`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话 ID |

**请求体**:

```json
{
  "content": "继续分析其他文件"
}
```

---

### 6. 获取项目问答记录

获取项目中的所有问答记录。

**端点**: `GET /api/session/projects/{project_name}/questions`

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| project_name | string | 编码后的项目名 |

---

## 任务调度 API

### 1. 创建任务

将任务添加到队列。

**端点**: `POST /api/scheduler/tasks`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 任务描述 |
| workspace | string | 否 | 工作目录 |
| timeout | int | 否 | 超时时间（毫秒），默认 600000 |
| auto_approve | bool | 否 | 是否自动批准工具操作 |
| allowed_tools | array[string] | 否 | 允许使用的工具列表 |

---

### 2. 获取任务队列

获取所有待执行任务。

**端点**: `GET /api/scheduler/tasks`

---

### 3. 创建定时任务

创建定时执行的任务。

**端点**: `POST /api/scheduler/scheduled-tasks`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 任务名称 |
| prompt | string | 是 | 任务描述 |
| cron | string | 是 | Cron 表达式 |
| workspace | string | 否 | 工作目录 |
| enabled | bool | 否 | 是否启用，默认 true |

---

### 4. 获取定时任务列表

获取所有定时任务。

**端点**: `GET /api/scheduler/scheduled-tasks`

---

### 5. 切换定时任务状态

启用或禁用定时任务。

**端点**: `POST /api/scheduler/scheduled-tasks/{task_id}/toggle`

---

### 6. 立即执行定时任务

手动触发定时任务执行。

**端点**: `POST /api/scheduler/scheduled-tasks/{task_id}/run`

---

### 7. 获取运行中任务

获取当前正在执行的任务。

**端点**: `GET /api/scheduler/tasks/running`

---

### 8. 获取已完成任务

获取已完成的任务列表（分页）。

**端点**: `GET /api/scheduler/tasks/completed`

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| limit | int | 20 | 每页数量 |

---

### 9. 获取失败任务

获取执行失败的任务列表（分页）。

**端点**: `GET /api/scheduler/tasks/failed`

---

### 10. 获取任务详情

获取指定任务的详细信息。

**端点**: `GET /api/scheduler/tasks/{task_id}`

---

### 11. 取消任务

取消正在执行的任务。

**端点**: `POST /api/scheduler/tasks/{task_id}/cancel`

---

### 12. 获取调度器状态

获取任务调度器的当前状态。

**端点**: `GET /api/scheduler/status`

**响应示例**:

```json
{
  "status": "running",
  "poll_interval": 10,
  "queue_count": 5,
  "scheduled_count": 3,
  "enabled_scheduled_count": 2,
  "running_count": 1
}
```

---

### 13. 启动调度器

启动任务调度器。

**端点**: `POST /api/scheduler/start`

---

### 14. 停止调度器

停止任务调度器。

**端点**: `POST /api/scheduler/stop`

---

### 15. 验证 Cron 表达式

验证 Cron 表达式是否有效。

**端点**: `POST /api/scheduler/validate-cron`

**请求体**:

```json
{
  "cron": "*/5 * * * *"
}
```

**响应示例**:

```json
{
  "valid": true,
  "next_run": "2026-03-06T10:05:00"
}
```

---

### 16. 获取 Cron 示例

获取常用 Cron 表达式示例。

**端点**: `GET /api/scheduler/cron-examples`

---

## 其他 API

### 1. 获取 Claude 版本

**端点**: `GET /api/claude/version`

### 2. 获取环境变量

**端点**: `GET /api/claude/env`

### 3. 获取 Claude 配置

**端点**: `GET /api/claude/config`

### 4. 获取工具列表

**端点**: `GET /api/status/tools`

### 5. 获取系统状态

**端点**: `GET /api/status`

### 6. 获取 MCP 服务器列表

**端点**: `GET /api/mcp/servers`

### 7. 获取技能列表

**端点**: `GET /api/skills`

### 8. 获取插件列表

**端点**: `GET /api/claude/plugins`

---

## 错误响应

### 错误格式

所有 API 错误响应格式如下：

```json
{
  "detail": "错误描述信息"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 认证失败 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 422 | 请求体验证失败 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

### 常见错误

| 错误 | 说明 |
|------|------|
| "prompt is required" | prompt 参数必填 |
| "Invalid session_id" | 无效的会话 ID |
| "Session not found" | 会话不存在 |
| "Session is not waiting" | 会话未在等待状态 |
| "Workspace not allowed" | 工作目录不在允许范围内 |
| "Task not found" | 任务不存在 |
| "Scheduler is not running" | 调度器未运行 |
| "Invalid cron expression" | Cron 表达式无效 |

---

## 使用示例

### Python 示例

#### 1. 同步任务执行

```python
import httpx

def execute_task(prompt: str, working_dir: str = ".") -> dict:
    """同步执行任务"""
    response = httpx.post(
        'http://127.0.0.1:8000/api/task',
        json={
            "prompt": prompt,
            "working_dir": working_dir,
            "tools": ["Read", "Write", "Bash", "Glob", "Grep"]
        },
        timeout=300.0  # 5分钟超时
    )
    response.raise_for_status()
    return response.json()

# 使用示例
result = execute_task("列出当前目录的 Python 文件", "E:/workspace/myproject")
print(f"会话ID: {result['session_id']}")
print(f"消耗费用: ${result['cost_usd']:.4f}")
print(f"执行时长: {result['duration_ms']}ms")
print(f"结果: {result['message']}")
```

#### 2. 流式任务执行

```python
import httpx

def stream_task(prompt: str):
    """流式执行任务，实时处理输出"""
    with httpx.stream(
        'POST',
        'http://127.0.0.1:8000/api/task/stream',
        json={"prompt": prompt},
        timeout=300.0
    ) as response:
        for line in response.iter_lines():
            if line.startswith('data: '):
                data = line[6:]  # 去掉 "data: " 前缀
                if data.strip() == '[DONE]':
                    break
                message = eval(data)  # 解析 JSON 消息
                handle_message(message)

def handle_message(message: dict):
    """处理不同类型的消息"""
    msg_type = message.get('type')
    if msg_type == 'text':
        print(f"[文本] {message['content']}")
    elif msg_type == 'thinking':
        print(f"[思考] {message['content']}")
    elif msg_type == 'tool_use':
        print(f"[工具] 调用 {message['tool_name']}: {message['tool_input']}")
    elif msg_type == 'tool_result':
        print(f"[结果] {message['content'][:100]}...")
    elif msg_type == 'complete':
        print(f"[完成] 费用: ${message['metadata']['cost_usd']:.4f}")
    elif msg_type == 'error':
        print(f"[错误] {message['content']}")
    elif msg_type == 'question':
        # 处理交互式问答
        question = message['question']
        print(f"[问答] {question['question_text']}")
        print(f"选项: {question['options']}")

# 使用示例
stream_task("分析项目代码结构")
```

#### 3. 会话管理

```python
import httpx

def create_session() -> dict:
    """创建新会话"""
    response = httpx.post(
        'http://127.0.0.1:8000/api/task/new-session',
        json={}
    )
    return response.json()

def get_sessions() -> list:
    """获取活动会话列表"""
    response = httpx.get('http://127.0.0.1:8000/api/task/sessions')
    return response.json()['sessions']

def get_session_status(session_id: str) -> dict:
    """获取会话状态"""
    response = httpx.get(
        f'http://127.0.0.1:8000/api/task/session/{session_id}/status'
    )
    return response.json()

def resume_session(session_id: str, prompt: str) -> dict:
    """恢复并继续会话"""
    response = httpx.post(
        'http://127.0.0.1:8000/api/task',
        json={
            "prompt": prompt,
            "resume": session_id
        }
    )
    return response.json()

# 使用示例
# 创建新会话
new_session = create_session()
print(f"新会话ID: {new_session['session_id']}")

# 获取所有活动会话
sessions = get_sessions()
for s in sessions:
    print(f"会话: {s['session_id']}, 消息数: {s['message_count']}")
```

#### 4. 提交问答答案

```python
import httpx

def submit_answer(session_id: str, question_id: str, answer: str) -> dict:
    """提交问答答案"""
    response = httpx.post(
        'http://127.0.0.1:8000/api/task/answer',
        json={
            "session_id": session_id,
            "question_id": question_id,
            "answer": answer
        }
    )
    return response.json()

# 单选答案
result = submit_answer("abc-123-def", "q-001", "option_a")

# 多选答案（数组格式）
result = submit_answer("abc-123-def", "q-002", ["option_a", "option_c"])
```

#### 5. 任务调度

```python
import httpx

def create_task(prompt: str, workspace: str = ".") -> dict:
    """创建队列任务"""
    response = httpx.post(
        'http://127.0.0.1:8000/api/scheduler/tasks',
        json={
            "prompt": prompt,
            "workspace": workspace,
            "timeout": 600000,
            "auto_approve": False,
            "allowed_tools": ["Read", "Write", "Bash", "Glob"]
        }
    )
    return response.json()

def create_scheduled_task(name: str, prompt: str, cron: str) -> dict:
    """创建定时任务"""
    response = httpx.post(
        'http://127.0.0.1:8000/api/scheduler/scheduled-tasks',
        json={
            "name": name,
            "prompt": prompt,
            "cron": cron,  # 例如: "0 9 * * *" 每天9点执行
            "workspace": "E:/workspace",
            "enabled": True
        }
    )
    return response.json()

def get_scheduler_status() -> dict:
    """获取调度器状态"""
    response = httpx.get('http://127.0.0.1:8000/api/scheduler/status')
    return response.json()

# 使用示例
# 创建定时任务
task = create_scheduled_task(
    name="每日报告",
    prompt="生成项目报告",
    cron="0 9 * * *"
)
print(f"定时任务ID: {task['id']}")

# 获取调度器状态
status = get_scheduler_status()
print(f"队列任务数: {status['queue_count']}")
print(f"运行中任务: {status['running_count']}")
```

#### 6. 会话历史查询

```python
import httpx

def get_projects(page: int = 1, limit: int = 20) -> dict:
    """获取项目列表"""
    response = httpx.get(
        'http://127.0.0.1:8000/api/session/projects',
        params={"page": page, "limit": limit}
    )
    return response.json()

def get_project_sessions(project_name: str) -> list:
    """获取项目会话列表"""
    response = httpx.get(
        f'http://127.0.0.1:8000/api/session/projects/{project_name}/sessions'
    )
    return response.json()['sessions']

def get_session_messages(session_id: str, limit: int = 100) -> list:
    """获取会话消息历史"""
    response = httpx.get(
        f'http://127.0.0.1:8000/api/session/sessions/{session_id}/messages',
        params={"limit": limit}
    )
    return response.json()['messages']

def continue_session(session_id: str, message: str) -> dict:
    """向历史会话发送消息"""
    response = httpx.post(
        f'http://127.0.0.1:8000/api/session/sessions/{session_id}/messages',
        json={"content": message}
    )
    return response.json()

# 使用示例
projects = get_projects()
print(f"项目总数: {projects['total']}")

for project in projects['projects']:
    print(f"- {project['path']}: {project['session_count']} 个会话")
```

---

### JavaScript 示例

#### 1. 同步任务执行

```javascript
async function executeTask(prompt, options = {}) {
  const response = await fetch('http://127.0.0.1:8000/api/task', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      prompt,
      working_dir: options.working_dir || '.',
      tools: options.tools || ['Read', 'Write', 'Bash', 'Glob', 'Grep']
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }

  return await response.json();
}

// 使用示例
const result = await executeTask('列出当前目录的 Python 文件', {
  working_dir: 'E:/workspace/myproject'
});

console.log(`会话ID: ${result.session_id}`);
console.log(`消耗费用: $${result.cost_usd.toFixed(4)}`);
console.log(`执行时长: ${result.duration_ms}ms`);
console.log(`结果: ${result.message}`);
```

#### 2. 流式任务执行

```javascript
async function* streamTask(prompt) {
  const response = await fetch('http://127.0.0.1:8000/api/task/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ prompt })
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
        const data = line.slice(6);
        if (data === '[DONE]') return;
        yield JSON.parse(data);
      }
    }
  }
}

// 使用示例
for await (const message of streamTask('分析项目代码结构')) {
  switch (message.type) {
    case 'text':
      console.log(`[文本] ${message.content}`);
      break;
    case 'thinking':
      console.log(`[思考] ${message.content}`);
      break;
    case 'tool_use':
      console.log(`[工具] 调用 ${message.tool_name}`);
      break;
    case 'tool_result':
      console.log(`[结果] ${message.content?.substring(0, 100)}...`);
      break;
    case 'complete':
      console.log(`[完成] 费用: $${message.metadata.cost_usd.toFixed(4)}`);
      break;
    case 'error':
      console.log(`[错误] ${message.content}`);
      break;
    case 'question':
      console.log(`[问答] ${message.question.question_text}`);
      console.log(`选项: ${message.question.options.join(', ')}`);
      break;
  }
}
```

#### 3. 会话管理

```javascript
async function createSession() {
  const response = await fetch('http://127.0.0.1:8000/api/task/new-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  });
  return await response.json();
}

async function getSessions() {
  const response = await fetch('http://127.0.0.1:8000/api/task/sessions');
  const data = await response.json();
  return data.sessions;
}

async function getSessionStatus(sessionId) {
  const response = await fetch(
    `http://127.0.0.1:8000/api/task/session/${sessionId}/status`
  );
  return await response.json();
}

async function checkSessionExists(sessionId) {
  const response = await fetch(
    `http://127.0.0.1:8000/api/task/session/${sessionId}/exists`
  );
  return await response.json();
}

// 使用示例
const newSession = await createSession();
console.log(`新会话ID: ${newSession.session_id}`);

const sessions = await getSessions();
for (const session of sessions) {
  console.log(`会话: ${session.session_id}, 消息数: ${session.message_count}`);
}
```

#### 4. 提交问答答案

```javascript
async function submitAnswer(sessionId, questionId, answer) {
  const response = await fetch('http://127.0.0.1:8000/api/task/answer', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      session_id: sessionId,
      question_id: questionId,
      answer  // 字符串或数组
    })
  });
  return await response.json();
}

// 单选答案
const result = await submitAnswer('abc-123-def', 'q-001', 'option_a');

// 多选答案
const result2 = await submitAnswer('abc-123-def', 'q-002', ['option_a', 'option_c']);
```

#### 5. 任务调度

```javascript
async function createTask(prompt, options = {}) {
  const response = await fetch('http://127.0.0.1:8000/api/scheduler/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      workspace: options.workspace || '.',
      timeout: options.timeout || 600000,
      auto_approve: options.auto_approve || false,
      allowed_tools: options.allowed_tools || ['Read', 'Write', 'Bash']
    })
  });
  return await response.json();
}

async function createScheduledTask(name, prompt, cron) {
  const response = await fetch(
    'http://127.0.0.1:8000/api/scheduler/scheduled-tasks',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        prompt,
        cron,
        workspace: 'E:/workspace',
        enabled: true
      })
    }
  );
  return await response.json();
}

async function getSchedulerStatus() {
  const response = await fetch('http://127.0.0.1:8000/api/scheduler/status');
  return await response.json();
}

async function getScheduledTasks() {
  const response = await fetch(
    'http://127.0.0.1:8000/api/scheduler/scheduled-tasks'
  );
  return await response.json();
}

// 使用示例
const task = await createScheduledTask(
  '每日报告',
  '生成项目报告',
  '0 9 * * *'
);
console.log(`定时任务ID: ${task.id}`);

const status = await getSchedulerStatus();
console.log(`队列任务数: ${status.queue_count}`);
```

#### 6. 会话历史查询

```javascript
async function getProjects(page = 1, limit = 20) {
  const response = await fetch(
    `http://127.0.0.1:8000/api/session/projects?page=${page}&limit=${limit}`
  );
  return await response.json();
}

async function getProjectSessions(projectName) {
  const response = await fetch(
    `http://127.0.0.1:8000/api/session/projects/${projectName}/sessions`
  );
  const data = await response.json();
  return data.sessions;
}

async function getSessionMessages(sessionId, limit = 100) {
  const response = await fetch(
    `http://127.0.0.1:8000/api/session/sessions/${sessionId}/messages?limit=${limit}`
  );
  const data = await response.json();
  return data.messages;
}

// 使用示例
const projects = await getProjects();
console.log(`项目总数: ${projects.total}`);

for (const project of projects.projects) {
  console.log(`${project.path}: ${project.session_count} 个会话`);
}
```

---

### cURL 示例

#### 1. 同步任务执行

```bash
# 基础同步任务
curl -X POST http://127.0.0.1:8000/api/task \
  -H "Content-Type: application/json" \
  -d '{"prompt": "列出当前目录的文件"}'

# 指定工作目录和工具
curl -X POST http://127.0.0.1:8000/api/task \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "分析项目代码结构",
    "working_dir": "E:/workspace/myproject",
    "tools": ["Read", "Write", "Bash", "Glob", "Grep"]
  }'

# 恢复指定会话
curl -X POST http://127.0.0.1:8000/api/task \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "继续分析其他模块",
    "resume": "abc-123-def"
  }'
```

#### 2. 流式任务执行

```bash
# 流式执行（实时输出）
curl -X POST http://127.0.0.1:8000/api/task/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "分析项目结构"}'

# 使用 jq 处理流式输出
curl -s -X POST http://127.0.0.1:8000/api/task/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "列出所有 Python 文件"}' | \
  while read -r line; do
    if [[ $line == data:\ * ]]; then
      echo "$line" | cut -d' ' -f2- | jq -r '.content // empty'
    fi
  done
```

#### 3. 会话管理

```bash
# 创建新会话
curl -X POST http://127.0.0.1:8000/api/task/new-session \
  -H "Content-Type: application/json" \
  -d '{}'

# 获取活动会话列表
curl -X GET http://127.0.0.1:8000/api/task/sessions

# 获取会话状态
curl -X GET http://127.0.0.1:8000/api/task/session/abc-123-def/status

# 检查会话是否存在
curl -X GET http://127.0.0.1:8000/api/task/session/abc-123-def/exists
```

#### 4. 提交问答答案

```bash
# 提交单选答案
curl -X POST http://127.0.0.1:8000/api/task/answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123-def",
    "question_id": "q-001",
    "answer": "option_a"
  }'

# 提交多选答案
curl -X POST http://127.0.0.1:8000/api/task/answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123-def",
    "question_id": "q-002",
    "answer": ["option_a", "option_c"]
  }'
```

#### 5. 任务调度

```bash
# 创建队列任务
curl -X POST http://127.0.0.1:8000/api/scheduler/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "生成项目报告",
    "workspace": "E:/workspace",
    "timeout": 600000,
    "auto_approve": false,
    "allowed_tools": ["Read", "Write", "Bash"]
  }'

# 获取任务队列
curl -X GET http://127.0.0.1:8000/api/scheduler/tasks

# 获取运行中的任务
curl -X GET http://127.0.0.1:8000/api/scheduler/tasks/running

# 获取已完成任务
curl -X GET "http://127.0.0.1:8000/api/scheduler/tasks/completed?page=1&limit=20"

# 创建定时任务
curl -X POST http://127.0.0.1:8000/api/scheduler/scheduled-tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "每日报告生成",
    "prompt": "生成项目报告并发送到邮箱",
    "cron": "0 9 * * *",
    "workspace": "E:/workspace",
    "enabled": true
  }'

# 获取定时任务列表
curl -X GET http://127.0.0.1:8000/api/scheduler/scheduled-tasks

# 切换定时任务状态
curl -X POST http://127.0.0.1:8000/api/scheduler/scheduled-tasks/task-001/toggle

# 立即执行定时任务
curl -X POST http://127.0.0.1:8000/api/scheduler/scheduled-tasks/task-001/run

# 取消任务
curl -X POST http://127.0.0.1:8000/api/scheduler/tasks/task-001/cancel

# 获取调度器状态
curl -X GET http://127.0.0.1:8000/api/scheduler/status

# 验证 Cron 表达式
curl -X POST http://127.0.0.1:8000/api/scheduler/validate-cron \
  -H "Content-Type: application/json" \
  -d '{"cron": "*/5 * * * *"}'

# 获取 Cron 示例
curl -X GET http://127.0.0.1:8000/api/scheduler/cron-examples

# 启动调度器
curl -X POST http://127.0.0.1:8000/api/scheduler/start

# 停止调度器
curl -X POST http://127.0.0.1:8000/api/scheduler/stop
```

#### 6. 会话历史查询

```bash
# 获取项目列表
curl -X GET "http://127.0.0.1:8000/api/session/projects?page=1&limit=20"

# 获取项目会话列表
curl -X GET "http://127.0.0.1:8000/api/session/projects/E--workspace-myproject/sessions?page=1&limit=20"

# 获取会话消息
curl -X GET "http://127.0.0.1:8000/api/session/sessions/abc-123-def/messages?limit=100"

# 向会话发送消息（继续会话）
curl -X POST http://127.0.0.1:8000/api/session/sessions/abc-123-def/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "继续分析其他文件"}'

# 获取项目问答记录
curl -X GET http://127.0.0.1:8000/api/session/projects/E--workspace-myproject/questions
```

#### 7. 其他 API

```bash
# 获取 Claude 版本
curl -X GET http://127.0.0.1:8000/api/claude/version

# 获取环境变量
curl -X GET http://127.0.0.1:8000/api/claude/env

# 获取 Claude 配置
curl -X GET http://127.0.0.1:8000/api/claude/config

# 获取工具列表
curl -X GET http://127.0.0.1:8000/api/status/tools

# 获取系统状态
curl -X GET http://127.0.0.1:8000/api/status

# 获取 MCP 服务器列表
curl -X GET http://127.0.0.1:8000/api/mcp/servers

# 获取技能列表
curl -X GET http://127.0.0.1:8000/api/skills

# 获取插件列表
curl -X GET http://127.0.0.1:8000/api/claude/plugins
```

---

**文档版本**: v9.0.3
**最后更新**: 2026-03-06
