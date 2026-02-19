"""Claude 相关数据模型"""

from typing import Any

from pydantic import BaseModel


class RuntimeInfo(BaseModel):
    """运行时信息"""
    os: str
    os_version: str
    python_version: str


class VersionInfo(BaseModel):
    """版本信息"""
    cli_version: str
    sdk_version: str
    runtime: RuntimeInfo


class EnvInfo(BaseModel):
    """环境变量信息"""
    variables: dict[str, str]


class ConfigInfo(BaseModel):
    """配置信息"""
    working_dir: str
    default_permission_mode: str
    allowed_tools: list[str]


# ==================== v0.3.2 工具统计展示 ====================


class TaskStats(BaseModel):
    """任务统计"""
    total: int = 0
    success: int = 0
    failed: int = 0
    avg_duration_ms: int = 0
    total_cost_usd: float = 0.0


class StatsInfo(BaseModel):
    """工具使用统计"""
    tools_usage: dict[str, int] = {}
    files_changed: int = 0
    task_stats: TaskStats = TaskStats()


class PermissionMode(BaseModel):
    """权限模式"""
    name: str
    description: str
    scenarios: list[str]


class PermissionModesInfo(BaseModel):
    """权限模式信息"""
    modes: list[PermissionMode]


class ToolInfo(BaseModel):
    """工具信息"""
    name: str
    description: str
    category: str = "文件操作"
    modifies_files: bool = False


class ToolsInfo(BaseModel):
    """工具列表信息"""
    tools: list[ToolInfo]


# ==================== v0.3.3 文档展示 ====================


class Parameter(BaseModel):
    """工具参数"""
    name: str
    type: str
    required: bool
    description: str


class ToolExample(BaseModel):
    """工具示例"""
    input: dict[str, Any]
    description: str


class ToolDoc(BaseModel):
    """工具文档"""
    name: str
    description: str
    category: str
    modifies_files: bool
    parameters: list[Parameter]
    example: ToolExample


class ToolsDoc(BaseModel):
    """工具文档列表"""
    tools: list[ToolDoc]


class AgentDoc(BaseModel):
    """代理文档"""
    name: str
    description: str
    use_cases: list[str]


class AgentsDoc(BaseModel):
    """代理文档列表"""
    agents: list[AgentDoc]


class CommandOption(BaseModel):
    """命令选项"""
    name: str
    description: str


class CommandDoc(BaseModel):
    """命令文档"""
    name: str
    description: str
    usage: str
    options: list[CommandOption]


class CommandsDoc(BaseModel):
    """命令文档列表"""
    commands: list[CommandDoc]


class PermissionModeGuide(BaseModel):
    """权限模式指南"""
    mode: str
    scenario: str


class ErrorHandling(BaseModel):
    """错误处理"""
    try_catch: str
    logging: str
    user_message: str


class BestPracticesDoc(BaseModel):
    """最佳实践文档"""
    tool_selection: dict[str, list[str]]
    permission_mode_guide: list[PermissionModeGuide]
    error_handling: ErrorHandling


# ==================== v0.3.7 插件管理 ====================


class Plugin(BaseModel):
    """插件"""
    id: str
    name: str
    description: str
    version: str
    author: str
    is_enabled: bool = True
    is_builtin: bool = False


class PluginsDoc(BaseModel):
    """插件列表"""
    plugins: list[Plugin]
    total: int = 0


# ==================== v0.3.8 钩子配置 ====================


class HookConfig(BaseModel):
    """钩子配置"""
    tools: list[str] = []
    action: str = "allow"  # "allow" or "block"
    notification: bool = False


class Hook(BaseModel):
    """钩子"""
    id: str
    name: str
    type: str  # PreToolUse, PostToolUse, Stop, SessionStart, Notification
    enabled: bool
    config: HookConfig = HookConfig()


class HooksDoc(BaseModel):
    """钩子列表"""
    hooks: list[Hook]
    total: int = 0


class HookTypeDoc(BaseModel):
    """钩子类型说明"""
    name: str
    description: str
    example: str


class HookTypesDoc(BaseModel):
    """钩子类型列表"""
    hook_types: list[HookTypeDoc]
