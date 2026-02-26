# 任务调度 - Cron 表达式解析器设计

> 本文档定义 Cron 表达式解析器的技术设计，支持 5 位和 6 位格式。

## 1. 概述

### 1.1 功能目标

Cron 表达式解析器负责：
- 解析 Cron 表达式（支持 5 位和 6 位格式）
- 验证表达式有效性
- 计算下次执行时间
- 判断定时任务是否到期

### 1.2 使用场景

```python
# 创建定时任务时解析 Cron 表达式
scheduled_task = ScheduledTask(
    name="每日代码检查",
    cron="0 9 * * *",  # 每天 9:00 执行
    ...
)

# 计算下次执行时间
next_run = cron_parser.calculate_next_run(scheduled_task.cron)
# -> 2024-01-15T09:00:00

# 检查是否到期
is_due = cron_parser.is_due(scheduled_task.next_run)
# -> True/False
```

---

## 2. Cron 表达式格式

### 2.1 5 位标准格式

标准 Unix Cron 格式：`分 时 日 月 周`

| 位置 | 字段 | 取值范围 | 允许特殊字符 |
|------|------|----------|--------------|
| 1 | 分钟 (minute) | 0-59 | * , - / |
| 2 | 小时 (hour) | 0-23 | * , - / |
| 3 | 日期 (day) | 1-31 | * , - / ? L W |
| 4 | 月份 (month) | 1-12 | * , - / |
| 5 | 星期 (weekday) | 0-6 | * , - / ? L # |

> 注意：星期 0 和 7 都表示星期日

### 2.2 6 位扩展格式

扩展格式：`秒 分 时 日 月 周`

| 位置 | 字段 | 取值范围 | 允许特殊字符 |
|------|------|----------|--------------|
| 1 | 秒 (second) | 0-59 | * , - / |
| 2 | 分钟 (minute) | 0-59 | * , - / |
| 3 | 小时 (hour) | 0-23 | * , - / |
| 4 | 日期 (day) | 1-31 | * , - / ? L W |
| 5 | 月份 (month) | 1-12 | * , - / |
| 6 | 星期 (weekday) | 0-6 | * , - / ? L # |

### 2.3 字段别名

| 别名 | 对应值 |
|------|--------|
| @yearly | 0 0 1 1 * |
| @annually | 0 0 1 1 * |
| @monthly | 0 0 1 * * |
| @weekly | 0 0 * * 0 |
| @daily | 0 0 * * * |
| @midnight | 0 0 * * * |
| @hourly | 0 * * * * |

---

## 3. 特殊字符语义

### 3.1 通配符 `*`

表示任意值。

```python
# 每小时的每分钟
"* * * * *"

# 每天的任何时间
"0 0 * * *"
```

### 3.2 范围 `-`

表示连续范围。

```python
# 每天 9 点到 17 点
"0 9-17 * * *"

# 工作日 (周一到周五)
"0 9 * * 1-5"

# 1 月到 3 月
"0 0 1 1-3 *"
```

### 3.3 列表 `,`

表示多个离散值。

```python
# 每天 9 点、12 点、18 点
"0 9,12,18 * * *"

# 周一、周三、周五
"0 9 * * 1,3,5"

# 1 月、6 月、12 月
"0 0 1 1,6,12 *"
```

### 3.4 步进 `/`

表示间隔值。

```python
# 每 5 分钟
"*/5 * * * *"

# 每小时的每 15 分钟
"*/15 * * * *"

# 每天 0 点开始，每 6 小时
"0 */6 * * *"

# 1 月到 12 月，每 3 个月
"0 0 1 */3 *"

# 每 30 秒 (6 位格式)
"*/30 * * * * *"
```

### 3.5 日期和星期互斥 `?`

在 5 位格式中，`?` 表示"不指定"，用于日期和星期互斥的场景。

```python
# 每月 15 日执行，不关心星期
"0 0 15 * *"

# 每周周一执行，不关心日期
"0 0 * * 1"

# 每月最后一个工作日
"0 0 L * *"

# 每月第 3 个周五
"0 0 * * 5#3"
```

### 3.6 月末 `L`

表示月末（最后一天）。

```python
# 每月最后一天
"0 0 L * *"

# 每周最后一天 (周六)
"0 0 * * 6L"

# 每月最后一个工作日 (周一到周五)
"0 0 LW * *"
```

### 3.7 最近工作日 `W`

表示距离指定日期最近的工作日。

```python
# 每月 15 日最近的工作日
"0 0 15W * *"

# 每月最后一天最近的工作日
"0 0 LW * *"
```

### 3.8 星期序号 `#`

表示第几个星期几。

```python
# 每月第 3 个周五 (5#3)
"0 0 * * 5#3"

# 每月第 2 个周一
"0 0 * * 1#2"

# 每月第 1 个和第 3 个周五
"0 0 * * 5#1,5#3"
```

