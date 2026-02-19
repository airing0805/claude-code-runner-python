"""MCP 服务器管理器"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.mcp.schemas import (
    MCPServer,
    MCPServerConfig,
    MCPServerCreate,
    MCPServerStatus,
    MCPServerTools,
    MCPTool,
)


class MCPManager:
    """MCP 服务器管理器"""

    CONFIG_PATH = Path.home() / ".claude" / "mcp-servers" / "servers.json"

    def __init__(self):
        self._ensure_config_dir()
        self._lock = asyncio.Lock()

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    def get_servers(self) -> list[MCPServer]:
        """获取 MCP 服务器列表"""
        if not self.CONFIG_PATH.exists():
            return []

        try:
            with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                servers_data = data.get("servers", [])
                return [MCPServer(**server) for server in servers_data]
        except (json.JSONDecodeError, IOError):
            return []

    def get_server(self, server_id: str) -> Optional[MCPServer]:
        """获取单个 MCP 服务器"""
        servers = self.get_servers()
        for server in servers:
            if server.id == server_id:
                return server
        return None

    def _save_servers(self, servers: list[MCPServer]) -> None:
        """保存服务器列表到配置文件（线程安全）"""
        data = {"servers": [server.model_dump(mode="json") for server in servers]}

        # 原子写入：先写临时文件，再重命名
        temp_path = self.CONFIG_PATH.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        temp_path.replace(self.CONFIG_PATH)

    async def _save_servers_async(self, servers: list[MCPServer]) -> None:
        """异步保存服务器列表（带锁）"""
        async with self._lock:
            self._save_servers(servers)

    def create_server(self, server_data: MCPServerCreate) -> MCPServer:
        """创建 MCP 服务器"""
        now = datetime.now(timezone.utc)

        server = MCPServer(
            id=f"mcp_{uuid.uuid4().hex[:8]}",
            name=server_data.name,
            connection_type=server_data.connection_type,
            config=server_data.config,
            enabled=server_data.enabled,
            created_at=now,
            last_connected=None,
        )

        servers = self.get_servers()
        servers.append(server)
        self._save_servers(servers)

        return server

    def update_server(self, server_id: str, server_data: MCPServerCreate) -> Optional[MCPServer]:
        """更新 MCP 服务器"""
        servers = self.get_servers()

        for i, server in enumerate(servers):
            if server.id == server_id:
                # 更新字段
                servers[i] = MCPServer(
                    id=server_id,
                    name=server_data.name,
                    connection_type=server_data.connection_type,
                    config=server_data.config,
                    enabled=server_data.enabled,
                    created_at=server.created_at,
                    last_connected=server.last_connected,
                )
                self._save_servers(servers)
                return servers[i]

        return None

    def delete_server(self, server_id: str) -> bool:
        """删除 MCP 服务器"""
        servers = self.get_servers()
        original_len = len(servers)

        servers = [s for s in servers if s.id != server_id]

        if len(servers) < original_len:
            self._save_servers(servers)
            return True

        return False

    async def get_server_status(self, server_id: str) -> Optional[MCPServerStatus]:
        """获取 MCP 服务器连接状态"""
        server = self.get_server(server_id)
        if not server:
            return None

        # TODO: 实际连接 MCP 服务器检查状态
        # 目前返回模拟状态
        if not server.enabled:
            return MCPServerStatus(
                id=server.id,
                name=server.name,
                status="offline",
                message="服务器已禁用",
                last_checked=datetime.now(timezone.utc),
            )

        return MCPServerStatus(
            id=server.id,
            name=server.name,
            status="offline",
            message="状态检查未实现",
            last_checked=datetime.now(timezone.utc),
        )

    async def get_server_tools(self, server_id: str) -> Optional[MCPServerTools]:
        """获取 MCP 服务器提供的工具列表"""
        server = self.get_server(server_id)
        if not server:
            return None

        # TODO: 实际从 MCP 服务器获取工具列表
        # 目前返回空列表
        return MCPServerTools(
            server_id=server.id,
            server_name=server.name,
            tools=[],
        )


# 全局管理器实例
_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """获取 MCP 管理器单例"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
