"""任务执行器单元测试"""

import asyncio
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.scheduler.executor import (
    TaskExecutor,
    ErrorCollector,
    ExecutionError,
    ExecutionResult,
    ErrorType,
    ErrorSeverity,
    classify_error,
    should_retry_error,
    should_retry,
    calculate_retry_delay,
    can_transition,
    VALID_TRANSITIONS,
    BASE_DELAY,
    MAX_DELAY,
    JITTER,
    RETRYABLE_ERRORS,
)
from app.scheduler.models import Task, TaskStatus
from app.scheduler.storage import TaskStorage
from app.scheduler.config import MAX_RETRIES


@pytest.fixture
def mock_storage():
    """创建模拟存储层"""
    storage = MagicMock(spec=TaskStorage)
    storage.queue = MagicMock()
    storage.running = MagicMock()
    storage.history = MagicMock()
    storage.queue.add = MagicMock()
    storage.running.add = MagicMock()
    storage.running.remove = MagicMock()
    storage.history.add_completed = MagicMock()
    storage.history.add_failed = MagicMock()
    return storage


@pytest.fixture
def sample_task():
    """创建示例任务"""
    return Task(
        id=str(uuid.uuid4()),
        prompt="测试任务描述",
        workspace="/test/workspace",
        timeout=600000,  # 10 分钟
    )


class TestErrorCollector:
    """错误收集器测试"""

    def test_error_collector_creation(self):
        """测试错误收集器创建"""
        collector = ErrorCollector()
        assert not collector.has_errors()
        assert collector.get_latest() is None
        assert collector.get_all() == []

    def test_error_collector_add_error(self):
        """测试添加错误"""
        collector = ErrorCollector()
        error = ValueError("测试错误")

        exec_error = collector.add(
            error,
            severity=ErrorSeverity.MEDIUM,
            context={"task_id": "test-123"},
        )

        assert collector.has_errors()
        assert collector.get_latest() == exec_error
        assert exec_error.type == "ValueError"
        assert exec_error.message == "测试错误"
        assert exec_error.severity == ErrorSeverity.MEDIUM

    def test_error_collector_multiple_errors(self):
        """测试收集多个错误"""
        collector = ErrorCollector()

        collector.add(ValueError("错误1"), severity=ErrorSeverity.LOW)
        collector.add(RuntimeError("错误2"), severity=ErrorSeverity.HIGH)

        errors = collector.get_all()
        assert len(errors) == 2
        assert errors[0].message == "错误1"
        assert errors[1].message == "错误2"

    def test_error_collector_clear(self):
        """测试清空错误列表"""
        collector = ErrorCollector()
        collector.add(ValueError("错误"))
        assert collector.has_errors()

        collector.clear()

        assert not collector.has_errors()

    def test_execution_error_to_dict(self):
        """测试执行错误转字典"""
        error = ExecutionError(
            type="ValueError",
            message="测试错误",
            severity=ErrorSeverity.HIGH,
            retryable=True,
            stack_trace="line 1\nline 2",
            context={"key": "value"},
        )

        result = error.to_dict()

        assert result["type"] == "ValueError"
        assert result["message"] == "测试错误"
        assert result["severity"] == "high"
        assert result["retryable"] is True
        assert result["stack_trace"] == "line 1\nline 2"
        assert result["context"] == {"key": "value"}


class TestExecutionResult:
    """执行结果测试"""

    def test_execution_result_success(self):
        """测试成功的执行结果"""
        result = ExecutionResult(
            success=True,
            message="执行成功",
            cost_usd=0.05,
            duration_ms=5000,
            files_changed=["/test/a.py"],
            tools_used=["Read", "Edit"],
        )

        assert result.success is True
        assert result.message == "执行成功"
        assert result.cost_usd == 0.05
        assert result.duration_ms == 5000
        assert result.files_changed == ["/test/a.py"]
        assert result.error is None

    def test_execution_result_failure(self):
        """测试失败的执行结果"""
        result = ExecutionResult(
            success=False,
            message="执行失败",
            error="超时错误",
        )

        assert result.success is False
        assert result.error == "超时错误"


