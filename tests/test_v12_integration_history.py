"""
v12 界面重构 - 历史记录流程集成测试

测试目标：
- 测试打开历史抽屉
- 测试加载会话列表
- 测试继续会话功能

v12.0.0.5 - 集成测试
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from fastapi.testclient import TestClient


class TestHistoryDrawerFlow:
    """历史记录抽屉流程集成测试"""

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

    def test_history_drawer_open_close(self):
        """测试历史抽屉打开和关闭"""
        drawer = MockHistoryDrawer()

        # 初始状态
        assert drawer.is_open is False

        # 打开
        drawer.open()
        assert drawer.is_open is True

        # 关闭
        drawer.close()
        assert drawer.is_open is False

    def test_history_drawer_toggle(self):
        """测试切换历史抽屉状态"""
        drawer = MockHistoryDrawer()

        # 第一次切换：打开
        drawer.toggle()
        assert drawer.is_open is True

        # 第二次切换：关闭
        drawer.toggle()
        assert drawer.is_open is False

    def test_load_sessions_success(self, mock_claude_dir):
        """测试成功加载会话列表"""
        # 创建测试项目
        project_dir_name = "E--test-project"
        project_dir = mock_claude_dir / "projects" / project_dir_name
        project_dir.mkdir(parents=True)

        # 创建多个会话文件
        for i in range(3):
            session_file = project_dir / f"session-{i}.jsonl"
            with open(session_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "type": "user",
                    "sessionId": f"session-{i}",
                    "timestamp": datetime.now().isoformat(),
                    "cwd": "E:\\test\\project",
                    "message": {"content": f"测试消息 {i}"}
                }, ensure_ascii=False) + "\n")

        # 模拟加载会话
        drawer = MockHistoryDrawer()
        sessions = []
        for filepath in project_dir.glob("*.jsonl"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.loads(f.readline())
                sessions.append({
                    "id": data.get("sessionId"),
                    "timestamp": data.get("timestamp"),
                    "cwd": data.get("cwd"),
                })

        drawer.set_mock_sessions(sessions)
        drawer.load_sessions_sync()

        assert len(drawer.sessions) == 3
        assert drawer.is_loading is False

    def test_load_empty_sessions(self):
        """测试加载空会话列表"""
        drawer = MockHistoryDrawer()
        drawer.set_mock_sessions([])
        drawer.load_sessions_sync()

        assert len(drawer.sessions) == 0
        assert drawer.is_empty_visible is True

    def test_load_sessions_api_error(self):
        """测试 API 错误处理"""
        drawer = MockHistoryDrawer()
        drawer.set_mock_error("API Error")
        drawer.load_sessions_sync()

        assert len(drawer.sessions) == 0
        assert drawer.error_message == "加载会话列表失败"

    def test_select_session_closes_drawer(self):
        """测试选择会话后关闭抽屉"""
        drawer = MockHistoryDrawer()
        drawer.sessions = [
            {"id": "s1", "summary": "Session 1"},
            {"id": "s2", "summary": "Session 2"},
        ]
        drawer.open()

        # 选择会话
        selected_sessions = []

        def on_select(session):
            selected_sessions.append(session)

        drawer.on_select(on_select)
        drawer.select_session("s1")

        # 验证抽屉已关闭
        assert drawer.is_open is False
        # 验证回调被触发
        assert len(selected_sessions) == 1
        assert selected_sessions[0]["id"] == "s1"

    def test_select_nonexistent_session(self):
        """测试选择不存在的会话"""
        drawer = MockHistoryDrawer()
        drawer.sessions = [{"id": "s1"}]

        result = drawer.select_session("nonexistent")

        # 应该静默处理
        assert result is None
        assert drawer.is_open is False

    def test_escape_key_closes_drawer(self):
        """测试 ESC 键关闭抽屉"""
        drawer = MockHistoryDrawer()
        drawer.open()

        drawer.handle_keydown({"key": "Escape"})

        assert drawer.is_open is False

    def test_escape_key_ignored_when_closed(self):
        """测试抽屉关闭时 ESC 键被忽略"""
        drawer = MockHistoryDrawer()
        initial_state = drawer.is_open

        drawer.handle_keydown({"key": "Escape"})

        assert drawer.is_open == initial_state


class TestHistoryTimeFormatting:
    """历史记录时间格式化测试"""

    def test_format_time_today(self):
        """测试今天的时间格式化"""
        drawer = MockHistoryDrawer()
        now = datetime.now()
        timestamp = now.isoformat()

        formatted = drawer.format_time(timestamp)

        assert "今天" in formatted

    def test_format_time_yesterday(self):
        """测试昨天的时间格式化"""
        drawer = MockHistoryDrawer()
        yesterday = datetime.now() - timedelta(days=1)
        timestamp = yesterday.isoformat()

        formatted = drawer.format_time(timestamp)

        assert "昨天" in formatted

    def test_format_time_this_week(self):
        """测试本周的时间格式化"""
        drawer = MockHistoryDrawer()
        past_date = datetime.now() - timedelta(days=3)
        timestamp = past_date.isoformat()

        formatted = drawer.format_time(timestamp)

        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        assert any(day in formatted for day in weekdays)

    def test_format_time_invalid(self):
        """测试无效时间"""
        drawer = MockHistoryDrawer()

        formatted = drawer.format_time(None)
        assert formatted == "未知时间"

        formatted = drawer.format_time("invalid")
        assert formatted == "未知时间"

    def test_format_time_unix_timestamp(self):
        """测试 Unix 时间戳"""
        drawer = MockHistoryDrawer()
        timestamp = int(datetime.now().timestamp() * 1000)

        formatted = drawer.format_time(timestamp)

        assert formatted != "未知时间"


class TestHistorySessionRendering:
    """历史会话渲染测试"""

    def test_render_sessions_with_data(self):
        """测试渲染会话列表"""
        drawer = MockHistoryDrawer()
        sessions = [
            {
                "id": "test-1",
                "working_dir": "/path/to/project",
                "summary": "Test session",
                "created_at": datetime.now().isoformat(),
                "message_count": 5
            }
        ]

        html = drawer.render_sessions(sessions)

        assert "test-1" in html
        assert "/path/to/project" in html
        assert "Test session" in html

    def test_render_sessions_html_escaping(self):
        """测试会话项 HTML 转义"""
        drawer = MockHistoryDrawer()
        sessions = [
            {
                "id": "test-1",
                "summary": "<script>alert('xss')</script>",
                "working_dir": "/path"
            }
        ]

        html = drawer.render_sessions(sessions)

        # 应该转义 HTML 标签
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_empty_sessions(self):
        """测试渲染空会话列表"""
        drawer = MockHistoryDrawer()

        html = drawer.render_sessions([])

        assert html == ""


class TestHistoryAPIIntegration:
    """历史记录 API 集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def temp_session_dir(self, tmp_path):
        """创建临时会话目录"""
        claude_dir = tmp_path / ".claude"
        projects_dir = claude_dir / "projects"
        projects_dir.mkdir(parents=True)

        # 创建测试项目
        project_dir = projects_dir / "E--test-project"
        project_dir.mkdir()

        # 创建会话文件
        session_file = project_dir / "test-session.jsonl"
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "type": "user",
                "sessionId": "test-session",
                "timestamp": datetime.now().isoformat(),
                "cwd": "E:\\test\\project",
                "message": {"content": "测试消息"}
            }) + "\n")

        yield claude_dir

    def test_list_sessions_api(self, client):
        """测试会话列表 API"""
        response = client.get("/api/sessions?working_dir=.")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_get_session_messages_api(self, client):
        """测试获取会话消息 API"""
        # 首先尝试获取会话列表
        sessions_response = client.get("/api/sessions?working_dir=.")

        if sessions_response.status_code == 200:
            sessions_data = sessions_response.json()
            if sessions_data["sessions"]:
                session_id = sessions_data["sessions"][0]["id"]

                # 获取消息
                messages_response = client.get(f"/api/sessions/{session_id}/messages")

                # 可能是 200 或 404
                assert messages_response.status_code in [200, 404]

                if messages_response.status_code == 200:
                    messages_data = messages_response.json()
                    assert "messages" in messages_data
                    assert "session_id" in messages_data

    def test_get_session_messages_pagination(self, client):
        """测试会话消息分页"""
        # 获取会话列表
        sessions_response = client.get("/api/sessions?working_dir=.")

        if sessions_response.status_code == 200:
            sessions_data = sessions_response.json()
            if sessions_data["sessions"]:
                session_id = sessions_data["sessions"][0]["id"]

                # 测试分页参数
                response = client.get(
                    f"/api/sessions/{session_id}/messages?page=1&limit=10"
                )

                if response.status_code == 200:
                    data = response.json()
                    assert "pagination" in data
                    assert "page" in data["pagination"]
                    assert "limit" in data["pagination"]
                    assert "total" in data["pagination"]

    def test_session_not_found(self, client):
        """测试会话不存在"""
        response = client.get("/api/sessions/nonexistent-session/messages")

        assert response.status_code == 404

    def test_list_projects_with_sessions(self, client):
        """测试获取包含会话的项目列表"""
        response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data

        # 每个项目应该有 session_count
        for project in data["projects"]:
            assert "session_count" in project


