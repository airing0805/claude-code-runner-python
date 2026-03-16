"""历史任务存储模块"""

import json
from pathlib import Path
from typing import List

from .models import Task, PaginatedResponse
from .config import MAX_HISTORY


class HistoryStorage:
    """历史任务存储（已完成/失败）"""

    def __init__(self, completed_filepath: Path, failed_filepath: Path):
        # 使用不同的文件
        self.completed_filepath = completed_filepath
        self.failed_filepath = failed_filepath
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
        from .storage_base import atomic_write
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