class TestClassifyError:
    """错误分类测试"""

    def test_classify_timeout_error(self):
        """测试超时错误分类"""
        error = asyncio.TimeoutError()
        assert classify_error(error) == ErrorType.TIMEOUT

    def test_classify_timeout_in_message(self):
        """测试消息中包含 timeout 的错误"""
        error = RuntimeError("Connection timeout")
        assert classify_error(error) == ErrorType.TIMEOUT

    def test_classify_resource_error_rate_limit(self):
        """测试资源错误 - 限流"""
        error = RuntimeError("Rate limit exceeded")
        assert classify_error(error) == ErrorType.RESOURCE

    def test_classify_resource_error_connection(self):
        """测试资源错误 - 连接"""
        error = RuntimeError("Connection refused")
        assert classify_error(error) == ErrorType.RESOURCE

    def test_classify_resource_error_network(self):
        """测试资源错误 - 网络"""
        error = RuntimeError("Network unavailable")
        assert classify_error(error) == ErrorType.RESOURCE

    def test_classify_validation_error_invalid(self):
        """测试验证错误 - invalid"""
        error = ValueError("Invalid parameter")
        assert classify_error(error) == ErrorType.VALIDATION

    def test_classify_validation_error_permission(self):
        """测试验证错误 - permission"""
        error = PermissionError("Permission denied")
        assert classify_error(error) == ErrorType.VALIDATION

    def test_classify_transient_error(self):
        """测试临时性错误（默认）"""
        error = RuntimeError("Unknown error")
        assert classify_error(error) == ErrorType.TRANSIENT


class TestShouldRetryError:
    """重试判断测试"""

    def test_should_retry_timeout(self):
        """测试超时错误可重试"""
        error = asyncio.TimeoutError()
        assert should_retry_error(error) is True

    def test_should_retry_resource(self):
        """测试资源错误可重试"""
        error = RuntimeError("Rate limit exceeded")
        assert should_retry_error(error) is True

    def test_should_retry_transient(self):
        """测试临时性错误可重试"""
        error = RuntimeError("Temporary failure")
        assert should_retry_error(error) is True

    def test_should_not_retry_validation(self):
        """测试验证错误不可重试"""
        error = ValueError("Invalid input")
        assert should_retry_error(error) is False

    def test_should_not_retry_permission(self):
        """测试权限错误不可重试"""
        error = PermissionError("Permission denied")
        assert should_retry_error(error) is False


class TestShouldRetry:
    """任务重试判断测试"""

    def test_should_retry_within_limit(self):
        """测试重试次数内可重试"""
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试",
            retries=0,
        )
        assert should_retry(task, ErrorType.TIMEOUT) is True

    def test_should_retry_at_limit(self):
        """测试达到重试次数上限"""
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试",
            retries=MAX_RETRIES,
        )
        assert should_retry(task, ErrorType.TIMEOUT) is False

    def test_should_not_retry_validation_error(self):
        """测试验证错误不可重试"""
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试",
            retries=0,
        )
        assert should_retry(task, ErrorType.VALIDATION) is False

    def test_should_not_retry_permanent_error(self):
        """测试永久性错误不可重试"""
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试",
            retries=0,
        )
        assert should_retry(task, ErrorType.PERMANENT) is False


class TestCalculateRetryDelay:
    """重试延迟计算测试"""

    def test_retry_delay_first_retry(self):
        """测试第一次重试延迟"""
        # delay = 5 * 2^0 = 5 ± jitter
        delay = calculate_retry_delay(0)
        expected = BASE_DELAY * (2**0)
        # 考虑抖动 ±10%
        assert expected * (1 - JITTER) <= delay <= expected * (1 + JITTER)

    def test_retry_delay_second_retry(self):
        """测试第二次重试延迟"""
        # delay = 5 * 2^1 = 10 ± jitter
        delay = calculate_retry_delay(1)
        expected = BASE_DELAY * (2**1)
        assert expected * (1 - JITTER) <= delay <= expected * (1 + JITTER)

    def test_retry_delay_third_retry(self):
        """测试第三次重试延迟"""
        # delay = 5 * 2^2 = 20 ± jitter
        delay = calculate_retry_delay(2)
        expected = BASE_DELAY * (2**2)
        assert expected * (1 - JITTER) <= delay <= expected * (1 + JITTER)

    def test_retry_delay_max_cap(self):
        """测试延迟上限"""
        # 高重试次数应该被限制在 MAX_DELAY
        delay = calculate_retry_delay(100)
        assert delay <= MAX_DELAY * (1 + JITTER)

    def test_retry_delay_non_negative(self):
        """测试延迟非负"""
        delay = calculate_retry_delay(0)
        assert delay >= 0


