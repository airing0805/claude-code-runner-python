"""安全验证模块验证函数"""

import os
from pathlib import Path
from typing import Optional, List

from .security_constants import (
    VALID_TOOLS, FORBIDDEN_DIRS, PATH_TRAVERSAL_PATTERNS,
    VALID_NAME_PATTERN, MAX_PROMPT_LENGTH, MAX_NAME_LENGTH,
    MIN_TIMEOUT, MAX_TIMEOUT
)
from .security_exceptions import SecurityError


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


def validate_allowed_tools(tools: List[str] | None) -> List[str] | None:
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

    # 最大值不限制
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