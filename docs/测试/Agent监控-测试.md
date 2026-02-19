# Agent 监控 - 测试文档

## 1. 测试策略

### 1.1 测试目标

验证子代理监控 API 的功能完整性。

### 1.2 测试范围

| 模块 | 测试内容 |
|------|---------|
| 子代理列表 | 获取、筛选 |
| 子代理详情 | 状态、进度 |
| 终止子代理 | 手动终止 |
| 日志流 | SSE 流式日志 |

---

## 2. 单元测试

### 2.1 数据模型测试

```python
# tests/test_agents.py

from app.agents.schemas import Agent, AgentStatus
from datetime import datetime

class TestAgentStatus:
    """Agent 状态枚举测试"""

    def test_all_statuses(self):
        """测试所有状态"""
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.TERMINATED.value == "terminated"
        assert AgentStatus.FAILED.value == "failed"


class TestAgent:
    """Agent 模型测试"""

    def test_agent_creation(self):
        """测试 Agent 创建"""
        agent = Agent(
            id="sub_abc123",
            parent_task_id="task_xyz789",
            status=AgentStatus.RUNNING,
            prompt="分析代码结构",
            started_at=datetime.now(),
            progress=45,
            tools_used=["Read", "Glob"],
            files_changed=["src/utils.py"]
        )
        assert agent.id == "sub_abc123"
        assert agent.status == AgentStatus.RUNNING

    def test_agent_completed(self):
        """测试完成的 Agent"""
        agent = Agent(
            id="sub_completed",
            parent_task_id="task_xyz",
            status=AgentStatus.COMPLETED,
            prompt="分析完成",
            started_at=datetime.now(),
            ended_at=datetime.now(),
            progress=100,
            tools_used=[],
            files_changed=[]
        )
        assert agent.status == AgentStatus.COMPLETED
        assert agent.progress == 100
        assert agent.ended_at is not None


class TestAgentList:
    """Agent 列表测试"""

    def test_agent_list_response(self):
        """测试列表响应"""
        data = {
            "agents": [
                {
                    "id": "sub_1",
                    "status": "running",
                    "prompt": "test"
                }
            ],
            "total": 1,
            "running_count": 1
        }
        assert data["total"] == 1
        assert data["running_count"] == 1
```

---

## 3. 集成测试

### 3.1 子代理列表 API 测试

```python
class TestAgentsEndpoint:
    """Agent API 测试"""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_agent_manager(self):
        """Mock Agent 管理器"""
        with patch("app.routers.agents.AgentManager") as mock:
            mock_instance = MagicMock()
            mock_instance.get_agents.return_value = ([], 0, 0)
            mock.return_value = mock_instance
            yield mock_instance

    def test_get_agents_success(self, client, mock_agent_manager):
        """测试获取子代理列表成功"""
        response = client.get("/api/agents")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "total" in data
        assert "running_count" in data

    def test_filter_by_status(self, client, mock_agent_manager):
        """测试按状态筛选"""
        response = client.get("/api/agents?status=running")

        assert response.status_code == 200

    def test_filter_by_parent_task(self, client, mock_agent_manager):
        """测试按父任务筛选"""
        response = client.get("/api/agents?parent_task_id=task_xyz")

        assert response.status_code == 200

    def test_limit_param(self, client, mock_agent_manager):
        """测试限制数量"""
        response = client.get("/api/agents?limit=10")

        assert response.status_code == 200
```

### 3.2 子代理详情 API 测试

```python
class TestAgentDetail:
    """Agent 详情测试"""

    def test_get_agent_detail(self, client, mock_agent_manager):
        """测试获取详情"""
        response = client.get("/api/agents/sub_abc123")

        assert response.status_code in [200, 404]

    def test_get_nonexistent_agent(self, client, mock_agent_manager):
        """测试获取不存在的 Agent"""
        mock_agent_manager.get_agent.return_value = None

        response = client.get("/api/agents/nonexistent")

        assert response.status_code == 404
```

### 3.3 终止子代理测试

