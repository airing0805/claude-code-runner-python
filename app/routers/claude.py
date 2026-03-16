"""Claude Code 环境信息 API"""

import os
import platform
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter

from app.claude.hooks_manager import get_hook_manager
from app.claude.plugins_manager import get_plugin_manager
from app.claude.schemas import (
    AgentDoc,
    AgentsDoc,
    BestPracticesDoc,
    CommandDoc,
    CommandOption,
    CommandsDoc,
    ConfigInfo,
    EnvInfo,
    ErrorHandling,
    Hook,
    HooksDoc,
    HookTypesDoc,
    Parameter,
    PermissionMode,
    PermissionModeGuide,
    PermissionModesInfo,
    Plugin,
    PluginsDoc,
    StatsInfo,
    TaskStats,
    ToolDoc,
    ToolExample,
    ToolInfo,
    ToolsDoc,
    ToolsInfo,
    VersionInfo,
)

router = APIRouter(prefix="/api/claude", tags=["claude"])

# 敏感环境变量关键词
SENSITIVE_KEYS = {
    "ANTHROPIC_API_KEY",
    "API_KEY",
    "TOKEN",
    "PASSWORD",
    "SECRET",
    "PRIVATE_KEY",
}

# Claude Code 相关环境变量
CLAUDE_RELATED_VARS = {
    "ANTHROPIC_API_KEY",
    "CLAUDECODE",
    "WORKING_DIR",
    "HOST",
    "PORT",
    "CLAUDE_API_KEY",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_BASE_URL",
}


def mask_sensitive_value(key: str, value: str) -> str:
    """隐藏敏感信息"""
    key_upper = key.upper()
    for sensitive in SENSITIVE_KEYS:
        if sensitive in key_upper:
            return "***"
    return value


# ==================== v0.3.1 基础 API ====================


@router.get("/version", response_model=VersionInfo)
async def get_version():
    """获取 Claude 版本信息"""
    return VersionInfo(
        cli_version="1.0.0",  # TODO: 从 Claude CLI 获取实际版本
        sdk_version="0.0.25",
        runtime={
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": sys.version,
        },
    )


@router.get("/env", response_model=EnvInfo)
async def get_env():
    """获取环境变量（敏感信息隐藏）"""
    variables: dict[str, str] = {}

    # 只返回与 Claude Code 相关的变量
    for key, value in os.environ.items():
        # 检查是否是 Claude 相关变量或不在排除列表中
        if key in CLAUDE_RELATED_VARS or any(
            suffix in key.upper() for suffix in ["CLAUDE", "ANTHROPIC"]
        ):
            variables[key] = mask_sensitive_value(key, value)

    return EnvInfo(variables=variables)


@router.get("/config", response_model=ConfigInfo)
async def get_config():
    """获取 Claude 配置信息"""
    # 从环境变量获取配置
    working_dir = os.getenv("WORKING_DIR", ".")
    permission_mode = os.getenv("CLAUDE_PERMISSION_MODE", "default")

    # 默认工具列表
    allowed_tools = [
        "Read",
        "Write",
        "Edit",
        "Bash",
        "Glob",
        "Grep",
        "WebSearch",
        "WebFetch",
        "Task",
    ]

    return ConfigInfo(
        working_dir=working_dir,
        default_permission_mode=permission_mode,
        allowed_tools=allowed_tools,
    )


# ==================== v0.3.2 工具统计展示 ====================

# 核心工具列表
CORE_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "WebSearch",
    "WebFetch",
    "Task",
]

# 全局统计存储
_stats = {
    "tools_usage": defaultdict(int, {tool: 0 for tool in CORE_TOOLS}),
    "files_changed": 0,
    "task_stats": {
        "total": 0,
        "success": 0,
        "failed": 0,
        "total_duration_ms": 0,
        "total_cost_usd": 0.0,
    },
}


def record_tool_use(tool_name: str):
    """记录工具使用"""
    _stats["tools_usage"][tool_name] += 1


