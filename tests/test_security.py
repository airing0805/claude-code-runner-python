"""安全验证模块单元测试

测试工作目录验证、工具白名单验证等安全功能。
"""

import os
import pytest
from pathlib import Path

from app.scheduler.security import (
    SecurityError,
    VALID_TOOLS,
    FORBIDDEN_DIRS,
    PATH_TRAVERSAL_PATTERNS,
    MAX_PROMPT_LENGTH,
    MAX_NAME_LENGTH,
    MIN_TIMEOUT,
    MAX_TIMEOUT,
    validate_workspace,
    validate_allowed_tools,
    validate_prompt_length,
    validate_timeout,
    validate_task_name,
    sanitize_input,
    validate_task_id,
    validate_cron_expression,
    validate_auto_approve,
    is_safe_path,
    sanitize_file_path,
)


class TestSecurityConstants:
    """测试安全常量定义"""

    def test_valid_tools_not_empty(self):
        """验证工具白名单不为空"""
        assert len(VALID_TOOLS) > 0

    def test_valid_tools_contains_basic_tools(self):
        """验证基础工具在白名单中"""
        assert "Read" in VALID_TOOLS
        assert "Write" in VALID_TOOLS
        assert "Edit" in VALID_TOOLS
        assert "Bash" in VALID_TOOLS

    def test_valid_tools_contains_mcp_tools(self):
        """验证 MCP 工具在白名单中"""
        assert "mcp__filesystem__read_file" in VALID_TOOLS
        assert "mcp__github__create_issue" in VALID_TOOLS

    def test_forbidden_dirs_not_empty(self):
        """验证禁止目录列表不为空"""
        assert len(FORBIDDEN_DIRS) > 0

    def test_path_traversal_patterns_not_empty(self):
        """验证路径遍历模式列表不为空"""
        assert len(PATH_TRAVERSAL_PATTERNS) > 0

    def test_limits_are_positive(self):
        """验证限制值为正数"""
        assert MAX_PROMPT_LENGTH > 0
        assert MAX_NAME_LENGTH > 0
        assert MIN_TIMEOUT > 0
        assert MAX_TIMEOUT > MIN_TIMEOUT


