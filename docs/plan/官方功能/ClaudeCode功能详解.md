# Claude Code 功能详解

本文档详细记录 Claude Code（Anthropic 官方 Claude Code SDK）提供的核心功能。

## 主要章节

| 章节 | 内容 |
|------|------|
| 核心概念 | 工具调用、权限控制、流式响应、会话管理 |
| 可用工具（9个） | Read、Write、Edit、Bash、Glob、Grep、WebSearch、WebFetch、Task |
| 权限模式（4种） | default、acceptEdits、plan、bypassPermissions |
| 消息类型 | text、thinking、tool_use、tool_result、error、complete |
| 执行模式 | 同步执行 vs 流式执行 |
| 会话管理 | 继续对话、恢复会话 |
| 配置选项 | ClaudeCodeOptions、环境变量 |
| 响应数据 | 任务统计、费用计算 |
| 内置命令 | /commit、/commit-push-pr、/dedupe、/oncall-triage、/bug、/clear、/mcp、/init、/insights |
| 代理类型 | general-purpose、explore、code-explorer、code-architect 等 |
| 插件系统 | 官方插件、插件架构、MCP 服务器 |
| 最佳实践 | 工具选择、权限模式选择、错误处理 |
| 安装方式 | Mac/Linux/Windows 安装脚本 |
| 数据政策 | 数据收集、使用政策、隐私保护 |

---

## 核心概念

Claude Code 是 Anthropic 提供的 AI 编程助手 SDK，允许开发者通过 API 调用 Claude 执行编程任务。核心功能包括：

- **工具调用**：Claude 可以使用各种工具来读取、修改和执行代码
- **权限控制**：通过权限模式控制工具执行的行为
- **流式响应**：支持实时流式输出执行过程
- **会话管理**：支持继续对话和恢复历史会话

---

## 1. 可用工具（Tools）

Claude Code 内置以下核心工具：

| 工具名称 | 功能描述 | 是否修改文件 | 说明 |
|---------|---------|-------------|------|
| **Read** | 读取文件内容 | 否 | 查看文件内容，支持指定行号范围 |
| **Write** | 创建新文件 | 是 | 创建全新的文件 |
| **Edit** | 编辑现有文件 | 是 | 对现有文件进行精确修改 |
| **Bash** | 运行终端命令 | 可能 | 执行 shell 命令 |
| **Glob** | 按模式查找文件 | 否 | 使用 glob 模式搜索文件 |
| **Grep** | 搜索文件内容 | 否 | 在文件中搜索文本内容 |
| **WebSearch** | 搜索网络 | 否 | 搜索互联网获取信息 |
| **WebFetch** | 获取网页内容 | 否 | 抓取网页内容 |
| **Task** | 启动子代理任务 | 取决于子任务 | 创建子代理执行独立任务 |

### 1.1 Read 工具

读取文件内容的工具。

```python
# 调用示例
{
    "name": "Read",
    "input": {
        "file_path": "/path/to/file.py",
        "limit": 100,        # 可选，限制行数
        "offset": 0           # 可选，起始行号
    }
}
```

**参数说明**：
- `file_path`（必需）：要读取的文件路径
- `limit`（可选）：限制返回的行数
- `offset`（可选）：从指定行号开始读取

### 1.2 Write 工具

创建新文件或覆盖现有文件。

```python
{
    "name": "Write",
    "input": {
        "file_path": "/path/to/new_file.py",
        "content": "# 文件内容..."
    }
}
```

**参数说明**：
- `file_path`（必需）：目标文件路径
- `content`（必需）：文件内容

**注意**：如果文件已存在，会覆盖原文件。

### 1.3 Edit 工具

对现有文件进行精确编辑。

```python
{
    "name": "Edit",
    "input": {
        "file_path": "/path/to/file.py",
        "old_string": "旧代码块",
        "new_string": "新代码块"
    }
}
```

**参数说明**：
- `file_path`（必需）：要编辑的文件路径
- `old_string`（必需）：要替换的代码（必须精确匹配）
- `new_string`（必需）：替换后的新代码

### 1.4 Bash 工具

执行终端命令。

```python
{
    "name": "Bash",
    "input": {
        "command": "npm install",
        "description": "安装项目依赖"
    }
}
```

**参数说明**：
- `command`（必需）：要执行的命令
- `description`（可选）：命令描述

### 1.5 Glob 工具

使用 glob 模式查找文件。

