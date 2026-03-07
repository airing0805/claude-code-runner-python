"""定时任务存储模块"""

import re
import uuid
from typing import Optional, List

from .models import ScheduledTask
from .storage_base import BaseStorage, _normalize_datetime_field


class ScheduledStorage(BaseStorage):
    """定时任务存储"""

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
            logger.info("[ScheduledStorage] 数据一致性修复完成，已回写文件")
        return {"tasks": tasks}

    def _sanitize_tasks(self, tasks: list) -> tuple[list, bool]:
        """修复任务列表中的数据一致性问题，返回 (修复后的列表, 是否有变更)

        修复规则：
        1. 重复 ID：同一 ID 出现多次时，从第 2 条起追加 -2、-3 ... 后缀，使每条记录拥有唯一 ID
        2. 过期 next_run：next_run 非空且时间早于当前时间时，清空为 null，由调度器重新计算
        3. 时间字段格式：将 created_at/updated_at/last_run/next_run 统一为 'YYYY-MM-DD HH:MM:SS'
        """
        from .timezone_utils import parse_datetime, now_shanghai

        changed = False
        id_counter: dict[str, int] = {}
        now = now_shanghai()

        for task in tasks:
            original_id = task.get("id", "")

            # --- 规则1: 修复重复 ID ---
            if original_id in id_counter:
                id_counter[original_id] += 1
                suffix = id_counter[original_id]
                # 去掉末尾已有的 -N 后缀，基于原始 base 重新编号
                base_id = re.sub(r'-\d+$', '', original_id)
                new_id = f"{base_id}-{suffix}"
                # 确保 new_id 唯一（避免与其他任务冲突）
                while any(t.get("id") == new_id for t in tasks if t is not task):
                    suffix += 1
                    new_id = f"{base_id}-{suffix}"
                from .storage_base import logger
                logger.warning(
                    f"[ScheduledStorage] 发现重复ID，自动修正: '{original_id}' -> '{new_id}' "
                    f"(name={task.get('name', '')})"
                )
                task["id"] = new_id
                task["next_run"] = None  # ID 变更，重置 next_run 由调度器重新计算
                changed = True
            else:
                id_counter[original_id] = 1

            # --- 规则2: 清空过期 next_run ---
            next_run_str = task.get("next_run")
            if next_run_str:
                next_run_dt = parse_datetime(next_run_str)
                if next_run_dt is not None and next_run_dt < now:
                    from .storage_base import logger
                    logger.info(
                        f"[ScheduledStorage] 清空过期next_run: "
                        f"id={task.get('id')}, name={task.get('name', '')}, next_run={next_run_str}"
                    )
                    task["next_run"] = None
                    changed = True

            # --- 规则3: 统一时间字段格式 ---
            for field in ("created_at", "updated_at", "last_run", "next_run"):
                if _normalize_datetime_field(task, field):
                    from .storage_base import logger
                    logger.debug(f"[ScheduledStorage] 时间格式已修正: id={task.get('id')}, field={field}")
                    changed = True

        return tasks, changed

    def save(self, task: ScheduledTask) -> None:
        """保存定时任务

        规则：
        - ID 相同则按顺序更新第一条匹配记录
        - 未找到则追加
        """
        data = self._read()
        tasks = data.get("tasks", [])

        # 查找相同 ID 的任务（_read 已保证无重复 ID，直接按 ID 匹配）
        found = False
        for i, t in enumerate(tasks):
            if t["id"] == task.id:
                tasks[i] = task.to_dict()
                found = True
                break

        if not found:
            tasks.append(task.to_dict())

        self._write({"tasks": tasks})

    def get_all(self) -> List[ScheduledTask]:
        """获取所有定时任务"""
        data = self._read()
        return [ScheduledTask.from_dict(t) for t in data.get("tasks", [])]

    def get(self, task_id: str) -> Optional[ScheduledTask]:
        """获取指定定时任务（优先返回已启用的任务）"""
        tasks = self.get_all()
        # 优先返回已启用的任务
        for task in tasks:
            if task.id == task_id and task.enabled:
                return task
        # 如果没有启用的，返回第一个匹配的任务
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

    def get_enabled(self) -> List[ScheduledTask]:
        """获取所有已启用的定时任务（按ID去重）"""
        tasks = self.get_all()
        enabled_tasks = [t for t in tasks if t.enabled]
        
        # 按ID去重：相同ID只保留一个（优先保留已处理的）
        seen_ids = set()
        result = []
        for task in enabled_tasks:
            if task.id not in seen_ids:
                seen_ids.add(task.id)
                result.append(task)
        
        return result

    def count(self) -> int:
        """获取定时任务数量"""
        data = self._read()
        return len(data.get("tasks", []))

    def enabled_count(self) -> int:
        """获取已启用定时任务数量"""
        return len(self.get_enabled())