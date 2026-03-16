# 安全指南

> 本文件定义项目的安全要求和最佳实践。

## 安全检查清单

在 ANY 提交前确认：

- [ ] 无硬编码密钥（API Key、密码、Token）
- [ ] 所有用户输入已验证
- [ ] SQL 注入防护（使用参数化查询）
- [ ] XSS 防护（HTML 转义）
- [ ] 错误消息不泄露敏感信息
- [ ] 文件路径已验证（防止目录遍历）

## 密钥管理

### 环境变量

```python
# 正确 ✅ - 使用环境变量
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY")

# 错误 ❌ - 硬编码密钥
API_KEY = "sk-ant-api03-xxxxx"  # 绝对禁止！
```

### 启动时验证

```python
def validate_config():
    """验证必要的环境变量"""
    required = ["ANTHROPIC_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"缺少环境变量: {', '.join(missing)}")

# 应用启动时调用
validate_config()
```

### .env 文件管理

```bash
# .env.example (提交到版本控制)
ANTHROPIC_API_KEY=your-api-key-here
WORKING_DIR=.
HOST=127.0.0.1
PORT=8000

# .env (不提交，包含真实密钥)
ANTHROPIC_API_KEY=sk-ant-api03-real-key
```

```gitignore
# .gitignore
.env
*.pem
secrets/
```

## 输入验证

### API 输入验证

```python
from pydantic import BaseModel, Field, validator

class TaskRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    working_dir: str | None = None

    @validator("prompt")
    def validate_prompt(cls, v: str) -> str:
        # 去除首尾空白
        v = v.strip()
        if not v:
            raise ValueError("prompt 不能为空")
        return v

    @validator("working_dir")
    def validate_working_dir(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # 防止路径注入
        if ".." in v or v.startswith("/etc"):
            raise ValueError("非法工作目录")
        return v
```

### 文件路径验证

```python
from pathlib import Path

ALLOWED_BASE_DIRS = [
    Path(os.getenv("WORKING_DIR", ".")).resolve(),
]

def validate_file_path(file_path: str) -> Path:
    """
    验证文件路径安全性

    防止目录遍历攻击（如 ../../../etc/passwd）
    """
    path = Path(file_path).resolve()

    # 检查是否在允许的目录内
    for base_dir in ALLOWED_BASE_DIRS:
        try:
            path.relative_to(base_dir)
            return path
        except ValueError:
            continue

    raise ValueError(f"路径不在允许的目录内: {file_path}")
```

## 错误处理安全

### 不泄露敏感信息

```python
# 正确 ✅ - 通用错误消息
@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("服务器错误")  # 服务端记录详细信息
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误"},  # 客户端显示通用消息
    )

# 错误 ❌ - 泄露敏感信息
return {"error": f"数据库连接失败: {db_password}"}  # 绝对禁止！
```

### 异常分类处理

```python
class AppException(Exception):
    """应用异常基类"""
    def __init__(self, message: str, user_message: str = "操作失败"):
        self.message = message          # 日志用
        self.user_message = user_message # 用户看到的

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"应用错误: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={"error": exc.user_message},
    )
```

## API 安全

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/task")
@limiter.limit("10/minute")
async def run_task(request: Request, task: TaskRequest):
    ...
```

### 请求大小限制

```python
from fastapi import FastAPI

app = FastAPI()

# 限制请求体大小
@app.post("/api/task")
async def run_task(task: TaskRequest):
    # prompt 长度由 Pydantic 验证
    ...
```

## 敏感数据处理

### 日志脱敏

```python
import re

def sanitize_log(message: str) -> str:
    """脱敏日志中的敏感信息"""
    # API Key
    message = re.sub(r'sk-[a-zA-Z0-9-]+', 'sk-***', message)
    # 密码
    message = re.sub(r'password["\']?\s*[:=]\s*["\'][^"\']+["\']',
                     'password=***', message)
    return message

logger.info(sanitize_log(f"Processing with key: {api_key}"))
```

### 响应过滤

```python
class SafeTaskResponse(BaseModel):
    """安全的响应模型 - 不包含敏感字段"""
    success: bool
    message: str
    # 不包含: internal_error, stack_trace, config_path 等
```

## 安全响应协议

如果发现安全问题：

1. **立即停止** 当前工作
2. **标记问题** 在代码中添加注释
3. **修复优先级**
   - CRITICAL: 立即修复
   - HIGH: 当天修复
   - MEDIUM: 本周修复
4. **密钥轮换** 如果密钥已泄露
5. **全面审查** 检查类似问题

```python
# 发现硬编码密钥时的处理
# TODO: SECURITY - 发现硬编码 API Key，需要立即移除
# api_key = "sk-ant-xxxxx"  # 已移除

# 替换为
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY 未设置")
```

## 依赖安全

```bash
# 定期检查依赖漏洞
pip-audit

# 使用 uv 管理依赖
uv sync --group dev
```
