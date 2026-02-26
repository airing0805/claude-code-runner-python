"""Cron 解析器单元测试"""

import pytest
from datetime import datetime

from app.scheduler.cron import (
    CronParser,
    CronExpression,
    CronField,
    is_due,
    format_next_run,
    RANGES,
    CRON_ALIASES,
)


class TestCronField:
    """CronField 数据结构测试"""

    def test_cron_field_creation(self):
        """测试 Cron 字段创建"""
        field = CronField(
            field_type="minute",
            values=[0, 15, 30, 45],
            has_wildcard=False,
        )

        assert field.field_type == "minute"
        assert field.values == [0, 15, 30, 45]
        assert field.has_wildcard is False

    def test_cron_field_wildcard(self):
        """测试通配符字段"""
        field = CronField(
            field_type="hour",
            values=list(range(24)),
            has_wildcard=True,
        )

        assert field.has_wildcard is True
        assert len(field.values) == 24


class TestCronParserStandardFormat:
    """测试标准格式（5位）解析"""

    @pytest.fixture
    def parser(self):
        return CronParser()

    def test_parse_standard_format_basic(self, parser):
        """测试基本 5 位格式解析"""
        expr = parser.parse("0 * * * *")

        assert expr.is_extended is False
        assert expr.second is None
        assert expr.minute is not None
        assert expr.hour is not None
        assert expr.day is not None
        assert expr.month is not None
        assert expr.weekday is not None

    def test_parse_all_wildcards(self, parser):
        """测试全通配符表达式"""
        expr = parser.parse("* * * * *")

        assert expr.minute.has_wildcard is True
        assert expr.hour.has_wildcard is True
        assert expr.day.has_wildcard is True
        assert expr.month.has_wildcard is True
        assert expr.weekday.has_wildcard is True

    def test_parse_fixed_values(self, parser):
        """测试固定值表达式"""
        expr = parser.parse("30 14 15 6 1")

        assert expr.minute.values == [30]
        assert expr.hour.values == [14]
        assert expr.day.values == [15]
        assert expr.month.values == [6]
        assert expr.weekday.values == [1]

    def test_parse_standard_field_count(self, parser):
        """测试字段数量验证"""
        # 4 个字段应该失败
        with pytest.raises(ValueError, match="5 或 6 个字段"):
            parser.parse("0 * * *")

        # 7 个字段应该失败
        with pytest.raises(ValueError):
            parser.parse("0 0 0 * * * *")

    def test_parse_standard_format_structure(self, parser):
        """测试 5 位格式的字段结构"""
        expr = parser.parse("15 8 1 1 0")

        assert expr.is_extended is False
        assert expr.second is None  # 5 位格式没有秒字段
        assert expr.minute.values == [15]
        assert expr.hour.values == [8]
        assert expr.day.values == [1]
        assert expr.month.values == [1]
        assert expr.weekday.values == [0]


class TestCronParserExtendedFormat:
    """测试扩展格式（6位）解析"""

    @pytest.fixture
    def parser(self):
        return CronParser()

    def test_parse_extended_format_basic(self, parser):
        """测试基本 6 位格式解析"""
        expr = parser.parse("0 0 * * * *")

        assert expr.is_extended is True
        assert expr.second is not None
        assert expr.minute is not None
        assert expr.hour is not None

    def test_parse_extended_with_seconds(self, parser):
        """测试带秒的 6 位格式"""
        expr = parser.parse("30 15 10 * * *")

        assert expr.is_extended is True
        assert expr.second.values == [30]
        assert expr.minute.values == [15]
        assert expr.hour.values == [10]

    def test_parse_extended_all_wildcards(self, parser):
        """测试 6 位全通配符"""
        expr = parser.parse("* * * * * *")

        assert expr.second.has_wildcard is True
        assert expr.minute.has_wildcard is True
        assert expr.hour.has_wildcard is True
        assert expr.day.has_wildcard is True
        assert expr.month.has_wildcard is True
        assert expr.weekday.has_wildcard is True

    def test_parse_extended_field_count(self, parser):
        """测试 6 位格式字段数量验证"""
        with pytest.raises(ValueError):
            parser.parse("0 0 0 * * * *")  # 7 个字段


