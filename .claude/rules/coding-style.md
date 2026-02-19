# Python 编码风格

> 本文件定义项目的 Python 编码规范，遵循 PEP 8 和现代 Python 最佳实践。

## 代码组织

### 文件结构

```python
# 1. 模块文档字符串
"""模块描述 - 一行概述"""

# 2. 导入（按顺序分组）
import standard_library
import third_party
from local_package import module

# 3. 常量
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# 4. 类型定义（使用 TypeAlias）
type MessageId = str
type JsonDict = dict[str, Any]

# 5. 异常类
class CustomError(Exception): ...

# 6. 数据类
@dataclass
class Config:
    name: str
    value: int

# 7. 类定义
class Service:
    pass

# 8. 函数定义
def main() -> None: ...
```

### 文件大小限制

- **单文件不超过 400 行**（理想状态 200-300 行）
- **函数不超过 50 行**
- **类方法不超过 30 行**
- 超过限制时考虑拆分模块

## 类型注解

### 必须使用类型注解

```python
# 正确 ✅
def process_message(
    content: str,
    timeout: float = 30.0,
) -> TaskResult:
    ...

# 错误 ❌
def process_message(content, timeout=30.0):
    ...
```

### 使用现代类型语法 (Python 3.12+)

```python
# 使用 type 别名
type MessageId = str
type Headers = dict[str, str]
type Handler = Callable[[str], Awaitable[None]]

# 使用泛型
type Results[T] = list[T]
```

### Optional 使用

```python
# 使用 Optional 或 | None
def find_session(session_id: str) -> Session | None:
    ...

# 或更简洁
def get_config(key: str) -> str | None:
    ...
```

## 数据结构

### 优先使用 dataclass

```python
from dataclasses import dataclass, field

@dataclass
class StreamMessage:
    """流式消息"""
    type: MessageType
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tool_name: str | None = None
    metadata: dict = field(default_factory=dict)
```

### 不可变性

```python
# 使用 frozen=True 创建不可变数据类
@dataclass(frozen=True)
class TaskConfig:
    prompt: str
    working_dir: str
    tools: tuple[str, ...] = ()
```

### Enum 使用

```python
from enum import Enum, auto

class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    TOOL_USE = "tool_use"
    ERROR = "error"
    COMPLETE = "complete"
```

## 函数设计

### 纯函数优先

```python
# 正确 ✅ - 纯函数，返回新对象
def merge_headers(base: dict, extra: dict) -> dict:
    return {**base, **extra}

# 错误 ❌ - 修改参数
def merge_headers(base: dict, extra: dict) -> None:
    base.update(extra)  # 副作用！
```

### 单一职责

```python
# 正确 ✅
def validate_prompt(prompt: str) -> bool:
    return bool(prompt and len(prompt) <= 10000)

def create_client(config: Config) -> ClaudeCodeClient:
    return ClaudeCodeClient(working_dir=config.working_dir)

# 错误 ❌ - 做太多事情
def validate_and_create_and_run(prompt: str) -> TaskResult:
    ...
```

## 异步编程

### async/await 规范

```python
# 使用 async context manager
async with ClaudeSDKClient(options=options) as client:
    await client.query(prompt)
    async for message in client.receive_response():
        yield message

# 使用 AsyncIterator 作为返回类型
async def stream_messages(prompt: str) -> AsyncIterator[StreamMessage]:
    async for msg in self.receive():
        yield msg
```

### 并发控制

```python
# 使用 asyncio.gather 并行执行
results = await asyncio.gather(
    fetch_session(session_id),
    fetch_messages(session_id),
    return_exceptions=True,
)

# 使用 asyncio.Semaphore 限制并发
semaphore = asyncio.Semaphore(10)
async with semaphore:
    await process_task(task)
```

## 错误处理

### 显式异常处理

```python
# 正确 ✅
async def run_task(prompt: str) -> TaskResult:
    try:
        result = await self._execute(prompt)
        return TaskResult(success=True, message=result)
    except ClaudeAPIError as e:
        logger.error(f"API 错误: {e}")
        return TaskResult(success=False, message=str(e))
    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        raise
```

### 使用 contextlib

```python
from contextlib import suppress

# 安全忽略特定异常
with suppress(KeyError, AttributeError):
    value = data["nested"]["key"]
```

## 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 模块 | snake_case | `claude_runner.py` |
| 类 | PascalCase | `ClaudeCodeClient` |
| 函数 | snake_case | `run_stream()` |
| 变量 | snake_case | `session_id` |
| 常量 | UPPER_SNAKE | `MAX_RETRIES` |
| 私有属性 | _leading_underscore | `_files_changed` |
| 保护方法 | _leading_underscore | `_create_options()` |

## 导入规范

```python
# 标准库
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

# 第三方
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 本地
from app.claude_runner import ClaudeCodeClient
from app.claude_runner.client import MessageType
```

## 文档字符串

```python
def run_stream(
    self,
    prompt: str,
    on_message: Callable[[StreamMessage], None] | None = None,
) -> AsyncIterator[StreamMessage]:
    """
    执行任务并流式返回消息

    Args:
        prompt: 任务提示文本
        on_message: 可选的消息回调函数

    Yields:
        StreamMessage: 流式消息对象

    Example:
        async for msg in client.run_stream("hello"):
            print(msg.content)
    """
```