class TestCanTransition:
    """状态转换测试"""

    def test_pending_to_running(self):
        """测试 PENDING -> RUNNING"""
        assert can_transition(TaskStatus.PENDING, TaskStatus.RUNNING) is True

    def test_pending_to_cancelled(self):
        """测试 PENDING -> CANCELLED"""
        assert can_transition(TaskStatus.PENDING, TaskStatus.CANCELLED) is True

    def test_running_to_completed(self):
        """测试 RUNNING -> COMPLETED"""
        assert can_transition(TaskStatus.RUNNING, TaskStatus.COMPLETED) is True

    def test_running_to_failed(self):
        """测试 RUNNING -> FAILED"""
        assert can_transition(TaskStatus.RUNNING, TaskStatus.FAILED) is True

    def test_running_to_pending_retry(self):
        """测试 RUNNING -> PENDING（重试）"""
        assert can_transition(TaskStatus.RUNNING, TaskStatus.PENDING) is True

    def test_failed_to_pending_retry(self):
        """测试 FAILED -> PENDING（手动重试）"""
        assert can_transition(TaskStatus.FAILED, TaskStatus.PENDING) is True

    def test_completed_no_transition(self):
        """测试 COMPLETED 是终态"""
        assert can_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING) is False
        assert can_transition(TaskStatus.COMPLETED, TaskStatus.FAILED) is False

    def test_cancelled_no_transition(self):
        """测试 CANCELLED 是终态"""
        assert can_transition(TaskStatus.CANCELLED, TaskStatus.RUNNING) is False
        assert can_transition(TaskStatus.CANCELLED, TaskStatus.PENDING) is False

    def test_invalid_transition(self):
        """测试无效状态转换"""
        assert can_transition(TaskStatus.PENDING, TaskStatus.COMPLETED) is False
        assert can_transition(TaskStatus.RUNNING, TaskStatus.RUNNING) is False


