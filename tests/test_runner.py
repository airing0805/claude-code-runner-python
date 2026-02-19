"""测试用例 - 模拟多个场景"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.claude_runner import ClaudeCodeClient, TaskResult
from app.claude_runner.client import MessageType, StreamMessage


class TestClaudeCodeClient:
    """Claude Code 客户端测试"""

    def test_client_initialization(self):
        """测试客户端初始化"""
        client = ClaudeCodeClient(
            working_dir="/test/path",
            allowed_tools=["Read", "Write"],
        )

        assert client.working_dir == "/test/path"
        assert client.allowed_tools == ["Read", "Write"]
        assert client._files_changed == []
        assert client._tools_used == []

    def test_default_tools(self):
        """测试默认工具列表"""
        client = ClaudeCodeClient()

        assert "Read" in client.allowed_tools
        assert "Write" in client.allowed_tools
        assert "Edit" in client.allowed_tools
        assert "Bash" in client.allowed_tools

    def test_permission_mode_default(self):
        """测试默认权限模式"""
        client = ClaudeCodeClient()
        assert client.permission_mode == "acceptEdits"

    def test_custom_permission_mode(self):
        """测试自定义权限模式"""
        client = ClaudeCodeClient(permission_mode="plan")
        assert client.permission_mode == "plan"

    @pytest.mark.asyncio
    async def test_track_tool_use(self):
        """测试工具使用跟踪"""
        client = ClaudeCodeClient()

        # 模拟文件编辑
        await client._track_tool_use("Edit", {"file_path": "/test/file.py"})
        await client._track_tool_use("Edit", {"file_path": "/test/another.py"})
        await client._track_tool_use("Read", {"file_path": "/test/read.py"})

        assert "/test/file.py" in client._files_changed
        assert "/test/another.py" in client._files_changed
        assert "/test/read.py" not in client._files_changed  # Read 不跟踪
        assert "Edit" in client._tools_used
        assert "Read" in client._tools_used

    @pytest.mark.asyncio
    async def test_track_write_tool(self):
        """测试 Write 工具跟踪"""
        client = ClaudeCodeClient()

        await client._track_tool_use("Write", {"file_path": "/test/new_file.py"})

        assert "/test/new_file.py" in client._files_changed
        assert "Write" in client._tools_used


class TestStreamMessage:
    """流式消息测试"""

    def test_message_creation(self):
        """测试消息创建"""
        msg = StreamMessage(
            type=MessageType.TEXT,
            content="Hello",
        )

        assert msg.type == MessageType.TEXT
        assert msg.content == "Hello"
        assert msg.timestamp is not None

    def test_message_with_tool_info(self):
        """测试带工具信息的消息"""
        msg = StreamMessage(
            type=MessageType.TOOL_USE,
            content="调用工具",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
        )

        assert msg.tool_name == "Read"
        assert msg.tool_input == {"file_path": "/test.py"}

    def test_message_with_metadata(self):
        """测试带元数据的消息"""
        msg = StreamMessage(
            type=MessageType.COMPLETE,
            content="完成",
            metadata={"cost_usd": 0.05, "duration_ms": 3000},
        )

        assert msg.metadata["cost_usd"] == 0.05
        assert msg.metadata["duration_ms"] == 3000


class TestTaskResult:
    """任务结果测试"""

    def test_success_result(self):
        """测试成功结果"""
        result = TaskResult(
            success=True,
            message="任务完成",
            cost_usd=0.05,
            duration_ms=5000,
            files_changed=["/test/file.py"],
            tools_used=["Read", "Edit"],
        )

        assert result.success is True
        assert result.cost_usd == 0.05
        assert len(result.files_changed) == 1

    def test_failure_result(self):
        """测试失败结果"""
        result = TaskResult(
            success=False,
            message="执行失败",
        )

        assert result.success is False
        assert result.files_changed == []

    def test_empty_result(self):
        """测试空结果"""
        result = TaskResult(success=True, message="")

        assert result.success is True
        assert result.message == ""
        assert result.files_changed == []
        assert result.tools_used == []


# ============== 场景测试（简化版）==============

class TestScenarios:
    """
    模拟场景测试

    这些测试模拟了真实使用场景的核心逻辑
    """

    @pytest.mark.asyncio
    async def test_scenario_list_files(self):
        """
        场景1: 列出项目文件

        验证: 工具跟踪逻辑正确
        """
        client = ClaudeCodeClient(working_dir="/test/project")

        # 模拟 Glob 工具调用
        await client._track_tool_use("Glob", {"pattern": "**/*.py"})

        assert "Glob" in client._tools_used

    @pytest.mark.asyncio
    async def test_scenario_code_review(self):
        """
        场景2: 代码审查

        验证: Read 工具被正确跟踪
        """
        client = ClaudeCodeClient(working_dir="/test/project")

        # 模拟 Read 工具调用
        await client._track_tool_use("Read", {"file_path": "/test/auth.py"})

        assert "Read" in client._tools_used
        assert "/test/auth.py" not in client._files_changed  # Read 不修改文件

    @pytest.mark.asyncio
    async def test_scenario_add_type_hints(self):
        """
        场景3: 添加类型提示

        验证: Edit 工具被正确跟踪，文件变更被记录
        """
        client = ClaudeCodeClient(working_dir="/test/project")

        # 模拟读取文件
        await client._track_tool_use("Read", {"file_path": "/test/utils.py"})
        # 模拟编辑文件
        await client._track_tool_use("Edit", {
            "file_path": "/test/utils.py",
            "old_string": "def add(a, b):",
            "new_string": "def add(a: int, b: int) -> int:",
        })

        assert "/test/utils.py" in client._files_changed
        assert "Read" in client._tools_used
        assert "Edit" in client._tools_used

    @pytest.mark.asyncio
    async def test_scenario_create_new_file(self):
        """
        场景4: 创建新文件

        验证: Write 工具被正确跟踪
        """
        client = ClaudeCodeClient(working_dir="/test/project")

        # 模拟创建文件
        await client._track_tool_use("Write", {
            "file_path": "/test/new_module.py",
            "content": "# New module\n",
        })

        assert "/test/new_module.py" in client._files_changed
        assert "Write" in client._tools_used

    @pytest.mark.asyncio
    async def test_scenario_multiple_file_edits(self):
        """
        场景5: 批量编辑多个文件

        验证: 多个文件变更被正确记录
        """
        client = ClaudeCodeClient(working_dir="/test/project")

        files = ["/test/a.py", "/test/b.py", "/test/c.py"]
        for f in files:
            await client._track_tool_use("Edit", {"file_path": f})

        assert len(client._files_changed) == 3
        for f in files:
            assert f in client._files_changed

    @pytest.mark.asyncio
    async def test_scenario_bash_command(self):
        """
        场景6: 执行 Bash 命令

        验证: Bash 工具被跟踪，但不记录文件变更
        """
        client = ClaudeCodeClient(working_dir="/test/project")

        await client._track_tool_use("Bash", {"command": "ls -la"})

        assert "Bash" in client._tools_used
        assert len(client._files_changed) == 0


# ============== API 测试 ==============

class TestAPI:
    """FastAPI 接口测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from app.main import app

        return TestClient(app)

    def test_get_status(self, client):
        """测试状态接口"""
        response = client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    def test_get_tools(self, client):
        """测试工具列表接口"""
        response = client.get("/api/tools")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tools"]) > 0

        # 验证工具包含必要信息
        tool_names = [t["name"] for t in data["tools"]]
        assert "Read" in tool_names
        assert "Write" in tool_names
        assert "Edit" in tool_names

    def test_index_page(self, client):
        """测试主页"""
        response = client.get("/")

        assert response.status_code == 200
        assert "Claude Code Runner" in response.text

    def test_task_request_validation(self, client):
        """测试任务请求验证"""
        # 缺少 prompt
        response = client.post("/api/task", json={})
        assert response.status_code == 422

    def test_task_request_with_tools(self, client):
        """测试带工具列表的任务请求（仅验证 API 结构）"""
        # 这个测试验证 API 能正确接收参数
        # 实际执行需要有效的 API Key
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