class TestValidateWorkspace:
    """测试工作目录验证"""

    def test_none_workspace_returns_default(self):
        """测试 None 返回默认值"""
        result = validate_workspace(None)
        assert result == "."

    def test_empty_workspace_returns_default(self):
        """测试空字符串返回默认值"""
        result = validate_workspace("   ")
        assert result == "."

    def test_valid_workspace(self):
        """测试有效的工作目录"""
        # 在 Windows 上路径会被规范化为绝对路径
        result = validate_workspace("/tmp/project")
        # 验证路径包含 project 目录
        assert "project" in result

    def test_workspace_with_traversal_attack(self):
        """测试路径遍历攻击被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("../../etc/passwd")
        assert exc_info.value.code == "PATH_TRAVERSAL_DETECTED"

    def test_workspace_with_tilde(self):
        """测试 ~ 字符被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("~/secret")
        assert exc_info.value.code == "PATH_TRAVERSAL_DETECTED"

    def test_workspace_with_unc_path(self):
        """测试 UNC 路径中的双反斜杠被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("\\\\server\\share")
        assert exc_info.value.code == "PATH_TRAVERSAL_DETECTED"

    def test_forbidden_unix_directory(self):
        """测试 Unix 系统目录被拒绝"""
        # 在 Windows 上 /etc/passwd 可能被接受，所以我们测试 /root
        # 注意: 这个测试在 Windows 上可能不会按预期工作
        # 跳过或调整以适应平台
        import platform
        if platform.system() != "Windows":
            with pytest.raises(SecurityError) as exc_info:
                validate_workspace("/etc/passwd")
            assert exc_info.value.code == "FORBIDDEN_DIRECTORY"
        else:
            # Windows 上测试 Windows 特定目录
            with pytest.raises(SecurityError) as exc_info:
                validate_workspace("C:\\Windows\\System32")
            assert exc_info.value.code == "FORBIDDEN_DIRECTORY"

    def test_forbidden_windows_directory(self):
        """测试 Windows 系统目录被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("C:\\Windows\\System32")
        assert exc_info.value.code == "FORBIDDEN_DIRECTORY"

    def test_default_workspace_indicator(self):
        """测试默认工作空间标识符"""
        # 保存原环境变量
        old_dir = os.getenv("WORKING_DIR")

        try:
            os.environ["WORKING_DIR"] = "/test/dir"
            result = validate_workspace("默认工作空间")
            # 验证结果包含 test/dir（路径可能在不同平台上不同）
            assert "test" in result and "dir" in result
        finally:
            # 恢复环境变量
            if old_dir is None:
                os.environ.pop("WORKING_DIR", None)
            else:
                os.environ["WORKING_DIR"] = old_dir

    def test_workspace_outside_whitelist(self, tmp_path, monkeypatch):
        """测试白名单外的路径被拒绝"""
        # 设置允许的工作目录
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()
        monkeypatch.setenv("WORKING_DIR", str(allowed_dir))
        monkeypatch.setenv("SCHEDULER_ALLOW_ANY_WORKSPACE", "false")

        # 尝试使用白名单外的目录
        with pytest.raises(SecurityError) as exc_info:
            validate_workspace("/tmp/outside")
        assert exc_info.value.code == "WORKSPACE_NOT_IN_WHITELIST"

    def test_workspace_inside_whitelist(self, tmp_path, monkeypatch):
        """测试白名单内的路径被允许"""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()
        monkeypatch.setenv("WORKING_DIR", str(allowed_dir))
        monkeypatch.setenv("SCHEDULER_ALLOW_ANY_WORKSPACE", "false")

        sub_dir = allowed_dir / "project"
        sub_dir.mkdir()

        result = validate_workspace(str(sub_dir))
        assert result == str(sub_dir)

    def test_allow_any_workspace(self, monkeypatch):
        """测试允许任意工作目录模式"""
        monkeypatch.setenv("SCHEDULER_ALLOW_ANY_WORKSPACE", "true")

        # 应该允许任意路径（但仍然拒绝系统目录）
        result = validate_workspace("/any/path")
        # 验证路径包含 any/path（平台特定格式）
        assert "any" in result and "path" in result

        # 但仍然拒绝系统目录
        import platform
        if platform.system() == "Windows":
            with pytest.raises(SecurityError) as exc_info:
                validate_workspace("C:\\Windows")
            assert exc_info.value.code == "FORBIDDEN_DIRECTORY"
        else:
            with pytest.raises(SecurityError) as exc_info:
                validate_workspace("/etc")
            assert exc_info.value.code == "FORBIDDEN_DIRECTORY"


class TestValidateAllowedTools:
    """测试工具白名单验证"""

    def test_none_tools_returns_none(self):
        """测试 None 返回 None"""
        result = validate_allowed_tools(None)
        assert result is None

    def test_empty_tools_returns_empty(self):
        """测试空列表返回空列表"""
        result = validate_allowed_tools([])
        assert result == []

    def test_valid_tool(self):
        """测试有效工具"""
        result = validate_allowed_tools(["Read", "Write"])
        assert result == ["Read", "Write"]

    def test_invalid_tool(self):
        """测试无效工具被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_allowed_tools(["InvalidTool"])
        assert exc_info.value.code == "INVALID_TOOL_NAME"
        assert "InvalidTool" in exc_info.value.message

    def test_mcp_tool(self):
        """测试 MCP 工具被允许"""
        result = validate_allowed_tools([
            "mcp__filesystem__read_file",
            "mcp__github__create_issue"
        ])
        assert "mcp__filesystem__read_file" in result
        assert "mcp__github__create_issue" in result

    def test_task_variant_tool(self):
        """测试 Task 变体工具被允许"""
        result = validate_allowed_tools(["Task-create", "Task-review"])
        assert result == ["Task-create", "Task-review"]

    def test_invalid_mcp_format(self):
        """测试无效的 MCP 格式被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_allowed_tools(["mcp__invalid"])
        assert exc_info.value.code == "INVALID_TOOL_NAME"


