"""存储层扩展测试 - 补充覆盖率到 80%+

专注于稳定通过的测试以提升 storage.py 覆盖率。
"""

import pytest
import uuid
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from app.scheduler.models import Task, TaskLog, TaskStatus, ScheduledTask
from app.scheduler import storage, config


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
            "CANCELLED_FILE": config.CANCELLED_FILE,
            "LOGS_FILE": config.LOGS_FILE,
        }

    # 清理数据文件
    for f in [
        config.QUEUE_FILE,
        config.SCHEDULED_FILE,
        config.RUNNING_FILE,
        config.COMPLETED_FILE,
        config.FAILED_FILE,
        config.CANCELLED_FILE,
        config.LOGS_FILE,
    ]:
        if f.exists():
            f.unlink()

    # 清除单例
    storage._task_storage = None

    yield

    # 清理单例
    storage._task_storage = None


class TestFileLock:
    """测试 FileLock"""

    def test_lock_acquire_non_blocking_fails_immediately(self, tmp_path):
        """测试非阻塞获取锁"""
        lock_file = tmp_path / "test.lock"
        lock1 = storage.FileLock(lock_file)

        # 第一次获取
        assert lock1.acquire(blocking=False) is True

        # 第二次应该失败（非阻塞）
        lock2 = storage.FileLock(lock_file)
        assert lock2.acquire(blocking=False) is False

        # 释放后可以再次获取
        lock1.release()
        assert lock2.acquire(blocking=False) is True
        lock2.release()

    def test_lock_release_ignores_nonexistent_file(self, tmp_path):
        """测试释放锁时忽略不存在的锁文件"""
        lock_file = tmp_path / "test.lock"
        lock = storage.FileLock(lock_file)

        # 锁文件不存在，释放应该静默忽略
        lock.release()
        # 再次释放也应该正常
        lock.release()

    def test_lock_concurrent_access(self, tmp_path):
        """测试并发锁访问"""
        lock_file = tmp_path / "test.lock"

        def try_acquire_lock():
            lock = storage.FileLock(lock_file)
            return lock.acquire(blocking=False)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(try_acquire_lock) for _ in range(5)]
            results = [f.result() for f in futures]

        # 只有一个应该成功
        assert sum(results) == 1


