"""任务调度存储层基础类"""

import json
import logging
import os
import tempfile
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

from .config import (
    DATA_DIR,
    LOCK_TIMEOUT,
    LOCK_RETRY_INTERVAL,
    MAX_LOCK_RETRIES,
)


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


def _normalize_datetime_field(task: dict, field: str) -> bool:
    """将 task 字典中指定时间字段统一格式化为 'YYYY-MM-DD HH:MM:SS'

    支持的输入格式：
    - ISO 8601 带时区: "2026-03-06T09:00:00+08:00"
    - ISO 8601 无时区: "2026-03-06T09:00:00"
    - ISO 带毫秒:     "2026-03-06T09:00:00.123456"
    - 空格分隔:       "2026-03-06 09:00:00.034541"

    不修改 None 或无法解析的值，绝对不修改 prompt 等非时间字段。

    Returns:
        是否发生了变更
    """
    from .timezone_utils import parse_datetime, format_datetime

    value = task.get(field)
    if not value:
        return False

    dt = parse_datetime(str(value))
    if dt is None:
        return False

    normalized = format_datetime(dt)
    if normalized != value:
        task[field] = normalized
        return True
    return False


class BaseStorage:
    """JSON 文件存储基类"""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath

    def _read_raw(self) -> dict[str, Any]:
        """读取原始数据（不加锁）"""
        if not self.filepath.exists():
            return {"tasks": []}
        content = self.filepath.read_text(encoding="utf-8")
        if not content.strip():
            return {"tasks": []}
        return json.loads(content)

    def _read(self) -> dict[str, Any]:
        """读取数据（加锁）"""
        return self._read_raw()

    def _write_raw(self, data: dict[str, Any]) -> None:
        """写入原始数据（不加锁）"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self.filepath, data)

    def _write(self, data: dict[str, Any]) -> None:
        """写入数据（加锁和原子操作）"""
        self._write_raw(data)