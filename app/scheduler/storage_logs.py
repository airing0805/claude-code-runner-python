"""任务日志存储模块

扩展支持分类查询、分页和搜索功能。
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class PaginatedLogsResult:
    """分页日志结果"""
    items: List[Dict]
    total: int
    page: int
    limit: int
    pages: int


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

    def get_by_type(
        self,
        task_id: str,
        log_type: str,
        limit: int = 100,
    ) -> List[Dict]:
        """获取指定任务的指定类型日志

        Args:
            task_id: 任务 ID
            log_type: 日志类型 ("stdout" | "stderr")
            limit: 返回数量限制

        Returns:
            日志条目列表
        """
        all_logs = self.get_all(limit * 10)
        filtered = [
            log for log in all_logs
            if log.get("task_id") == task_id and log.get("type") == log_type
        ]
        return filtered[-limit:] if len(filtered) > limit else filtered

    def get_by_time_range(
        self,
        task_id: str,
        start_time: str,
        end_time: str,
        log_type: Optional[str] = None,
    ) -> List[Dict]:
        """获取指定时间范围内的日志

        Args:
            task_id: 任务 ID
            start_time: 开始时间 (ISO 格式)
            end_time: 结束时间 (ISO 格式)
            log_type: 可选的日志类型过滤 ("stdout" | "stderr")

        Returns:
            日志条目列表
        """
        all_logs = self.get_all(10000)
        filtered = []

        for log in all_logs:
            if log.get("task_id") != task_id:
                continue

            # 时间过滤
            log_time = log.get("timestamp", "")
            if log_time < start_time or log_time > end_time:
                continue

            # 类型过滤
            if log_type and log.get("type") != log_type:
                continue

            filtered.append(log)

        return filtered

    def get_paginated(
        self,
        task_id: str,
        page: int = 1,
        limit: int = 100,
        log_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> PaginatedLogsResult:
        """分页获取日志

        Args:
            task_id: 任务 ID
            page: 页码 (从 1 开始)
            limit: 每页数量
            log_type: 可选的日志类型过滤
            start_time: 可选的开始时间过滤
            end_time: 可选的结束时间过滤

        Returns:
            分页日志结果
        """
        # 先获取所有匹配的日志
        all_logs = self.get_all(100000)
        filtered = []

        for log in all_logs:
            if log.get("task_id") != task_id:
                continue

            # 类型过滤
            if log_type and log.get("type") != log_type:
                continue

            # 时间范围过滤
            if start_time or end_time:
                log_time = log.get("timestamp", "")
                if start_time and log_time < start_time:
                    continue
                if end_time and log_time > end_time:
                    continue

            filtered.append(log)

        # 按时间正序排列
        filtered.sort(key=lambda x: x.get("timestamp", ""))

        # 计算分页
        total = len(filtered)
        pages = (total + limit - 1) // limit if total > 0 else 1
        page = min(page, pages) if pages > 0 else 1

        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        items = filtered[start_idx:end_idx]

        return PaginatedLogsResult(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    def search(
        self,
        task_id: str,
        keyword: str,
        regex: bool = False,
        log_type: Optional[str] = None,
        page: int = 1,
        limit: int = 100,
    ) -> PaginatedLogsResult:
        """搜索日志

        Args:
            task_id: 任务 ID
            keyword: 搜索关键字
            regex: 是否使用正则表达式
            log_type: 可选的日志类型过滤
            page: 页码
            limit: 每页数量

        Returns:
            分页搜索结果
        """
        all_logs = self.get_all(100000)
        results = []

        # 编译正则表达式
        pattern = None
        if regex:
            try:
                pattern = re.compile(keyword, re.IGNORECASE)
            except re.error:
                # 无效的正则表达式，返回空结果
                return PaginatedLogsResult(
                    items=[],
                    total=0,
                    page=page,
                    limit=limit,
                    pages=0,
                )

        for log in all_logs:
            if log.get("task_id") != task_id:
                continue

            # 类型过滤
            if log_type and log.get("type") != log_type:
                continue

            content = log.get("content", "")

            # 搜索匹配
            matched = False
            match_positions: List[List[int]] = []

            if regex and pattern:
                match = pattern.search(content)
                if match:
                    matched = True
                    match_positions.append([match.start(), match.end()])
            else:
                # 关键字搜索（不区分大小写）
                keyword_lower = keyword.lower()
                content_lower = content.lower()
                pos = 0
                while True:
                    idx = content_lower.find(keyword_lower, pos)
                    if idx == -1:
                        break
                    match_positions.append([idx, idx + len(keyword)])
                    pos = idx + 1

                if match_positions:
                    matched = True

            if matched:
                results.append({
                    **log,
                    "match_positions": match_positions,
                })

        # 按时间正序排列
        results.sort(key=lambda x: x.get("timestamp", ""))

        # 计算分页
        total = len(results)
        pages = (total + limit - 1) // limit if total > 0 else 1
        page = min(page, pages) if pages > 0 else 1

        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        items = results[start_idx:end_idx]

        return PaginatedLogsResult(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    def get_count_by_type(self, task_id: str) -> Dict[str, int]:
        """获取指定任务的各类型日志数量

        Args:
            task_id: 任务 ID

        Returns:
            包含 stdout 和 stderr 数量的字典
        """
        all_logs = self.get_all(100000)
        counts = {"stdout": 0, "stderr": 0}

        for log in all_logs:
            if log.get("task_id") == task_id:
                log_type = log.get("type")
                if log_type in counts:
                    counts[log_type] += 1

        return counts

    def clear(self) -> None:
        """清空所有日志"""
        self._ensure_init()
        # 清空文件内容
        self.filepath.write_text("", encoding="utf-8")
