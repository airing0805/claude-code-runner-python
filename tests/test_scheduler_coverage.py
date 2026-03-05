"""任务调度器覆盖率补充测试

此文件包含为提高测试覆盖率而补充的测试用例，专门针对未覆盖的代码路径。
"""

import pytest
import uuid
import json
from pathlib import Path
from datetime import datetime

from app.scheduler.models import (
    Task,
    ScheduledTask,
    TaskStatus,
    TaskSource,
)
from app.scheduler import storage, config


class TestQueueFullError:
    """QueueFullError 异常测试"""

    def test_queue_full_error_properties(self):
        """测试队列已满异常的属性"""
        error = storage.QueueFullError(current_size=100, max_size=100)
        assert error.current_size == 100
        assert error.max_size == 100
        assert "100/100" in str(error)


class TestQueueStorageMethods:
    """队列存储方法测试"""

    def test_queue_add_to_front(self):
        """测试添加到队列头部"""
        # 清空现有队列数据
        storage.QUEUE_FILE.write_text('{"tasks": []}', encoding="utf-8")

        queue_storage = storage.QueueStorage()

        # 添加任务1
        task1 = Task(id=str(uuid.uuid4()), prompt="任务1")
        queue_storage.add(task1)

        # 添加到头部
        task2 = Task(id=str(uuid.uuid4()), prompt="任务2")
        queue_storage.add_to_front(task2)

        tasks = queue_storage.get_all()
        assert len(tasks) == 2
        assert tasks[0].prompt == "任务2"
        assert tasks[1].prompt == "任务1"


class TestRunningStorageMethods:
    """运行中存储方法测试"""

    def test_running_storage_clear(self):
        """测试清空运行中任务"""
        running_storage = storage.RunningStorage()

        # 添加任务
        for i in range(3):
            task = Task(id=str(uuid.uuid4()), prompt=f"任务{i}")
            running_storage.add(task)

        running_storage.clear()
        assert running_storage.count() == 0

    def test_running_storage_count(self):
        """测试计数"""
        running_storage = storage.RunningStorage()
        assert running_storage.count() == 0

        task = Task(id=str(uuid.uuid4()), prompt="测试")
        running_storage.add(task)
        assert running_storage.count() == 1


class TestCompletedStorage:
    """已完成存储测试"""

    def test_completed_storage_get_failed_empty(self):
        """测试获取空的失败任务列表"""
        # 清空现有失败数据
        storage.FAILED_FILE.write_text('{"tasks": []}', encoding="utf-8")

        history_storage = storage.HistoryStorage()

        result = history_storage.get_failed()
        assert len(result.items) == 0
        assert result.total == 0


class TestCancelledStorageEdgeCases:
    """已取消任务存储边界情况测试"""

    def test_cancelled_storage_get_all(self):
        """测试获取所有已取消任务"""
        # 清空现有记录
        storage.CANCELLED_FILE.write_text('{"tasks": []}', encoding="utf-8")

        cancelled_storage = storage.CancelledStorage()

        # 添加多个任务
        for i in range(3):
            task = Task(
                id=str(uuid.uuid4()),
                prompt=f"任务 {i}",
                status=TaskStatus.CANCELLED,
            )
            cancelled_storage.add(task)

        tasks = cancelled_storage.get_all()
        assert len(tasks) == 3

    def test_cancelled_storage_get_by_id(self):
        """测试根据ID获取已取消任务"""
        cancelled_storage = storage.CancelledStorage()

        task_id = str(uuid.uuid4())
        task = Task(id=task_id, prompt="测试", status=TaskStatus.CANCELLED)
        cancelled_storage.add(task)

        retrieved = cancelled_storage.get(task_id)
        assert retrieved is not None
        assert retrieved.id == task_id

    def test_cancelled_storage_count(self):
        """测试已取消任务计数"""
        # 清空现有记录
        storage.CANCELLED_FILE.write_text('{"tasks": []}', encoding="utf-8")

        cancelled_storage = storage.CancelledStorage()

        assert cancelled_storage.count() == 0

        for i in range(5):
            task = Task(id=str(uuid.uuid4()), prompt=f"任务{i}", status=TaskStatus.CANCELLED)
            cancelled_storage.add(task)

        assert cancelled_storage.count() == 5

    def test_cancelled_storage_clear(self):
        """测试清空已取消任务"""
        # 清空现有记录
        storage.CANCELLED_FILE.write_text('{"tasks": []}', encoding="utf-8")

        cancelled_storage = storage.CancelledStorage()

        task = Task(id=str(uuid.uuid4()), prompt="测试", status=TaskStatus.CANCELLED)
        cancelled_storage.add(task)

        cancelled_storage.clear()
        assert cancelled_storage.count() == 0

    def test_cancelled_storage_limit_enforcement(self):
        """测试已取消任务存储限制"""
        # 清空现有记录
        storage.CANCELLED_FILE.write_text('{"tasks": []}', encoding="utf-8")

        cancelled_storage = storage.CancelledStorage()

        # 添加超过 MAX_HISTORY 的任务
        for i in range(storage.MAX_HISTORY + 10):
            task = Task(
                id=str(uuid.uuid4()),
                prompt=f"任务 {i}",
                status=TaskStatus.CANCELLED,
            )
            cancelled_storage.add(task)

        # 应该只保留 MAX_HISTORY 个
        tasks = cancelled_storage.get_all()
        assert len(tasks) <= storage.MAX_HISTORY


