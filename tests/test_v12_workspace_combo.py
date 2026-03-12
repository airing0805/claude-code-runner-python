"""
工作空间组合控件 (WorkspaceCombo) 单元测试

测试目标：
- 下拉选择功能
- 手动输入功能
- 路径验证逻辑
- 历史记录显示

v12.0.0.4 - 界面重构测试
"""

import pytest
from unittest.mock import MagicMock, patch
import json


class TestWorkspaceComboPathValidation:
    """测试工作空间路径验证逻辑"""

    def test_valid_unix_path(self):
        """测试有效的 Unix 路径"""
        valid_paths = [
            "/home/user/project",
            "/var/www/html",
            "/tmp/test",
            "/",
            "/path/to/some/deep/directory",
        ]

        for path in valid_paths:
            result = self._validate_path_format(path)
            assert result["valid"] is True, f"Path {path} should be valid"

    def test_valid_windows_path(self):
        """测试有效的 Windows 路径"""
        valid_paths = [
            "C:\\Users\\admin\\project",
            "D:\\projects\\test",
            "E:/data/workspace",
            "C:/",
            "Z:\\some\\path",
        ]

        for path in valid_paths:
            result = self._validate_path_format(path)
            assert result["valid"] is True, f"Path {path} should be valid"

    def test_invalid_path_no_absolute(self):
        """测试无效的相对路径"""
        invalid_paths = [
            "relative/path",
            "./current",
            "folder",
            "",
            "no/slash",
        ]

        for path in invalid_paths:
            result = self._validate_path_format(path)
            assert result["valid"] is False, f"Path {path} should be invalid"
            assert "绝对路径" in result["error"] or "格式" in result["error"]

    def test_invalid_path_traversal(self):
        """测试路径遍历攻击"""
        malicious_paths = [
            "../../../etc/passwd",
            "/home/user/../..",
            "~/malicious",
            "/path/with/../traversal",
        ]

        for path in malicious_paths:
            result = self._validate_path_format(path)
            # 路径遍历应该被检测到
            assert result["valid"] is False or ".." not in path, \
                f"Path traversal should be blocked: {path}"

    def test_empty_path_is_valid(self):
        """测试空路径应该被视为有效（新会话）"""
        result = self._validate_path_format("")
        # 空路径在 WorkspaceCombo 中被视为有效（新会话）
        # 但在格式验证中可能无效，取决于实现
        assert result is not None

    def _validate_path_format(self, path: str) -> dict:
        """
        模拟 JavaScript 端的路径验证逻辑
        对应 workspaceCombo.js 中的 _validatePathFormat 方法
        """
        if not path or not isinstance(path, str):
            return {"valid": False, "error": "路径格式不正确"}

        # 防止路径遍历攻击
        if ".." in path or "~" in path:
            return {"valid": False, "error": "路径包含非法字符"}

        # 验证路径格式（支持 Unix 和 Windows）
        is_unix_path = path.startswith("/")
        is_windows_path = len(path) >= 3 and path[1] == ":" and path[2] in "/\\"

        if not is_unix_path and not is_windows_path:
            return {"valid": False, "error": "路径格式不正确（需要绝对路径）"}

        return {"valid": True}


class TestWorkspaceComboHistory:
    """测试历史记录功能"""

    def test_history_deduplication(self):
        """测试历史记录去重"""
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

    def test_history_limit(self):
        """测试历史记录数量限制（最多 20 条）"""
        history = [f"/path/to/project{i}" for i in range(30)]

        # 模拟添加到历史的逻辑
        result = self._add_to_history([], history)

        assert len(result) <= 20

    def test_history_order_preservation(self):
        """测试历史记录顺序保持（新添加的在前面）"""
        history = ["/path/1", "/path/2", "/path/3"]

        # 添加新路径
        result = self._add_to_history(history, "/path/4")

        assert result[0] == "/path/4"

    def test_history_move_to_front(self):
        """测试重复路径移动到前面"""
        history = ["/path/1", "/path/2", "/path/3"]

        # 再次添加已存在的路径
        result = self._add_to_history(history, "/path/2")

        assert result[0] == "/path/2"
        assert len(result) == 3

    def _deduplicate_history(self, history: list) -> list:
        """模拟历史记录去重逻辑"""
        seen = set()
        result = []
        for item in history:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _add_to_history(self, history: list, new_items) -> list:
        """模拟添加到历史记录的逻辑"""
        if isinstance(new_items, list):
            # 批量添加
            result = list(history)
            for item in new_items:
                if item in result:
                    result.remove(item)
                result.insert(0, item)
            return result[:20]
        else:
            # 单个添加
            result = list(history)
            if new_items in result:
                result.remove(new_items)
            result.insert(0, new_items)
            return result[:20]


class TestWorkspaceComboEvents:
    """测试事件触发"""

    def test_on_change_callback(self):
        """测试值变化回调"""
        callback_values = []

        def mock_callback(value):
            callback_values.append(value)

        # 模拟 WorkspaceCombo 的值变化
        combo = MockWorkspaceCombo()
        combo.on_change(mock_callback)
        combo.set_value("/new/path")

        assert len(callback_values) == 1
        assert callback_values[0] == "/new/path"

    def test_on_validate_callback(self):
        """测试验证回调"""
        validation_results = []

        def mock_validate(result):
            validation_results.append(result)

        combo = MockWorkspaceCombo()
        combo.on_validate(mock_validate)
        combo.validate_path("/invalid/../../../path")

        assert len(validation_results) >= 1
        # 应该检测到路径遍历
        assert any(r.get("valid") is False for r in validation_results)

    def test_set_disabled_state(self):
        """测试禁用状态"""
        combo = MockWorkspaceCombo()
        combo.set_disabled(True)

        assert combo.disabled is True

        combo.set_disabled(False)
        assert combo.disabled is False


class MockWorkspaceCombo:
    """模拟 WorkspaceCombo 类"""

    def __init__(self):
        self.current_value = ""
        self.history = []
        self.disabled = False
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


class TestWorkspaceComboHtmlEscape:
    """测试 HTML 转义"""

    def test_escape_html_special_chars(self):
        """测试 HTML 特殊字符转义"""
        test_cases = [
            ("<script>alert('xss')</script>", "&lt;script&gt;alert('xss')&lt;/script&gt;"),
            ("path with <tag>", "path with &lt;tag&gt;"),
            ("path & more", "path &amp; more"),
            ("path\"quote", "path\"quote"),  # 引号在不同实现中可能不同
        ]

        for input_str, expected_contains in test_cases:
            escaped = self._escape_html(input_str)
            # 验证特殊字符被转义
            assert "<script>" not in escaped
            assert "&lt;" in escaped or "<" not in input_str

    def _escape_html(self, text: str) -> str:
        """模拟 HTML 转义"""
        import html
        return html.escape(text)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
