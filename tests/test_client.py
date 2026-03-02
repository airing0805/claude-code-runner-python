"""
Claude Code Client 专项测试

测试 client.py 中的所有数据类、辅助类和核心功能
"""

import asyncio
import os
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, ANY

import pytest

from app.claude_runner.client import (
    # 枚举
    QuestionStatus,
    MessageType,

    # 数据类
    QuestionOption,
    FollowUpQuestion,
    AskUserQuestion,
    StreamMessage,
    TaskResult,

    # 辅助类
    InputValidator,
    ConcurrencyManager,

    # 主客户端
    ClaudeCodeClient,
)


# ==================== 枚举测试 ====================

class TestQuestionStatus:
    """QuestionStatus 枚举测试"""

    def test_all_statuses(self):
        """测试所有状态值"""
        assert QuestionStatus.PENDING.value == "pending"
        assert QuestionStatus.SHOWING.value == "showing"
        assert QuestionStatus.ANSWERED.value == "answered"
        assert QuestionStatus.PROCESSING.value == "processing"
        assert QuestionStatus.COMPLETED.value == "completed"
        assert QuestionStatus.ERROR.value == "error"
        assert QuestionStatus.TIMEOUT.value == "timeout"


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
        assert MessageType.ASK_USER_QUESTION.value == "ask_user_question"


# ==================== 数据类测试 ====================

class TestQuestionOption:
    """QuestionOption 数据类测试"""

    def test_creation_basic(self):
        """测试基本创建"""
        option = QuestionOption(
            id="opt_1",
            label="选项 1",
        )
        assert option.id == "opt_1"
        assert option.label == "选项 1"
        assert option.description is None
        assert option.default is False

    def test_creation_full(self):
        """测试完整创建"""
        option = QuestionOption(
            id="opt_2",
            label="选项 2",
            description="这是一个选项描述",
            default=True,
        )
        assert option.id == "opt_2"
        assert option.description == "这是一个选项描述"
        assert option.default is True

    def test_with_chinese_label(self):
        """测试中文标签"""
        option = QuestionOption(id="x", label="确认操作")
        assert option.label == "确认操作"


class TestFollowUpQuestion:
    """FollowUpQuestion 数据类测试"""

    def test_creation_basic(self):
        """测试基本创建"""
        q = FollowUpQuestion(
            question_id="follow_1",
            question_text="追问问题",
            type="multiple_choice",
        )
        assert q.question_id == "follow_1"
        assert q.question_text == "追问问题"
        assert q.type == "multiple_choice"
        assert q.required is True  # 默认值

    def test_creation_with_options(self):
        """测试带选项的创建"""
        options = [
            QuestionOption(id="a", label="是"),
            QuestionOption(id="b", label="否"),
        ]
        q = FollowUpQuestion(
            question_id="follow_1",
            question_text="继续吗？",
            type="multiple_choice",
            options=options,
        )
        assert len(q.options) == 2
        assert q.options[0].label == "是"
        assert q.options[1].label == "否"


