"""Cron 表达式验证器

提供Cron表达式的验证功能。
"""

from typing import Optional, Tuple
from .cron_parser import CronParser, CronField


class CronValidator:
    """Cron 表达式验证器"""

    def __init__(self, parser: Optional[CronParser] = None):
        self.parser = parser or CronParser()

    def validate(self, cron: str) -> Tuple[bool, Optional[str]]:
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
            if cron_normalized.lower() in self.parser.ALIASES:
                cron_normalized = self.parser.ALIASES[cron_normalized.lower()]

            # 1. 检查格式
            fields = cron_normalized.split()
            if len(fields) not in (5, 6):
                return False, f"字段数量必须是 5 或 6，当前为 {len(fields)}"

            # 2. 解析表达式
            expression = self.parser.parse(cron)

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
            from .cron_calculator import CronCalculator
            calculator = CronCalculator(self.parser)
            next_run = calculator.calculate_next_run(cron)
            if next_run is None:
                return False, "无法计算下次执行时间"

            return True, None

        except Exception as e:
            return False, str(e)

    def _validate_field(self, field: CronField, field_type: str) -> bool:
        """验证字段值是否在有效范围内"""
        min_val, max_val = self.parser.RANGES[field_type]

        # 跳过特殊字段
        if field.is_last_day or field.is_weekday or field.nth_weekday:
            return True

        for value in field.values:
            if isinstance(value, tuple):
                continue  # n#k 格式跳过验证
            if value < min_val or value > max_val:
                return False

        return True