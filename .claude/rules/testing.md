# 测试策略

> 本文件定义项目的测试要求、覆盖率和 pytest 最佳实践。

## 测试覆盖率要求

- **最低覆盖率: 80%**
- **核心模块目标: 90%+**
- 新代码必须包含测试

## 测试结构

```
tests/
├── __init__.py
├── conftest.py           # 共享 fixtures
├── test_runner.py        # ClaudeCodeClient 测试
├── test_api.py           # API 端点测试
├── test_scenarios.py     # 场景测试
└── fixtures/
    └── mock_responses.py # 模拟数据
```

## pytest 配置

### pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
markers = [
    "slow: 标记慢测试",
    "integration: 标记集成测试",
]
```

## 测试类型

### 1. 单元测试

测试单个函数或类的行为：

```python
import pytest
from app.claude_runner.client import MessageType, StreamMessage

class TestStreamMessage:
    """StreamMessage 单元测试"""

    def test_message_creation(self):
        """测试消息创建"""
        msg = StreamMessage(
            type=MessageType.TEXT,
            content="Hello",
        )
        assert msg.type == MessageType.TEXT
        assert msg.content == "Hello"

    @pytest.mark.parametrize("msg_type,content", [
        (MessageType.TEXT, "text content"),
        (MessageType.ERROR, "error message"),
        (MessageType.COMPLETE, "done"),
    ])
    def test_various_types(self, msg_type: MessageType, content: str):
        """参数化测试多种消息类型"""
        msg = StreamMessage(type=msg_type, content=content)
        assert msg.type == msg_type
```

### 2. 异步测试

使用 `pytest-asyncio`：

```python
@pytest.mark.asyncio
async def test_track_tool_use():
    """测试工具使用跟踪"""
    client = ClaudeCodeClient()

    await client._track_tool_use("Edit", {"file_path": "/test/file.py"})

    assert "/test/file.py" in client._files_changed
    assert "Edit" in client._tools_used
```

### 3. API 测试

使用 FastAPI TestClient：

```python
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

class TestAPI:
    """API 端点测试"""

    def test_get_status(self, client: TestClient):
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    def test_task_validation(self, client: TestClient):
        # 缺少 prompt 应返回 422
        response = client.post("/api/task", json={})
        assert response.status_code == 422
```

### 4. Mock 测试

使用 `unittest.mock` 隔离外部依赖：

```python
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
class TestClaudeCodeClientMocked:
    """使用 Mock 的客户端测试"""

    @patch("app.claude_runner.client.ClaudeSDKClient")
    async def test_run_stream_yields_messages(self, mock_sdk):
        """测试流式输出"""
        # 配置 mock
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.query = AsyncMock()
        mock_instance.receive_response = AsyncMock(return_value=[])
        mock_sdk.return_value = mock_instance

        client = ClaudeCodeClient()
        messages = []
        async for msg in client.run_stream("test"):
            messages.append(msg)

        # 验证
        mock_instance.query.assert_called_once_with("test")
```

## Fixtures 使用

### conftest.py 共享 fixtures

```python
import pytest
from app.claude_runner import ClaudeCodeClient

@pytest.fixture
def client() -> ClaudeCodeClient:
    """创建默认客户端"""
    return ClaudeCodeClient(working_dir="/test")

@pytest.fixture
def sample_task_request() -> dict:
    """示例任务请求"""
    return {
        "prompt": "测试任务",
        "working_dir": "/test/project",
    }
```

### fixture 使用

```python
def test_with_fixtures(client: ClaudeCodeClient, sample_task_request: dict):
    """使用 fixtures 的测试"""
    assert client.working_dir == "/test"
    assert sample_task_request["prompt"] == "测试任务"
```

## 场景测试

测试真实使用场景的核心逻辑：

```python
class TestScenarios:
    """模拟场景测试"""

    @pytest.mark.asyncio
    async def test_scenario_code_review(self):
        """
        场景: 代码审查

        验证: Read 工具被正确跟踪，不修改文件
        """
        client = ClaudeCodeClient()

        await client._track_tool_use("Read", {"file_path": "/test/auth.py"})

        assert "Read" in client._tools_used
        assert "/test/auth.py" not in client._files_changed

    @pytest.mark.asyncio
    async def test_scenario_batch_edit(self):
        """
        场景: 批量编辑多个文件
        """
        client = ClaudeCodeClient()

        files = ["/test/a.py", "/test/b.py", "/test/c.py"]
        for f in files:
            await client._track_tool_use("Edit", {"file_path": f})

        assert len(client._files_changed) == 3
```

## 运行测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行并显示覆盖率
uv run pytest tests/ -v --cov=app --cov-report=term-missing

# 运行特定测试
uv run pytest tests/test_runner.py::TestClaudeCodeClient -v

# 运行标记的测试
uv run pytest tests/ -m "not slow" -v
```

## 测试检查清单

在提交代码前确认：

- [ ] 所有测试通过
- [ ] 覆盖率 ≥ 80%
- [ ] 新功能有对应测试
- [ ] 边界条件已测试
- [ ] 错误路径已测试
- [ ] Mock 使用得当，不过度模拟