---

## 4. 解析算法设计

### 4.1 核心类设计

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class CronField:
    """Cron 字段"""
    field_type: str           # second/minute/hour/day/month/weekday
    values: list[int]         # 可能的值列表
    has_wildcard: bool        # 是否包含通配符
    has_step: bool            # 是否有步进值
    step_value: int           # 步进值
    is_range: bool            # 是否是范围
    range_start: int          # 范围开始
    range_end: int            # 范围结束
    is_list: bool             # 是否是列表
    list_values: list[int]   # 列表值

@dataclass
class CronExpression:
    """Cron 表达式"""
    is_extended: bool         # 是否是 6 位格式
    second: Optional[CronField]
    minute: CronField
    hour: CronField
    day: CronField
    month: CronField
    weekday: CronField

class CronParser:
    """Cron 表达式解析器"""

    # 字段范围定义
    RANGES = {
        "second": (0, 59),
        "minute": (0, 59),
        "hour": (0, 23),
        "day": (1, 31),
        "month": (1, 12),
        "weekday": (0, 6),
    }

    # 月份别名
    MONTH_ALIASES = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "may": 5, "jun": 6, "jul": 7, "aug": 8,
        "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    # 星期别名
    WEEKDAY_ALIASES = {
        "sun": 0, "mon": 1, "tue": 2, "wed": 3,
        "thu": 4, "fri": 5, "sat": 6,
    }
```

### 4.2 解析流程

```python
def parse(self, cron: str) -> CronExpression:
    """
    解析 Cron 表达式

    1. 去除首尾空白
    2. 检查是否是别名
    3. 按空格分割字段
    4. 判断是 5 位还是 6 位格式
    5. 解析每个字段
    6. 验证字段有效性
    """
    cron = cron.strip()

    # 检查别名
    if cron in self.ALIASES:
        cron = self.ALIASES[cron]

    fields = cron.split()

    # 判断格式
    if len(fields) == 5:
        return self._parse_standard_format(fields)
    elif len(fields) == 6:
        return self._parse_extended_format(fields)
    else:
        raise ValueError(f"无效的 Cron 表达式格式: {len(fields)} 个字段")

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
    field = field.lower()

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

    # 处理步进
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

    # 处理列表
    if "," in field:
        parts = field.split(",")
        values = []
        list_values = []
        for part in parts:
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

    # 处理范围
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
```

### 4.3 别名解析

```python
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

    # 检查是否是数字
    if value.isdigit():
        return int(value)

    raise ValueError(f"无效的 {field_type} 值: {value}")
```

---

## 5. 下次执行时间计算算法

### 5.1 算法概述

计算下次执行时间的核心思路：
1. 从当前时间开始
2. 依次递增时间单位（秒/分/时/日/月）
3. 检查每个候选时间是否匹配 Cron 表达式
4. 返回第一个匹配的时间

### 5.2 实现设计

```python
from datetime import datetime, timedelta

class CronParser:

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

        expression = self.parse(cron)
        current = from_time.replace(second=0, microsecond=0)

        # 最多尝试计算 1 年内的下一个执行时间
        max_iterations = 365 * 24 * 60 * 60  # 1 年的秒数

        for _ in range(max_iterations):
            if self._matches(expression, current):
                return current

            # 递增到下一秒
            current = current + timedelta(seconds=1)

            # 快速跳过不可能匹配的时间
            current = self._skip_to_next_valid(current, expression)

        return None

    def _matches(self, expression: CronExpression, dt: datetime) -> bool:
        """检查时间是否匹配 Cron 表达式"""
        # 检查秒
        if expression.second is not None:
            if not self._field_matches(expression.second, dt.second):
                return False

        # 检查分钟
        if not self._field_matches(expression.minute, dt.minute):
            return False

        # 检查小时
        if not self._field_matches(expression.hour, dt.hour):
            return False

        # 检查日期
        if not self._field_matches(expression.day, dt.day):
            return False

        # 检查月份
        if not self._field_matches(expression.month, dt.month):
            return False

        # 检查星期
        # 注意：Python 的 weekday() 返回 0-6 (周一=0)
        # Cron 的星期 0 和 7 都是周日
        weekday = dt.weekday()
        if not self._field_matches(expression.weekday, weekday):
            return False

        return True

    def _field_matches(self, field: CronField, value: int) -> bool:
        """检查字段值是否匹配"""
        # 处理 L (月末)
        if field.field_type == "day" and value == 31:
            # 检查是否月末
            # 实际实现需要考虑不同月份的天数
            return True  # 简化处理

        # 处理 n#k 格式
        # 需要特殊处理

        return value in field.values