def record_task_result(success: bool, duration_ms: int, cost_usd: float):
    """记录任务结果"""
    stats = _stats["task_stats"]
    stats["total"] += 1
    if success:
        stats["success"] += 1
    else:
        stats["failed"] += 1
    stats["total_duration_ms"] += duration_ms
    stats["total_cost_usd"] += cost_usd


def record_file_change():
    """记录文件变更"""
    _stats["files_changed"] += 1


@router.get("/stats", response_model=StatsInfo)
async def get_stats():
    """获取工具使用统计"""
    task_stats = _stats["task_stats"]
    total = task_stats["total"]
    avg_duration = (
        task_stats["total_duration_ms"] // total if total > 0 else 0
    )

    return StatsInfo(
        tools_usage=dict(_stats["tools_usage"]),
        files_changed=_stats["files_changed"],
        task_stats=TaskStats(
            total=task_stats["total"],
            success=task_stats["success"],
            failed=task_stats["failed"],
            avg_duration_ms=avg_duration,
            total_cost_usd=round(task_stats["total_cost_usd"], 4),
        ),
    )


@router.get("/permission-modes", response_model=PermissionModesInfo)
async def get_permission_modes():
    """获取权限模式说明"""
    modes = [
        PermissionMode(
            name="default",
            description="默认模式，每次工具调用需要用户确认",
            scenarios=["安全性要求高的场景", "需要人工审核的操作"],
        ),
        PermissionMode(
            name="acceptEdits",
            description="自动接受编辑操作（Write/Edit），其他操作仍需确认",
            scenarios=["日常开发", "批量修改文件"],
        ),
        PermissionMode(
            name="plan",
            description="规划模式，先生成计划，用户批准后执行",
            scenarios=["复杂任务", "需要规划的操作", "重要或不可逆的操作"],
        ),
        PermissionMode(
            name="bypassPermissions",
            description="跳过所有权限检查，完全自动化",
            scenarios=["CI/CD自动化", "无人值守任务"],
        ),
    ]
    return PermissionModesInfo(modes=modes)


# ==================== v0.3.3 文档展示 ====================


