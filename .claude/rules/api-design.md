# REST API 设计指南

> 本文件定义 FastAPI 项目中 REST API 的设计规范。

## 路由设计

### URL 命名约定

```python
# 资源使用复数名词
@app.get("/api/sessions")          # ✅ 正确
@app.get("/api/session")           # ❌ 错误

@app.get("/api/projects/{id}/sessions")  # ✅ 嵌套资源

# 使用 kebab-case（多单词）
@app.get("/api/task-results")      # ✅ 正确
@app.get("/api/taskResults")       # ❌ 错误
```

### HTTP 方法语义

| 方法 | 用途 | 幂等性 |
|------|------|--------|
| GET | 获取资源 | 是 |
| POST | 创建资源/执行操作 | 否 |
| PUT | 完整更新资源 | 是 |
| PATCH | 部分更新资源 | 是 |
| DELETE | 删除资源 | 是 |

```python
# 执行任务 (非幂等操作)
@app.post("/api/task")
async def run_task(task: TaskRequest): ...

# 获取状态 (幂等)
@app.get("/api/status")
async def get_status(): ...

# 流式输出
@app.post("/api/task/stream")
async def run_task_stream(task: TaskRequest): ...
```

## 响应格式

### 统一响应结构

```python
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    success: bool
    data: T | None = None
    error: str | None = None
    metadata: dict = {}

# 使用示例
@app.get("/api/sessions", response_model=APIResponse[list[Session]])
async def list_sessions():
    sessions = await get_sessions()
    return APIResponse(success=True, data=sessions)
```

### 状态码使用

```python
from fastapi import HTTPException

# 200 - 成功
return {"status": "ok"}

# 201 - 创建成功
return TaskResponse(...), status_code=201

# 400 - 请求参数错误
raise HTTPException(status_code=400, detail="参数验证失败")

# 404 - 资源不存在
raise HTTPException(status_code=404, detail="会话不存在")

# 500 - 服务器错误
raise HTTPException(status_code=500, detail="内部服务错误")
```

## 请求模型

### Pydantic 模型定义

```python
from pydantic import BaseModel, Field
from typing import Optional

class TaskRequest(BaseModel):
    """任务请求模型"""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="任务提示文本",
    )
    working_dir: Optional[str] = Field(
        None,
        description="工作目录",
    )
    tools: Optional[list[str]] = Field(
        None,
        description="允许使用的工具列表",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "帮我分析这个项目的结构",
                "working_dir": "/home/user/project",
                "tools": ["Read", "Glob"],
            }
        }
```

### 响应模型

```python
class TaskResponse(BaseModel):
    """任务响应模型"""
    success: bool
    message: str
    session_id: Optional[str] = None
    cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    files_changed: list[str] = []
    tools_used: list[str] = []
```

## 分页

### 分页参数

```python
from pydantic import BaseModel, Field

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页数量")

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T]
    total: int
    page: int
    limit: int
    pages: int

@app.get("/api/sessions")
async def list_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[Session]:
    offset = (page - 1) * limit
    items = get_sessions(offset, limit)
    total = count_sessions()
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )
```

## 流式响应 (SSE)

```python
from fastapi.responses import StreamingResponse
import json

@app.post("/api/task/stream")
async def run_task_stream(task: TaskRequest):
    """SSE 流式输出"""

    async def event_generator():
        client = ClaudeCodeClient()

        async for msg in client.run_stream(task.prompt):
            data = {
                "type": msg.type.value,
                "content": msg.content,
                "timestamp": msg.timestamp,
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

## 错误处理

### 统一异常处理

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class TaskError(Exception):
    """任务执行错误"""
    def __init__(self, message: str, code: str = "TASK_ERROR"):
        self.message = message
        self.code = code

@app.exception_handler(TaskError)
async def task_error_handler(request: Request, exc: TaskError):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": exc.message,
            "code": exc.code,
        },
    )

# 使用
@app.post("/api/task")
async def run_task(task: TaskRequest):
    if not task.prompt:
        raise TaskError("prompt 不能为空", "INVALID_PROMPT")
```

## 依赖注入

```python
from fastapi import Depends

def get_client(
    working_dir: str = Depends(get_working_dir),
) -> ClaudeCodeClient:
    """获取客户端实例"""
    return ClaudeCodeClient(working_dir=working_dir)

@app.post("/api/task")
async def run_task(
    task: TaskRequest,
    client: ClaudeCodeClient = Depends(get_client),
):
    return await client.run(task.prompt)
```

## API 文档

FastAPI 自动生成 OpenAPI 文档：

```python
app = FastAPI(
    title="Claude Code Runner",
    description="通过 Web API 调用 Claude Code 执行任务",
    version="0.1.0",
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc",        # ReDoc
)

# 路由文档
@app.get(
    "/api/sessions",
    response_model=list[Session],
    summary="获取会话列表",
    description="返回当前项目的所有历史会话",
    responses={
        200: {"description": "成功返回会话列表"},
    },
)
async def list_sessions(): ...
```

## 安全

### 输入验证

```python
from pydantic import validator, Field

class TaskRequest(BaseModel):
    prompt: str

    @validator("prompt")
    def validate_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt 不能为空")
        if len(v) > 10000:
            raise ValueError("prompt 长度不能超过 10000 字符")
        return v.strip()
```

### 路径安全

```python
from pathlib import Path

def safe_path(base_dir: Path, user_path: str) -> Path:
    """安全地拼接路径，防止目录遍历攻击"""
    target = (base_dir / user_path).resolve()
    if not str(target).startswith(str(base_dir.resolve())):
        raise ValueError("非法路径")
    return target
```
