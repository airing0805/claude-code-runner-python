# CoPaw 定时与协作功能实现原理分析

## 概述

CoPaw 项目的"定时与协作"功能主要通过 `app/crons` 模块实现，使用 **定时任务调度工具** 作为任务调度框架，并结合 **AI 任务执行框架** 执行智能任务。

---

## 1. 定时任务：定义、配置和调度

### 技术栈

| 组件 | 技术 |
|------|------|
| 任务调度 | 定时任务调度工具 (异步版本) |
| 数据存储 | JSON 格式文件永久保存 |
| 运行时 | 异步并发执行 |
| AI 框架 | AI 任务执行框架 + CoPaw 智能助手 |

### 核心文件

| 文件 | 功能 |
|------|------|
| manager.py | 定时任务管理员 - 调度器核心 |
| models.py | 数据模型 - 任务规范定义 |
| executor.py | 任务执行器 - 执行逻辑 |
| api.py | 网络接口端点 |
| cron/repo/json_repo.py | JSON 永久保存存储 |

### 任务定义 (models.py)

```python
# 定时配置
class ScheduleSpec(BaseModel):
    type: Literal["cron"] = "cron"
    cron: str          # 5 字段定时表达式
    timezone: str = "UTC"

# 运行时配置
class JobRuntimeSpec(BaseModel):
    max_concurrency: int = 1        # 最大同时运行数量
    timeout_seconds: int = 120       # 超时时间
    misfire_grace_seconds: int = 60 # 错过执行容忍时间

# 任务规范
class CronJobSpec(BaseModel):
    id: str
    name: str
    enabled: bool = True
    schedule: ScheduleSpec          # 定时配置
    task_type: Literal["text", "agent"]  # 任务类型
    text: Optional[str] = None      # 文本类型内容
    request: Optional[CronJobRequest] = None  # 智能类型请求
    dispatch: DispatchSpec         # 分发配置
    runtime: JobRuntimeSpec        # 运行时配置
```

### 调度器初始化 (manager.py:32-76)

```python
class CronManager:
    def __init__(self, *, repo, runner, channel_manager, timezone="UTC"):
        self._scheduler = AsyncIOScheduler(timezone=timezone)
        self._executor = CronExecutor(runner=runner, channel_manager=channel_manager)
        self._rt: Dict[str, _Runtime] = {}  # 每任务运行时状态

    async def start(self):
        jobs_file = await self._repo.load()
        self._scheduler.start()
        for job in jobs_file.jobs:
            await self._register_or_update(job)

        # 心跳检查: 定时检查任务
        hb = get_heartbeat_config()
        if getattr(hb, "enabled", True):
            interval_seconds = parse_heartbeat_every(hb.every)
            self._scheduler.add_job(
                self._heartbeat_callback,
                trigger=IntervalTrigger(seconds=interval_seconds),
                id=HEARTBEAT_JOB_ID,
            )
```

### Cron 表达式解析 (manager.py:226-243)

```python
def _build_trigger(self, spec: CronJobSpec) -> CronTrigger:
    parts = [p for p in spec.schedule.cron.split() if p]
    # 强制 5 字段 (无秒)
    minute, hour, day, month, day_of_week = parts
    return CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        timezone=spec.schedule.timezone,
    )
```

---

## 2. 队列机制

### 实现方式

CoPaw **没有使用传统消息队列**，而是采用以下机制：

1. **APScheduler 内置队列**: AsyncIOScheduler 内部维护任务队列
2. **并发控制**: 使用 `asyncio.Semaphore` 限制并发数

### 关键配置 (models.py:60-63)

```python
class JobRuntimeSpec(BaseModel):
    max_concurrency: int = Field(default=1, ge=1)   # 每任务最大并发
    timeout_seconds: int = Field(default=120, ge=1) # 任务超时
    misfire_grace_seconds: int = Field(default=60)   # 错过执行容忍时间
```

### 并发控制实现 (manager.py:27-29, 196-200)

```python
@dataclass
class _Runtime:
    sem: asyncio.Semaphore  # 信号量控制并发

# 注册任务时创建信号量
async def _register_or_update(self, spec: CronJobSpec) -> None:
    self._rt[spec.id] = _Runtime(
        sem=asyncio.Semaphore(spec.runtime.max_concurrency),
    )
```