class TestCronSpecialCharacters:
    """测试特殊字符解析"""

    @pytest.fixture
    def parser(self):
        return CronParser()

    # 测试通配符 *
    def test_wildcard_character(self, parser):
        """测试通配符 *"""
        expr = parser.parse("* 0 * * *")

        assert expr.minute.has_wildcard is True
        assert expr.minute.values == list(range(0, 60))

    # 测试步进 /
    def test_step_character(self, parser):
        """测试步进字符 /"""
        expr = parser.parse("*/15 * * * *")

        assert expr.minute.has_step is True
        assert expr.minute.step_value == 15
        assert expr.minute.values == [0, 15, 30, 45]

    def test_step_character_hour(self, parser):
        """测试小时字段步进"""
        expr = parser.parse("0 */6 * * *")

        assert expr.hour.has_step is True
        assert expr.hour.step_value == 6
        assert expr.hour.values == [0, 6, 12, 18]

    def test_step_with_range(self, parser):
        """测试范围步进 n-m/n"""
        expr = parser.parse("0-30/10 * * * *")

        assert expr.minute.has_step is True
        assert expr.minute.is_range is True
        assert expr.minute.range_start == 0
        assert expr.minute.range_end == 30
        assert expr.minute.values == [0, 10, 20, 30]

    # 测试范围 -
    def test_range_character(self, parser):
        """测试范围字符 -"""
        expr = parser.parse("0 9-17 * * *")

        assert expr.hour.is_range is True
        assert expr.hour.range_start == 9
        assert expr.hour.range_end == 17
        assert expr.hour.values == list(range(9, 18))

    def test_range_character_minute(self, parser):
        """测试分钟字段范围"""
        expr = parser.parse("10-20 * * * *")

        assert expr.minute.is_range is True
        assert expr.minute.values == list(range(10, 21))

    # 测试列表 ,
    def test_list_character(self, parser):
        """测试列表字符 ,"""
        expr = parser.parse("0,15,30,45 * * * *")

        assert expr.minute.is_list is True
        assert expr.minute.list_values == [0, 15, 30, 45]
        assert expr.minute.values == [0, 15, 30, 45]

    def test_list_character_mixed(self, parser):
        """测试混合列表"""
        expr = parser.parse("0 1,3,5 * * *")

        assert expr.hour.is_list is True
        assert expr.hour.values == [1, 3, 5]

    # 测试组合使用
    def test_combined_special_chars(self, parser):
        """测试组合特殊字符"""
        expr = parser.parse("*/10 8-18 * * 1-5")

        assert expr.minute.has_step is True
        assert expr.minute.values == [0, 10, 20, 30, 40, 50]
        assert expr.hour.is_range is True
        assert expr.weekday.is_range is True
        assert expr.weekday.values == [1, 2, 3, 4, 5]


class TestCronAliases:
    """测试 Cron 别名"""

    @pytest.fixture
    def parser(self):
        return CronParser()

    def test_hourly_alias(self, parser):
        """测试 @hourly 别名"""
        expr = parser.parse("@hourly")
        assert expr.minute.values == [0]

    def test_daily_alias(self, parser):
        """测试 @daily 别名"""
        expr = parser.parse("@daily")
        assert expr.minute.values == [0]
        assert expr.hour.values == [0]

    def test_weekly_alias(self, parser):
        """测试 @weekly 别名"""
        expr = parser.parse("@weekly")
        assert expr.minute.values == [0]
        assert expr.hour.values == [0]
        assert expr.weekday.values == [0]  # 周日

    def test_monthly_alias(self, parser):
        """测试 @monthly 别名"""
        expr = parser.parse("@monthly")
        assert expr.minute.values == [0]
        assert expr.hour.values == [0]
        assert expr.day.values == [1]

    def test_yearly_alias(self, parser):
        """测试 @yearly 别名"""
        expr = parser.parse("@yearly")
        assert expr.minute.values == [0]
        assert expr.hour.values == [0]
        assert expr.day.values == [1]
        assert expr.month.values == [1]

    def test_midnight_alias(self, parser):
        """测试 @midnight 别名"""
        expr = parser.parse("@midnight")
        assert expr.hour.values == [0]