```python
{
    "name": "Glob",
    "input": {
        "pattern": "**/*.py",
        "path": "/path/to/search"
    }
}
```

**参数说明**：
- `pattern`（必需）：glob 模式（如 `**/*.py`）
- `path`（可选）：搜索路径，默认为当前工作目录

### 1.6 Grep 工具

在文件中搜索文本内容。

```python
{
    "name": "Grep",
    "input": {
        "pattern": "def.*function",
        "path": "/path/to/search",
        "glob": "*.py",
        "-n": true,
        "output_mode": "content"
    }
}
```

**参数说明**：
- `pattern`（必需）：正则表达式搜索模式
- `path`（可选）：搜索路径
- `glob`（可选）：文件过滤模式
- `-n`（可选）：是否显示行号
- `output_mode`（可选）：输出模式（content/files_with_matches/count）

### 1.7 WebSearch 工具

搜索互联网获取信息。

```python
{
    "name": "WebSearch",
    "input": {
        "query": "Python async best practices 2025",
        "num_results": 5
    }
}
```

**参数说明**：
- `query`（必需）：搜索关键词
- `num_results`（可选）：返回结果数量

### 1.8 WebFetch 工具

获取网页内容。

```python
{
    "name": "WebFetch",
    "input": {
        "url": "https://example.com/docs",
        "prompt": "提取文档中的 API 接口说明"
    }
}
```

**参数说明**：
- `url`（必需）：目标 URL
- `prompt`（可选）：从页面中提取信息的提示

### 1.9 Task 工具

启动子代理任务。

```python
{
    "name": "Task",
    "input": {
        "prompt": "分析这个代码库的错误处理模式",
        "agent": "general-purpose",
        "model": "sonnet"
    }
}
```

**参数说明**：
- `prompt`（必需）：子任务描述
- `agent`（可选）：代理类型（general-purpose/explore）
- `model`（可选）：使用的模型（sonnet/haiku）

---

## 2. 权限模式（Permission Modes）

Claude Code 提供四种权限模式来控制工具执行行为：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **default** | 默认模式，每次工具调用需要用户确认 | 安全性要求高的场景 |
| **acceptEdits** | 自动接受编辑操作（Write/Edit），其他操作仍需确认 | 日常开发 |
| **plan** | 规划模式，先生成计划，用户批准后执行 | 复杂任务需要规划 |
| **bypassPermissions** | 跳过所有权限检查，完全自动化 | 无人值守自动化 |

### 2.1 default 模式

默认权限模式，每次工具调用都会请求用户确认。

```python
options = ClaudeCodeOptions(
    permission_mode="default",
    cwd="/path/to/project"
)
```

**行为**：
- 每次工具调用前暂停
- 等待用户 approve/deny
- 可设置允许的工具列表限制

### 2.2 acceptEdits 模式

自动接受文件编辑操作，其他操作仍需确认。

```python
options = ClaudeCodeOptions(
    permission_mode="acceptEdits",
    cwd="/path/to/project"
)
```

**行为**：
- Write/Edit 工具自动执行
- Bash/删除等敏感操作仍需确认
- 适合日常开发工作流

### 2.3 plan 模式

规划模式，先输出执行计划，用户批准后再执行。

```python
options = ClaudeCodeOptions(
    permission_mode="plan",
    cwd="/path/to/project"
)
```

**行为**：
- Claude 先分析任务并生成执行计划
- 显示将要执行的操作列表
- 用户批准后才开始执行
- 适合重要或不可逆的操作

### 2.4 bypassPermissions 模式

完全自动化，跳过所有权限检查。

```python
options = ClaudeCodeOptions(
    permission_mode="bypassPermissions",
    cwd="/path/to/project"
)
```

**行为**：
- 所有工具调用自动执行
- 无需任何用户交互
- 适合 CI/CD、无人值守任务
- **注意**：存在风险，请确保输入可信

---

## 3. 消息类型

Claude Code 通过流式响应返回多种消息类型：

| 消息类型 | 说明 | 包含内容 |
|---------|------|---------|
| **text** | 文本响应 | Claude 的文本输出 |
| **thinking** | 思考过程 | 内部推理过程（可选） |
| **tool_use** | 工具调用 | 工具名称和参数 |
| **tool_result** | 工具结果 | 工具执行结果 |
| **error** | 错误信息 | 错误描述 |
| **complete** | 任务完成 | 最终结果和统计信息 |

### 3.1 消息结构