### 任务执行入口 (manager.py:268-298)

```python
async def _execute_once(self, job: CronJobSpec) -> None:
    rt = self._rt.get(job.id)
    if not rt:
        rt = _Runtime(sem=asyncio.Semaphore(job.runtime.max_concurrency))
        self._rt[job.id] = rt

    async with rt.sem:  # 获取信号量，控制并发
        st = self._states.get(job.id, CronJobState())
        st.last_status = "running"  # 设置为运行中
        self._states[job.id] = st

        try:
            await self._executor.execute(job)
            st.last_status = "success"
        except Exception as e:
            st.last_status = "error"
            st.last_error = repr(e)
            raise
        finally:
            st.last_run_at = datetime.utcnow()
```

---

## 3. 运行状态管理

### 状态定义 (models.py:120-126)

```python
class CronJobState(BaseModel):
    next_run_at: Optional[datetime] = None      # 下次运行时间
    last_run_at: Optional[datetime] = None      # 上次运行时间
    last_status: Optional[
        Literal["success", "error", "running", "skipped"]
    ] = None
    last_error: Optional[str] = None            # 上次错误信息
```

### 状态流转

```
创建任务 → PENDING (enabled=True 时自动调度)
     ↓
定时触发 / 手动触发
     ↓
获取信号量 (max_concurrency 控制)
     ↓
设置状态: "running"  ← ← ← ← ← ← ← 运行中状态在此设置
     ↓
执行任务 (CronExecutor.execute)
     ↓
成功 → 状态: "success"
失败 → 状态: "error", last_error=错误信息
     ↓
更新 last_run_at
```

### "运行中"状态设置 (manager.py:275-277)

```python
async def _execute_once(self, job: CronJobSpec) -> None:
    async with rt.sem:
        st = self._states.get(job.id, CronJobState())
        st.last_status = "running"  # ← 运行状态在此设置
        self._states[job.id] = st
```

### "运行成功"判定 (manager.py:279-286)

```python
try:
    await self._executor.execute(job)  # 执行无异常 = 成功
    st.last_status = "success"
    st.last_error = None
    logger.info("cron _execute_once: job_id=%s status=success", job.id)
except Exception as e:
    st.last_status = "error"
    st.last_error = repr(e)
    raise
```

**成功后续操作**:
- 记录 `last_status = "success"`
- 清除 `last_error`
- 更新 `last_run_at` 时间戳
- 前端通过 SSE 或轮询获取状态

### "运行失败"捕获 (manager.py:287-295)

```python
except Exception as e:  # pylint: disable=broad-except
    st.last_status = "error"
    st.last_error = repr(e)  # 错误信息保存
    logger.warning(
        "cron _execute_once: job_id=%s status=error error=%s",
        job.id, repr(e),
    )
    raise  # 重新抛出异常
```

**错误信息传递**:
1. 异常被捕获，保存到 `last_error`
2. `_task_done_cb` 回调处理失败任务 (manager.py:171-192)
3. 错误信息推送到 console push store，前端展示

```python
def _task_done_cb(self, task: asyncio.Task, job: CronJobSpec) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        # 推送到前端控制台
        session_id = job.dispatch.target.session_id
        if session_id:
            error_text = f"❌ Cron job [{job.name}] failed: {exc}"
            asyncio.ensure_future(push_store_append(session_id, error_text))
```

---

## 4. 完整数据流

### 定时任务触发流程

```
1. APScheduler 定时触发
   ↓
2. _scheduled_callback(job_id)  (manager.py:245-256)
   ↓
3. _execute_once(job)            (manager.py:268-298)
   ├─ 获取并发信号量
   ├─ 设置状态: "running"
   ├─ 执行任务
   │   └─ CronExecutor.execute()
   │       ├─ text 类型: 发送文本到渠道
   │       └─ agent 类型: 调用 runner.stream_query()
   │           └─ 执行 CoPawAgent
   │
   ├─ 成功 → 状态: "success"
   └─ 失败 → 状态: "error", last_error
   ↓
4. 更新 next_run_at (下次执行时间)
   ↓
5. 状态持久化到内存 (_states dict)
```