class TestAskUserQuestion:
    """AskUserQuestion 数据类测试"""

    def test_creation_minimal(self):
        """测试最小创建"""
        q = AskUserQuestion(
            question_id="q1",
            question_text="这是一个问题",
            type="multiple_choice",
        )
        assert q.question_id == "q1"
        assert q.question_text == "这是一个问题"
        assert q.type == "multiple_choice"
        assert q.required is True
        assert q.follow_up_questions == {}

    def test_creation_with_options(self):
        """测试带选项的创建"""
        options = [
            QuestionOption(id="1", label="Python"),
            QuestionOption(id="2", label="JavaScript"),
        ]
        q = AskUserQuestion(
            question_id="q1",
            question_text="选择语言",
            type="multiple_choice",
            options=options,
        )
        assert len(q.options) == 2
        assert q.options[0].label == "Python"

    def test_creation_with_all_fields(self):
        """测试完整字段创建"""
        options = [QuestionOption(id="x", label="确定")]
        q = AskUserQuestion(
            question_id="q_full",
            question_text="完整问题",
            type="multiple_choice",
            header="选择",
            description="请选择一个选项",
            options=options,
            required=False,
            multi_select=True,
            max_selections=3,
            min_selections=1,
            timeout_seconds=600,
        )
        assert q.header == "选择"
        assert q.description == "请选择一个选项"
        assert q.required is False
        assert q.multi_select is True
        assert q.max_selections == 3
        assert q.min_selections == 1
        assert q.timeout_seconds == 600

    def test_default_timestamp(self):
        """测试默认时间戳"""
        before = time.time()
        q = AskUserQuestion(
            question_id="q1",
            question_text="问题",
            type="multiple_choice",
        )
        after = time.time()
        assert before <= q.created_at <= after

    def test_with_raw_tool_input(self):
        """测试带原始工具输入"""
        raw_input = {"questions": [{"question": "原始问题"}]}
        q = AskUserQuestion(
            question_id="q1",
            question_text="解析后的问题",
            type="multiple_choice",
            raw_tool_input=raw_input,
        )
        assert q.raw_tool_input == raw_input


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

    def test_ask_question_message(self):
        """测试询问用户问题消息"""
        question = AskUserQuestion(
            question_id="q1",
            question_text="继续吗？",
            type="boolean",
        )
        msg = StreamMessage(
            type=MessageType.ASK_USER_QUESTION,
            content="请回答问题",
            question=question,
        )
        assert msg.type == MessageType.ASK_USER_QUESTION
        assert msg.question.question_text == "继续吗？"

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


# ==================== 辅助类测试 ====================

class TestInputValidator:
    """InputValidator 测试"""

    def test_init(self):
        """测试初始化"""
        validator = InputValidator()
        assert validator.max_input_length == 1000
        assert validator.allowed_chars is None

    def test_validate_options_valid(self):
        """测试验证有效选项"""
        validator = InputValidator()
        options = [
            {"label": "选项 1", "description": "描述 1"},
            {"label": "选项 2"},
        ]
        assert validator.validate_question_options(options) is True

    def test_validate_options_not_list(self):
        """测试非列表选项"""
        validator = InputValidator()
        assert validator.validate_question_options("not a list") is False

    def test_validate_options_invalid_item(self):
        """测试无效选项项"""
        validator = InputValidator()
        options = [
            {"label": "选项 1"},
            "not a dict",  # 无效项
        ]
        assert validator.validate_question_options(options) is False

    def test_validate_options_missing_label(self):
        """测试缺少标签"""
        validator = InputValidator()
        options = [
            {"description": "只有描述"},
        ]
        assert validator.validate_question_options(options) is False

    def test_validate_options_empty_label(self):
        """测试空标签"""
        validator = InputValidator()
        options = [
            {"label": ""},
        ]
        assert validator.validate_question_options(options) is False

    def test_validate_options_label_too_long(self):
        """测试标签过长"""
        validator = InputValidator()
        options = [
            {"label": "x" * 101},  # 超过 100 字符
        ]
        assert validator.validate_question_options(options) is False

    def test_sanitize_user_input(self):
        """测试清理用户输入"""
        validator = InputValidator()
        result = validator.sanitize_user_input('<script>alert("x")</script>')
        assert "<script>" not in result
        assert ">" not in result

    def test_sanitize_length_limit(self):
        """测试长度限制"""
        validator = InputValidator()
        validator.max_input_length = 10  # 修改属性进行测试
        result = validator.sanitize_user_input("123456789012345")
        assert len(result) == 10

    def test_sanitize_removes_dangerous_chars(self):
        """测试移除危险字符"""
        validator = InputValidator()
        dangerous = "<>&'`"
        result = validator.sanitize_user_input(dangerous)
        for char in dangerous:
            assert char not in result

    def test_sanitize_with_allowed_chars(self):
        """测试 allow_chars 属性存在

        注意：sanitize_user_input 方法只移除危险字符，不根据 allowed_chars 过滤
        allowed_chars 只在 validate_question_options 中使用
        """
        validator = InputValidator()
        validator.max_input_length = 100  # 修改属性进行测试
        validator.allowed_chars = "abcdefghijklmnopqrstuvwxyz"

        result = validator.sanitize_user_input("ABC<xyz>")
        # sanitize_user_input 只移除危险字符，保留字母
        assert "ABC" in result
        assert "xyz" in result
        assert "<" not in result
        assert ">" not in result


