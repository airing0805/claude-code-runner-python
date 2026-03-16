"""时区工具模块

统一使用中国上海时区 (UTC+8)。
所有时间操作均通过此模块进行，避免时区混用导致的调度错误。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

# 中国上海时区 (UTC+8)
SHANGHAI_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def now_shanghai() -> datetime:
    """获取当前上海时间（带时区信息）"""
    return datetime.now(SHANGHAI_TZ)


def now_iso() -> str:
    """获取当前上海时间的格式字符串 (格式: 2026-03-05 03:20:00)"""
    return now_shanghai().strftime("%Y-%m-%d %H:%M:%S")


def to_shanghai(dt: datetime) -> datetime:
    """将任意 datetime 转换为上海时区

    Args:
        dt: 任意 datetime 对象（naive 或 aware）

    Returns:
        带上海时区的 datetime
    """
    if dt.tzinfo is None:
        # naive datetime：假定为上海本地时间
        return dt.replace(tzinfo=SHANGHAI_TZ)
    else:
        # aware datetime：转换时区
        return dt.astimezone(SHANGHAI_TZ)


def parse_datetime(s: str) -> Optional[datetime]:
    """解析时间字符串，返回带上海时区的 datetime

    支持格式：
    - ISO 8601 with timezone: "2026-03-06T09:00:00+08:00"
    - ISO 8601 without timezone: "2026-03-06T09:00:00"
    - Space separator: "2026-03-06 09:00:00"

    Args:
        s: 时间字符串

    Returns:
        带上海时区的 datetime，解析失败返回 None
    """
    if not s:
        return None

    try:
        s_normalized = s.strip().replace(" ", "T")
        dt = datetime.fromisoformat(s_normalized)
        return to_shanghai(dt)
    except (ValueError, AttributeError):
        return None


def format_datetime(dt: datetime) -> str:
    """格式化 datetime 为统一的字符串格式

    Args:
        dt: datetime 对象

    Returns:
        格式化字符串，例如 "2026-03-06 09:00:00"
    """
    dt_sh = to_shanghai(dt)
    return dt_sh.strftime("%Y-%m-%d %H:%M:%S")


def is_due(next_run: Optional[str]) -> bool:
    """判断定时任务是否到期

    Args:
        next_run: 下次执行时间字符串

    Returns:
        是否到期
    """
    if next_run is None:
        return False

    dt = parse_datetime(next_run)
    if dt is None:
        return False

    return now_shanghai() >= dt
