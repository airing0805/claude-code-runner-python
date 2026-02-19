# v0.3.4 - MCP 服务器管理技术设计

## 1. API 接口设计

### 1.1 获取所有 MCP 服务器

```
GET /api/mcp/servers
```

**响应示例**：
```json
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
```

### 1.2 创建 MCP 服务器

```
POST /api/mcp/servers
```

**请求体**：
```json
{
  "name": "GitHub",
  "connection_type": "stdio",
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"]
  }
}
```

### 1.3 更新 MCP 服务器

```
PUT /api/mcp/servers/{server_id}
```

**请求体**：
```json
{
  "name": "GitHub MCP",
  "enabled": false
}
```

### 1.4 删除 MCP 服务器

```
DELETE /api/mcp/servers/{server_id}
```

### 1.5 获取服务器状态

```
GET /api/mcp/servers/{server_id}/status
```

### 1.6 获取服务器工具列表

```
GET /api/mcp/servers/{server_id}/tools
```

## 2. 数据结构设计

### 2.1 MCPServer

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MCPServerConfig(BaseModel):
    command: Optional[str] = None
    args: Optional[list[str]] = None
    url: Optional[str] = None
    cwd: Optional[str] = None

class MCPServer(BaseModel):
    id: str
    name: str
    connection_type: str  # "stdio" or "http"
    config: MCPServerConfig
    enabled: bool = True
    created_at: datetime
    last_connected: Optional[datetime] = None
```

## 3. 后端实现

### 3.1 路由文件

新建 `app/routers/mcp.py`：

```python
from fastapi import APIRouter, HTTPException
from app.mcp.schemas import MCPServer, MCPServerCreate

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

@router.get("/servers", response_model=list[MCPServer])
async def get_servers():
    """获取 MCP 服务器列表"""
    ...

@router.post("/servers", response_model=MCPServer)
async def create_server(server: MCPServerCreate):
    """创建 MCP 服务器"""
    ...

@router.put("/servers/{server_id}", response_model=MCPServer)
async def update_server(server_id: str, server: MCPServerUpdate):
    """更新 MCP 服务器"""
    ...

@router.delete("/servers/{server_id}")
async def delete_server(server_id: str):
    """删除 MCP 服务器"""
    ...
```

### 3.2 MCP 服务管理

```python
import json
from pathlib import Path

class MCPManager:
    """MCP 服务器管理器"""

    CONFIG_PATH = Path.home() / ".claude" / "mcp-servers" / "servers.json"

    def get_servers(self) -> list[MCPServer]:
        """获取服务器列表"""
        if not self.CONFIG_PATH.exists():
            return []
        with open(self.CONFIG_PATH) as f:
            data = json.load(f)
            return [MCPServer(**server) for server in data.get("servers", [])]

    def save_servers(self, servers: list[MCPServer]):
        """保存服务器配置"""
        ...
```

## 4. 前端设计

### 4.1 页面结构

```
┌─────────────────────────────────────────────────────────────┐
│  MCP 服务器管理                                              │
│                                                             │
│  [+ 添加服务器]                                              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 名称    │ 类型    │ 状态      │ 操作                │   │
│  ├─────────┼─────────┼───────────┼────────────────────┤   │
│  │ GitHub  │ stdio   │ 在线      │ [编辑] [删除]       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 5. 关键文件

| 文件 | 操作 |
|------|------|
| `app/routers/mcp.py` | 新建 |
| `app/mcp/schemas.py` | 新建 |
| `app/mcp/manager.py` | 新建 |
| `app/main.py` | 修改 - 注册路由 |
| `web/static/modules/mcpManager.js` | 新建 |