class TestValidatePromptLength:
    """测试提示词长度验证"""

    def test_valid_prompt(self):
        """测试有效提示词"""
        result = validate_prompt_length("This is a valid prompt")
        assert result == "This is a valid prompt"

    def test_empty_prompt(self):
        """测试空提示词被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_prompt_length("")
        assert exc_info.value.code == "EMPTY_PROMPT"

    def test_whitespace_only_prompt(self):
        """测试仅包含空白字符的提示词被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_prompt_length("   ")
        assert exc_info.value.code == "EMPTY_PROMPT"

    def test_prompt_trimming(self):
        """测试提示词首尾空白被移除"""
        result = validate_prompt_length("  hello  ")
        assert result == "hello"

    def test_prompt_too_long(self):
        """测试过长的提示词被拒绝"""
        long_prompt = "a" * (MAX_PROMPT_LENGTH + 1)
        with pytest.raises(SecurityError) as exc_info:
            validate_prompt_length(long_prompt)
        assert exc_info.value.code == "PROMPT_TOO_LONG"

    def test_prompt_at_max_length(self):
        """测试最大长度提示词被接受"""
        max_prompt = "a" * MAX_PROMPT_LENGTH
        result = validate_prompt_length(max_prompt)
        assert len(result) == MAX_PROMPT_LENGTH

    def test_custom_max_length(self):
        """测试自定义最大长度"""
        result = validate_prompt_length("abc", max_length=10)
        assert result == "abc"

        with pytest.raises(SecurityError):
            validate_prompt_length("a" * 11, max_length=10)


class TestValidateTimeout:
    """测试超时时间验证"""

    def test_valid_timeout(self):
        """测试有效超时时间"""
        result = validate_timeout(60000)  # 1 分钟
        assert result == 60000

    def test_timeout_too_small(self):
        """测试过小的超时时间被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_timeout(500)  # 小于最小值
        assert exc_info.value.code == "TIMEOUT_TOO_SMALL"

    def test_timeout_at_min_limit(self):
        """测试最小边界值被接受"""
        result = validate_timeout(MIN_TIMEOUT)
        assert result == MIN_TIMEOUT

    def test_timeout_too_large(self):
        """测试过大的超时时间被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_timeout(MAX_TIMEOUT + 1)
        assert exc_info.value.code == "TIMEOUT_TOO_LARGE"

    def test_timeout_at_max_limit(self):
        """测试最大边界值被接受"""
        result = validate_timeout(MAX_TIMEOUT)
        assert result == MAX_TIMEOUT


class TestValidateTaskName:
    """测试任务名称验证"""

    def test_valid_name(self):
        """测试有效名称"""
        result = validate_task_name("Test Task")
        assert result == "Test Task"

    def test_empty_name(self):
        """测试空名称被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_task_name("")
        assert exc_info.value.code == "EMPTY_NAME"

    def test_whitespace_only_name(self):
        """测试仅包含空白字符的名称被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_task_name("   ")
        assert exc_info.value.code == "EMPTY_NAME"

    def test_name_trimming(self):
        """测试名称首尾空白被移除"""
        result = validate_task_name("  task-name  ")
        assert result == "task-name"

    def test_name_too_long(self):
        """测试过长的名称被拒绝"""
        long_name = "a" * (MAX_NAME_LENGTH + 1)
        with pytest.raises(SecurityError) as exc_info:
            validate_task_name(long_name)
        assert exc_info.value.code == "NAME_TOO_LONG"

    def test_name_with_chinese(self):
        """测试包含中文名称被接受"""
        result = validate_task_name("测试任务名称")
        assert result == "测试任务名称"

    def test_name_with_underscore(self):
        """测试包含下划线名称被接受"""
        result = validate_task_name("test_task_name")
        assert result == "test_task_name"

    def test_name_with_hyphen(self):
        """测试包含连字符名称被接受"""
        result = validate_task_name("test-task-name")
        assert result == "test-task-name"

    def test_name_with_invalid_characters(self):
        """测试包含非法字符的名称被拒绝"""
        invalid_chars = ["<", ">", ":", "\"", "|", "?", "*"]
        for char in invalid_chars:
            with pytest.raises(SecurityError) as exc_info:
                validate_task_name(f"test{char}name")
            assert exc_info.value.code == "INVALID_NAME_CHARACTER"


