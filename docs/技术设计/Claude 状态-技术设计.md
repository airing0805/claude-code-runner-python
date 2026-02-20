# Claude 状态 技术设计

## 概述

Claude 状态功能整合了环境信息展示、状态查询和工具统计展示三个模块的技术设计，为用户提供统一的 Claude Code 运行状态查看入口。

> **来源文档**: 本文档由以下技术设计文档合并而成：
> - 环境信息展示-技术设计.md
> - 状态查询API-技术设计.md
> - 工具统计展示-技术设计.md

---

## 1. 环境信息展示

### 1.1 API 接口设计

#### 1.1.1 获取 Claude 版本

```
GET /api/claude/version
```

**响应示例**：
```json
{
  "cli_version": "1.0.12",
  "sdk_version": "0.0.25",
  "runtime": {
    "os": "Windows",
    "os_version": "11",
    "python_version": "3.12.0"
  }
}
```

#### 1.1.2 获取环境变量

```
GET /api/claude/env
```

**响应示例**：
```json
{
  "variables": {
    "ANTHROPIC_API_KEY": "sk-***",
    "WORKING_DIR": "E:\\workspaces_2026_python\\claude-code-runner",
    "CLAUDECODE": "true",
    "PORT": "8000"
  }
}
```

**说明**：
- 敏感变量（API_KEY、TOKEN、PASSWORD 等）显示为 `***`
- 仅返回与 Claude Code 相关的变量

#### 1.1.3 获取配置信息

```
GET /api/claude/config
```

**响应示例**：
```json
{
  "working_dir": "E:\\workspaces_2026_python\\claude-code-runner",
  "default_permission_mode": "default",
  "allowed_tools": [
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "WebSearch",
    "WebFetch",
    "Task"
  ]
}
```

### 1.2 数据结构设计

#### VersionInfo

```python
from pydantic import BaseModel

class RuntimeInfo(BaseModel):
    os: str
    os_version: str
    python_version: str

class VersionInfo(BaseModel):
    cli_version: str
    sdk_version: str
    runtime: RuntimeInfo
```

#### EnvInfo

```python
from pydantic import BaseModel

class EnvInfo(BaseModel):
    variables: dict[str, str]
```

#### ConfigInfo

```python
from pydantic import BaseModel

class ConfigInfo(BaseModel):
    working_dir: str
    default_permission_mode: str
    allowed_tools: list[str]
```

### 1.3 敏感信息处理

```python
SENSITIVE_KEYS = {
    "ANTHROPIC_API_KEY",
    "API_KEY",
    "TOKEN",
    "PASSWORD",
    "SECRET",
    "PRIVATE_KEY",
}

def mask_sensitive_value(key: str, value: str) -> str:
    """隐藏敏感信息"""
    key_upper = key.upper()
    for sensitive in SENSITIVE_KEYS:
        if sensitive in key_upper:
            return "***"
    return value
```

---

## 2. 状态查询

### 2.1 服务状态

#### GET /api/status

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

### 2.2 工具列表

#### GET /api/tools

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

## 3. 工具统计展示

### 3.1 API 接口设计

#### 3.1.1 获取工具使用统计

```
GET /api/claude/stats
```

**响应示例**：
```json
{
  "tools_usage": {
    "Read": 15,
    "Write": 3,
    "Edit": 8,
    "Bash": 5,
    "Glob": 12,
    "Grep": 7,
    "WebSearch": 2,
    "WebFetch": 1,
    "Task": 0
  },
  "files_changed": 11,
  "task_stats": {
    "total": 10,
    "success": 9,
    "failed": 1,
    "avg_duration_ms": 3500,
    "total_cost_usd": 0.52
  }
}
```

#### 3.1.2 获取权限模式说明

```
GET /api/claude/permission-modes
```

**响应示例**：
```json
{
  "modes": [
    {
      "name": "default",
      "description": "默认模式，每次工具调用需要用户确认",
      "scenarios": ["安全性要求高的场景", "需要人工审核的操作"]
    },
    {
      "name": "acceptEdits",
      "description": "自动接受编辑操作（Write/Edit），其他操作仍需确认",
      "scenarios": ["日常开发", "批量修改文件"]
    },
    {
      "name": "plan",
      "description": "规划模式，先生成计划，用户批准后执行",
      "scenarios": ["复杂任务", "需要规划的操作", "重要或不可逆的操作"]
    },
    {
      "name": "bypassPermissions",
      "description": "跳过所有权限检查，完全自动化",
      "scenarios": ["CI/CD自动化", "无人值守任务"]
    }
  ]
}
```

### 3.2 数据结构设计

#### ToolStats

```python
from pydantic import BaseModel

class ToolUsage(BaseModel):
    Read: int
    Write: int
    Edit: int
    Bash: int
    Glob: int
    Grep: int
    WebSearch: int
    WebFetch: int
    Task: int

class TaskStats(BaseModel):
    total: int
    success: int
    failed: int
    avg_duration_ms: int
    total_cost_usd: float

class StatsInfo(BaseModel):
    tools_usage: ToolUsage
    files_changed: int
    task_stats: TaskStats
```

