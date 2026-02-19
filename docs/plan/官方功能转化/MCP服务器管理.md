# MCP 服务器管理

## 概述

管理 Claude Code 的 MCP (Model Context Protocol) 外部服务连接。用户可以通过浏览器配置和管理 MCP 服务器。

## 需求

### 13.1 核心功能

| 功能 | 描述 |
|------|------|
| 服务器列表 | 查看已配置的 MCP 服务器 |
| 添加服务器 | 配置新的 MCP 服务器连接 |
| 编辑服务器 | 修改现有服务器配置 |
| 删除服务器 | 移除服务器配置 |
| 连接状态 | 查看服务器在线/离线状态 |
| 工具列表 | 查看服务器提供的工具 |

### 13.2 连接类型

| 类型 | 说明 |
|------|------|
| stdio | 标准输入输出模式（本地命令） |
| http/sse | HTTP 模式（远程服务） |

### 13.3 API 设计

```json
# 获取所有 MCP 服务器
GET /api/mcp/servers

Response: 200 OK
{
  "servers": [
    {
      "id": "mcp_abc123",
      "name": "GitHub",
      "connection_type": "stdio",
      "config": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"]
      },
      "enabled": true,
      "created_at": "2026-02-19T10:30:00Z",
      "last_connected": "2026-02-19T11:45:00Z"
    }
  ]
}

# 创建 MCP 服务器
POST /api/mcp/servers

Request:
{
  "name": "GitHub",
  "connection_type": "stdio",
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "cwd": "/home/user/mcp-servers"
  }
}

Response: 201 Created
{
  "id": "mcp_abc123",
  "name": "GitHub",
  ...
}

# 更新 MCP 服务器
PUT /api/mcp/servers/{server_id}

Request:
{
  "name": "GitHub MCP",
  "enabled": false
}

# 删除 MCP 服务器
DELETE /api/mcp/servers/{server_id}

# 获取服务器状态
GET /api/mcp/servers/{server_id}/status

Response: 200 OK
{
  "server_id": "mcp_abc123",
  "status": "connected",
  "tools_count": 8
}

# 获取服务器工具列表
GET /api/mcp/servers/{server_id}/tools

Response: 200 OK
{
  "server_id": "mcp_abc123",
  "tools": [
    {
      "name": "search_repositories",
      "description": "Search for GitHub repositories",
      "input_schema": {"type": "object", "properties": {...}}
    }
  ]
}

# 手动连接/断开
POST /api/mcp/servers/{server_id}/connect
POST /api/mcp/servers/{server_id}/disconnect
```

### 13.4 UI 设计

- 服务器列表表格（名称、类型、状态、操作）
- 添加/编辑对话框（支持 stdio 和 http 两种配置）
- 工具详情面板（展开显示可用工具）

### 13.5 优先级

| 功能 | 优先级 |
|------|--------|
| 服务器列表 API | P0 |
| 添加服务器 | P0 |
| 编辑/删除服务器 | P0 |
| 连接状态显示 | P0 |
| 获取工具列表 | P0 |
| 手动连接/断开 | P1 |

## 实现方案

- 配置文件存储在 `~/.claude/mcp-servers/servers.json`
- 使用 subprocess 管理 stdio 类型连接
- 敏感配置字段（如 token）需要加密存储