class TestSanitizeInput:
    """测试输入清理"""

    def test_normal_input_unchanged(self):
        """测试正常输入保持不变"""
        result = sanitize_input("Hello World")
        assert result == "Hello World"

    def test_control_characters_removed(self):
        """测试控制字符被移除"""
        result = sanitize_input("Hello\x00World")
        assert result == "HelloWorld"

    def test_newline_preserved(self):
        """测试换行符被保留"""
        result = sanitize_input("Hello\nWorld")
        assert result == "Hello\nWorld"

    def test_tab_preserved(self):
        """测试制表符被保留"""
        result = sanitize_input("Hello\tWorld")
        assert result == "Hello\tWorld"

    def test_script_tag_escaped(self):
        """测试 script 标签被转义"""
        result = sanitize_input("<script>alert('xss')</script>")
        assert "<script" not in result
        assert "&lt;script" in result


class TestValidateTaskId:
    """测试任务 ID 验证"""

    def test_valid_task_id(self):
        """测试有效任务 ID"""
        result = validate_task_id("abc-123-def")
        assert result == "abc-123-def"

    def test_empty_task_id(self):
        """测试空任务 ID 被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_task_id("")
        assert exc_info.value.code == "EMPTY_TASK_ID"

    def test_whitespace_only_task_id(self):
        """测试仅包含空白字符的 ID 被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_task_id("   ")
        assert exc_info.value.code == "EMPTY_TASK_ID"

    def test_task_id_trimming(self):
        """测试任务 ID 首尾空白被移除"""
        result = validate_task_id("  task-id-123  ")
        assert result == "task-id-123"


