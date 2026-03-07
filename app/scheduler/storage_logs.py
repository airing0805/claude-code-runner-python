"""任务日志存储模块"""

import json
from pathlib import Path
from typing import List, Dict


class LogsStorage:
    """任务日志存储（使用 JSONL 格式）"""

    def __init__(self, filepath: Path):
        self.filepath = filepath

    def _ensure_init(self) -> None:
        """确保文件存在"""
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.write_text("", encoding="utf-8")

    def append(self, log_entry: dict) -> None:
        """追加日志条目"""
        self._ensure_init()
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def get_all(self, limit: int = 100) -> List[Dict]:
        """获取最近的日志条目"""
        if not self.filepath.exists():
            return []

        logs = []
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        # 返回最近的日志
        return logs[-limit:] if len(logs) > limit else logs

    def get_by_task_id(self, task_id: str, limit: int = 100) -> List[Dict]:
        """获取指定任务的日志"""
        all_logs = self.get_all(limit * 10)  # 获取更多日志以便过滤
        return [log for log in all_logs if log.get("task_id") == task_id][-limit:]

    def clear(self) -> None:
        """清空所有日志"""
        self._ensure_init()
        # 清空文件内容
        self.filepath.write_text("", encoding="utf-8")