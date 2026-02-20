# 文档展示 - 测试文档

## 1. 测试策略

### 1.1 测试目标

验证文档展示 API 的功能完整性和内容准确性。

### 1.2 测试范围

| 模块 | 测试内容 |
|------|---------|
| 工具详解文档 | 9个工具详细信息 |
| 代理类型说明 | 9种代理类型 |
| 内置命令说明 | 5个命令 |
| 最佳实践指南 | 工具选择、权限模式、错误处理 |

---

## 2. 单元测试

### 2.1 数据模型测试

```python
# tests/test_docs.py

from app.claude.docs_data import (
    Parameter, ToolExample, ToolDoc,
    AgentDoc, CommandOption, CommandDoc,
    BestPracticesDoc
)

class TestToolDoc:
    """工具文档模型测试"""

    def test_tool_doc_creation(self):
        """测试工具文档创建"""
        tool = ToolDoc(
            name="Read",
            description="读取文件内容",
            category="文件操作",
            modifies_files=False,
            parameters=[
                Parameter(
                    name="file_path",
                    type="string",
                    required=True,
                    description="要读取的文件路径"
                )
            ],
            example=ToolExample(
                input={"file_path": "/path/to/file.py"},
                description="读取整个文件"
            )
        )
        assert tool.name == "Read"
        assert tool.modifies_files is False
        assert len(tool.parameters) == 1

    def test_tool_doc_validates_modifies_files(self):
        """测试 modifies_files 字段"""
        read_tool = ToolDoc(
            name="Read",
            description="读取",
            category="文件操作",
            modifies_files=False,
            parameters=[],
            example=ToolExample(input={}, description="")
        )
        assert read_tool.modifies_files is False

        write_tool = ToolDoc(
            name="Write",
            description="写入",
            category="文件操作",
            modifies_files=True,
            parameters=[],
            example=ToolExample(input={}, description="")
        )
        assert write_tool.modifies_files is True


class TestAgentDoc:
    """代理文档模型测试"""

    def test_agent_doc_creation(self):
        """测试代理文档创建"""
        agent = AgentDoc(
            name="general-purpose",
            description="通用任务代理",
            use_cases=["处理各种编程任务", "回答问题"]
        )
        assert agent.name == "general-purpose"
        assert len(agent.use_cases) == 2


class TestCommandDoc:
    """命令文档模型测试"""

    def test_command_doc_creation(self):
        """测试命令文档创建"""
        command = CommandDoc(
            name="/commit",
            description="提交当前更改到 Git",
            usage="/commit -m \"message\"",
            options=[
                CommandOption(name="-m", description="提交信息")
            ]
        )
        assert command.name == "/commit"
        assert command.usage == "/commit -m \"message\""
        assert len(command.options) == 1


class TestBestPracticesDoc:
    """最佳实践文档模型测试"""

    def test_best_practices_creation(self):
        """测试最佳实践文档创建"""
        practices = BestPracticesDoc(
            tool_selection={
                "read_only": ["Read", "Glob", "Grep"],
                "modify_files": ["Write", "Edit"]
            },
            permission_mode_guide=[
                {"mode": "default", "scenario": "交互式开发"},
                {"mode": "bypassPermissions", "scenario": "CI/CD"}
            ],
            error_handling={
                "try_catch": "使用 try-except",
                "logging": "记录错误"
            }
        )
        assert "read_only" in practices.tool_selection
        assert len(practices.permission_mode_guide) == 2
```

### 2.2 文档数据测试

