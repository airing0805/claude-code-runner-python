"""任务调度存储层

提供 JSON 文件存储、并发安全、原子写入等功能。
"""

import json
import os
import tempfile
import time
import msvcrt
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from app.scheduler.config import (
    DATA_DIR,
    QUEUE_FILE,
    SCHEDULED_FILE,
    RUNNING_FILE,
    COMPLETED_FILE,
    FAILED_FILE,
    MAX_HISTORY,
    LOCK_TIMEOUT,
    LOCK_RETRY_INTERVAL,
    MAX_LOCK_RETRIES,
)
from app.scheduler.models import PaginatedResponse, Task, ScheduledTask


class FileLock:
    """文件锁实现（简化版，使用原子文件创建）"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.lock_path = filepath.with_suffix(filepath.suffix + ".lock")

    def acquire(self, blocking: bool = True) -> bool:
        """获取文件锁"""
        import time

        retries = 0
        max_retries = MAX_LOCK_RETRIES if blocking else 10

        while retries < max_retries:
            try:
                # 尝试创建锁文件（原子操作）
                fd = os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
                os.close(fd)
                return True
            except FileExistsError:
                # 锁文件已存在
                if not blocking:
                    return False
                time.sleep(LOCK_RETRY_INTERVAL)
                retries += 1
            except OSError:
                time.sleep(LOCK_RETRY_INTERVAL)
                retries += 1

        return False

    def release(self) -> None:
        """释放文件锁"""
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except OSError:
            pass

    def __enter__(self) -> "FileLock":
        if not self.acquire():
            raise RuntimeError(f"Failed to acquire lock for {self.filepath}")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()


@contextmanager
def file_lock(lock: FileLock):
    """文件锁上下文管理器"""
    lock.acquire()
    try:
        yield
    finally:
        lock.release()


def atomic_write(filepath: Path, data: dict) -> None:
    """原子写入 JSON 文件"""
    # 创建临时文件
    fd, temp_path = tempfile.mkstemp(
        dir=filepath.parent,
        suffix=".tmp",
    )

    try:
        # 写入临时文件
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 原子重命名
        os.replace(temp_path, filepath)
    except Exception:
        # 失败时删除临时文件
        if Path(temp_path).exists():
            Path(temp_path).unlink()
        raise


class BaseStorage:
    """JSON 文件存储基类"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.lock = FileLock(filepath)

    def _read_raw(self) -> dict:
        """读取原始数据（不加锁）"""
        if not self.filepath.exists():
            return {"tasks": []}
        content = self.filepath.read_text(encoding="utf-8")
        if not content.strip():
            return {"tasks": []}
        return json.loads(content)

    def _read(self) -> dict:
        """读取数据（加锁）"""
        with self.lock:
            return self._read_raw()

    def _write_raw(self, data: dict) -> None:
        """写入原始数据（不加锁）"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self.filepath, data)

    def _write(self, data: dict) -> None:
        """写入数据（加锁和原子操作）"""
        with self.lock:
            self._write_raw(data)


class QueueStorage(BaseStorage):
    """任务队列存储"""

    def __init__(self):
        super().__init__(QUEUE_FILE)
        self._ensure_init()

    def _ensure_init(self) -> None:
        """确保文件存在"""
        if not self.filepath.exists():
            self._write_raw({"tasks": []})

    def add(self, task: Task) -> None:
        """添加任务到队列"""
        data = self._read()
        data["tasks"].append(task.to_dict())
        self._write(data)

    def get_all(self) -> list[Task]:
        """获取所有队列任务"""
        data = self._read()
        return [Task.from_dict(t) for t in data.get("tasks", [])]

    def get(self, task_id: str) -> Optional[Task]:
        """获取指定任务"""
        tasks = self.get_all()
        for task in tasks:
            if task.id == task_id:
                return task
        return None

    def remove(self, task_id: str) -> bool:
        """从队列中移除任务"""
        data = self._read()
        original_count = len(data["tasks"])
        data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
        self._write(data)
        return len(data["tasks"]) < original_count

    def pop(self) -> Optional[Task]:
        """弹出队首任务（FIFO）"""
        data = self._read()
        if not data.get("tasks"):
            return None
        task_data = data["tasks"].pop(0)
        self._write(data)
        return Task.from_dict(task_data)

    def clear(self) -> None:
        """清空队列"""
        self._write({"tasks": []})

    def count(self) -> int:
        """获取队列任务数量"""
        data = self._read()
        return len(data.get("tasks", []))


class ScheduledStorage(BaseStorage):
    """定时任务存储"""

    def __init__(self):
        super().__init__(SCHEDULED_FILE)
        self._ensure_init()

    def _ensure_init(self) -> None:
        """确保文件存在"""
        if not self.filepath.exists():
            self._write_raw({"tasks": []})

    def save(self, task: ScheduledTask) -> None:
        """保存或更新定时任务"""
        data = self._read()
        tasks = data.get("tasks", [])

        # 查找并更新或添加
        found = False
        for i, t in enumerate(tasks):
            if t["id"] == task.id:
                tasks[i] = task.to_dict()
                found = True
                break

        if not found:
            tasks.append(task.to_dict())

        self._write({"tasks": tasks})

    def get_all(self) -> list[ScheduledTask]:
        """获取所有定时任务"""
        data = self._read()
        return [ScheduledTask.from_dict(t) for t in data.get("tasks", [])]

    def get(self, task_id: str) -> Optional[ScheduledTask]:
        """获取指定定时任务"""
        tasks = self.get_all()
        for task in tasks:
            if task.id == task_id:
                return task
        return None

    def delete(self, task_id: str) -> bool:
        """删除定时任务"""
        data = self._read()
        original_count = len(data.get("tasks", []))
        data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
        self._write(data)
        return len(data["tasks"]) < original_count

    def get_enabled(self) -> list[ScheduledTask]:
        """获取所有已启用的定时任务"""
        return [t for t in self.get_all() if t.enabled]

    def count(self) -> int:
        """获取定时任务数量"""
        data = self._read()
        return len(data.get("tasks", []))

    def enabled_count(self) -> int:
        """获取已启用定时任务数量"""
        return len(self.get_enabled())


class RunningStorage(BaseStorage):
    """运行中任务存储"""

    def __init__(self):
        super().__init__(RUNNING_FILE)
        self._ensure_init()

    def _ensure_init(self) -> None:
        """确保文件存在"""
        if not self.filepath.exists():
            self._write_raw({"tasks": []})

    def add(self, task: Task) -> None:
        """添加运行中的任务"""
        data = self._read()
        data["tasks"].append(task.to_dict())
        self._write(data)

    def get_all(self) -> list[Task]:
        """获取所有运行中任务"""
        data = self._read()
        return [Task.from_dict(t) for t in data.get("tasks", [])]

    def get(self, task_id: str) -> Optional[Task]:
        """获取指定运行中任务"""
        tasks = self.get_all()
        for task in tasks:
            if task.id == task_id:
                return task
        return None

    def remove(self, task_id: str) -> Optional[Task]:
        """移除运行中的任务"""
        data = self._read()
        removed_task = None
        for i, t in enumerate(data["tasks"]):
            if t["id"] == task_id:
                removed_task = Task.from_dict(t)
                data["tasks"].pop(i)
                break
        self._write(data)
        return removed_task

    def update(self, task: Task) -> None:
        """更新运行中的任务"""
        data = self._read()
        for i, t in enumerate(data["tasks"]):
            if t["id"] == task.id:
                data["tasks"][i] = task.to_dict()
                break
        self._write(data)

    def clear(self) -> None:
        """清空运行中任务"""
        self._write({"tasks": []})

    def count(self) -> int:
        """获取运行中任务数量"""
        data = self._read()
        return len(data.get("tasks", []))


class HistoryStorage(BaseStorage):
    """历史任务存储（已完成/失败）"""

    def __init__(self):
        # 使用不同的文件
        self.completed_filepath = COMPLETED_FILE
        self.failed_filepath = FAILED_FILE
        self._ensure_init()

    def _ensure_init(self) -> None:
        """确保文件存在"""
        if not self.completed_filepath.exists():
            self._write_history(self.completed_filepath, {"tasks": []})
        if not self.failed_filepath.exists():
            self._write_history(self.failed_filepath, {"tasks": []})

    def _read_history(self, filepath: Path) -> dict:
        """读取历史文件"""
        if not filepath.exists():
            return {"tasks": []}
        content = filepath.read_text(encoding="utf-8")
        if not content.strip():
            return {"tasks": []}
        return json.loads(content)

    def _write_history(self, filepath: Path, data: dict) -> None:
        """写入历史文件"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(filepath, data)

    def add_completed(self, task: Task) -> None:
        """添加已完成任务"""
        self._add(self.completed_filepath, task)

    def add_failed(self, task: Task) -> None:
        """添加失败任务"""
        self._add(self.failed_filepath, task)

    def _add(self, filepath: Path, task: Task) -> None:
        """添加任务到历史"""
        data = self._read_history(filepath)
        tasks = data.get("tasks", [])

        # 添加到列表开头（最新在前）
        tasks.insert(0, task.to_dict())

        # 限制历史记录数量
        if len(tasks) > MAX_HISTORY:
            tasks = tasks[:MAX_HISTORY]

        self._write_history(filepath, {"tasks": tasks})

    def get_completed(self, page: int = 1, limit: int = 20) -> PaginatedResponse:
        """获取已完成任务（分页）"""
        return self._get_paginated(self.completed_filepath, page, limit)

    def get_failed(self, page: int = 1, limit: int = 20) -> PaginatedResponse:
        """获取失败任务（分页）"""
        return self._get_paginated(self.failed_filepath, page, limit)

    def _get_paginated(
        self, filepath: Path, page: int, limit: int
    ) -> PaginatedResponse:
        """分页获取历史任务"""
        data = self._read_history(filepath)
        tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        total = len(tasks)

        offset = (page - 1) * limit
        items = tasks[offset : offset + limit]
        pages = (total + limit - 1) // limit if total > 0 else 1

        return PaginatedResponse(
            items=[t.to_dict() for t in items],
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )


class TaskStorage:
    """统一的任务存储接口"""

    def __init__(self):
        self.queue = QueueStorage()
        self.scheduled = ScheduledStorage()
        self.running = RunningStorage()
        self.history = HistoryStorage()

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
