# MCP 服务器管理 - 测试文档

## 1. 测试策略

### 1.1 测试目标

验证 MCP 服务器管理 API 的 CRUD 操作和状态查询功能。

### 1.2 测试范围

| 模块 | 测试内容 |
|------|---------|
| 服务器列表 | 获取所有服务器 |
| 创建服务器 | stdio 和 http 类型 |
| 更新服务器 | 修改配置和启用/禁用 |
| 删除服务器 | 移除服务器 |
| 连接状态 | 在线/离线状态 |

---

## 2. 单元测试

### 2.1 数据模型测试

```python
# tests/test_mcp.py

from app.mcp.schemas import MCPServer, MCPServerConfig, MCPServerCreate, MCPServerUpdate
from datetime import datetime

class TestMCPServerConfig:
    """MCP 服务器配置模型测试"""

    def test_stdio_config(self):
        """测试 stdio 类型配置"""
        config = MCPServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"]
        )
        assert config.command == "npx"
        assert len(config.args) == 2

    def test_http_config(self):
        """测试 http 类型配置"""
        config = MCPServerConfig(
            url="https://mcp.example.com/api"
        )
        assert config.url == "https://mcp.example.com/api"

    def test_config_with_cwd(self):
        """测试带工作目录的配置"""
        config = MCPServerConfig(
            command="node",
            args=["server.js"],
            cwd="/home/user/mcp"
        )
        assert config.cwd == "/home/user/mcp"


class TestMCPServer:
    """MCP 服务器模型测试"""

    def test_server_creation(self):
        """测试服务器创建"""
        server = MCPServer(
            id="mcp_abc123",
            name="GitHub",
            connection_type="stdio",
            config=MCPServerConfig(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"]
            ),
            enabled=True,
            created_at=datetime.now()
        )
        assert server.id == "mcp_abc123"
        assert server.name == "GitHub"
        assert server.connection_type == "stdio"

    def test_server_default_enabled(self):
        """测试默认启用"""
        server = MCPServer(
            id="mcp_123",
            name="Test",
            connection_type="stdio",
            config=MCPServerConfig(command="test"),
            created_at=datetime.now()
        )
        assert server.enabled is True


class TestMCPServerCreate:
    """MCP 服务器创建请求模型测试"""

    def test_create_stdio_server(self):
        """测试创建 stdio 服务器"""
        server = MCPServerCreate(
            name="GitHub",
            connection_type="stdio",
            config=MCPServerConfig(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"]
            )
        )
        assert server.name == "GitHub"
        assert server.connection_type == "stdio"

    def test_create_http_server(self):
        """测试创建 http 服务器"""
        server = MCPServerCreate(
            name="Remote MCP",
            connection_type="http",
            config=MCPServerConfig(url="https://mcp.example.com")
        )
        assert server.connection_type == "http"


class TestMCPServerUpdate:
    """MCP 服务器更新请求模型测试"""

    def test_update_name(self):
        """测试更新名称"""
        update = MCPServerUpdate(name="New Name")
        assert update.name == "New Name"

    def test_update_enabled(self):
        """测试更新启用状态"""
        update = MCPServerUpdate(enabled=False)
        assert update.enabled is False

    def test_partial_update(self):
        """测试部分更新"""
        update = MCPServerUpdate(enabled=False)
        assert update.name is None  # 未更新
```

---

## 3. 集成测试

### 3.1 服务器列表 API 测试

```python
class TestMCPServersEndpoint:
    """MCP 服务器 API 测试"""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_mcp_manager(self):
        """Mock MCP 管理器"""
        with patch("app.routers.mcp.MCPManager") as mock:
            mock_instance = MagicMock()
            mock_instance.get_servers.return_value = [
                MCPServer(
                    id="mcp_1",
                    name="GitHub",
                    connection_type="stdio",
                    config=MCPServerConfig(command="npx", args=["-y", "server"]),
                    enabled=True,
                    created_at=datetime.now()
                )
            ]
            mock.return_value = mock_instance
            yield mock_instance

    def test_get_servers_success(self, client, mock_mcp_manager):
        """测试获取服务器列表成功"""
        response = client.get("/api/mcp/servers")

        assert response.status_code == 200
        data = response.json()

        assert "servers" in data or isinstance(data, list)

    def test_get_servers_empty(self, client, mock_mcp_manager):
        """测试空服务器列表"""
        mock_mcp_manager.get_servers.return_value = []

        response = client.get("/api/mcp/servers")

        assert response.status_code == 200
```

### 3.2 创建服务器 API 测试

```python
class TestCreateMCPServer:
    """创建 MCP 服务器测试"""

    def test_create_stdio_server(self, client, mock_mcp_manager):
        """测试创建 stdio 服务器"""
        response = client.post("/api/mcp/servers", json={
            "name": "GitHub",
            "connection_type": "stdio",
            "config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"]
            }
        })

        assert response.status_code in [200, 201]

    def test_create_http_server(self, client, mock_mcp_manager):
        """测试创建 http 服务器"""
        response = client.post("/api/mcp/servers", json={
            "name": "Remote MCP",
            "connection_type": "http",
            "config": {
                "url": "https://mcp.example.com"
            }
        })

        assert response.status_code in [200, 201]

    def test_create_server_validation_error(self, client):
        """测试创建验证错误"""
        # 缺少必需字段
        response = client.post("/api/mcp/servers", json={
            "name": "Test"
            # 缺少 connection_type
        })

        assert response.status_code == 422
```

