"""任务执行器核心模块"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .config import DEFAULT_TIMEOUT
from .models import Task, TaskStatus
from .storage import TaskStorage
from .security import (
    validate_workspace,
    validate_allowed_tools,
    validate_prompt_length,
    validate_timeout,
    SecurityError,
)
from .timezone_utils import now_iso, format_datetime
from .executor_errors import ErrorCollector, classify_error
from .executor_retry import handle_retry


logger = logging.getLogger(__name__)


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
    - 任务执行日志记录
    """

    def __init__(self, storage: TaskStorage) -> None:
        self.storage = storage
        self._current_task: Optional[Task] = None
        self._is_executing: bool = False
        self._error_collector = ErrorCollector()

    def _log(
        self,
        task_id: str,
        level: str,
        message: str,
        context: dict | None = None,
    ) -> None:
        """记录任务执行日志

        Args:
            task_id: 任务 ID
            level: 日志级别 (INFO, WARNING, ERROR)
            message: 日志消息
            context: 上下文信息
        """
        log_entry = {
            "id": str(uuid.uuid4()),
            "task_id": task_id,
            "timestamp": now_iso(),
            "level": level,
            "message": message,
            "context": context or {},
        }
        self.storage.logs.append(log_entry)

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
            self._log(
                task.id,
                "ERROR",
                "任务验证失败",
                {"prompt_preview": task.prompt[:50]},
            )
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
        task.started_at = now_iso()
        self.storage.running.add(task)

        logger.info(f"Task {task.id} started: {task.prompt[:50]}...")

        # 记录任务开始日志
        self._log(
            task.id,
            "INFO",
            "任务开始执行",
            {
                "prompt": task.prompt,
                "workspace": task.workspace,
                "timeout": task.timeout,
                "source": task.source.value,
            },
        )

        try:
            # 执行任务（带超时控制）
            result = await asyncio.wait_for(
                self._execute_with_client(task),
                timeout=task.timeout / 1000.0,  # 转换为秒
            )

            if result.success:
                return await self._handle_success(task, result)
            else:
                return await self._handle_failure(task, result)

        except asyncio.TimeoutError:
            return await self._handle_timeout(task)

        except Exception as e:
            return await self._handle_error(task, e)

        finally:
            self._is_executing = False
            self._current_task = None

    def _validate_task(self, task: Task) -> bool:
        """验证任务有效性

        检查:
        - 提示词非空且长度在限制内
        - 超时时间在有效范围
        - 工作目录安全
        - 工具白名单验证
        """
        try:
            # 1. 验证提示词
            validate_prompt_length(task.prompt)

            # 2. 验证超时时间
            validate_timeout(task.timeout)

            # 3. 验证工作目录
            validate_workspace(task.workspace)

            # 4. 验证工具白名单
            validate_allowed_tools(task.allowed_tools)

            return True

        except SecurityError as e:
            logger.error(
                f"Task {task.id} validation failed: {e.message} (code: {e.code})"
            )
            return False
        except Exception as e:
            logger.error(f"Task {task.id} validation failed: {e}")
            return False

    async def _execute_with_client(self, task: Task) -> ExecutionResult:
        """使用 ClaudeCodeClient 执行任务"""
        try:
            from app.claude_runner.client import ClaudeCodeClient
            
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

    async def _handle_success(self, task: Task, result: ExecutionResult) -> ExecutionResult:
        """处理执行成功"""
        task.finished_at = now_iso()
        task.status = TaskStatus.COMPLETED
        task.result = {
            "success": True,
            "message": result.message,
        }

        # 从运行中移除，保存到已完成历史
        self.storage.running.remove(task.id)
        self.storage.history.add_completed(task)

        # 记录成功日志
        self._log(
            task.id,
            "INFO",
            "任务执行成功",
            {
                "duration_ms": task.duration_ms,
                "cost_usd": task.cost_usd,
                "files_changed": task.files_changed,
                "tools_used": task.tools_used,
                "message": result.message,
            },
        )

        logger.info(
            f"Task {task.id} completed in {task.duration_ms}ms, "
            f"cost: ${task.cost_usd:.4f}" if task.cost_usd is not None
            else f"Task {task.id} completed in {task.duration_ms}ms, cost: $0.0000"
        )
        return result

    async def _handle_failure(self, task: Task, result: ExecutionResult) -> ExecutionResult:
        """处理执行失败"""
        error = Exception(result.error or "Unknown error")
        return await self._handle_retry_logic(task, error)

    async def _handle_timeout(self, task: Task) -> ExecutionResult:
        """处理超时"""
        error = asyncio.TimeoutError(f"Task execution timeout ({task.timeout}ms)")
        self._error_collector.add(
            error,
            severity=ErrorSeverity.MEDIUM,
            context={"timeout_ms": task.timeout},
        )
        # 记录超时日志
        self._log(
            task.id,
            "ERROR",
            "任务执行超时",
            {"timeout_ms": task.timeout},
        )
        return await self._handle_retry_logic(task, error)

    async def _handle_error(self, task: Task, error: Exception) -> ExecutionResult:
        """处理异常"""
        self._error_collector.add(
            error,
            severity=ErrorSeverity.MEDIUM,
            context={"task_id": task.id},
        )
        return await self._handle_retry_logic(task, error)

    async def _handle_retry_logic(self, task: Task, error: Exception) -> ExecutionResult:
        """处理重试逻辑的统一入口"""
        from .executor_retry import handle_retry
        
        result = await handle_retry(
            task, error, self.storage, self._error_collector, logger
        )
        
        return ExecutionResult(
            success=result["success"],
            message=result["message"],
            error=result["error"],
        )

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否取消成功
        """
        # 1. 检查队列中的任务
        task = self.storage.queue.get(task_id)
        if task:
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.finished_at = now_iso()
                task.error = "用户取消"
                self.storage.queue.remove(task_id)
                self.storage.cancelled.add(task)
                logger.info(f"Task {task_id} cancelled from queue")
                return True

        # 2. 检查运行中的任务
        task = self.storage.running.get(task_id)
        if task:
            # 运行中的任务标记为取消，执行器会在下次检查时处理
            task.status = TaskStatus.CANCELLED
            task.error = "用户取消"
            self.storage.running.update(task)
            logger.info(f"Task {task_id} marked for cancellation")
            return True

        logger.warning(f"Task {task_id} not found for cancellation")
        return False