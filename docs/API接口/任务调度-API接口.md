# 任务调度 API 文档

本文档描述任务调度系统的 REST API 接口。

## 概述

任务调度系统提供以下核心功能：
- 任务队列管理：添加、查询、删除、清空待执行任务
- 定时任务管理：创建、修改、删除、启用/禁用定时任务
- 任务状态查询：查询运行中、已完成、失败任务
- 调度器控制：启动/停止调度器，查看调度器状态

## 基础信息

| 项目 | 值 |
|------|-----|
| 基础路径 | `/api` |
| 认证方式 | 与主 API 一致 |
| 响应格式 | JSON |

## 通用响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

### 错误响应

```json
{
  "success": false,
  "error": "错误信息",
  "code": "ERROR_CODE"
}
```

### 分页响应

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "limit": 20,
  "pages": 5
}
```

---

## 任务队列管理

### 添加任务到队列

**POST** `/api/tasks`

添加一个新的任务到执行队列。

**请求体**

```json
{
  "prompt": "任务描述/提示词",
  "workspace": "./workspace",
  "timeout": 600000,
  "auto_approve": false,
  "allowed_tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| prompt | string | 是 | - | 任务描述/提示词 |
| workspace | string | 否 | "." | 工作目录 |
| timeout | integer | 否 | 600000 | 超时时间（毫秒） |
| auto_approve | boolean | 否 | false | 是否自动批准工具操作 |
| allowed_tools | array[string] | 否 | null | 允许使用的工具列表，null 表示全部允许 |

**响应** `201 Created`

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "prompt": "任务描述",
    "workspace": "./workspace",
    "timeout": 600000,
    "auto_approve": false,
    "allowed_tools": null,
    "created_at": "2024-01-01T00:00:00",
    "started_at": null,
    "finished_at": null,
    "retries": 0,
    "status": "pending",
    "scheduled": false,
    "scheduled_id": null,
    "result": null,
    "error": null,
    "files_changed": [],
    "tools_used": [],
    "cost_usd": null,
    "duration_ms": null
  },
  "message": "任务已添加到队列"
}
```

### 获取队列列表

**GET** `/api/tasks`

获取所有待执行的任务队列。

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| 无 | - | - | - |

**响应** `200 OK`

```json
{
  "success": true,
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "prompt": "任务描述",
      "workspace": "./workspace",
      "timeout": 600000,
      "auto_approve": false,
      "allowed_tools": null,
      "created_at": "2024-01-01T00:00:00",
      "started_at": null,
      "finished_at": null,
      "retries": 0,
      "status": "pending",
      "scheduled": false,
      "scheduled_id": null,
      "result": null,
      "error": null,
      "files_changed": [],
      "tools_used": [],
      "cost_usd": null,
      "duration_ms": null
    }
  ],
  "total": 1
}
```

### 删除队列中的任务

**DELETE** `/api/tasks/{id}`

从队列中删除指定的任务。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| id | string | 任务 ID |

**响应** `200 OK`

```json
{
  "success": true,
  "message": "任务已从队列中删除"
}
```

### 清空队列

**DELETE** `/api/tasks/clear`

清空所有待执行的任务。

**响应** `200 OK`

```json
{
  "success": true,
  "message": "队列已清空"
}
```

---

## 定时任务管理

### 创建定时任务

**POST** `/api/scheduled-tasks`

创建一个新的定时任务。

**请求体**

```json
{
  "name": "每日代码审查",
  "prompt": "请审查项目的代码质量",
  "cron": "0 9 * * *",
  "workspace": "./workspace",
  "timeout": 600000,
  "auto_approve": false,
  "allowed_tools": ["Read", "Glob", "Grep"],
  "enabled": true
}
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| name | string | 是 | - | 任务名称 |
| prompt | string | 是 | - | 任务描述/提示词 |
| cron | string | 是 | - | Cron 表达式 |
| workspace | string | 否 | "." | 工作目录 |
| timeout | integer | 否 | 600000 | 超时时间（毫秒） |
| auto_approve | boolean | 否 | false | 是否自动批准工具操作 |
| allowed_tools | array[string] | 否 | null | 允许使用的工具列表 |
| enabled | boolean | 否 | true | 是否启用 |