class TestCronValidation:
    """测试 Cron 表达式验证"""

    @pytest.fixture
    def parser(self):
        return CronParser()

    def test_validate_valid_expression(self, parser):
        """测试有效表达式验证"""
        is_valid, error = parser.validate("0 * * * *")
        assert is_valid is True
        assert error is None

    def test_validate_valid_expression_extended(self, parser):
        """测试有效 6 位表达式验证"""
        is_valid, error = parser.validate("0 0 * * * *")
        assert is_valid is True
        assert error is None

    def test_validate_invalid_field_count(self, parser):
        """测试无效字段数量"""
        is_valid, error = parser.validate("0 * * *")
        assert is_valid is False
        assert "字段数量" in error

    def test_validate_invalid_value(self, parser):
        """测试无效值"""
        is_valid, error = parser.validate("60 * * * *")  # 分钟超出范围
        assert is_valid is False

    def test_validate_invalid_hour(self, parser):
        """测试无效小时值"""
        is_valid, error = parser.validate("0 25 * * *")  # 小时超出范围
        assert is_valid is False

    def test_validate_empty_string(self, parser):
        """测试空字符串"""
        is_valid, error = parser.validate("")
        assert is_valid is False

    def test_validate_alias(self, parser):
        """测试别名验证"""
        is_valid, error = parser.validate("@hourly")
        assert is_valid is True
        assert error is None


class TestCalculateNextRun:
    """测试下次执行时间计算"""

    @pytest.fixture
    def parser(self):
        return CronParser()

    def test_calculate_next_run_hourly(self, parser):
        """测试每小时执行的下次时间"""
        from_time = datetime(2024, 1, 1, 10, 30, 0)  # 10:30
        next_run = parser.calculate_next_run("0 * * * *", from_time)

        assert next_run is not None
        assert next_run.hour == 11
        assert next_run.minute == 0
        assert next_run.second == 0

    def test_calculate_next_run_daily(self, parser):
        """测试每天执行的下次时间"""
        from_time = datetime(2024, 1, 1, 8, 0, 0)
        next_run = parser.calculate_next_run("0 9 * * *", from_time)

        assert next_run is not None
        assert next_run.hour == 9
        assert next_run.minute == 0

    def test_calculate_next_run_already_passed_today(self, parser):
        """测试今天时间已过的下次执行"""
        from_time = datetime(2024, 1, 1, 15, 0, 0)  # 15:00
        next_run = parser.calculate_next_run("0 10 * * *", from_time)  # 每天 10:00

        assert next_run is not None
        assert next_run.day == 2  # 明天
        assert next_run.hour == 10

    def test_calculate_next_run_specific_time(self, parser):
        """测试特定时间执行"""
        from_time = datetime(2024, 1, 1, 0, 0, 0)
        next_run = parser.parse("30 14 * * *")
        next_time = parser.calculate_next_run("30 14 * * *", from_time)

        assert next_time is not None
        assert next_time.hour == 14
        assert next_time.minute == 30

    def test_calculate_next_run_step(self, parser):
        """测试步进表达式下次执行时间"""
        from_time = datetime(2024, 1, 1, 10, 0, 0)
        next_run = parser.calculate_next_run("*/15 * * * *", from_time)

        assert next_run is not None
        assert next_run.minute in [0, 15, 30, 45]

    def test_calculate_next_run_extended_format(self, parser):
        """测试 6 位格式的下次执行时间"""
        from_time = datetime(2024, 1, 1, 10, 30, 15)
        # 每分钟的整秒 (秒=0, 分=*, 时=*, 日=*, 月=*, 周=*)
        next_run = parser.calculate_next_run("0 * * * * *", from_time)

        assert next_run is not None
        assert next_run.minute == 31
        assert next_run.second == 0

    def test_get_next_runs_multiple(self, parser):
        """测试获取多个下次执行时间"""
        from_time = datetime(2024, 1, 1, 0, 0, 0)
        runs = parser.get_next_runs("0 * * * *", count=5, from_time=from_time)

        assert len(runs) == 5
        # 每次间隔 1 小时
        for i, run in enumerate(runs):
            assert run.hour == i
            assert run.minute == 0

    def test_calculate_next_run_none_on_invalid(self, parser):
        """测试无效表达式返回 None"""
        next_run = parser.calculate_next_run("invalid cron")
        assert next_run is None


