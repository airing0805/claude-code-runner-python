"""任务执行器错误处理模块"""

import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any

from .timezone_utils import now_iso


class ErrorType(Enum):
    """错误类型"""
    TRANSIENT = "transient"        # 临时性错误（可重试）
    PERMANENT = "permanent"        # 永久性错误（不可重试）
    TIMEOUT = "timeout"           # 超时错误（可重试）
    USER_CANCEL = "user_cancel"   # 用户取消（不可重试）
    VALIDATION = "validation"     # 验证错误（不可重试）
    RESOURCE = "resource"         # 资源错误（可重试）


class ErrorSeverity(Enum):
    """错误严重级别"""
    LOW = "low"           # 轻微错误，可继续
    MEDIUM = "medium"     # 中等错误，需要重试
    HIGH = "high"         # 严重错误，需要人工介入
    CRITICAL = "critical" # 致命错误，系统问题


# 可重试的错误类型
RETRYABLE_ERRORS: set[ErrorType] = {
    ErrorType.TRANSIENT,
    ErrorType.TIMEOUT,
    ErrorType.RESOURCE,
}


@dataclass
class ExecutionError:
    """执行错误详情"""
    type: str                    # 错误类型
    message: str                 # 错误消息
    severity: ErrorSeverity      # 严重级别
    retryable: bool              # 是否可重试
    timestamp: str = field(
        default_factory=lambda: now_iso()
    )
    stack_trace: Optional[str] = None  # 堆栈信息
    context: dict = field(default_factory=dict)  # 上下文信息

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "message": self.message,
            "severity": self.severity.value,
            "retryable": self.retryable,
            "timestamp": self.timestamp,
            "stack_trace": self.stack_trace,
            "context": self.context,
        }


class ErrorCollector:
    """错误收集器"""

    def __init__(self) -> None:
        self.errors: list[ExecutionError] = []

    def add(
        self,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[dict] = None,
    ) -> ExecutionError:
        """收集错误信息"""
        exec_error = ExecutionError(
            type=type(error).__name__,
            message=str(error),
            severity=severity,
            retryable=should_retry_error(error),
            stack_trace=traceback.format_exc(),
            context=context or {},
        )
        self.errors.append(exec_error)
        return exec_error

    def has_errors(self) -> bool:
        """检查是否有错误"""
        return len(self.errors) > 0

    def get_latest(self) -> Optional[ExecutionError]:
        """获取最新的错误"""
        return self.errors[-1] if self.errors else None

    def get_all(self) -> list[ExecutionError]:
        """获取所有错误"""
        return self.errors.copy()

    def clear(self) -> None:
        """清空错误列表"""
        self.errors.clear()


def classify_error(error: Exception) -> ErrorType:
    """分类错误类型"""
    error_str = str(error).lower()

    # 超时错误
    if isinstance(error, TimeoutError) or "timeout" in error_str:
        return ErrorType.TIMEOUT

    # 资源错误（网络、API 限流等）
    resource_keywords = ["rate limit", "connection", "network", "unavailable"]
    if any(kw in error_str for kw in resource_keywords):
        return ErrorType.RESOURCE

    # 验证错误
    validation_keywords = ["invalid", "validation", "not found", "permission"]
    if any(kw in error_str for kw in validation_keywords):
        return ErrorType.VALIDATION

    # 默认为临时性错误
    return ErrorType.TRANSIENT


def should_retry_error(error: Exception) -> bool:
    """判断错误是否可以重试"""
    error_type = classify_error(error)
    return error_type in RETRYABLE_ERRORS


def should_retry(task, error_type: ErrorType) -> bool:
    """判断是否应该重试"""
    from .config import MAX_RETRIES
    
    # 检查重试次数
    if task.retries >= MAX_RETRIES:
        return False

    # 检查错误类型
    return error_type in RETRYABLE_ERRORS