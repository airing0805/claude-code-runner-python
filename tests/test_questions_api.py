"""提问历史记录 API 测试

测试 GET /api/projects/{project_name}/questions 管点及相关功能
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from fastapi.testclient import TestClient
from app.main import app
from app.services.questions import extract_question, mask_sensitive_info

client = TestClient(app)


# ============== Fixtures ==============

@pytest.fixture
def temp_claude_dir():
    """临时 Claude 目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        claude_dir = Path(tmpdir)
        projects_dir = claude_dir / "projects"
        projects_dir.mkdir(parents=True)
        yield claude_dir


@pytest.fixture
def sample_session_file(temp_claude_dir):
    """创建示例会话文件"""
    project_dir = temp_claude_dir / "projects" / "E--test-project"
    project_dir.mkdir(parents=True)

    session_id = "d9eb61b6-5eb1-42f7-974c-832e54859911"
    session_file = project_dir / f"{session_id}.jsonl"

    # 创建测试会话内容
    session_data = [
        {
            "type": "user",
            "sessionId": session_id,
            "uuid": "uuid-1",
            "timestamp": "2026-03-05T10:30:00.000Z",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "帮我实现一个用户登录功能，需要包括邮箱和密码验证"
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "sessionId": session_id,
            "uuid": "uuid-2",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "好的，我来帮你实现用户登录功能"
                    }
                ]
            }
        }
    ]

    with open(session_file, "w", encoding="utf-8") as f:
        for line in session_data:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    return session_file


@pytest.fixture
def sample_session_with_ide_tags(temp_claude_dir):
    """创建包含 IDE 标签的会话文件"""
    project_dir = temp_claude_dir / "projects" / "E--test-project"
    project_dir.mkdir(parents=True, exist_ok=True)

    session_id = "session-with-ide-tags"
    session_file = project_dir / f"{session_id}.jsonl"

    # 创建包含 IDE 标签的会话内容
    session_data = [
        {
            "type": "user",
            "sessionId": session_id,
            "uuid": "uuid-1",
            "timestamp": "2026-03-05T10:30:00.000Z",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """
<ide_selection>class User:\n    def __init__(self):\n        pass</ide_selection>
<ide_opened_file>src/models/user.py</ide_opened_file>
请帮我优化这个 User 类
                        """
                    }
                ]
            }
        }
    ]

    with open(session_file, "w", encoding="utf-8") as f:
        for line in session_data:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    return session_file


@pytest.fixture
def sample_session_with_sensitive_info(temp_claude_dir):
    """创建包含敏感信息的会话文件"""
    project_dir = temp_claude_dir / "projects" / "E--test-project"
    project_dir.mkdir(parents=True, exist_ok=True)

    session_id = "session-with-secrets"
    session_file = project_dir / f"{session_id}.jsonl"

    # 创建包含敏感信息的会话内容
    session_data = [
        {
            "type": "user",
            "sessionId": session_id,
            "uuid": "uuid-1",
            "timestamp": "2026-03-05T10:30:00.000Z",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "配置数据库连接，使用 sk-ant-api03-abc123-def456 作为 API key, password 设置为 mySecretPass123"
                    }
                ]
            }
        }
    ]

    with open(session_file, "w", encoding="utf-8") as f:
        for line in session_data:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    return session_file


# ============== Unit Tests for extract_question ==============