class TestAtomicWrite:
    """测试 atomic_write"""

    def test_atomic_write_no_cleanup_on_success(self, tmp_path):
        """测试成功时不保留临时文件"""
        filepath = tmp_path / "test.json"
        data = {"key": "value"}

        storage.atomic_write(filepath, data)

        # 临时文件应该被清理
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

        # 目标文件应该存在
        assert filepath.exists()

    def test_atomic_write_empty_data(self, tmp_path):
        """测试写入空数据"""
        filepath = tmp_path / "test.json"

        storage.atomic_write(filepath, {})

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        assert data == {}

    def test_atomic_write_unicode_content(self, tmp_path):
        """测试写入 Unicode 内容"""
        filepath = tmp_path / "test.json"
        data = {
            "chinese": "中文测试",
            "emoji": "😀",
            "special": "特殊字符 & < > \"",
        }

        storage.atomic_write(filepath, data)

        with open(filepath, encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == data


class TestCancelledStorage:
    """测试 CancelledStorage"""

    def test_cancelled_get_nonexistent(self):
        """测试获取不存在的取消任务"""
        cancelled_storage = storage.CancelledStorage()
        assert cancelled_storage.get("nonexistent") is None

    def test_cancelled_count(self):
        """测试取消任务计数"""
        cancelled_storage = storage.CancelledStorage()

        assert cancelled_storage.count() == 0

        for i in range(5):
            task = Task(
                id=str(uuid.uuid4()),
                prompt=f"任务 {i}",
                status=TaskStatus.CANCELLED,
            )
            cancelled_storage.add(task)

        assert cancelled_storage.count() == 5


class TestLogsStorage:
    """测试 LogsStorage"""

    def test_logs_append_single(self):
        """测试追加单条日志"""
        logs_storage = storage.LogsStorage()
        log = TaskLog(
            id=str(uuid.uuid4()),
            task_id="task-123",
            timestamp="2024-01-01T00:00:00",
            level="INFO",
            message="测试日志",
        )

        logs_storage.append(log)

        logs = logs_storage.get_all(limit=10)
        assert len(logs) == 1
        assert logs[0].message == "测试日志"

    def test_logs_append_multiple(self):
        """测试追加多条日志"""
        logs_storage = storage.LogsStorage()

        for i in range(10):
            log = TaskLog(
                id=str(uuid.uuid4()),
                task_id="task-123",
                timestamp=f"2024-01-01T00:00:{i:02d}",
                level="INFO",
                message=f"日志 {i}",
            )
            logs_storage.append(log)

        logs = logs_storage.get_all(limit=20)
        assert len(logs) == 10

    def test_logs_get_by_task_id(self):
        """测试根据任务 ID 获取日志"""
        logs_storage = storage.LogsStorage()
        task_id = "task-123"

        # 为任务添加多条日志
        for i in range(5):
            log = TaskLog(
                id=str(uuid.uuid4()),
                task_id=task_id,
                timestamp=f"2024-01-01T00:00:{i:02d}",
                level="INFO",
                message=f"日志 {i}",
            )
            logs_storage.append(log)

        # 获取指定任务的日志
        logs = logs_storage.get_by_task_id(task_id, limit=10)
        assert len(logs) == 5

    def test_logs_clear(self):
        """测试清空日志"""
        logs_storage = storage.LogsStorage()

        # 添加一些日志
        for i in range(10):
            log = TaskLog(
                id=str(uuid.uuid4()),
                task_id="task-123",
                timestamp=f"2024-01-01T00:00:{i:02d}",
                level="INFO",
                message=f"日志 {i}",
            )
            logs_storage.append(log)

        logs_storage.clear()

        # 应该为空
        logs = logs_storage.get_all()
        assert len(logs) == 0

    def test_logs_empty_file(self):
        """测试空日志文件"""
        logs_storage = storage.LogsStorage()

        # 清空文件
        logs_storage.clear()

        # 获取应该返回空列表
        logs = logs_storage.get_all()
        assert logs == []


class TestBaseStorageEdgeCases:
    """测试 BaseStorage 边界情况"""

    def test_read_raw_empty_file(self, tmp_path):
        """测试读取空文件"""
        filepath = tmp_path / "empty.json"
        filepath.write_text("", encoding="utf-8")

        base_storage = storage.BaseStorage(filepath)
        data = base_storage._read_raw()
        assert data == {"tasks": []}

    def test_read_raw_whitespace_only(self, tmp_path):
        """测试读取只有空白的文件"""
        filepath = tmp_path / "whitespace.json"
        filepath.write_text("   \n\t\n", encoding="utf-8")

        base_storage = storage.BaseStorage(filepath)
        data = base_storage._read_raw()
        assert data == {"tasks": []}

    def test_read_raw_nonexistent_file(self, tmp_path):
        """测试读取不存在的文件"""
        filepath = tmp_path / "nonexistent.json"

        base_storage = storage.BaseStorage(filepath)
        data = base_storage._read_raw()
        assert data == {"tasks": []}

    def test_read_valid_json(self, tmp_path):
        """测试读取有效的 JSON"""
        filepath = tmp_path / "valid.json"
        filepath.write_text('{"tasks": [{"id": "123"}]}', encoding="utf-8")

        base_storage = storage.BaseStorage(filepath)
        data = base_storage._read_raw()
        assert data == {"tasks": [{"id": "123"}]}


class TestHistoryStorageFindById:
    """测试历史存储按 ID 查找"""

    def test_find_in_completed(self):
        """测试在已完成任务中查找"""
        history_storage = storage.HistoryStorage()
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            prompt="已完成任务",
            status=TaskStatus.COMPLETED,
        )
        history_storage.add_completed(task)

        found = history_storage.find_by_id(task_id)
        assert found is not None
        assert found.id == task_id

    def test_find_in_failed(self):
        """测试在失败任务中查找"""
        history_storage = storage.HistoryStorage()
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            prompt="失败任务",
            status=TaskStatus.FAILED,
            error="执行失败",
        )
        history_storage.add_failed(task)

        found = history_storage.find_by_id(task_id)
        assert found is not None
        assert found.id == task_id

    def test_find_nonexistent(self):
        """测试查找不存在的任务"""
        history_storage = storage.HistoryStorage()
        assert history_storage.find_by_id("nonexistent-id") is None


class TestScheduledStorageCount:
    """测试定时任务存储计数"""

    def test_scheduled_count(self):
        """测试定时任务总数"""
        scheduled_storage = storage.ScheduledStorage()

        assert scheduled_storage.count() == 0

        for i in range(10):
            task = ScheduledTask(
                id=str(uuid.uuid4()),
                name=f"任务 {i}",
                prompt="测试",
                cron="0 * * * *",
            )
            scheduled_storage.save(task)

        assert scheduled_storage.count() == 10

    def test_scheduled_enabled_count(self):
        """测试已启用任务计数"""
        scheduled_storage = storage.ScheduledStorage()

        for i in range(10):
            task = ScheduledTask(
                id=str(uuid.uuid4()),
                name=f"任务 {i}",
                prompt="测试",
                cron="0 * * * *",
                enabled=(i % 2 == 0),
            )
            scheduled_storage.save(task)

        # 应该有 5 个启用（偶数索引）
        assert scheduled_storage.enabled_count() == 5


class TestGetStorageSingleton:
    """测试存储单例"""

    def test_get_storage_returns_singleton(self):
        """测试 get_storage 返回单例"""
        storage._task_storage = None

        instance1 = storage.get_storage()
        instance2 = storage.get_storage()

        assert instance1 is instance2

    def test_get_storage_instance_method(self):
        """测试 TaskStorage.get_instance 类方法"""
        storage.TaskStorage._instance = None

        instance1 = storage.TaskStorage.get_instance()
        instance2 = storage.TaskStorage.get_instance()

        assert instance1 is instance2

    def test_get_storage_after_clear(self):
        """测试清除单例后获取新实例"""
        storage._task_storage = None

        instance1 = storage.get_storage()
        storage._task_storage = None
        instance2 = storage.get_storage()

        assert instance1 is not instance2