@router.get("/docs/tools", response_model=ToolsDoc)
async def get_tools_docs():
    """获取工具详细说明"""
    tools = [
        ToolDoc(
            name="Read",
            description="读取文件内容",
            category="文件操作",
            modifies_files=False,
            parameters=[
                Parameter(name="file_path", type="string", required=True, description="要读取的文件路径"),
                Parameter(name="limit", type="integer", required=False, description="限制返回的行数"),
                Parameter(name="offset", type="integer", required=False, description="从指定行号开始读取"),
            ],
            example=ToolExample(input={"file_path": "/path/to/file.py"}, description="读取整个文件"),
        ),
        ToolDoc(
            name="Write",
            description="创建新文件或覆盖现有文件",
            category="文件操作",
            modifies_files=True,
            parameters=[
                Parameter(name="file_path", type="string", required=True, description="要写入的文件路径"),
                Parameter(name="content", type="string", required=True, description="文件内容"),
            ],
            example=ToolExample(input={"file_path": "/path/to/file.py", "content": "Hello World"}, description="创建新文件"),
        ),
        ToolDoc(
            name="Edit",
            description="编辑现有文件的部分内容",
            category="文件操作",
            modifies_files=True,
            parameters=[
                Parameter(name="file_path", type="string", required=True, description="要编辑的文件路径"),
                Parameter(name="old_string", type="string", required=True, description="要替换的原始文本"),
                Parameter(name="new_string", type="string", required=True, description="替换后的文本"),
            ],
            example=ToolExample(
                input={"file_path": "/path/to/file.py", "old_string": "old text", "new_string": "new text"},
                description="替换文件中的文本",
            ),
        ),
        ToolDoc(
            name="Bash",
            description="执行终端命令",
            category="系统操作",
            modifies_files=False,
            parameters=[
                Parameter(name="command", type="string", required=True, description="要执行的命令"),
                Parameter(name="description", type="string", required=False, description="命令说明"),
            ],
            example=ToolExample(input={"command": "ls -la", "description": "列出目录内容"}, description="列出当前目录文件"),
        ),
        ToolDoc(
            name="Glob",
            description="按模式查找文件",
            category="文件操作",
            modifies_files=False,
            parameters=[
                Parameter(name="pattern", type="string", required=True, description="文件匹配模式"),
            ],
            example=ToolExample(input={"pattern": "**/*.py"}, description="查找所有 Python 文件"),
        ),
        ToolDoc(
            name="Grep",
            description="搜索文件内容",
            category="搜索",
            modifies_files=False,
            parameters=[
                Parameter(name="pattern", type="string", required=True, description="搜索模式"),
                Parameter(name="path", type="string", required=False, description="搜索路径"),
            ],
            example=ToolExample(input={"pattern": "def main", "path": "*.py"}, description="搜索函数定义"),
        ),
        ToolDoc(
            name="WebSearch",
            description="搜索网络",
            category="网络",
            modifies_files=False,
            parameters=[
                Parameter(name="query", type="string", required=True, description="搜索查询"),
            ],
            example=ToolExample(input={"query": "Python asyncio tutorial"}, description="搜索 Python 教程"),
        ),
        ToolDoc(
            name="WebFetch",
            description="获取网页内容",
            category="网络",
            modifies_files=False,
            parameters=[
                Parameter(name="url", type="string", required=True, description="网页 URL"),
            ],
            example=ToolExample(input={"url": "https://example.com"}, description="获取网页内容"),
        ),
        ToolDoc(
            name="Task",
            description="启动子代理任务",
            category="代理",
            modifies_files=False,
            parameters=[
                Parameter(name="prompt", type="string", required=True, description="代理任务描述"),
                Parameter(name="agent", type="string", required=False, description="代理类型"),
            ],
            example=ToolExample(
                input={"prompt": "分析这个代码库的结构", "agent": "explore"},
                description="启动探索代理分析代码库",
            ),
        ),
    ]
    return ToolsDoc(tools=tools)


@router.get("/docs/agents", response_model=AgentsDoc)
async def get_agents_docs():
    """获取代理类型说明"""
    agents = [
        AgentDoc(
            name="general-purpose",
            description="通用任务代理，处理各种编程任务",
            use_cases=["处理各种编程任务", "回答问题", "代码生成"],
        ),
        AgentDoc(
            name="explore",
            description="代码库探索代理，快速了解代码结构",
            use_cases=["快速了解代码库结构", "查找文件", "定位功能"],
        ),
        AgentDoc(
            name="code-explorer",
            description="代码探索代理，深入分析代码",
            use_cases=["分析代码逻辑", "查找调用链", "理解依赖关系"],
        ),
        AgentDoc(
            name="code-architect",
            description="代码架构代理，设计系统架构",
            use_cases=["系统设计", "架构评审", "技术选型"],
        ),
        AgentDoc(
            name="code-reviewer",
            description="代码审查代理，审查代码质量",
            use_cases=["代码审查", "发现潜在问题", "提出改进建议"],
        ),
        AgentDoc(
            name="agent-creator",
            description="代理创建代理，生成新代理",
            use_cases=["创建自定义代理", "扩展代理功能"],
        ),
        AgentDoc(
            name="plugin-validator",
            description="插件验证代理，验证插件质量",
            use_cases=["插件验证", "安全检查", "兼容性测试"],
        ),
        AgentDoc(
            name="skill-reviewer",
            description="技能审查代理，审查技能定义",
            use_cases=["技能审查", "模式提取", "技能优化"],
        ),
        AgentDoc(
            name="conversation-analyzer",
            description="对话分析代理，分析会话模式",
            use_cases=["会话分析", "模式识别", "优化建议"],
        ),
    ]
    return AgentsDoc(agents=agents)


