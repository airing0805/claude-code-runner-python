# Claude 状态 - 测试文档

## 概述

Claude 状态测试文档整合了环境信息展示、状态查询和工具统计展示三个模块的测试内容。

> **来源文档**: 本文档由以下测试文档合并而成：
> - 环境信息展示-测试.md
> - 状态查询-测试.md
> - 工具统计展示-测试.md

---

## 1. 测试策略

### 1.1 测试目标

验证 Claude 状态相关 API 的功能完整性和安全性。

### 1.2 测试范围

| 模块 | 测试内容 |
|------|---------|
| 版本信息 API | 返回正确的版本数据格式 |
| 环境变量 API | 敏感信息隐藏、仅返回相关变量 |
| 配置信息 API | 返回正确的配置数据 |
| 服务状态 API | 运行状态、工作目录、活跃任务 |
| 工具列表 API | 可用工具列表 |
| 工具使用统计 | 数据格式、统计准确性 |
| 权限模式说明 | 四种模式描述完整 |

---

## 2. 单元测试

### 2.1 敏感信息隐藏函数测试

```python
# tests/test_claude_env.py

from app.claude.utils import mask_sensitive_value, SENSITIVE_KEYS

class TestSensitiveValueMasking:
    """敏感信息隐藏测试"""

    def test_mask_api_key(self):
        """测试 API Key 隐藏"""
        assert mask_sensitive_value("ANTHROPIC_API_KEY", "sk-xxx") == "***"
        assert mask_sensitive_value("api_key", "secret") == "***"
        assert mask_sensitive_value("APIKEY", "token") == "***"

    def test_mask_token(self):
        """测试 Token 隐藏"""
        assert mask_sensitive_value("TOKEN", "abc123") == "***"
        assert mask_sensitive_value("GITHUB_TOKEN", "ghp_xxx") == "***"

    def test_mask_password(self):
        """测试密码隐藏"""
        assert mask_sensitive_value("PASSWORD", "mypassword") == "***"
        assert mask_sensitive_value("DB_PASSWORD", "dbpass") == "***"

    def test_mask_secret(self):
        """测试 Secret 隐藏"""
        assert mask_sensitive_value("SECRET_KEY", "secret") == "***"
        assert mask_sensitive_value("PRIVATE_KEY", "key") == "***"

    def test_no_mask_regular_values(self):
        """测试普通变量不隐藏"""
        assert mask_sensitive_value("WORKING_DIR", "/home/user") == "/home/user"
        assert mask_sensitive_value("PORT", "8000") == "8000"
        assert mask_sensitive_value("DEBUG", "true") == "true"

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        assert mask_sensitive_value("anthropic_api_key", "key") == "***"
        assert mask_sensitive_value("Api_Key", "key") == "***"
```

### 2.2 数据模型测试

