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

    # 自定义管理配置存储路径
    CONFIG_PATH = Path.home() / ".claude" / "mcp-servers" / "servers.json"
    # Claude Code 全局配置路径
    CLAUDE_CONFIG_PATH = Path.home() / ".claude.json"

    def __init__(self):
        self._ensure_config_dir()
        self._lock = asyncio.Lock()

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    def get_servers(self) -> list[MCPServer]:
        """获取 MCP 服务器列表（从自定义配置加载）"""
        if not self.CONFIG_PATH.exists():
            # 如果没有自定义配置，尝试从 Claude Code 配置加载
            return self._load_from_claude_config()

        try:
            with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                servers_data = data.get("servers", [])
                # 为缺少 created_at 的旧数据补充默认值
                servers = []
                for server_data in servers_data:
                    if "created_at" not in server_data:
                        server_data["created_at"] = datetime.now(timezone.utc).isoformat()
                    servers.append(MCPServer(**server_data))
                return servers
        except (json.JSONDecodeError, IOError):
            return self._load_from_claude_config()

    def _load_from_claude_config(self) -> list[MCPServer]:
        """从 Claude Code 全局配置加载 MCP 服务器"""
        servers = []
        if not self.CLAUDE_CONFIG_PATH.exists():
            return servers

        try:
            with open(self.CLAUDE_CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                mcp_servers = config.get("mcpServers", {})

                for name, server_config in mcp_servers.items():
                    connection_type = server_config.get("type", "stdio")
                    config_obj = MCPServerConfig(
                        command=server_config.get("command"),
                        args=server_config.get("args", []),
                        url=server_config.get("url"),
                        env=server_config.get("env"),
                    )

                    server = MCPServer(
                        id=f"mcp_{uuid.uuid4().hex[:8]}",
                        name=name.title(),  # 首字母大写
                        connection_type=connection_type,
                        config=config_obj,
                        enabled=True,
                        created_at=datetime.now(timezone.utc),
                        last_connected=None,
                    )
                    servers.append(server)
        except (json.JSONDecodeError, IOError):
            pass

        return servers

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

        # 同时更新 Claude Code 全局配置
        self._update_claude_config(servers)

    def _update_claude_config(self, servers: list[MCPServer]) -> None:
        """更新 Claude Code 全局配置文件"""
        if not self.CLAUDE_CONFIG_PATH.exists():
            return

        try:
            with open(self.CLAUDE_CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        # 获取原有的 mcpServers 配置
        existing_mcp_servers = config.get("mcpServers", {})

        # 构建新的服务器配置（只包含用户管理的服务器）
        managed_server_keys = {server.name.lower().replace(" ", "-") for server in servers}

        # 保留不在管理范围内的原有服务器
        mcp_servers = {}
        for name, server_config in existing_mcp_servers.items():
            if name not in managed_server_keys:
                mcp_servers[name] = server_config

        # 添加用户管理的服务器
        for server in servers:
            if not server.enabled:
                continue

            # 转换为 Claude Code 格式
            server_config = {}
            if server.connection_type == "stdio":
                server_config["type"] = "stdio"
                if server.config.command:
                    server_config["command"] = server.config.command
                if server.config.args:
                    server_config["args"] = server.config.args
                if server.config.env:
                    server_config["env"] = server.config.env
            elif server.connection_type == "http":
                server_config["type"] = "http"
                if server.config.url:
                    server_config["url"] = server.config.url

            # 使用小写名称作为 key
            mcp_servers[server.name.lower().replace(" ", "-")] = server_config

        # 更新全局配置
        config["mcpServers"] = mcp_servers

        # 写回配置文件
        try:
            with open(self.CLAUDE_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except IOError:
            pass  # 忽略写入错误

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