class TestTaskExecutor:
    """任务执行器测试"""

    def test_executor_creation(self, mock_storage):
        """测试执行器创建"""
        executor = TaskExecutor(mock_storage)

        assert executor.storage == mock_storage
        assert executor.is_executing() is False
        assert executor.get_current_task() is None

    def test_validate_task_empty_prompt(self, mock_storage):
        """测试空任务描述验证"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="",
        )

        result = executor._validate_task(task)

        assert result is False

    def test_validate_task_whitespace_prompt(self, mock_storage):
        """测试空白任务描述验证"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="   ",
        )

        result = executor._validate_task(task)

        assert result is False

    def test_validate_task_timeout_too_small(self, mock_storage):
        """测试超时时间过小"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试任务",
            timeout=500,  # 小于 1000ms
        )

        result = executor._validate_task(task)

        assert result is False

    def test_validate_task_timeout_too_large(self, mock_storage):
        """测试超时时间过大"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试任务",
            timeout=4000000,  # 大于 3600000ms
        )

        result = executor._validate_task(task)

        assert result is False

    def test_validate_task_valid(self, mock_storage, sample_task):
        """测试有效任务验证"""
        executor = TaskExecutor(mock_storage)

        result = executor._validate_task(sample_task)

        assert result is True

    @pytest.mark.asyncio
    async def test_execute_empty_prompt_fails(self, mock_storage):
        """测试空描述任务执行失败"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="",
        )

        result = await executor.execute(task)

        assert result.success is False
        assert result.error == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_execute_timeout_too_small_fails(self, mock_storage):
        """测试超时过小任务执行失败"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试任务",
            timeout=500,
        )

        result = await executor.execute(task)

        assert result.success is False
        assert result.error == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_storage, sample_task):
        """测试成功执行任务"""
        executor = TaskExecutor(mock_storage)

        with patch.object(
            executor, "_execute_with_client", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = ExecutionResult(
                success=True,
                message="执行成功",
                cost_usd=0.05,
                duration_ms=5000,
                files_changed=["/test/a.py"],
                tools_used=["Read", "Edit"],
            )

            # 预设任务的 cost_usd 和 duration_ms 避免 None 格式化问题
            sample_task.cost_usd = 0.05
            sample_task.duration_ms = 5000

            result = await executor.execute(sample_task)

            assert result.success is True
            assert result.message == "执行成功"
            # 验证状态更新
            assert sample_task.status == TaskStatus.COMPLETED
            # 验证存储操作
            mock_storage.running.add.assert_called_once()
            mock_storage.running.remove.assert_called_once()
            mock_storage.history.add_completed.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_timeout(self, mock_storage, sample_task):
        """测试任务执行超时"""
        executor = TaskExecutor(mock_storage)

        # 设置合法的最小超时时间（1秒），但执行时间更长
        sample_task.timeout = 1000  # 1000ms = 1秒（最小合法超时）

        async def slow_execute(task):
            await asyncio.sleep(2)  # 2秒，超过1秒超时
            return ExecutionResult(success=True, message="完成")

        with patch.object(
            executor, "_execute_with_client", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = slow_execute

            result = await executor.execute(sample_task)

            assert result.success is False
            # 超时错误会触发重试
            assert sample_task.retries >= 1 or sample_task.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_retry_on_transient_error(self, mock_storage, sample_task):
        """测试临时性错误触发重试"""
        executor = TaskExecutor(mock_storage)
        sample_task.retries = 0  # 初始重试次数

        with patch.object(
            executor, "_execute_with_client", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = RuntimeError("Temporary failure")

            result = await executor.execute(sample_task)

            # 应该触发重试
            assert result.success is False
            assert sample_task.retries == 1
            assert sample_task.status == TaskStatus.PENDING
            # 验证重新加入队列
            mock_storage.queue.add.assert_called()

    @pytest.mark.asyncio
    async def test_execute_max_retries_exceeded(self, mock_storage):
        """测试达到最大重试次数"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试任务",
            timeout=600000,
            retries=MAX_RETRIES,  # 已达到最大重试次数
        )

        with patch.object(
            executor, "_execute_with_client", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = RuntimeError("Temporary failure")

            result = await executor.execute(task)

            # 不应再重试
            assert result.success is False
            assert task.status == TaskStatus.FAILED
            mock_storage.history.add_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_validation_error_no_retry(self, mock_storage, sample_task):
        """测试验证错误不重试"""
        executor = TaskExecutor(mock_storage)

        with patch.object(
            executor, "_execute_with_client", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = ValueError("Invalid parameter")

            result = await executor.execute(sample_task)

            # 验证错误不重试
            assert result.success is False
            assert sample_task.status == TaskStatus.FAILED
            mock_storage.history.add_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_updates_task_fields(self, mock_storage, sample_task):
        """测试执行更新任务字段"""
        executor = TaskExecutor(mock_storage)

        async def mock_execute_with_fields(task):
            # 模拟 _execute_with_client 的行为，更新任务字段
            task.files_changed = ["/test/a.py", "/test/b.py"]
            task.tools_used = ["Read", "Edit", "Glob"]
            task.cost_usd = 0.123
            task.duration_ms = 10000
            return ExecutionResult(
                success=True,
                message="执行成功",
                cost_usd=0.123,
                duration_ms=10000,
                files_changed=["/test/a.py", "/test/b.py"],
                tools_used=["Read", "Edit", "Glob"],
            )

        with patch.object(
            executor, "_execute_with_client", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = mock_execute_with_fields

            await executor.execute(sample_task)

            assert sample_task.cost_usd == 0.123
            assert sample_task.duration_ms == 10000
            assert sample_task.files_changed == ["/test/a.py", "/test/b.py"]
            assert sample_task.tools_used == ["Read", "Edit", "Glob"]
            assert sample_task.started_at is not None
            assert sample_task.finished_at is not None

    @pytest.mark.asyncio
    async def test_execute_sets_executing_flag(self, mock_storage, sample_task):
        """测试执行过程中设置执行标志"""
        executor = TaskExecutor(mock_storage)

        async def check_flag(task):
            # 执行过程中应该设置标志
            assert executor.is_executing() is True
            assert executor.get_current_task() == task
            return ExecutionResult(success=True, message="完成")

        with patch.object(
            executor, "_execute_with_client", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = check_flag

            await executor.execute(sample_task)

            # 执行完成后应该清除标志
            assert executor.is_executing() is False
            assert executor.get_current_task() is None


class TestErrorType:
    """错误类型枚举测试"""

    def test_error_type_values(self):
        """测试错误类型枚举值"""
        assert ErrorType.TRANSIENT.value == "transient"
        assert ErrorType.PERMANENT.value == "permanent"
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.USER_CANCEL.value == "user_cancel"
        assert ErrorType.VALIDATION.value == "validation"
        assert ErrorType.RESOURCE.value == "resource"

    def test_retryable_errors_set(self):
        """测试可重试错误集合"""
        assert ErrorType.TRANSIENT in RETRYABLE_ERRORS
        assert ErrorType.TIMEOUT in RETRYABLE_ERRORS
        assert ErrorType.RESOURCE in RETRYABLE_ERRORS
        assert ErrorType.PERMANENT not in RETRYABLE_ERRORS
        assert ErrorType.VALIDATION not in RETRYABLE_ERRORS
        assert ErrorType.USER_CANCEL not in RETRYABLE_ERRORS


class TestErrorSeverity:
    """错误严重级别测试"""

    def test_error_severity_values(self):
        """测试错误严重级别枚举值"""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestHandleSuccess:
    """成功处理测试"""

    def test_handle_success_updates_task(self, mock_storage):
        """测试成功处理更新任务状态"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试",
            status=TaskStatus.RUNNING,
            cost_usd=0.05,
            duration_ms=5000,
        )
        result = ExecutionResult(
            success=True,
            message="执行成功",
            cost_usd=0.05,
            duration_ms=5000,
        )

        executor._handle_success(task, result)

        assert task.status == TaskStatus.COMPLETED
        assert task.finished_at is not None
        assert task.result["success"] is True
        mock_storage.history.add_completed.assert_called_once()


class TestHandleTimeout:
    """超时处理测试"""

    def test_handle_timeout_adds_error(self, mock_storage):
        """测试超时处理添加错误"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试",
            timeout=60000,
            retries=MAX_RETRIES,  # 已达上限，不重试
        )

        result = executor._handle_timeout(task)

        assert result.success is False
        assert executor._error_collector.has_errors()
        error = executor._error_collector.get_latest()
        assert error.type == "TimeoutError"


class TestHandleRetry:
    """重试处理测试"""

    def test_handle_retry_within_limit(self, mock_storage):
        """测试重试次数内处理"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试",
            timeout=60000,
            retries=0,
        )
        error = RuntimeError("Temporary failure")

        result = executor._handle_retry(task, error)

        assert result.success is False
        assert task.retries == 1
        assert task.status == TaskStatus.PENDING
        mock_storage.queue.add.assert_called_once()

    def test_handle_retry_exceeds_limit(self, mock_storage):
        """测试超过重试次数"""
        executor = TaskExecutor(mock_storage)
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试",
            timeout=60000,
            retries=MAX_RETRIES,
        )
        error = RuntimeError("Temporary failure")

        result = executor._handle_retry(task, error)

        assert result.success is False
        assert task.status == TaskStatus.FAILED
        mock_storage.history.add_failed.assert_called_once()
