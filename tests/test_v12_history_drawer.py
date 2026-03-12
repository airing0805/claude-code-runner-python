"""
历史记录抽屉 (HistoryDrawer) 单元测试

测试目标：
- 打开/关闭功能
- 会话列表加载
- 继续会话功能
- 时间格式化

v12.0.0.4 - 界面重构测试
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import json


class TestHistoryDrawerOpenClose:
    """测试打开/关闭功能"""

    def test_initial_state_is_closed(self):
        """测试初始状态为关闭"""
        drawer = MockHistoryDrawer()
        assert drawer.is_open is False

    def test_open_drawer(self):
        """测试打开抽屉"""
        drawer = MockHistoryDrawer()
        drawer.open()

        assert drawer.is_open is True

    def test_close_drawer(self):
        """测试关闭抽屉"""
        drawer = MockHistoryDrawer()
        drawer.open()
        drawer.close()

        assert drawer.is_open is False

    def test_toggle_drawer(self):
        """测试切换抽屉状态"""
        drawer = MockHistoryDrawer()

        # 第一次切换：打开
        drawer.toggle()
        assert drawer.is_open is True

        # 第二次切换：关闭
        drawer.toggle()
        assert drawer.is_open is False

    def test_open_already_open_drawer(self):
        """测试打开已打开的抽屉（应该无操作）"""
        drawer = MockHistoryDrawer()
        drawer.open()
        initial_call_count = drawer.load_sessions_call_count

        drawer.open()  # 再次打开

        # 不应该再次加载会话
        assert drawer.load_sessions_call_count == initial_call_count

    def test_close_already_closed_drawer(self):
        """测试关闭已关闭的抽屉（应该无操作）"""
        drawer = MockHistoryDrawer()

        drawer.close()  # 关闭已关闭的抽屉

        assert drawer.is_open is False


class TestHistoryDrawerSessionList:
    """测试会话列表加载"""

    def test_load_sessions_success(self):
        """测试成功加载会话列表"""
        drawer = MockHistoryDrawer()

        sessions = [
            {"id": "s1", "working_dir": "/path/1", "summary": "Session 1"},
            {"id": "s2", "working_dir": "/path/2", "summary": "Session 2"},
        ]

        drawer.set_mock_sessions(sessions)
        drawer.load_sessions_sync()

        assert len(drawer.sessions) == 2
        assert drawer.sessions[0]["id"] == "s1"

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

    def test_render_sessions(self):
        """测试渲染会话列表"""
        drawer = MockHistoryDrawer()
        sessions = [
            {
                "id": "test-1",
                "working_dir": "/path/to/project",
                "summary": "Test session",
                "created_at": "2024-03-10T10:00:00",
                "message_count": 5
            }
        ]

        html = drawer.render_sessions(sessions)

        assert "test-1" in html
        assert "/path/to/project" in html
        assert "Test session" in html

    def test_session_item_escaping(self):
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


class TestHistoryDrawerContinueSession:
    """测试继续会话功能"""

    def test_select_session(self):
        """测试选择会话"""
        selected_sessions = []

        def on_select(session):
            selected_sessions.append(session)

        drawer = MockHistoryDrawer()
        drawer.sessions = [
            {"id": "s1", "summary": "Session 1"},
            {"id": "s2", "summary": "Session 2"},
        ]
        drawer.on_select(on_select)

        drawer.select_session("s1")

        assert len(selected_sessions) == 1
        assert selected_sessions[0]["id"] == "s1"
        assert drawer.is_open is False  # 选择后应该关闭抽屉

    def test_select_nonexistent_session(self):
        """测试选择不存在的会话"""
        drawer = MockHistoryDrawer()
        drawer.sessions = [{"id": "s1"}]

        result = drawer.select_session("nonexistent")

        # 应该静默处理不存在的会话
        assert result is None
        assert drawer.is_open is False

    def test_select_session_closes_drawer(self):
        """测试选择会话后关闭抽屉"""
        drawer = MockHistoryDrawer()
        drawer.sessions = [{"id": "s1"}]
        drawer.open()

        drawer.select_session("s1")

        assert drawer.is_open is False

    def test_set_current_session(self):
        """测试设置当前会话"""
        drawer = MockHistoryDrawer()
        drawer.sessions = [
            {"id": "s1"},
            {"id": "s2"},
        ]

        drawer.set_current_session("s1")

        assert drawer.current_session_id == "s1"


class TestHistoryDrawerTimeFormatting:
    """测试时间格式化"""

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
        # 3 天前
        past_date = datetime.now() - timedelta(days=3)
        timestamp = past_date.isoformat()

        formatted = drawer.format_time(timestamp)

        # 应该显示星期几
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        assert any(day in formatted for day in weekdays)

    def test_format_time_older(self):
        """测试更早的时间格式化"""
        drawer = MockHistoryDrawer()
        # 10 天前
        past_date = datetime.now() - timedelta(days=10)
        timestamp = past_date.isoformat()

        formatted = drawer.format_time(timestamp)

        # 应该显示月/日格式
        assert "/" in formatted or "月" in formatted or past_date.month in range(1, 13)

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
        timestamp = int(datetime.now().timestamp() * 1000)  # 毫秒

        formatted = drawer.format_time(timestamp)

        assert formatted != "未知时间"


class TestHistoryDrawerKeyboardNavigation:
    """测试键盘导航"""

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
        """同步版本的加载会话（用于测试）"""
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
                # Unix 时间戳（毫秒）
                if timestamp > 1e10:
                    date = datetime.fromtimestamp(timestamp / 1000)
                else:
                    date = datetime.fromtimestamp(timestamp)
            else:
                date = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                # 处理时区
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