```python
@dataclass
class StreamMessage:
    type: MessageType           # 消息类型
    content: str                # 消息内容
    timestamp: str              # 时间戳
    tool_name: str | None       # 工具名称（tool_use 时）
    tool_input: dict | None     # 工具输入参数
    metadata: dict              # 附加元数据
```

### 3.2 完整响应示例

```json
{
    "type": "complete",
    "content": "任务完成",
    "metadata": {
        "session_id": "session_abc123",
        "cost_usd": 0.0525,
        "duration_ms": 3500,
        "is_error": false
    }
}
```

---

## 4. 执行模式

### 4.1 同步执行

等待任务完成后返回完整结果。

```python
client = ClaudeCodeClient(working_dir="/path/to/project")
result = await client.run("分析这个项目的结构")

# result 类型
@dataclass
class TaskResult:
    success: bool                # 是否成功
    message: str                 # 响应消息
    session_id: str | None       # 会话 ID
    cost_usd: float              # 费用（美元）
    duration_ms: int             # 耗时（毫秒）
    files_changed: list[str]     # 变更的文件列表
    tools_used: list[str]        # 使用的工具列表
```

### 4.2 流式执行

实时获取执行过程中的消息。

```python
client = ClaudeCodeClient(working_dir="/path/to/project")

async for msg in client.run_stream("阅读 main.py"):
    if msg.type == MessageType.TEXT:
        print(f"文本: {msg.content}")
    elif msg.type == MessageType.TOOL_USE:
        print(f"调用工具: {msg.tool_name}")
    elif msg.type == MessageType.COMPLETE:
        print(f"完成 - 费用: ${msg.metadata['cost_usd']}")
```

---

## 5. 会话管理

### 5.1 继续对话

在同一会话中继续对话。

```python
client = ClaudeCodeClient(
    working_dir="/path/to/project",
    continue_conversation=True
)

# 第一轮
result1 = await client.run("阅读 auth.py")

# 第二轮 - 继续同一会话
result2 = await client.run("现在添加登录功能")
```

### 5.2 恢复会话

通过会话 ID 恢复历史会话。

```python
client = ClaudeCodeClient(
    working_dir="/path/to/project",
    resume="session_abc123"  # 之前返回的 session_id
)

result = await client.run("继续之前的任务")
```

---

## 6. 配置选项

### 6.1 ClaudeCodeOptions

```python
@dataclass
class ClaudeCodeOptions:
    permission_mode: str         # 权限模式
    cwd: str                    # 工作目录
    continue_conversation: bool # 继续对话
    resume: str | None          # 恢复的会话 ID
    allowed_tools: list[str] | None  # 允许的工具列表
    max_tokens: int | None      # 最大输出 token
    model: str | None           # 使用的模型
```

### 6.2 环境变量

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | 是 |
| `WORKING_DIR` | 工作目录 | 是 |
| `CLAUDECODE` | 嵌套调用标识 | 自动设置 |

---

## 7. 响应数据

### 7.1 任务统计信息

每次任务完成后返回详细统计：

```json
{
    "success": true,
    "message": "任务完成响应",
    "session_id": "session_abc123",
    "cost_usd": 0.0525,
    "duration_ms": 3500,
    "files_changed": [
        "/path/to/file1.py",
        "/path/to/file2.py"
    ],
    "tools_used": [
        "Read",
        "Grep",
        "Edit"
    ]
}
```

### 7.2 费用计算

费用基于输入和输出的 token 数量计算：

```
总费用 = (输入 token 数 × 输入单价 + 输出 token 数 × 输出单价) / 1,000,000
```

---

## 8. 最佳实践

### 8.1 工具选择

根据任务需求选择合适的工具：

- **只读任务**：使用 Read、Glob、Grep
- **需要修改**：添加 Write、Edit
- **需要执行**：添加 Bash
- **需要搜索**：添加 WebSearch、WebFetch

### 8.2 权限模式选择

| 场景 | 推荐模式 |
|------|---------|
| 交互式开发 | `acceptEdits` |
| 审查/分析任务 | `default` |
| 复杂重构 | `plan` |
| CI/CD 自动化 | `bypassPermissions` |

### 8.3 错误处理

```python
try:
    async for msg in client.run_stream(prompt):
        if msg.type == MessageType.ERROR:
            logger.error(f"执行错误: {msg.content}")
        elif msg.type == MessageType.COMPLETE:
            if msg.metadata.get("is_error"):
                logger.warning("任务执行失败")
except Exception as e:
    logger.exception("Unexpected error")
```