**Cron 表达式格式**

- 标准 5 位格式：`分 时 日 月 周`
- 扩展 6 位格式：`秒 分 时 日 月 周`

示例：
- `0 9 * * *` - 每天 9:00 执行
- `0 9 * * 1-5` - 工作日 9:00 执行
- `*/15 * * * *` - 每 15 分钟执行

**响应** `201 Created`

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "每日代码审查",
    "prompt": "请审查项目的代码质量",
    "cron": "0 9 * * *",
    "workspace": "./workspace",
    "timeout": 600000,
    "auto_approve": false,
    "allowed_tools": ["Read", "Glob", "Grep"],
    "enabled": true,
    "last_run": null,
    "next_run": "2024-01-02T09:00:00",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "run_count": 0
  },
  "message": "定时任务已创建"
}
```

### 获取定时任务列表

**GET** `/api/scheduled-tasks`

获取所有定时任务。

**响应** `200 OK`

```json
{
  "success": true,
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "每日代码审查",
      "prompt": "请审查项目的代码质量",
      "cron": "0 9 * * *",
      "workspace": "./workspace",
      "timeout": 600000,
      "auto_approve": false,
      "allowed_tools": ["Read", "Glob", "Grep"],
      "enabled": true,
      "last_run": "2024-01-01T09:00:00",
      "next_run": "2024-01-02T09:00:00",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00",
      "run_count": 1
    }
  ],
  "total": 1
}
```

### 更新定时任务

**PATCH** `/api/scheduled-tasks/{id}`

更新指定定时任务的配置。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| id | string | 定时任务 ID |

**请求体**

```json
{
  "name": "新的任务名称",
  "prompt": "新的任务描述",
  "cron": "0 10 * * *",
  "workspace": "./new-workspace",
  "timeout": 900000,
  "auto_approve": true,
  "allowed_tools": ["Read", "Write", "Edit"],
  "enabled": false
}
```

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "新的任务名称",
    "prompt": "新的任务描述",
    "cron": "0 10 * * *",
    "workspace": "./new-workspace",
    "timeout": 900000,
    "auto_approve": true,
    "allowed_tools": ["Read", "Write", "Edit"],
    "enabled": false,
    "last_run": "2024-01-01T09:00:00",
    "next_run": null,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T10:00:00",
    "run_count": 1
  },
  "message": "定时任务已更新"
}
```

### 删除定时任务

**DELETE** `/api/scheduled-tasks/{id}`

删除指定的定时任务。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| id | string | 定时任务 ID |

**响应** `200 OK`

```json
{
  "success": true,
  "message": "定时任务已删除"
}
```

### 启用/禁用定时任务

**POST** `/api/scheduled-tasks/{id}/toggle`

切换定时任务的启用/禁用状态。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| id | string | 定时任务 ID |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "enabled": false,
    "next_run": null
  },
  "message": "定时任务已禁用"
}
```

### 立即执行定时任务

**POST** `/api/scheduled-tasks/{id}/run`

立即执行指定的定时任务（将任务添加到队列）。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| id | string | 定时任务 ID |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "task_id": "660e8400-e29b-41d4-a716-446655440001"
  },
  "message": "任务已添加到队列"
}
```

---

## 任务状态查询

### 获取运行中任务

**GET** `/api/tasks/running`

获取当前正在执行的任务。

**响应** `200 OK`

```json
{
  "success": true,
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "prompt": "任务描述",
      "workspace": "./workspace",
      "timeout": 600000,
      "auto_approve": false,
      "allowed_tools": null,
      "created_at": "2024-01-01T00:00:00",
      "started_at": "2024-01-01T00:00:10",
      "finished_at": null,
      "retries": 0,
      "status": "running",
      "scheduled": false,
      "scheduled_id": null,
      "result": null,
      "error": null,
      "files_changed": ["file1.py"],
      "tools_used": ["Read", "Glob"],
      "cost_usd": null,
      "duration_ms": null
    }
  ],
  "total": 1
}
```

### 获取已完成任务

**GET** `/api/tasks/completed`