#### PermissionMode

```python
from pydantic import BaseModel

class PermissionMode(BaseModel):
    name: str
    description: str
    scenarios: list[str]

class PermissionModesInfo(BaseModel):
    modes: list[PermissionMode]
```

---

## 4. 后端实现

### 4.1 路由文件

新建 `app/routers/claude.py`：

```python
from fastapi import APIRouter, HTTPException
from app.claude.schemas import VersionInfo, EnvInfo, ConfigInfo

router = APIRouter(prefix="/api/claude", tags=["claude"])

@router.get("/version", response_model=VersionInfo)
async def get_version():
    """获取 Claude 版本信息"""
    ...

@router.get("/env", response_model=EnvInfo)
async def get_env():
    """获取环境变量（敏感信息隐藏）"""
    ...

@router.get("/config", response_model=ConfigInfo)
async def get_config():
    """获取 Claude 配置信息"""
    ...

@router.get("/stats", response_model=StatsInfo)
async def get_stats():
    """获取工具使用统计"""
    ...

@router.get("/permission-modes", response_model=PermissionModesInfo)
async def get_permission_modes():
    """获取权限模式说明"""
    ...
```

### 4.2 路由注册

在 `app/main.py` 中注册新路由：

```python
from app.routers import claude

app.include_router(claude.router)
```

### 4.3 统计存储

使用内存或数据库存储统计数据：

```python
class StatsCollector:
    """收集工具使用统计"""

    def __init__(self):
        self.tools_usage: dict[str, int] = defaultdict(int)
        self.files_changed: int = 0
        self.task_stats: list[dict] = []

    def record_tool_use(self, tool_name: str):
        self.tools_usage[tool_name] += 1

    def record_file_change(self):
        self.files_changed += 1
```

---

## 5. 前端设计

### 5.1 页面结构

```
┌─────────────────────────────────────────────────────────────┐
│  Claude 状态                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐        │
│  │  版本信息            │  │  环境变量            │        │
│  │  ─────────          │  │  ─────────          │        │
│  │  CLI: 1.0.12        │  │  WORKING_DIR: ***   │        │
│  │  SDK: 0.0.25        │  │  PORT: 8000         │        │
│  │  OS: Windows 11     │  │  ...                │        │
│  └─────────────────────┘  └─────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  配置信息                                            │   │
│  │  ─────────                                          │   │
│  │  工作目录: E:\workspaces_2026_python\...            │   │
│  │  权限模式: default                                   │   │
│  │  可用工具: Read, Write, Edit, Bash, Glob, Grep...  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  工具使用统计                                         │   │
│  │  ─────────                                          │   │
│  │  Read: 15  Write: 3  Edit: 8  Bash: 5  Glob: 12  │   │
│  │  Grep: 7  WebSearch: 2  WebFetch: 1  Task: 0     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  权限模式说明                                         │   │
│  │  ─────────                                          │   │
│  │  default - 每次需要确认                               │   │
│  │  acceptEdits - 自动接受编辑                          │   │
│  │  plan - 规划模式                                    │   │
│  │  bypassPermissions - 完全自动化                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 API 调用

```javascript
// 获取版本信息
async function loadVersionInfo() {
  const response = await fetch('/api/claude/version');
  return await response.json();
}

// 获取环境变量
async function loadEnvInfo() {
  const response = await fetch('/api/claude/env');
  return await response.json();
}

// 获取配置
async function loadConfigInfo() {
  const response = await fetch('/api/claude/config');
  return await response.json();
}

// 获取工具统计
async function loadStats() {
  const response = await fetch('/api/claude/stats');
  return await response.json();
}

// 获取权限模式
async function loadPermissionModes() {
  const response = await fetch('/api/claude/permission-modes');
  return await response.json();
}
```

---

## 6. 错误响应

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

## 7. 测试策略

### 7.1 单元测试

- 测试 `mask_sensitive_value` 函数
- 测试各个 endpoint 返回正确的数据格式

### 7.2 API 测试

- 测试 `/api/claude/version` 返回 200
- 测试 `/api/claude/env` 不包含明文 API Key
- 测试 `/api/claude/config` 返回正确配置
- 测试 `/api/claude/stats` 返回统计信息
- 测试 `/api/claude/permission-modes` 返回权限模式

---

## 8. 关键文件

| 文件 | 操作 |
|------|------|
| `app/routers/claude.py` | 新建 |
| `app/claude/schemas.py` | 新建 |
| `app/claude/__init__.py` | 新建 |
| `app/main.py` | 修改 - 注册路由 |
| `web/templates/index.html` | 修改 - 添加导航 |
| `web/static/app.js` | 修改 - 添加视图 |
| `web/static/modules/claudeStatus.js` | 新建 |
