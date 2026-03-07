"""Cron 表达式解析器统一入口

支持 5 位标准格式（分 时 日 月 周）和 6 位扩展格式（秒 分 时 日 月 周）。
提供表达式解析、验证、下次执行时间计算等功能。
"""

from datetime import datetime
from typing import Optional, Tuple, List
from .cron_parser import CronParser, CronExpression, CronField, RANGES, MONTH_ALIASES, WEEKDAY_ALIASES, CRON_ALIASES
from .cron_validator import CronValidator
from .cron_calculator import CronCalculator


def is_due(next_run: Optional[str]) -> bool:
    """
    判断定时任务是否到期

    Args:
        next_run: 下次执行时间字符串（ISO 8601 格式）

    Returns:
        bool: 是否到期
    """
    if not next_run:
        return False
        
    from .timezone_utils import parse_datetime, now_shanghai
    next_run_dt = parse_datetime(next_run)
    if next_run_dt is None:
        return False
        
    return next_run_dt <= now_shanghai()


# 创建全局实例
_cron_parser: Optional[CronParser] = None
_cron_validator: Optional[CronValidator] = None
_cron_calculator: Optional[CronCalculator] = None


def get_cron_parser() -> CronParser:
    """获取 Cron 解析器单例实例"""
    global _cron_parser
    if _cron_parser is None:
        _cron_parser = CronParser()
    return _cron_parser


def get_cron_validator() -> CronValidator:
    """获取 Cron 验证器单例实例"""
    global _cron_validator
    if _cron_validator is None:
        _cron_validator = CronValidator(get_cron_parser())
    return _cron_validator


def get_cron_calculator() -> CronCalculator:
    """获取 Cron 计算器单例实例"""
    global _cron_calculator
    if _cron_calculator is None:
        _cron_calculator = CronCalculator(get_cron_parser())
    return _cron_calculator


# 向后兼容的便捷函数
def parse_cron(cron: str) -> CronExpression:
    """解析 Cron 表达式"""
    return get_cron_parser().parse(cron)


def validate_cron(cron: str) -> Tuple[bool, Optional[str]]:
    """验证 Cron 表达式"""
    return get_cron_validator().validate(cron)


def calculate_next_run(
    cron: str,
    from_time: Optional[datetime] = None,
) -> Optional[datetime]:
    """计算下次执行时间"""
    return get_cron_calculator().calculate_next_run(cron, from_time)


def get_next_runs(
    cron: str,
    count: int = 5,
    from_time: Optional[datetime] = None,
) -> List[datetime]:
    """获取未来 n 个执行时间"""
    return get_cron_calculator().get_next_runs(cron, count, from_time)


def format_next_run(dt: datetime) -> str:
    """
    格式化下次执行时间

    Args:
        dt: 日期时间对象

    Returns:
        格式化的时间字符串（带上海时区）
    """
    from .timezone_utils import format_datetime
    return format_datetime(dt)