获取已完成的任务历史（支持分页）。

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码 |
| limit | integer | 20 | 每页数量（最大 100） |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "prompt": "任务描述",
        "workspace": "./workspace",
        "timeout": 600000,
        "auto_approve": false,
        "allowed_tools": null,
        "created_at": "2024-01-01T00:00:00",
        "started_at": "2024-01-01T00:00:10",
        "finished_at": "2024-01-01T00:05:00",
        "retries": 0,
        "status": "completed",
        "scheduled": false,
        "scheduled_id": null,
        "result": { "message": "任务完成" },
        "error": null,
        "files_changed": ["file1.py", "file2.py"],
        "tools_used": ["Read", "Write", "Glob", "Grep"],
        "cost_usd": 0.05,
        "duration_ms": 300000
      }
    ],
    "total": 100,
    "page": 1,
    "limit": 20,
    "pages": 5
  }
}
```

### 获取失败任务

**GET** `/api/tasks/failed`

获取失败的任务历史（支持分页）。

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码 |
| limit | integer | 20 | 每页数量（最大 100） |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "prompt": "任务描述",
        "workspace": "./workspace",
        "timeout": 600000,
        "auto_approve": false,
        "allowed_tools": null,
        "created_at": "2024-01-01T00:00:00",
        "started_at": "2024-01-01T00:00:10",
        "finished_at": "2024-01-01T00:01:00",
        "retries": 2,
        "status": "failed",
        "scheduled": false,
        "scheduled_id": null,
        "result": null,
        "error": "Task execution timeout",
        "files_changed": [],
        "tools_used": ["Read", "Glob"],
        "cost_usd": 0.02,
        "duration_ms": 60000
      }
    ],
    "total": 10,
    "page": 1,
    "limit": 20,
    "pages": 1
  }
}
```

### 获取任务详情

**GET** `/api/tasks/{id}`

获取指定任务的详细信息（可在任意状态查询）。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| id | string | 任务 ID |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "prompt": "任务描述",
    "workspace": "./workspace",
    "timeout": 600000,
    "auto_approve": false,
    "allowed_tools": null,
    "created_at": "2024-01-01T00:00:00",
    "started_at": "2024-01-01T00:00:10",
    "finished_at": "2024-01-01T00:05:00",
    "retries": 0,
    "status": "completed",
    "scheduled": true,
    "scheduled_id": "770e8400-e29b-41d4-a716-446655440000",
    "result": { "message": "任务完成", "summary": "分析了 5 个文件" },
    "error": null,
    "files_changed": ["file1.py", "file2.py"],
    "tools_used": ["Read", "Write", "Glob", "Grep"],
    "cost_usd": 0.05,
    "duration_ms": 300000
  }
}
```

---

## 调度器控制

### 获取调度器状态

**GET** `/api/scheduler/status`

获取调度器的当前状态。

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "status": "running",
    "poll_interval": 10,
    "queue_count": 5,
    "scheduled_count": 3,
    "enabled_scheduled_count": 2,
    "running_count": 1,
    "is_executing": true,
    "current_task_id": "550e8400-e29b-41d4-a716-446655440000",
    "updated_at": "2024-01-01T12:00:00"
  }
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 调度器状态：`stopped`、`running`、`starting`、`stopping` |
| poll_interval | integer | 轮询间隔（秒） |
| queue_count | integer | 队列中的任务数量 |
| scheduled_count | integer | 定时任务总数 |
| enabled_scheduled_count | integer | 已启用的定时任务数量 |
| running_count | integer | 当前运行中的任务数量 |
| is_executing | boolean | 是否正在执行任务 |
| current_task_id | string \| null | 当前执行中的任务 ID |
| updated_at | string | 状态更新时间 |

**调度器状态说明**

| 状态 | 说明 |
|------|------|
| stopped | 调度器已停止 |
| running | 调度器正在运行 |
| starting | 调度器正在启动 |
| stopping | 调度器正在停止 |

### 启动调度器

**POST** `/api/scheduler/start`

启动任务调度器。

**响应** `200 OK`

```json
{
  "success": true,
  "message": "调度器已启动"
}
```

### 停止调度器

**POST** `/api/scheduler/stop`

停止任务调度器。

**响应** `200 OK`

```json
{
  "success": true,
  "message": "调度器已停止"
}
```

---

## Cron 表达式验证

### 验证 Cron 表达式

**POST** `/api/scheduler/validate-cron`

验证 Cron 表达式的有效性。

**请求体**

```json
{
  "cron": "0 9 * * *"
}
```

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "valid": true,
    "next_runs": [
      "2024-01-02T09:00:00",
      "2024-01-03T09:00:00",
      "2024-01-04T09:00:00",
      "2024-01-05T09:00:00",
      "2024-01-06T09:00:00"
    ]
  }
}
```

