/**
 * 工具渲染器基类
 * v0.5.3 - 工具渲染器重构
 *
 * 所有工具渲染器的通用接口和工具函数
 */

// 动态导入 CopyButton（避免循环依赖）
let CopyButtonModule = null;
async function getCopyButton() {
    if (!CopyButtonModule) {
        const module = await import('../copyButton.js');
        CopyButtonModule = module.CopyButton;
    }
    return CopyButtonModule;
}

/**
 * 基础工具渲染器
 * 提供通用方法供具体渲染器继承或使用
 */
export const BaseRenderer = {
    /**
     * 渲染方法（抽象方法，子类应重写）
     * @param {Object} data - 渲染数据
     * @returns {HTMLElement|null}
     * @throws {Error} 如果子类未实现此方法
     */
    render(data) {
        throw new Error('BaseRenderer.render() must be implemented by subclass');
    },
    /**
     * 从文件路径获取文件名（最后两级）
     * @param {string} filePath - 文件路径
     * @returns {string}
     */
    getFileName(filePath) {
        if (!filePath) return '';
        const parts = filePath.split('/');
        return parts.slice(-2).join('/');
    },

    /**
     * 获取文件扩展名
     * @param {string} filePath - 文件路径
     * @returns {string}
     */
    getFileExtension(filePath) {
        if (!filePath) return '';
        const parts = filePath.split('.');
        return parts.length > 1 ? parts.pop().toLowerCase() : '';
    },

    /**
     * 根据扩展名获取语言标识
     * @param {string} ext - 文件扩展名
     * @returns {string|null}
     */
    getLanguageFromExt(ext) {
        const languageMap = {
            ts: 'TypeScript',
            tsx: 'TypeScript React',
            js: 'JavaScript',
            jsx: 'JavaScript React',
            py: 'Python',
            rb: 'Ruby',
            go: 'Go',
            rs: 'Rust',
            java: 'Java',
            cpp: 'C++',
            c: 'C',
            css: 'CSS',
            scss: 'SCSS',
            html: 'HTML',
            json: 'JSON',
            yaml: 'YAML',
            yml: 'YAML',
            md: 'Markdown',
            sql: 'SQL',
            sh: 'Shell',
            bash: 'Bash',
            toml: 'TOML',
            xml: 'XML',
        };
        return languageMap[ext] || null;
    },

    /**
     * HTML 转义
     * @param {string} text - 原始文本
     * @returns {string}
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 截断内容
     * @param {string} content - 内容
     * @param {number} maxLength - 最大长度
     * @returns {{ display: string, truncated: boolean, remaining: number }}
     */
    truncateContent(content, maxLength = 500) {
        if (!content) return { display: '', truncated: false, remaining: 0 };
        if (content.length <= maxLength) {
            return { display: content, truncated: false, remaining: 0 };
        }
        return {
            display: content.slice(0, maxLength),
            truncated: true,
            remaining: content.length - maxLength
        };
    },

    /**
     * 按行截断内容
     * @param {string} content - 内容
     * @param {number} maxLines - 最大行数
     * @returns {{ lines: string[], truncated: boolean, remaining: number }}
     */
    truncateLines(content, maxLines = 30) {
        if (!content) return { lines: [], truncated: false, remaining: 0 };
        const lines = content.split('\n');
        if (lines.length <= maxLines) {
            return { lines, truncated: false, remaining: 0 };
        }
        return {
            lines: lines.slice(0, maxLines),
            truncated: true,
            remaining: lines.length - maxLines
        };
    },

    /**
     * 创建基础容器结构
     * @param {Object} options - 配置选项
     * @returns {HTMLDivElement}
     */
    createContainer(options = {}) {
        const {
            className = '',
            borderColor = 'zinc-700/50',
            bgColor = 'zinc-900/70'
        } = options;

        const container = document.createElement('div');
        container.className = `tool-renderer w-full mt-2 ${className}`.trim();
        return container;
    },

    /**
     * 创建头部区域
     * @param {Object} options - 配置选项
     * @returns {HTMLDivElement}
     */
    createHeader(options = {}) {
        const {
            icon = '',
            iconClass = '',
            title = '',
            titleClass = 'text-zinc-300',
            badges = [],
            extraContent = []
        } = options;

        const header = document.createElement('div');
        header.className = 'tool-header flex items-center gap-2 px-3 py-2 border-b border-zinc-700/50 bg-zinc-800/30';

        // 图标
        if (icon) {
            const iconEl = document.createElement('span');
            iconEl.className = `tool-icon ${iconClass}`.trim();
            iconEl.innerHTML = icon;
            header.appendChild(iconEl);
        }

        // 标题
        if (title) {
            const titleEl = document.createElement('span');
            titleEl.className = `tool-title text-xs font-medium ${titleClass}`.trim();
            titleEl.textContent = title;
            header.appendChild(titleEl);
        }

        // 徽章
        badges.forEach(badge => {
            const badgeEl = document.createElement('span');
            badgeEl.className = `text-[10px] text-zinc-500 bg-zinc-700/50 px-1.5 py-0.5 rounded ${badge.class || ''}`.trim();
            badgeEl.textContent = badge.text;
            header.appendChild(badgeEl);
        });

        // 额外内容（右侧）
        const extraWrapper = document.createElement('div');
        extraWrapper.className = 'flex items-center gap-1.5 ml-auto';
        extraContent.forEach(el => {
            if (el instanceof HTMLElement) {
                extraWrapper.appendChild(el);
            }
        });
        if (extraWrapper.children.length > 0) {
            header.appendChild(extraWrapper);
        }

        return header;
    },

    /**
     * 创建内容区域
     * @param {Object} options - 配置选项
     * @returns {HTMLDivElement}
     */
    createContent(options = {}) {
        const {
            className = '',
            maxHeight = ''
        } = options;

        const content = document.createElement('div');
        content.className = `tool-content overflow-x-auto ${className}`.trim();
        if (maxHeight) {
            content.style.maxHeight = maxHeight;
            content.style.overflowY = 'auto';
        }
        return content;
    },

    /**
     * 添加复制按钮到容器
     * @param {HTMLElement} container - 容器元素
     * @param {string} text - 要复制的文本
     * @param {Object} options - 配置选项
     * @returns {Promise<HTMLButtonElement>}
     */
    async addCopyButton(container, text, options = {}) {
        const CopyButton = await getCopyButton();
        const button = CopyButton.create(text, options);

        // 将按钮添加到容器
        if (container instanceof HTMLElement) {
            container.appendChild(button);
        }

        return button;
    },

    /**
     * 创建复制按钮（不添加到容器）
     * @param {string} text - 要复制的文本
     * @param {Object} options - 配置选项
     * @returns {Promise<HTMLButtonElement>}
     */
    async createCopyButton(text, options = {}) {
        const CopyButton = await getCopyButton();
        return CopyButton.create(text, options);
    },

    /**
     * 格式化时间戳
     * @param {string|number|Date} timestamp - 时间戳
     * @param {Object} options - 格式化选项
     * @param {boolean} [options.showSeconds=true] - 是否显示秒
     * @param {boolean} [options.showDate=false] - 是否显示日期
     * @returns {string}
     */
    formatTimestamp(timestamp, options = {}) {
        const { showSeconds = true, showDate = false } = options;

        if (!timestamp) return '';

        let date;
        if (timestamp instanceof Date) {
            date = timestamp;
        } else if (typeof timestamp === 'number') {
            date = new Date(timestamp);
        } else if (typeof timestamp === 'string') {
            // 尝试解析 ISO 格式或其他常见格式
            date = new Date(timestamp);
        } else {
            return '';
        }

        // 检查日期是否有效
        if (isNaN(date.getTime())) {
            return '';
        }

        const pad = (n) => n.toString().padStart(2, '0');

        const hours = pad(date.getHours());
        const minutes = pad(date.getMinutes());
        const seconds = pad(date.getSeconds());

        let timeStr = `${hours}:${minutes}`;
        if (showSeconds) {
            timeStr += `:${seconds}`;
        }

        if (showDate) {
            const year = date.getFullYear();
            const month = pad(date.getMonth() + 1);
            const day = pad(date.getDate());
            return `${year}-${month}-${day} ${timeStr}`;
        }

        return timeStr;
    },

    /**
     * 格式化相对时间（如 "5 分钟前"）
     * @param {string|number|Date} timestamp - 时间戳
     * @returns {string}
     */
    formatRelativeTime(timestamp) {
        if (!timestamp) return '';

        let date;
        if (timestamp instanceof Date) {
            date = timestamp;
        } else if (typeof timestamp === 'number') {
            date = new Date(timestamp);
        } else if (typeof timestamp === 'string') {
            date = new Date(timestamp);
        } else {
            return '';
        }

        if (isNaN(date.getTime())) {
            return '';
        }

        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);

        if (diffSec < 60) {
            return '刚刚';
        } else if (diffMin < 60) {
            return `${diffMin} 分钟前`;
        } else if (diffHour < 24) {
            return `${diffHour} 小时前`;
        } else if (diffDay < 7) {
            return `${diffDay} 天前`;
        } else {
            // 超过 7 天，显示具体日期
            return this.formatTimestamp(timestamp, { showDate: true, showSeconds: false });
        }
    },

    /**
     * 格式化文件大小
     * @param {number} bytes - 字节数
     * @returns {string}
     */
    formatFileSize(bytes) {
        if (typeof bytes !== 'number' || bytes < 0) return '';

        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let unitIndex = 0;
        let size = bytes;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }

        // 保留 1-2 位小数
        const formatted = size < 10 ? size.toFixed(1) : Math.round(size);
        return `${formatted} ${units[unitIndex]}`;
    },

    /**
     * 格式化持续时间（毫秒转为可读格式）
     * @param {number} ms - 毫秒数
     * @returns {string}
     */
    formatDuration(ms) {
        if (typeof ms !== 'number' || ms < 0) return '';

        if (ms < 1000) {
            return `${ms}ms`;
        } else if (ms < 60000) {
            return `${(ms / 1000).toFixed(1)}s`;
        } else if (ms < 3600000) {
            const minutes = Math.floor(ms / 60000);
            const seconds = Math.round((ms % 60000) / 1000);
            return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
        } else {
            const hours = Math.floor(ms / 3600000);
            const minutes = Math.round((ms % 3600000) / 60000);
            return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
        }
    }
};

// 默认导出
export default BaseRenderer;