```

### 5.3 优化算法

```python
def _skip_to_next_valid(
    self,
    current: datetime,
    expression: CronExpression,
) -> datetime:
    """
    快速跳转到下一个可能匹配的时间

    优化策略：
    1. 如果分钟不匹配，跳转到下一个匹配分钟的开始
    2. 如果小时不匹配，跳转到下一个匹配小时的开始
    3. 依此类推
    """
    # 简化实现：每次跳过 1 分钟
    # 实际实现应根据字段匹配情况优化跳过策略
    return current + timedelta(minutes=1)
```

---

## 6. 表达式验证规则

### 6.1 验证项目

```python
class CronParser:

    def validate(self, cron: str) -> tuple[bool, Optional[str]]:
        """
        验证 Cron 表达式有效性

        Returns:
            (is_valid, error_message)
        """
        try:
            # 1. 检查格式
            fields = cron.strip().split()
            if len(fields) not in (5, 6):
                return False, f"字段数量必须是 5 或 6，当前为 {len(fields)}"

            # 2. 解析表达式
            expression = self.parse(cron)

            # 3. 验证每个字段
            for field, field_type in [
                (expression.second, "second") if expression.second else (None, None),
                (expression.minute, "minute"),
                (expression.hour, "hour"),
                (expression.day, "day"),
                (expression.month, "month"),
                (expression.weekday, "weekday"),
            ]:
                if field is None:
                    continue

                if not self._validate_field(field, field_type):
                    return False, f"{field_type} 字段值无效"

            # 4. 检查日期和星期的互斥
            # 如果两者都指定了非通配符值，返回警告

            # 5. 计算下次执行时间
            next_run = self.calculate_next_run(cron)
            if next_run is None:
                return False, "无法计算下次执行时间"

            return True, None

        except Exception as e:
            return False, str(e)

    def _validate_field(self, field: CronField, field_type: str) -> bool:
        """验证字段值是否在有效范围内"""
        min_val, max_val = self.RANGES[field_type]

        for value in field.values:
            if value < min_val or value > max_val:
                return False

        return True
```

### 6.2 错误消息示例

| 错误类型 | 错误消息 |
|----------|----------|
| 字段数量错误 | "字段数量必须是 5 或 6，当前为 4" |
| 数值范围错误 | "minute 字段值 60 超出有效范围 0-59" |
| 无效字符 | "day 字段包含无效字符: abc" |
| 月份别名错误 | "month 字段包含无效别名: xyz" |
| 无法计算下次时间 | "无法计算下次执行时间" |

---

## 7. 到期检查

### 7.1 判断任务是否到期

```python
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
        next_run_time = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
        now = datetime.now(next_run_time.tzinfo)
        return now >= next_run_time
    except (ValueError, AttributeError):
        return False
```

### 7.2 更新下次执行时间

```python
def update_next_run(scheduled_task: ScheduledTask) -> str:
    """
    更新定时任务的下次执行时间

    Args:
        scheduled_task: 定时任务对象

    Returns:
        新的下次执行时间 (ISO 格式字符串)
    """
    if not scheduled_task.enabled:
        return scheduled_task.next_run

    # 计算新的下次执行时间
    last_run = scheduled_task.last_run

    if last_run:
        # 从上次执行时间开始计算
        last_run_time = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
        next_run = cron_parser.calculate_next_run(
            scheduled_task.cron,
            from_time=last_run_time,
        )
    else:
        # 没有上次执行时间，从当前时间计算
        next_run = cron_parser.calculate_next_run(scheduled_task.cron)

    if next_run:
        return next_run.isoformat()

    return scheduled_task.next_run
```

---

## 8. 常用 Cron 表达式示例

### 8.1 标准 5 位格式

| 表达式 | 含义 | 示例输出 |
|--------|------|----------|
| `* * * * *` | 每分钟 | 每分钟的 0 秒 |
| `*/5 * * * *` | 每 5 分钟 | 0, 5, 10, ... 分钟 |
| `*/15 * * * *` | 每 15 分钟 | 0, 15, 30, 45 分钟 |
| `0 * * * *` | 每小时 | 每小时整点 |
| `0 */2 * * *` | 每 2 小时 | 0, 2, 4, ... 点 |
| `0 9 * * *` | 每天 9 点 | 每天 09:00 |
| `0 9,18 * * *` | 每天 9 点和 18 点 | 每天 09:00, 18:00 |
| `0 9 * * 1-5` | 工作日 9 点 | 周一至周五 09:00 |
| `0 9 * * 1,3,5` | 周一、周三、周五 9 点 | 每周一三五 09:00 |
| `0 0 1 * *` | 每月 1 日 0 点 | 每月 1 日 00:00 |
| `0 0 1,15 * *` | 每月 1 日和 15 日 0 点 | 每月 1, 15 日 00:00 |
| `0 0 L * *` | 每月最后一天 0 点 | 每月最后一天 00:00 |
| `0 9 1 * *` | 每月 1 日 9 点 | 每月 1 日 09:00 |
| `0 9 * * 1#1` | 每月第一个周一 9 点 | 每月第一个周一 09:00 |