**无效表达式响应**

```json
{
  "success": false,
  "error": "无效的 Cron 表达式：秒数超出范围 (0-59)",
  "code": "INVALID_CRON"
}
```

### 获取常用 Cron 表达式示例

**GET** `/api/scheduler/cron-examples`

获取常用 Cron 表达式示例。

**响应** `200 OK`

```json
{
  "success": true,
  "data": [
    {
      "expression": "*/5 * * * *",
      "description": "每 5 分钟执行",
      "next_run_example": "2024-01-01T00:05:00"
    },
    {
      "expression": "0 * * * *",
      "description": "每小时执行",
      "next_run_example": "2024-01-01T01:00:00"
    },
    {
      "expression": "0 9 * * *",
      "description": "每天 9:00 执行",
      "next_run_example": "2024-01-02T09:00:00"
    },
    {
      "expression": "0 9 * * 1-5",
      "description": "工作日 9:00 执行",
      "next_run_example": "2024-01-02T09:00:00"
    },
    {
      "expression": "0 9 * * 0,6",
      "description": "周末 9:00 执行",
      "next_run_example": "2024-01-06T09:00:00"
    },
    {
      "expression": "0 0 1 * *",
      "description": "每月 1 日执行",
      "next_run_example": "2024-02-01T00:00:00"
    }
  ]
}
```

---

## 错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| TASK_NOT_FOUND | 404 | 任务不存在 |
| INVALID_CRON | 400 | Cron 表达式无效 |
| SCHEDULED_TASK_NOT_FOUND | 404 | 定时任务不存在 |
| SCHEDULER_NOT_RUNNING | 400 | 调度器未运行 |
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| STORAGE_ERROR | 500 | 存储操作失败 |

---

## 任务状态说明

| 状态 | 说明 |
|------|------|
| pending | 待执行，位于队列中等待调度 |
| running | 正在执行 |
| completed | 已完成，任务成功执行 |
| failed | 失败，任务执行失败 |
| cancelled | 已取消，任务被手动停止 |

---

## 附录：Cron 表达式使用指南

### A.1 表达式格式

#### 标准 5 位格式

```
分 时 日 月 周
```

| 位置 | 字段 | 取值范围 | 说明 |
|------|------|----------|------|
| 1 | 分钟 | 0-59 | 每小时内的第几分钟 |
| 2 | 小时 | 0-23 | 每天内的第几小时 |
| 3 | 日期 | 1-31 | 每月内的第几天 |
| 4 | 月份 | 1-12 | 每年内的第几月 |
| 5 | 星期 | 0-6 | 每周内的第几天（0=周日，6=周六） |

#### 扩展 6 位格式

```
秒 分 时 日 月 周
```

| 位置 | 字段 | 取值范围 | 说明 |
|------|------|----------|------|
| 1 | 秒 | 0-59 | 每分钟内的第几秒 |
| 2 | 分钟 | 0-59 | 每小时内的第几分钟 |
| 3-6 | 同上 | - | 与 5 位格式相同 |

### A.2 特殊字符

| 字符 | 含义 | 示例 |
|------|------|------|
| `*` | 任意值 | `* * * * *` = 每分钟 |
| `/` | 间隔 | `*/5 * * * *` = 每 5 分钟 |
| `-` | 范围 | `0 9-17 * * *` = 9:00-17:00 整点 |
| `,` | 列表 | `0 9,12,18 * * *` = 9:00, 12:00, 18:00 |
| `L` | 月末 | `0 0 L * *` = 每月最后一天零点 |

