"""Cron 表达式解析器核心逻辑

支持 5 位标准格式（分 时 日 月 周）和 6 位扩展格式（秒 分 时 日 月 周）。
提供表达式解析功能。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple

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

    def validate(self, cron: str) -> Tuple[bool, Optional[str]]:
        """
        验证 Cron 表达式（向后兼容委托）

        Args:
            cron: Cron 表达式字符串

        Returns:
            (is_valid, error_message) 元组
        """
        from .cron_validator import CronValidator
        validator = CronValidator(self)
        return validator.validate(cron)

    def calculate_next_run(
        self,
        cron: str,
        from_time: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """
        计算下次执行时间（委托给 CronCalculator）

        Args:
            cron: Cron 表达式
            from_time: 起始时间，默认当前时间

        Returns:
            下次执行时间，如果无法计算返回 None
        """
        from .cron_calculator import CronCalculator
        calculator = CronCalculator(self)
        return calculator.calculate_next_run(cron, from_time)

    def get_next_runs(
        self,
        cron: str,
        count: int = 5,
        from_time: Optional[datetime] = None,
    ) -> list[datetime]:
        """
        获取未来 n 个执行时间（委托给 CronCalculator）

        Args:
            cron: Cron 表达式
            count: 返回数量
            from_time: 起始时间，默认当前时间

        Returns:
            执行时间列表
        """
        from .cron_calculator import CronCalculator
        calculator = CronCalculator(self)
        return calculator.get_next_runs(cron, count, from_time)

    def _get_last_day_of_month(self, year: int, month: int) -> int:
        """
        获取指定月份的最后一天（委托给 CronCalculator）

        Args:
            year: 年份
            month: 月份

        Returns:
            该月的最后一天
        """
        from .cron_calculator import CronCalculator
        calculator = CronCalculator(self)
        return calculator._get_last_day_of_month(year, month)

    def _matches(self, expression: CronExpression, dt: datetime) -> bool:
        """
        检查时间是否匹配 Cron 表达式（委托给 CronCalculator）

        Args:
            expression: Cron 表达式对象
            dt: 待检查的时间

        Returns:
            是否匹配
        """
        from .cron_calculator import CronCalculator
        calculator = CronCalculator(self)
        return calculator._matches(expression, dt)

    def _field_matches(self, field: CronField, value: int, dt: datetime) -> bool:
        """
        检查字段值是否匹配（委托给 CronCalculator）

        Args:
            field: Cron 字段对象
            value: 待检查的值
            dt: 日期时间对象

        Returns:
            是否匹配
        """
        from .cron_calculator import CronCalculator
        calculator = CronCalculator(self)
        return calculator._field_matches(field, value, dt)

    def _validate_field(self, field: CronField, field_type: str) -> bool:
        """
        验证字段值是否在有效范围内（委托给 CronValidator）

        Args:
            field: Cron 字段对象
            field_type: 字段类型

        Returns:
            是否有效
        """
        from .cron_validator import CronValidator
        validator = CronValidator(self)
        return validator._validate_field(field, field_type)