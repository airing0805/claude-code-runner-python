"""任务调度模块

提供任务队列、定时任务调度、任务执行等功能。
"""

from app.scheduler.models import Task, ScheduledTask, TaskStatus
from app.scheduler.storage import TaskStorage, get_storage
from app.scheduler.config import (
    DATA_DIR,
    DEFAULT_TIMEOUT,
    POLL_INTERVAL,
    MAX_RETRIES,
    MAX_HISTORY,
    SchedulerStatus,
)
from app.scheduler.scheduler import (
    Scheduler,
    get_scheduler,
    start_scheduler,
    stop_scheduler,
    get_scheduler_status,
)
from app.scheduler.executor import TaskExecutor, get_executor

__all__ = [
    # 数据模型
    "Task",
    "ScheduledTask",
    "TaskStatus",
    # 存储
    "TaskStorage",
    "get_storage",
    # 配置
    "DATA_DIR",
    "DEFAULT_TIMEOUT",
    "POLL_INTERVAL",
    "MAX_RETRIES",
    "MAX_HISTORY",
    "SchedulerStatus",
    # 调度器
    "Scheduler",
    "get_scheduler",
    "start_scheduler",
    "stop_scheduler",
    "get_scheduler_status",
    # 执行器
    "TaskExecutor",
    "get_executor",
]