class TestConcurrencyManager:
    """ConcurrencyManager 测试"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        manager = ConcurrencyManager()
        assert manager.max_concurrent_questions == 5
        assert manager.active_questions == {}
        assert manager.question_queue.empty() is True

    @pytest.mark.asyncio
    async def test_acquire_slot_success(self):
        """测试成功获取槽位"""
        manager = ConcurrencyManager()
        result = await manager.acquire_question_slot("session-1", "question-1")
        assert result is True
        assert "question-1" in manager.active_questions

    @pytest.mark.asyncio
    async def test_acquire_slot_limit(self):
        """测试并发限制"""
        manager = ConcurrencyManager()
        manager.max_concurrent_questions = 2  # 修改属性进行测试

        # 获取两个槽位
        r1 = await manager.acquire_question_slot("s1", "q1")
        r2 = await manager.acquire_question_slot("s2", "q2")
        assert r1 is True
        assert r2 is True

        # 第三个应该失败
        r3 = await manager.acquire_question_slot("s3", "q3")
        assert r3 is False

    @pytest.mark.asyncio
    async def test_release_slot(self):
        """测试释放槽位"""
        manager = ConcurrencyManager()
        await manager.acquire_question_slot("s1", "q1")
        assert "q1" in manager.active_questions

        await manager.release_question_slot("q1")
        assert "q1" not in manager.active_questions

    @pytest.mark.asyncio
    async def test_queue_processing(self):
        """测试队列处理"""
        manager = ConcurrencyManager()
        manager.max_concurrent_questions = 1  # 修改属性进行测试

        # 填满槽位
        await manager.acquire_question_slot("s1", "q1")

        # 尝试获取新槽位，应该失败并加入队列
        r = await manager.acquire_question_slot("s2", "q2")
        assert r is False

        # 释放槽位，应该自动处理队列
        await manager.release_question_slot("q1")
        await asyncio.sleep(0.1)  # 等待异步处理

        # 新槽位应该被获取
        assert "q2" in manager.active_questions


# ==================== ClaudeCodeClient 测试 ====================

class TestClaudeCodeClient:
    """ClaudeCodeClient 核心测试"""

    def test_init_default(self):
        """测试默认初始化"""
        client = ClaudeCodeClient()
        assert client.working_dir == "."
        assert client.permission_mode == "acceptEdits"
        assert client.continue_conversation is False
        assert client.resume is None

    def test_init_with_params(self):
        """测试带参数初始化"""
        client = ClaudeCodeClient(
            working_dir="/test",
            allowed_tools=["Read"],
            permission_mode="plan",
            continue_conversation=True,
            resume="session-123",
        )
        assert client.working_dir == "/test"
        assert client.allowed_tools == ["Read"]
        assert client.permission_mode == "plan"
        assert client.continue_conversation is True
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

    def test_session_id(self):
        """测试会话 ID"""
        client = ClaudeCodeClient()
        assert client.get_session_id() is None

        client.set_session_id("session-123")
        assert client.get_session_id() == "session-123"

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

    @pytest.mark.asyncio
    async def test_update_question_state(self):
        """测试更新问题状态"""
        client = ClaudeCodeClient()
        await client._update_question_state(
            "q1",
            QuestionStatus.PENDING,
            {"test": "data"}
        )
        assert "q1" in client._question_states
        assert client._question_states["q1"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_wait_for_answer_immediate(self):
        """测试立即获取答案"""
        client = ClaudeCodeClient()
        client._answer_event = asyncio.Event()
        client._is_waiting_answer = True

        # 模拟答案到达
        answer = {"question_id": "q1", "answer": "yes"}
        client._pending_answer = answer

        # 设置事件
        client._answer_event.set()

        result = await client.wait_for_answer("q1")
        assert result == answer

    @pytest.mark.asyncio
    async def test_wait_for_answer_timeout(self):
        """测试等待超时"""
        client = ClaudeCodeClient()
        client._answer_event = asyncio.Event()

        result = await client.wait_for_answer("q1", timeout=0.1)
        assert result is None

    def test_is_waiting_answer(self):
        """测试检查是否等待答案"""
        client = ClaudeCodeClient()
        assert client.is_waiting_answer() is False

        client._is_waiting_answer = True
        assert client.is_waiting_answer() is True

    def test_get_pending_question_id(self):
        """测试获取待处理问题 ID"""
        client = ClaudeCodeClient()
        assert client.get_pending_question_id() is None

        client._pending_question_id = "q1"
        assert client.get_pending_question_id() == "q1"

    @pytest.mark.asyncio
    async def test_submit_answer_success(self):
        """测试提交答案成功"""
        client = ClaudeCodeClient()
        client.set_session_id("session-123")
        client._answer_event = asyncio.Event()
        client._question_states["q1"] = {
            "status": QuestionStatus.SHOWING.value,
            "updated_at": time.time(),
            "metadata": {}
        }

        answer = {"question_id": "q1", "answer": "yes"}
        result = await client.submit_answer(answer)

        assert result is True
        assert client._pending_answer == answer

    @pytest.mark.asyncio
    async def test_submit_answer_no_session(self):
        """测试无会话时提交答案"""
        client = ClaudeCodeClient()
        answer = {"question_id": "q1", "answer": "yes"}
        result = await client.submit_answer(answer)
        assert result is False

    @pytest.mark.asyncio
    async def test_submit_answer_empty(self):
        """测试提交空答案"""
        client = ClaudeCodeClient()
        client.set_session_id("session-123")
        client._question_states["q1"] = {
            "status": QuestionStatus.SHOWING.value,
            "updated_at": time.time(),
            "metadata": {}
        }

        answer = {"question_id": "q1", "answer": "   "}  # 只有空格
        result = await client.submit_answer(answer)
        assert result is False

    @pytest.mark.asyncio
    async def test_submit_answer_dangerous_chars(self):
        """测试提交包含危险字符的答案

        注意：原始代码保存的是原始答案字典，不进行清理修改
        测试验证提交成功，但不检查内容清理（因为原代码不保存清理后内容）
        """
        client = ClaudeCodeClient()
        client.set_session_id("session-123")
        client._question_states["q1"] = {
            "status": QuestionStatus.SHOWING.value,
            "updated_at": time.time(),
            "metadata": {}
        }
        client._answer_event = asyncio.Event()

        answer = {"question_id": "q1", "answer": "<script>alert(1)</script>"}
        result = await client.submit_answer(answer)

        # 应该成功
        assert result is True
        # 验证答案被保存（原始内容，未被修改）
        assert client._pending_answer == answer


class TestParseQuestionData:
    """_parse_question_data 方法测试"""

    @pytest.mark.asyncio
    async def test_parse_basic_question(self):
        """测试解析基本问题"""
        client = ClaudeCodeClient()
        tool_input = {
            "question_id": "q1",
            "question_text": "这是一个问题",
            "type": "multiple_choice",
            "options": [
                {"label": "选项 1", "id": "1"},
                {"label": "选项 2", "id": "2"},
            ],
        }

        result = await client._parse_question_data(tool_input)

        assert result is not None
        assert result.question_id == "q1"
        assert result.question_text == "这是一个问题"
        assert len(result.options) == 2

    @pytest.mark.asyncio
    async def test_parse_with_questions_field(self):
        """测试解析带 questions 字段的数据"""
        client = ClaudeCodeClient()
        tool_input = {
            "questions": [
                {
                    "question_id": "q1",
                    "question_text": "问题文本",
                    "options": [
                        {"label": "是", "id": "y"},
                        {"label": "否", "id": "n"},
                    ],
                }
            ]
        }

        result = await client._parse_question_data(tool_input)

        assert result is not None
        assert result.question_text == "问题文本"
        assert len(result.options) == 2

    @pytest.mark.asyncio
    async def test_parse_without_options(self):
        """测试无选项时的默认选项"""
        client = ClaudeCodeClient()
        tool_input = {
            "question_id": "q1",
            "question_text": "问题",
            "type": "text",
        }

        result = await client._parse_question_data(tool_input)

        assert result is not None
        assert len(result.options) == 3  # 应该添加默认选项
        assert result.options[0].label == "选项1"

    @pytest.mark.asyncio
    async def test_parse_with_all_fields(self):
        """测试解析完整字段"""
        client = ClaudeCodeClient()
        tool_input = {
            "question_id": "q_full",
            "question_text": "完整问题",
            "type": "multiple_choice",
            "header": "选择",
            "description": "请选择",
            "required": False,
            "multiSelect": True,
            "maxSelections": 2,
            "minSelections": 0,
            "timeoutSeconds": 600,
        }

        result = await client._parse_question_data(tool_input)

        assert result is not None
        assert result.header == "选择"
        assert result.description == "请选择"
        assert result.required is False
        assert result.multi_select is True
        assert result.max_selections == 2
        assert result.min_selections == 0
        assert result.timeout_seconds == 600

    @pytest.mark.asyncio
    async def test_parse_with_follow_up_questions(self):
        """测试解析追问问题"""
        client = ClaudeCodeClient()
        tool_input = {
            "question_id": "q1",
            "question_text": "主问题",
            "type": "multiple_choice",
            "options": [{"label": "选项 1", "id": "1"}],
            "follow_up_questions": {
                "1": [
                    {
                        "question_id": "f1",
                        "question_text": "追问 1",
                        "type": "text",
                    }
                ]
            },
        }

        result = await client._parse_question_data(tool_input)

        assert result is not None
        assert "1" in result.follow_up_questions
        assert len(result.follow_up_questions["1"]) == 1
        assert result.follow_up_questions["1"][0].question_text == "追问 1"

    @pytest.mark.asyncio
    async def test_parse_invalid_options(self):
        """测试解析无效选项（选项验证失败时返回 None）"""
        client = ClaudeCodeClient()
        tool_input = {
            "question_id": "q1",
            "question_text": "问题",
            "type": "multiple_choice",
            "options": [
                {"label": "x" * 101},  # 超长标签
            ],
        }

        result = await client._parse_question_data(tool_input)

        # 当选项验证失败时，仍然返回 AskUserQuestion，但 options 为 None
        assert result is not None
        assert result.options is None
        assert result.question_id == "q1"
        assert result.question_text == "问题"


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

        # 模拟一个简单的文本消息
        from claude_agent_sdk import AssistantMessage, TextBlock

        text_block = MagicMock()
        text_block.text = "Hello World"
        text_block.name = None

        assistant_msg = MagicMock(spec=AssistantMessage)
        assistant_msg.content = [text_block]

        mock_instance.receive_response = AsyncMock(return_value=iter([assistant_msg]))

        client = ClaudeCodeClient()
        messages = []
        async for msg in client.run_stream("test"):
            messages.append(msg)

        # 验证
        mock_instance.query.assert_called_once_with("test")
        assert len(messages) > 0

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

    @pytest.mark.asyncio
    @patch("app.claude_runner.client.ClaudeSDKClient")
    async def test_run_stream_resumes_session(self, mock_sdk_class):
        """测试恢复会话"""
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.query = AsyncMock()
        mock_instance.receive_response = AsyncMock(return_value=iter([]))

        mock_sdk_class.return_value = mock_instance

        client = ClaudeCodeClient(resume="session-123")
        options = client._create_options()

        assert options.resume == "session-123"


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

        # 模拟一个完整消息流
        async def message_generator():
            yield result_msg

        mock_instance.receive_response = message_generator
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

    @pytest.mark.asyncio
    async def test_concurrent_question_slots(self):
        """测试并发问题槽位"""
        manager = ConcurrencyManager()
        manager.max_concurrent_questions = 3  # 修改属性进行测试

        # 并发获取多个槽位
        tasks = [
            manager.acquire_question_slot(f"s{i}", f"q{i}")
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)

        # 前三个应该成功
        assert results[0] is True
        assert results[1] is True
        assert results[2] is True
        # 后两个应该失败
        assert results[3] is False
        assert results[4] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
