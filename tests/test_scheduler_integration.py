"""调度器集成测试

测试主调度器的核心功能：
- 定时任务到期触发
- 队列任务执行
- 启动/停止
- 状态管理
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.scheduler.scheduler import Scheduler, get_scheduler, start_scheduler, stop_scheduler
from app.scheduler.config import POLL_INTERVAL, SchedulerStatus
from app.scheduler.models import Task, TaskStatus, ScheduledTask
from app.scheduler.storage import TaskStorage
from app.scheduler.executor import TaskExecutor, ExecutionResult


@pytest.fixture
def mock_storage():
    """创建模拟存储层"""
    storage = MagicMock(spec=TaskStorage)

    # 队列存储
    storage.queue = MagicMock()
    storage.queue.count = MagicMock(return_value=0)
    storage.queue.pop = MagicMock(return_value=None)
    storage.queue.add = MagicMock()
    storage.queue.get = MagicMock(return_value=None)
    storage.queue.clear = MagicMock()

    # 定时任务存储
    storage.scheduled = MagicMock()
    storage.scheduled.count = MagicMock(return_value=0)
    storage.scheduled.enabled_count = MagicMock(return_value=0)
    storage.scheduled.get_enabled = MagicMock(return_value=[])
    storage.scheduled.get = MagicMock(return_value=None)
    storage.scheduled.save = MagicMock()
    storage.scheduled.add = MagicMock()

    # 运行中任务存储
    storage.running = MagicMock()
    storage.running.count = MagicMock(return_value=0)
    storage.running.add = MagicMock()
    storage.running.remove = MagicMock()

    # 历史记录存储
    storage.history = MagicMock()
    storage.history.add_completed = MagicMock()
    storage.history.add_failed = MagicMock()

    return storage


@pytest.fixture
def mock_executor():
    """创建模拟执行器"""
    executor = MagicMock(spec=TaskExecutor)
    executor.is_executing = MagicMock(return_value=False)
    executor.get_current_task = MagicMock(return_value=None)
    executor.execute = AsyncMock(return_value=ExecutionResult(
        success=True,
        message="执行成功",
        cost_usd=0.05,
        duration_ms=5000,
    ))
    return executor


@pytest.fixture
def scheduler(mock_storage, mock_executor):
    """创建使用模拟依赖的调度器"""
    return Scheduler(
        storage=mock_storage,
        executor=mock_executor,
        poll_interval=1,  # 使用较短的轮询间隔加速测试
    )


@pytest.fixture
def sample_task():
    """创建示例任务"""
    return Task(
        id=str(uuid.uuid4()),
        prompt="测试任务",
        workspace="/test/workspace",
        timeout=60000,
        status=TaskStatus.PENDING,
    )


@pytest.fixture
def sample_scheduled_task():
    """创建示例定时任务"""
    return ScheduledTask(
        id=str(uuid.uuid4()),
        name="测试定时任务",
        prompt="定时任务描述",
        cron="* * * * *",  # 每分钟执行
        workspace="/test/workspace",
        timeout=60000,
        enabled=True,
        next_run=datetime.now().isoformat(),  # 设置为当前时间，模拟到期
    )


class TestSchedulerStatus:
    """调度器状态管理测试"""

    def test_initial_status_stopped(self, scheduler):
        """测试初始状态为已停止"""
        assert scheduler.status == SchedulerStatus.STOPPED
        assert scheduler.is_stopped() is True
        assert scheduler.is_running() is False

    def test_get_status_info(self, scheduler, mock_storage):
        """测试获取状态信息"""
        mock_storage.queue.count.return_value = 5
        mock_storage.scheduled.count.return_value = 3
        mock_storage.scheduled.enabled_count.return_value = 2
        mock_storage.running.count.return_value = 1

        info = scheduler.get_status_info()

        assert info["status"] == "stopped"
        assert info["queue_count"] == 5
        assert info["scheduled_count"] == 3
        assert info["enabled_scheduled_count"] == 2
        assert info["running_count"] == 1
        assert info["poll_interval"] == 1
        assert info["is_executing"] is False
        assert info["current_task_id"] is None
        assert "updated_at" in info

    def test_get_status_info_with_running_task(self, scheduler, mock_storage, mock_executor, sample_task):
        """测试运行中任务的状态信息"""
        mock_executor.is_executing.return_value = True
        mock_executor.get_current_task.return_value = sample_task

        info = scheduler.get_status_info()

        assert info["is_executing"] is True
        assert info["current_task_id"] == sample_task.id


class TestSchedulerStartStop:
    """调度器启动/停止测试"""

    @pytest.mark.asyncio
    async def test_start_scheduler(self, scheduler):
        """测试启动调度器"""
        result = await scheduler.start()

        assert result is True
        assert scheduler.status == SchedulerStatus.RUNNING
        assert scheduler.is_running() is True

        # 清理
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_start_already_running(self, scheduler):
        """测试重复启动"""
        await scheduler.start()

        result = await scheduler.start()

        assert result is False
        assert scheduler.status == SchedulerStatus.RUNNING

        # 清理
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_stop_scheduler(self, scheduler):
        """测试停止调度器"""
        await scheduler.start()
        result = await scheduler.stop()

        assert result is True
        assert scheduler.status == SchedulerStatus.STOPPED
        assert scheduler.is_stopped() is True

    @pytest.mark.asyncio
    async def test_stop_already_stopped(self, scheduler):
        """测试重复停止"""
        result = await scheduler.stop()

        assert result is False
        assert scheduler.status == SchedulerStatus.STOPPED

    @pytest.mark.asyncio
    async def test_start_stop_cycle(self, scheduler):
        """测试启动-停止循环"""
        # 第一次启动
        result1 = await scheduler.start()
        assert result1 is True
        assert scheduler.is_running() is True

        # 停止
        result2 = await scheduler.stop()
        assert result2 is True
        assert scheduler.is_stopped() is True

        # 再次启动
        result3 = await scheduler.start()
        assert result3 is True
        assert scheduler.is_running() is True

        # 清理
        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_stop_waits_for_loop(self, scheduler, mock_storage, mock_executor):
        """测试停止会等待循环结束"""
        # 启动调度器
        await scheduler.start()

        # 等待循环开始
        await asyncio.sleep(0.1)

        # 停止应该等待循环结束
        stop_task = asyncio.create_task(scheduler.stop())
        await asyncio.sleep(0.1)

        # 等待停止完成
        await stop_task

        # 验证最终状态是已停止
        assert scheduler.status == SchedulerStatus.STOPPED


class TestScheduledTaskTrigger:
    """定时任务到期触发测试"""

    @pytest.mark.asyncio
    async def test_trigger_scheduled_task(self, scheduler, mock_storage, sample_scheduled_task):
        """测试触发定时任务"""
        mock_storage.scheduled.get_enabled.return_value = [sample_scheduled_task]

        await scheduler._trigger_scheduled_task(sample_scheduled_task)

        # 验证任务被加入队列
        mock_storage.queue.add.assert_called_once()
        added_task = mock_storage.queue.add.call_args[0][0]
        assert added_task.prompt == sample_scheduled_task.prompt
        assert added_task.workspace == sample_scheduled_task.workspace

        # 验证定时任务更新
        assert sample_scheduled_task.last_run is not None
        assert sample_scheduled_task.run_count == 1
        mock_storage.scheduled.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_scheduled_tasks_due(self, scheduler, mock_storage, sample_scheduled_task):
        """测试检查到期的定时任务"""
        # 设置定时任务已到期（next_run 是过去的时间）
        past_time = datetime.now() - timedelta(minutes=1)
        sample_scheduled_task.next_run = past_time.isoformat()

        mock_storage.scheduled.get_enabled.return_value = [sample_scheduled_task]

        await scheduler._check_scheduled_tasks()

        # 验证任务被触发
        mock_storage.queue.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_scheduled_tasks_not_due(self, scheduler, mock_storage, sample_scheduled_task):
        """测试未到期的定时任务"""
        # 设置定时任务未到期（next_run 是未来的时间）
        future_time = datetime.now() + timedelta(hours=1)
        sample_scheduled_task.next_run = future_time.isoformat()

        mock_storage.scheduled.get_enabled.return_value = [sample_scheduled_task]

        await scheduler._check_scheduled_tasks()

        # 验证任务未被触发
        mock_storage.queue.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_scheduled_tasks_disabled(self, scheduler, mock_storage, sample_scheduled_task):
        """测试已禁用的定时任务"""
        sample_scheduled_task.enabled = False

        mock_storage.scheduled.get_enabled.return_value = []

        await scheduler._check_scheduled_tasks()

        # 验证任务未被触发
        mock_storage.queue.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_multiple_scheduled_tasks(self, scheduler, mock_storage):
        """测试多个到期定时任务"""
        tasks = []
        for i in range(3):
            task = ScheduledTask(
                id=str(uuid.uuid4()),
                name=f"定时任务 {i}",
                prompt=f"任务描述 {i}",
                cron="* * * * *",
                workspace="/test/workspace",
                timeout=60000,
                enabled=True,
                next_run=datetime.now().isoformat(),
            )
            tasks.append(task)

        mock_storage.scheduled.get_enabled.return_value = tasks

        await scheduler._check_scheduled_tasks()

        # 验证所有任务都被触发
        assert mock_storage.queue.add.call_count == 3

    @pytest.mark.asyncio
    async def test_check_scheduled_tasks_stops_on_signal(self, scheduler, mock_storage, sample_scheduled_task):
        """测试收到停止信号时中断检查"""
        mock_storage.scheduled.get_enabled.return_value = [sample_scheduled_task] * 10

        # 设置停止信号
        scheduler._stop_event.set()

        await scheduler._check_scheduled_tasks()

        # 验证没有任务被触发（因为立即退出）
        mock_storage.queue.add.assert_not_called()


class TestQueueProcessing:
    """队列任务执行测试"""

    @pytest.mark.asyncio
    async def test_process_queue_with_task(self, scheduler, mock_storage, mock_executor, sample_task):
        """测试处理队列中的任务"""
        mock_storage.queue.pop.return_value = sample_task

        await scheduler._process_queue()

        # 验证执行器被调用
        mock_executor.execute.assert_called_once_with(sample_task)

    @pytest.mark.asyncio
    async def test_process_queue_empty(self, scheduler, mock_storage, mock_executor):
        """测试空队列"""
        mock_storage.queue.pop.return_value = None

        await scheduler._process_queue()

        # 验证执行器未被调用
        mock_executor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_queue_already_executing(self, scheduler, mock_storage, mock_executor, sample_task):
        """测试执行中时跳过"""
        mock_executor.is_executing.return_value = True
        mock_storage.queue.pop.return_value = sample_task

        await scheduler._process_queue()

        # 验证跳过执行
        mock_executor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_task_success(self, scheduler, mock_storage, mock_executor, sample_task):
        """测试任务执行成功"""
        mock_executor.execute.return_value = ExecutionResult(
            success=True,
            message="执行成功",
            cost_usd=0.05,
            duration_ms=5000,
        )

        result = await scheduler._execute_task(sample_task)

        mock_executor.execute.assert_called_once_with(sample_task)

    @pytest.mark.asyncio
    async def test_execute_task_failure(self, scheduler, mock_storage, mock_executor, sample_task):
        """测试任务执行失败"""
        mock_executor.execute.return_value = ExecutionResult(
            success=False,
            message="执行失败",
            error="测试错误",
        )

        result = await scheduler._execute_task(sample_task)

        mock_executor.execute.assert_called_once_with(sample_task)

    @pytest.mark.asyncio
    async def test_execute_task_exception(self, scheduler, mock_storage, mock_executor, sample_task):
        """测试任务执行异常"""
        mock_executor.execute.side_effect = RuntimeError("执行异常")
        sample_task.status = TaskStatus.RUNNING

        # 异常应该被捕获并处理
        await scheduler._execute_task(sample_task)

        # 验证任务状态被设置为失败
        assert sample_task.status == TaskStatus.FAILED
        mock_storage.running.remove.assert_called_once_with(sample_task.id)
        mock_storage.history.add_failed.assert_called_once()


class TestRunLoop:
    """调度循环测试"""

    @pytest.mark.asyncio
    async def test_run_loop_processes_queue(self, scheduler, mock_storage, mock_executor, sample_task):
        """测试循环处理队列任务"""
        pop_count = 0

        def mock_pop():
            nonlocal pop_count
            pop_count += 1
            if pop_count == 1:
                return sample_task
            # 第一次之后返回 None，让循环继续
            return None

        mock_storage.queue.pop.side_effect = mock_pop

        # 启动调度器
        await scheduler.start()

        # 等待第一次处理
        await asyncio.sleep(0.5)

        # 停止调度器
        await scheduler.stop()

        # 验证任务被执行
        mock_executor.execute.assert_called()

    @pytest.mark.asyncio
    async def test_run_loop_checks_scheduled_tasks(self, scheduler, mock_storage, mock_executor, sample_scheduled_task):
        """测试循环检查定时任务"""
        check_count = 0

        def mock_get_enabled():
            nonlocal check_count
            check_count += 1
            return [sample_scheduled_task] if check_count == 1 else []

        mock_storage.scheduled.get_enabled.side_effect = mock_get_enabled

        # 启动调度器
        await scheduler.start()

        # 等待检查
        await asyncio.sleep(0.5)

        # 停止调度器
        await scheduler.stop()

        # 验证定时任务被检查
        mock_storage.scheduled.get_enabled.assert_called()

    @pytest.mark.asyncio
    async def test_run_loop_continues_on_exception(self, scheduler, mock_storage, mock_executor):
        """测试循环在异常时继续运行"""
        call_count = 0

        def mock_pop():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("模拟异常")
            return None

        mock_storage.queue.pop.side_effect = mock_pop

        # 启动调度器
        await scheduler.start()

        # 等待第一次处理（会抛出异常）
        await asyncio.sleep(0.5)

        # 验证调度器仍在运行
        assert scheduler.is_running() is True

        # 停止调度器
        await scheduler.stop()


class TestRunTaskNow:
    """立即执行任务测试"""

    def test_run_task_now_found(self, scheduler, mock_storage, sample_task):
        """测试立即执行存在的任务"""
        mock_storage.queue.get.return_value = sample_task

        result = scheduler.run_task_now(sample_task.id)

        assert result == sample_task
        mock_storage.queue.get.assert_called_once_with(sample_task.id)

    def test_run_task_now_not_found(self, scheduler, mock_storage):
        """测试立即执行不存在的任务"""
        mock_storage.queue.get.return_value = None

        result = scheduler.run_task_now("non-existent-id")

        assert result is None

    def test_run_scheduled_now(self, scheduler, mock_storage, sample_scheduled_task):
        """测试立即执行定时任务"""
        mock_storage.scheduled.get.return_value = sample_scheduled_task

        result = scheduler.run_scheduled_now(sample_scheduled_task.id)

        assert result is not None
        assert result.prompt == sample_scheduled_task.prompt
        mock_storage.queue.add.assert_called_once()

    def test_run_scheduled_now_not_found(self, scheduler, mock_storage):
        """测试立即执行不存在的定时任务"""
        mock_storage.scheduled.get.return_value = None

        result = scheduler.run_scheduled_now("non-existent-id")

        assert result is None


class TestGlobalFunctions:
    """全局函数测试"""

    def test_get_scheduler_singleton(self):
        """测试获取调度器单例"""
        # 重置单例
        import app.scheduler.scheduler as scheduler_module
        scheduler_module._scheduler = None

        scheduler1 = get_scheduler()
        scheduler2 = get_scheduler()

        assert scheduler1 is scheduler2

    @pytest.mark.asyncio
    async def test_start_scheduler_function(self):
        """测试全局启动函数"""
        import app.scheduler.scheduler as scheduler_module
        scheduler_module._scheduler = None

        result = await start_scheduler()

        assert result is True

        # 清理
        await stop_scheduler()

    @pytest.mark.asyncio
    async def test_stop_scheduler_function(self):
        """测试全局停止函数"""
        import app.scheduler.scheduler as scheduler_module
        scheduler_module._scheduler = None

        await start_scheduler()
        result = await stop_scheduler()

        assert result is True

    @pytest.mark.asyncio
    async def test_stop_scheduler_when_none(self):
        """测试调度器为 None 时停止"""
        import app.scheduler.scheduler as scheduler_module
        scheduler_module._scheduler = None

        result = await stop_scheduler()

        assert result is False
