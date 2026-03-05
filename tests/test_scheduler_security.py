"""任务调度安全验证单元测试"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from app.scheduler.security import (
    SecurityError,
    validate_workspace,
    validate_allowed_tools,
    validate_prompt_length,
    validate_timeout,
    validate_task_name,
    validate_cron_expression,
    validate_auto_approve,
    validate_task_id,
    sanitize_input,
    is_safe_path,
    sanitize_file_path,
    VALID_TOOLS,
    FORBIDDEN_DIRS,
    PATH_TRAVERSAL_PATTERNS,
    VALID_NAME_PATTERN,
    MAX_PROMPT_LENGTH,
    MAX_NAME_LENGTH,
    MIN_TIMEOUT,
    MAX_TIMEOUT,
)


class TestValidateWorkspace:
    """工作目录验证测试"""

    def test_validate_workspace_none_returns_default(self):
        """测试空值返回默认值"""
        result = validate_workspace(None)
        assert result == "."

    def test_validate_workspace_empty_returns_default(self):
        """测试空字符串返回默认值"""
        result = validate_workspace("")
        assert result == "."

    def test_validate_workspace_whitespace_returns_default(self):
        """测试空白返回默认值"""
        result = validate_workspace("   ")
        assert result == "."

    def test_validate_workspace_with_dots(self):
        """测试包含点的路径"""
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("../etc")

        assert "PATH_TRAVERSAL_DETECTED" in exc_info.value.code

    def test_validate_workspace_with_tilde(self):
        """测试包含波浪号的路径"""
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("~/file")

        assert "PATH_TRAVERSAL_DETECTED" in exc_info.value.code

    def test_validate_workspace_simple_path(self, tmp_path):
        """测试简单路径"""
        result = validate_workspace(str(tmp_path))
        assert isinstance(result, str)
        assert str(tmp_path) in result

    def test_validate_workspace_forbidden_windows_system32(self):
        """测试 Windows 禁止目录"""
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("C:\\Windows\\System32")

        assert "FORBIDDEN_DIRECTORY" in exc_info.value.code

    def test_validate_workspace_forbidden_program_files(self):
        """测试 Program Files 禁止目录"""
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("C:\\Program Files")

        assert "FORBIDDEN_DIRECTORY" in exc_info.value.code

    @pytest.mark.skipif(os.name == "nt", reason="Unix-only test")
    def test_validate_workspace_forbidden_unix_etc(self):
        """测试 Unix 禁止目录 /etc"""
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("/etc/passwd")

        assert "FORBIDDEN_DIRECTORY" in exc_info.value.code

    @pytest.mark.skipif(os.name == "nt", reason="Unix-only test")
    def test_validate_workspace_forbidden_unix_root(self):
        """测试 Unix 禁止目录 /root"""
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("/root")

        assert "FORBIDDEN_DIRECTORY" in exc_info.value.code

    @pytest.mark.skipif(os.name == "nt", reason="Unix-only test")
    @patch.dict(os.environ, {"WORKING_DIR": "/safe/dir"}, clear=True)
    def test_validate_workspace_default_indicator(self):
        """测试默认工作空间标识符"""
        result = validate_workspace("默认工作空间")
        assert "safe" in result

    @pytest.mark.skipif(os.name == "nt", reason="Unix-only test")
    @patch.dict(os.environ, {"WORKING_DIR": "/custom/dir"}, clear=True)
    def test_validate_workspace_custom_working_dir(self):
        """测试自定义工作目录"""
        result = validate_workspace(".")
        assert "custom" in result

    def test_validate_workspace_invalid_path(self):
        """测试无效路径"""
        # 在 Windows 上测试路径遍历
        if os.name == "nt":
            with pytest.raises(SecurityError) as exc_info:
                validate_workspace("C:\\Windows\\System32\\..\\..\\..\\etc")

            # 可能是 FORBIDDEN_DIRECTORY 或 PATH_TRAVERSAL_DETECTED
            assert "FORBIDDEN" in exc_info.value.code or "PATH_TRAVERSAL" in exc_info.value.code
        else:
            # Unix 上测试路径遍历
            with pytest.raises(SecurityError) as exc_info:
                validate_workspace("../../../etc/passwd")

            assert "PATH_TRAVERSAL_DETECTED" in exc_info.value.code


class TestValidateAllowedTools:
    """工具白名单验证测试"""

    def test_validate_allowed_tools_none(self):
        """测试 None 值"""
        result = validate_allowed_tools(None)
        assert result is None

    def test_validate_allowed_tools_empty_list(self):
        """测试空列表"""
        result = validate_allowed_tools([])
        assert result == []

    def test_validate_allowed_tools_valid_tools(self):
        """测试有效工具"""
        result = validate_allowed_tools(["Read", "Write", "Edit", "Glob"])
        assert result == ["Read", "Write", "Edit", "Glob"]

    def test_validate_allowed_tools_mcp_tool(self):
        """测试 MCP 工具"""
        result = validate_allowed_tools(["mcp__filesystem__read_file"])
        assert result == ["mcp__filesystem__read_file"]

    def test_validate_allowed_tools_task_variant(self):
        """测试 Task 工具变体"""
        result = validate_allowed_tools(["Task-xxx"])
        assert result == ["Task-xxx"]

    def test_validate_allowed_tools_invalid_tool(self):
        """测试无效工具"""
        with pytest.raises(SecurityError) as exc_info:
            validate_allowed_tools(["InvalidTool"])

        assert exc_info.value.code == "INVALID_TOOL_NAME"
        assert "InvalidTool" in str(exc_info.value)

    def test_validate_allowed_tools_mcp_invalid_format(self):
        """测试格式错误的 MCP 工具"""
        with pytest.raises(SecurityError) as exc_info:
            validate_allowed_tools(["mcp__invalid"])

        assert exc_info.value.code == "INVALID_TOOL_NAME"

    def test_validate_allowed_tools_mcp_full_format(self):
        """测试完整格式的 MCP 工具"""
        result = validate_allowed_tools(["mcp__github__create_issue"])
        assert result == ["mcp__github__create_issue"]


class TestValidatePromptLength:
    """提示词长度验证测试"""

    def test_validate_prompt_length_valid(self):
        """测试有效长度"""
        result = validate_prompt_length("正常长度的提示词")
        assert result == "正常长度的提示词"

    def test_validate_prompt_length_empty(self):
        """测试空提示词"""
        with pytest.raises(SecurityError) as exc_info:
            validate_prompt_length("")

        assert exc_info.value.code == "EMPTY_PROMPT"
        assert "不能为空" in exc_info.value.message

    def test_validate_prompt_length_whitespace_only(self):
        """测试纯空白提示词"""
        with pytest.raises(SecurityError) as exc_info:
            validate_prompt_length("   \t\n   ")

        assert exc_info.value.code == "EMPTY_PROMPT"

    def test_validate_prompt_length_too_long(self):
        """测试超长提示词"""
        long_prompt = "x" * (MAX_PROMPT_LENGTH + 1)
        with pytest.raises(SecurityError) as exc_info:
            validate_prompt_length(long_prompt)

        assert exc_info.value.code == "PROMPT_TOO_LONG"
        assert f"({MAX_PROMPT_LENGTH + 1} > {MAX_PROMPT_LENGTH})" in exc_info.value.message

    def test_validate_prompt_length_max_allowed(self):
        """测试最大允许长度"""
        max_prompt = "x" * MAX_PROMPT_LENGTH
        result = validate_prompt_length(max_prompt)
        assert len(result) == MAX_PROMPT_LENGTH

    def test_validate_prompt_length_trims_whitespace(self):
        """测试空白符裁剪"""
        result = validate_prompt_length("  测试提示词  ")
        assert result == "测试提示词"
        assert result[0] != " "
        assert result[-1] != " "

    def test_validate_prompt_length_custom_max(self):
        """测试自定义最大长度"""
        result = validate_prompt_length("abc", max_length=10)
        assert result == "abc"


class TestValidateTimeout:
    """超时时间验证测试"""

    def test_validate_timeout_valid(self):
        """测试有效超时"""
        result = validate_timeout(60000)
        assert result == 60000

    def test_validate_timeout_minimum(self):
        """测试最小超时"""
        result = validate_timeout(MIN_TIMEOUT)
        assert result == MIN_TIMEOUT

    def test_validate_timeout_maximum(self):
        """测试最大超时"""
        result = validate_timeout(MAX_TIMEOUT)
        assert result == MAX_TIMEOUT

    def test_validate_timeout_too_small(self):
        """测试超时过小"""
        with pytest.raises(SecurityError) as exc_info:
            validate_timeout(MIN_TIMEOUT - 1)

        assert exc_info.value.code == "TIMEOUT_TOO_SMALL"
        assert f"不能小于 {MIN_TIMEOUT} 毫秒" in exc_info.value.message

    def test_validate_timeout_too_large(self):
        """测试超时过大"""
        with pytest.raises(SecurityError) as exc_info:
            validate_timeout(MAX_TIMEOUT + 1)

        assert exc_info.value.code == "TIMEOUT_TOO_LARGE"
        assert f"不能超过 {MAX_TIMEOUT} 毫秒" in exc_info.value.message


class TestValidateTaskName:
    """任务名称验证测试"""

    def test_validate_task_name_valid(self):
        """测试有效名称"""
        result = validate_task_name("测试任务")
        assert result == "测试任务"

    def test_validate_task_name_with_numbers(self):
        """测试包含数字"""
        result = validate_task_name("任务123")
        assert result == "任务123"

    def test_validate_task_name_with_underscores(self):
        """测试包含下划线"""
        result = validate_task_name("test_task")
        assert result == "test_task"

    def test_validate_task_name_with_hyphens(self):
        """测试包含连字符"""
        result = validate_task_name("my-task-name")
        assert result == "my-task-name"

    def test_validate_task_name_empty(self):
        """测试空名称"""
        with pytest.raises(SecurityError) as exc_info:
            validate_task_name("")

        assert exc_info.value.code == "EMPTY_NAME"
        assert "不能为空" in exc_info.value.message

    def test_validate_task_name_whitespace_only(self):
        """测试纯空白名称"""
        with pytest.raises(SecurityError) as exc_info:
            validate_task_name("   ")

        assert exc_info.value.code == "EMPTY_NAME"

    def test_validate_task_name_too_long(self):
        """测试超长名称"""
        long_name = "x" * (MAX_NAME_LENGTH + 1)
        with pytest.raises(SecurityError) as exc_info:
            validate_task_name(long_name)

        assert exc_info.value.code == "NAME_TOO_LONG"

    def test_validate_task_name_invalid_characters(self):
        """测试非法字符"""
        with pytest.raises(SecurityError) as exc_info:
            validate_task_name("任务@#$")

        assert exc_info.value.code == "INVALID_NAME_CHARACTER"
        assert "非法字符" in exc_info.value.message

    def test_validate_task_name_custom_max(self):
        """测试自定义最大长度"""
        result = validate_task_name("abc", max_length=10)
        assert result == "abc"


class TestValidateCronExpression:
    """Cron 表达式验证测试"""

    def test_validate_cron_expression_valid(self):
        """测试有效表达式"""
        result = validate_cron_expression("0 * * * *")
        assert result == "0 * * * *"

    def test_validate_cron_expression_empty(self):
        """测试空表达式"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("")

        assert exc_info.value.code == "EMPTY_CRON"
        assert "不能为空" in exc_info.value.message

    def test_validate_cron_expression_whitespace(self):
        """测试空白表达式"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("   ")

        assert exc_info.value.code == "EMPTY_CRON"

    def test_validate_cron_expression_too_long(self):
        """测试超长表达式"""
        long_cron = "x" * 101
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression(long_cron)

        assert exc_info.value.code == "CRON_TOO_LONG"

    def test_validate_cron_expression_with_dollar(self):
        """测试包含 $"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("0 $ * * *")

        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_validate_cron_expression_with_semicolon(self):
        """测试包含 ;"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("0 ; * * *")

        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_validate_cron_expression_with_ampersand(self):
        """测试包含 &"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("0 & * * *")

        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_validate_cron_expression_with_pipe(self):
        """测试包含 |"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("0 | * * *")

        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_validate_cron_expression_with_greater_than(self):
        """测试包含 >"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("0 > * * *")

        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_validate_cron_expression_with_less_than(self):
        """测试包含 <"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("0 < * * *")

        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_validate_cron_expression_with_backtick(self):
        """测试包含 `"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("0 ` * * *")

        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_validate_cron_expression_trims_whitespace(self):
        """测试空白符裁剪"""
        result = validate_cron_expression("  0 * * * *  ")
        assert result == "0 * * * *"
        assert result[0] != " "
        assert result[-1] != " "


