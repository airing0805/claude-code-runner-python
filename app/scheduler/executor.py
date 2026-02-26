"""任务执行器

负责执行任务、超时控制、状态转换和重试机制。
"""

import asyncio
import logging
import random
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from app.claude_runner.client import ClaudeCodeClient
from app.scheduler.config import DEFAULT_TIMEOUT, MAX_RETRIES
from app.scheduler.models import Task, TaskStatus
from app.scheduler.storage import TaskStorage

logger = logging.getLogger(__name__)


# 重试延迟配置
BASE_DELAY = 5.0       # 基础延迟（秒）
MAX_DELAY = 60.0       # 最大延迟（秒）
JITTER = 0.1           # 抖动因子


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
        default_factory=lambda: datetime.now().isoformat()
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


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    message: str
    cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    files_changed: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    error: Optional[str] = None


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
    if isinstance(error, asyncio.TimeoutError) or "timeout" in error_str:
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


def should_retry(task: Task, error_type: ErrorType) -> bool:
    """判断是否应该重试"""
    # 检查重试次数
    if task.retries >= MAX_RETRIES:
        return False

    # 检查错误类型
    return error_type in RETRYABLE_ERRORS


def calculate_retry_delay(retry_count: int) -> float:
    """
    计算重试延迟时间（指数退避 + 抖动）

    Args:
        retry_count: 当前重试次数（从 0 开始）

    Returns:
        float: 延迟时间（秒）
    """
    # 指数退避：delay = base * 2^retry_count
    delay = BASE_DELAY * (2 ** retry_count)

    # 限制最大延迟
    delay = min(delay, MAX_DELAY)

    # 添加随机抖动（±10%）
    jitter = delay * JITTER * random.uniform(-1, 1)
    delay = delay + jitter

    return max(0, delay)


# 允许的状态转换映射
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {
        TaskStatus.RUNNING,     # 开始执行
        TaskStatus.CANCELLED,   # 用户取消
    },
    TaskStatus.RUNNING: {
        TaskStatus.COMPLETED,   # 执行成功
        TaskStatus.FAILED,      # 执行失败（不可重试）
        TaskStatus.PENDING,     # 执行失败（可重试）
        TaskStatus.CANCELLED,   # 用户取消
    },
    TaskStatus.FAILED: {
        TaskStatus.PENDING,     # 手动重试
        TaskStatus.CANCELLED,   # 用户取消
    },
    TaskStatus.COMPLETED: set(),  # 终态，不可转换
    TaskStatus.CANCELLED: set(),  # 终态，不可转换
}


def can_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """检查状态转换是否合法"""
    return to_status in VALID_TRANSITIONS.get(from_status, set())


