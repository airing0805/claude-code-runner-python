"""v0.3.1 环境信息展示测试"""

import pytest
from fastapi.testclient import TestClient


class TestSensitiveValueMasking:
    """敏感信息隐藏函数测试"""

    def test_mask_api_key(self):
        """测试 API Key 隐藏"""
        from app.routers.claude import mask_sensitive_value

        assert mask_sensitive_value("ANTHROPIC_API_KEY", "sk-xxx") == "***"
        assert mask_sensitive_value("api_key", "secret") == "***"
        # APIKEY 作为独立单词时应被隐藏
        assert mask_sensitive_value("API_KEY", "token") == "***"

    def test_mask_token(self):
        """测试 Token 隐藏"""
        from app.routers.claude import mask_sensitive_value

        assert mask_sensitive_value("TOKEN", "abc123") == "***"
        assert mask_sensitive_value("GITHUB_TOKEN", "ghp_xxx") == "***"

    def test_mask_password(self):
        """测试密码隐藏"""
        from app.routers.claude import mask_sensitive_value

        assert mask_sensitive_value("PASSWORD", "mypassword") == "***"
        assert mask_sensitive_value("DB_PASSWORD", "dbpass") == "***"

    def test_mask_secret(self):
        """测试 Secret 隐藏"""
        from app.routers.claude import mask_sensitive_value

        assert mask_sensitive_value("SECRET_KEY", "secret") == "***"
        assert mask_sensitive_value("PRIVATE_KEY", "key") == "***"

    def test_no_mask_regular_values(self):
        """测试普通变量不隐藏"""
        from app.routers.claude import mask_sensitive_value

        assert mask_sensitive_value("WORKING_DIR", "/home/user") == "/home/user"
        assert mask_sensitive_value("PORT", "8000") == "8000"
        assert mask_sensitive_value("DEBUG", "true") == "true"

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        from app.routers.claude import mask_sensitive_value

        assert mask_sensitive_value("anthropic_api_key", "key") == "***"
        assert mask_sensitive_value("Api_Key", "key") == "***"


class TestVersionEndpoint:
    """版本信息 API 测试"""

    @pytest.fixture
    def client(self):
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


class TestEnvEndpoint:
    """环境变量 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app

        return TestClient(app)

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
            if "KEY" in key.upper() and "API" in key.upper():
                assert value == "***", f"敏感变量 {key} 未被隐藏"
            if "TOKEN" in key.upper():
                assert value == "***", f"敏感变量 {key} 未被隐藏"

    def test_only_relevant_variables(self, client):
        """测试只返回相关变量"""
        response = client.get("/api/claude/env")
        data = response.json()

        variables = data.get("variables", {})
        # 验证包含 Claude Code 相关变量
        relevant_keys = ["WORKING_DIR", "CLAUDECODE", "PORT"]
        # 应该包含至少一个相关变量
        assert any(key in variables for key in relevant_keys)
        assert isinstance(variables, dict)


class TestConfigEndpoint:
    """配置信息 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app

        return TestClient(app)

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


class TestSecurity:
    """安全测试"""

    @pytest.fixture
    def client(self):
        from app.main import app

        return TestClient(app)

    def test_no_plain_text_credentials(self, client):
        """测试没有明文凭证"""
        import re

        response = client.get("/api/claude/env")
        data = response.json()

        variables = str(data)

        # 验证不包含常见 API Key 模式
        patterns = [
            r"sk-ant-api03-\w+",  # Anthropic API Key
            r"ghp_\w+",  # GitHub Token
            r"sk-\w+",  # OpenAI Key
        ]

        for pattern in patterns:
            matches = re.findall(pattern, variables, re.IGNORECASE)
            assert len(matches) == 0, f"发现可能的 API Key: {matches}"


class TestPerformance:
    """性能测试"""

    @pytest.fixture
    def client(self):
        from app.main import app

        return TestClient(app)

    def test_response_time(self, client):
        """测试响应时间 < 100ms"""
        import time

        start = time.time()
        response = client.get("/api/claude/version")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.1  # 100ms


# ==================== v0.3.2 工具统计展示测试 ====================