class TestValidateAutoApprove:
    """自动批准验证测试"""

    def test_validate_auto_approve_true(self):
        """测试 True"""
        result = validate_auto_approve(True)
        assert result is True

    def test_validate_auto_approve_false(self):
        """测试 False"""
        result = validate_auto_approve(False)
        assert result is False

    def test_validate_auto_approve_truthy(self):
        """测试真值"""
        result = validate_auto_approve(1)
        assert result is True

    def test_validate_auto_approve_falsy(self):
        """测试假值"""
        result = validate_auto_approve(0)
        assert result is False

    def test_validate_auto_approve_string_true(self):
        """测试字符串 'true'"""
        result = validate_auto_approve("true")
        assert result is True

    def test_validate_auto_approve_string_false(self):
        """测试字符串 'false'"""
        result = validate_auto_approve("false")
        assert result is True  # 非 False 都返回 True


class TestValidateTaskId:
    """任务 ID 验证测试"""

    def test_validate_task_id_valid(self):
        """测试有效 ID"""
        result = validate_task_id("task-123-abc")
        assert result == "task-123-abc"

    def test_validate_task_id_uuid(self):
        """测试 UUID 格式"""
        result = validate_task_id("550e8400-e29b-41d4-a716-446655440000")
        assert result == "550e8400-e29b-41d4-a716-446655440000"

    def test_validate_task_id_empty(self):
        """测试空 ID"""
        with pytest.raises(SecurityError) as exc_info:
            validate_task_id("")

        assert exc_info.value.code == "EMPTY_TASK_ID"
        assert "不能为空" in exc_info.value.message

    def test_validate_task_id_whitespace(self):
        """测试空白 ID"""
        with pytest.raises(SecurityError) as exc_info:
            validate_task_id("   ")

        assert exc_info.value.code == "EMPTY_TASK_ID"

    def test_validate_task_id_trims_whitespace(self):
        """测试空白符裁剪"""
        result = validate_task_id("  task-id  ")
        assert result == "task-id"
        assert result[0] != " "
        assert result[-1] != " "