class TaskExecutor:
    """任务执行器

    负责：
    - 调用 ClaudeCodeClient 执行任务
    - 超时控制机制
    - 任务状态跟踪
    - 失败重试机制
    - 错误信息收集
    """

    def __init__(self, storage: TaskStorage) -> None:
        self.storage = storage
        self._current_task: Optional[Task] = None
        self._is_executing: bool = False
        self._error_collector = ErrorCollector()

    def is_executing(self) -> bool:
        """检查是否正在执行任务"""
        return self._is_executing

    def get_current_task(self) -> Optional[Task]:
        """获取当前执行中的任务"""
        return self._current_task

    async def execute(self, task: Task) -> ExecutionResult:
        """
        执行单个任务

        Args:
            task: 待执行的任务

        Returns:
            ExecutionResult: 执行结果
        """
        # 验证任务
        if not self._validate_task(task):
            return ExecutionResult(
                success=False,
                message="任务验证失败",
                error="VALIDATION_ERROR",
            )

        # 设置执行状态
        self._current_task = task
        self._is_executing = True
        self._error_collector.clear()

        # 更新任务状态为运行中
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        self.storage.running.add(task)

        logger.info(f"Task {task.id} started: {task.prompt[:50]}...")

        try:
            # 执行任务（带超时控制）
            result = await asyncio.wait_for(
                self._execute_with_client(task),
                timeout=task.timeout / 1000.0,
            )

            if result.success:
                return self._handle_success(task, result)
            else:
                return self._handle_failure(task, result)

        except asyncio.TimeoutError:
            return self._handle_timeout(task)

        except Exception as e:
            return self._handle_error(task, e)

        finally:
            self._is_executing = False
            self._current_task = None

    def _validate_task(self, task: Task) -> bool:
        """验证任务有效性"""
        if not task.prompt or not task.prompt.strip():
            logger.error(f"Task {task.id} validation failed: empty prompt")
            return False
        if task.timeout < 1000 or task.timeout > 3600000:
            logger.error(f"Task {task.id} validation failed: invalid timeout")
            return False
        return True

    async def _execute_with_client(self, task: Task) -> ExecutionResult:
        """使用 ClaudeCodeClient 执行任务"""
        try:
            client = ClaudeCodeClient(
                working_dir=task.workspace,
                allowed_tools=task.allowed_tools,
                permission_mode="acceptEdits" if task.auto_approve else "default",
            )

            client_result = await client.run(task.prompt)

            # 更新任务信息
            task.files_changed = client_result.files_changed
            task.tools_used = client_result.tools_used
            task.cost_usd = client_result.cost_usd
            task.duration_ms = client_result.duration_ms

            return ExecutionResult(
                success=client_result.success,
                message=client_result.message,
                cost_usd=client_result.cost_usd,
                duration_ms=client_result.duration_ms,
                files_changed=client_result.files_changed,
                tools_used=client_result.tools_used,
                error=None if client_result.success else client_result.message,
            )

        except Exception as e:
            self._error_collector.add(
                e,
                severity=ErrorSeverity.MEDIUM,
                context={"task_id": task.id},
            )
            raise

    def _handle_success(self, task: Task, result: ExecutionResult) -> ExecutionResult:
        """处理执行成功"""
        task.finished_at = datetime.now().isoformat()
        task.status = TaskStatus.COMPLETED
        task.result = {
            "success": True,
            "message": result.message,
        }

        # 从运行中移除，保存到已完成历史
        self.storage.running.remove(task.id)
        self.storage.history.add_completed(task)

        logger.info(
            f"Task {task.id} completed in {task.duration_ms}ms, "
            f"cost: ${task.cost_usd:.4f}" if task.cost_usd is not None
            else f"Task {task.id} completed in {task.duration_ms}ms, cost: $0.0000"
        )
        return result

    def _handle_failure(self, task: Task, result: ExecutionResult) -> ExecutionResult:
        """处理执行失败"""
        error = Exception(result.error or "Unknown error")
        return self._handle_retry(task, error)

    def _handle_timeout(self, task: Task) -> ExecutionResult:
        """处理超时"""
        error = asyncio.TimeoutError(f"Task execution timeout ({task.timeout}ms)")
        self._error_collector.add(
            error,
            severity=ErrorSeverity.MEDIUM,
            context={"timeout_ms": task.timeout},
        )
        return self._handle_retry(task, error)

    def _handle_error(self, task: Task, error: Exception) -> ExecutionResult:
        """处理异常"""
        self._error_collector.add(
            error,
            severity=ErrorSeverity.MEDIUM,
            context={"task_id": task.id},
        )
        return self._handle_retry(task, error)

    def _handle_retry(self, task: Task, error: Exception) -> ExecutionResult:
        """处理重试逻辑"""
        error_type = classify_error(error)

        # 判断是否可重试
        if not should_retry(task, error_type):
            # 不可重试，标记失败
            task.finished_at = datetime.now().isoformat()
            task.status = TaskStatus.FAILED
            task.error = str(error)
            task.result = {
                "success": False,
                "error": str(error),
                "errors": [e.to_dict() for e in self._error_collector.get_all()],
            }

            # 从运行中移除，保存到失败历史
            self.storage.running.remove(task.id)
            self.storage.history.add_failed(task)

            logger.error(f"Task {task.id} failed permanently: {error}")
            return ExecutionResult(
                success=False,
                message="任务执行失败，已达到最大重试次数",
                error=str(error),
            )

        # 可重试
        task.retries += 1
        retry_delay = calculate_retry_delay(task.retries)

        # 重置执行状态
        task.status = TaskStatus.PENDING
        task.started_at = None
        task.finished_at = None
        task.error = f"重试 {task.retries}/{MAX_RETRIES}: {str(error)}"

        # 从运行中移除，重新加入队列
        self.storage.running.remove(task.id)
        self.storage.queue.add(task)

        logger.info(
            f"Task {task.id} scheduled for retry "
            f"({task.retries}/{MAX_RETRIES}) in {retry_delay:.1f}s"
        )

        return ExecutionResult(
            success=False,
            message=f"任务将重试（第 {task.retries} 次）",
            error=str(error),
        )

    def _transition_status(
        self,
        task: Task,
        new_status: TaskStatus,
        error: Optional[str] = None,
    ) -> bool:
        """
        执行状态转换

        Args:
            task: 任务对象
            new_status: 目标状态
            error: 错误信息（可选）

        Returns:
            bool: 转换是否成功
        """
        if not can_transition(task.status, new_status):
            logger.warning(
                f"Invalid status transition: {task.status.value} -> {new_status.value}"
            )
            return False

        old_status = task.status
        task.status = new_status
        task.finished_at = datetime.now().isoformat()

        if error:
            task.error = error

        # 根据状态执行不同的存储操作
        if new_status == TaskStatus.COMPLETED:
            self.storage.running.remove(task.id)
            self.storage.history.add_completed(task)
        elif new_status == TaskStatus.FAILED:
            self.storage.running.remove(task.id)
            self.storage.history.add_failed(task)
        elif new_status == TaskStatus.PENDING:
            # 重试：重新加入队列
            self.storage.running.remove(task.id)
            self.storage.queue.add(task)

        logger.info(f"Task {task.id}: {old_status.value} -> {new_status.value}")
        return True


# 全局执行器实例
_executor: Optional[TaskExecutor] = None


def get_executor() -> TaskExecutor:
    """获取执行器实例"""
    global _executor
    if _executor is None:
        from app.scheduler.storage import get_storage
        _executor = TaskExecutor(get_storage())
    return _executor
