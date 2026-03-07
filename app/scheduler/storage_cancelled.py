"""已取消任务存储模块"""

import json
from pathlib import Path
from typing import List

from .models import Task, PaginatedResponse
from .config import MAX_HISTORY


class CancelledStorage:
    """已取消任务存储"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self._ensure_init()

    def _ensure_init(self) -> None:
        """确保文件存在"""
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.write_text("", encoding="utf-8")

    def add(self, task: Task) -> None:
        """添加已取消任务"""
        data = self._read()
        tasks = data.get("tasks", [])

        # 添加到列表开头（最新在前）
        tasks.insert(0, task.to_dict())

        # 限制历史记录数量
        if len(tasks) > MAX_HISTORY:
            tasks = tasks[:MAX_HISTORY]

        self._write({"tasks": tasks})

    def get_all(self, page: int = 1, limit: int = 20) -> PaginatedResponse:
        """获取已取消任务（分页）"""
        data = self._read()
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

    def _read(self) -> dict:
        """读取数据"""
        if not self.filepath.exists():
            return {"tasks": []}
        content = self.filepath.read_text(encoding="utf-8")
        if not content.strip():
            return {"tasks": []}
        return json.loads(content)

    def _write(self, data: dict) -> None:
        """写入数据"""
        from .storage_base import atomic_write
        atomic_write(self.filepath, data)