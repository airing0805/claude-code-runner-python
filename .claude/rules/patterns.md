# 设计模式

> 本文件定义项目中使用的设计模式和架构约定。

## 架构概览

```
┌─────────────────────────────────────────────────┐
│                   FastAPI App                    │
│  app/main.py - 路由、请求处理、SSE 流式输出      │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│               ClaudeCodeClient                   │
│  src/claude_runner/client.py - SDK 封装核心     │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│               Claude Code                         │
│  claude-code - Anthropic 官方工具               │
└─────────────────────────────────────────────────┘
```

## 核心模式

### 1. 客户端封装模式

封装第三方 SDK，提供统一接口：

```python
class ClaudeCodeClient:
    """
    Claude Code 客户端封装

    职责:
    - 封装 SDK 调用细节
    - 提供流式和同步两种执行模式
    - 跟踪工具使用和文件变更
    - 处理环境变量管理（嵌套调用）
    """

    def __init__(self, config: ClientConfig):
        self._config = config
        self._files_changed: list[str] = []
        self._tools_used: list[str] = []

    async def run(self, prompt: str) -> TaskResult:
        """同步执行，返回完整结果"""
        ...

    async def run_stream(self, prompt: str) -> AsyncIterator[StreamMessage]:
        """流式执行，逐步返回消息"""
        ...
```

### 2. 数据传输对象 (DTO)

使用 Pydantic 和 dataclass 定义数据结构：

```python
# Pydantic - API 边界
class TaskRequest(BaseModel):
    prompt: str
    working_dir: str | None = None

class TaskResponse(BaseModel):
    success: bool
    message: str
    files_changed: list[str] = []

# dataclass - 内部使用
@dataclass
class TaskResult:
    success: bool
    message: str
    files_changed: list[str] = field(default_factory=list)
```

### 3. 异步迭代器模式

流式处理使用 AsyncIterator：

```python
async def run_stream(self, prompt: str) -> AsyncIterator[StreamMessage]:
    """
    流式返回消息

    优点:
    - 实时反馈进度
    - 减少内存占用
    - 支持长时间运行的任务
    """
    async with ClaudeSDKClient(options=self._create_options()) as client:
        await client.query(prompt)

        async for message in client.receive_response():
            stream_msg = self._process_message(message)
            if stream_msg:
                yield stream_msg
```

### 4. 上下文管理器模式

资源管理使用 async context manager：

```python
async def run_stream(self, prompt: str) -> AsyncIterator[StreamMessage]:
    # 保存环境变量状态
    old_env = os.environ.pop("CLAUDECODE", None)

    try:
        async with ClaudeSDKClient(options=options) as client:
            yield from process(client)
    finally:
        # 恢复环境变量
        if old_env is not None:
            os.environ["CLAUDECODE"] = old_env
```

## 设计原则

### 单一职责 (SRP)

每个类/模块只做一件事：

```python
# 正确 ✅ - 职责清晰
class ClaudeCodeClient:
    """只负责与 Claude SDK 交互"""
    pass

class SessionManager:
    """只负责会话管理"""
    pass

class ProjectService:
    """只负责项目相关操作"""
    pass

# 错误 ❌ - 职责混乱
class ClaudeApp:
    def run_task(self): ...
    def manage_sessions(self): ...
    def handle_http(self): ...
```

### 依赖注入

通过参数传递依赖：

```python
# 正确 ✅
def create_client(config: Config) -> ClaudeCodeClient:
    return ClaudeCodeClient(
        working_dir=config.working_dir,
        permission_mode=config.permission_mode,
    )

# 错误 ❌ - 硬编码依赖
def create_client() -> ClaudeCodeClient:
    working_dir = os.getenv("WORKING_DIR")  # 隐式依赖
    return ClaudeCodeClient(working_dir=working_dir)
```

### 不可变性

优先使用不可变数据：

```python
# 正确 ✅ - 返回新对象
def add_tool(self, tool: str) -> "ClaudeCodeClient":
    return ClaudeCodeClient(
        working_dir=self.working_dir,
        allowed_tools=[*self.allowed_tools, tool],
    )

# 也可以使用 frozen dataclass
@dataclass(frozen=True)
class TaskConfig:
    prompt: str
    tools: tuple[str, ...] = ()
```

## 错误处理模式

### Result 模式

使用数据类表示结果：

```python
@dataclass
class TaskResult:
    success: bool
    message: str
    error: str | None = None
    files_changed: list[str] = field(default_factory=list)

async def run(self, prompt: str) -> TaskResult:
    try:
        # 执行任务
        return TaskResult(success=True, message=result)
    except Exception as e:
        return TaskResult(success=False, message="", error=str(e))
```

### 分层错误处理

```python
# SDK 层 - 原始异常
async def run_stream(self, prompt: str) -> AsyncIterator[StreamMessage]:
    try:
        async for msg in client.receive_response():
            yield msg
    except Exception as e:
        yield StreamMessage(type=MessageType.ERROR, content=str(e))

# API 层 - 用户友好消息
@app.exception_handler(TaskError)
async def handle_task_error(request: Request, exc: TaskError):
    return JSONResponse(
        status_code=400,
        content={"error": exc.user_message},
    )
```

## 配置模式

### 环境变量配置

```python
from dataclasses import dataclass
import os

@dataclass
class Config:
    """应用配置"""
    working_dir: str
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            working_dir=os.getenv("WORKING_DIR", "."),
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "8000")),
        )
```

### 配置验证

```python
def validate_config(config: Config) -> None:
    """验证配置有效性"""
    if not Path(config.working_dir).exists():
        raise ValueError(f"工作目录不存在: {config.working_dir}")

    if not (1 <= config.port <= 65535):
        raise ValueError(f"无效端口: {config.port}")
```

## 项目结构

```
claude-code-runner/
├── app/
│   ├── main.py           # FastAPI 应用入口
│   ├── templates/        # Jinja2 模板
│   └── static/           # 静态文件
├── src/
│   └── claude_runner/
│       ├── __init__.py   # 公开 API
│       └── client.py     # 核心客户端
├── tests/
│   ├── conftest.py       # 共享 fixtures
│   └── test_runner.py    # 测试用例
├── .env.example          # 环境变量模板
├── pyproject.toml        # 项目配置
└── CLAUDE.md             # 项目说明
```
