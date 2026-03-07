"""Cron 表达式计算器

提供Cron表达式的下次执行时间计算功能。
"""

from datetime import datetime, timedelta
from typing import Optional, List
from .cron_parser import CronParser, CronExpression, CronField


class CronCalculator:
    """Cron 表达式计算器"""

    def __init__(self, parser: Optional[CronParser] = None):
        self.parser = parser or CronParser()

    def calculate_next_run(
        self,
        cron: str,
        from_time: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """
        计算下次执行时间

        Args:
            cron: Cron 表达式
            from_time: 起始时间，默认当前时间

        Returns:
            下次执行时间，如果无法计算返回 None
        """
        from .timezone_utils import now_shanghai
        
        if from_time is None:
            from_time = now_shanghai()

        try:
            expression = self.parser.parse(cron)
        except ValueError:
            return None

        # 6 位格式保留微秒，5 位格式秒和微秒都设为 0
        # 对于 5 位格式，需要先检查 from_time 本身是否就是有效的执行时间
        # 如果是（秒=0），直接返回，否则从下一分钟开始搜索
        if not expression.is_extended:
            # 5 位格式：检查秒是否为 0，如果是则检查是否匹配
            if from_time.second == 0 and self._matches(expression, from_time):
                # 当前时间就是有效的执行时间，直接返回
                return from_time
            # 否则从下一分钟开始搜索
            current = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        else:
            current = from_time.replace(microsecond=0) + timedelta(seconds=1)

        # 最多尝试计算 1 年内的下一个执行时间
        # 按分钟迭代，最多 366 * 24 * 60 = 527,040 次
        max_iterations = 366 * 24 * 60

        for _ in range(max_iterations):
            if self._matches(expression, current):
                return current

            # 对于 5 位格式，按分钟递增；6 位格式按秒递增
            if expression.is_extended:
                current = current + timedelta(seconds=1)
            else:
                current = current + timedelta(minutes=1)

            # 确保不会无限循环（超过 1 年）
            if current.year > from_time.year + 1:
                break

        return None

    def _matches(self, expression: CronExpression, dt: datetime) -> bool:
        """检查时间是否匹配 Cron 表达式"""
        # 5 位格式：秒必须为 0
        if not expression.is_extended:
            if dt.second != 0:
                return False

        # 6 位格式：检查秒
        if expression.second is not None:
            if not self._field_matches(expression.second, dt.second, dt):
                return False

        # 检查分钟
        if expression.minute is not None:
            if not self._field_matches(expression.minute, dt.minute, dt):
                return False

        # 检查小时
        if expression.hour is not None:
            if not self._field_matches(expression.hour, dt.hour, dt):
                return False

        # 检查日期
        if expression.day is not None:
            if not self._field_matches(expression.day, dt.day, dt):
                return False

        # 检查月份
        if expression.month is not None:
            if not self._field_matches(expression.month, dt.month, dt):
                return False

        # 检查星期
        # 注意：Python 的 weekday() 返回 0-6 (周一=0)
        # Cron 的星期 0 和 7 都是周日
        if expression.weekday is not None:
            weekday = dt.weekday()
            if not self._field_matches(expression.weekday, weekday, dt):
                return False

        return True

    def _field_matches(self, field: CronField, value: int, dt: datetime) -> bool:
        """检查字段值是否匹配"""
        # 处理 L (月末)
        if field.is_last_day:
            # 获取当月最后一天
            if field.field_type == "day":
                last_day = self._get_last_day_of_month(dt.year, dt.month)
                return value == last_day
            elif field.field_type == "weekday":
                # 每周最后一天 (周六)
                return value == 6

        # 处理 W (最近工作日)
        if field.is_weekday:
            if field.field_type == "day":
                # 计算最近工作日
                target_day = value
                weekday = dt.weekday()
                days_diff = target_day - weekday
                if days_diff < -3:
                    days_diff += 7
                elif days_diff > 4:
                    days_diff -= 7
                return value == (weekday + days_diff)

        # 处理 n#k 格式 (第几个星期几)
        if field.nth_weekday is not None:
            weekday, nth = field.nth_weekday
            # 计算第 n 个星期几的日期
            first_day = dt.replace(day=1)
            first_weekday = first_day.weekday()
            # 计算第一个目标星期的日期
            days_to_first = (weekday - first_weekday) % 7
            target_day = 1 + days_to_first + (nth - 1) * 7
            # 检查是否超出当月天数
            last_day = self._get_last_day_of_month(dt.year, dt.month)
            if target_day <= last_day:
                return value == target_day
            return False

        # 处理列表中的 n#k 格式
        if field.is_list:
            for item in field.list_values:
                if isinstance(item, tuple):
                    weekday, nth = item
                    first_day = dt.replace(day=1)
                    first_weekday = first_day.weekday()
                    days_to_first = (weekday - first_weekday) % 7
                    target_day = 1 + days_to_first + (nth - 1) * 7
                    last_day = self._get_last_day_of_month(dt.year, dt.month)
                    if target_day <= last_day and value == target_day:
                        return True
                elif value == item:
                    return True
            return False

        return value in field.values

    def _get_last_day_of_month(self, year: int, month: int) -> int:
        """获取指定月份的最后一天"""
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        return last_day

    def get_next_runs(
        self,
        cron: str,
        count: int = 5,
        from_time: Optional[datetime] = None,
    ) -> List[datetime]:
        """
        获取未来 n 个执行时间

        Args:
            cron: Cron 表达式
            count: 返回数量
            from_time: 起始时间，默认当前时间

        Returns:
            执行时间列表
        """
        from .timezone_utils import now_shanghai
        
        results: List[datetime] = []
        current = from_time if from_time else now_shanghai()

        # 解析表达式确定格式
        try:
            expression = self.parser.parse(cron)
        except ValueError:
            return results

        for _ in range(count):
            next_run = self.calculate_next_run(cron, current)
            if next_run is None:
                break
            results.append(next_run)
            # 从下次执行时间开始计算下一个
            # 5 位格式：加 1 分钟；6 位格式：加 1 秒
            if expression.is_extended:
                current = next_run + timedelta(seconds=1)
            else:
                current = next_run + timedelta(minutes=1)

        return results