@router.get("/docs/commands", response_model=CommandsDoc)
async def get_commands_docs():
    """获取内置命令说明"""
    commands = [
        # CLI 启动命令 (9个)
        CommandDoc(
            name="claude",
            description="启动 Claude Code CLI，进入交互式对话模式",
            usage="claude",
            options=[],
            category="cli",
        ),
        CommandDoc(
            name='claude "问题"',
            description="直接执行单次任务，完成后自动退出",
            usage='claude "分析这个项目的结构"',
            options=[],
            category="cli",
        ),
        CommandDoc(
            name="claude -c",
            description="在指定目录中启动 Claude Code",
            usage="claude -c /path/to/project",
            options=[CommandOption(name="-c", description="指定工作目录")],
            category="cli",
        ),
        CommandDoc(
            name="claude --version",
            description="显示 Claude Code CLI 版本信息",
            usage="claude --version",
            options=[CommandOption(name="--version", description="显示版本号")],
            category="cli",
        ),
        CommandDoc(
            name="claude update",
            description="更新 Claude Code CLI 到最新版本",
            usage="claude update",
            options=[],
            category="cli",
        ),
        CommandDoc(
            name="claude doctor",
            description="诊断 Claude Code 配置问题并提供修复建议",
            usage="claude doctor",
            options=[],
            category="cli",
        ),
        CommandDoc(
            name="claude mcp",
            description="管理 MCP (Model Context Protocol) 服务器连接",
            usage="claude mcp [list|add|remove]",
            options=[
                CommandOption(name="list", description="列出已连接的 MCP 服务器"),
                CommandOption(name="add", description="添加新的 MCP 服务器"),
                CommandOption(name="remove", description="移除 MCP 服务器"),
            ],
            category="cli",
        ),
        CommandDoc(
            name="claude login",
            description="登录 Claude Code 账户",
            usage="claude login",
            options=[],
            category="cli",
        ),
        CommandDoc(
            name="claude logout",
            description="退出当前登录的账户",
            usage="claude logout",
            options=[],
            category="cli",
        ),
        # 斜杠命令 (24个)
        CommandDoc(
            name="/help",
            description="显示所有可用命令的帮助信息",
            usage="/help [command]",
            options=[CommandOption(name="command", description="可选，指定命令名称")],
            category="slash",
        ),
        CommandDoc(
            name="/config",
            description="查看或修改 Claude Code 配置",
            usage="/config [key] [value]",
            options=[
                CommandOption(name="key", description="配置项名称"),
                CommandOption(name="value", description="配置值"),
            ],
            category="slash",
        ),
        CommandDoc(
            name="/model",
            description="切换使用的 AI 模型",
            usage="/model [model-name]",
            options=[CommandOption(name="model-name", description="模型名称，如 sonnet-4-5")],
            category="slash",
        ),
        CommandDoc(
            name="/memory",
            description="管理 Claude Code 记忆功能",
            usage="/memory [add|list|clear] [content]",
            options=[
                CommandOption(name="add", description="添加记忆"),
                CommandOption(name="list", description="列出所有记忆"),
                CommandOption(name="clear", description="清除所有记忆"),
            ],
            category="slash",
        ),
        CommandDoc(
            name="/init",
            description="初始化新项目或功能模块",
            usage="/init <project-name>",
            options=[CommandOption(name="project-name", description="项目或功能名称")],
            category="slash",
        ),
        CommandDoc(
            name="/clear",
            description="清除当前会话内容，重新开始对话",
            usage="/clear",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/compact",
            description="手动压缩会话上下文以节省 tokens",
            usage="/compact",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/exit",
            description="退出当前 Claude Code 会话",
            usage="/exit",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/bug",
            description="启动 Bug 调查代理，帮你定位和修复问题",
            usage="/bug <description>",
            options=[CommandOption(name="description", description="Bug 描述")],
            category="slash",
        ),
        CommandDoc(
            name="/doctor",
            description="诊断当前会话问题并提供修复建议",
            usage="/doctor",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/usage",
            description="查看当前会话的 token 使用量",
            usage="/usage",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/stats",
            description="查看会话统计信息，如工具使用次数等",
            usage="/stats",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/permissions",
            description="查看或修改当前权限模式",
            usage="/permissions [mode]",
            options=[CommandOption(name="mode", description="权限模式：default/acceptEdits/plan/bypassPermissions")],
            category="slash",
        ),
        CommandDoc(
            name="/terminal-setup",
            description="指导设置终端环境以获得最佳体验",
            usage="/terminal-setup",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/add-dir",
            description="添加额外的工作目录到上下文",
            usage="/add-dir <path>",
            options=[CommandOption(name="path", description="目录路径")],
            category="slash",
        ),
        CommandDoc(
            name="/context",
            description="查看当前会话的上下文信息",
            usage="/context",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/cost",
            description="查看当前会话的费用消耗",
            usage="/cost",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/agents",
            description="查看运行中的子代理列表",
            usage="/agents",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/bashes",
            description="查看活跃的 Bash 会话",
            usage="/bashes",
            options=[],
            category="slash",
        ),
        CommandDoc(
            name="/todos",
            description="查看和管理当前会话的待办事项",
            usage="/todos [add|done|clear] [text]",
            options=[
                CommandOption(name="add", description="添加待办"),
                CommandOption(name="done", description="标记完成"),
                CommandOption(name="clear", description="清除所有"),
            ],
            category="slash",
        ),
        CommandDoc(
            name="/resume",
            description="恢复之前暂停的会话",
            usage="/resume <session-id>",
            options=[CommandOption(name="session-id", description="会话 ID")],
            category="slash",
        ),
        CommandDoc(
            name="/rewind",
            description="将会话倒回到指定时间点",
            usage="/rewind <steps|time>",
            options=[
                CommandOption(name="steps", description="回退的步骤数"),
                CommandOption(name="time", description="回退到的时间点"),
            ],
            category="slash",
        ),
        CommandDoc(
            name="/export",
            description="导出会话记录到文件",
            usage="/export [format]",
            options=[CommandOption(name="format", description="导出格式：markdown/json")],
            category="slash",
        ),
        # 符号命令 (4个)
        CommandDoc(
            name="!",
            description="执行 Shell 命令的快捷方式",
            usage="!<command>",
            options=[CommandOption(name="command", description="要执行的命令")],
            category="symbol",
        ),
        CommandDoc(
            name="/",
            description="快速搜索之前使用过的斜杠命令",
            usage="/<keyword>",
            options=[CommandOption(name="keyword", description="搜索关键词")],
            category="symbol",
        ),
        CommandDoc(
            name="@",
            description="引用项目中的特定文件或代码片段",
            usage="@<filename>",
            options=[CommandOption(name="filename", description="文件名或路径")],
            category="symbol",
        ),
        CommandDoc(
            name="&",
            description="并行执行多个命令（实验性功能）",
            usage="&<command1> &<command2>",
            options=[CommandOption(name="command", description="要并行执行的命令")],
            category="symbol",
        ),
        # 快捷键 (8个)
        CommandDoc(
            name="Ctrl+C",
            description="中断当前正在执行的操作",
            usage="Ctrl+C",
            options=[],
            category="shortcut",
        ),
        CommandDoc(
            name="Ctrl+D",
            description="退出当前会话（等同于 /exit）",
            usage="Ctrl+D",
            options=[],
            category="shortcut",
        ),
        CommandDoc(
            name="Ctrl+L",
            description="清除当前终端屏幕（等同于 /clear）",
            usage="Ctrl+L",
            options=[],
            category="shortcut",
        ),
        CommandDoc(
            name="Ctrl+R",
            description="搜索命令历史",
            usage="Ctrl+R",
            options=[],
            category="shortcut",
        ),
        CommandDoc(
            name="Tab",
            description="自动补全命令或文件名",
            usage="Tab",
            options=[],
            category="shortcut",
        ),
        CommandDoc(
            name="↑/↓",
            description="浏览命令历史记录",
            usage="↑ 或 ↓",
            options=[],
            category="shortcut",
        ),
        CommandDoc(
            name="Esc",
            description="取消当前选择或关闭弹窗",
            usage="Esc",
            options=[],
            category="shortcut",
        ),
        CommandDoc(
            name="Ctrl+Z",
            description="撤销上一次的输入",
            usage="Ctrl+Z",
            options=[],
            category="shortcut",
        ),
        # 项目文件 (2个)
        CommandDoc(
            name="CLAUDE.md",
            description="项目根目录的配置文件，用于定义项目特定规则和行为",
            usage="CLAUDE.md",
            options=[],
            category="file",
        ),
        CommandDoc(
            name=".claude/settings.json",
            description="用户级别的配置文件，定义全局设置和偏好",
            usage=".claude/settings.json",
            options=[],
            category="file",
        ),
    ]
    return CommandsDoc(commands=commands)


