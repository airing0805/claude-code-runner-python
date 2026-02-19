"""MCP 服务器管理 API"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.mcp.manager import get_mcp_manager
from app.mcp.schemas import (
    MCPServer,
    MCPServerCreate,
    MCPServerStatus,
    MCPServerTools,
    MCPServerUpdate,
)

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/servers", response_model=dict[str, list[MCPServer]])
async def get_servers():
    """获取 MCP 服务器列表"""
    manager = get_mcp_manager()
    servers = manager.get_servers()
    return {"servers": servers}


@router.post("/servers", response_model=MCPServer)
async def create_server(server: MCPServerCreate):
    """创建 MCP 服务器"""
    manager = get_mcp_manager()
    created_server = manager.create_server(server)
    return created_server


@router.put("/servers/{server_id}", response_model=MCPServer)
async def update_server(server_id: str, server: MCPServerUpdate):
    """更新 MCP 服务器"""
    manager = get_mcp_manager()

    # 获取现有服务器
    existing = manager.get_server(server_id)
    if not existing:
        raise HTTPException(status_code=404, detail="服务器不存在")

    # 构建更新数据
    update_data = MCPServerCreate(
        name=server.name if server.name is not None else existing.name,
        connection_type=server.connection_type if server.connection_type is not None else existing.connection_type,
        config=server.config if server.config is not None else existing.config,
        enabled=server.enabled if server.enabled is not None else existing.enabled,
    )

    updated = manager.update_server(server_id, update_data)
    return updated


@router.delete("/servers/{server_id}")
async def delete_server(server_id: str):
    """删除 MCP 服务器"""
    manager = get_mcp_manager()

    success = manager.delete_server(server_id)
    if not success:
        raise HTTPException(status_code=404, detail="服务器不存在")

    return {"success": True, "message": "服务器已删除"}


@router.get("/servers/{server_id}/status", response_model=MCPServerStatus)
async def get_server_status(server_id: str):
    """获取 MCP 服务器连接状态"""
    manager = get_mcp_manager()

    # 检查服务器是否存在
    server = manager.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    status = await manager.get_server_status(server_id)
    if not status:
        raise HTTPException(status_code=404, detail="无法获取服务器状态")

    return status


@router.get("/servers/{server_id}/tools", response_model=MCPServerTools)
async def get_server_tools(server_id: str):
    """获取 MCP 服务器提供的工具列表"""
    manager = get_mcp_manager()

    # 检查服务器是否存在
    server = manager.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    tools = await manager.get_server_tools(server_id)
    if not tools:
        raise HTTPException(status_code=404, detail="无法获取工具列表")

    return tools