class TestSanitizeInput:
    """输入清理测试"""

    def test_sanitize_input_normal_text(self):
        """测试普通文本"""
        result = sanitize_input("正常文本")
        assert result == "正常文本"

    def test_sanitize_input_with_control_chars(self):
        """测试包含控制字符"""
        result = sanitize_input("text\x00\x01\x02end")
        assert result == "textend"

    def test_sanitize_input_preserves_newlines(self):
        """测试保留换行符"""
        result = sanitize_input("line1\nline2\r\nline3")
        assert "\n" in result
        assert "\r\n" in result

    def test_sanitize_input_preserves_tabs(self):
        """测试保留制表符"""
        result = sanitize_input("col1\tcol2")
        assert "\t" in result

    def test_sanitize_input_removes_script_tags(self):
        """测试移除 script 标签"""
        result = sanitize_input("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script" in result

    def test_sanitize_input_special_chars(self):
        """测试特殊字符处理"""
        result = sanitize_input("hello 世界 test")
        assert "hello 世界 test" in result


class TestIsSafePath:
    """路径安全检查测试"""

    def test_is_safe_path_within_base(self, tmp_path):
        """测试在基础目录内的路径"""
        base = tmp_path / "base"
        base.mkdir()
        result = is_safe_path(str(base), str(base / "subdir"))
        assert result is True

    def test_is_safe_path_exact_base(self, tmp_path):
        """测试基础目录本身"""
        base = tmp_path / "base"
        base.mkdir()
        result = is_safe_path(str(base), str(base))
        assert result is True

    def test_is_safe_path_parent_traversal(self, tmp_path):
        """测试父目录遍历"""
        base = tmp_path / "base"
        base.mkdir()
        result = is_safe_path(str(base), "../other")
        assert result is False

    def test_is_safe_path_absolute_outside(self, tmp_path):
        """测试基础目录外的绝对路径"""
        base = tmp_path / "base"
        base.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        result = is_safe_path(str(base), str(outside))
        assert result is False

    def test_is_safe_path_symlink_like(self, tmp_path):
        """测试符号链接风格路径"""
        base = tmp_path / "base"
        base.mkdir()
        result = is_safe_path(str(base), "/etc/passwd")
        assert result is False

    def test_is_safe_path_invalid_base(self, tmp_path):
        """测试无效基础目录"""
        base = tmp_path / "nonexistent"
        result = is_safe_path(str(base), "subdir")
        assert result is False


class TestSanitizeFilePath:
    """文件路径清理测试"""

    def test_sanitize_file_path_normal(self):
        """测试普通路径"""
        result = sanitize_file_path("/path/to/file.txt")
        assert result == "/path/to/file.txt"

    def test_sanitize_file_path_removes_parent(self):
        """测试移除父目录引用"""
        result = sanitize_file_path("/path/../to/file.txt")
        assert ".." not in result

    def test_sanitize_file_path_removes_tilde(self):
        """测试移除波浪号"""
        result = sanitize_file_path("~/file.txt")
        assert "~" not in result

    def test_sanitize_file_path_removes_control_chars(self):
        """测试移除控制字符"""
        result = sanitize_file_path("/path\x00/file.txt")
        assert "\x00" not in result

    def test_sanitize_file_path_preserves_allowed(self):
        """测试保留允许的字符"""
        result = sanitize_file_path("/path/to/file_name-123.txt")
        assert "/" in result
        assert "-" in result
        assert "_" in result
        assert "." in result


class TestConstants:
    """常量测试"""

    def test_valid_tools_not_empty(self):
        """测试有效工具列表不为空"""
        assert len(VALID_TOOLS) > 0
        assert "Read" in VALID_TOOLS
        assert "Write" in VALID_TOOLS
        assert "Edit" in VALID_TOOLS

    def test_forbidden_dirs_not_empty(self):
        """测试禁止目录列表不为空"""
        assert len(FORBIDDEN_DIRS) > 0
        assert "/etc" in FORBIDDEN_DIRS
        assert "C:\\Windows" in FORBIDDEN_DIRS

    def test_path_traversal_patterns(self):
        """测试路径遍历模式"""
        assert ".." in PATH_TRAVERSAL_PATTERNS
        assert "~" in PATH_TRAVERSAL_PATTERNS

    def test_valid_name_pattern_matches(self):
        """测试名称模式匹配"""
        assert VALID_NAME_PATTERN.match("test_name") is not None
        assert VALID_NAME_PATTERN.match("测试名称") is not None
        assert VALID_NAME_PATTERN.match("name-123") is not None

    def test_valid_name_pattern_rejects(self):
        """测试名称模式拒绝"""
        assert VALID_NAME_PATTERN.match("name@test") is None
        assert VALID_NAME_PATTERN.match("name#tag") is None

    def test_max_prompt_length(self):
        """测试最大提示词长度常量"""
        assert MAX_PROMPT_LENGTH == 10000

    def test_max_name_length(self):
        """测试最大名称长度常量"""
        assert MAX_NAME_LENGTH == 100

    def test_min_timeout(self):
        """测试最小超时常量"""
        assert MIN_TIMEOUT == 1000

    def test_max_timeout(self):
        """测试最大超时常量"""
        assert MAX_TIMEOUT == 3600000


class TestSecurityError:
    """安全错误类测试"""

    def test_security_error_creation(self):
        """测试错误创建"""
        error = SecurityError("测试错误", "TEST_CODE")
        assert error.message == "测试错误"
        assert error.code == "TEST_CODE"

    def test_security_error_default_code(self):
        """测试默认错误代码"""
        error = SecurityError("测试错误")
        assert error.code == "SECURITY_ERROR"

    def test_security_error_str_representation(self):
        """测试字符串表示"""
        error = SecurityError("测试错误", "TEST_CODE")
        error_str = str(error)
        assert "测试错误" in error_str

    def test_security_error_inheritance(self):
        """测试继承自 Exception"""
        error = SecurityError("测试")
        assert isinstance(error, Exception)

    def test_security_error_can_be_raised(self):
        """测试可以抛出"""
        with pytest.raises(SecurityError) as exc_info:
            raise SecurityError("错误消息", "ERROR_CODE")

        assert exc_info.value.message == "错误消息"
        assert exc_info.value.code == "ERROR_CODE"
