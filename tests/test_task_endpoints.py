"""
后端单元测试 - API 端点测试

测试 task.py 中的 API 端点，包括：
- POST /api/task - 同步任务执行
- POST /api/task/stream - 流式任务执行
- POST /api/task/answer - 提交用户回答
- GET /api/task/session/{id}/status - 获取会话状态
- GET /api/task/sessions - 列出所有会话
- POST /api/task/new-session - 创建新会话
- GET /api/task/session/{id}/exists - 检查会话是否存在
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.routers import task
from app.routers.task import (
    TaskRequest,
    TaskResponse,
    QuestionAnswerRequest,
    QuestionAnswerResponse,
    SessionStatusResponse,
    NewSessionRequest,
    NewSessionResponse,
    get_project_dir_name,
    check_session_file_valid,
    save_user_message_to_session,
)


class TestTaskRequestModel:
    """TaskRequest 模型测试"""

    def test_task_request_defaults(self):
        """测试 TaskRequest 默认值"""
        request = TaskRequest(prompt="测试任务")

        assert request.prompt == "测试任务"
        assert request.working_dir is None
        assert request.tools is None
        assert request.resume is None
        assert request.new_session is False
        assert request.permission_mode == "default"

    def test_task_request_with_working_dir(self):
        """测试带工作目录的 TaskRequest"""
        request = TaskRequest(
            prompt="测试任务",
            working_dir="/test/workspace",
            tools=["Read", "Write"],
            resume="session-123",
            new_session=True,
            permission_mode="acceptEdits",
        )

        assert request.working_dir == "/test/workspace"
        assert request.tools == ["Read", "Write"]
        assert request.resume == "session-123"
        assert request.new_session is True
        assert request.permission_mode == "acceptEdits"


class TestTaskResponseModel:
    """TaskResponse 模型测试"""

    def test_task_response_creation(self):
        """测试创建 TaskResponse"""
        response = TaskResponse(
            success=True,
            message="任务完成",
            session_id="session-123",
            cost_usd=0.05,
            duration_ms=2000,
            files_changed=["file1.py"],
            tools_used=["Read", "Write"],
        )

        assert response.success is True
        assert response.message == "任务完成"
        assert response.session_id == "session-123"
        assert response.cost_usd == 0.05
        assert response.duration_ms == 2000
        assert response.files_changed == ["file1.py"]
        assert response.tools_used == ["Read", "Write"]


class TestQuestionAnswerRequestModel:
    """QuestionAnswerRequest 模型测试"""

    def test_question_answer_request_string(self):
        """测试字符串答案"""
        request = QuestionAnswerRequest(
            session_id="session-123",
            question_id="q1",
            answer="yes",
        )

        assert request.session_id == "session-123"
        assert request.question_id == "q1"
        assert request.answer == "yes"

    def test_question_answer_request_list(self):
        """测试列表答案"""
        request = QuestionAnswerRequest(
            session_id="session-123",
            question_id="q1",
            answer=["option1", "option2"],
        )

        assert isinstance(request.answer, list)

    def test_question_answer_request_bool(self):
        """测试布尔答案"""
        request = QuestionAnswerRequest(
            session_id="session-123",
            question_id="q1",
            answer=True,
        )

        assert request.answer is True


class TestSessionStatusResponseModel:
    """SessionStatusResponse 模型测试"""

    def test_session_status_response(self):
        """测试创建 SessionStatusResponse"""
        response = SessionStatusResponse(
            session_id="session-123",
            is_waiting=True,
            pending_question_id="q1",
            created_at=1234567890.0,
        )

        assert response.session_id == "session-123"
        assert response.is_waiting is True
        assert response.pending_question_id == "q1"
        assert response.created_at == 1234567890.0


class TestProjectDirName:
    """项目目录名生成函数测试"""

    def test_windows_path(self):
        """测试 Windows 路径转换"""
        # Windows 绝对路径
        result = get_project_dir_name("E:\\workspaces_2026\\project")
        assert result == "E--workspaces-2026-project"

    def test_windows_different_drive(self):
        """测试不同盘符的 Windows 路径"""
        result = get_project_dir_name("C:\\Users\\test")
        assert result == "C--Users-test"

    def test_unix_path(self):
        """测试 Unix 路径转换"""
        result = get_project_dir_name("/home/user/project")
        assert result == "-home-user-project"

    def test_path_with_underscores(self):
        """测试包含下划线的路径"""
        result = get_project_dir_name("/home/user_name/project_name")
        assert result == "-home-user-name-project-name"


class TestCheckSessionFileValid:
    """会话文件验证函数测试"""

    @pytest.mark.asyncio
    async def test_session_file_not_exists(self):
        """测试会话文件不存在的情况"""
        with patch("pathlib.Path.exists", return_value=False):
            result = await check_session_file_valid("session-123", "/test/workspace")
            assert result is False

    @pytest.mark.asyncio
    async def test_session_file_empty(self):
        """测试空会话文件"""
        with patch("pathlib.Path") as mock_path:
            mock_path.exists.return_value = True
            mock_path.stat.return_value.st_size = 0

            result = await check_session_file_valid("session-123", "/test/workspace")
            assert result is False


class TestSaveUserMessageToSession:
    """保存用户消息到会话测试"""

    @pytest.mark.asyncio
    async def test_save_user_message_new_file(self):
        """测试保存新用户消息"""
        # 这个测试需要 mock 文件系统操作
        with patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.exists", return_value=False), \
             patch("builtins.open", create=True) as mock_open, \
             patch("subprocess.run") as mock_subprocess:

            mock_subprocess.return_value = MagicMock(returncode=0, stdout="master")

            await save_user_message_to_session(
                session_id="test-session",
                prompt="测试提示",
                cwd="/test/workspace",
            )

            # 验证文件被创建
            mock_open.assert_called()


class TestAPIEndpointIntegration:
    """API 端点集成测试（使用 mock）"""

    @pytest.mark.asyncio
    async def test_get_session_status_not_found(self):
        """测试获取不存在的会话状态"""
        from app.routers.session_manager import session_manager

        # 使用全局 session_manager，确保会话不存在
        session_info = await session_manager.get_session_info("non-existent-session")

        assert session_info is None


class TestSessionStatusEndpoint:
    """会话状态端点测试"""

    @pytest.mark.asyncio
    async def test_get_session_status_from_manager(self):
        """测试从 SessionManager 获取会话状态"""
        from app.routers.session_manager import SessionManager

        manager = SessionManager()

        # 创建模拟会话
        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value="q1")

        await manager.create_session("test-session", mock_client)

        # 获取会话信息
        info = await manager.get_session_info("test-session")

        assert info is not None
        assert info.session_id == "test-session"
        assert info.pending_question_id == "q1"


class TestTaskEndpointModels:
    """任务端点模型测试"""

    def test_task_response_fields(self):
        """测试 TaskResponse 所有字段"""
        response = TaskResponse(
            success=False,
            message="Error occurred",
            session_id=None,
            cost_usd=None,
            duration_ms=None,
            files_changed=[],
            tools_used=[],
        )

        assert response.success is False
        assert response.message == "Error occurred"
        assert response.session_id is None


class TestNewSessionModels:
    """新会话模型测试"""

    def test_new_session_request_defaults(self):
        """测试 NewSessionRequest 默认值"""
        request = NewSessionRequest()

        assert request.session_id is None

    def test_new_session_request_with_id(self):
        """测试带会话 ID 的 NewSessionRequest"""
        request = NewSessionRequest(session_id="session-123")

        assert request.session_id == "session-123"

    def test_new_session_response(self):
        """测试 NewSessionResponse"""
        response = NewSessionResponse(
            success=True,
            message="已结束 2 个会话",
            ended_sessions=["s1", "s2"],
        )

        assert response.success is True
        assert len(response.ended_sessions) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
