# 提问历史记录 API 文档

本文档描述提问历史记录系统的 REST API 接口。

## 概述

提问历史记录功能提供以下核心功能：
- 项目列表：获取用户所有有会话记录的项目
- 提问列表：获取指定项目的历史提问记录
- 提问详情：获取每个提问的详细内容、时间戳等信息

> **版本**: v1.0 (2026-03-06)
> **说明**: 提问历史记录是 v8.0.0 版本的新功能

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

## 项目管理

### 获取项目列表

**GET** `/api/projects`

获取用户所有有会话记录的项目列表。

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
    "projects": [
      {
        "encoded_name": "E--workspaces-2026-project",
        "path": "E:\\workspaces_2026\\project",
        "session_count": 25,
        "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20,
    "pages": 1
  }
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| encoded_name | string | 项目编码名称（用于 API 调用） |
| path | string | 项目实际路径 |
| session_count | integer | 该项目的会话数量 |
| tools | array[string] | 该项目会话中使用的工具列表 |

---

## 提问历史记录

### 获取项目提问列表

**GET** `/api/projects/{project_name}/questions`

获取指定项目的提问历史记录列表（分页）。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| project_name | string | 项目编码名称 |

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码，从 1 开始 |
| limit | integer | 20 | 每页数量，最大 100 |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "d9eb61b6-5eb1-42f7-974c-832e54859911",
        "session_id": "d9eb61b6-5eb1-42f7-974c-832e54859911",
        "project_name": "E--workspaces-2026-project",
        "question_text": "帮我实现一个用户认证功能，包括登录、注册、密码找回等",
        "timestamp": "2026-03-05T10:30:00.000Z",
        "time_display": "3 小时前"
      }
    ],
    "total": 50,
    "page": 1,
    "limit": 20,
    "pages": 3
  },
  "project_path": "E:\\workspaces_2026\\project"
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 会话唯一标识 |
| session_id | string | 会话 ID（与 id 相同） |
| project_name | string | 项目编码名称 |
| question_text | string | 完整提问文本（不限长度） |
| timestamp | string | ISO 格式时间戳 |
| time_display | string | 友好时间显示（如 "3 小时前"） |

**时间显示格式**

| 时间范围 | 显示格式 | 示例 |
|----------|----------|------|
| < 1 分钟 | 刚刚 | 刚刚 |
| < 1 小时 | N 分钟前 | 5 分钟前 |
| < 24 小时 | N 小时前 | 3 小时前 |
| 昨天 | 昨天 HH:mm | 昨天 10:30 |
| < 7 天 | N 天前 | 3 天前 |
| >= 7 天 | YYYY-MM-DD HH:mm | 2026-02-28 14:30 |

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 404 | PROJECT_NOT_FOUND | 项目不存在 |

```json
{
  "success": false,
  "detail": "项目不存在",
  "code": "PROJECT_NOT_FOUND"
}
```

---

## 数据提取规则

### 提问内容提取

系统从会话 JSONL 文件中提取首次用户提问，遵循以下规则：

1. **定位首次用户消息**：寻找 `type == "user"` 的第一条记录

2. **提取提问内容**：从 `message.content` 数组中提取所有 `text` 类型的内容

3. **过滤特殊标签**：排除以下内容
   - `<ide_selection>...</ide_selection>` - IDE 选中的代码
   - `<ide_opened_file>...</ide_opened_file>` - IDE 打开的文件
   - `<command-message>...</command-message>` - 命令消息标识
   - `<command-name>...</command-name>` - 命令名称
   - `<command-args>...</command-args>` - 命令参数

4. **敏感信息过滤**：自动脱敏以下内容
   - API Keys（以 `sk-` 开头的密钥）
   - GitHub Tokens（包含 `ghp_`, `gho_` 等前缀）
   - Passwords（包含 `password`, `pwd` 字段）
   - AWS Keys（包含 `AKIA` 前缀）

### 缓存机制

系统使用元数据缓存提高性能：

- **缓存位置**：项目目录下的 `.metadata.json` 文件
- **缓存内容**：会话标志位（has_question, question_timestamp）
- **失效策略**：基于文件修改时间（mtime）自动失效
- **性能目标**：缓存读取 < 10ms，二次访问响应 < 100ms

---

## 错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| PROJECT_NOT_FOUND | 404 | 项目不存在 |
| INVALID_PAGE | 400 | 页码无效 |
| INVALID_LIMIT | 400 | 每页数量超出范围 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

---

## 使用示例

### 获取所有项目

```bash
curl -X GET "http://localhost:8000/api/projects"
```

### 获取指定项目的提问列表

```bash
curl -X GET "http://localhost:8000/api/projects/E--workspaces-2026-project/questions?page=1&limit=20"
```

### 使用 JavaScript 调用

```javascript
// 获取项目列表
const projectsResponse = await fetch('/api/projects');
const projectsData = await projectsResponse.json();

// 获取项目提问列表
const questionsResponse = await fetch('/api/projects/E--workspaces-2026-project/questions?page=1&limit=20');
const questionsData = await questionsResponse.json();

console.log(questionsData.data.items);
```

---

## 附录：项目编码名称

### 编码规则

项目路径在 API 调用时需要编码：

| 原始路径 | 编码名称 |
|----------|----------|
| `E:\workspaces_2026\project` | `E--workspaces-2026-project` |
| `C:\my-projects\test` | `C--my-projects-test` |
| `/home/user/project` | `-home-user-project` |

### 编码规则说明

- **Windows 路径**：`E:\path` → `E--path`（盘符 + `--` + 路径）
- **Unix 路径**：`/home/user` → `-home-user`（以 `-` 开头）
- 路径分隔符和下划线都转换为 `-`

---

## 附录 B：前端集成

### 视图切换

前端通过 `Views.QUESTIONS` 常量切换到提问历史记录视图：

```javascript
const Views = {
  SESSIONS: 'sessions',
  TASKS: 'tasks',
  SCHEDULER: 'scheduler',
  QUESTIONS: 'questions',  // 提问历史记录视图
};
```

### 组件结构

```
提问历史记录
├── 项目列表视图
│   └── [项目项] → 点击进入提问列表
└── 提问列表视图
    ├── 返回按钮 → 返回项目列表
    └── [提问项] → 点击继续会话
```

### 功能特性

- **虚拟滚动**：支持大量提问记录的高效渲染
- **文本截断**：超过 200 字符自动截断，支持展开/收起
- **一键复制**：点击复制按钮复制完整提问内容
- **继续会话**：点击提问项进入对应会话继续对话
- **响应式适配**：支持桌面端和移动端
