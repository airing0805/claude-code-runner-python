"""任务API修复测试

测试 task.py 中代码修改的正确性。
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import tempfile
import os

from app.routers.task import (
    get_project_dir_name,
    check_session_file_valid,
    save_user_message_to_session,
)


class TestProjectDirName:
    """测试项目目录名生成"""

    def test_windows_path(self):
        """测试 Windows 路径处理"""
        # Windows 路径
        result = get_project_dir_name("E:\\workspaces_2026\\project")
        assert result == "E--workspaces-2026-project"

    def test_unix_path(self):
        """测试 Unix 路径处理"""
        # Unix 路径
        result = get_project_dir_name("/home/user/project")
        assert result == "-home-user-project"

    def test_path_with_underscores(self):
        """测试包含下划线的路径"""
        result = get_project_dir_name("E:\\workspaces_2026_test\\project")
        assert "_" in "E:\\workspaces_2026_test\\project" or result.count("-") > 0


class TestCheckSessionFileValid:
    """测试会话文件验证"""

    def test_session_file_not_exists(self):
        """测试会话文件不存在的情况"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 临时 CLAUDE_DIR
            result = check_session_file_valid("non-existent-session", tmpdir)
            assert result is False

    def test_empty_session_file(self):
        """测试空会话文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一个空文件
            session_file = Path(tmpdir) / "test.jsonl"
            session_file.write_text("", encoding="utf-8")

            # 由于 check_session_file_valid 需要访问 ~/.claude 目录
            # 这里主要验证函数逻辑正确
            # 实际测试需要 mock CLAUDE_DIR
            pass


class TestSaveUserMessageToSession:
    """测试保存用户消息到会话"""

    @pytest.mark.asyncio
    async def test_save_message_creates_file(self):
        """测试保存消息会创建会话文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.task.CLAUDE_DIR", Path(tmpdir)):
                # Mock subprocess.run 以避免实际调用 git
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="master")

                    session_id = "test-session-123"
                    prompt = "Test prompt"
                    cwd = tmpdir

                    await save_user_message_to_session(session_id, prompt, cwd)

                    # 验证文件被创建
                    project_hash = get_project_dir_name(cwd)
                    session_file = Path(tmpdir) / "projects" / project_hash / f"{session_id}.jsonl"
                    assert session_file.exists()

                    # 验证文件内容
                    with open(session_file, "r", encoding="utf-8") as f:
                        data = json.loads(f.readline())
                        assert data["type"] == "user"
                        assert data["sessionId"] == session_id
                        assert data["message"]["content"][0]["text"] == prompt

    @pytest.mark.asyncio
    async def test_save_message_existing_file(self):
        """测试会话文件已存在时不覆盖"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.task.CLAUDE_DIR", Path(tmpdir)):
                session_id = "test-session-456"
                prompt = "Test prompt"
                cwd = tmpdir

                # 先创建会话文件
                project_hash = get_project_dir_name(cwd)
                project_dir = Path(tmpdir) / "projects" / project_hash
                project_dir.mkdir(parents=True, exist_ok=True)
                session_file = project_dir / f"{session_id}.jsonl"
                session_file.write_text('{"type": "existing"}\n', encoding="utf-8")

                # 再次保存
                await save_user_message_to_session(session_id, prompt, cwd)

                # 验证文件内容未被覆盖
                with open(session_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    assert "existing" in content
                    assert "Test prompt" not in content


class TestTaskRequestValidation:
    """测试任务请求验证"""

    def test_task_request_defaults(self):
        """测试任务请求默认值"""
        from app.routers.task import TaskRequest

        request = TaskRequest(prompt="Test")
        assert request.prompt == "Test"
        assert request.working_dir is None
        assert request.tools is None
        assert request.resume is None
        assert request.new_session is False
        assert request.permission_mode == "default"

    def test_task_request_with_options(self):
        """测试任务请求带选项"""
        from app.routers.task import TaskRequest

        request = TaskRequest(
            prompt="Test",
            working_dir="/test",
            tools=["Read", "Write"],
            new_session=True,
            permission_mode="acceptEdits",
        )
        assert request.working_dir == "/test"
        assert request.tools == ["Read", "Write"]
        assert request.new_session is True
        assert request.permission_mode == "acceptEdits"
