"""主调度器

使用 APScheduler 管理定时任务，提供进程隔离的任务执行。
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from app.scheduler.config import SchedulerStatus, POLL_INTERVAL
from app.scheduler.models import ScheduledTask, Task, TaskStatus
from app.scheduler.storage import TaskStorage, get_storage
from app.scheduler.apscheduler_wrapper import APSchedulerWrapper
from app.scheduler.security import validate_workspace
from app.scheduler.timezone_utils import now_iso, format_datetime

logger = logging.getLogger(__name__)


class Scheduler:
    """主调度器

    负责：
    - 使用 APScheduler 管理定时任务
    - 从队列获取任务执行
    - 管理任务状态迁移
    - 启动/停止调度器
    - 调度器状态管理
    """

    def __init__(
        self,
        storage: Optional[TaskStorage] = None,
    ) -> None:
        self.storage = storage or get_storage()
        self.apscheduler = APSchedulerWrapper(self.storage)
        self._status = SchedulerStatus.STOPPED
        self._queue_task: asyncio.Task[None] | None = None  # 队列处理任务

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
        # 获取 APScheduler 的任务信息
        aps_jobs = self.apscheduler.get_jobs()

        return {
            "status": self._status.value,
            "queue_count": self.storage.queue.count(),
            "scheduled_count": self.storage.scheduled.count(),
            "enabled_scheduled_count": self.storage.scheduled.enabled_count(),
            "running_count": self.storage.running.count(),
            "apscheduler_jobs": aps_jobs,
            "updated_at": now_iso(),
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

        try:
            # 启动前恢复运行中的任务
            await self._recover_running_tasks()

            # 加载所有启用的定时任务到 APScheduler
            await self._load_scheduled_tasks()

            # 启动 APScheduler
            self.apscheduler.start()

            # 启动队列处理循环
            self._queue_task = asyncio.create_task(self._run_queue_loop())
            logger.info("队列处理循环已启动")

            self._status = SchedulerStatus.RUNNING
            logger.info("调度器已启动")
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
            # 取消队列处理任务
            if self._queue_task and not self._queue_task.done():
                self._queue_task.cancel()
                try:
                    await self._queue_task
                except asyncio.CancelledError:
                    pass
                logger.info("队列处理循环已取消")

            # 关闭 APScheduler
            self.apscheduler.shutdown(wait=True)
            self._status = SchedulerStatus.STOPPED
            logger.info("调度器已停止")
            return True

        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
            self._status = SchedulerStatus.STOPPED
            return False

    async def _load_scheduled_tasks(self) -> None:
        """
        加载所有启用的定时任务到 APScheduler
        并检查过期任务立即执行

        触发条件：
        1. next_run 已过期（is_due 返回 True）
        2. next_run 为 None 或空（服务运行期间新增的任务）
        """
        from app.scheduler.cron import CronParser, is_due

        scheduled_tasks = self.storage.scheduled.get_enabled()
        logger.info(f"加载 {len(scheduled_tasks)} 个启用的定时任务")

        # 调试：打印所有任务的 next_run 状态
        for task in scheduled_tasks:
            logger.debug(f"任务状态: id={task.id}, name={task.name}, next_run={task.next_run!r}, enabled={task.enabled}")

        cron_parser = CronParser()

        for scheduled in scheduled_tasks:
            try:
                # 检查是否需要触发任务执行
                should_trigger = False
                trigger_reason = ""

                if is_due(scheduled.next_run):
                    # next_run 存在且已过期
                    should_trigger = True
                    trigger_reason = f"任务已过期 (next_run={scheduled.next_run})"
                elif not scheduled.next_run or scheduled.next_run.strip() == "":
                    # next_run 为 None 或空（服务运行期间新增的任务）
                    should_trigger = True
                    trigger_reason = f"任务 next_run 为空 (当前值: {scheduled.next_run!r})"

                logger.info(f"检查任务: {scheduled.name}, should_trigger={should_trigger}, reason={trigger_reason}")

                if should_trigger:
                    logger.info(f"检测到需要执行的任务: {scheduled.name} ({scheduled.id}), 原因: {trigger_reason}")

                    # 立即触发任务（加入队列）
                    await self.apscheduler.trigger_scheduled_task(scheduled.id)

                    # 注意：trigger_scheduled_task 内部已经会更新 next_run，
                    # 这里不需要重复更新（避免覆盖已保存的值）
                    # 重新获取任务以确保获取最新的 next_run
                    updated_task = self.storage.scheduled.get(scheduled.id)
                    if updated_task:
                        logger.info(f"触发后任务状态: id={updated_task.id}, next_run={updated_task.next_run}")

                # 添加到 APScheduler
                self.apscheduler.add_scheduled_task(scheduled)

                # 保存计算出的 next_run 到存储（APScheduler 内部已计算）
                if scheduled.next_run:
                    self.storage.scheduled.save(scheduled)
                    logger.info(f"已保存任务下次执行时间: {scheduled.name}, next_run: {scheduled.next_run}")

                logger.info(f"定时任务已加载: {scheduled.name} ({scheduled.id})")
            except Exception as e:
                logger.error(f"加载定时任务失败: {scheduled.id}, 错误: {e}", exc_info=True)

    async def _recover_running_tasks(self) -> None:
        """
        恢复运行中的任务

        服务重启时，running.json 中可能有未完成的任务。
        将这些任务的状态重置为 pending 并加入队列头部。
        """
        running_tasks = self.storage.running.get_all()
        if not running_tasks:
            return

        logger.info(f"发现 {len(running_tasks)} 个运行中的任务，开始恢复")

        for task in running_tasks:
            # 规范化 workspace
            task.workspace = validate_workspace(task.workspace)

            # 重置任务状态
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.error = "服务重启，任务重新排队"

            # 加入队列头部（优先处理）
            self.storage.queue.add_to_front(task)
            logger.info(f"任务已恢复到队列: {task.id}")

        # 清空 running 存储
        self.storage.running.clear()
        logger.info(f"已恢复 {len(running_tasks)} 个运行中的任务")

    async def _run_queue_loop(self) -> None:
        """队列处理循环

        定期从队列中取出任务并执行。
        同时每隔 POLL_INTERVAL 检查 scheduled.json 中的任务，
        当 next_run 为 null 或为空时触发执行。
        只有当没有运行中的任务时，才从队列取任务执行。
        """
        # 延迟导入避免循环依赖
        from app.scheduler.executor import TaskExecutor

        executor = TaskExecutor(self.storage)

        logger.info("队列处理循环已开始运行")

        while self._status == SchedulerStatus.RUNNING:
            try:
                # === 检查 scheduled.json 中的任务 ===
                # 触发条件：next_run 为 null 或空（适用于服务运行期间新增的任务）
                self._check_scheduled_tasks_on_loop()

                # 检查是否有运行中的任务
                if self.storage.running.count() == 0:
                    # 没有运行中的任务，从队列获取任务
                    task = self.storage.queue.pop()

                    if task:
                        logger.info(f"从队列取出任务: {task.id}, prompt: {task.prompt[:50]}...")

                        # 执行任务
                        try:
                            result = await executor.execute(task)

                            if result.success:
                                logger.info(f"任务执行成功: {task.id}")
                            else:
                                logger.warning(f"任务执行失败: {task.id}, 错误: {result.error}")

                        except Exception as e:
                            logger.error(f"执行任务时发生异常: {task.id}, 错误: {e}", exc_info=True)
                else:
                    # 有运行中的任务，跳过本次检查
                    logger.debug(f"有运行中的任务，等待执行完成")

                # 等待一段时间
                await asyncio.sleep(POLL_INTERVAL)

            except asyncio.CancelledError:
                logger.info("队列处理循环已取消")
                break
            except Exception as e:
                logger.error(f"队列处理循环错误: {e}", exc_info=True)
                await asyncio.sleep(POLL_INTERVAL)

    def _check_scheduled_tasks_on_loop(self) -> None:
        """在队列处理循环中检查定时任务

        检查 scheduled.json 中的任务，当 next_run 为 null 或空时触发执行。
        这个方法在每次 POLL_INTERVAL 执行一次。
        """
        # 延迟导入避免循环依赖
        from app.scheduler.cron import is_due

        try:
            scheduled_tasks = self.storage.scheduled.get_enabled()

            for scheduled in scheduled_tasks:
                # 检查是否需要触发任务执行
                should_trigger = False
                trigger_reason = ""

                if is_due(scheduled.next_run):
                    # next_run 存在且已过期
                    should_trigger = True
                    trigger_reason = f"任务已过期 (next_run={scheduled.next_run})"
                elif not scheduled.next_run or scheduled.next_run.strip() == "":
                    # next_run 为 None 或空（适用于服务运行期间新增的任务）
                    should_trigger = True
                    trigger_reason = f"任务 next_run 为空 (当前值: {scheduled.next_run!r})"

                if should_trigger:
                    logger.info(f"[循环检查] 检测到需要执行的任务: {scheduled.name} ({scheduled.id}), 原因: {trigger_reason}")

                    # 使用 APScheduler 触发任务（异步执行）
                    asyncio.create_task(self.apscheduler.trigger_scheduled_task(scheduled.id))

                    # 触发后重新获取任务，打印最新的 next_run 状态
                    updated_task = self.storage.scheduled.get(scheduled.id)
                    if updated_task:
                        logger.info(f"[循环检查] 触发后任务状态: id={updated_task.id}, next_run={updated_task.next_run}")

        except Exception as e:
            logger.error(f"[循环检查] 检查定时任务失败: {e}", exc_info=True)

    def add_scheduled_task(self, scheduled: ScheduledTask) -> bool:
        """
        添加定时任务

        Args:
            scheduled: 定时任务对象

        Returns:
            bool: 是否添加成功
        """
        try:
            # 规范化 workspace
            scheduled.workspace = validate_workspace(scheduled.workspace)

            # 保存到存储
            self.storage.scheduled.save(scheduled)

            # 添加到 APScheduler
            self.apscheduler.add_scheduled_task(scheduled)
            logger.info(f"定时任务已添加: {scheduled.name} ({scheduled.id})")
            return True
        except Exception as e:
            logger.error(f"添加定时任务失败: {scheduled.id}, 错误: {e}")
            return False

    def update_scheduled_task(self, scheduled: ScheduledTask) -> bool:
        """
        更新定时任务

        Args:
            scheduled: 定时任务对象

        Returns:
            bool: 是否更新成功
        """
        try:
            # 规范化 workspace
            scheduled.workspace = validate_workspace(scheduled.workspace)

            # 先移除旧的
            if scheduled.enabled:
                self.apscheduler.remove_scheduled_task(scheduled.id)

            # 保存到存储
            self.storage.scheduled.save(scheduled)

            # 如果启用，重新添加到 APScheduler
            if scheduled.enabled:
                self.apscheduler.add_scheduled_task(scheduled)
                logger.info(f"定时任务已更新并启用: {scheduled.name} ({scheduled.id})")
            else:
                logger.info(f"定时任务已更新并禁用: {scheduled.name} ({scheduled.id})")
            return True
        except Exception as e:
            logger.error(f"更新定时任务失败: {scheduled.id}, 错误: {e}")
            return False

    def remove_scheduled_task(self, task_id: str) -> bool:
        """
        移除定时任务

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否移除成功
        """
        try:
            # 从存储移除
            success = self.storage.scheduled.delete(task_id)

            # 从 APScheduler 移除
            self.apscheduler.remove_scheduled_task(task_id)

            if success:
                logger.info(f"定时任务已移除: {task_id}")
            return success
        except Exception as e:
            logger.error(f"移除定时任务失败: {task_id}, 错误: {e}")
            return False

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

        # 规范化 workspace
        workspace = validate_workspace(scheduled.workspace)

        # 创建任务并加入队列
        task = Task(
            id=str(uuid.uuid4()),
            prompt=scheduled.prompt,
            workspace=workspace,
            timeout=scheduled.timeout,
            auto_approve=scheduled.auto_approve,
            allowed_tools=scheduled.allowed_tools,
            source="immediate",
            scheduled_id=scheduled.id,
            scheduled_name=scheduled.name,
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

    def get_job_info(self, task_id: str) -> Optional[dict]:
        """
        获取任务信息

        Args:
            task_id: 任务 ID

        Returns:
            任务信息字典，不存在返回 None
        """
        return self.apscheduler.get_job_info(task_id)


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
