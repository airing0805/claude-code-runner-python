"""存储层单元测试"""

import pytest
import uuid
import json
from pathlib import Path

from app.scheduler.models import Task, ScheduledTask, TaskStatus
from app.scheduler import storage
from app.scheduler import config


# 备份原始文件路径
_original_files = {}


@pytest.fixture(autouse=True)
def clean_data_dir():
    """每个测试前后清理数据目录"""
    global _original_files

    # 备份原始文件
    if not _original_files:
        _original_files = {
            "QUEUE_FILE": config.QUEUE_FILE,
            "SCHEDULED_FILE": config.SCHEDULED_FILE,
            "RUNNING_FILE": config.RUNNING_FILE,
            "COMPLETED_FILE": config.COMPLETED_FILE,
            "FAILED_FILE": config.FAILED_FILE,
        }

    # 清理数据文件
    for f in [config.QUEUE_FILE, config.SCHEDULED_FILE, config.RUNNING_FILE,
              config.COMPLETED_FILE, config.FAILED_FILE]:
        if f.exists():
            f.unlink()

    # 清除单例
    storage._task_storage = None

    yield

    # 清理单例
    storage._task_storage = None


class TestQueueStorage:
    """队列存储测试"""

    def test_add_task_to_queue(self):
        """测试添加任务到队列"""
        queue_storage = storage.QueueStorage()
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试任务",
            workspace="/test",
        )

        queue_storage.add(task)

        tasks = queue_storage.get_all()
        assert len(tasks) == 1
        assert tasks[0].prompt == "测试任务"

    def test_get_all_tasks_from_queue(self):
        """测试获取队列所有任务"""
        queue_storage = storage.QueueStorage()

        # 添加多个任务
        for i in range(3):
            task = Task(
                id=str(uuid.uuid4()),
                prompt=f"任务 {i}",
            )
            queue_storage.add(task)

        tasks = queue_storage.get_all()
        assert len(tasks) == 3

    def test_get_task_by_id(self):
        """测试根据 ID 获取任务"""
        queue_storage = storage.QueueStorage()
        task_id = str(uuid.uuid4())
        task = Task(id=task_id, prompt="测试任务")
        queue_storage.add(task)

        retrieved = queue_storage.get(task_id)
        assert retrieved is not None
        assert retrieved.id == task_id
        assert retrieved.prompt == "测试任务"

    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        queue_storage = storage.QueueStorage()

        result = queue_storage.get("nonexistent-id")
        assert result is None

    def test_remove_task_from_queue(self):
        """测试从队列移除任务"""
        queue_storage = storage.QueueStorage()
        task_id = str(uuid.uuid4())
        task = Task(id=task_id, prompt="测试任务")
        queue_storage.add(task)

        removed = queue_storage.remove(task_id)
        assert removed is True

        tasks = queue_storage.get_all()
        assert len(tasks) == 0

    def test_pop_task_from_queue(self):
        """测试弹出队首任务"""
        queue_storage = storage.QueueStorage()

        # 添加多个任务
        for i in range(3):
            task = Task(
                id=str(uuid.uuid4()),
                prompt=f"任务 {i}",
            )
            queue_storage.add(task)

        # 弹出队首
        popped = queue_storage.pop()
        assert popped is not None
        assert popped.prompt == "任务 0"

        # 再次获取应该少一个
        tasks = queue_storage.get_all()
        assert len(tasks) == 2

    def test_pop_empty_queue(self):
        """测试弹出空队列"""
        queue_storage = storage.QueueStorage()

        result = queue_storage.pop()
        assert result is None

    def test_clear_queue(self):
        """测试清空队列"""
        queue_storage = storage.QueueStorage()

        # 添加任务
        for i in range(5):
            task = Task(id=str(uuid.uuid4()), prompt=f"任务 {i}")
            queue_storage.add(task)

        queue_storage.clear()

        tasks = queue_storage.get_all()
        assert len(tasks) == 0

    def test_queue_count(self):
        """测试队列计数"""
        queue_storage = storage.QueueStorage()

        assert queue_storage.count() == 0

        for i in range(3):
            task = Task(id=str(uuid.uuid4()), prompt=f"任务 {i}")
            queue_storage.add(task)

        assert queue_storage.count() == 3


