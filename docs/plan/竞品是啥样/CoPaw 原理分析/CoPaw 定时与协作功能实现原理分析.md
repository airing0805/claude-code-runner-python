# CoPaw 定时与协作功能实现原理分析

## 概述

本地 项目位置 ： "E:\repository_git\CoPaw"
CoPaw 项目的"定时与协作"功能主要通过 `app/crons` 模块实现，使用 **APScheduler** 作为任务调度框架，并结合 **AgentScope** 框架执行 AI 任务。

---

## 1. 定时任务：定义、配置和调度

### 技术栈

| 组件 | 技术 |
|------|------|
| 任务调度 | APScheduler (AsyncIOScheduler) |
| 数据存储 | JSON 文件持久化 |
| 运行时 | asyncio 异步执行 |
| AI 框架 | AgentScope + CoPawAgent |

### 核心文件

| 文件 | 功能 |
|------|------|
| [manager.py](E:/repository_git/CoPaw/src/copaw/app/crons/manager.py) | 定时任务管理器 - 调度器核心 |
| [models.py](E:/repository_git/CoPaw/src/copaw/app/crons/models.py) | 数据模型 - 任务规范定义 |
| [executor.py](E:/repository_git/CoPaw/src/copaw/app/crons/executor.py) | 任务执行器 - 执行逻辑 |
| [api.py](E:/repository_git/CoPaw/src/copaw/app/crons/api.py) | REST API 端点 |
| [cron/repo/json_repo.py](E:/repository_git/CoPaw/src/copaw/app/crons/repo/json_repo.py) | JSON 持久化存储 |

### 任务定义 (models.py)

```python
# 定时配置
class ScheduleSpec(BaseModel):
    type: Literal["cron"] = "cron"
    cron: str          # 5 字段 cron 表达式
    timezone: str = "UTC"

# 运行时配置
class JobRuntimeSpec(BaseModel):
    max_concurrency: int = 1        # 最大并发数
    timeout_seconds: int = 120       # 超时时间
    misfire_grace_seconds: int = 60 # 错过执行宽限期

# 任务规范
class CronJobSpec(BaseModel):
    id: str
    name: str
    enabled: bool = True
    schedule: ScheduleSpec          # 定时配置
    task_type: Literal["text", "agent"]  # 任务类型
    text: Optional[str] = None      # text 类型内容
    request: Optional[CronJobRequest] = None  # agent 类型请求
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

        # Heartbeat: 定时心跳任务
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
