"""任务调度存储层统一入口

提供 JSON 文件存储、并发安全、原子写入等功能。
"""

from pathlib import Path
from typing import Optional

from .config import (
    QUEUE_FILE,
    SCHEDULED_FILE,
    RUNNING_FILE,
    COMPLETED_FILE,
    FAILED_FILE,
    CANCELLED_FILE,
    LOGS_FILE,
)
from .models import Task, ScheduledTask, PaginatedResponse
from .storage_queue import QueueStorage
from .storage_scheduled import ScheduledStorage
from .storage_running import RunningStorage
from .storage_history import HistoryStorage
from .storage_cancelled import CancelledStorage
from .storage_logs import LogsStorage


class TaskStorage:
    """统一的任务存储接口"""

    def __init__(self):
        self.queue = QueueStorage(QUEUE_FILE)
        self.scheduled = ScheduledStorage(SCHEDULED_FILE)
        self.running = RunningStorage(RUNNING_FILE)
        self.history = HistoryStorage(COMPLETED_FILE, FAILED_FILE)
        self.cancelled = CancelledStorage(CANCELLED_FILE)
        self.logs = LogsStorage(LOGS_FILE)

    @classmethod
    def get_instance(cls) -> "TaskStorage":
        """获取单例实例"""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance


# 全局单例
_task_storage: Optional[TaskStorage] = None


def get_storage() -> TaskStorage:
    """获取任务存储实例"""
    global _task_storage
    if _task_storage is None:
        _task_storage = TaskStorage()
    return _task_storage
