# 会话管理 API 技术设计

## 概述

会话管理 API 提供项目会话的列表、详情查询功能，用于管理 Claude Code 执行的历史会话。

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

## 会话列表

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

---

## 消息历史

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

## 数据结构

### 会话消息内容块

消息内容支持多种类型的内容块：

| 类型 | 说明 |
|------|------|
| text | 文本内容 |
| tool_use | 工具调用请求 |
| tool_result | 工具执行结果 |
| thinking | 思考过程 |
| image | 图片内容 |

### 会话元数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 会话唯一 ID |
| title | string | 会话标题（首条用户消息） |
| timestamp | string | 创建时间 |
| message_count | int | 消息数量 |
| size | int | 会话数据大小（字节） |