```python
from app.claude.schemas import VersionInfo, EnvInfo, ConfigInfo, RuntimeInfo
from app.status.schemas import StatusResponse, ToolInfo

class TestVersionInfo:
    """版本信息模型测试"""

    def test_valid_version_info(self):
        """测试有效版本信息"""
        info = VersionInfo(
            cli_version="1.0.12",
            sdk_version="0.0.25",
            runtime=RuntimeInfo(
                os="Windows",
                os_version="11",
                python_version="3.12.0"
            )
        )
        assert info.cli_version == "1.0.12"
        assert info.sdk_version == "0.0.25"

    def test_version_info_from_dict(self):
        """测试从字典创建"""
        data = {
            "cli_version": "1.0.12",
            "sdk_version": "0.0.25",
            "runtime": {
                "os": "Windows",
                "os_version": "11",
                "python_version": "3.12.0"
            }
        }
        info = VersionInfo(**data)
        assert info.runtime.os == "Windows"


class TestEnvInfo:
    """环境变量模型测试"""

    def test_env_info_with_masked_values(self):
        """测试包含隐藏值的环境变量"""
        info = EnvInfo(
            variables={
                "ANTHROPIC_API_KEY": "***",
                "WORKING_DIR": "/test",
                "PORT": "8000"
            }
        )
        assert info.variables["ANTHROPIC_API_KEY"] == "***"
        assert info.variables["WORKING_DIR"] == "/test"


class TestConfigInfo:
    """配置信息模型测试"""

    def test_config_info(self):
        """测试配置信息"""
        info = ConfigInfo(
            working_dir="/test/path",
            default_permission_mode="acceptEdits",
            allowed_tools=["Read", "Write", "Edit"]
        )
        assert info.working_dir == "/test/path"
        assert len(info.allowed_tools) == 3


class TestStatusResponse:
    """状态响应模型测试"""

    def test_status_response_creation(self):
        """测试状态响应创建"""
        response = StatusResponse(
            status="running",
            working_dir="/test/path",
            active_tasks=2
        )
        assert response.status == "running"
        assert response.working_dir == "/test/path"
        assert response.active_tasks == 2

    def test_status_stopped(self):
        """测试停止状态"""
        response = StatusResponse(
            status="stopped",
            working_dir="/test/path",
            active_tasks=0
        )
        assert response.status == "stopped"
        assert response.active_tasks == 0


class TestToolInfo:
    """工具信息模型测试"""

    def test_tool_info_creation(self):
        """测试工具信息创建"""
        tool = ToolInfo(
            name="Read",
            description="读取文件内容"
        )
        assert tool.name == "Read"
        assert tool.description == "读取文件内容"


class TestToolUsage:
    """工具使用统计模型测试"""

    def test_tool_usage_creation(self):
        """测试工具使用统计创建"""
        usage = ToolUsage(
            Read=15,
            Write=3,
            Edit=8,
            Bash=5,
            Glob=12,
            Grep=7,
            WebSearch=2,
            WebFetch=1,
            Task=0
        )
        assert usage.Read == 15
        assert usage.Write == 3
        assert usage.Task == 0

    def test_tool_usage_default_zero(self):
        """测试默认值"""
        usage = ToolUsage()
        assert usage.Read == 0
        assert usage.Write == 0


class TestTaskStats:
    """任务统计模型测试"""

    def test_task_stats_creation(self):
        """测试任务统计创建"""
        stats = TaskStats(
            total=10,
            success=9,
            failed=1,
            avg_duration_ms=3500,
            total_cost_usd=0.52
        )
        assert stats.total == 10
        assert stats.success == 9
        assert stats.failed == 1


class TestPermissionMode:
    """权限模式模型测试"""

    def test_permission_mode_creation(self):
        """测试权限模式创建"""
        mode = PermissionMode(
            name="default",
            description="默认模式，每次工具调用需要用户确认",
            scenarios=["安全性要求高的场景"]
        )
        assert mode.name == "default"
        assert len(mode.scenarios) == 1

    def test_all_permission_modes(self):
        """测试所有权限模式"""
        modes_info = PermissionModesInfo(modes=[
            PermissionMode(name="default", description="默认模式", scenarios=["场景1"]),
            PermissionMode(name="acceptEdits", description="自动接受编辑", scenarios=["场景2"]),
            PermissionMode(name="plan", description="规划模式", scenarios=["场景3"]),
            PermissionMode(name="bypassPermissions", description="跳过权限", scenarios=["场景4"]),
        ])
        assert len(modes_info.modes) == 4
```

---

## 3. 集成测试

### 3.1 版本信息 API 测试

```python
class TestVersionEndpoint:
    """版本信息 API 测试"""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_get_version_success(self, client):
        """测试获取版本成功"""
        response = client.get("/api/claude/version")

        assert response.status_code == 200
        data = response.json()

        # 验证必要字段
        assert "cli_version" in data
        assert "sdk_version" in data
        assert "runtime" in data

        # 验证 runtime 字段
        assert "os" in data["runtime"]
        assert "os_version" in data["runtime"]
        assert "python_version" in data["runtime"]

    def test_version_response_format(self, client):
        """测试版本响应格式"""
        response = client.get("/api/claude/version")
        data = response.json()

        # 验证字段类型
        assert isinstance(data["cli_version"], str)
        assert isinstance(data["sdk_version"], str)
        assert isinstance(data["runtime"], dict)
```

### 3.2 环境变量 API 测试

```python
class TestEnvEndpoint:
    """环境变量 API 测试"""

    def test_get_env_success(self, client):
        """测试获取环境变量成功"""
        response = client.get("/api/claude/env")

        assert response.status_code == 200
        data = response.json()
        assert "variables" in data

    def test_api_key_is_masked(self, client):
        """测试 API Key 被隐藏"""
        response = client.get("/api/claude/env")
        data = response.json()

        # 验证 API Key 被隐藏
        if "ANTHROPIC_API_KEY" in data["variables"]:
            assert data["variables"]["ANTHROPIC_API_KEY"] == "***"

    def test_no_sensitive_data_exposed(self, client):
        """测试没有敏感数据泄露"""
        response = client.get("/api/claude/env")
        data = response.json()

        # 验证不包含明文敏感信息
        variables = data.get("variables", {})
        for key, value in variables.items():
            if "KEY" in key.upper() or "TOKEN" in key.upper():
                assert value == "***", f"敏感变量 {key} 未被隐藏"
            if "PASSWORD" in key.upper() or "SECRET" in key.upper():
                assert value == "***", f"敏感变量 {key} 未被隐藏"

    def test_only_relevant_variables(self, client):
        """测试只返回相关变量"""
        response = client.get("/api/claude/env")
        data = response.json()

        variables = data.get("variables", {})
        # 应该包含至少一个相关变量，或者返回空
        assert isinstance(variables, dict)
```