class TestHistoryStorageLimits:
    """历史存储限制测试"""

    def test_history_limit_on_add(self):
        """测试添加任务时历史记录限制"""
        history_storage = storage.HistoryStorage()

        # 清空现有记录
        storage.COMPLETED_FILE.write_text('{"tasks": []}', encoding="utf-8")

        # 添加超过 MAX_HISTORY 的已完成任务
        for i in range(storage.MAX_HISTORY + 5):
            task = Task(
                id=str(uuid.uuid4()),
                prompt=f"任务 {i}",
                status=TaskStatus.COMPLETED,
            )
            history_storage.add_completed(task)

        # 应该限制为 MAX_HISTORY
        result = history_storage.get_completed()
        assert len(result.items) <= storage.MAX_HISTORY

    def test_history_get_completed_empty(self):
        """测试获取空的已完成任务"""
        history_storage = storage.HistoryStorage()

        # 清空现有记录
        storage.COMPLETED_FILE.write_text('{"tasks": []}', encoding="utf-8")

        result = history_storage.get_completed()
        assert len(result.items) == 0
        assert result.total == 0

    def test_history_get_failed_pagination(self):
        """测试失败任务分页"""
        history_storage = storage.HistoryStorage()

        # 清空现有记录
        storage.FAILED_FILE.write_text('{"tasks": []}', encoding="utf-8")

        # 添加15个失败任务
        for i in range(15):
            task = Task(
                id=str(uuid.uuid4()),
                prompt=f"任务 {i}",
                status=TaskStatus.FAILED,
                error="错误",
            )
            history_storage.add_failed(task)

        # 第一页
        page1 = history_storage.get_failed(page=1, limit=10)
        assert len(page1.items) == 10
        assert page1.total == 15


class TestTaskStorageSingleton:
    """任务存储单例测试"""

    def test_get_storage_returns_singleton(self):
        """测试获取存储返回单例"""
        storage._task_storage = None

        storage1 = storage.get_storage()
        storage2 = storage.get_storage()

        assert storage1 is storage2


class TestStorageEdgeCases:
    """存储层边界情况测试"""

    def test_running_storage_update_nonexistent_task(self):
        """测试更新不存在的运行中任务"""
        running_storage = storage.RunningStorage()
        task = Task(id=str(uuid.uuid4()), prompt="不存在", status=TaskStatus.RUNNING)

        # 更新不存在的任务应该不抛出异常
        running_storage.update(task)  # 应该静默处理

    def test_running_storage_remove_nonexistent_task(self):
        """测试移除不存在的运行中任务"""
        running_storage = storage.RunningStorage()

        result = running_storage.remove("nonexistent-id")
        assert result is None


class TestModelsLegacyCompatibility:
    """模型旧数据兼容性测试"""

    def test_task_from_dict_with_legacy_scheduled_field(self):
        """测试从旧格式字典创建任务（scheduled 字段）"""
        data = {
            "id": "test-id",
            "prompt": "测试任务",
            "status": "pending",
            "scheduled": True,  # 旧字段
            "created_at": "2024-01-01T00:00:00",
        }

        task = Task.from_dict(data)

        assert task.source == TaskSource.SCHEDULED
        assert "scheduled" not in task.to_dict()

    def test_task_from_dict_with_legacy_not_scheduled(self):
        """测试从旧格式字典创建任务（scheduled=False）"""
        data = {
            "id": "test-id",
            "prompt": "测试任务",
            "status": "pending",
            "scheduled": False,  # 旧字段
            "created_at": "2024-01-01T00:00:00",
        }

        task = Task.from_dict(data)

        assert task.source == TaskSource.MANUAL
        assert "scheduled" not in task.to_dict()

    def test_task_from_dict_with_camel_case_fields(self):
        """测试从驼峰式字段创建任务"""
        data = {
            "id": "test-id",
            "prompt": "测试任务",
            "autoApprove": True,  # 驼峰式
            "allowedTools": ["Read", "Write"],
            "createdAt": "2024-01-01T00:00:00",
        }

        task = Task.from_dict(data)

        assert task.auto_approve is True
        assert task.allowed_tools == ["Read", "Write"]
        assert task.created_at == "2024-01-01T00:00:00"

    def test_scheduled_task_from_dict_without_name(self):
        """测试从无 name 字段的字典创建定时任务"""
        data = {
            "id": "test-id",
            "prompt": "测试任务",
            "cron": "0 * * * *",
        }

        task = ScheduledTask.from_dict(data)

        # 应该使用 id 作为默认 name
        assert task.name == "test-id"


class TestConfigFunctions:
    """配置模块函数测试"""

    def test_get_data_dir(self):
        """测试获取数据目录"""
        result = config.get_data_dir()
        assert result == config.DATA_DIR
        assert result.exists()

    def test_ensure_data_dir(self):
        """测试确保数据目录存在"""
        # 保存原始目录
        original_data_dir = config.DATA_DIR

        # 设置一个临时目录
        temp_dir = Path(__file__).parent / "temp_test_data"

        try:
            config.DATA_DIR = temp_dir
            config.ensure_data_dir()

            assert temp_dir.exists()
            assert temp_dir.is_dir()
        finally:
            # 恢复原始目录
            config.DATA_DIR = original_data_dir
            # 清理临时目录
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)


class TestBaseStorage:
    """BaseStorage 边界情况测试"""

    def test_base_storage_read_raw_with_tasks_key(self, tmp_path):
        """测试读取包含 tasks 键的文件"""
        file_path = tmp_path / "test.json"
        file_path.write_text('{"tasks": []}', encoding="utf-8")

        base = storage.BaseStorage(file_path)
        result = base._read_raw()
        assert result == {"tasks": []}
