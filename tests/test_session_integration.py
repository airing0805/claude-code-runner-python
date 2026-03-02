"""
会话集成测试

测试完整的会话生命周期，包括创建、发送消息、接收答案等
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.claude_runner.client import (
    ClaudeCodeClient,
    MessageType,
    StreamMessage,
    AskUserQuestion,
    QuestionStatus,
    QuestionOption,
)


class TestSessionLifecycle:
    """会话生命周期测试"""

    @pytest.mark.asyncio
    @patch("app.claude_runner.client.ClaudeSDKClient")
    async def test_create_new_session(self, mock_sdk_class):
        """测试创建新会话"""
        from claude_agent_sdk import ResultMessage

        # 创建 mock ResultMessage（包含 session_id）
        result_msg = MagicMock(spec=ResultMessage)
        result_msg.session_id = "new-session-abc123"
        result_msg.total_cost_usd = 0.05
        result_msg.duration_ms = 2000
        result_msg.is_error = False

        # 创建 mock 实例
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.query = AsyncMock()

        # receive_response 返回异步生成器，包含 ResultMessage
        async def message_gen():
            yield result_msg

        mock_instance.receive_response = message_gen
        mock_sdk_class.return_value = mock_instance

        # 创建客户端（没有 resume 参数）
        client = ClaudeCodeClient(working_dir="/test")

        # 初始状态
        assert client.get_session_id() is None
        assert client._session_id is None

        # 运行任务并收集消息
        messages = []
        async for msg in client.run_stream("hello"):
            messages.append(msg)

        # 验证 SDK 被调用
        mock_instance.query.assert_called_once_with("hello")

        # 验证会话ID被正确创建
        assert client.get_session_id() == "new-session-abc123"
        assert client._session_id == "new-session-abc123"

        # 验证收到完成消息
        assert len(messages) >= 1
        complete_msg = messages[-1]
        assert complete_msg.type == MessageType.COMPLETE
        assert complete_msg.metadata["session_id"] == "new-session-abc123"

    @pytest.mark.asyncio
    @patch("app.claude_runner.client.ClaudeSDKClient")
    async def test_resume_existing_session(self, mock_sdk_class):
        """测试恢复已有会话"""
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.query = AsyncMock()
        mock_instance.receive_response = AsyncMock(return_value=iter([]))

        mock_sdk_class.return_value = mock_instance

        # 创建客户端带 resume 参数
        session_id = "existing-session-123"
        client = ClaudeCodeClient(resume=session_id)

        # 验证选项包含 resume
        options = client._create_options()
        assert options.resume == session_id

    @pytest.mark.asyncio
    async def test_session_state_tracking(self):
        """测试会话状态跟踪"""
        client = ClaudeCodeClient()
        client.set_session_id("test-session-001")

        assert client.get_session_id() == "test-session-001"

        # 更新状态
        await client._update_question_state("q1", QuestionStatus.PENDING)
        assert client._question_states["q1"]["status"] == "pending"

        # 检查等待状态
        assert client.is_waiting_answer() is False

        client._is_waiting_answer = True
        assert client.is_waiting_answer() is True


class TestQuestionAnswerFlow:
    """问答流程测试"""

    @pytest.mark.asyncio
    async def test_question_display_and_answer(self):
        """测试问题显示和回答完整流程"""
        client = ClaudeCodeClient()
        client.set_session_id("session-123")

        # 1. 创建问题
        question = AskUserQuestion(
            question_id="q1",
            question_text="继续执行吗？",
            type="boolean",
            options=[
                QuestionOption(id="yes", label="是", default=True),
                QuestionOption(id="no", label="否"),
            ],
        )

        # 2. 初始化问题状态为 SHOWING（可以接受答案的状态）
        client._question_states["q1"] = {
            "status": QuestionStatus.SHOWING.value,
            "updated_at": 0,
            "metadata": {}
        }
        client._answer_event = asyncio.Event()
        client._is_waiting_answer = True
        client._pending_question_id = "q1"

        # 3. 提交答案
        answer = {
            "question_id": "q1",
            "answer": "yes",
        }
        result = await client.submit_answer(answer)

        # 4. 验证结果
        assert result is True
        assert client._pending_answer == answer

    @pytest.mark.asyncio
    async def test_question_timeout(self):
        """测试问题超时"""
        client = ClaudeCodeClient()
        client._answer_event = asyncio.Event()
        client._is_waiting_answer = True

        # 等待答案，设置超时为 0.1 秒
        result = await client.wait_for_answer("q1", timeout=0.1)

        # 应该返回 None（超时）
        assert result is None

        # 检查状态更新为超时
        assert client._question_states["q1"]["status"] == QuestionStatus.TIMEOUT.value

    @pytest.mark.asyncio
    async def test_answer_after_timeout(self):
        """测试超时后提交答案应该失败"""
        client = ClaudeCodeClient()
        client.set_session_id("session-123")

        # 设置问题状态为超时（不是 SHOWING）
        client._question_states["q1"] = {
            "status": QuestionStatus.TIMEOUT.value,
            "updated_at": 0,
            "metadata": {}
        }

        # 尝试提交答案
        answer = {"question_id": "q1", "answer": "yes"}
        result = await client.submit_answer(answer)

        # 应该失败（状态不对）
        assert result is False

    @pytest.mark.asyncio
    async def test_submit_answer_without_session(self):
        """测试无会话时提交答案"""
        client = ClaudeCodeClient()
        # 没有设置 session_id

        answer = {"question_id": "q1", "answer": "yes"}
        result = await client.submit_answer(answer)

        assert result is False

    @pytest.mark.asyncio
    async def test_submit_empty_answer(self):
        """测试提交空答案"""
        client = ClaudeCodeClient()
        client.set_session_id("session-123")
        client._question_states["q1"] = {
            "status": QuestionStatus.SHOWING.value,
            "updated_at": 0,
            "metadata": {}
        }
        client._answer_event = asyncio.Event()

        # 提交空答案
        answer = {"question_id": "q1", "answer": ""}
        result = await client.submit_answer(answer)

        assert result is False


class TestMultiQuestionFlow:
    """多问题流程测试"""

    @pytest.mark.asyncio
    async def test_sequential_questions(self):
        """测试顺序处理多个问题"""
        client = ClaudeCodeClient()
        client.set_session_id("session-multi")

        # 创建三个问题
        for i in range(1, 4):
            client._question_states[f"q{i}"] = {
                "status": QuestionStatus.SHOWING.value,  # 使用 SHOWING 状态
                "updated_at": 0,
                "metadata": {}
            }

        # 依次处理
        for i in range(1, 4):
            # 设置等待状态
            client._answer_event = asyncio.Event()
            client._is_waiting_answer = True
            client._pending_question_id = f"q{i}"

            # 提交答案
            answer = {"question_id": f"q{i}", "answer": f"answer-{i}"}
            result = await client.submit_answer(answer)

            assert result is True
            assert client._pending_answer == answer

    @pytest.mark.asyncio
    async def test_concurrent_questions(self):
        """测试并发限制"""
        from app.claude_runner.client import ConcurrencyManager

        manager = ConcurrencyManager()
        manager.max_concurrent_questions = 2

        # 尝试获取多个槽位
        results = []
        for i in range(5):
            r = await manager.acquire_question_slot(f"s{i}", f"q{i}")
            results.append(r)

        # 只有两个成功
        assert sum(results) == 2

        # 释放一个槽位
        await manager.release_question_slot("q0")

        # 等待队列处理
        await asyncio.sleep(0.1)

        # 队列中有等待的项，释放后会自动获取
        # 由于 acquire_question_slot 的逻辑，队列项会被自动处理
        # 检查活跃槽位数量应该还是 1（因为队列处理是异步的）
        # 实际上 release_question_slot 会触发 acquire_question_slot
        assert len(manager.active_questions) >= 1


class TestMessageTypes:
    """消息类型测试"""

    def test_text_message_creation(self):
        """测试文本消息创建"""
        msg = StreamMessage(
            type=MessageType.TEXT,
            content="这是一条文本消息",
        )
        assert msg.type == MessageType.TEXT
        assert msg.content == "这是一条文本消息"

    def test_tool_use_message_creation(self):
        """测试工具使用消息创建"""
        msg = StreamMessage(
            type=MessageType.TOOL_USE,
            content="调用 Read 工具",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
        )
        assert msg.type == MessageType.TOOL_USE
        assert msg.tool_name == "Read"

    def test_error_message_creation(self):
        """测试错误消息创建"""
        msg = StreamMessage(
            type=MessageType.ERROR,
            content="执行出错：文件不存在",
        )
        assert msg.type == MessageType.ERROR

    def test_complete_message_creation(self):
        """测试完成消息创建"""
        msg = StreamMessage(
            type=MessageType.COMPLETE,
            content="任务完成",
            metadata={
                "session_id": "sess-123",
                "cost_usd": 0.05,
                "duration_ms": 3000,
            },
        )
        assert msg.type == MessageType.COMPLETE
        assert msg.metadata["cost_usd"] == 0.05


class TestSessionMetadata:
    """会话元数据测试"""

    @pytest.mark.asyncio
    @patch("app.claude_runner.client.ClaudeSDKClient")
    async def test_session_id_from_result(self, mock_sdk_class):
        """测试从结果中获取 session_id"""
        from claude_agent_sdk import ResultMessage

        # 创建 mock 结果消息
        result_msg = MagicMock(spec=ResultMessage)
        result_msg.session_id = "generated-session-456"
        result_msg.total_cost_usd = 0.10
        result_msg.duration_ms = 5000
        result_msg.is_error = False

        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.query = AsyncMock()

        async def message_gen():
            yield result_msg

        mock_instance.receive_response = message_gen
        mock_sdk_class.return_value = mock_instance

        client = ClaudeCodeClient()
        result = await client.run("test task")

        # 验证 session_id 被正确获取
        assert result.session_id == "generated-session-456"
        assert client.get_session_id() == "generated-session-456"

    @pytest.mark.asyncio
    async def test_track_file_changes(self):
        """测试跟踪文件变更"""
        client = ClaudeCodeClient()

        # 模拟多个文件操作
        await client._track_tool_use("Read", {"file_path": "/read.py"})
        await client._track_tool_use("Write", {"file_path": "/new.py"})
        await client._track_tool_use("Edit", {"file_path": "/existing.py"})
        await client._track_tool_use("Edit", {"file_path": "/existing.py"})  # 重复编辑

        # Read 不应该记录
        assert "/read.py" not in client._files_changed

        # Write 和 Edit 应该记录
        assert "/new.py" in client._files_changed
        assert "/existing.py" in client._files_changed

        # 重复编辑只记录一次
        assert client._files_changed.count("/existing.py") == 1

        # 工具使用跟踪
        assert "Read" in client._tools_used
        assert "Write" in client._tools_used
        assert "Edit" in client._tools_used


class TestPermissionModes:
    """权限模式测试"""

    def test_default_permission_mode(self):
        """测试默认权限模式"""
        client = ClaudeCodeClient()
        assert client.permission_mode == "acceptEdits"

    def test_plan_permission_mode(self):
        """测试计划模式"""
        client = ClaudeCodeClient(permission_mode="plan")
        options = client._create_options()
        assert options.permission_mode == "plan"

    def test_bypass_permissions_mode(self):
        """测试绕过权限模式"""
        client = ClaudeCodeClient(permission_mode="bypassPermissions")
        options = client._create_options()
        assert options.permission_mode == "bypassPermissions"


class TestContinueConversation:
    """继续对话测试"""

    @pytest.mark.asyncio
    @patch("app.claude_runner.client.ClaudeSDKClient")
    async def test_continue_conversation_enabled(self, mock_sdk_class):
        """测试启用继续对话"""
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.query = AsyncMock()
        mock_instance.receive_response = AsyncMock(return_value=iter([]))

        mock_sdk_class.return_value = mock_instance

        client = ClaudeCodeClient(continue_conversation=True)
        options = client._create_options()

        assert options.continue_conversation is True

        # 运行任务
        messages = []
        async for msg in client.run_stream("继续上次的话题"):
            messages.append(msg)

        mock_instance.query.assert_called_once_with("继续上次的话题")

    @pytest.mark.asyncio
    @patch("app.claude_runner.client.ClaudeSDKClient")
    async def test_continue_conversation_disabled(self, mock_sdk_class):
        """测试禁用继续对话"""
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.query = AsyncMock()
        mock_instance.receive_response = AsyncMock(return_value=iter([]))

        mock_sdk_class.return_value = mock_instance

        client = ClaudeCodeClient(continue_conversation=False)
        options = client._create_options()

        assert options.continue_conversation is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