class TestStatsEndpoint:
    """工具使用统计 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app

        return TestClient(app)

    def test_get_stats_success(self, client):
        """测试获取工具使用统计成功"""
        response = client.get("/api/claude/stats")

        assert response.status_code == 200
        data = response.json()

        # 验证必要字段
        assert "tools_usage" in data
        assert "files_changed" in data
        assert "task_stats" in data

    def test_stats_tools_usage_fields(self, client):
        """测试工具使用统计字段"""
        response = client.get("/api/claude/stats")
        data = response.json()

        # 验证 tools_usage 是字典类型
        assert isinstance(data["tools_usage"], dict)

        # 验证返回的工具统计格式正确（值为整数）
        for tool, count in data["tools_usage"].items():
            assert isinstance(tool, str)
            assert isinstance(count, int)
            assert count >= 0

    def test_stats_task_stats_fields(self, client):
        """测试任务统计字段"""
        response = client.get("/api/claude/stats")
        data = response.json()

        task_stats = data["task_stats"]

        # 验证任务统计字段
        assert "total" in task_stats
        assert "success" in task_stats
        assert "failed" in task_stats
        assert "avg_duration_ms" in task_stats
        assert "total_cost_usd" in task_stats

        # 验证字段类型
        assert isinstance(task_stats["total"], int)
        assert isinstance(task_stats["success"], int)
        assert isinstance(task_stats["failed"], int)
        assert isinstance(task_stats["avg_duration_ms"], int)
        assert isinstance(task_stats["total_cost_usd"], (int, float))

    def test_stats_files_changed(self, client):
        """测试文件变更统计"""
        response = client.get("/api/claude/stats")
        data = response.json()

        assert isinstance(data["files_changed"], int)
        assert data["files_changed"] >= 0

    def test_stats_initial_values(self, client):
        """测试初始统计值"""
        response = client.get("/api/claude/stats")
        data = response.json()

        # 初始值应该是 0
        assert data["task_stats"]["total"] == 0
        assert data["task_stats"]["success"] == 0
        assert data["task_stats"]["failed"] == 0
        assert data["files_changed"] == 0


class TestPermissionModesEndpoint:
    """权限模式说明 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app

        return TestClient(app)

    def test_get_permission_modes_success(self, client):
        """测试获取权限模式说明成功"""
        response = client.get("/api/claude/permission-modes")

        assert response.status_code == 200
        data = response.json()

        assert "modes" in data
        assert isinstance(data["modes"], list)

    def test_permission_modes_complete(self, client):
        """测试权限模式完整"""
        response = client.get("/api/claude/permission-modes")
        data = response.json()

        modes = data["modes"]

        # 验证四种模式都存在
        mode_names = [m["name"] for m in modes]
        expected_modes = ["default", "acceptEdits", "plan", "bypassPermissions"]
        for mode in expected_modes:
            assert mode in mode_names, f"缺少权限模式: {mode}"

    def test_permission_mode_structure(self, client):
        """测试权限模式数据结构"""
        response = client.get("/api/claude/permission-modes")
        data = response.json()

        for mode in data["modes"]:
            # 验证每个模式的字段
            assert "name" in mode
            assert "description" in mode
            assert "scenarios" in mode
            assert isinstance(mode["scenarios"], list)
            assert len(mode["scenarios"]) > 0

    def test_permission_mode_descriptions(self, client):
        """测试权限模式描述内容"""
        response = client.get("/api/claude/permission-modes")
        data = response.json()

        # 验证描述不为空
        for mode in data["modes"]:
            assert len(mode["description"]) > 0
            assert len(mode["scenarios"]) > 0


class TestToolsDocsEndpoint:
    """工具文档 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app

        return TestClient(app)

    def test_get_tools_docs_success(self, client):
        """测试获取工具文档成功"""
        response = client.get("/api/claude/docs/tools")

        assert response.status_code == 200
        data = response.json()

        assert "tools" in data
        assert isinstance(data["tools"], list)

    def test_tools_docs_complete(self, client):
        """测试工具文档完整"""
        response = client.get("/api/claude/docs/tools")
        data = response.json()

        tools = data["tools"]

        # 验证 9 个工具都存在
        tool_names = [t["name"] for t in tools]
        expected_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebSearch", "WebFetch", "Task"]
        for tool in expected_tools:
            assert tool in tool_names, f"缺少工具: {tool}"

    def test_tool_doc_structure(self, client):
        """测试工具文档结构"""
        response = client.get("/api/claude/docs/tools")
        data = response.json()

        for tool in data["tools"]:
            # 验证必要字段
            assert "name" in tool
            assert "description" in tool
            assert "category" in tool
            assert "modifies_files" in tool
            assert "parameters" in tool
            assert "example" in tool

            # 验证字段类型
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)
            assert isinstance(tool["category"], str)
            assert isinstance(tool["modifies_files"], bool)
            assert isinstance(tool["parameters"], list)
            assert isinstance(tool["example"], dict)

    def test_tool_modifies_files_accuracy(self, client):
        """测试工具 modifies_files 准确性"""
        response = client.get("/api/claude/docs/tools")
        data = response.json()

        # Read、Glob、Grep、WebSearch、WebFetch、Task 不应修改文件
        readonly_tools = ["Read", "Glob", "Grep", "WebSearch", "WebFetch", "Task"]
        for tool in data["tools"]:
            if tool["name"] in readonly_tools:
                assert tool["modifies_files"] is False, f"{tool['name']} 应标记为不修改文件"

        # Write、Edit 应修改文件
        modify_tools = ["Write", "Edit"]
        for tool in data["tools"]:
            if tool["name"] in modify_tools:
                assert tool["modifies_files"] is True, f"{tool['name']} 应标记为修改文件"