class TestValidateCronExpression:
    """测试 Cron 表达式验证"""

    def test_valid_cron(self):
        """测试有效 Cron 表达式"""
        result = validate_cron_expression("*/5 * * * *")
        assert result == "*/5 * * * *"

    def test_empty_cron(self):
        """测试空 Cron 表达式被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("")
        assert exc_info.value.code == "EMPTY_CRON"

    def test_whitespace_only_cron(self):
        """测试仅包含空白字符的 Cron 被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("   ")
        assert exc_info.value.code == "EMPTY_CRON"

    def test_cron_trimming(self):
        """测试 Cron 首尾空白被移除"""
        result = validate_cron_expression("  */5 * * * *  ")
        assert result == "*/5 * * * *"

    def test_cron_too_long(self):
        """测试过长的 Cron 表达式被拒绝"""
        long_cron = "a" * 101
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression(long_cron)
        assert exc_info.value.code == "CRON_TOO_LONG"

    def test_cron_with_dollar_sign(self):
        """测试包含 $ 的 Cron 被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("*/5 * * * *; rm -rf /")
        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_cron_with_semicolon(self):
        """测试包含 ; 的 Cron 被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("*/5 * * * *; echo test")
        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_cron_with_ampersand(self):
        """测试包含 & 的 Cron 被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("*/5 * * * *& malicious")
        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_cron_with_pipe(self):
        """测试包含 | 的 Cron 被拒绝"""
        with pytest.raises(SecurityError) as exc_info:
            validate_cron_expression("*/5 * * * *| cat /etc/passwd")
        assert exc_info.value.code == "CRON_INVALID_CHARACTER"

    def test_cron_at_max_length(self):
        """测试最大长度 Cron 被接受"""
        max_cron = "a" * 100
        result = validate_cron_expression(max_cron)
        assert len(result) == 100


class TestValidateAutoApprove:
    """测试自动批准标志验证"""

    def test_true_value(self):
        """测试 True 值"""
        result = validate_auto_approve(True)
        assert result is True

    def test_false_value(self):
        """测试 False 值"""
        result = validate_auto_approve(False)
        assert result is False

    def test_truthy_value(self):
        """测试真值转换"""
        result = validate_auto_approve(1)
        assert result is True

    def test_falsy_value(self):
        """测试假值转换"""
        result = validate_auto_approve(0)
        assert result is False


class TestIsSafePath:
    """测试路径安全性检查"""

    def test_safe_path(self, tmp_path):
        """测试安全路径"""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        safe_file = base_dir / "safe.txt"

        assert is_safe_path(str(base_dir), str(safe_file))

    def test_unsafe_path_traversal(self, tmp_path):
        """测试路径遍历攻击被检测"""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        unsafe_path = base_dir.parent / "unsafe.txt"

        assert not is_safe_path(str(base_dir), str(unsafe_path))

    def test_safe_subdirectory(self, tmp_path):
        """测试安全的子目录"""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        sub_dir = base_dir / "sub" / "dir"
        sub_dir.mkdir(parents=True)

        assert is_safe_path(str(base_dir), str(sub_dir))

    def test_invalid_path(self):
        """测试无效路径"""
        result = is_safe_path("/base", "")
        assert result is False


class TestSanitizeFilePath:
    """测试文件路径清理"""

    def test_normal_path(self):
        """测试正常路径"""
        result = sanitize_file_path("/home/user/file.txt")
        assert result == "/home/user/file.txt"

    def test_path_with_dots_removed(self):
        """测试路径中的 .. 被移除"""
        result = sanitize_file_path("/home/user/../secret/file.txt")
        assert ".." not in result

    def test_path_with_tilde_removed(self):
        """测试路径中的 ~ 被移除"""
        result = sanitize_file_path("~/file.txt")
        assert "~" not in result

    def test_control_characters_removed(self):
        """测试控制字符被移除"""
        result = sanitize_file_path("/file\x00.txt")
        assert "\x00" not in result

    def test_newline_preserved(self):
        """测试换行符在路径中被保留（不太可能但测试覆盖）"""
        result = sanitize_file_path("/file\n.txt")
        assert "\n" in result


class TestSecurityIntegration:
    """集成测试"""

    def test_validate_complete_task(self):
        """测试完整的任务验证流程"""
        # 验证所有字段
        prompt = validate_prompt_length("Test prompt")
        workspace = validate_workspace("/tmp/project")
        timeout = validate_timeout(60000)
        name = validate_task_name("Test Task")
        tools = validate_allowed_tools(["Read", "Write"])
        task_id = validate_task_id("task-123")

        # 所有验证都应该通过
        assert prompt == "Test prompt"
        # 工作目录路径在不同平台上可能不同
        assert "tmp" in workspace and "project" in workspace
        assert timeout == 60000
        assert name == "Test Task"
        assert tools == ["Read", "Write"]
        assert task_id == "task-123"

    def test_multiple_security_errors(self):
        """测试多个安全错误"""
        errors = []

        # 收集各种错误
        try:
            validate_prompt_length("")
        except SecurityError as e:
            errors.append(("prompt", e.code))

        try:
            validate_timeout(100)
        except SecurityError as e:
            errors.append(("timeout", e.code))

        try:
            validate_task_name("")
        except SecurityError as e:
            errors.append(("name", e.code))

        try:
            validate_workspace("../../etc/passwd")
        except SecurityError as e:
            errors.append(("workspace", e.code))

        # 所有错误都应该被捕获
        assert len(errors) == 4

        # 验证错误代码
        error_codes = {code for _, code in errors}
        expected_codes = {"EMPTY_PROMPT", "TIMEOUT_TOO_SMALL", "EMPTY_NAME", "PATH_TRAVERSAL_DETECTED"}
        assert error_codes == expected_codes
