# v0.3.3 - 文档展示技术设计

## 1. API 接口设计

### 1.1 获取工具详细说明

```
GET /api/claude/docs/tools
```

**响应示例**：
```json
{
  "tools": [
    {
      "name": "Read",
      "description": "读取文件内容",
      "category": "文件操作",
      "modifies_files": false,
      "parameters": [
        {
          "name": "file_path",
          "type": "string",
          "required": true,
          "description": "要读取的文件路径"
        },
        {
          "name": "limit",
          "type": "integer",
          "required": false,
          "description": "限制返回的行数"
        },
        {
          "name": "offset",
          "type": "integer",
          "required": false,
          "description": "从指定行号开始读取"
        }
      ],
      "example": {
        "input": {"file_path": "/path/to/file.py"},
        "description": "读取整个文件"
      }
    },
    ...
  ]
}
```

### 1.2 获取代理类型说明

```
GET /api/claude/docs/agents
```

**响应示例**：
```json
{
  "agents": [
    {
      "name": "general-purpose",
      "description": "通用任务代理",
      "use_cases": ["处理各种编程任务", "回答问题", "代码生成"]
    },
    {
      "name": "explore",
      "description": "代码库探索代理",
      "use_cases": ["快速了解代码库结构", "查找文件", "定位功能"]
    },
    ...
  ]
}
```

### 1.3 获取内置命令说明

```
GET /api/claude/docs/commands
```

**响应示例**：
```json
{
  "commands": [
    {
      "name": "/commit",
      "description": "提交当前更改到 Git",
      "usage": "/commit -m \"commit message\"",
      "options": [
        {"name": "-m", "description": "提交信息"}
      ]
    },
    ...
  ]
}
```

### 1.4 获取最佳实践

```
GET /api/claude/docs/best-practices
```

**响应示例**：
```json
{
  "tool_selection": {
    "read_only": ["Read", "Glob", "Grep"],
    "modify_files": ["Write", "Edit"],
    "execute": ["Bash"],
    "search": ["WebSearch", "WebFetch"]
  },
  "permission_mode_guide": [
    {"mode": "default", "scenario": "交互式开发"},
    {"mode": "acceptEdits", "scenario": "审查/分析任务"},
    {"mode": "plan", "scenario": "复杂重构"},
    {"mode": "bypassPermissions", "scenario": "CI/CD自动化"}
  ],
  "error_handling": {
    "try_catch": "使用 try-except 捕获异常",
    "logging": "记录详细错误信息",
    "user_message": "返回用户友好的错误消息"
  }
}
```

## 2. 数据结构设计

### 2.1 ToolDoc

```python
from pydantic import BaseModel

class Parameter(BaseModel):
    name: str
    type: str
    required: bool
    description: str

class ToolExample(BaseModel):
    input: dict
    description: str

class ToolDoc(BaseModel):
    name: str
    description: str
    category: str
    modifies_files: bool
    parameters: list[Parameter]
    example: ToolExample
```

### 2.2 AgentDoc

```python
from pydantic import BaseModel

class AgentDoc(BaseModel):
    name: str
    description: str
    use_cases: list[str]
```

### 2.3 CommandDoc

```python
from pydantic import BaseModel

class CommandOption(BaseModel):
    name: str
    description: str

class CommandDoc(BaseModel):
    name: str
    description: str
    usage: str
    options: list[CommandOption]
```

## 3. 后端实现

### 3.1 路由设计

在 `app/routers/claude.py` 中添加：

```python
@router.get("/docs/tools", response_model=ToolsDoc)
async def get_tools_docs():
    """获取工具详细说明"""
    ...

@router.get("/docs/agents", response_model=AgentsDoc)
async def get_agents_docs():
    """获取代理类型说明"""
    ...

@router.get("/docs/commands", response_model=CommandsDoc)
async def get_commands_docs():
    """获取内置命令说明"""
    ...

@router.get("/docs/best-practices", response_model=BestPracticesDoc)
async def get_best_practices():
    """获取最佳实践指南"""
    ...
```

### 3.2 文档数据

文档数据存储为静态常量，从 ClaudeCode功能详解.md 提取：

```python
TOOLS_DOCS: list[ToolDoc] = [...]
AGENTS_DOCS: list[AgentDoc] = [...]
COMMANDS_DOCS: list[CommandDoc] = [...]
```

## 4. 前端设计

### 4.1 页面结构

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Code 文档                                           │
├─────────────────────────────────────────────────────────────┤
│  [工具] [代理] [命令] [最佳实践]                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 工具详解                                             │   │
│  │ ─────────                                            │   │
│  │ Read - 读取文件内容                                  │   │
│  │   参数: file_path, limit, offset                   │   │
│  │   示例: {"file_path": "/path/to/file.py"}          │   │
│  │                                                     │   │
│  │ Write - 创建新文件                                   │   │
│  │ Edit - 编辑文件                                      │   │
│  │ ...                                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 5. 关键文件

| 文件 | 操作 |
|------|------|
| `app/routers/claude.py` | 修改 - 添加 docs 相关端点 |
| `app/claude/docs_data.py` | 新建 - 文档数据 |
| `web/static/modules/claudeStatus.js` | 修改 - 添加文档展示模块 |