### 3.3 配置信息 API 测试

```python
class TestConfigEndpoint:
    """配置信息 API 测试"""

    def test_get_config_success(self, client):
        """测试获取配置成功"""
        response = client.get("/api/claude/config")

        assert response.status_code == 200
        data = response.json()

        # 验证必要字段
        assert "working_dir" in data
        assert "default_permission_mode" in data
        assert "allowed_tools" in data

    def test_allowed_tools_is_list(self, client):
        """测试 allowed_tools 是列表"""
        response = client.get("/api/claude/config")
        data = response.json()

        assert isinstance(data["allowed_tools"], list)
        # 验证包含常用工具
        expected_tools = ["Read", "Write", "Edit", "Bash"]
        for tool in expected_tools:
            assert tool in data["allowed_tools"]

    def test_permission_mode_valid(self, client):
        """测试权限模式有效"""
        response = client.get("/api/claude/config")
        data = response.json()

        valid_modes = ["default", "acceptEdits", "plan", "bypassPermissions"]
        assert data["default_permission_mode"] in valid_modes
```

### 3.4 服务状态 API 测试

```python
class TestStatusEndpoint:
    """状态 API 测试"""

    def test_get_status_success(self, client):
        """测试获取服务状态成功"""
        response = client.get("/api/status")

        assert response.status_code == 200
        data = response.json()

        # 验证必要字段
        assert "status" in data
        assert "working_dir" in data
        assert "active_tasks" in data

    def test_status_running(self, client):
        """测试运行状态"""
        response = client.get("/api/status")
        data = response.json()

        # status 应该是 running 或 stopped
        assert data["status"] in ["running", "stopped"]

    def test_active_tasks_type(self, client):
        """测试活跃任务数为整数"""
        response = client.get("/api/status")
        data = response.json()

        assert isinstance(data["active_tasks"], int)
        assert data["active_tasks"] >= 0
```

### 3.5 工具列表 API 测试

```python
class TestToolsEndpoint:
    """工具列表 API 测试"""

    def test_get_tools_success(self, client):
        """测试获取工具列表成功"""
        response = client.get("/api/tools")

        assert response.status_code == 200
        data = response.json()

        assert "tools" in data

    def test_tool_structure(self, client):
        """测试工具信息结构"""
        response = client.get("/api/tools")
        data = response.json()

        tool = data["tools"][0]
        required_fields = ["name", "description"]

        for field in required_fields:
            assert field in tool

    def test_tool_descriptions_not_empty(self, client):
        """测试工具描述不为空"""
        response = client.get("/api/tools")
        data = response.json()

        for tool in data["tools"]:
            assert len(tool["description"]) > 0
```

### 3.6 工具统计 API 测试

```python
class TestStatsEndpoint:
    """工具统计 API 测试"""

    def test_get_stats_success(self, client):
        """测试获取统计成功"""
        response = client.get("/api/claude/stats")

        assert response.status_code == 200
        data = response.json()

        # 验证结构
        assert "tools_usage" in data
        assert "files_changed" in data
        assert "task_stats" in data

    def test_tools_usage_structure(self, client):
        """测试工具使用统计结构"""
        response = client.get("/api/claude/stats")
        data = response.json()

        tools = data["tools_usage"]
        expected_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebSearch", "WebFetch", "Task"]

        for tool in expected_tools:
            assert tool in tools, f"缺少工具: {tool}"
            assert isinstance(tools[tool], int), f"{tool} 应该是整数"

    def test_task_stats_structure(self, client):
        """测试任务统计结构"""
        response = client.get("/api/claude/stats")
        data = response.json()

        task_stats = data["task_stats"]
        required_fields = ["total", "success", "failed", "avg_duration_ms", "total_cost_usd"]

        for field in required_fields:
            assert field in task_stats, f"缺少字段: {field}"
```

### 3.7 权限模式 API 测试