@router.get("/docs/best-practices", response_model=BestPracticesDoc)
async def get_best_practices():
    """获取最佳实践指南"""
    return BestPracticesDoc(
        tool_selection={
            "read_only": ["Read", "Glob", "Grep", "WebSearch", "WebFetch"],
            "modify_files": ["Write", "Edit"],
            "execute": ["Bash"],
            "search": ["WebSearch", "WebFetch"],
        },
        permission_mode_guide=[
            PermissionModeGuide(mode="default", scenario="交互式开发"),
            PermissionModeGuide(mode="acceptEdits", scenario="审查/分析任务"),
            PermissionModeGuide(mode="plan", scenario="复杂重构"),
            PermissionModeGuide(mode="bypassPermissions", scenario="CI/CD自动化"),
        ],
        error_handling=ErrorHandling(
            try_catch="使用 try-except 捕获异常",
            logging="记录详细错误信息",
            user_message="返回用户友好的错误消息",
        ),
    )


# ==================== v0.3.7 插件管理 ====================


@router.get("/plugins", response_model=PluginsDoc)
async def get_plugins():
    """获取插件列表"""
    manager = get_plugin_manager()
    plugins = manager.get_plugins()
    return PluginsDoc(plugins=plugins, total=len(plugins))


@router.get("/plugins/{plugin_id}", response_model=Plugin)
async def get_plugin(plugin_id: str):
    """获取插件详情"""
    manager = get_plugin_manager()
    plugin = manager.get_plugin(plugin_id)
    if not plugin:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="插件不存在")
    return plugin


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str):
    """启用插件"""
    manager = get_plugin_manager()
    success = manager.enable_plugin(plugin_id)
    if not success:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="插件不存在")
    return {"success": True, "message": f"插件 {plugin_id} 已启用"}


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str):
    """禁用插件"""
    manager = get_plugin_manager()
    success = manager.disable_plugin(plugin_id)
    if not success:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="插件不存在")
    return {"success": True, "message": f"插件 {plugin_id} 已禁用"}


# ==================== v0.3.8 钩子配置 ====================


@router.get("/hooks", response_model=HooksDoc)
async def get_hooks():
    """获取钩子配置"""
    manager = get_hook_manager()
    hooks = manager.get_hooks()
    return HooksDoc(hooks=hooks, total=len(hooks))


@router.get("/hooks/types", response_model=HookTypesDoc)
async def get_hook_types():
    """获取钩子类型说明"""
    manager = get_hook_manager()
    hook_types = manager.get_hook_types()
    return HookTypesDoc(hook_types=hook_types)


@router.put("/hooks")
async def update_hooks(hooks: list[Hook]):
    """更新钩子配置"""
    manager = get_hook_manager()
    success = manager.save_hooks(hooks)
    if not success:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="保存钩子配置失败")
    return {"success": True, "message": "钩子配置已保存"}
