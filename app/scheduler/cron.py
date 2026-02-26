"""Cron 表达式解析器

支持 5 位标准格式（分 时 日 月 周）和 6 位扩展格式（秒 分 时 日 月 周）。
提供表达式解析、验证、下次执行时间计算等功能。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


# 字段范围定义
RANGES: dict[str, tuple[int, int]] = {
    "second": (0, 59),
    "minute": (0, 59),
    "hour": (0, 23),
    "day": (1, 31),
    "month": (1, 12),
    "weekday": (0, 6),
}

# 月份别名
MONTH_ALIASES: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# 星期别名
WEEKDAY_ALIASES: dict[str, int] = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3,
    "thu": 4, "fri": 5, "sat": 6,
}

# Cron 表达式别名
CRON_ALIASES: dict[str, str] = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}


@dataclass
class CronField:
    """Cron 字段"""

    field_type: str  # second/minute/hour/day/month/weekday
    values: list[int]  # 可能的值列表
    has_wildcard: bool = False  # 是否包含通配符
    has_step: bool = False  # 是否有步进值
    step_value: int = 1  # 步进值
    is_range: bool = False  # 是否是范围
    range_start: int = 0  # 范围开始
    range_end: int = 0  # 范围结束
    is_list: bool = False  # 是否是列表
    list_values: list[int] = field(default_factory=list)  # 列表值
    is_last_day: bool = False  # 是否是月末 (L)
    is_weekday: bool = False  # 是否是工作日 (W)
    nth_weekday: Optional[tuple[int, int]] = None  # 第几个星期几 (n#k)


@dataclass
class CronExpression:
    """Cron 表达式"""

    is_extended: bool = False  # 是否是 6 位格式
    second: Optional[CronField] = None
    minute: Optional[CronField] = None
    hour: Optional[CronField] = None
    day: Optional[CronField] = None
    month: Optional[CronField] = None
    weekday: Optional[CronField] = None


class CronParser:
    """Cron 表达式解析器"""

    RANGES = RANGES
    MONTH_ALIASES = MONTH_ALIASES
    WEEKDAY_ALIASES = WEEKDAY_ALIASES
    ALIASES = CRON_ALIASES

    def __init__(self) -> None:
        """初始化解析器"""
        self._cache: dict[str, CronExpression] = {}

    def parse(self, cron: str) -> CronExpression:
        """
        解析 Cron 表达式

        Args:
            cron: Cron 表达式字符串

        Returns:
            CronExpression 对象

        Raises:
            ValueError: 表达式格式无效
        """
        cron = cron.strip()

        # 检查缓存
        if cron in self._cache:
            return self._cache[cron]

        # 检查别名
        if cron.lower() in self.ALIASES:
            cron = self.ALIASES[cron.lower()]

        fields = cron.split()

        # 判断格式
        if len(fields) == 5:
            expression = self._parse_standard_format(fields)
        elif len(fields) == 6:
            expression = self._parse_extended_format(fields)
        else:
            raise ValueError(f"无效的 Cron 表达式格式: 期望 5 或 6 个字段，实际 {len(fields)} 个")

        # 缓存结果
        self._cache[cron] = expression

        return expression

    def _parse_standard_format(self, fields: list[str]) -> CronExpression:
        """解析 5 位标准格式（分 时 日 月 周）"""
        if len(fields) != 5:
            raise ValueError("标准格式需要 5 个字段")

        return CronExpression(
            is_extended=False,
            second=None,
            minute=self._parse_field(fields[0], "minute"),
            hour=self._parse_field(fields[1], "hour"),
            day=self._parse_field(fields[2], "day"),
            month=self._parse_field(fields[3], "month"),
            weekday=self._parse_field(fields[4], "weekday"),
        )

    def _parse_extended_format(self, fields: list[str]) -> CronExpression:
        """解析 6 位扩展格式（秒 分 时 日 月 周）"""
        if len(fields) != 6:
            raise ValueError("扩展格式需要 6 个字段")

        return CronExpression(
            is_extended=True,
            second=self._parse_field(fields[0], "second"),
            minute=self._parse_field(fields[1], "minute"),
            hour=self._parse_field(fields[2], "hour"),
            day=self._parse_field(fields[3], "day"),
            month=self._parse_field(fields[4], "month"),
            weekday=self._parse_field(fields[5], "weekday"),
        )

    def _parse_field(self, field: str, field_type: str) -> CronField:
        """
        解析单个字段

        支持格式:
        - *           -> 通配符
        - */n         -> 步进
        - n-m         -> 范围
        - n,m,o       -> 列表
        - n-m/o       -> 范围步进
        - L           -> 月末 (day/weekday)
        - W           -> 最近工作日 (day)
        - n#k         -> 第 k 个星期 n (weekday)
        """
        min_val, max_val = self.RANGES[field_type]
        field = field.strip()

        # 处理特殊字符
        if field == "*":
            return CronField(
                field_type=field_type,
                values=list(range(min_val, max_val + 1)),
                has_wildcard=True,
                has_step=False,
                step_value=1,
                is_range=False,
                range_start=min_val,
                range_end=max_val,
                is_list=False,
                list_values=[],
            )

        # 处理 L (月末)
        if field.lower() == "l":
            return CronField(
                field_type=field_type,
                values=[],
                has_wildcard=False,
                has_step=False,
                step_value=1,
                is_range=False,
                range_start=0,
                range_end=0,
                is_list=False,
                list_values=[],
                is_last_day=True,
            )

        # 处理 W (最近工作日)
        if field.lower() == "w":
            return CronField(
                field_type=field_type,
                values=[],
                has_wildcard=False,
                has_step=False,
                step_value=1,
                is_range=False,
                range_start=0,
                range_end=0,
                is_list=False,
                list_values=[],
                is_weekday=True,
            )

        # 处理 LW (月末工作日)
        if field.lower() == "lw":
            return CronField(
                field_type=field_type,
                values=[],
                has_wildcard=False,
                has_step=False,
                step_value=1,
                is_range=False,
                range_start=0,
                range_end=0,
                is_list=False,
                list_values=[],
                is_last_day=True,
                is_weekday=True,
            )

        # 处理步进 (n/m 或 */m)
        if "/" in field:
            base, step = field.split("/")
            step_value = int(step)

            if base == "*":
                # */n 格式
                values = list(range(min_val, max_val + 1, step_value))
                return CronField(
                    field_type=field_type,
                    values=values,
                    has_wildcard=False,
                    has_step=True,
                    step_value=step_value,
                    is_range=False,
                    range_start=min_val,
                    range_end=max_val,
                    is_list=False,
                    list_values=[],
                )
            elif "-" in base:
                # n-m/n 格式
                start, end = base.split("-")
                start_val = self._parse_value(start, field_type)
                end_val = self._parse_value(end, field_type)
                values = list(range(start_val, end_val + 1, step_value))
                return CronField(
                    field_type=field_type,
                    values=values,
                    has_wildcard=False,
                    has_step=True,
                    step_value=step_value,
                    is_range=True,
                    range_start=start_val,
                    range_end=end_val,
                    is_list=False,
                    list_values=[],
                )

        # 处理列表 (n,m,o)
        if "," in field:
            parts = field.split(",")
            values = []
            list_values = []
            for part in parts:
                # 处理 n#k 格式
                if "#" in part and field_type == "weekday":
                    weekday_part, nth = part.split("#")
                    weekday_val = self._parse_value(weekday_part, field_type)
                    nth_val = int(nth)
                    values.append((weekday_val, nth_val))
                    list_values.append((weekday_val, nth_val))
                else:
                    val = self._parse_value(part.strip(), field_type)
                    values.append(val)
                    list_values.append(val)
            return CronField(
                field_type=field_type,
                values=values,
                has_wildcard=False,
                has_step=False,
                step_value=1,
                is_range=False,
                range_start=0,
                range_end=0,
                is_list=True,
                list_values=list_values,
            )

        # 处理范围 (n-m)
        if "-" in field:
            start, end = field.split("-")
            start_val = self._parse_value(start, field_type)
            end_val = self._parse_value(end, field_type)
            values = list(range(start_val, end_val + 1))
            return CronField(
                field_type=field_type,
                values=values,
                has_wildcard=False,
                has_step=False,
                step_value=1,
                is_range=True,
                range_start=start_val,
                range_end=end_val,
                is_list=False,
                list_values=[],
            )

        # 处理 n#k 格式 (第几个星期几)
        if "#" in field and field_type == "weekday":
            weekday_part, nth = field.split("#")
            weekday_val = self._parse_value(weekday_part, field_type)
            nth_val = int(nth)
            return CronField(
                field_type=field_type,
                values=[(weekday_val, nth_val)],
                has_wildcard=False,
                has_step=False,
                step_value=1,
                is_range=False,
                range_start=0,
                range_end=0,
                is_list=False,
                list_values=[],
                nth_weekday=(weekday_val, nth_val),
            )

        # 单个值
        value = self._parse_value(field, field_type)
        return CronField(
            field_type=field_type,
            values=[value],
            has_wildcard=False,
            has_step=False,
            step_value=1,
            is_range=False,
            range_start=value,
            range_end=value,
            is_list=False,
            list_values=[value],
        )

    def _parse_value(self, value: str, field_type: str) -> int:
        """解析字段值，支持别名"""
        value = value.lower()

        # 月份别名
        if field_type == "month":
            if value in self.MONTH_ALIASES:
                return self.MONTH_ALIASES[value]

        # 星期别名
        if field_type == "weekday":
            if value in self.WEEKDAY_ALIASES:
                return self.WEEKDAY_ALIASES[value]
            # 星期日可以用 0 或 7 表示
            if value == "7":
                return 0

        # 检查是否是数字
        if value.isdigit():
            return int(value)

        raise ValueError(f"无效的 {field_type} 值: {value}")

    def validate(self, cron: str) -> tuple[bool, Optional[str]]:
        """
        验证 Cron 表达式

        Args:
            cron: Cron 表达式字符串

        Returns:
            (is_valid, error_message) 元组
        """
        try:
            # 0. 检查别名
            cron_normalized = cron.strip()
            if cron_normalized.lower() in self.ALIASES:
                cron_normalized = self.ALIASES[cron_normalized.lower()]

            # 1. 检查格式
            fields = cron_normalized.split()
            if len(fields) not in (5, 6):
                return False, f"字段数量必须是 5 或 6，当前为 {len(fields)}"

            # 2. 解析表达式
            expression = self.parse(cron)

            # 3. 验证每个字段
            for field_obj, field_type in [
                (expression.second, "second") if expression.second else (None, None),
                (expression.minute, "minute"),
                (expression.hour, "hour"),
                (expression.day, "day"),
                (expression.month, "month"),
                (expression.weekday, "weekday"),
            ]:
                if field_obj is None or field_type is None:
                    continue

                if not self._validate_field(field_obj, field_type):
                    return False, f"{field_type} 字段值无效"

            # 4. 计算下次执行时间
            next_run = self.calculate_next_run(cron)
            if next_run is None:
                return False, "无法计算下次执行时间"

            return True, None

        except Exception as e:
            return False, str(e)

    def _validate_field(self, field: CronField, field_type: str) -> bool:
        """验证字段值是否在有效范围内"""
        min_val, max_val = self.RANGES[field_type]

        # 跳过特殊字段
        if field.is_last_day or field.is_weekday or field.nth_weekday:
            return True

        for value in field.values:
            if isinstance(value, tuple):
                continue  # n#k 格式跳过验证
            if value < min_val or value > max_val:
                return False

        return True

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
        if from_time is None:
            from_time = datetime.now()

        try:
            expression = self.parse(cron)
        except ValueError:
            return None

        # 6 位格式保留微秒，5 位格式秒和微秒都设为 0
        if expression.is_extended:
            current = from_time.replace(microsecond=0)
        else:
            current = from_time.replace(second=0, microsecond=0)

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

    def _skip_to_next_valid(
        self,
        current: datetime,
        expression: CronExpression,
    ) -> datetime:
        """
        快速跳转到下一个可能匹配的时间
        """
        # 5 位格式：秒必须是 0，如果秒不为 0，跳到当前分钟的 0 秒
        if not expression.is_extended:
            if current.second != 0:
                # 跳到当前分钟的 0 秒
                return current.replace(second=0)

        # 处理日期字段的 L 格式（月末）
        if expression.day is not None and expression.day.is_last_day:
            # 计算当月最后一天
            last_day = self._get_last_day_of_month(current.year, current.month)
            if current.day < last_day:
                # 跳到月末
                return current.replace(day=last_day, hour=0, minute=0, second=0)
            else:
                # 已是月末，跳到下月第一天
                if current.month == 12:
                    return current.replace(year=current.year + 1, month=1, day=1, hour=0, minute=0, second=0)
                else:
                    return current.replace(month=current.month + 1, day=1, hour=0, minute=0, second=0)

        # 6 位格式：处理秒
        if expression.is_extended and expression.second is not None:
            sec_field = expression.second
            if sec_field.has_step and not sec_field.has_wildcard:
                # */n 格式，跳到下一个匹配秒
                step = sec_field.step_value
                next_second = ((current.second // step) + 1) * step
                if next_second <= 59:
                    return current.replace(second=next_second)
                else:
                    # 秒超出范围，秒归零并递增分钟
                    current = current.replace(second=0)
                    current = current + timedelta(minutes=1)
                    return current
            elif not sec_field.has_wildcard:
                # 固定秒值
                if current.second not in sec_field.values:
                    # 找到下一个匹配的秒
                    next_sec = None
                    for s in sec_field.values:
                        if s > current.second:
                            next_sec = s
                            break
                    if next_sec is not None:
                        return current.replace(second=next_sec)
                    else:
                        # 秒已超出范围，秒归零并递增分钟
                        current = current.replace(second=0)
                        current = current + timedelta(minutes=1)
                        return current

        # 处理分钟步进
        if expression.minute is not None:
            min_field = expression.minute
            if min_field.has_step and not min_field.has_wildcard:
                # */n 格式，跳到下一个匹配分钟
                step = min_field.step_value
                next_minute = ((current.minute // step) + 1) * step
                if next_minute <= 59:
                    return current.replace(minute=next_minute, second=0)
                else:
                    # 分钟超出范围，分钟归零并递增小时
                    current = current.replace(minute=0, second=0)
                    current = current + timedelta(hours=1)
                    return current
            elif not min_field.has_wildcard:
                # 固定分钟值
                if current.minute not in min_field.values:
                    next_min = None
                    for m in min_field.values:
                        if m > current.minute:
                            next_min = m
                            break
                    if next_min is not None:
                        return current.replace(minute=next_min, second=0)
                    else:
                        current = current.replace(minute=0, second=0)
                        current = current + timedelta(hours=1)
                        return current
                else:
                    # 分钟匹配，检查小时是否匹配
                    if expression.hour is not None:
                        hour_field = expression.hour
                        if not hour_field.has_wildcard:
                            if current.hour not in hour_field.values:
                                # 小时不匹配，跳到下一个匹配小时
                                next_hour = None
                                for h in hour_field.values:
                                    if h > current.hour:
                                        next_hour = h
                                        break
                                if next_hour is not None:
                                    return current.replace(hour=next_hour, minute=0, second=0)
                                else:
                                    # 跳到下一天
                                    current = current.replace(hour=0, minute=0, second=0)
                                    current = current + timedelta(days=1)
                                    return current

        # 处理小时步进
        if expression.hour is not None:
            hour_field = expression.hour
            if hour_field.has_step and not hour_field.has_wildcard:
                step = hour_field.step_value
                next_hour = ((current.hour // step) + 1) * step
                if next_hour <= 23:
                    return current.replace(hour=next_hour, minute=0, second=0)
                else:
                    current = current.replace(hour=0, minute=0, second=0)
                    current = current + timedelta(days=1)
                    return current
            elif not hour_field.has_wildcard:
                # 固定小时值
                if current.hour not in hour_field.values:
                    next_hour = None
                    for h in hour_field.values:
                        if h > current.hour:
                            next_hour = h
                            break
                    if next_hour is not None:
                        return current.replace(hour=next_hour, minute=0, second=0)
                    else:
                        # 跳到下一天
                        current = current.replace(hour=0, minute=0, second=0)
                        current = current + timedelta(days=1)
                        return current

        # 默认递增 1 秒
        return current + timedelta(seconds=1)

    def get_next_runs(
        self,
        cron: str,
        count: int = 5,
        from_time: Optional[datetime] = None,
    ) -> list[datetime]:
        """
        获取未来 n 个执行时间

        Args:
            cron: Cron 表达式
            count: 返回数量
            from_time: 起始时间，默认当前时间

        Returns:
            执行时间列表
        """
        results: list[datetime] = []
        current = from_time if from_time else datetime.now()

        # 解析表达式确定格式
        try:
            expression = self.parse(cron)
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


def is_due(next_run: Optional[str]) -> bool:
    """
    判断定时任务是否到期

    Args:
        next_run: 下次执行时间 (ISO 格式字符串)

    Returns:
        是否到期
    """
    if next_run is None:
        return False

    try:
        # 尝试解析带时区和不带时区的时间
        if "+" in next_run or "Z" in next_run or next_run.endswith("+00:00"):
            next_run_time = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
            now = datetime.now(next_run_time.tzinfo)
        else:
            next_run_time = datetime.fromisoformat(next_run)
            now = datetime.now()
        return now >= next_run_time
    except (ValueError, AttributeError):
        return False


def format_next_run(dt: datetime) -> str:
    """
    格式化下次执行时间

    Args:
        dt: 日期时间对象

    Returns:
        格式化的时间字符串
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")
