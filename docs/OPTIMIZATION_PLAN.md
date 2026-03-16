# Claude Code Runner 优化方案

## 项目概述

Claude Code Runner 是一个基于 Claude Agent SDK 的 Web 服务，通过 FastAPI 提供 REST API 和 Web 界面来调用 Claude Code 执行编程任务。

---

## 一、性能优化

### 1.1 存储层优化 (高优先级)

**问题**:
- 当前使用 JSON 文件存储 (`queue.json`, `scheduled.json`, `running.json` 等)
- 每次读写都需要解析整个文件，O(n) 复杂度
- 在高并发场景下，文件锁会成为性能瓶颈
- 重启服务会丢失内存中的数据

**优化方案**:

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **SQLite** | 无需额外依赖、持久化、支持 SQL 查询 | 并发写入有限制 | 中小规模项目 |
| **Redis** | 高性能、支持过期、分布式 | 需要额外依赖和部署 | 高并发、生产环境 |

**推荐方案**: 采用 SQLite 作为主要存储，Redis 作为缓存和限流

**实施步骤**:
1. 引入 `aiosqlite` 依赖
2. 创建数据库迁移脚本
3. 实现 `SQLiteStorage` 类，兼容现有接口
4. 添加数据目录到 `.gitignore`

### 1.2 调度器轮询优化 (中优先级)

**问题**:
- 当前轮询间隔为 10 秒 (`POLL_INTERVAL = 10`)
- 每次循环检查所有定时任务，O(n) 复杂度
- 定时任务触发有最大 10 秒延迟

**优化方案**:
1. **动态轮询间隔**: 根据队列状态动态调整
   - 有任务时：1 秒
   - 无任务时：5-10 秒

2. **事件驱动触发**: 使用 APScheduler 的内置触发器，减少主动检查

3. **增量检查**: 只检查即将到期的任务，而不是所有任务

```python
# 优化后的轮询逻辑
async def _run_queue_loop(self):
    while self._status == SchedulerStatus.RUNNING:
        # 根据队列状态动态调整间隔
        if self.storage.queue.count() > 0:
            poll_interval = 1  # 有任务时快速响应
        else:
            poll_interval = min(POLL_INTERVAL * 2, 30)  # 无任务时适当延长

        # ... 执行逻辑
        await asyncio.sleep(poll_interval)
```

### 1.3 FastAPI 响应优化 (中优先级)

**问题**:
- 缺少响应压缩
- CORS 配置可以更精细
- 缺少缓存头

**优化方案**:

1. **添加响应压缩**:
```python
# 添加到 main.py
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

2. **优化 CORS 配置**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 限制具体域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,  # 缓存预检请求结果
)
```

3. **添加缓存控制**:
```python
from fastapi.middleware.cache import CacheMiddleware
```

---

## 二、功能增强

### 2.1 MCP 管理器功能完善 (中优先级)

**问题**:
- `get_server_status()` 返回模拟状态
- `get_server_tools()` 返回空列表
- 实际功能未实现

**优化方案**:

1. **实现服务器状态检查**:
```python
async def get_server_status(self, server_id: str) -> Optional[MCPServerStatus]:
    server = self.get_server(server_id)
    if not server:
        return None

    # 实际连接 MCP 服务器检查状态
    try:
        if server.connection_type == "stdio":
            # 测试 stdio 连接
            result = await self._test_stdio_connection(server)
        else:
            # 测试 HTTP 连接
            result = await self._test_http_connection(server)

        return MCPServerStatus(
            id=server.id,
            name=server.name,
            status="online" if result else "offline",
            message="连接成功" if result else "连接失败",
            last_checked=datetime.now(timezone.utc),
        )
    except Exception as e:
        return MCPServerStatus(
            id=server.id,
            name=server.name,
            status="error",
            message=str(e),
            last_checked=datetime.now(timezone.utc),
        )
```

2. **实现工具列表获取**:
   - 调用 MCP 服务器的 `tools/list` 方法
   - 缓存工具列表

### 2.2 认证模块增强 (高优先级)

**问题**:
- 用户和 API Key 存储在内存中，重启会丢失
- Token 黑名单也是内存存储，无法跨进程共享

**优化方案**:

1. **短期方案 - SQLite 存储**:
   - 创建 `users` 表
   - 创建 `api_keys` 表
   - 保持向后兼容

2. **长期方案 - Redis 集成**:
   - 使用 Redis 存储 Token 黑名单（支持过期自动清理）
   - 使用 Redis 存储会话状态

```python
# 建议的数据库表结构

# users 表
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    name TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

# api_keys 表
CREATE TABLE api_keys (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    prefix TEXT NOT NULL,
    permissions TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    expires_at TEXT,
    last_used_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

# token_blacklist 表
CREATE TABLE token_blacklist (
    jti TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

### 2.3 Claude Code 客户端优化 (中优先级)

**问题**:
- 会话完整性延迟 20 秒 (`SESSION_WRITE_DELAY_SECONDS = 20`) 太长
- 无法精确判断会话是否真正完成

**优化方案**:

1. **缩短延迟时间**: 20 秒可以缩短到 5-10 秒

2. **使用会话状态检查 API**:
   - 调用 Claude Code 的会话查询接口
   - 轮询检查会话状态直到完成

3. **异步写入检测**:
```python
# 优化后的延迟逻辑
async def _wait_for_session_write(self, session_id: str):
    max_attempts = 10
    for _ in range(max_attempts):
        if await self._check_session_complete(session_id):
            return
        await asyncio.sleep(1)  # 每次等待 1 秒，最多 10 秒
