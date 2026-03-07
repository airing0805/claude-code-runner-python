"""任务执行器统一入口

负责执行任务、超时控制、状态转换和重试机制。
"""

import asyncio
import logging
from typing import Optional

from .models import Task, ExecutionResult
from .storage import TaskStorage
from .executor_core import TaskExecutor as _TaskExecutor

logger = logging.getLogger(__name__)

# 全局执行器实例
_executor: Optional[_TaskExecutor] = None


def get_executor() -> _TaskExecutor:
    """获取执行器实例"""
    global _executor
    if _executor is None:
        _executor = _TaskExecutor(get_storage())
    return _executor


# 向后兼容的便捷函数
async def execute_task(task: Task, storage: Optional[TaskStorage] = None) -> ExecutionResult:
    """执行单个任务"""
    from .storage import get_storage
    executor = _TaskExecutor(storage or get_storage())
    return await executor.execute(task)


def cancel_task(task_id: str, storage: Optional[TaskStorage] = None) -> bool:
    """取消任务"""
    from .storage import get_storage
    executor = _TaskExecutor(storage or get_storage())
    return executor.cancel_task(task_id)