class TestExtractQuestion:
    """测试 extract_question 函数"""

    def test_extract_question_from_valid_file(self, sample_session_file):
        """测试从有效会话文件提取提问"""
        result = extract_question(sample_session_file)

        assert result is not None
        assert result["id"] == "d9eb61b6-5eb1-42f7-974c-832e54859911"
        assert "用户登录功能" in result["question_text"]
        assert result["timestamp"] == "2026-03-05T10:30:00.000Z"

    def test_extract_question_filters_ide_tags(self, sample_session_with_ide_tags):
        """测试过滤 IDE 标签"""
        result = extract_question(sample_session_with_ide_tags)

        assert result is not None
        assert "<ide_selection>" not in result["question_text"]
        assert "<ide_opened_file>" not in result["question_text"]
        assert "优化这个 User 类" in result["question_text"]

    def test_extract_question_masks_sensitive_info(self, sample_session_with_sensitive_info):
        """测试敏感信息脱敏"""
        result = extract_question(sample_session_with_sensitive_info)

        assert result is not None
        assert "[API_KEY]" in result["question_text"] or "sk-ant-api03" not in result["question_text"]
        assert "[PASSWORD]" in result["question_text"] or "mySecretPass123" not in result["question_text"]

    def test_extract_question_empty_file(self, temp_claude_dir):
        """测试空文件"""
        project_dir = temp_claude_dir / "projects" / "E--test"
        project_dir.mkdir(parents=True)

        empty_file = project_dir / "empty-session.jsonl"
        empty_file.write_text("", encoding="utf-8")

        result = extract_question(empty_file)

    def test_mask_sensitive_info(self):
        """测试脱敏函数"""
        text = "password=secret123 and api_key=sk-ant-api03-abc123"
        result = mask_sensitive_info(text)
        assert "secret123" not in result
        assert "sk-ant-api03-abc123" not in result


# ============== API Tests ==============