### 手动触发流程 (API: /cron/jobs/{job_id}/run)

```
1. POST /cron/jobs/{job_id}/run
   ↓
2. manager.run_job(job_id)       (manager.py:144-167)
   ├─ 异步创建任务: asyncio.create_task()
   └─ 添加完成回调: _task_done_cb
   ↓
3. _execute_once(job)            (同定时触发)
   ↓
4. _task_done_cb 错误处理
   └─ 推送到前端展示
```

### 状态查询 API (api.py:103-111)

```
GET /cron/jobs/{job_id}/state
   ↓
manager.get_state(job_id)
   ↓
返回 CronJobState (JSON)
{
    "next_run_at": "2024-01-01T10:00:00",
    "last_run_at": "2024-01-01T09:00:00",
    "last_status": "success",
    "last_error": null
}
```

---

## 5. 模块协作关系

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (api.py)                     │
│  POST/GET/PUT/DELETE /cron/jobs/*                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              CronManager (manager.py)                       │
│  - APScheduler 调度器管理                                    │
│  - 任务注册/删除/暂停/恢复                                   │
│  - 状态管理 (_states)                                        │
│  - 并发控制 (Semaphore)                                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ CronExecutor  │  │  JsonJobRepo  │  │  Heartbeat    │
│ (executor.py)│  │  (json_repo)  │  │  Callback     │
│              │  │               │  │               │
│ 执行任务      │  │ 持久化 jobs   │  │ 心跳任务      │
│ - text       │  │   .json       │  │               │
│ - agent      │  │               │  │               │
└──────┬───────┘  └───────────────┘  └───────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    AgentRunner (runner.py)                   │
│  - AgentScope Runner                                         │
│  - CoPawAgent                                                │
│  - Session 管理                                              │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│              ChannelManager (channels/manager.py)            │
│  - 消息分发到各渠道 (Console, DingTalk, etc.)                │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. 关键配置参数汇总

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_concurrency` | 1 | 单任务最大并发数 |
| `timeout_seconds` | 120 | 任务执行超时时间 |
| `misfire_grace_seconds` | 60 | 错过执行时间容忍窗口 |
| cron 表达式 | 5字段 | minute hour day month day_of_week |

---

## 总结

1. **定时任务**: 基于 APScheduler 的 CronTrigger 实现，支持标准 5 字段 cron 表达式
2. **队列机制**: 无传统消息队列，使用 APScheduler 内置队列 + asyncio.Semaphore 控制并发
3. **运行状态**: 通过 `CronJobState` 实体类管理，状态存储在内存字典中
4. **状态触发**: 在获取信号量后立即设置 "running"，执行完成后根据结果设置为 "success" 或 "error"
5. **错误传递**: 通过 `_task_done_cb` 回调将错误推送到前端 console push store

---

# CoPaw 与 Claude Code Runner 定时任务对比

## 架构概览对比

| 维度 | CoPaw | Claude Code Runner (当前项目) |
|------|-------|-------------------------------|
| **项目路径** | E:\repository_git\CoPaw | e:\workspaces_2026_python\claude-code-runner |
| **任务调度** | APScheduler (AsyncIOScheduler) | APScheduler (AsyncIOScheduler) |
| **核心模块** | app/crons/ | app/scheduler/ |
| **存储方式** | JSON 文件 (单文件) | JSON 文件 (多文件分类) |
| **任务执行** | AgentScope + CoPawAgent | Claude Code CLI |
| **API 框架** | FastAPI | FastAPI |

---

## 1. 定时任务定义对比

### CoPaw (models.py)

```python
class ScheduleSpec(BaseModel):
    type: Literal["cron"] = "cron"
    cron: str          # 5 字段 cron
    timezone: str = "UTC"

class JobRuntimeSpec(BaseModel):
    max_concurrency: int = 1        # 并发控制
    timeout_seconds: int = 120      # 超时
    misfire_grace_seconds: int = 60 # 错过执行容忍

class CronJobSpec(BaseModel):
    id: str
    name: str
    enabled: bool = True
    schedule: ScheduleSpec
    task_type: Literal["text", "agent"]  # 支持 text/agent 两种类型
    text: Optional[str] = None
    request: Optional[CronJobRequest] = None
    dispatch: DispatchSpec
    runtime: JobRuntimeSpec
```

### 当前项目 (models.py)

```python
class ScheduledTask(BaseModel):
    id: str
    name: str
    cron: str                    # cron 表达式
    prompt: str                  # 任务内容
    workspace: str              # 工作目录
    enabled: bool = True
    timeout: int = 120          # 超时
    auto_approve: bool = False  # 自动批准
    allowed_tools: list[str] = [] # 允许的工具
    next_run: Optional[str] = None
    last_run: Optional[str] = None
```

**对比总结**:
- CoPaw 支持 **text** 和 **agent** 两种任务类型，当前项目只支持 **prompt** 任务
- CoPaw 有 **并发控制** (max_concurrency)，当前项目无此配置
- 当前项目有 **allowed_tools** 白名单，CoPaw 无此功能

---

## 2. 队列机制对比

### CoPaw - 无传统队列

```python
# manager.py - 使用 Semaphore 控制并发
@dataclass
class _Runtime:
    sem: asyncio.Semaphore

async def _execute_once(self, job: CronJobSpec) -> None:
    async with rt.sem:  # 信号量控制
        st.last_status = "running"
        await self._executor.execute(job)
```

- 使用 `asyncio.Semaphore` 控制并发
- 无独立队列存储，任务直接在信号量保护下执行

### 当前项目 - 完整队列系统

```python
# storage.py - 多存储分类
class TaskStorage:
    def __init__(self):
        self.queue = QueueStorage()        # 待执行队列
        self.scheduled = ScheduledStorage() # 定时任务
        self.running = RunningStorage()    # 运行中
        self.history = HistoryStorage()    # 历史记录
        self.cancelled = CancelledStorage() # 已取消
        self.logs = LogsStorage()          # 日志

# scheduler.py - 队列处理循环
async def _run_queue_loop(self) -> None:
    while self._status == SchedulerStatus.RUNNING:
        task = self.storage.queue.pop()  # FIFO 取出
        if task:
            result = await executor.execute(task)
        await asyncio.sleep(POLL_INTERVAL)
```

**对比总结**:

| 特性 | CoPaw | 当前项目 |
|------|-------|----------|
| 队列实现 | APScheduler 内置 + Semaphore | 独立 QueueStorage (JSON 文件) |
| 队列容量 | 无限制 (依赖 Semaphore) | 无明确限制 |
| 并发消费者 | Semaphore 控制 | 轮询循环 (单线程) |
| 优先级队列 | 不支持 | 支持 (add_to_front) |
| 任务持久化 | 任务定义持久化 | 队列/运行中/历史全量持久化 |

---

## 3. 运行状态管理对比

### CoPaw 状态

```python
# models.py
class CronJobState(BaseModel):
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_status: Optional[Literal["success", "error", "running", "skipped"]] = None
    last_error: Optional[str] = None

# manager.py - 状态设置
async def _execute_once(self, job: CronJobSpec) -> None:
    async with rt.sem:
        st.last_status = "running"  # ← 运行中
        try:
            await self._executor.execute(job)
            st.last_status = "success"
        except Exception as e:
            st.last_status = "error"
            st.last_error = repr(e)
```

### 当前项目状态

```python
# models.py
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# executor.py - 状态流转
async def execute(self, task: Task) -> ExecutionResult:
    task.status = TaskStatus.PENDING
    task.status = TaskStatus.RUNNING  # ← 运行中
    # ... 执行 ...
    if success:
        task.status = TaskStatus.COMPLETED
    else:
        task.status = TaskStatus.FAILED
```

**对比总结**:

| 特性 | CoPaw | 当前项目 |
|------|-------|----------|
| 状态存储 | 内存字典 _states | JSON 文件 (running.json) |
| 状态定义 | 字符串 ("running"/"success"/"error") | 枚举 (TaskStatus) |
| 运行中设置 | 获取信号量后立即设置 | 执行前设置 |
| 成功判定 | execute() 无异常 | result.success == True |
| 失败捕获 | 捕获所有 Exception | 多种错误类型处理 |

---

## 4. 错误处理对比

### CoPaw

```python
# manager.py - 错误回调
def _task_done_cb(self, task: asyncio.Task, job: CronJobSpec) -> None:
    exc = task.exception()
    if exc is not None:
        # 推送到前端
        session_id = job.dispatch.target.session_id
        error_text = f"❌ Cron job [{job.name}] failed: {exc}"
        asyncio.ensure_future(push_store_append(session_id, error_text))
```

### 当前项目

```python
# executor.py - 错误分类
class ErrorType(Enum):
    TRANSIENT = "transient"    # 可重试
    PERMANENT = "permanent"    # 不可重试
    TIMEOUT = "timeout"        # 超时
    USER_CANCEL = "user_cancel"
    VALIDATION = "validation"
    RESOURCE = "resource"

# 重试机制
MAX_RETRIES = 2
BASE_DELAY = 5.0
MAX_DELAY = 60.0

# 错误处理
async def execute(self, task: Task) -> ExecutionResult:
    try:
        # 执行
    except Exception as e:
        error_type = self._classify_error(e)
        if error_type in RETRYABLE_ERRORS:
            # 重试逻辑
```

**对比总结**:

| 特性 | CoPaw | 当前项目 |
|------|-------|----------|
| 错误分类 | 简单 (Exception 捕获) | 详细分类 (ErrorType 枚举) |
| 重试机制 | 无 | 指数退避 + 抖动 |
| 前端通知 | console push store | 任务状态 API |

---

## 5. 任务执行流程对比

### CoPaw 流程

```
定时触发 → _scheduled_callback
    ↓
_execute_once (获取信号量)
    ↓
设置状态: "running"
    ↓
CronExecutor.execute()
    ├─ text: channel_manager.send_text()
    └─ agent: runner.stream_query() → CoPawAgent
    ↓
成功 → "success" / 失败 → "error"
    ↓
更新 next_run_at
```

### 当前项目流程

```
APScheduler 定时触发
    ↓
apscheduler.trigger_scheduled_task() → 加入队列
    ↓
_run_queue_loop() 轮询取出
    ↓
TaskExecutor.execute()
    ├─ 设置状态: "running" (写入 running.json)
    ├─ ClaudeCodeClient.run_stream()
    │   └─ Claude Code CLI
    ├─ 成功 → COMPLETED / 失败 → FAILED
    └─ 写入历史记录
    ↓
POLL_INTERVAL 轮询
```

---

## 6. 关键配置对比

| 配置项 | CoPaw | 当前项目 |
|--------|-------|----------|
| **max_concurrency** | ✅ (Semaphore) | ❌ |
| **timeout_seconds** | ✅ | ✅ (timeout) |
| **misfire_grace_seconds** | ✅ | ❌ |
| **allowed_tools** | ❌ | ✅ |
| **auto_approve** | ❌ | ✅ |
| **workspace** | ❌ | ✅ |
| **timezone** | ✅ | ❌ |

---

## 7. 各自优势

### CoPaw 优势

1. **并发控制**: Semaphore 实现精确的并发控制
2. **任务类型多样**: 支持 text 和 agent 两种类型
3. **协作推送**: 错误信息实时推送到前端
4. **代码简洁**: 结构更简单直观

### 当前项目优势

1. **完整队列系统**: 队列/运行中/历史分离，支持持久化
2. **任务恢复**: 服务重启后自动恢复运行中的任务
3. **重试机制**: 指数退避重试，提高可靠性
4. **工具限制**: allowed_tools 白名单，更安全
5. **自动批准**: auto_approve 选项
6. **数据一致性**: 自动修复重复 ID、过期时间等

---

## 8. 总结差异

| 维度 | CoPaw | 当前项目 |
|------|-------|----------|
| **架构模式** | 调度器直接执行 | 调度器 → 队列 → 执行器 |
| **并发模型** | Semaphore | 轮询循环 |
| **状态存储** | 内存 | JSON 文件 |
| **错误恢复** | 简单重试 | 详细分类 + 指数退避 |
| **任务隔离** | 信号量 | 文件级隔离 |
| **扩展性** | 简单 | 更丰富 |
