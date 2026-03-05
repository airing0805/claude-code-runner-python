"""安全验证模块

提供工作目录验证、工具白名单验证等安全功能。
"""

import os
import re
from pathlib import Path
from typing import Optional

# ============= 常量定义 =============

# 有效的工具名称白名单
# 参考 Claude Code 官方文档的工具列表
VALID_TOOLS: set[str] = {
    # 文件操作
    "Read",        # 读取文件内容
    "Write",       # 写入文件内容
    "Edit",        # 编辑文件内容
    "Glob",        # 文件路径匹配
    "Grep",        # 文本搜索
    "Bash",        # 执行 shell 命令

    # 任务管理
    "Task",        # 创建子任务
    "TodoWrite",   # 写入 TODO 列表

    # 网络操作
    "WebFetch",    # 获取网页内容
    "WebSearch",   # 网络搜索

    # 其他
    "NotebookEdit",  # Jupyter notebook 编辑
    "NotebookRead",  # Jupyter notebook 读取
    "Mcp",          # MCP 工具调用

    # 代理工具 (MCP 扩展)
    "mcp__filesystem__read_file",
    "mcp__filesystem__write_file",
    "mcp__filesystem__read_text_file",
    "mcp__filesystem__write_text_file",
    "mcp__filesystem__list_directory",
    "mcp__filesystem__create_directory",
    "mcp__filesystem__move_file",
    "mcp__filesystem__search_files",
    "mcp__filesystem__get_file_info",
    "mcp__filesystem__directory_tree",
    "mcp__filesystem__edit_file",
    "mcp__filesystem__read_multiple_files",
    "mcp__filesystem__read_media_file",
    "mcp__chrome-devtools__take_snapshot",
    "mcp__chrome-devtools__navigate_page",
    "mcp__chrome-devtools__click",
    "mcp__chrome-devtools__fill",
    "mcp__chrome-devtools__fill_form",
    "mcp__chrome-devtools__type_text",
    "mcp__chrome-devtools__press_key",
    "mcp__chrome-devtools__take_screenshot",
    "mcp__chrome-devtools__hover",
    "mcp__chrome-devtools__evaluate_script",
    "mcp__chrome-devtools__wait_for",
    "mcp__chrome-devtools__list_pages",
    "mcp__chrome-devtools__select_page",
    "mcp__chrome-devtools__new_page",
    "mcp__chrome-devtools__close_page",
    "mcp__chrome-devtools__list_network_requests",
    "mcp__chrome-devtools__get_network_request",
    "mcp__chrome-devtools__list_console_messages",
    "mcp__chrome-devtools__get_console_message",
    "mcp__playwright__browser_navigate",
    "mcp__playwright__browser_snapshot",
    "mcp__playwright__browser_click",
    "mcp__playwright__browser_type",
    "mcp__playwright__browser_take_screenshot",
    "mcp__playwright__browser_hover",
    "mcp__playwright__browser_evaluate",
    "mcp__playwright__browser_fill_form",
    "mcp__playwright__browser_select_option",
    "mcp__playwright__browser_press_key",
    "mcp__playwright__browser_wait_for",
    "mcp__playwright__browser_tabs",
    "mcp__playwright__browser_close",
    "mcp__playwright__browser_file_upload",
    "mcp__playwright__browser_drag",
    "mcp__playwright__browser_handle_dialog",
    "mcp__playwright__browser_console_messages",
    "mcp__playwright__browser_network_requests",
    "mcp__playwright__browser_resize",
    "mcp__playwright__browser_run_code",
    "mcp__github__create_issue",
    "mcp__github__get_issue",
    "mcp__github__list_issues",
    "mcp__github__update_issue",
    "mcp__github__add_issue_comment",
    "mcp__github__create_pull_request",
    "mcp__github__get_pull_request",
    "mcp__github__list_pull_requests",
    "mcp__github__get_pull_request_files",
    "mcp__github__get_pull_request_status",
    "mcp__github__get_pull_request_reviews",
    "mcp__github__get_pull_request_comments",
    "mcp__github__merge_pull_request",
    "mcp__github__create_pull_request_review",
    "mcp__github__update_pull_request_branch",
    "mcp__github__create_branch",
    "mcp__github__get_file_contents",
    "mcp__github__create_or_update_file",
    "mcp__github__push_files",
    "mcp__github__search_code",
    "mcp__github__search_issues",
    "mcp__github__search_repositories",
    "mcp__github__search_users",
    "mcp__github__list_commits",
    "mcp__github__fork_repository",
    "mcp__github__create_repository",
    "mcp__memory__create_entities",
    "mcp__memory__create_relations",
    "mcp__memory__add_observations",
    "mcp__memory__delete_entities",
    "mcp__memory__delete_observations",
    "mcp__memory__delete_relations",
    "mcp__memory__read_graph",
    "mcp__memory__search_nodes",
    "mcp__memory__open_nodes",
    "mcp__sequential-thinking__sequentialthinking",
    "mcp__web_reader__webReader",
    "mcp__4_5v_mcp__analyze_image",
}

