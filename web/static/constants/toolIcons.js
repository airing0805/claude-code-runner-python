/**
 * 工具图标系统
 * v0.5.4 - 消息渲染增强
 *
 * 提供工具名称到 Unicode 图标的映射
 */

/**
 * 工具图标映射表
 * 工具名称 -> Unicode 图标
 */
export const TOOL_ICONS = {
    // 任务管理
    todowrite: '☑️',      // ListTodo

    // 文件操作
    read: '📄',          // FileCode
    write: '📝',         // FilePlus2
    edit: '✏️',          // Pencil

    // 命令执行
    bash: '⌨️',          // Terminal

    // 搜索工具
    grep: '🔍',          // Search
    glob: '📁',          // FolderOpen

    // 子代理
    task: '🤖',          // Bot

    // 网络工具
    websearch: '🌐',     // Globe
    webfetch: '🌐',      // Globe

    // MCP 工具
    mcp__sequential-thinking__sequentialthinking: '🧠', // Brain
};

/**
 * 工具图标模式匹配
 * 用于匹配工具名称中包含特定关键词的工具
 */
export const TOOL_ICON_PATTERNS = [
    { patterns: ['web', 'fetch', 'url'], icon: '🌐' },      // Globe
    { patterns: ['git', 'commit'], icon: '🔀' },            // GitBranch
    { patterns: ['sql', 'database', 'query'], icon: '🗄️' }, // Database
    { patterns: ['file', 'disk'], icon: '💾' },             // HardDrive
    { patterns: ['search', 'find'], icon: '🔍' },           // Search
    { patterns: ['http', 'api', 'request'], icon: '🔌' },   // Plug
    { patterns: ['image', 'img', 'picture', 'vision'], icon: '🖼️' }, // Image
    { patterns: ['analyze', 'analysis'], icon: '📊' },      // Chart
    { patterns: ['mcp'], icon: '🔌' },                       // MCP connector
    { patterns: ['github'], icon: '🐙' },                   // GitHub
    { patterns: ['sequential', 'thinking'], icon: '🧠' },   // Brain
];

/**
 * 获取工具图标
 * 先精确匹配 TOOL_ICONS，再模式匹配 TOOL_ICON_PATTERNS
 *
 * @param {string} toolName - 工具名称
 * @returns {string} Unicode 图标
 */
export function getToolIcon(toolName) {
    if (!toolName) {
        return '🔧'; // Wrench - 默认图标
    }

    const name = toolName.toLowerCase();

    // 1. 精确匹配
    if (TOOL_ICONS[name]) {
        return TOOL_ICONS[name];
    }

    // 2. 模式匹配
    for (const { patterns, icon } of TOOL_ICON_PATTERNS) {
        if (patterns.some((p) => name.includes(p))) {
            return icon;
        }
    }

    // 3. 默认图标
    return '🔧'; // Wrench
}

/**
 * 获取工具颜色类名
 * 根据工具类型返回对应的颜色类名
 *
 * @param {string} toolName - 工具名称
 * @returns {string} CSS 类名
 */
export function getToolColorClass(toolName) {
    if (!toolName) {
        return 'tool-color-default';
    }

    const name = toolName.toLowerCase();

    // 文件操作类 - cyan
    if (['read', 'write', 'edit', 'glob'].some(t => name.includes(t))) {
        return 'tool-color-cyan';
    }

    // 命令执行类 - green
    if (['bash', 'terminal', 'shell'].some(t => name.includes(t))) {
        return 'tool-color-green';
    }

    // 搜索类 - violet
    if (['grep', 'search', 'find'].some(t => name.includes(t))) {
        return 'tool-color-violet';
    }

    // 任务管理类 - amber
    if (['todo', 'task'].some(t => name.includes(t))) {
        return 'tool-color-amber';
    }

    // 网络类 - sky
    if (['web', 'http', 'api', 'url'].some(t => name.includes(t))) {
        return 'tool-color-sky';
    }

    // 思考类 - rose
    if (['thinking', 'sequential', 'brain'].some(t => name.includes(t))) {
        return 'tool-color-rose';
    }

    return 'tool-color-default';
}

// 导出到全局命名空间
if (typeof window !== 'undefined') {
    window.ToolIcons = {
        TOOL_ICONS,
        TOOL_ICON_PATTERNS,
        getToolIcon,
        getToolColorClass,
    };
}

// 默认导出
export default {
    TOOL_ICONS,
    TOOL_ICON_PATTERNS,
    getToolIcon,
    getToolColorClass,
};