---

## 9. 内置命令（Slash Commands）

Claude Code 提供内置的斜杠命令，方便用户快速执行常用操作。

### 9.1 CLI 启动命令（终端执行）

| 命令 | 说明 |
|------|------|
| `claude` | 启动交互式会话 |
| `claude "问题"` | 带初始问题直接启动 |
| `claude -c` | 继续上次对话 |
| `claude --version` | 查看版本号 |
| `claude update` | 更新客户端 |
| `claude doctor` | 诊断安装环境/检查依赖 |
| `claude mcp` | 启动 MCP 向导 |
| `claude login` | 登录 Anthropic 账户 |
| `claude logout` | 登出账户 |

### 9.2 斜杠命令（交互会话中使用）

| 命令 | 说明 |
|------|------|
| `/help` | 查看帮助列表 |
| `/config` | 配置设置（语言、模型、主题等） |
| `/model` | 切换 AI 模型 |
| `/memory` | 管理全局记忆（CLAUDE.md） |
| `/init` | 初始化项目，生成 CLAUDE.md |
| `/clear` | 清除当前对话上下文（别名：`/reset`, `/new`） |
| `/compact` | 压缩会话内容，节省 tokens |
| `/exit` | 退出 Claude Code |
| `/bug` | 向 Anthropic 报告 Bug |
| `/doctor` | 诊断问题 |
| `/usage` | 查看用量统计 |
| `/stats` | 查看统计信息 |
| `/permissions` | 管理权限设置 |
| `/terminal-setup` | 终端设置优化 |
| `/add-dir` | 添加额外工作目录 |
| `/context` | 查看上下文信息 |
| `/cost` | 查看成本/Token 消耗 |
| `/agents` | 管理 Agent 任务 |
| `/bashes` | 管理 Bash 任务 |
| `/todos` | 管理待办事项 |
| `/resume` | 恢复之前的会话 |
| `/rewind` | 回退到之前的 checkpoint（别名：`/checkpoint`） |
| `/export` | 导出会话内容 |

### 9.3 符号命令

| 符号 | 说明 |
|------|------|
| `!` | Bash 模式（执行 shell 命令） |
| `/` | 命令模式（调用斜杠命令） |
| `@` | 引用文件路径 |
| `&` | 后台运行 |

### 9.4 常用快捷键

| 快捷键 | 说明 |
|--------|------|
| `Ctrl+C` | 中断当前操作 |
| `Ctrl+D` | 退出会话 |
| `Ctrl+L` | 清屏 |
| `Ctrl+R` | 搜索历史命令 |
| `Tab` | 自动补全 |
| `↑/↓` | 浏览历史命令 |
| `Esc` | 取消当前输入 |
| `Ctrl+Z` | 挂起会话 |

### 9.5 项目文件

| 文件 | 说明 |
|------|------|
| `CLAUDE.md` | 项目记忆文件，存储项目上下文、约定和常用命令 |
| `.claude/settings.json` | 用户配置文件 |

### 9.6 使用小贴士

1. **首次使用**：运行 `claude doctor` 检查环境，然后 `claude init` 初始化项目
2. **节省 Token**：定期使用 `/compact` 压缩上下文
3. **多目录支持**：用 `/add-dir` 添加多个工作目录
4. **会话恢复**：用 `/resume` 或 `claude -c` 继续之前的工作
5. **权限管理**：通过 `/permissions` 控制 Claude 的操作权限

---

## 10. 代理类型（Agents）

Claude Code 内置多种专业代理，可通过 Task 工具调用：

| 代理类型 | 用途 | 说明 |
|----------|------|------|
| **general-purpose** | 通用任务 | 处理各种编程任务 |
| **explore** | 代码库探索 | 快速了解代码库结构 |
| **code-explorer** | 代码分析 | 深入分析代码逻辑 |
| **code-architect** | 架构设计 | 设计系统架构方案 |
| **code-reviewer** | 代码审查 | 审查代码质量和安全 |
| **agent-creator** | 插件创建 | 辅助开发 Claude Code 插件 |
| **plugin-validator** | 插件验证 | 验证插件结构 |
| **skill-reviewer** | 技能审查 | 审查技能定义 |
| **conversation-analyzer** | 对话分析 | 分析对话模式 |

### 10.1 调用代理

```python
{
    "name": "Task",
    "input": {
        "prompt": "分析这个项目的错误处理模式",
        "agent": "code-explorer",
        "model": "sonnet"
    }
}
```

