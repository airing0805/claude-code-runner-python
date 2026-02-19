# Agent 子代理管理

## 概述

监控和管理由主任务通过 Task 工具触发的子代理（Sub-Agent）。用户可以查看子代理状态、查看日志、终止失控的子代理。

## 需求

### 15.1 核心功能

| 功能 | 描述 |
|------|------|
| 子代理列表 | 查看所有子代理及状态 |
| 子代理详情 | 查看执行进度、工具使用、文件变更 |
| 终止子代理 | 手动终止运行中的子代理 |
| 日志流 | SSE 流式查看子代理执行日志 |
| 过滤排序 | 按状态过滤、按时长排序 |

### 15.2 状态类型

| 状态 | 描述 |
|------|------|
| running | 运行中 |
| completed | 已完成 |
| terminated | 已终止 |
| failed | 失败 |

### 15.3 API 设计

```json
# 获取子代理列表
GET /api/agents?status={status}&parent_task_id={task_id}&limit=50

Response: 200 OK
{
  "agents": [
    {
      "id": "sub_abc123",
      "parent_task_id": "task_xyz789",
      "status": "running",
      "prompt": "分析代码结构",
      "started_at": "2026-02-19T10:30:45Z",
      "progress": 45,
      "tools_used": ["Read", "Glob"],
      "files_changed": ["src/utils.py"]
    }
  ],
  "total": 15,
  "running_count": 3
}

# 获取子代理详情
GET /api/agents/{agent_id}

Response: 200 OK
{
  "id": "sub_abc123",
  "parent_task_id": "task_xyz789",
  "status": "running",
  "prompt": "分析代码结构",
  "started_at": "2026-02-19T10:30:45Z",
  "duration_ms": 154000,
  "progress": 45,
  "current_message": "正在分析 src/utils...",
  "tools_used": [...],
  "files_changed": [...],
  "cost_usd": 0.0234
}

# 终止子代理
POST /api/agents/{agent_id}/terminate

Response: 200 OK
{
  "success": true,
  "message": "子代理 sub_abc123 已终止"
}

# 获取日志流 (SSE)
GET /api/agents/{agent_id}/logs

data: {"type": "log", "content": "Reading file: src/utils.py"}
data: {"type": "tool_use", "tool_name": "Grep", "input": {...}}

# 获取文件变更
GET /api/agents/{agent_id}/files

# 获取工具使用历史
GET /api/agents/{agent_id}/tools
```

### 15.4 UI 设计

- 子代理列表表格（状态、ID、任务描述、进度、工具）
- 详情面板（基本信息、当前任务、工具历史、文件变更）
- 实时日志区域
- 终止按钮

### 15.5 优先级

| 功能 | 优先级 |
|------|--------|
| 子代理列表 API | P0 |
| 子代理详情 API | P0 |
| 终止子代理 API | P0 |
| 前端列表页 | P0 |
| 前端详情面板 | P0 |
| 日志流 API | P1 |
| 过滤功能 | P1 |

## 实现要点

- 在 Task 工具调用时创建 SubAgent 对象
- 内存中存储子代理状态
- 使用 SSE 推送日志