```python
class TestTerminateAgent:
    """终止 Agent 测试"""

    def test_terminate_running_agent(self, client, mock_agent_manager):
        """测试终止运行中的 Agent"""
        response = client.post("/api/agents/sub_abc123/terminate")

        assert response.status_code in [200, 404]

    def test_terminate_completed_agent(self, client, mock_agent_manager):
        """测试终止已完成的 Agent"""
        response = client.post("/api/agents/sub_completed/terminate")

        # 已完成的不应该被终止
        assert response.status_code in [200, 400, 404]

    def test_terminate_nonexistent_agent(self, client, mock_agent_manager):
        """测试终止不存在的 Agent"""
        response = client.post("/api/agents/nonexistent/terminate")

        assert response.status_code == 404
```

### 3.4 日志流测试

```python
class TestAgentLogs:
    """Agent 日志测试"""

    def test_get_agent_logs(self, client, mock_agent_manager):
        """测试获取日志"""
        response = client.get("/api/agents/sub_abc123/logs")

        # SSE 流式响应
        assert response.status_code in [200, 404]
        assert "text/event-stream" in response.headers.get("content-type", "")
```

---

## 4. Agent 管理器测试

```python
class TestAgentManager:
    """Agent 管理器测试"""

    def test_create_agent(self):
        """测试创建 Agent"""
        from app.agents.manager import AgentManager

        manager = AgentManager()
        agent = manager.create_agent(
            parent_task_id="task_xyz",
            prompt="分析代码"
        )

        assert agent.parent_task_id == "task_xyz"
        assert agent.status == AgentStatus.RUNNING
        assert agent.id in manager.agents

    def test_update_status(self):
        """测试更新状态"""
        manager = AgentManager()
        agent = manager.create_agent("task_xyz", "test")

        manager.update_status(agent.id, AgentStatus.COMPLETED)

        assert manager.agents[agent.id].status == AgentStatus.COMPLETED

    def test_terminate_agent(self):
        """测试终止 Agent"""
        manager = AgentManager()
        agent = manager.create_agent("task_xyz", "test")

        result = manager.terminate(agent.id)

        assert result is True
        assert manager.agents[agent.id].status == AgentStatus.TERMINATED

    def test_get_agents_by_status(self):
        """测试按状态获取"""
        manager = AgentManager()
        agent1 = manager.create_agent("task_1", "test1")
        agent2 = manager.create_agent("task_2", "test2")

        manager.update_status(agent1.id, AgentStatus.COMPLETED)

        running = manager.get_agents(status=AgentStatus.RUNNING)
        completed = manager.get_agents(status=AgentStatus.COMPLETED)

        assert len(running) == 1
        assert len(completed) == 1
```

---

## 5. E2E 测试

```python
# tests/e2e/test_agents.py

class TestAgentMonitorPageE2E:
    """Agent 监控页面 E2E 测试"""

    def test_agent_page_loads(self, page: Page):
        """测试页面加载"""
        page.goto("http://127.0.0.1:8000/")
        page.click("text=Agent 监控")

        expect(page.locator("h1")).to_contain_text("Agent")

    def test_status_filter(self, page: Page):
        """测试状态筛选"""
        page.goto("http://127.0.0.1:8000/agents")

        page.click("text=运行中")
        # 验证筛选结果

    def test_terminate_button(self, page: Page):
        """测试终止按钮"""
        page.goto("http://127.0.0.1:8000/agents")

        page.click("text=终止")
        # 验证确认对话框
```

---

## 6. 运行测试

```bash
# 运行 Agent 相关测试
uv run pytest tests/ -k "agent" -v
```

---

## 7. 验收标准

- [ ] 子代理列表 API 正常工作
- [ ] 支持按状态筛选
- [ ] 支持按父任务筛选
- [ ] 支持数量限制
- [ ] 子代理详情 API 正常工作
- [ ] 终止 API 正常工作
- [ ] 日志流 API 正常工作
- [ ] UI 正确显示所有功能