### 8.2 扩展 6 位格式

| 表达式 | 含义 | 示例输出 |
|--------|------|----------|
| `0 * * * * *` | 每分钟 | 每分钟 0 秒 |
| `30 * * * * *` | 每分钟的 30 秒 | 每分钟 30 秒 |
| `0,30 * * * * *` | 每 30 秒 | 0, 30 秒 |
| `0 0 0 * * *` | 每天午夜 | 每天 00:00:00 |
| `0 0 9 * * *` | 每天 9 点 | 每天 09:00:00 |
| `0 0 9,12,18 * * *` | 每天 9/12/18 点 | 每天 09:00:00, 12:00:00, 18:00:00 |

---

## 9. 接口设计

### 9.1 公开 API

```python
class CronParser:
    """Cron 表达式解析器"""

    def __init__(self):
        """初始化解析器"""
        pass

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
        pass

    def validate(self, cron: str) -> tuple[bool, Optional[str]]:
        """
        验证 Cron 表达式

        Args:
            cron: Cron 表达式字符串

        Returns:
            (is_valid, error_message) 元组
        """
        pass

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
        pass

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
        pass


def is_due(next_run: Optional[str]) -> bool:
    """
    判断任务是否到期

    Args:
        next_run: 下次执行时间 (ISO 格式字符串)

    Returns:
        是否到期
    """
    pass


def format_next_run(dt: datetime) -> str:
    """
    格式化下次执行时间

    Args:
        dt: 日期时间对象

    Returns:
        格式化的时间字符串
    """
    pass
```

### 9.2 使用示例

```python
# 创建解析器实例
parser = CronParser()

# 验证表达式
is_valid, error = parser.validate("0 9 * * *")
if not is_valid:
    print(f"无效的表达式: {error}")

# 计算下次执行时间
next_run = parser.calculate_next_run("0 9 * * *")
print(f"下次执行时间: {next_run}")

# 获取未来 5 个执行时间
next_runs = parser.get_next_runs("*/5 * * * *", count=5)
for run in next_runs:
    print(f"  - {run}")

# 检查是否到期
if is_due(scheduled_task.next_run):
    print("任务已到期")
```

---

## 10. 错误处理

### 10.1 异常类型

```python
class CronParseError(Exception):
    """Cron 解析错误"""
    pass


class CronValidationError(CronParseError):
    """Cron 验证错误"""
    pass


class CronCalculationError(CronParseError):
    """Cron 计算错误"""
    pass
```

### 10.2 错误处理策略

| 错误类型 | 处理策略 |
|----------|----------|
| 格式错误 | 抛出 CronParseError，包含详细错误信息 |
| 值越界 | 抛出 CronValidationError，指出具体字段和值 |
| 计算超时 | 返回 None，记录警告日志 |
| 无效别名 | 抛出 CronValidationError，建议有效别名 |

---

## 11. 测试用例

### 11.1 标准格式解析测试

```python
def test_standard_format():
    parser = CronParser()

    # 测试通配符
    expr = parser.parse("* * * * *")
    assert expr.minute.values == list(range(0, 60))
    assert expr.hour.values == list(range(0, 24))

    # 测试范围
    expr = parser.parse("0 9-17 * * *")
    assert expr.hour.values == list(range(9, 18))

    # 测试列表
    expr = parser.parse("0 9,12,18 * * *")
    assert expr.hour.values == [9, 12, 18]

    # 测试步进
    expr = parser.parse("*/5 * * * *")
    assert expr.minute.values == [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
```

### 11.2 下次执行时间测试

```python
def test_calculate_next_run():
    parser = CronParser()

    # 测试每 5 分钟
    from datetime import datetime
    now = datetime(2024, 1, 15, 10, 3, 0)

    next_run = parser.calculate_next_run("*/5 * * * *", from_time=now)
    assert next_run == datetime(2024, 1, 15, 10, 5, 0)

    # 测试每天 9 点
    now = datetime(2024, 1, 15, 10, 0, 0)
    next_run = parser.calculate_next_run("0 9 * * *", from_time=now)
    assert next_run == datetime(2024, 1, 16, 9, 0, 0)
```

---

## 12. 性能考虑

### 12.1 缓存策略

- 解析结果缓存：相同表达式只解析一次
- 下次执行时间缓存：定时任务对象缓存

### 12.2 计算优化

- 快速跳过不匹配的时间
- 使用数学计算替代循环（步进场景）
- 设置最大迭代次数防止无限循环

### 12.3 边界情况

- 处理夏令时切换
- 处理闰年
- 处理月份天数差异（28/29/30/31）