### A.3 别名支持

| 别名 | 等价表达式 | 含义 |
|------|-----------|------|
| `@hourly` | `0 * * * *` | 每小时整点 |
| `@daily` | `0 0 * * *` | 每天零点 |
| `@midnight` | `0 0 * * *` | 每天午夜 |
| `@weekly` | `0 0 * * 0` | 每周日零点 |
| `@monthly` | `0 0 1 * *` | 每月 1 日零点 |
| `@yearly` | `0 0 1 1 *` | 每年 1 月 1 日零点 |

### A.4 常用表达式速查表

#### 间隔执行

| 表达式 | 含义 |
|--------|------|
| `*/5 * * * *` | 每 5 分钟 |
| `*/15 * * * *` | 每 15 分钟 |
| `*/30 * * * *` | 每 30 分钟 |
| `0 * * * *` | 每小时整点 |
| `0 */2 * * *` | 每 2 小时 |
| `0 */6 * * *` | 每 6 小时 |

#### 每日定时

| 表达式 | 含义 |
|--------|------|
| `0 0 * * *` | 每天零点 |
| `0 6 * * *` | 每天 6:00 |
| `0 9 * * *` | 每天 9:00 |
| `0 12 * * *` | 每天 12:00（中午） |
| `0 18 * * *` | 每天 18:00 |
| `30 14 * * *` | 每天 14:30 |

#### 工作日定时

| 表达式 | 含义 |
|--------|------|
| `0 9 * * 1-5` | 周一到周五 9:00 |
| `0 9,18 * * 1-5` | 周一到周五 9:00 和 18:00 |
| `30 8 * * 1-5` | 周一到周五 8:30 |

#### 每周定时

| 表达式 | 含义 |
|--------|------|
| `0 9 * * 0` | 每周日 9:00 |
| `0 9 * * 1` | 每周一 9:00 |
| `0 9 * * 5` | 每周五 9:00 |
| `0 9 * * 1,3,5` | 每周一、三、五 9:00 |

#### 每月定时

| 表达式 | 含义 |
|--------|------|
| `0 0 1 * *` | 每月 1 日零点 |
| `0 0 15 * *` | 每月 15 日零点 |
| `0 0 L * *` | 每月最后一天零点 |
| `0 9 1,15 * *` | 每月 1 日和 15 日 9:00 |

### A.5 注意事项

1. **星期日表示**：可以用 `0` 或 `7` 表示
2. **月份天数**：系统自动处理不同月份的天数差异
3. **月末处理**：使用 `L` 时系统会自动计算正确日期
4. **验证表达式**：使用 `/api/scheduler/validate-cron` API 验证

### A.6 快速参考卡

```
┌─────────────────────────────────────────────────────────────┐
│                    Cron 表达式格式                           │
├─────────────────────────────────────────────────────────────┤
│  5位格式: 分  时  日  月  周                                  │
│  6位格式: 秒  分  时  日  月  周                               │
├─────────────────────────────────────────────────────────────┤
│  特殊字符:                                                   │
│    *  - 任意值                                               │
│    /  - 间隔（*/5 = 每5个单位）                               │
│    -  - 范围（9-17 = 从9到17）                               │
│    ,  - 列表（1,3,5 = 1和3和5）                              │
│    L  - 月末                                                 │
├─────────────────────────────────────────────────────────────┤
│  常用别名:                                                   │
│    @hourly  = 0 * * * *      (每小时)                        │
│    @daily   = 0 0 * * *      (每天)                          │
│    @weekly  = 0 0 * * 0      (每周)                          │
│    @monthly = 0 0 1 * *      (每月)                          │
│    @yearly  = 0 0 1 1 *      (每年)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 附录 B：调度器配置说明

### B.1 核心配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| DEFAULT_TIMEOUT | 600000 (10分钟) | 默认任务超时时间（毫秒） |
| MIN_TIMEOUT | 1000 (1秒) | 最小超时时间 |
| MAX_TIMEOUT | 3600000 (1小时) | 最大超时时间 |
| POLL_INTERVAL | 10 | 调度器轮询间隔（秒） |
| MAX_RETRIES | 2 | 任务最大重试次数 |
| MAX_HISTORY | 1000 | 历史记录最大保留数量 |

### B.2 数据存储

任务调度系统使用 JSON 文件存储数据：

| 文件 | 说明 |
|------|------|
| data/queue.json | 任务队列（待执行任务） |
| data/scheduled.json | 定时任务配置 |
| data/running.json | 当前运行中的任务 |
| data/completed.json | 已完成任务历史 |
| data/failed.json | 失败任务历史 |

### B.3 分页配置

| 参数 | 默认值 | 最大值 | 说明 |
|------|--------|--------|------|
| page | 1 | - | 页码 |
| limit | 20 | 100 | 每页数量 |

---

## 附录 C：执行器与重试机制

### C.1 任务执行流程

```
┌─────────────────────────────────────────────────────────────┐
│                     任务执行流程                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   pending ──→ running ──→ completed                         │
│      │           │                                          │
│      │           ├──→ failed (达到最大重试)                  │
│      │           │                                          │
│      │           └──→ pending (可重试错误)                   │
│      │                    ↓                                 │
│      └────────←─────── retry (最多2次)                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### C.2 任务状态转换

