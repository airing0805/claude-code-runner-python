# v0.3.6 - Agent 监控技术设计

## 1. API 接口设计

### 1.1 获取子代理列表

```
GET /api/agents?status={status}&parent_task_id={task_id}&limit=50
```

**响应示例**：
```json
{
  "agents": [
    {
      "id": "sub_abc123",
      "parent_task_id": "task_xyz789",
      "status": "running",
      "prompt": "分析代码结构",
      "started_at": "2026-02-19T10:30:45Z",
      "progress": 45,
      "tools_used": ["Read", "Glob"],
      "files_changed": ["src/utils.py"]
    }
  ],
  "total": 15,
  "running_count": 3
}
```

### 1.2 获取子代理详情

```
GET /api/agents/{agent_id}
```

### 1.3 终止子代理

```
POST /api/agents/{agent_id}/terminate
```

### 1.4 获取日志流

```
GET /api/agents/{agent_id}/logs
```

返回 SSE 流式日志。

### 1.5 获取文件变更

```
GET /api/agents/{agent_id}/files
```

### 1.6 获取工具使用

```
GET /api/agents/{agent_id}/tools
```

## 2. 数据结构设计

### 2.1 Agent

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class AgentStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    FAILED = "failed"

class Agent(BaseModel):
    id: str
    parent_task_id: str
    status: AgentStatus
    prompt: str
    started_at: datetime
    ended_at: datetime | None = None
    progress: int = 0
    tools_used: list[str] = []
    files_changed: list[str] = []
```

## 3. 后端实现

### 3.1 路由设计

新建 `app/routers/agents.py`：

```python
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.get("")
async def get_agents(
    status: str = None,
    parent_task_id: str = None,
    limit: int = 50
):
    """获取子代理列表"""
    ...

@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """获取子代理详情"""
    ...

@router.post("/{agent_id}/terminate")
async def terminate_agent(agent_id: str):
    """终止子代理"""
    ...

@router.get("/{agent_id}/logs")
async def get_agent_logs(agent_id: str):
    """获取日志流"""
    ...
```

### 3.2 Agent 管理

```python
class AgentManager:
    """子代理管理器"""

    def __init__(self):
        self.agents: dict[str, Agent] = {}

    def create_agent(self, parent_task_id: str, prompt: str) -> Agent:
        """创建子代理"""
        ...

    def update_status(self, agent_id: str, status: AgentStatus):
        """更新状态"""
        ...

    def terminate(self, agent_id: str):
        """终止子代理"""
        ...
```

## 4. 前端设计

### 4.1 页面结构

```
┌─────────────────────────────────────────────────────────────┐
│  Agent 监控                                                  │
│                                                             │
│  状态: [全部] [运行中] [已完成] [已终止] [失败]             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 任务描述              │ 状态    │ 进度 │ 操作        │   │
│  ├───────────────────────┼─────────┼──────┼─────────────┤   │
│  │ 分析代码结构          │ 运行中  │ 45%  │ [终止]      │   │
│  │ 查找安全漏洞          │ 已完成  │ 100% │ [查看]      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 5. 关键文件

| 文件 | 操作 |
|------|------|
| `app/routers/agents.py` | 新建 |
| `app/agents/manager.py` | 新建 |
| `app/main.py` | 修改 - 注册路由 |
| `web/static/modules/agentMonitor.js` | 新建 |
