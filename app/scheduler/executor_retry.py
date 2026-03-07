"""任务执行器重试机制模块"""

import random
from typing import Optional

from .config import MAX_RETRIES
from .executor_errors import ErrorType, should_retry
from .models import Task, TaskStatus
from .storage import TaskStorage


# 重试延迟配置
BASE_DELAY = 5.0       # 基础延迟（秒）
MAX_DELAY = 60.0       # 最大延迟（秒）
JITTER = 0.1           # 抖动因子


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


async def handle_retry(
    task: Task,
    error: Exception,
    storage: TaskStorage,
    error_collector,
    logger,
) -> dict:
    """处理重试逻辑"""
    from .executor_errors import classify_error
    from .timezone_utils import now_iso
    
    error_type = classify_error(error)

    # 判断是否可重试
    if not should_retry(task, error_type):
        # 不可重试，标记失败
        task.finished_at = now_iso()
        task.status = TaskStatus.FAILED
        task.error = str(error)
        task.result = {
            "success": False,
            "error": str(error),
            "errors": [e.to_dict() for e in error_collector.get_all()],
        }

        # 从运行中移除，保存到失败历史
        storage.running.remove(task.id)
        storage.history.add_failed(task)

        # 记录失败日志
        _log(
            task.id,
            "ERROR",
            "任务执行失败",
            {
                "error": str(error),
                "error_type": error_type.value,
                "retries": task.retries,
                "errors": [e.to_dict() for e in error_collector.get_all()],
            },
            storage
        )

        logger.error(f"Task {task.id} failed permanently: {error}")
        return {
            "success": False,
            "message": "任务执行失败，已达到最大重试次数",
            "error": str(error),
        }

    # 检查任务是否已被取消
    current_task = storage.queue.get(task.id)
    if current_task and current_task.status == TaskStatus.CANCELLED:
        task.status = TaskStatus.CANCELLED
        task.finished_at = now_iso()
        task.error = "任务已被用户取消"
        storage.running.remove(task.id)
        storage.cancelled.add(task)
        logger.info(f"Task {task.id} was cancelled by user")
        return {
            "success": False,
            "message": "任务已被取消",
            "error": "Task cancelled by user",
        }

    # 可重试
    task.retries += 1
    retry_delay = calculate_retry_delay(task.retries)

    # 重置执行状态
    task.status = TaskStatus.PENDING
    task.started_at = None
    task.finished_at = None
    task.error = f"重试 {task.retries}/{MAX_RETRIES}: {str(error)}"

    # 从运行中移除，重新加入队列（插入队首以优先处理）
    # 添加重试延迟，避免立即重试失败
    logger.info(f"等待重试延迟: {retry_delay:.1f}s")
    await asyncio.sleep(retry_delay)
    storage.running.remove(task.id)
    storage.queue.add_to_front(task)

    # 记录重试日志
    _log(
        task.id,
        "WARNING",
        f"任务将重试（第 {task.retries} 次）",
        {
            "error": str(error),
            "error_type": error_type.value,
            "retry_count": task.retries,
            "retry_delay": retry_delay,
        },
        storage
    )

    logger.info(
        f"Task {task.id} scheduled for retry "
        f"({task.retries}/{MAX_RETRIES}) in {retry_delay:.1f}s"
    )

    return {
        "success": False,
        "message": f"任务将重试（第 {task.retries} 次）",
        "error": str(error),
    }


def _log(
    task_id: str,
    level: str,
    message: str,
    context: dict | None = None,
    storage: Optional[TaskStorage] = None,
) -> None:
    """记录任务执行日志

    Args:
        task_id: 任务 ID
        level: 日志级别 (INFO, WARNING, ERROR)
        message: 日志消息
        context: 上下文信息
        storage: 存储实例
    """
    log_entry = {
        "id": str(uuid.uuid4()),
        "task_id": task_id,
        "timestamp": now_iso(),
        "level": level,
        "message": message,
        "context": context or {},
    }
    
    if storage:
        storage.logs.append(log_entry)