| 当前状态 | 可转换到 | 条件 |
|---------|---------|------|
| pending | running | 开始执行 |
| pending | cancelled | 用户取消 |
| running | completed | 执行成功 |
| running | failed | 执行失败且达到最大重试次数 |
| running | pending | 执行失败但可重试 |
| running | cancelled | 用户取消 |
| failed | pending | 手动重试 |
| completed | - | 终态，不可转换 |
| cancelled | - | 终态，不可转换 |

### C.3 错误分类与重试

#### 错误类型

| 类型 | 说明 | 可重试 |
|------|------|--------|
| transient | 临时性错误 | ✅ 是 |
| timeout | 超时错误 | ✅ 是 |
| resource | 资源错误（网络、限流） | ✅ 是 |
| permanent | 永久性错误 | ❌ 否 |
| user_cancel | 用户取消 | ❌ 否 |
| validation | 验证错误 | ❌ 否 |

#### 错误严重级别

| 级别 | 说明 |
|------|------|
| low | 轻微错误，可继续执行 |
| medium | 中等错误，需要重试 |
| high | 严重错误，需要人工介入 |
| critical | 致命错误，系统问题 |

### C.4 重试策略（指数退避）

任务失败后采用**指数退避 + 随机抖动**策略进行重试：

```
重试延迟 = base_delay × 2^retry_count + jitter

其中：
- base_delay = 5 秒
- max_delay = 60 秒
- jitter = ±10% 随机抖动
```

| 重试次数 | 基础延迟 | 实际延迟范围 |
|---------|---------|-------------|
| 1 | 5 秒 | 4.5 ~ 5.5 秒 |
| 2 | 10 秒 | 9 ~ 11 秒 |
| 3+ | 20 秒（限制） | 18 ~ 22 秒 |

### C.5 超时控制

- 超时检测使用 `asyncio.wait_for()` 实现
- 超时时间从任务配置的 `timeout` 字段获取（毫秒转秒）
- 超时后会触发 `asyncio.TimeoutError`，按可重试错误处理

### C.6 执行结果记录

任务执行完成后会记录以下信息：

| 字段 | 说明 |
|------|------|
| success | 是否成功 |
| message | 结果消息 |
| cost_usd | API 调用费用（美元） |
| duration_ms | 执行耗时（毫秒） |
| files_changed | 变更的文件列表 |
| tools_used | 使用的工具列表 |
| error | 错误信息（失败时） |

---

## 附录 D：系统限制

| 限制项 | 值 | 说明 |
|--------|-----|------|
| 最大并发任务 | 1 | 当前版本同时只能执行一个任务 |
| 最大重试次数 | 2 | 每个任务最多重试 2 次 |
| 最大超时时间 | 1 小时 | 单个任务最长执行时间 |
| 历史记录上限 | 1000 | 已完成/失败任务最大保留数量 |
| 分页大小上限 | 100 | 单次查询最多返回 100 条记录 |
