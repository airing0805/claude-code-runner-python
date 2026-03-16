"""运行中任务存储模块"""

from typing import Optional, List

from .models import Task
from .storage_base import BaseStorage


class RunningStorage(BaseStorage):
    """运行中任务存储"""

    def __init__(self, filepath):
        super().__init__(filepath)
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

    def get_all(self) -> List[Task]:
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