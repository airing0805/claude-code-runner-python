"""APScheduler 封装

使用成熟的 APScheduler 库替代自定义调度逻辑，提供：
- 进程隔离的任务执行
- 自动并发控制
- 内置 Cron 支持
- 任务失败重试
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
)

from app.scheduler.models import ScheduledTask, Task, TaskStatus, TaskSource
from app.scheduler.storage import TaskStorage, get_storage
from app.scheduler.security import validate_workspace
from app.scheduler.timezone_utils import SHANGHAI_TZ, now_shanghai, format_datetime
from app.scheduler.cron import calculate_next_run

logger = logging.getLogger(__name__)


class APSchedulerWrapper:
    """APScheduler 封装

    职责:
    - 封装 APScheduler 的配置和管理
    - 提供 Cron 定时触发
    - 处理任务状态和错误

    执行流程:
    1. Cron 触发 -> trigger_scheduled_task() -> 添加任务到队列
    2. Scheduler._run_queue_loop() -> 从队列取出任务
    3. TaskExecutor.execute() -> 统一执行任务
    """

    def __init__(self, storage: Optional[TaskStorage] = None):
        self.storage = storage or get_storage()
        self.scheduler = AsyncIOScheduler(timezone=SHANGHAI_TZ)
        self._setup_listeners()

    def _setup_listeners(self) -> None:
        """设置事件监听器"""
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED,
        )
        self.scheduler.add_listener(
            self._on_job_error,
            EVENT_JOB_ERROR,
        )
        self.scheduler.add_listener(
            self._on_job_missed,
            EVENT_JOB_MISSED,
        )

    def _on_job_executed(self, event) -> None:
        """任务执行完成事件"""
        job_id = event.job_id
        logger.info(f"[APScheduler] Cron 触发完成: {job_id}")

    def _on_job_error(self, event) -> None:
        """任务执行错误事件"""
        job_id = event.job_id
        exception = event.exception
        logger.error(f"[APScheduler] Cron 触发失败: {job_id}, 错误: {exception}")

    def _on_job_missed(self, event) -> None:
        """任务错过执行事件"""
        job_id = event.job_id
        logger.warning(f"[APScheduler] 任务错过执行: {job_id}")

    async def trigger_scheduled_task(self, scheduled_id: str) -> None:
        """触发定时任务 - 将任务添加到队列等待执行

        当 Cron 触发时，此方法负责：
        1. 检查定时任务是否存在且已启用
        2. 创建一个新任务到队列（统一由 _run_queue_loop 执行）

        注意：
        - 不进行任何去重操作
        - 同一个定时任务可能有多次触发在队列中等待执行
        - 如果队列积压，说明任务执行有问题，用户应该能看到

        Args:
            scheduled_id: 定时任务 ID
        """
        # 从 scheduled_tasks 存储获取最新配置
        scheduled = self.storage.scheduled.get(scheduled_id)
        if not scheduled:
            logger.warning(f"[APScheduler] 定时任务不存在: {scheduled_id}")
            return

        # 检查任务是否启用
        if not scheduled.enabled:
            logger.info(f"[APScheduler] 定时任务已禁用，跳过执行: {scheduled_id}")
            return

        # 规范化 workspace（处理空字符串和 None）
        workspace = validate_workspace(scheduled.workspace)

        # 直接添加到队列，不做任何去重
        # 让队列真实反映任务状态，用户可以看到有多少任务在等待
        new_task = Task(
            id=str(uuid.uuid4()),
            prompt=scheduled.prompt,
            workspace=workspace,
            timeout=scheduled.timeout,
            auto_approve=scheduled.auto_approve,
            allowed_tools=scheduled.allowed_tools,
            source=TaskSource.SCHEDULED,
            scheduled_id=scheduled.id,
            scheduled_name=scheduled.name,
        )
        self.storage.queue.add(new_task)

        # 更新定时任务的 last_run 和 next_run
        scheduled.last_run = format_datetime(now_shanghai())
        # 计算并更新下次执行时间
        next_run = calculate_next_run(scheduled.cron)
        if next_run:
            scheduled.next_run = format_datetime(next_run)
        self.storage.scheduled.save(scheduled)

        logger.info(
            f"[APScheduler] 定时任务已触发: {scheduled_id} ({scheduled.name}), "
            f"新任务ID: {new_task.id}, prompt: {scheduled.prompt[:50]}..."
        )

    def add_scheduled_task(self, scheduled: ScheduledTask) -> None:
        """添加定时任务到 APScheduler

        Args:
            scheduled: 定时任务对象

        Note:
            此方法只负责将定时任务注册到 APScheduler，
            不再往队列添加占位任务（由 trigger_scheduled_task 负责）。
        """
        # 计算下次执行时间
        from app.scheduler.cron import calculate_next_run
        from app.scheduler.timezone_utils import format_datetime
        next_run = calculate_next_run(scheduled.cron)
        if next_run:
            scheduled.next_run = format_datetime(next_run)

        # 添加定时任务到 APScheduler
        try:
            # 处理 Cron 表达式格式
            # APScheduler CronTrigger.from_crontab 只支持 5 字段格式（分 时 日 月 周）
            # 6 字段格式（秒 分 时 日 月 周）需要使用 CronTrigger 直接构造
            cron_fields = scheduled.cron.strip().split()

            if len(cron_fields) == 5:
                # 5 字段格式：分 时 日 月 周
                trigger = CronTrigger.from_crontab(scheduled.cron, timezone=SHANGHAI_TZ)
            elif len(cron_fields) == 6:
                # 6 字段格式：秒 分 时 日 月 周
                trigger = CronTrigger(
                    second=cron_fields[0],
                    minute=cron_fields[1],
                    hour=cron_fields[2],
                    day=cron_fields[3],
                    month=cron_fields[4],
                    day_of_week=cron_fields[5],
                    timezone=SHANGHAI_TZ,
                )
            else:
                raise ValueError(f"无效的 Cron 表达式格式: 期望 5 或 6 个字段，实际 {len(cron_fields)} 个")

            self.scheduler.add_job(
                func=self.trigger_scheduled_task,
                trigger=trigger,
                id=scheduled.id,
                args=[scheduled.id],
                max_instances=1,
                replace_existing=True,
                coalesce=False,
            )
            logger.info(
                f"[APScheduler] 定时任务已添加: {scheduled.id} ({scheduled.name}), "
                f"Cron: {scheduled.cron}, 下次执行: {scheduled.next_run}"
            )
        except Exception as e:
            logger.error(
                f"[APScheduler] 添加定时任务失败: {scheduled.id}, "
                f"Cron: {scheduled.cron}, 错误: {e}"
            )
            raise

    def remove_scheduled_task(self, task_id: str) -> bool:
        """移除定时任务

        Args:
            task_id: 任务 ID

        Returns:
            是否移除成功
        """
        try:
            # 从 APScheduler 移除
            self.scheduler.remove_job(task_id)

            logger.info(f"[APScheduler] 定时任务已移除: {task_id}")
            return True
        except Exception as e:
            logger.error(f"[APScheduler] 移除定时任务失败: {task_id}, 错误: {e}")
            return False

    def pause_scheduled_task(self, task_id: str) -> bool:
        """暂停定时任务

        Args:
            task_id: 任务 ID

        Returns:
            是否暂停成功
        """
        try:
            self.scheduler.pause_job(task_id)
            logger.info(f"[APScheduler] 定时任务已暂停: {task_id}")
            return True
        except Exception as e:
            logger.error(f"[APScheduler] 暂停定时任务失败: {task_id}, 错误: {e}")
            return False

    def resume_scheduled_task(self, task_id: str) -> bool:
        """恢复定时任务

        Args:
            task_id: 任务 ID

        Returns:
            是否恢复成功
        """
        try:
            self.scheduler.resume_job(task_id)
            logger.info(f"[APScheduler] 定时任务已恢复: {task_id}")
            return True
        except Exception as e:
            logger.error(f"[APScheduler] 恢复定时任务失败: {task_id}, 错误: {e}")
            return False

    def get_job_info(self, task_id: str) -> Optional[dict]:
        """获取任务信息

        Args:
            task_id: 任务 ID

        Returns:
            任务信息字典，不存在返回 None
        """
        try:
            job = self.scheduler.get_job(task_id)
            if job:
                return {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger),
                }
            return None
        except Exception as e:
            logger.error(f"[APScheduler] 获取任务信息失败: {task_id}, 错误: {e}")
            return None

    def start(self) -> None:
        """启动调度器"""
        self.scheduler.start()
        logger.info("[APScheduler] 调度器已启动")

    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器

        Args:
            wait: 是否等待正在执行的任务完成
        """
        self.scheduler.shutdown(wait=wait)
        logger.info("[APScheduler] 调度器已关闭")

    def get_jobs(self) -> list[dict]:
        """获取所有任务列表

        Returns:
            任务信息列表
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            })
        return jobs
