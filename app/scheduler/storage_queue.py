"""任务队列存储模块"""

import uuid
from typing import Optional, List

from .models import Task
from .storage_base import BaseStorage, _normalize_datetime_field


class QueueStorage(BaseStorage):
    """任务队列存储"""

    def __init__(self, filepath):
        super().__init__(filepath)
        self._ensure_init()

    def _ensure_init(self) -> None:
        """确保文件存在"""
        if not self.filepath.exists():
            self._write_raw({"tasks": []})

    def _read(self) -> dict:
        """读取数据，每次读取时自动修复数据一致性问题"""
        data = self._read_raw()
        tasks = data.get("tasks", [])
        tasks, changed = self._sanitize_tasks(tasks)
        if changed:
            self._write_raw({"tasks": tasks})
            from .storage_base import logger
            logger.info("[QueueStorage] 数据一致性修复完成，已回写文件")
        return {"tasks": tasks}

    def _sanitize_tasks(self, tasks: list) -> tuple[list, bool]:
        """修复队列任务列表中的数据一致性问题，返回 (修复后的列表, 是否有变更)

        修复规则：
        1. 重复 ID：同一 ID 出现多次时，为后续重复条目重新生成 UUID
           注意：只修改 id 字段，绝对不修改 prompt 及其他业务字段
        2. 时间字段格式：将 created_at/started_at/finished_at 统一为 'YYYY-MM-DD HH:MM:SS'
        """
        changed = False
        seen_ids: set[str] = set()

        for task in tasks:
            task_id = task.get("id", "")
            if task_id in seen_ids:
                new_id = str(uuid.uuid4())
                from .storage_base import logger
                logger.warning(
                    f"[QueueStorage] 发现重复ID，自动重新生成: '{task_id}' -> '{new_id}' "
                    f"(prompt前缀={str(task.get('prompt', ''))[:30]})"
                )
                task["id"] = new_id
                changed = True
            else:
                seen_ids.add(task_id)

            # --- 规则2: 统一时间字段格式 ---
            for field in ("created_at", "started_at", "finished_at"):
                if _normalize_datetime_field(task, field):
                    from .storage_base import logger
                    logger.debug(f"[QueueStorage] 时间格式已修正: id={task.get('id')}, field={field}")
                    changed = True

        return tasks, changed

    def add(self, task: Task) -> None:
        """添加任务到队列"""
        data = self._read()
        data["tasks"].append(task.to_dict())
        self._write(data)

    def add_to_front(self, task: Task) -> None:
        """添加任务到队列头部（优先处理）"""
        data = self._read()
        data["tasks"].insert(0, task.to_dict())
        self._write(data)

    def get_all(self) -> List[Task]:
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