```python
class TestPermissionModesEndpoint:
    """权限模式 API 测试"""

    def test_get_permission_modes_success(self, client):
        """测试获取权限模式成功"""
        response = client.get("/api/claude/permission-modes")

        assert response.status_code == 200
        data = response.json()

        assert "modes" in data
        assert len(data["modes"]) == 4

    def test_all_modes_present(self, client):
        """测试所有模式都存在"""
        response = client.get("/api/claude/permission-modes")
        data = response.json()

        mode_names = [mode["name"] for mode in data["modes"]]
        expected_names = ["default", "acceptEdits", "plan", "bypassPermissions"]

        for name in expected_names:
            assert name in mode_names, f"缺少模式: {name}"

    def test_mode_descriptions(self, client):
        """测试模式描述"""
        response = client.get("/api/claude/permission-modes")
        data = response.json()

        for mode in data["modes"]:
            assert "name" in mode
            assert "description" in mode
            assert "scenarios" in mode
            assert isinstance(mode["scenarios"], list)
            assert len(mode["scenarios"]) > 0
```

---

## 4. 安全测试

### 4.1 敏感信息泄露测试

```python
class TestSecurity:
    """安全测试"""

    def test_no_plain_text_credentials(self, client):
        """测试没有明文凭证"""
        response = client.get("/api/claude/env")
        data = response.json()

        variables = json.dumps(data)

        # 验证不包含常见 API Key 模式
        import re
        patterns = [
            r"sk-ant-api[03]-\w+",  # Anthropic API Key
            r"ghp_\w+",             # GitHub Token
            r"sk-\w+",              # OpenAI Key
        ]

        for pattern in patterns:
            matches = re.findall(pattern, variables, re.IGNORECASE)
            assert len(matches) == 0, f"发现可能的 API Key: {matches}"

    def test_unauthorized_access_denied(self, client):
        """测试未授权访问被拒绝"""
        # 如果实现了认证，测试未登录访问
        pass
```

---

## 5. 性能测试

```python
class TestPerformance:
    """性能测试"""

    def test_response_time(self, client):
        """测试响应时间 < 100ms"""
        import time

        start = time.time()
        response = client.get("/api/claude/version")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.1  # 100ms

    def test_status_response_time(self, client):
        """测试状态查询响应时间"""
        import time

        start = time.time()
        response = client.get("/api/status")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.1  # 100ms

    def test_tools_response_time(self, client):
        """测试工具列表响应时间"""
        import time

        start = time.time()
        response = client.get("/api/tools")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.1  # 100ms
```

---

## 6. E2E 测试

```python
# tests/e2e/test_claude_status.py

class TestClaudeStatusPageE2E:
    """Claude 状态页面 E2E 测试"""

    def test_status_page_loads(self, page: Page):
        """测试状态页面加载"""
        page.goto("http://127.0.0.1:8000/")
        page.click("text=Claude 状态")

        expect(page.locator("h1")).to_contain_text("Claude 状态")

    def test_version_info_displayed(self, page: Page):
        """测试版本信息显示"""
        page.goto("http://127.0.0.1:8000/claude/status")

        # 验证版本信息显示
        expect(page.locator(".version-info")).to_be_visible()
        expect(page.locator(".cli-version")).to_be_visible()

    def test_env_variables_displayed(self, page: Page):
        """测试环境变量显示"""
        page.goto("http://127.0.0.1:8000/claude/status")

        # 验证环境变量显示
        expect(page.locator(".env-variables")).to_be_visible()

    def test_sensitive_data_masked_in_ui(self, page: Page):
        """测试 UI 中敏感数据被隐藏"""
        page.goto("http://127.0.0.1:8000/claude/status")

        # 验证 API Key 显示为 ***
        api_key_element = page.locator(".env-variables")
        if api_key_element:
            assert "***" in api_key_element.text_content()

    def test_permission_modes_displayed(self, page: Page):
        """测试权限模式显示"""
        page.goto("http://127.0.0.1:8000/claude/status")

        # 验证四种模式都显示
        expect(page.locator("text=default")).to_be_visible()
        expect(page.locator("text=acceptEdits")).to_be_visible()
        expect(page.locator("text=plan")).to_be_visible()
        expect(page.locator("text=bypassPermissions")).to_be_visible()
```

---

## 7. 运行测试

```bash
# 运行 Claude 状态相关测试
uv run pytest tests/ -k "claude or status or tools or stats or permission" -v

# 运行敏感信息隐藏测试
uv run pytest tests/test_claude_env.py -v

# 运行 API 测试
uv run pytest tests/ -k "env or version or config" -v
```

---

## 8. 验收标准

- [x] 版本信息 API 返回正确格式
- [x] 环境变量 API 正确隐藏敏感信息
- [x] 配置信息 API 返回完整配置
- [x] 服务状态 API 正常工作
- [x] 工具列表 API 正常工作
- [x] 工具使用统计 API 正确显示
- [x] 权限模式说明包含四种模式
- [x] UI 正确显示所有信息
- [x] 安全测试通过 - 无明文敏感数据
- [x] 性能测试通过 - 响应时间 < 100ms
