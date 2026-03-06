"""
后端单元测试 - 消息解析器测试

测试消息解析和处理相关功能，包括：
- MessageType 枚举
- StreamMessage 数据类
- 消息类型识别
- 消息链构建
- 会话文件解析
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.claude_runner.client import (
    MessageType,
    StreamMessage,
    TaskResult,
    QuestionData,
    QuestionOption,
    AskUserQuestion,
    QuestionStatus,
    ClaudeCodeClient,
    PermissionMode,
)


class TestMessageType:
    """消息类型枚举测试"""

    def test_message_type_values(self):
        """测试消息类型枚举值"""
        assert MessageType.TEXT.value == "text"
        assert MessageType.TOOL_USE.value == "tool_use"
        assert MessageType.TOOL_RESULT.value == "tool_result"
        assert MessageType.THINKING.value == "thinking"
        assert MessageType.ERROR.value == "error"
        assert MessageType.COMPLETE.value == "complete"

    def test_message_type_from_value(self):
        """测试从值获取消息类型"""
        assert MessageType("text") == MessageType.TEXT
        assert MessageType("tool_use") == MessageType.TOOL_USE
        assert MessageType("complete") == MessageType.COMPLETE


class TestStreamMessage:
    """StreamMessage 数据类测试"""

    def test_text_message_creation(self):
        """测试创建文本消息"""
        msg = StreamMessage(
            type=MessageType.TEXT,
            content="Hello, world!",
        )

        assert msg.type == MessageType.TEXT
        assert msg.content == "Hello, world!"
        assert msg.timestamp is not None

    def test_tool_use_message_creation(self):
        """测试创建工具使用消息"""
        msg = StreamMessage(
            type=MessageType.TOOL_USE,
            content="调用 Read 工具",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
        )

        assert msg.type == MessageType.TOOL_USE
        assert msg.tool_name == "Read"
        assert msg.tool_input == {"file_path": "/test.py"}

    def test_tool_result_message_creation(self):
        """测试创建工具结果消息"""
        msg = StreamMessage(
            type=MessageType.TOOL_RESULT,
            content="文件内容...",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
        )

        assert msg.type == MessageType.TOOL_RESULT

    def test_error_message_creation(self):
        """测试创建错误消息"""
        msg = StreamMessage(
            type=MessageType.ERROR,
            content="文件不存在",
        )

        assert msg.type == MessageType.ERROR
        assert msg.content == "文件不存在"

    def test_complete_message_creation(self):
        """测试创建完成消息"""
        msg = StreamMessage(
            type=MessageType.COMPLETE,
            content="任务完成",
            metadata={
                "session_id": "session-123",
                "cost_usd": 0.05,
                "duration_ms": 2000,
                "files_changed": ["file1.py"],
                "tools_used": ["Read", "Write"],
            },
        )

        assert msg.type == MessageType.COMPLETE
        assert msg.metadata["session_id"] == "session-123"
        assert msg.metadata["cost_usd"] == 0.05

    def test_message_with_question(self):
        """测试带问题数据的消息"""
        question_data = QuestionData(
            question_id="q1",
            question_text="是否继续?",
            type="boolean",
        )

        msg = StreamMessage(
            type=MessageType.TEXT,
            content="请确认",
            question=question_data,
        )

        assert msg.question is not None
        assert msg.question.question_id == "q1"


class TestTaskResult:
    """TaskResult 数据类测试"""

    def test_task_result_success(self):
        """测试成功任务结果"""
        result = TaskResult(
            success=True,
            message="任务完成",
            session_id="session-123",
            cost_usd=0.05,
            duration_ms=2000,
            files_changed=["file1.py"],
            tools_used=["Read", "Write"],
        )

        assert result.success is True
        assert result.session_id == "session-123"
        assert result.cost_usd == 0.05

    def test_task_result_failure(self):
        """测试失败任务结果"""
        result = TaskResult(
            success=False,
            message="任务失败",
            session_id=None,
        )

        assert result.success is False
        assert result.message == "任务失败"


class TestQuestionOption:
    """QuestionOption 测试"""

    def test_question_option_creation(self):
        """测试创建问答选项"""
        option = QuestionOption(
            id="yes",
            label="是",
            description="确认操作",
            default=True,
        )

        assert option.id == "yes"
        assert option.label == "是"
        assert option.default is True

    def test_question_option_defaults(self):
        """测试问答选项默认值"""
        option = QuestionOption()

        assert option.id == ""
        assert option.label == ""
        assert option.description == ""
        assert option.default is None


class TestQuestionData:
    """QuestionData 测试"""

    def test_question_data_creation(self):
        """测试创建问题数据"""
        question = QuestionData(
            question_id="q1",
            question_text="是否继续?",
            type="boolean",
            header="确认",
            description="请确认是否继续执行",
            required=True,
        )

        assert question.question_id == "q1"
        assert question.question_text == "是否继续?"
        assert question.type == "boolean"
        assert question.required is True


class TestAskUserQuestion:
    """AskUserQuestion 测试"""

    def test_ask_user_question_creation(self):
        """测试创建用户问答"""
        question = AskUserQuestion(
            question_id="q1",
            question_text="选择操作",
            type="choice",
            header="操作选择",
            description="请选择要执行的操作",
            required=True,
            options=[
                QuestionOption(id="a", label="选项 A"),
                QuestionOption(id="b", label="选项 B"),
            ],
        )

        assert question.question_id == "q1"
        assert len(question.options) == 2
        assert question.options[0].id == "a"


class TestQuestionStatus:
    """QuestionStatus 枚举测试"""

    def test_question_status_values(self):
        """测试问题状态枚举值"""
        assert QuestionStatus.PENDING.value == "pending"
        assert QuestionStatus.SHOWING.value == "showing"
        assert QuestionStatus.SHOWING_UPPER.value == "showing_upper"
        assert QuestionStatus.ANSWERED.value == "answered"
        assert QuestionStatus.TIMEOUT.value == "timeout"
        assert QuestionStatus.CANCELLED.value == "cancelled"


class TestClaudeCodeClientMessageHandling:
    """ClaudeCodeClient 消息处理测试"""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """测试客户端初始化"""
        client = ClaudeCodeClient(
            working_dir="/test/workspace",
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
        )

        assert client.working_dir == "/test/workspace"
        assert "Read" in client.allowed_tools
        assert client.permission_mode == "acceptEdits"

    @pytest.mark.asyncio
    async def test_default_permission_mode(self):
        """测试默认权限模式"""
        client = ClaudeCodeClient()
        # 默认是 acceptEdits
        assert client.permission_mode == "acceptEdits"

    @pytest.mark.asyncio
    async def test_session_id_management(self):
        """测试会话 ID 管理"""
        client = ClaudeCodeClient()

        # 初始无会话 ID
        assert client.get_session_id() is None

        # 设置会话 ID
        client.set_session_id("test-session-123")
        assert client.get_session_id() == "test-session-123"

    @pytest.mark.asyncio
    async def test_is_waiting_answer_default(self):
        """测试默认等待状态"""
        client = ClaudeCodeClient()
        assert client.is_waiting_answer() is False

    @pytest.mark.asyncio
    async def test_pending_question_id_default(self):
        """测试默认待处理问题 ID"""
        client = ClaudeCodeClient()
        assert client.get_pending_question_id() is None


class TestMessageChainBuilding:
    """消息链构建测试"""

    def test_stream_message_list(self):
        """测试消息列表构建"""
        messages = [
            StreamMessage(type=MessageType.TEXT, content="第一段"),
            StreamMessage(type=MessageType.THINKING, content="思考中..."),
            StreamMessage(type=MessageType.TEXT, content="第二段"),
            StreamMessage(type=MessageType.TOOL_USE, content="调用工具", tool_name="Read"),
            StreamMessage(type=MessageType.COMPLETE, content="完成"),
        ]

        assert len(messages) == 5

        # 验证消息类型
        assert messages[0].type == MessageType.TEXT
        assert messages[3].type == MessageType.TOOL_USE
        assert messages[4].type == MessageType.COMPLETE

    def test_message_sequence_tracking(self):
        """测试消息序列追踪"""
        messages = []
        message_count = 0

        # 模拟消息流
        for i in range(5):
            msg = StreamMessage(
                type=MessageType.TEXT,
                content=f"消息 {i}",
            )
            messages.append(msg)
            message_count += 1

        assert message_count == 5
        assert len(messages) == 5


class TestMessageTypeDetection:
    """消息类型识别测试"""

    def test_detect_text_message(self):
        """测试识别文本消息"""
        msg = StreamMessage(type=MessageType.TEXT, content="Hello")
        assert msg.type == MessageType.TEXT

    def test_detect_tool_use_message(self):
        """测试识别工具使用消息"""
        msg = StreamMessage(
            type=MessageType.TOOL_USE,
            content="调用工具",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
        )
        assert msg.type == MessageType.TOOL_USE
        assert msg.tool_name == "Read"

    def test_detect_error_message(self):
        """测试识别错误消息"""
        msg = StreamMessage(
            type=MessageType.ERROR,
            content="错误: 文件不存在",
        )
        assert msg.type == MessageType.ERROR

    def test_detect_complete_message(self):
        """测试识别完成消息"""
        msg = StreamMessage(
            type=MessageType.COMPLETE,
            content="任务完成",
            metadata={"session_id": "sess-123"},
        )
        assert msg.type == MessageType.COMPLETE
        assert msg.metadata["session_id"] == "sess-123"


class TestPermissionMode:
    """权限模式测试"""

    def test_permission_mode_types(self):
        """测试权限模式类型"""
        # 测试不同的权限模式
        modes = ["default", "acceptEdits", "plan", "bypassPermissions"]

        for mode in modes:
            client = ClaudeCodeClient(permission_mode=mode)
            assert client.permission_mode == mode


class TestJSONLMessageParsing:
    """JSONL 消息解析测试"""

    def test_parse_user_message(self):
        """测试解析用户消息"""
        line = json.dumps({
            "type": "user",
            "sessionId": "sess-123",
            "uuid": "msg-uuid-1",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
            },
        })

        data = json.loads(line)
        assert data["type"] == "user"
        assert data["sessionId"] == "sess-123"

    def test_parse_assistant_message(self):
        """测试解析助手消息"""
        line = json.dumps({
            "type": "assistant",
            "sessionId": "sess-123",
            "uuid": "msg-uuid-2",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Hi there!"}],
            },
        })

        data = json.loads(line)
        assert data["type"] == "assistant"

    def test_parse_tool_use_message(self):
        """测试解析工具使用消息"""
        line = json.dumps({
            "type": "assistant",
            "sessionId": "sess-123",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "Read",
                        "input": {"file_path": "/test.py"},
                    }
                ],
            },
        })

        data = json.loads(line)
        content = data["message"]["content"]
        assert content[0]["type"] == "tool_use"
        assert content[0]["name"] == "Read"


class TestMessageContentTypes:
    """消息内容类型测试"""

    def test_text_content_parsing(self):
        """测试文本内容解析"""
        content = [{"type": "text", "text": "Hello world"}]

        for block in content:
            if block["type"] == "text":
                assert block["text"] == "Hello world"

    def test_thinking_content_parsing(self):
        """测试思考内容解析"""
        content = [{"type": "thinking", "thinking": "分析问题中..."}]

        for block in content:
            if block["type"] == "thinking":
                assert "分析问题" in block["thinking"]

    def test_tool_use_content_parsing(self):
        """测试工具使用内容解析"""
        content = [
            {
                "type": "tool_use",
                "id": "tool-1",
                "name": "Write",
                "input": {"file_path": "/new.py", "content": "print('hello')"},
            }
        ]

        for block in content:
            if block["type"] == "tool_use":
                assert block["name"] == "Write"
                assert block["input"]["file_path"] == "/new.py"

    def test_tool_result_content_parsing(self):
        """测试工具结果内容解析"""
        content = [
            {
                "type": "tool_result",
                "tool_use_id": "tool-1",
                "content": "File content here",
                "is_error": False,
            }
        ]

        for block in content:
            if block["type"] == "tool_result":
                assert "File content here" in block["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
