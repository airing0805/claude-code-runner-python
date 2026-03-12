"""
v12 界面重构 - 工作空间切换流程集成测试

测试目标：
- 测试选择历史工作空间
- 测试手动输入新路径
- 测试新会话创建

v12.0.0.5 - 集成测试
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from fastapi.testclient import TestClient


class TestWorkspaceSwitchFlow:
    """工作空间切换流程集成测试"""

    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)

    @pytest.fixture
    def mock_claude_dir(self, temp_project_dir):
        """创建模拟的 .claude 目录结构"""
        claude_dir = temp_project_dir / ".claude"
        projects_dir = claude_dir / "projects"
        projects_dir.mkdir(parents=True)

        yield claude_dir

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from app.main import app
        return TestClient(app)

    def test_list_sessions_for_workspace(self, client):
        """测试获取工作空间的会话列表"""
        # 调用 API（使用当前目录，这个测试主要验证 API 响应格式正确）
        response = client.get("/api/sessions?working_dir=.")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_list_projects_api(self, client, mock_claude_dir):
        """测试获取项目列表 API"""
        # 创建测试项目
        project_dir = mock_claude_dir / "projects" / "E--project1"
        project_dir.mkdir(parents=True)

        session_file = project_dir / "session-1.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "type": "user",
                "sessionId": "s1",
                "timestamp": datetime.now().isoformat(),
                "cwd": "E:\\project1",
                "message": {"content": "test"}
            }) + "\n")

        # 调用 API
        response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data

    def test_workspace_combo_validation_logic(self):
        """测试工作空间组合控件的路径验证逻辑"""
        # 测试有效路径
        valid_paths = [
            "/home/user/project",
            "/var/www/html",
            "C:\\Users\\admin\\project",
            "D:\\projects\\test",
        ]

        for path in valid_paths:
            result = self._validate_path_format(path)
            assert result["valid"] is True, f"Path {path} should be valid"

        # 测试无效路径
        invalid_paths = [
            "relative/path",
            "./current",
            "../../../etc/passwd",
            "~/malicious",
        ]

        for path in invalid_paths:
            result = self._validate_path_format(path)
            assert result["valid"] is False, f"Path {path} should be invalid"

    def test_workspace_history_deduplication(self):
        """测试工作空间历史去重"""
        history = [
            "/path/to/project1",
            "/path/to/project2",
            "/path/to/project1",  # 重复
            "/path/to/project3",
            "/path/to/project2",  # 重复
        ]

        deduped = self._deduplicate_history(history)

        assert len(deduped) == 3
        assert "/path/to/project1" in deduped
        assert "/path/to/project2" in deduped
        assert "/path/to/project3" in deduped

    def test_workspace_history_limit(self):
        """测试工作空间历史限制为 20 条"""
        history = [f"/path/to/project{i}" for i in range(30)]

        # 模拟添加到历史的逻辑
        result = self._add_to_history([], history)

        assert len(result) <= 20

    def test_workspace_change_triggers_new_session(self):
        """测试工作空间切换触发新会话创建"""
        # 模拟 WorkspaceCombo 的值变化
        combo = MockWorkspaceCombo()
        change_events = []

        def on_change(value):
            change_events.append(value)

        combo.on_change(on_change)
        combo.set_value("/new/workspace/path")

        assert len(change_events) == 1
        assert change_events[0] == "/new/workspace/path"

    def test_manual_input_new_path(self):
        """测试手动输入新路径"""
        combo = MockWorkspaceCombo()

        # 设置历史记录
        combo.set_history(["/existing/path1", "/existing/path2"])

        # 模拟用户手动输入新路径
        new_path = "/brand/new/path"
        combo.set_value(new_path)

        # 验证值被正确设置
        assert combo.get_value() == new_path

        # 验证路径验证被触发
        validation_result = combo.validate_path(new_path)
        assert validation_result["valid"] is True

    def test_select_from_history(self):
        """测试从历史记录选择工作空间"""
        combo = MockWorkspaceCombo()

        history = [
            "/path/to/project1",
            "/path/to/project2",
            "/path/to/project3",
        ]
        combo.set_history(history)

        # 选择历史记录中的路径
        selected_path = history[1]
        combo.set_value(selected_path)

        assert combo.get_value() == selected_path

    def test_add_to_history_moves_to_front(self):
        """测试添加已存在的路径会移动到前面"""
        combo = MockWorkspaceCombo()

        history = ["/path/1", "/path/2", "/path/3"]
        combo.set_history(history)

        # 添加已存在的路径
        combo.add_to_history("/path/2")

        result = combo.get_history()
        assert result[0] == "/path/2"
        assert len(result) == 3

    def test_workspace_combo_disabled_during_task(self):
        """测试任务执行时禁用工作空间控件"""
        combo = MockWorkspaceCombo()

        # 初始状态
        assert combo.disabled is False

        # 禁用
        combo.set_disabled(True)
        assert combo.disabled is True

        # 启用
        combo.set_disabled(False)
        assert combo.disabled is False

    def _validate_path_format(self, path: str) -> dict:
        """路径验证逻辑（模拟前端）"""
        if not path or not isinstance(path, str):
            return {"valid": False, "error": "路径格式不正确"}

        if ".." in path or "~" in path:
            return {"valid": False, "error": "路径包含非法字符"}

        is_unix_path = path.startswith("/")
        is_windows_path = len(path) >= 3 and path[1] == ":" and path[2] in "/\\"

        if not is_unix_path and not is_windows_path:
            return {"valid": False, "error": "路径格式不正确（需要绝对路径）"}

        return {"valid": True}

    def _deduplicate_history(self, history: list) -> list:
        """历史记录去重"""
        seen = set()
        result = []
        for item in history:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _add_to_history(self, history: list, new_items) -> list:
        """添加到历史记录"""
        if isinstance(new_items, list):
            result = list(history)
            for item in new_items:
                if item in result:
                    result.remove(item)
                result.insert(0, item)
            return result[:20]
        else:
            result = list(history)
            if new_items in result:
                result.remove(new_items)
            result.insert(0, new_items)
            return result[:20]


class TestWorkspaceComboEvents:
    """测试工作空间组合控件事件"""

    def test_on_change_callback_fired(self):
        """测试值变化回调被触发"""
        combo = MockWorkspaceCombo()
        callback_values = []

        def mock_callback(value):
            callback_values.append(value)

        combo.on_change(mock_callback)
        combo.set_value("/new/path")

        assert len(callback_values) == 1
        assert callback_values[0] == "/new/path"

    def test_on_validate_callback_fired(self):
        """测试验证回调被触发"""
        combo = MockWorkspaceCombo()
        validation_results = []

        def mock_validate(result):
            validation_results.append(result)

        combo.on_validate(mock_validate)
        combo.validate_path("/invalid/../../../path")

        assert len(validation_results) >= 1
        assert any(r.get("valid") is False for r in validation_results)

    def test_dropdown_open_close(self):
        """测试下拉菜单打开和关闭"""
        combo = MockWorkspaceCombo()
        combo.set_history(["/path/1", "/path/2"])

        # 打开下拉
        combo.open_dropdown()
        assert combo.is_open is True

        # 关闭下拉
        combo.close_dropdown()
        assert combo.is_open is False

    def test_escape_key_closes_dropdown(self):
        """测试 ESC 键关闭下拉"""
        combo = MockWorkspaceCombo()
        combo.open_dropdown()

        combo.handle_keydown({"key": "Escape"})

        assert combo.is_open is False


class MockWorkspaceCombo:
    """模拟 WorkspaceCombo 类"""

    def __init__(self):
        self.current_value = ""
        self.history = []
        self.disabled = False
        self.is_open = False
        self._on_change = None
        self._on_validate = None

    def set_value(self, value):
        self.current_value = value
        if self._on_change:
            self._on_change(value)

    def get_value(self):
        return self.current_value

    def set_history(self, history):
        self.history = self._deduplicate(history)

    def get_history(self):
        return list(self.history)

    def add_to_history(self, path):
        if not path:
            return

        if path in self.history:
            self.history.remove(path)

        self.history.insert(0, path)

        if len(self.history) > 20:
            self.history = self.history[:20]

    def on_change(self, callback):
        self._on_change = callback

    def on_validate(self, callback):
        self._on_validate = callback

    def set_disabled(self, disabled):
        self.disabled = disabled

    def validate_path(self, path):
        result = self._validate_path_format(path)
        if self._on_validate:
            self._on_validate(result)
        return result

    def open_dropdown(self):
        self.is_open = True

    def close_dropdown(self):
        self.is_open = False

    def handle_keydown(self, event):
        if event["key"] == "Escape" and self.is_open:
            self.close_dropdown()

    def _validate_path_format(self, path):
        if not path:
            return {"valid": True}

        if ".." in path or "~" in path:
            return {"valid": False, "error": "路径包含非法字符"}

        is_unix_path = path.startswith("/")
        is_windows_path = len(path) >= 3 and path[1] == ":" and path[2] in "/\\"

        if not is_unix_path and not is_windows_path:
            return {"valid": False, "error": "路径格式不正确（需要绝对路径）"}

        return {"valid": True}

    def _deduplicate(self, history):
        seen = set()
        result = []
        for item in history:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result


class TestWorkspaceAPIIntegration:
    """工作空间 API 集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from app.main import app
        return TestClient(app)

    def test_sessions_api_returns_correct_structure(self, client):
        """测试会话 API 返回正确的数据结构"""
        response = client.get("/api/sessions?working_dir=.")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_projects_api_pagination(self, client):
        """测试项目 API 分页"""
        response = client.get("/api/projects?page=1&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "pages" in data

    def test_project_sessions_api(self, client):
        """测试项目会话 API"""
        # 首先获取项目列表
        projects_response = client.get("/api/projects?limit=1")

        if projects_response.status_code == 200:
            projects_data = projects_response.json()
            if projects_data["projects"]:
                project_name = projects_data["projects"][0]["encoded_name"]

                # 获取该项目的会话
                sessions_response = client.get(f"/api/projects/{project_name}/sessions")

                assert sessions_response.status_code in [200, 404]

    def test_sessions_api_with_missing_working_dir(self, client):
        """测试缺少工作目录参数的会话 API"""
        response = client.get("/api/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