```

---

## 三、安全增强

### 3.1 安全中间件 (高优先级)

**问题**:
- 缺少安全响应头
- 缺少请求速率限制（细粒度控制）

**优化方案**:

1. **添加安全头中间件**:
```python
from fastapi.middleware.security import SecurityHeadersMiddleware
# 或自定义实现
```

2. **实现更精细的限流**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# 全局限流
@app.middleware("http")
async def add_rate_limit_headers(request, call_next):
    # 添加 X-RateLimit-* 头
    response = await call_next(request)
    return response
```

### 3.2 审计日志 (中优先级)

**问题**:
- 缺少完整的审计日志
- 难以追踪安全问题

**优化方案**:

1. **添加审计日志表**:
```python
# 审计日志记录
AUDIT_ACTIONS = [
    "user.login",
    "user.logout",
    "user.create",
    "user.update",
    "user.delete",
    "api_key.create",
    "api_key.revoke",
    "task.create",
    "task.cancel",
    "scheduler.create",
    "scheduler.update",
    "scheduler.delete",
]
```

---

## 四、监控和可观测性

### 4.1 性能指标 (中优先级)

**优化方案**:

1. **添加 Prometheus 指标**:
```python
from prometheus_client import Counter, Histogram, Gauge

# 请求计数
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# 任务执行
TASK_DURATION = Histogram(
    'task_duration_seconds',
    'Task execution duration'
)

# 活跃任务数
ACTIVE_TASKS = Gauge(
    'active_tasks',
    'Number of active tasks'
)
```

2. **添加健康检查端点**:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "0.6.0",
        "scheduler": get_scheduler_status(),
    }
```

### 4.2 结构化日志 (低优先级)

**优化方案**:
- 统一日志格式为 JSON
- 添加请求 ID 追踪
- 集成日志聚合服务（如 ELK、Loki）

---

## 五、依赖升级

### 5.1 依赖版本检查

**当前依赖** (来自 pyproject.toml):
```toml
dependencies = [
    "claude-agent-sdk>=0.1.44",
    "fastapi>=0.129.0",
    "jinja2>=3.1.6",
    "python-dotenv>=1.2.1",
    "pywin32>=311",
    "uvicorn>=0.41.0",
    "bcrypt>=4.2.0",
    "python-jose[cryptography]>=3.3.0",
    "pydantic>=2.10.0",
    "slowapi>=0.1.9",
    "apscheduler>=3.11.0",
]
```

**建议升级**:
```toml
dependencies = [
    "claude-agent-sdk>=0.1.44",
    "fastapi>=0.115.0",  # 更新版本
    "jinja2>=3.1.6",
    "python-dotenv>=1.2.1",
    "pywin32>=311",
    "uvicorn[standard]>=0.34.0",  # 添加 standard 额外依赖
    "bcrypt>=4.2.0",
    "python-jose[cryptography]>=3.3.0",
    "pydantic>=2.10.0",
    "slowapi>=0.1.9",
    "apscheduler>=3.11.0",
    # 新增
    "aiosqlite>=0.20.0",  # 异步 SQLite
    "python-multipart>=0.0.20",  # 文件上传
]
```

---

## 六、实施优先级

### 阶段 1: 稳定性增强 (1-2 周)
1. [ ] SQLite 存储层替换 JSON 文件
2. [ ] 完善 MCP 状态检查功能
3. [ ] 调度器轮询优化

### 阶段 2: 性能优化 (2-3 周)
1. [ ] FastAPI 响应压缩和 CORS 优化
2. [ ] 认证模块持久化
3. [ ] Token 黑名单 Redis 化

### 阶段 3: 安全加固 (1-2 周)
1. [ ] 安全中间件
2. [ ] 审计日志
3. [ ] 精细化限流

### 阶段 4: 可观测性 (1-2 周)
1. [ ] Prometheus 指标集成
2. [ ] 健康检查端点
3. [ ] 结构化日志

---

## 七、风险评估

| 优化项 | 风险等级 | 缓解措施 |
|--------|----------|----------|
| SQLite 替换 | 中 | 保持 JSON 存储作为备份，支持数据迁移脚本 |
| Redis 集成 | 低 | 提供配置开关，默认使用内存存储 |
| 调度器优化 | 低 | 保持向后兼容，逐步调整参数 |
| 安全中间件 | 中 | 先在测试环境验证 |

---

## 总结

本方案从性能、功能、安全和可观测性四个维度对 Claude Code Runner 进行了全面优化。建议按优先级分阶段实施，优先解决存储层和 MCP 功能问题，再逐步进行性能调优和安全加固。