class TestScheduledStorage:
    """定时任务存储测试"""

    def test_save_scheduled_task(self):
        """测试保存定时任务"""
        scheduled_storage = storage.ScheduledStorage()
        task = ScheduledTask(
            id=str(uuid.uuid4()),
            name="定时任务",
            prompt="测试",
            cron="0 * * * *",
        )

        scheduled_storage.save(task)

        tasks = scheduled_storage.get_all()
        assert len(tasks) == 1
        assert tasks[0].name == "定时任务"

    def test_update_scheduled_task(self):
        """测试更新定时任务"""
        scheduled_storage = storage.ScheduledStorage()
        task_id = str(uuid.uuid4())
        task = ScheduledTask(
            id=task_id,
            name="原名称",
            prompt="测试",
            cron="0 * * * *",
        )
        scheduled_storage.save(task)

        # 更新任务
        task.name = "新名称"
        task.enabled = False
        scheduled_storage.save(task)

        retrieved = scheduled_storage.get(task_id)
        assert retrieved.name == "新名称"
        assert retrieved.enabled is False

    def test_get_enabled_tasks(self):
        """测试获取已启用任务"""
        scheduled_storage = storage.ScheduledStorage()

        # 添加多个任务，部分启用
        for i in range(5):
            task = ScheduledTask(
                id=str(uuid.uuid4()),
                name=f"任务 {i}",
                prompt="测试",
                cron="0 * * * *",
                enabled=(i % 2 == 0),
            )
            scheduled_storage.save(task)

        enabled = scheduled_storage.get_enabled()
        assert len(enabled) == 3  # 0, 2, 4 启用

    def test_delete_scheduled_task(self):
        """测试删除定时任务"""
        scheduled_storage = storage.ScheduledStorage()
        task_id = str(uuid.uuid4())
        task = ScheduledTask(
            id=task_id,
            name="测试",
            prompt="测试",
            cron="0 * * * *",
        )
        scheduled_storage.save(task)

        deleted = scheduled_storage.delete(task_id)
        assert deleted is True

        tasks = scheduled_storage.get_all()
        assert len(tasks) == 0


class TestRunningStorage:
    """运行中任务存储测试"""

    def test_add_running_task(self):
        """测试添加运行中任务"""
        running_storage = storage.RunningStorage()
        task = Task(
            id=str(uuid.uuid4()),
            prompt="运行中任务",
            status=TaskStatus.RUNNING,
        )

        running_storage.add(task)

        tasks = running_storage.get_all()
        assert len(tasks) == 1
        assert tasks[0].status == TaskStatus.RUNNING

    def test_update_running_task(self):
        """测试更新运行中任务"""
        running_storage = storage.RunningStorage()
        task_id = str(uuid.uuid4())
        task = Task(id=task_id, prompt="运行中", status=TaskStatus.RUNNING)
        running_storage.add(task)

        # 更新任务
        task.status = TaskStatus.COMPLETED
        task.files_changed = ["/test/file.py"]
        running_storage.update(task)

        retrieved = running_storage.get(task_id)
        assert retrieved.status == TaskStatus.COMPLETED
        assert "/test/file.py" in retrieved.files_changed

    def test_remove_running_task(self):
        """测试移除运行中任务"""
        running_storage = storage.RunningStorage()
        task_id = str(uuid.uuid4())
        task = Task(id=task_id, prompt="运行中", status=TaskStatus.RUNNING)
        running_storage.add(task)

        removed = running_storage.remove(task_id)
        assert removed is not None
        assert removed.id == task_id

        tasks = running_storage.get_all()
        assert len(tasks) == 0


