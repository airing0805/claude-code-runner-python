"""MCP 服务器数据模型"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """MCP 服务器配置"""
    command: Optional[str] = None
    args: Optional[list[str]] = None
    url: Optional[str] = None
    cwd: Optional[str] = None
    env: Optional[dict[str, str]] = None


class MCPServer(BaseModel):
    """MCP 服务器"""
    id: str
    name: str
    connection_type: str = Field(..., pattern="^(stdio|http)$")
    config: MCPServerConfig
    enabled: bool = True
    created_at: datetime
    last_connected: Optional[datetime] = None


class MCPServerCreate(BaseModel):
    """创建 MCP 服务器请求"""
    name: str = Field(..., min_length=1, max_length=100)
    connection_type: str = Field(..., pattern="^(stdio|http)$")
    config: MCPServerConfig
    enabled: bool = True


class MCPServerUpdate(BaseModel):
    """更新 MCP 服务器请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    connection_type: Optional[str] = Field(None, pattern="^(stdio|http)$")
    config: Optional[MCPServerConfig] = None
    enabled: Optional[bool] = None


class MCPServerStatus(BaseModel):
    """MCP 服务器状态"""
    id: str
    name: str
    status: str = Field(..., pattern="^(online|offline|connecting|error)$")
    message: Optional[str] = None
    last_checked: datetime


class MCPTool(BaseModel):
    """MCP 服务器提供的工具"""
    name: str
    description: Optional[str] = None
    input_schema: dict = {}


class MCPServerTools(BaseModel):
    """MCP 服务器工具列表"""
    server_id: str
    server_name: str
    tools: list[MCPTool]