class TestCommonCronExpressions:
    """测试常用 Cron 表达式"""

    @pytest.fixture
    def parser(self):
        return CronParser()

    @pytest.mark.parametrize("cron,description", [
        ("* * * * *", "每分钟"),
        ("0 * * * *", "每小时整点"),
        ("0 0 * * *", "每天零点"),
        ("0 9 * * *", "每天 9:00"),
        ("0 9 * * 1", "每周一 9:00"),
        ("0 9 * * 1-5", "每周一到周五 9:00"),
        ("0 9 1 * *", "每月 1 号 9:00"),
        ("0 9 1 1 *", "每年 1 月 1 号 9:00"),
        ("*/15 * * * *", "每 15 分钟"),
        ("0 */2 * * *", "每 2 小时"),
        ("0 9-17 * * *", "每天 9:00-17:00 整点"),
        ("30 14 * * *", "每天 14:30"),
        ("0 0 1 * *", "每月 1 号零点"),
        ("0 0 * * 0", "每周日零点"),
    ])
    def test_common_expressions_valid(self, parser, cron, description):
        """测试常用表达式都能正确解析"""
        is_valid, error = parser.validate(cron)
        assert is_valid is True, f"{description} ({cron}) 验证失败: {error}"

        expr = parser.parse(cron)
        assert expr is not None

        # 确保能计算下次执行时间
        next_run = parser.calculate_next_run(cron)
        assert next_run is not None, f"{description} ({cron}) 无法计算下次执行时间"

    @pytest.mark.parametrize("cron,description,expected_hour,expected_minute", [
        ("0 * * * *", "每小时整点", None, 0),
        ("0 9 * * *", "每天 9:00", 9, 0),
        ("30 14 * * *", "每天 14:30", 14, 30),
    ])
    def test_common_expressions_next_run(
        self, parser, cron, description, expected_hour, expected_minute
    ):
        """测试常用表达式的下次执行时间"""
        from_time = datetime(2024, 1, 1, 8, 0, 0)
        next_run = parser.calculate_next_run(cron, from_time)

        assert next_run is not None
        if expected_minute is not None:
            assert next_run.minute == expected_minute
        if expected_hour is not None:
            assert next_run.hour == expected_hour


class TestIsDueFunction:
    """测试 is_due 函数"""

    def test_is_due_when_passed(self):
        """测试时间已过"""
        past_time = datetime(2020, 1, 1, 0, 0, 0).isoformat()
        assert is_due(past_time) is True

    def test_is_due_when_future(self):
        """测试时间未到"""
        future_time = datetime(2099, 12, 31, 23, 59, 59).isoformat()
        assert is_due(future_time) is False

    def test_is_due_with_none(self):
        """测试 None 值"""
        assert is_due(None) is False

    def test_is_due_with_invalid_format(self):
        """测试无效格式"""
        assert is_due("invalid time") is False
        assert is_due("") is False

    def test_is_due_with_timezone(self):
        """测试带时区的时间"""
        # 使用 UTC 时间
        past_time = "2020-01-01T00:00:00+00:00"
        assert is_due(past_time) is True