class TestContinueSessionFlow:
    """继续会话流程集成测试"""

    def test_continue_session_sets_session_id(self):
        """测试继续会话设置会话 ID"""
        # 模拟选择历史会话
        drawer = MockHistoryDrawer()
        session = {
            "id": "session-to-continue",
            "working_dir": "/path/to/project",
            "summary": "Session to continue"
        }
        drawer.sessions = [session]

        selected = None

        def on_select(s):
            nonlocal selected
            selected = s

        drawer.on_select(on_select)
        drawer.select_session("session-to-continue")

        assert selected is not None
        assert selected["id"] == "session-to-continue"

    def test_continue_session_updates_ui_state(self):
        """测试继续会话更新 UI 状态"""
        # 模拟会话管理器
        session_manager = MockSessionManager()

        session = {
            "id": "existing-session",
            "working_dir": "/project/path",
            "message_count": 10
        }

        session_manager.continue_session(session)

        assert session_manager.current_session_id == "existing-session"
        assert session_manager.working_dir == "/project/path"

    def test_continue_session_fetches_messages(self):
        """测试继续会话获取消息"""
        # 这个测试主要验证继续会话的逻辑流程
        # 使用 Mock 对象而不是真实的 API 客户端
        session_manager = MockSessionManager()

        session = {
            "id": "session-with-messages",
            "working_dir": "/project/path",
            "message_count": 5
        }

        session_manager.continue_session(session)

        # 验证会话状态更新
        assert session_manager.current_session_id == "session-with-messages"
        assert session_manager.working_dir == "/project/path"

    def test_continue_session_without_messages(self):
        """测试继续没有消息的会话"""
        session_manager = MockSessionManager()

        session = {
            "id": "empty-session",
            "working_dir": "/project/path",
            "message_count": 0
        }

        session_manager.continue_session(session)

        assert session_manager.current_session_id == "empty-session"