class TestHistoryStorage:
    """历史任务存储测试"""

    def test_add_completed_task(self):
        """测试添加已完成任务"""
        history_storage = storage.HistoryStorage()
        task = Task(
            id=str(uuid.uuid4()),
            prompt="已完成任务",
            status=TaskStatus.COMPLETED,
        )

        history_storage.add_completed(task)

        result = history_storage.get_completed()
        assert len(result.items) == 1
        assert result.items[0]["prompt"] == "已完成任务"

    def test_add_failed_task(self):
        """测试添加失败任务"""
        history_storage = storage.HistoryStorage()
        task = Task(
            id=str(uuid.uuid4()),
            prompt="失败任务",
            status=TaskStatus.FAILED,
            error="执行失败",
        )

        history_storage.add_failed(task)

        result = history_storage.get_failed()
        assert len(result.items) == 1
        assert result.items[0]["error"] == "执行失败"

    def test_completed_tasks_sorted_by_time(self):
        """测试已完成任务按时间排序"""
        history_storage = storage.HistoryStorage()

        # 添加多个任务
        for i in range(5):
            task = Task(
                id=str(uuid.uuid4()),
                prompt=f"任务 {i}",
                status=TaskStatus.COMPLETED,
            )
            history_storage.add_completed(task)

        result = history_storage.get_completed()
        # 最新添加的应该在最前面
        assert result.items[0]["prompt"] == "任务 4"

    def test_get_completed_pagination(self):
        """测试已完成任务分页"""
        history_storage = storage.HistoryStorage()

        # 添加 25 个任务
        for i in range(25):
            task = Task(
                id=str(uuid.uuid4()),
                prompt=f"任务 {i}",
                status=TaskStatus.COMPLETED,
            )
            history_storage.add_completed(task)

        # 第一页
        page1 = history_storage.get_completed(page=1, limit=10)
        assert len(page1.items) == 10
        assert page1.total == 25
        assert page1.pages == 3

        # 第二页
        page2 = history_storage.get_completed(page=2, limit=10)
        assert len(page2.items) == 10

        # 第三页
        page3 = history_storage.get_completed(page=3, limit=10)
        assert len(page3.items) == 5


class TestFileLock:
    """文件锁测试"""

    def test_lock_acquire_release(self, tmp_path):
        """测试锁获取和释放"""
        lock_file = tmp_path / "test.lock"
        lock = storage.FileLock(lock_file)

        # 获取锁
        acquired = lock.acquire()
        assert acquired is True

        # 释放锁
        lock.release()
        assert not lock_file.with_suffix(".lock").exists()

    def test_lock_non_blocking(self, tmp_path):
        """测试非阻塞获取锁"""
        lock_file = tmp_path / "test.lock"
        lock = storage.FileLock(lock_file)

        # 第一次获取
        assert lock.acquire(blocking=False) is True

        # 第二次应该失败（非阻塞）
        lock2 = storage.FileLock(lock_file)
        assert lock2.acquire(blocking=False) is False

        # 释放后可以再次获取
        lock.release()
        assert lock2.acquire(blocking=False) is True
        lock2.release()


class TestAtomicWrite:
    """原子写入测试"""

    def test_atomic_write_read(self, tmp_path):
        """测试原子写入和读取"""
        filepath = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        storage.atomic_write(filepath, data)

        # 验证写入的数据
        with open(filepath, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == data

    def test_atomic_write_overwrite(self, tmp_path):
        """测试原子覆盖写入"""
        filepath = tmp_path / "test.json"

        # 第一次写入
        storage.atomic_write(filepath, {"version": 1})
        # 第二次写入
        storage.atomic_write(filepath, {"version": 2})

        with open(filepath, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == {"version": 2}


class TestTaskStorage:
    """统一存储接口测试"""

    def test_get_storage_instance(self):
        """测试获取存储实例"""
        # 清除单例
        storage._task_storage = None
        task_storage = storage.get_storage()

        assert task_storage is not None
        assert task_storage.queue is not None
        assert task_storage.scheduled is not None
        assert task_storage.running is not None
        assert task_storage.history is not None