class TestFormatNextRun:
    """测试 format_next_run 函数"""

    def test_format_next_run_basic(self):
        """测试基本格式化"""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = format_next_run(dt)

        assert result == "2024-01-15 10:30:45"

    def test_format_next_run_midnight(self):
        """测试零点格式化"""
        dt = datetime(2024, 12, 31, 0, 0, 0)
        result = format_next_run(dt)

        assert result == "2024-12-31 00:00:00"

    def test_format_next_run_first_day(self):
        """测试月初格式化"""
        dt = datetime(2024, 1, 1, 0, 0, 0)
        result = format_next_run(dt)

        assert result == "2024-01-01 00:00:00"


class TestCronParserCache:
    """测试 Cron 解析器缓存"""

    def test_cache_same_expression(self):
        """测试相同表达式使用缓存"""
        parser = CronParser()
        cron = "0 * * * *"

        expr1 = parser.parse(cron)
        expr2 = parser.parse(cron)

        # 缓存的结果应该是同一个对象
        assert expr1 is expr2

    def test_cache_different_expressions(self):
        """测试不同表达式不使用缓存"""
        parser = CronParser()

        expr1 = parser.parse("0 * * * *")
        expr2 = parser.parse("*/5 * * * *")

        # 不同的表达式应该是不同对象
        assert expr1 is not expr2


class TestEdgeCases:
    """测试边界条件"""

    @pytest.fixture
    def parser(self):
        return CronParser()

    def test_year_boundary(self, parser):
        """测试跨年边界"""
        from_time = datetime(2024, 12, 31, 23, 59, 0)
        next_run = parser.calculate_next_run("0 0 1 1 *", from_time)  # 每年 1 月 1 日

        assert next_run is not None
        assert next_run.year == 2025
        assert next_run.month == 1
        assert next_run.day == 1

    def test_month_boundary(self, parser):
        """测试跨月边界"""
        from_time = datetime(2024, 1, 31, 23, 0, 0)
        next_run = parser.calculate_next_run("0 0 1 * *", from_time)  # 每月 1 号

        assert next_run is not None
        assert next_run.month == 2
        assert next_run.day == 1

    def test_february_last_day(self, parser):
        """测试 2 月末尾"""
        # 注意：L 支持月末
        from_time = datetime(2024, 2, 28, 0, 0, 0)
        next_run = parser.calculate_next_run("0 0 L * *", from_time)

        # L 是月末，2 月的最后一天是 29 日（2024 是闰年）
        assert next_run is not None
        assert next_run.day == 29

    def test_february_last_day_non_leap(self, parser):
        """测试非闰年 2 月末尾"""
        from_time = datetime(2023, 2, 28, 0, 0, 0)  # 2023 不是闰年
        next_run = parser.calculate_next_run("0 0 L * *", from_time)

        assert next_run is not None
        assert next_run.day == 28

    def test_max_minute_value(self, parser):
        """测试最大分钟值"""
        expr = parser.parse("59 * * * *")
        assert 59 in expr.minute.values

    def test_max_hour_value(self, parser):
        """测试最大小时值"""
        expr = parser.parse("0 23 * * *")
        assert 23 in expr.hour.values

    def test_max_day_value(self, parser):
        """测试最大日期值"""
        expr = parser.parse("0 0 31 * *")
        assert 31 in expr.day.values

    def test_weekday_sunday_both_formats(self, parser):
        """测试周日可以用 0 或 7"""
        expr0 = parser.parse("0 0 * * 0")
        expr7 = parser.parse("0 0 * * 7")

        # 7 会被转换为 0
        assert 0 in expr0.weekday.values
        assert 0 in expr7.weekday.values

    def test_whitespace_handling(self, parser):
        """测试空白处理"""
        expr1 = parser.parse("0 * * * *")
        expr2 = parser.parse("  0   *  *  *  *  ")
        expr3 = parser.parse("0\t*\t*\t*\t*")

        assert expr1.minute.values == expr2.minute.values
        assert expr1.minute.values == expr3.minute.values