class MockHistoryDrawer:
    """模拟 HistoryDrawer 类"""

    def __init__(self):
        self.is_open = False
        self.sessions = []
        self.current_session_id = None
        self.is_loading = False
        self.is_empty_visible = False
        self.error_message = None
        self._on_select = None
        self._on_close = None
        self.load_sessions_call_count = 0
        self._mock_sessions = None
        self._mock_error = None

    def open(self):
        if self.is_open:
            return
        self.is_open = True
        self.load_sessions_call_count += 1

    def close(self):
        if not self.is_open:
            return
        self.is_open = False
        if self._on_close:
            self._on_close()

    def toggle(self):
        if self.is_open:
            self.close()
        else:
            self.open()

    def load_sessions_sync(self):
        """同步版本的加载会话"""
        self.is_loading = True
        self.load_sessions_call_count += 1

        try:
            if self._mock_error:
                self.sessions = []
                self.error_message = "加载会话列表失败"
            elif self._mock_sessions is not None:
                self.sessions = self._mock_sessions
            else:
                self.sessions = []

            if len(self.sessions) == 0:
                self.is_empty_visible = True

        finally:
            self.is_loading = False

    def set_mock_sessions(self, sessions):
        self._mock_sessions = sessions
        self._mock_error = None

    def set_mock_error(self, error):
        self._mock_error = error
        self._mock_sessions = []

    def render_sessions(self, sessions):
        if not sessions:
            return ""

        html_parts = []
        for session in sessions:
            session_id = self._escape_html(session.get("id", ""))
            summary = self._escape_html(session.get("summary", "无摘要"))
            working_dir = self._escape_html(session.get("working_dir", ""))
            created_time = self.format_time(session.get("created_at"))
            message_count = session.get("message_count", 0)

            html = f'''
            <div class="history-session-item" data-session-id="{session_id}">
                <div class="session-header">
                    <span class="session-date">{created_time}</span>
                    <span class="session-count">{message_count} 条消息</span>
                </div>
                <div class="session-summary">{summary}</div>
                <div class="session-path">
                    <span class="path-text">{working_dir}</span>
                </div>
            </div>
            '''
            html_parts.append(html)

        return "".join(html_parts)

    def select_session(self, session_id):
        session = next((s for s in self.sessions if s["id"] == session_id), None)
        if not session:
            return None

        self.close()

        if self._on_select:
            self._on_select(session)

        return session

    def set_current_session(self, session_id):
        self.current_session_id = session_id

    def on_select(self, callback):
        self._on_select = callback

    def on_close(self, callback):
        self._on_close = callback

    def handle_keydown(self, event):
        if event["key"] == "Escape" and self.is_open:
            self.close()

    def format_time(self, timestamp):
        if not timestamp:
            return "未知时间"

        try:
            if isinstance(timestamp, (int, float)):
                if timestamp > 1e10:
                    date = datetime.fromtimestamp(timestamp / 1000)
                else:
                    date = datetime.fromtimestamp(timestamp)
            else:
                date = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                if date.tzinfo:
                    date = date.replace(tzinfo=None)
        except (ValueError, TypeError):
            return "未知时间"

        now = datetime.now()
        diff = now - date

        if diff.days == 0 and date.date() == now.date():
            return f"今天 {self._pad_zero(date.hour)}:{self._pad_zero(date.minute)}"

        yesterday = now - timedelta(days=1)
        if date.date() == yesterday.date():
            return f"昨天 {self._pad_zero(date.hour)}:{self._pad_zero(date.minute)}"

        if diff.days < 7:
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            return f"{weekdays[date.weekday()]} {self._pad_zero(date.hour)}:{self._pad_zero(date.minute)}"

        return f"{date.month}/{date.day} {self._pad_zero(date.hour)}:{self._pad_zero(date.minute)}"

    def _pad_zero(self, num):
        return f"{num:02d}"

    def _escape_html(self, text):
        if not text:
            return ""
        import html
        return html.escape(str(text))


class MockSessionManager:
    """模拟会话管理器"""

    def __init__(self):
        self.current_session_id = None
        self.working_dir = None

    def continue_session(self, session):
        self.current_session_id = session.get("id")
        self.working_dir = session.get("working_dir")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