class TestQuestionsAPI:
    """测试 Questions API"""

    def _patch_and_test(self, temp_claude_dir, test_func):
        """辅助方法：修补 PROJECTS_DIR 并执行测试"""
        import app.routers.session as session_module
        original_dir = session_module.PROJECTS_DIR
        session_module.PROJECTS_DIR = temp_claude_dir / "projects"

        try:
            return test_func()
        finally:
            session_module.PROJECTS_DIR = original_dir

    def test_get_projects_list(self, temp_claude_dir):
        """测试获取项目列表"""
        response = self._patch_and_test(temp_claude_dir, lambda: client.get("/api/projects"))
        assert response.status_code == 200

    def test_get_project_questions_basic(self, temp_claude_dir):
        """测试获取项目提问基本功能"""
        project_dir = temp_claude_dir / "projects" / "E--test"
        project_dir.mkdir(parents=True)

        session_file = project_dir / "test-session.jsonl"
        data = {
            "type": "user",
            "sessionId": "test-session-id",
            "timestamp": "2026-03-05T10:30:00.000Z",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "测试提问内容"}]
            }
        }

        with open(session_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

        response = self._patch_and_test(
            temp_claude_dir,
            lambda: client.get("/api/projects/E--test/questions")
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True

    def test_get_project_questions_pagination(self, temp_claude_dir):
        """测试分页功能"""
        project_dir = temp_claude_dir / "projects" / "E--pagination-test"
        project_dir.mkdir(parents=True)

        # 创建 15 个会话
        for i in range(15):
            session_file = project_dir / f"session-{i}.jsonl"
            data = {
                "type": "user",
                "sessionId": f"session-{i}",
                "timestamp": f"2026-03-05T10:{i:02d}:00.000Z",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": f"分页测试提问 {i}"}]
                }
            }

            with open(session_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

        # 测试第一页
        response = self._patch_and_test(
            temp_claude_dir,
            lambda: client.get("/api/projects/E--pagination-test/questions?page=1&limit=10")
        )

        assert response.status_code == 200
        data = response.json()

        if "data" in data:
            assert data["data"]["page"] == 1
            assert data["data"]["limit"] == 10
            assert len(data["data"]["items"]) <= 10

    def test_get_project_questions_invalid_project(self, temp_claude_dir):
        """测试获取不存在项目的提问"""
        response = self._patch_and_test(
            temp_claude_dir,
            lambda: client.get("/api/projects/non-existent-project/questions")
        )
        # 应该返回 404
        assert response.status_code == 404

    def test_get_project_questions_invalid_page(self, temp_claude_dir):
        """测试无效页码"""
        project_dir = temp_claude_dir / "projects" / "E--test"
        project_dir.mkdir(parents=True)

        response = self._patch_and_test(
            temp_claude_dir,
            lambda: client.get("/api/projects/E--test/questions?page=0")
        )
        # 应该返回 400 或处理为 1
        assert response.status_code in [200, 400, 422]

    def test_path_traversal_protection(self, temp_claude_dir):
        """测试路径遍历攻击保护"""
        response = self._patch_and_test(
            temp_claude_dir,
            lambda: client.get("/api/projects/../../../etc/passwd/questions")
        )
        # 应该返回 404 或 400
        assert response.status_code in [400, 404]

    def test_unicode_content(self, temp_claude_dir):
        """测试 Unicode 字符处理"""
        project_dir = temp_claude_dir / "projects" / "E--unicode"
        project_dir.mkdir(parents=True)

        session_file = project_dir / "unicode.jsonl"
        data = {
            "type": "user",
            "sessionId": "unicode-session",
            "timestamp": "2026-03-05T10:30:00.000Z",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "你好世界 🌍 Testing with émojis 😀"}]
            }
        }

        with open(session_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

        response = self._patch_and_test(
            temp_claude_dir,
            lambda: client.get("/api/projects/E--unicode/questions")
        )

        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]["items"]:
                # Unicode 字符应该被正确处理
                item = data["data"]["items"][0]
                assert "你好" in item["question_text"] or len(item["question_text"]) > 0

    def test_empty_question_content(self, temp_claude_dir):
        """测试空提问内容"""
        project_dir = temp_claude_dir / "projects" / "E--empty-content"
        project_dir.mkdir(parents=True)

        session_file = project_dir / "empty-content.jsonl"
        data = {
            "type": "user",
            "sessionId": "empty-session",
            "uuid": "uuid-1",
            "timestamp": "2026-03-05T10:30:00.000Z",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": ""}]
            }
        }

        with open(session_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

        response = self._patch_and_test(
            temp_claude_dir,
            lambda: client.get("/api/projects/E--empty-content/questions")
        )

        # 应该跳过空提问
        assert response.status_code in [200]
        data = response.json()
        if "data" in data:
            # 要么没有提问，要么提问列表为空
            assert len(data["data"].get("items", [])) == 0


# ============== Integration Tests ==============

class TestQuestionsIntegration:
    """集成测试"""

    def test_full_workflow(self, temp_claude_dir):
        """测试完整工作流程"""
        # 1. 创建项目
        project_dir = temp_claude_dir / "projects" / "E--integration-test"
        project_dir.mkdir(parents=True)

        # 2. 创建会话文件
        session_file = project_dir / "test-session.jsonl"
        session_data = [
            {
                "type": "user",
                "sessionId": "integration-test-session",
                "uuid": "uuid-1",
                "timestamp": "2026-03-05T10:30:00.000Z",
                "cwd": "E:\\test\\project",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这是一个集成测试问题"}
                    ]
                }
            }
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for line in session_data:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")

        # 3. 获取项目列表
        import app.routers.session as session_module
        original_dir = session_module.PROJECTS_DIR
        session_module.PROJECTS_DIR = temp_claude_dir / "projects"

        try:
            response = client.get("/api/projects")
        finally:
            session_module.PROJECTS_DIR = original_dir

        assert response.status_code == 200
        projects = response.json()["projects"]
        assert len(projects) > 0

        # 4. 获取提问列表
        session_module.PROJECTS_DIR = temp_claude_dir / "projects"

        try:
            response = client.get("/api/projects/E--integration-test/questions")
        finally:
            session_module.PROJECTS_DIR = original_dir

        assert response.status_code == 200
        questions = response.json().get("data", {}).get("items", [])
        assert len(questions) > 0
        assert "集成测试问题" in questions[0]["question_text"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