---

## 11. 插件系统（Plugins）

Claude Code 支持插件扩展，可以添加自定义命令、代理、技能和钩子。

### 11.1 官方插件

Claude Code 仓库内置以下官方插件：

| 插件名称 | 功能描述 |
|----------|---------|
| **agent-sdk-dev** | Agent SDK 开发套件，包含 `/new-sdk-app` 命令和 SDK 验证代理 |
| **code-review** | 自动代码审查，使用 5 个并行 Sonnet 代理进行多维度审查 |
| **commit-commands** | Git 工作流自动化：`/commit`、`/commit-push-pr`、`/clean_gone` |
| **feature-dev** | 功能开发工作流，7 阶段结构化开发流程 |
| **frontend-design** | 前端设计指南，提供生产级界面设计建议 |
| **hookify** | 创建自定义钩子，防止不良行为 |
| **plugin-dev** | 插件开发工具包，8 阶段插件创建工作流 |
| **pr-review-toolkit** | PR 审查工具集，专注于注释、测试、错误处理等 |
| **ralph-wiggum** | 交互式自引用 AI 循环，持续迭代直到完成 |
| **security-guidance** | 安全提醒钩子，监控 9 种安全模式 |
| **learning-output-style** | 交互式学习模式，在决策点请求代码贡献 |

### 11.2 插件结构

每个插件遵循标准结构：

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json          # 插件元数据
├── commands/               # 斜杠命令（可选）
├── agents/                 # 专业代理（可选）
├── skills/                # 技能定义（可选）
├── hooks/                 # 事件钩子（可选）
├── .mcp.json              # MCP 服务器配置（可选）
└── README.md              # 插件文档
```

### 11.3 插件类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **commands** | 斜杠命令 | `/commit`, `/code-review` |
| **agents** | 专业代理 | 代码审查代理、安全代理 |
| **skills** | 技能定义 | 前端设计技能、插件开发技能 |
| **hooks** | 事件钩子 | PreToolUse、SessionStart、Stop |
| **MCP** | 外部工具 | 数据库连接、API 集成 |

### 11.4 钩子类型

Claude Code 支持以下钩子：

| 钩子名称 | 触发时机 |
|----------|---------|
| **PreToolUse** | 工具执行前 |
| **PostToolUse** | 工具执行后 |
| **Stop** | 会话结束时 |
| **SessionStart** | 会话开始时 |
| **Notification** | 通知事件 |

---

## 12. 安装方式

### 12.1 Mac/Linux

```bash
# 官方安装脚本（推荐）
curl -fsSL https://claude.ai/install.sh | bash

# Homebrew
brew install --cask claude-code
```

### 12.2 Windows

```powershell
# PowerShell（推荐）
irm https://claude.ai/install.ps1 | iex

# WinGet
winget install Anthropic.ClaudeCode
```

### 12.3 npm（已废弃）

```bash
# 不推荐，已废弃
npm install -g @anthropic-ai/claude-code
```

### 12.4 安装后使用

```bash
# 进入项目目录
cd your-project

# 启动 Claude Code
claude

# 或在 IDE 中使用
# VSCode: 安装 Claude Code 扩展
```

---

## 13. 数据收集和使用政策

Claude Code 会收集以下数据：

### 13.1 收集的数据类型

- **使用数据**：代码接受或拒绝情况
- **对话数据**：相关会话信息
- **用户反馈**：通过 `/bug` 命令提交的内容

### 13.2 数据使用政策

- 用于改进 Claude Code 产品
- **不会**将用户反馈用于模型训练
- 限制敏感信息保留期限
- 限制用户会话数据访问权限

### 13.3 隐私保护

- 实施数据保留限制
- 限制敏感信息访问
- 明确政策：不用于模型训练

详细政策请参考：
- [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms)
- [Privacy Policy](https://www.anthropic.com/legal/privacy)
- [Data Usage Policies](https://code.claude.com/docs/en/data-usage)

---

## 14. 相关文档

- [官方文档](https://code.claude.com/docs/en/overview)
- [官方 GitHub 仓库](https://github.com/anthropics/claude-code)
- [插件系统文档](https://docs.claude.com/en/docs/claude-code/plugins)
- [Agent SDK 文档](https://docs.claude.com/en/api/agent-sdk/overview)
- [API 接口文档](../API接口.md)
- [技术架构文档](../技术架构.md)