# 禁止访问的系统目录
FORBIDDEN_DIRS: list[str] = [
    # Unix/Linux
    "/etc",
    "/root",
    "/var/log",
    "/usr/bin",
    "/bin",
    "/sbin",
    "/boot",
    "/dev",
    "/proc",
    "/sys",

    # Windows
    "C:\\Windows",
    "C:\\System32",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
]

# 路径遍历危险字符模式
PATH_TRAVERSAL_PATTERNS = [
    "..",           # 父目录引用
    "~",            # 用户主目录
    "\\\\",         # UNC 路径 (Windows)
]

# 任务名称验证模式
VALID_NAME_PATTERN = re.compile(r'^[\w\u4e00-\u9fff\- ]+$')

# 验证限制
MAX_PROMPT_LENGTH = 10000
MAX_NAME_LENGTH = 100
MIN_TIMEOUT = 1000      # 1 秒
MAX_TIMEOUT = 3600000   # 1 小时

# ============= 异常类 =============

class SecurityError(Exception):
    """安全验证错误"""

    def __init__(self, message: str, code: str = "SECURITY_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# ============= 验证函数 =============

def validate_workspace(workspace: str | None) -> str:
    """
    验证工作目录安全性

    Args:
        workspace: 工作目录路径

    Returns:
        str: 验证后的绝对路径

    Raises:
        SecurityError: 工作目录不安全
    """
    # 空值或空字符串使用默认值
    if workspace is None:
        return "."

    workspace = workspace.strip()
    if not workspace:
        return "."

    # 处理默认工作空间标识符
    default_indicators = ['默认工作空间', '默认', '.']
    if workspace in default_indicators:
        actual_workspace = os.getenv("WORKING_DIR", ".").strip()
        if not actual_workspace:
            return "."
        workspace = actual_workspace

    # 检查路径遍历攻击
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern in workspace:
            raise SecurityError(
                f"工作目录包含非法路径模式: {pattern}",
                code="PATH_TRAVERSAL_DETECTED"
            )

    # 路径规范化
    try:
        abs_workspace = Path(workspace).resolve()
    except Exception as e:
        raise SecurityError(
            f"工作目录格式无效: {e}",
            code="INVALID_PATH_FORMAT"
        )

    # 检查系统敏感目录
    abs_workspace_str = str(abs_workspace).lower()
    for forbidden in FORBIDDEN_DIRS:
        forbidden_lower = forbidden.lower()
        # Windows 路径分隔符统一处理
        abs_normalized = abs_workspace_str.replace("/", "\\")
        forbidden_normalized = forbidden_lower.replace("/", "\\")
        if abs_normalized.startswith(forbidden_normalized):
            raise SecurityError(
                f"禁止访问系统目录: {forbidden}",
                code="FORBIDDEN_DIRECTORY"
            )

    # 白名单检查（如果配置了环境变量）
    allow_any = os.getenv("SCHEDULER_ALLOW_ANY_WORKSPACE", "false").lower() == "true"
    if not allow_any:
        base_dir = os.getenv("WORKING_DIR") or os.getenv("SCHEDULER_ALLOWED_WORKSPACE")
        if base_dir:
            try:
                base_path = Path(base_dir).resolve()
                # 检查是否在允许的目录内
                abs_workspace.relative_to(base_path)
            except ValueError:
                raise SecurityError(
                    f"工作目录必须在允许范围内: {base_dir}",
                    code="WORKSPACE_NOT_IN_WHITELIST"
                )

    return str(abs_workspace)


def validate_allowed_tools(tools: list[str] | None) -> list[str] | None:
    """
    验证工具列表

    Args:
        tools: 工具名称列表

    Returns:
        list[str] | None: 验证后的工具列表

    Raises:
        SecurityError: 工具名称无效
    """
    if tools is None:
        return None

    if not tools:
        return []

    for tool in tools:
        # 检查是否在白名单中
        if tool in VALID_TOOLS:
            continue

        # 支持 MCP 工具前缀匹配
        if tool.startswith("mcp__"):
            # MCP 工具允许通过，格式为 mcp__server__tool
            parts = tool.split("__")
            if len(parts) >= 3:
                continue

        # 支持 Task 工具变体 (Task-xxx)
        if tool.startswith("Task-"):
            continue

        raise SecurityError(
            f"无效的工具名称: {tool}",
            code="INVALID_TOOL_NAME"
        )

    return tools


def validate_prompt_length(prompt: str, max_length: int = MAX_PROMPT_LENGTH) -> str:
    """
    验证提示词长度

    Args:
        prompt: 提示词内容
        max_length: 最大长度

    Returns:
        str: 验证后的提示词

    Raises:
        SecurityError: 提示词过长或为空
    """
    if not prompt or not prompt.strip():
        raise SecurityError(
            "提示词不能为空",
            code="EMPTY_PROMPT"
        )

    if len(prompt) > max_length:
        raise SecurityError(
            f"提示词长度超出限制 ({len(prompt)} > {max_length})",
            code="PROMPT_TOO_LONG"
        )

    return prompt.strip()


def validate_timeout(timeout: int) -> int:
    """
    验证超时时间

    Args:
        timeout: 超时时间（毫秒）

    Returns:
        int: 验证后的超时时间

    Raises:
        SecurityError: 超时时间无效
    """
    if timeout < MIN_TIMEOUT:
        raise SecurityError(
            f"超时时间不能小于 {MIN_TIMEOUT} 毫秒",
            code="TIMEOUT_TOO_SMALL"
        )

    if timeout > MAX_TIMEOUT:
        raise SecurityError(
            f"超时时间不能超过 {MAX_TIMEOUT} 毫秒",
            code="TIMEOUT_TOO_LARGE"
        )

    return timeout


def validate_task_name(name: str, max_length: int = MAX_NAME_LENGTH) -> str:
    """
    验证任务名称

    Args:
        name: 任务名称
        max_length: 最大长度

    Returns:
        str: 验证后的名称

    Raises:
        SecurityError: 名称无效
    """
    if not name or not name.strip():
        raise SecurityError(
            "任务名称不能为空",
            code="EMPTY_NAME"
        )

    name = name.strip()

    if len(name) > max_length:
        raise SecurityError(
            f"任务名称长度超出限制 ({len(name)} > {max_length})",
            code="NAME_TOO_LONG"
        )

    # 检查字符模式
    if not VALID_NAME_PATTERN.match(name):
        raise SecurityError(
            "任务名称包含非法字符，仅允许字母、数字、中文、下划线、连字符和空格",
            code="INVALID_NAME_CHARACTER"
        )

    return name


def sanitize_input(text: str) -> str:
    """
    清理输入文本，移除潜在的危险字符

    Args:
        text: 输入文本

    Returns:
        str: 清理后的文本
    """
    # 移除控制字符（保留换行符、制表符）
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

    # 移除潜在的脚本注入
    text = text.replace("<script", "&lt;script", 1)
    text = text.replace("</script>", "&lt;/script&gt;")

    return text


def validate_task_id(task_id: str) -> str:
    """
    验证任务 ID

    Args:
        task_id: 任务 ID

    Returns:
        str: 验证后的任务 ID

    Raises:
        SecurityError: 任务 ID 无效
    """
    if not task_id or not task_id.strip():
        raise SecurityError(
            "任务 ID 不能为空",
            code="EMPTY_TASK_ID"
        )

    return task_id.strip()


def validate_cron_expression(cron: str) -> str:
    """
    验证 Cron 表达式格式

    Args:
        cron: Cron 表达式

    Returns:
        str: 验证后的 Cron 表达式

    Raises:
        SecurityError: Cron 表达式无效
    """
    if not cron or not cron.strip():
        raise SecurityError(
            "Cron 表达式不能为空",
            code="EMPTY_CRON"
        )

    cron = cron.strip()

    # 检查长度限制
    if len(cron) > 100:
        raise SecurityError(
            "Cron 表达式过长",
            code="CRON_TOO_LONG"
        )

    # 检查特殊字符（防止命令注入）
    dangerous_chars = ["$", ";", "&", "|", ">", "<", "`"]
    for char in dangerous_chars:
        if char in cron:
            raise SecurityError(
                f"Cron 表达式包含非法字符: {char}",
                code="CRON_INVALID_CHARACTER"
            )

    return cron


def validate_auto_approve(auto_approve: bool) -> bool:
    """
    验证自动批准标志

    Args:
        auto_approve: 是否自动批准

    Returns:
        bool: 验证后的值
    """
    return bool(auto_approve)


# ============= 安全检查函数 =============

def is_safe_path(base_dir: str, user_path: str) -> bool:
    """
    检查用户路径是否在基础目录内（防止目录遍历）

    Args:
        base_dir: 基础目录
        user_path: 用户提供的路径

    Returns:
        bool: 路径是否安全
    """
    try:
        base = Path(base_dir).resolve()
        target = Path(user_path).resolve()
        target.relative_to(base)
        return True
    except ValueError:
        return False
    except Exception:
        return False


def sanitize_file_path(file_path: str) -> str:
    """
    清理文件路径，移除危险字符

    Args:
        file_path: 文件路径

    Returns:
        str: 清理后的路径
    """
    # 移除控制字符
    cleaned = "".join(char for char in file_path if ord(char) >= 32 or char in "\n\r\t")

    # 移除路径遍历模式
    cleaned = cleaned.replace("..", "")
    cleaned = cleaned.replace("~", "")

    return cleaned


# ============= 导出列表 =============

__all__ = [
    "SecurityError",
    "VALID_TOOLS",
    "FORBIDDEN_DIRS",
    "PATH_TRAVERSAL_PATTERNS",
    "MAX_PROMPT_LENGTH",
    "MAX_NAME_LENGTH",
    "MIN_TIMEOUT",
    "MAX_TIMEOUT",
    "validate_workspace",
    "validate_allowed_tools",
    "validate_prompt_length",
    "validate_timeout",
    "validate_task_name",
    "sanitize_input",
    "validate_task_id",
    "validate_cron_expression",
    "validate_auto_approve",
    "is_safe_path",
    "sanitize_file_path",
]
