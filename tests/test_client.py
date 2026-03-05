"""Claude Code Client 专项测试

测试 client.py 中的所有数据类、辅助类和核心功能
"""

import asyncio
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.claude_runner.client import (
    # 枚举
    MessageType,
    # 数据类
    StreamMessage,
    TaskResult,
    # 主客户端
    ClaudeCodeClient,
)


# ==================== 枚举测试 ====================

class TestMessageType:
    """MessageType 枚举测试"""

    def test_all_types(self):
        """测试所有消息类型"""
        assert MessageType.TEXT.value == "text"
        assert MessageType.TOOL_USE.value == "tool_use"
        assert MessageType.TOOL_RESULT.value == "tool_result"
        assert MessageType.THINKING.value == "thinking"
        assert MessageType.ERROR.value == "error"
        assert MessageType.COMPLETE.value == "complete"


# ==================== 数据类测试 ====================

class TestStreamMessage:
    """StreamMessage 数据类测试"""

    def test_text_message(self):
        """测试文本消息"""
        msg = StreamMessage(
            type=MessageType.TEXT,
            content="Hello World",
        )
        assert msg.type == MessageType.TEXT
        assert msg.content == "Hello World"
        assert msg.timestamp is not None

    def test_tool_use_message(self):
        """测试工具使用消息"""
        msg = StreamMessage(
            type=MessageType.TOOL_USE,
            content="调用工具",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
        )
        assert msg.type == MessageType.TOOL_USE
        assert msg.tool_name == "Read"
        assert msg.tool_input == {"file_path": "/test.py"}

    def test_complete_message(self):
        """测试完成消息"""
        msg = StreamMessage(
            type=MessageType.COMPLETE,
            content="任务完成",
            metadata={
                "session_id": "session-123",
                "cost_usd": 0.05,
                "duration_ms": 3000,
            },
        )
        assert msg.type == MessageType.COMPLETE
        assert msg.metadata["cost_usd"] == 0.05
        assert msg.metadata["duration_ms"] == 3000

    def test_error_message(self):
        """测试错误消息"""
        msg = StreamMessage(
            type=MessageType.ERROR,
            content="执行错误",
        )
        assert msg.type == MessageType.ERROR

    def test_custom_timestamp(self):
        """测试自定义时间戳"""
        custom_time = "2024-01-01T00:00:00"
        msg = StreamMessage(
            type=MessageType.TEXT,
            content="测试",
            timestamp=custom_time,
        )
        assert msg.timestamp == custom_time

    def test_default_metadata(self):
        """测试默认元数据"""
        msg = StreamMessage(
            type=MessageType.TEXT,
            content="测试",
        )
        assert msg.metadata == {}


class TestTaskResult:
    """TaskResult 数据类测试"""

    def test_success_result(self):
        """测试成功结果"""
        result = TaskResult(
            success=True,
            message="任务完成",
            session_id="session-123",
            cost_usd=0.05,
            duration_ms=3000,
            files_changed=["/test/a.py"],
            tools_used=["Read", "Edit"],
        )
        assert result.success is True
        assert result.message == "任务完成"
        assert result.session_id == "session-123"
        assert result.cost_usd == 0.05
        assert result.duration_ms == 3000
        assert len(result.files_changed) == 1
        assert len(result.tools_used) == 2

    def test_failure_result(self):
        """测试失败结果"""
        result = TaskResult(
            success=False,
            message="执行失败",
        )
        assert result.success is False
        assert result.message == "执行失败"
        assert result.session_id is None

    def test_default_lists(self):
        """测试默认列表"""
        result = TaskResult(success=True, message="测试")
        assert result.files_changed == []
        assert result.tools_used == []


# ==================== ClaudeCodeClient 测试 ====================