```python
class TestDocsData:
    """文档数据测试"""

    def test_all_9_tools_present(self):
        """测试所有9个工具都存在"""
        from app.claude.docs_data import TOOLS_DOCS

        expected_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebSearch", "WebFetch", "Task"]
        actual_tools = [tool.name for tool in TOOLS_DOCS]

        for tool in expected_tools:
            assert tool in actual_tools, f"缺少工具: {tool}"

    def test_all_tools_have_required_fields(self):
        """测试所有工具都有必填字段"""
        from app.claude.docs_data import TOOLS_DOCS

        for tool in TOOLS_DOCS:
            assert tool.name, "工具缺少名称"
            assert tool.description, "工具缺少描述"
            assert tool.category, "工具缺少分类"
            assert tool.parameters is not None, "工具缺少参数列表"

    def test_all_9_agents_present(self):
        """测试所有9种代理都存在"""
        from app.claude.docs_data import AGENTS_DOCS

        expected_agents = [
            "general-purpose", "explore", "code-explorer", "code-architect",
            "code-reviewer", "agent-creator", "plugin-validator",
            "skill-reviewer", "conversation-analyzer"
        ]
        actual_agents = [agent.name for agent in AGENTS_DOCS]

        for agent in expected_agents:
            assert agent in actual_agents, f"缺少代理: {agent}"

    def test_all_5_commands_present(self):
        """测试所有5个命令都存在"""
        from app.claude.docs_data import COMMANDS_DOCS

        expected_commands = ["/commit", "/commit-push-pr", "/dedupe", "/oncall-triage", "/bug"]
        actual_commands = [cmd.name for cmd in COMMANDS_DOCS]

        for cmd in expected_commands:
            assert cmd in actual_commands, f"缺少命令: {cmd}"
```

---

## 3. 集成测试

### 3.1 工具文档 API 测试

```python
class TestToolsDocsEndpoint:
    """工具文档 API 测试"""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_get_tools_docs_success(self, client):
        """测试获取工具文档成功"""
        response = client.get("/api/claude/docs/tools")

        assert response.status_code == 200
        data = response.json()

        assert "tools" in data
        assert len(data["tools"]) == 9

    def test_tool_doc_structure(self, client):
        """测试工具文档结构"""
        response = client.get("/api/claude/docs/tools")
        data = response.json()

        tool = data["tools"][0]
        required_fields = ["name", "description", "category", "modifies_files", "parameters"]

        for field in required_fields:
            assert field in tool, f"工具文档缺少字段: {field}"

    def test_parameter_structure(self, client):
        """测试参数结构"""
        response = client.get("/api/claude/docs/tools")
        data = response.json()

        # 查找 Read 工具
        read_tool = next((t for t in data["tools"] if t["name"] == "Read"), None)
        assert read_tool is not None

        param = read_tool["parameters"][0]
        assert "name" in param
        assert "type" in param
        assert "required" in param
        assert "description" in param
```

### 3.2 代理文档 API 测试

```python
class TestAgentsDocsEndpoint:
    """代理文档 API 测试"""

    def test_get_agents_docs_success(self, client):
        """测试获取代理文档成功"""
        response = client.get("/api/claude/docs/agents")

        assert response.status_code == 200
        data = response.json()

        assert "agents" in data
        assert len(data["agents"]) == 9

    def test_agent_doc_structure(self, client):
        """测试代理文档结构"""
        response = client.get("/api/claude/docs/agents")
        data = response.json()

        agent = data["agents"][0]
        required_fields = ["name", "description", "use_cases"]

        for field in required_fields:
            assert field in agent, f"代理文档缺少字段: {field}"

    def test_use_cases_not_empty(self, client):
        """测试使用场景不为空"""
        response = client.get("/api/claude/docs/agents")
        data = response.json()

        for agent in data["agents"]:
            assert len(agent["use_cases"]) > 0, f"代理 {agent['name']} 缺少使用场景"
```

### 3.3 命令文档 API 测试

```python
class TestCommandsDocsEndpoint:
    """命令文档 API 测试"""

    def test_get_commands_docs_success(self, client):
        """测试获取命令文档成功"""
        response = client.get("/api/claude/docs/commands")

        assert response.status_code == 200
        data = response.json()

        assert "commands" in data
        assert len(data["commands"]) == 5

    def test_command_doc_structure(self, client):
        """测试命令文档结构"""
        response = client.get("/api/claude/docs/commands")
        data = response.json()

        command = data["commands"][0]
        required_fields = ["name", "description", "usage", "options"]

        for field in required_fields:
            assert field in command, f"命令文档缺少字段: {field}"

    def test_all_required_commands(self, client):
        """测试所有必需命令"""
        response = client.get("/api/claude/docs/commands")
        data = response.json()

        command_names = [cmd["name"] for cmd in data["commands"]]
        required = ["/commit", "/commit-push-pr", "/dedupe", "/oncall-triage", "/bug"]

        for cmd in required:
            assert cmd in command_names, f"缺少命令: {cmd}"
```

