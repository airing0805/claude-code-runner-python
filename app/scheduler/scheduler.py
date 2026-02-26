"""主调度器

负责定时轮询、检查定时任务到期、从队列获取任务执行。
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from app.scheduler.config import POLL_INTERVAL, SchedulerStatus
from app.scheduler.cron import CronParser, is_due
from app.scheduler.executor import TaskExecutor, get_executor
from app.scheduler.models import ScheduledTask, Task, TaskStatus
from app.scheduler.storage import TaskStorage, get_storage

logger = logging.getLogger(__name__)


class Scheduler:
    """主调度器

    负责：
    - 定时轮询循环（默认 10 秒）
    - 检查定时任务到期
    - 从队列获取任务执行
    - 管理任务状态迁移
    - 启动/停止调度器
    - 调度器状态管理
    """

    def __init__(
        self,
        storage: Optional[TaskStorage] = None,
        executor: Optional[TaskExecutor] = None,
        poll_interval: int = POLL_INTERVAL,
    ) -> None:
        self.storage = storage or get_storage()
        self.executor = executor or get_executor()
        self.poll_interval = poll_interval
        self._status = SchedulerStatus.STOPPED
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._cron_parser = CronParser()

    @property
    def status(self) -> SchedulerStatus:
        """获取调度器状态"""
        return self._status

    def get_status_info(self) -> dict:
        """
        获取调度器详细状态信息

        Returns:
            包含状态、统计信息的字典
        """
        return {
            "status": self._status.value,
            "poll_interval": self.poll_interval,
            "queue_count": self.storage.queue.count(),
            "scheduled_count": self.storage.scheduled.count(),
            "enabled_scheduled_count": self.storage.scheduled.enabled_count(),
            "running_count": self.storage.running.count(),
            "is_executing": self.executor.is_executing(),
            "current_task_id": (
                self.executor.get_current_task().id
                if self.executor.get_current_task()
                else None
            ),
            "updated_at": datetime.now().isoformat(),
        }

    async def start(self) -> bool:
        """
        启动调度器

        Returns:
            bool: 是否启动成功
        """
        if self._status == SchedulerStatus.RUNNING:
            logger.warning("调度器已在运行中")
            return False

        if self._status == SchedulerStatus.STARTING:
            logger.warning("调度器正在启动中")
            return False

        logger.info("正在启动调度器...")
        self._status = SchedulerStatus.STARTING
        self._stop_event.clear()

        try:
            # 创建调度任务
            self._task = asyncio.create_task(self._run_loop())
            self._status = SchedulerStatus.RUNNING
            logger.info(f"调度器已启动，轮询间隔: {self.poll_interval}秒")
            return True

        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            self._status = SchedulerStatus.STOPPED
            return False

    async def stop(self) -> bool:
        """
        停止调度器

        Returns:
            bool: 是否停止成功
        """
        if self._status == SchedulerStatus.STOPPED:
            logger.warning("调度器已停止")
            return False

        if self._status == SchedulerStatus.STOPPING:
            logger.warning("调度器正在停止中")
            return False

        logger.info("正在停止调度器...")
        self._status = SchedulerStatus.STOPPING

        try:
            # 设置停止信号
            self._stop_event.set()

            # 等待调度任务结束
            if self._task and not self._task.done():
                try:
                    # 最多等待 5 秒
                    await asyncio.wait_for(self._task, timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("调度任务未在超时时间内结束，强制取消")
                    self._task.cancel()
                    try:
                        await self._task
                    except asyncio.CancelledError:
                        pass

            self._task = None
            self._status = SchedulerStatus.STOPPED
            logger.info("调度器已停止")
            return True

        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
            self._status = SchedulerStatus.STOPPED
            return False

    async def _run_loop(self) -> None:
        """
        主调度循环

        每次循环执行:
        1. 检查定时任务是否到期，到期则加入队列
        2. 从队列获取任务执行
        """
        logger.info("调度循环开始")

        while not self._stop_event.is_set():
            try:
                # 1. 检查定时任务到期
                await self._check_scheduled_tasks()

                # 2. 执行队列中的任务
                await self._process_queue()

            except Exception as e:
                logger.exception(f"调度循环异常: {e}")

            # 等待下一次轮询
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval,
                )
                # 如果 wait 返回，说明收到了停止信号
                break
            except asyncio.TimeoutError:
                # 超时正常，继续下一次循环
                pass

        logger.info("调度循环结束")

    async def _check_scheduled_tasks(self) -> None:
        """
        检查定时任务是否到期

        到期的定时任务会被转换为普通任务加入队列
        """
        try:
            scheduled_tasks = self.storage.scheduled.get_enabled()

            for scheduled in scheduled_tasks:
                if self._stop_event.is_set():
                    break

                # 检查是否到期
                if is_due(scheduled.next_run):
                    await self._trigger_scheduled_task(scheduled)

        except Exception as e:
            logger.error(f"检查定时任务失败: {e}")

    async def _trigger_scheduled_task(self, scheduled: ScheduledTask) -> None:
        """
        触发定时任务

        将定时任务转换为普通任务加入队列，并更新下次执行时间

        Args:
            scheduled: 到期的定时任务
        """
        logger.info(f"定时任务到期: {scheduled.name} ({scheduled.id})")

        try:
            # 创建任务并加入队列
            task = Task(
                id=str(uuid.uuid4()),
                prompt=scheduled.prompt,
                workspace=scheduled.workspace,
                timeout=scheduled.timeout,
                auto_approve=scheduled.auto_approve,
                allowed_tools=scheduled.allowed_tools,
                scheduled=True,
                scheduled_id=scheduled.id,
            )

            self.storage.queue.add(task)
            logger.info(f"定时任务已加入队列: {task.id}")

            # 更新定时任务的执行信息
            scheduled.last_run = datetime.now().isoformat()
            scheduled.run_count += 1

            # 计算下次执行时间
            next_run = self._cron_parser.calculate_next_run(scheduled.cron)
            if next_run:
                scheduled.next_run = next_run.isoformat()

            # 保存更新
            self.storage.scheduled.save(scheduled)
            logger.info(f"定时任务下次执行时间: {scheduled.next_run}")

        except Exception as e:
            logger.error(f"触发定时任务失败: {e}")

    async def _process_queue(self) -> None:
        """
        处理任务队列

        从队列获取任务并执行
        """
        # 如果正在执行任务，跳过
        if self.executor.is_executing():
            return

        # 从队列获取任务
        task = self.storage.queue.pop()
        if task is None:
            return

        logger.info(f"从队列获取任务: {task.id}")
        await self._execute_task(task)

    async def _execute_task(self, task: Task) -> None:
        """
        执行单个任务

        Args:
            task: 待执行的任务
        """
        try:
            result = await self.executor.execute(task)

            if result.success:
                logger.info(f"任务执行成功: {task.id}")
            else:
                logger.warning(f"任务执行失败: {task.id}, 原因: {result.error}")

        except Exception as e:
            logger.exception(f"任务执行异常: {task.id}, 错误: {e}")

            # 确保异常情况下任务状态被正确处理
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.finished_at = datetime.now().isoformat()
                self.storage.running.remove(task.id)
                self.storage.history.add_failed(task)

    def run_task_now(self, task_id: str) -> Optional[Task]:
        """
        立即执行指定的队列任务

        注意：此方法是同步的，只是将任务移到队首
        实际执行会在下一次轮询时进行

        Args:
            task_id: 任务 ID

        Returns:
            Task: 找到的任务，未找到返回 None
        """
        task = self.storage.queue.get(task_id)
        if task is None:
            logger.warning(f"未找到任务: {task_id}")
            return None

        logger.info(f"任务已标记为立即执行: {task_id}")
        return task

    def run_scheduled_now(self, scheduled_id: str) -> Optional[Task]:
        """
        立即执行指定的定时任务

        将定时任务转换为普通任务加入队列

        Args:
            scheduled_id: 定时任务 ID

        Returns:
            Task: 创建的任务，未找到定时任务返回 None
        """
        scheduled = self.storage.scheduled.get(scheduled_id)
        if scheduled is None:
            logger.warning(f"未找到定时任务: {scheduled_id}")
            return None

        # 创建任务并加入队列
        task = Task(
            id=str(uuid.uuid4()),
            prompt=scheduled.prompt,
            workspace=scheduled.workspace,
            timeout=scheduled.timeout,
            auto_approve=scheduled.auto_approve,
            allowed_tools=scheduled.allowed_tools,
            scheduled=True,
            scheduled_id=scheduled.id,
        )

        self.storage.queue.add(task)
        logger.info(f"定时任务已立即加入队列: {scheduled.name} -> {task.id}")

        return task

    def is_running(self) -> bool:
        """检查调度器是否在运行"""
        return self._status == SchedulerStatus.RUNNING

    def is_stopped(self) -> bool:
        """检查调度器是否已停止"""
        return self._status == SchedulerStatus.STOPPED


# 全局调度器实例
_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """获取调度器单例实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler


async def start_scheduler() -> bool:
    """
    启动全局调度器

    Returns:
        bool: 是否启动成功
    """
    scheduler = get_scheduler()
    return await scheduler.start()


async def stop_scheduler() -> bool:
    """
    停止全局调度器

    Returns:
        bool: 是否停止成功
    """
    global _scheduler
    if _scheduler is None:
        return False

    result = await _scheduler.stop()
    return result


def get_scheduler_status() -> dict:
    """
    获取全局调度器状态

    Returns:
        调度器状态信息字典
    """
    scheduler = get_scheduler()
    return scheduler.get_status_info()