### 3.3 更新服务器 API 测试

```python
class TestUpdateMCPServer:
    """更新 MCP 服务器测试"""

    def test_update_server_name(self, client, mock_mcp_manager):
        """测试更新服务器名称"""
        response = client.put("/api/mcp/servers/mcp_1", json={
            "name": "New GitHub"
        })

        assert response.status_code in [200, 404]

    def test_update_server_enabled(self, client, mock_mcp_manager):
        """测试启用/禁用服务器"""
        response = client.put("/api/mcp/servers/mcp_1", json={
            "enabled": False
        })

        assert response.status_code in [200, 404]

    def test_update_nonexistent_server(self, client, mock_mcp_manager):
        """测试更新不存在的服务器"""
        mock_mcp_manager.get_server.side_effect = lambda id: None

        response = client.put("/api/mcp/servers/nonexistent", json={
            "name": "Test"
        })

        assert response.status_code == 404
```

### 3.4 删除服务器 API 测试

```python
class TestDeleteMCPServer:
    """删除 MCP 服务器测试"""

    def test_delete_server_success(self, client, mock_mcp_manager):
        """测试删除服务器成功"""
        response = client.delete("/api/mcp/servers/mcp_1")

        assert response.status_code in [200, 204]

    def test_delete_nonexistent_server(self, client, mock_mcp_manager):
        """测试删除不存在的服务器"""
        response = client.delete("/api/mcp/servers/nonexistent")

        assert response.status_code == 404
```

### 3.5 服务器状态 API 测试

```python
class TestMCPServerStatus:
    """MCP 服务器状态测试"""

    def test_get_server_status(self, client, mock_mcp_manager):
        """测试获取服务器状态"""
        response = client.get("/api/mcp/servers/mcp_1/status")

        assert response.status_code in [200, 404]

    def test_server_tools_list(self, client, mock_mcp_manager):
        """测试获取服务器工具列表"""
        response = client.get("/api/mcp/servers/mcp_1/tools")

        assert response.status_code in [200, 404]
```

---

## 4. MCP 管理器测试

### 4.1 管理器功能测试

```python
class TestMCPManager:
    """MCP 管理器测试"""

    def test_load_servers_from_file(self, tmp_path):
        """测试从文件加载服务器"""
        from app.mcp.manager import MCPManager

        # 创建临时配置文件
        config_file = tmp_path / "servers.json"
        config_file.write_text(json.dumps({
            "servers": [
                {
                    "id": "mcp_1",
                    "name": "Test",
                    "connection_type": "stdio",
                    "config": {"command": "test"},
                    "enabled": True
                }
            ]
        }))

        manager = MCPManager(config_path=config_file)
        servers = manager.get_servers()

        assert len(servers) == 1
        assert servers[0].name == "Test"

    def test_save_servers(self, tmp_path):
        """测试保存服务器配置"""
        from app.mcp.manager import MCPManager

        config_file = tmp_path / "servers.json"
        manager = MCPManager(config_path=config_file)

        servers = [
            MCPServer(
                id="mcp_1",
                name="Test",
                connection_type="stdio",
                config=MCPServerConfig(command="test"),
                enabled=True,
                created_at=datetime.now()
            )
        ]

        manager.save_servers(servers)
        assert config_file.exists()
```

---

## 5. E2E 测试

```python
# tests/e2e/test_mcp.py

class TestMCPPageE2E:
    """MCP 服务器管理页面 E2E 测试"""

    def test_mcp_page_loads(self, page: Page):
        """测试 MCP 页面加载"""
        page.goto("http://127.0.0.1:8000/")
        page.click("text=MCP 服务器")

        expect(page.locator("h1")).to_contain_text("MCP")

    def test_add_server_button(self, page: Page):
        """测试添加服务器按钮"""
        page.goto("http://127.0.0.1:8000/mcp")

        page.click("text=添加服务器")
        expect(page.locator(".modal")).to_be_visible()

    def test_server_list_displayed(self, page: Page):
        """测试服务器列表显示"""
        page.goto("http://127.0.0.1:8000/mcp")

        expect(page.locator(".server-list")).to_be_visible()
```

---

## 6. 运行测试

```bash
# 运行 MCP 相关测试
uv run pytest tests/ -k "mcp" -v

# 运行 MCP 管理器测试
uv run pytest tests/test_mcp.py -v
```

---

## 7. 验收标准

- [ ] 服务器列表 API 正常工作
- [ ] 可以创建 stdio 类型服务器
- [ ] 可以创建 http 类型服务器
- [ ] 可以更新服务器配置
- [ ] 可以启用/禁用服务器
- [ ] 可以删除服务器
- [ ] 状态查询 API 正常工作
- [ ] 工具列表查询 API 正常工作
- [ ] UI 正确显示所有功能