### 3.4 最佳实践 API 测试

```python
class TestBestPracticesEndpoint:
    """最佳实践 API 测试"""

    def test_get_best_practices_success(self, client):
        """测试获取最佳实践成功"""
        response = client.get("/api/claude/docs/best-practices")

        assert response.status_code == 200
        data = response.json()

        required_sections = ["tool_selection", "permission_mode_guide", "error_handling"]
        for section in required_sections:
            assert section in data, f"缺少章节: {section}"

    def test_tool_selection_structure(self, client):
        """测试工具选择结构"""
        response = client.get("/api/claude/docs/best-practices")
        data = response.json()

        tool_selection = data["tool_selection"]
        assert "read_only" in tool_selection
        assert "modify_files" in tool_selection

    def test_permission_mode_guide(self, client):
        """测试权限模式指南"""
        response = client.get("/api/claude/docs/best-practices")
        data = response.json()

        guide = data["permission_mode_guide"]
        assert len(guide) == 4  # 四种模式

        modes = [item["mode"] for item in guide]
        assert "default" in modes
        assert "acceptEdits" in modes
        assert "plan" in modes
        assert "bypassPermissions" in modes
```

---

## 4. 内容准确性测试

### 4.1 工具描述准确性

```python
class TestDocsAccuracy:
    """文档内容准确性测试"""

    def test_read_tool_description(self):
        """测试 Read 工具描述"""
        from app.claude.docs_data import TOOLS_DOCS
        read_tool = next((t for t in TOOLS_DOCS if t.name == "Read"), None)

        assert "读取" in read_tool.description
        assert read_tool.modifies_files is False

    def test_write_tool_description(self):
        """测试 Write 工具描述"""
        from app.claude.docs_data import TOOLS_DOCS
        write_tool = next((t for t in TOOLS_DOCS if t.name == "Write"), None)

        assert "创建" in write_tool.description or "写入" in write_tool.description
        assert write_tool.modifies_files is True

    def test_bash_tool_has_command_param(self):
        """测试 Bash 工具参数"""
        from app.claude.docs_data import TOOLS_DOCS
        bash_tool = next((t for t in TOOLS_DOCS if t.name == "Bash"), None)

        param_names = [p.name for p in bash_tool.parameters]
        assert "command" in param_names

    def test_general_purpose_agent(self):
        """测试通用代理"""
        from app.claude.docs_data import AGENTS_DOCS
        agent = next((a for a in AGENTS_DOCS if a.name == "general-purpose"), None)

        assert "通用" in agent.description or "任务" in agent.description
        assert len(agent.use_cases) > 0
```

---

## 5. E2E 测试

```python
# tests/e2e/test_docs.py

class TestDocsPageE2E:
    """文档页面 E2E 测试"""

    def test_docs_page_loads(self, page: Page):
        """测试文档页面加载"""
        page.goto("http://127.0.0.1:8000/")
        page.click("text=文档")

        expect(page.locator("h1")).to_contain_text("文档")

    def test_tools_tab(self, page: Page):
        """测试工具标签页"""
        page.goto("http://127.0.0.1:8000/claude/docs")

        page.click("text=工具")
        expect(page.locator(".tools-list")).to_be_visible()

    def test_agents_tab(self, page: Page):
        """测试代理标签页"""
        page.goto("http://127.0.0.1:8000/claude/docs")

        page.click("text=代理")
        expect(page.locator(".agents-list")).to_be_visible()

    def test_commands_tab(self, page: Page):
        """测试命令标签页"""
        page.goto("http://127.0.0.1:8000/claude/docs")

        page.click("text=命令")
        expect(page.locator(".commands-list")).to_be_visible()
```

---

## 6. 运行测试

```bash
# 运行文档相关测试
uv run pytest tests/ -k "docs" -v

# 运行文档数据测试
uv run pytest tests/test_docs.py -v
```

---

## 7. 验收标准

- [ ] 工具文档 API 返回9个工具
- [ ] 代理文档 API 返回9种代理
- [ ] 命令文档 API 返回5个命令
- [ ] 最佳实践包含三个章节
- [ ] 所有文档字段完整
- [ ] 文档内容准确
- [ ] UI 正确显示所有文档
