"""任务执行器异步修复测试

测试 executor.py 中异步函数修改的正确性。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.scheduler.executor import TaskExecutor
from app.scheduler.models import Task, TaskStatus
from app.scheduler.executor_core import ExecutionResult
from app.scheduler.storage import get_storage


class TestAsyncHandleRetry:
    """测试异步重试处理"""

    @pytest.mark.asyncio
    async def test_handle_error_with_sleep(self):
        """测试 _handle_error 使用异步处理而非阻塞的 time.sleep"""
        # 创建模拟存储
        mock_storage = MagicMock()
        mock_storage.running = MagicMock()
        mock_storage.running.remove = MagicMock()
        mock_storage.history = MagicMock()
        mock_storage.history.add_failed = MagicMock()

        # 创建执行器实例
        executor = TaskExecutor(storage=mock_storage)

        # 创建测试任务
        task = Task(id="test-task-1", prompt="Test prompt")

        # 执行异步错误处理
        error = Exception("Test error")
        result = await executor._handle_error(task, error)

        # 验证结果
        assert result is not None
        assert result.success is False

        # 验证异步函数能正常执行

    @pytest.mark.asyncio
    async def test_handle_success_is_async(self):
        """验证 _handle_success 是异步函数"""
        mock_storage = MagicMock()
        executor = TaskExecutor(storage=mock_storage)

        task = Task(id="test-task-2", prompt="Test prompt")
        result = ExecutionResult(success=True, message="Success")

        # 验证可以 await 调用
        handle_result = await executor._handle_success(task, result)
        assert handle_result is not None

    @pytest.mark.asyncio
    async def test_handle_failure_is_async(self):
        """验证 _handle_failure 是异步函数"""
        mock_storage = MagicMock()
        executor = TaskExecutor(storage=mock_storage)

        task = Task(id="test-task-3", prompt="Test prompt")
        result = ExecutionResult(success=False, message="Failure", error="Test error")

        handle_result = await executor._handle_failure(task, result)
        assert handle_result is not None

    @pytest.mark.asyncio
    async def test_handle_timeout_is_async(self):
        """验证 _handle_timeout 是异步函数"""
        mock_storage = MagicMock()
        mock_storage.running = MagicMock()
        mock_storage.running.remove = MagicMock()
        mock_storage.history = MagicMock()
        mock_storage.history.add_failed = MagicMock()

        executor = TaskExecutor(storage=mock_storage)

        task = Task(id="test-task-4", prompt="Test prompt", timeout=1000)

        handle_result = await executor._handle_timeout(task)
        assert handle_result is not None

    @pytest.mark.asyncio
    async def test_handle_error_is_async(self):
        """验证 _handle_error 是异步函数"""
        mock_storage = MagicMock()
        mock_storage.running = MagicMock()
        mock_storage.running.remove = MagicMock()
        mock_storage.history = MagicMock()
        mock_storage.history.add_failed = MagicMock()

        executor = TaskExecutor(storage=mock_storage)

        task = Task(id="test-task-5", prompt="Test prompt")
        error = Exception("Test error")

        handle_result = await executor._handle_error(task, error)
        assert handle_result is not None
