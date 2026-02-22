/**
 * 工具预览系统
 * v0.5.4 - 消息渲染增强
 *
 * 提供工具调用的简短预览文本生成
 */

/**
 * 获取文件路径预览（显示最后两级目录）
 * @param {string} filePath - 完整文件路径
 * @returns {string} 预览路径
 */
function getFilePathPreview(filePath) {
    if (!filePath) return '';

    // 统一使用 / 分隔符
    const normalized = filePath.replace(/\\/g, '/');
    const parts = normalized.split('/');

    // 如果只有一级，直接返回
    if (parts.length <= 1) {
        return parts[0] || '';
    }

    // 返回最后两级
    return parts.slice(-2).join('/');
}

/**
 * 工具预览处理器映射表
 * 工具名称 -> 预览生成函数
 *
 * @type {Record<string, (input: Record<string, unknown>) => string|null>}
 */
export const TOOL_PREVIEW_HANDLERS = {
    /**
     * Read 工具预览 - 显示文件路径
     */
    read: (input) => {
        if (!input || !input.file_path) return null;
        return getFilePathPreview(String(input.file_path));
    },

    /**
     * Edit 工具预览 - 显示文件路径
     */
    edit: (input) => {
        if (!input || !input.file_path) return null;
        return getFilePathPreview(String(input.file_path));
    },

    /**
     * Write 工具预览 - 显示文件路径
     */
    write: (input) => {
        if (!input || !input.file_path) return null;
        return getFilePathPreview(String(input.file_path));
    },

    /**
     * Bash 工具预览 - 显示命令（截断到 50 字符）
     */
    bash: (input) => {
        if (!input || !input.command) return null;
        const cmd = String(input.command);
        return cmd.length > 50 ? cmd.slice(0, 50) + '...' : cmd;
    },

    /**
     * Grep 工具预览 - 显示搜索模式
     */
    grep: (input) => {
        if (!input || !input.pattern) return null;
        return `"${String(input.pattern)}"`;
    },

    /**
     * Glob 工具预览 - 显示 glob 模式
     */
    glob: (input) => {
        if (!input || !input.pattern) return null;
        return String(input.pattern);
    },

    /**
     * Task 工具预览 - 显示任务描述
     */
    task: (input) => {
        if (!input) return null;
        // 优先显示 description，其次显示 prompt 的前 50 字符
        if (input.description) {
            return String(input.description);
        }
        if (input.prompt) {
            const prompt = String(input.prompt);
            return prompt.length > 50 ? prompt.slice(0, 50) + '...' : prompt;
        }
        return null;
    },

    /**
     * TodoWrite 工具预览 - 显示任务数量
     */
    todowrite: (input) => {
        if (!input || !input.todos || !Array.isArray(input.todos)) return null;
        const count = input.todos.length;
        const completed = input.todos.filter(t => t.status === 'completed').length;
        return `${completed}/${count} 完成`;
    },

    /**
     * AskUserQuestion 工具预览 - 显示问题数量
     */
    askuserquestion: (input) => {
        if (!input || !input.questions || !Array.isArray(input.questions)) return null;
        const count = input.questions.length;
        return `${count} 个问题`;
    },

    /**
     * WebSearch 工具预览 - 显示搜索查询
     */
    websearch: (input) => {
        if (!input || !input.query) return null;
        const query = String(input.query);
        return query.length > 50 ? query.slice(0, 50) + '...' : query;
    },

    /**
     * WebFetch 工具预览 - 显示 URL hostname
     */
    webfetch: (input) => {
        if (!input || !input.url) return null;
        try {
            const url = new URL(String(input.url));
            return url.hostname;
        } catch {
            // URL 解析失败，返回截断的 URL
            const url = String(input.url);
            return url.length > 30 ? url.slice(0, 30) + '...' : url;
        }
    },
};

/**
 * 获取工具预览文本
 *
 * @param {string} toolName - 工具名称
 * @param {Record<string, unknown>|undefined} input - 工具输入参数
 * @returns {string|null} 预览文本，无预览时返回 null
 */
export function getToolPreview(toolName, input) {
    if (!toolName || !input) {
        return null;
    }

    const name = toolName.toLowerCase();

    // 1. 查找精确匹配的处理器
    const handler = TOOL_PREVIEW_HANDLERS[name];
    if (handler) {
        return handler(input);
    }

    // 2. 模式匹配 - Web/Fetch 工具
    if (name.includes('web') || name.includes('fetch') || name.includes('url')) {
        if (input.url) {
            try {
                const url = new URL(String(input.url));
                return url.hostname;
            } catch {
                const url = String(input.url);
                return url.length > 30 ? url.slice(0, 30) + '...' : url;
            }
        }
    }

    // 3. 通用回退 - 如果有 file_path 或 path，显示路径预览
    if (input.file_path) {
        return getFilePathPreview(String(input.file_path));
    }
    if (input.path) {
        return getFilePathPreview(String(input.path));
    }

    return null;
}

// 导出到全局命名空间
if (typeof window !== 'undefined') {
    window.ToolPreview = {
        TOOL_PREVIEW_HANDLERS,
        getToolPreview,
        getFilePathPreview,
    };
}

// 默认导出
export default {
    TOOL_PREVIEW_HANDLERS,
    getToolPreview,
    getFilePathPreview,
};