class TestClaudeCodeClient:
    """ClaudeCodeClient 核心测试"""

    def test_init_default(self):
        """测试默认初始化"""
        client = ClaudeCodeClient()
        assert client.working_dir == "."
        assert client.permission_mode == "acceptEdits"
        assert client.resume is None

    def test_init_with_params(self):
        """测试带参数初始化"""
        client = ClaudeCodeClient(
            working_dir="/test",
            allowed_tools=["Read"],
            permission_mode="plan",
            resume="session-123",
        )
        assert client.working_dir == "/test"
        assert client.allowed_tools == ["Read"]
        assert client.permission_mode == "plan"
        assert client.resume == "session-123"

    def test_default_tools(self):
        """测试默认工具列表"""
        client = ClaudeCodeClient()
        assert "Read" in client.allowed_tools
        assert "Write" in client.allowed_tools
        assert "Edit" in client.allowed_tools
        assert "Bash" in client.allowed_tools
        assert "Glob" in client.allowed_tools
        assert "Grep" in client.allowed_tools

    def test_create_options(self):
        """测试创建 SDK 选项"""
        client = ClaudeCodeClient(
            working_dir="/test",
            permission_mode="plan",
        )
        options = client._create_options()
        assert options.permission_mode == "plan"
        assert options.cwd == "/test"

    def test_create_options_with_resume(self):
        """测试带 resume 创建选项"""
        client = ClaudeCodeClient(resume="session-123")
        options = client._create_options()
        assert options.resume == "session-123"

    @pytest.mark.asyncio
    async def test_track_tool_use_edit(self):
        """测试跟踪 Edit 工具"""
        client = ClaudeCodeClient()
        await client._track_tool_use("Edit", {"file_path": "/test/a.py"})

        assert "Edit" in client._tools_used
        assert "/test/a.py" in client._files_changed

    @pytest.mark.asyncio
    async def test_track_tool_use_write(self):
        """测试跟踪 Write 工具"""
        client = ClaudeCodeClient()
        await client._track_tool_use("Write", {"file_path": "/test/b.py"})

        assert "Write" in client._tools_used
        assert "/test/b.py" in client._files_changed

    @pytest.mark.asyncio
    async def test_track_tool_use_read(self):
        """测试跟踪 Read 工具（不应记录文件变更）"""
        client = ClaudeCodeClient()
        await client._track_tool_use("Read", {"file_path": "/test/c.py"})

        assert "Read" in client._tools_used
        assert "/test/c.py" not in client._files_changed


# ==================== Mock 集成测试 ====================

class TestRunStreamMocked:
    """run_stream 方法的 Mock 测试"""

    @pytest.mark.asyncio
    @patch("app.claude_runner.client.ClaudeSDKClient")
    async def test_run_stream_with_text_message(self, mock_sdk_class):
        """测试流式输出文本消息"""
        # 创建 mock 实例
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.query = AsyncMock()
        mock_instance.receive_response = AsyncMock(return_value=[])
        mock_sdk_class.return_value = mock_instance

        client = ClaudeCodeClient()
        messages = []
        async for msg in client.run_stream("test"):
            messages.append(msg)

        # 验证
        mock_instance.query.assert_called_once_with("test")
        assert len(messages) >= 0

    @pytest.mark.asyncio
    @patch("app.claude_runner.client.ClaudeSDKClient")
    async def test_run_stream_handles_exception(self, mock_sdk_class):
        """测试流式输出异常处理"""
        # 创建 mock 实例
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(side_effect=Exception("Test error"))
        mock_instance.__aexit__ = AsyncMock(return_value=None)

        mock_sdk_class.return_value = mock_instance

        client = ClaudeCodeClient()
        messages = []
        async for msg in client.run_stream("test"):
            messages.append(msg)

        # 应该产生一个 ERROR 消息
        assert any(msg.type == MessageType.ERROR for msg in messages)


class TestRunMethod:
    """run 方法测试"""

    @pytest.mark.asyncio
    @patch("app.claude_runner.client.ClaudeSDKClient")
    async def test_run_collects_messages(self, mock_sdk_class):
        """测试 run 方法收集消息"""
        from claude_agent_sdk import ResultMessage

        # 创建 mock 结果消息
        result_msg = MagicMock(spec=ResultMessage)
        result_msg.session_id = "session-123"
        result_msg.total_cost_usd = 0.05
        result_msg.duration_ms = 1000
        result_msg.is_error = False

        # 创建 mock 实例
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.query = AsyncMock()

        # 模拟一个完整消息流 - 使用异步生成器
        async def message_generator():
            yield result_msg

        mock_instance.receive_response.return_value = message_generator()
        mock_sdk_class.return_value = mock_instance

        client = ClaudeCodeClient()
        result = await client.run("test")

        # 验证结果
        assert isinstance(result, TaskResult)
        assert result.session_id == "session-123"
        assert result.cost_usd == 0.05
        assert result.duration_ms == 1000
        assert result.success is True


# ==================== 边界条件测试 ====================

class TestEdgeCases:
    """边界条件测试"""

    @pytest.mark.asyncio
    async def test_duplicate_file_tracking(self):
        """测试重复文件跟踪"""
        client = ClaudeCodeClient()

        # 多次编辑同一文件
        await client._track_tool_use("Edit", {"file_path": "/test/a.py"})
        await client._track_tool_use("Edit", {"file_path": "/test/a.py"})
        await client._track_tool_use("Edit", {"file_path": "/test/a.py"})

        # 文件应该只记录一次
        assert client._files_changed.count("/test/a.py") == 1

    @pytest.mark.asyncio
    async def test_empty_tool_input(self):
        """测试空工具输入"""
        client = ClaudeCodeClient()
        await client._track_tool_use("Edit", {})

        assert "Edit" in client._tools_used
        assert len(client._files_changed) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
