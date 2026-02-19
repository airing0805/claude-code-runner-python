/**
 * 常量定义模块
 * 定义应用程序中使用的常量数据
 */

// 工具列表配置
const AVAILABLE_TOOLS = [
    { name: 'Read', description: '读取文件', selected: true },
    { name: 'Write', description: '创建文件', selected: true },
    { name: 'Edit', description: '编辑文件', selected: true },
    { name: 'Bash', description: '执行命令', selected: true },
    { name: 'Glob', description: '查找文件', selected: true },
    { name: 'Grep', description: '搜索内容', selected: true },
    { name: 'WebSearch', description: '网络搜索', selected: false },
    { name: 'WebFetch', description: '获取网页', selected: false },
    { name: 'Task', description: '子代理任务', selected: false },
];

// 视图名称常量
const Views = {
    CURRENT_SESSION: 'current-session',
    HISTORY: 'history',
    EXAMPLES: 'examples',
    CLAUDE_STATUS: 'claude-status',
    CLAUDE_DOCS: 'claude-docs',
    AGENT_MONITOR: 'agent-monitor',
    SKILLS: 'skills',
    MCP_SERVERS: 'mcp-servers',
    PLUGINS: 'plugins'
};

// 消息类型常量
const MessageTypes = {
    TEXT: 'text',
    THINKING: 'thinking',
    TOOL_USE: 'tool_use',
    TOOL_RESULT: 'tool_result',
    ERROR: 'error',
    COMPLETE: 'complete',
    INFO: 'info'
};

// 导出到全局命名空间
window.AVAILABLE_TOOLS = AVAILABLE_TOOLS;
window.Views = Views;
window.MessageTypes = MessageTypes;
