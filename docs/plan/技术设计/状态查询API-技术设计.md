# 状态查询 API 技术设计

## 概述

状态查询 API 提供服务状态、可用工具列表等基础信息的查询功能。

---

## 基础信息

- **Base URL**: `http://127.0.0.1:8000`
- **Content-Type**: `application/json`

---

## 页面路由

### GET /

返回 Web 界面主页。

**响应**: HTML 页面

---

## 服务状态

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

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 服务状态（running/stopped） |
| working_dir | string | 当前工作目录 |
| active_tasks | int | 当前活跃任务数 |

---

## 工具列表

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

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 工具名称 |
| description | string | 工具功能描述 |

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
