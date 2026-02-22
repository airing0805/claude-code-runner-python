/**
 * SearchRenderer - 搜索工具渲染器
 * v0.5.3 - 工具渲染器重构
 *
 * 包含：GrepRenderer、GlobRenderer、SearchResultRenderer
 */

import { BaseRenderer } from './base.js';

// 使用全局 CopyButton（由 copyButton.js 挂载到 window）
const CopyButton = window.CopyButton;

/**
 * Grep 工具输入渲染器
 * 显示搜索模式、路径、文件类型等
 */
export const GrepRenderer = {
    /**
     * 渲染 Grep 工具输入
     * @param {Object} input - 工具输入参数
     * @param {string} input.pattern - 搜索模式
     * @param {string} [input.path] - 搜索路径
     * @param {string} [input.glob] - 文件 glob 模式
     * @param {string} [input.type] - 文件类型
     * @returns {HTMLElement|null}
     */
    render(input) {
        if (!input || !input.pattern) {
            return null;
        }

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 创建卡片
        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 创建头部
        const header = BaseRenderer.createHeader({
            icon: '🔍',
            iconClass: 'text-amber-400',
            title: 'Search'
        });

        // 创建内容区域
        const contentEl = this._createContent(input);

        card.appendChild(header);
        card.appendChild(contentEl);
        container.appendChild(card);

        return container;
    },

    /**
     * 创建内容区域
     * @param {Object} input - 输入参数
     * @returns {HTMLElement}
     */
    _createContent(input) {
        const contentEl = document.createElement('div');
        contentEl.className = 'p-3 space-y-2';

        // Pattern
        contentEl.appendChild(this._createField('Pattern:', input.pattern, 'text-amber-300 bg-amber-500/10'));

        // Path
        if (input.path) {
            contentEl.appendChild(this._createField('Path:', input.path));
        }

        // Glob
        if (input.glob) {
            contentEl.appendChild(this._createField('Glob:', input.glob));
        }

        // Type
        if (input.type) {
            contentEl.appendChild(this._createField('Type:', input.type));
        }

        // 选项标签
        const options = this._extractOptions(input);
        if (options.length > 0) {
            contentEl.appendChild(this._createOptionsRow(options));
        }

        return contentEl;
    },

    /**
     * 提取选项参数
     * @param {Object} input - 输入参数
     * @returns {Array<{flag: string, label: string}>}
     */
    _extractOptions(input) {
        const options = [];

        // -i 忽略大小写
        if (input.i || input['-i']) {
            options.push({ flag: '-i', label: '忽略大小写' });
        }

        // -n 显示行号
        if (input.n || input['-n']) {
            options.push({ flag: '-n', label: '显示行号' });
        }

        // output_mode
        if (input.output_mode) {
            options.push({ flag: `--output=${input.output_mode}`, label: '' });
        }

        // head_limit
        if (input.head_limit) {
            options.push({ flag: `--head=${input.head_limit}`, label: '' });
        }

        return options;
    },

    /**
     * 创建选项标签行
     * @param {Array<{flag: string, label: string}>} options - 选项列表
     * @returns {HTMLElement}
     */
    _createOptionsRow(options) {
        const row = document.createElement('div');
        row.className = 'flex items-center gap-2 flex-wrap';

        const labelEl = document.createElement('span');
        labelEl.className = 'text-xs text-zinc-500';
        labelEl.textContent = 'Options:';
        row.appendChild(labelEl);

        options.forEach(opt => {
            const tag = document.createElement('span');
            tag.className = 'text-[10px] text-zinc-400 bg-zinc-700/50 px-1.5 py-0.5 rounded font-mono';
            tag.textContent = opt.flag;
            if (opt.label) {
                tag.title = opt.label;
            }
            row.appendChild(tag);
        });

        return row;
    },

    /**
     * 创建字段行
     * @param {string} label - 标签
     * @param {string} value - 值
     * @param {string} [valueClass] - 值的额外样式
     * @returns {HTMLElement}
     */
    _createField(label, value, valueClass = '') {
        const field = document.createElement('div');
        field.className = 'flex items-center gap-2';

        const labelEl = document.createElement('span');
        labelEl.className = 'text-xs text-zinc-500';
        labelEl.textContent = label;

        const valueEl = document.createElement('code');
        valueEl.className = `text-xs font-mono ${valueClass} px-1.5 py-0.5 rounded`.trim();
        valueEl.textContent = value;

        field.appendChild(labelEl);
        field.appendChild(valueEl);
        return field;
    }
};

/**
 * Glob 工具输入渲染器
 * 显示文件匹配模式和路径
 */
export const GlobRenderer = {
    /**
     * 渲染 Glob 工具输入
     * @param {Object} input - 工具输入参数
     * @param {string} input.pattern - Glob 模式
     * @param {string} [input.path] - 搜索路径
     * @returns {HTMLElement|null}
     */
    render(input) {
        if (!input || !input.pattern) {
            return null;
        }

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 创建卡片
        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 创建头部
        const header = BaseRenderer.createHeader({
            icon: '📁',
            iconClass: 'text-cyan-400',
            title: 'Find Files'
        });

        // 创建内容区域
        const contentEl = this._createContent(input);

        card.appendChild(header);
        card.appendChild(contentEl);
        container.appendChild(card);

        return container;
    },

    /**
     * 创建内容区域
     * @param {Object} input - 输入参数
     * @returns {HTMLElement}
     */
    _createContent(input) {
        const contentEl = document.createElement('div');
        contentEl.className = 'p-3 space-y-2';

        // Pattern
        const patternField = document.createElement('div');
        patternField.className = 'flex items-center gap-2';

        const patternLabel = document.createElement('span');
        patternLabel.className = 'text-xs text-zinc-500';
        patternLabel.textContent = 'Pattern:';

        const patternValue = document.createElement('code');
        patternValue.className = 'text-xs font-mono text-cyan-300 bg-cyan-500/10 px-1.5 py-0.5 rounded';
        patternValue.textContent = input.pattern;

        patternField.appendChild(patternLabel);
        patternField.appendChild(patternValue);
        contentEl.appendChild(patternField);

        // Path
        if (input.path) {
            const pathField = document.createElement('div');
            pathField.className = 'flex items-center gap-2';

            const pathLabel = document.createElement('span');
            pathLabel.className = 'text-xs text-zinc-500';
            pathLabel.textContent = 'Path:';

            const pathValue = document.createElement('span');
            pathValue.className = 'text-xs font-mono text-zinc-300';
            pathValue.textContent = input.path;

            pathField.appendChild(pathLabel);
            pathField.appendChild(pathValue);
            contentEl.appendChild(pathField);
        }

        // 匹配规则说明
        const rulesHint = this._createRulesHint(input.pattern);
        if (rulesHint) {
            contentEl.appendChild(rulesHint);
        }

        return contentEl;
    },

    /**
     * 创建匹配规则说明
     * @param {string} pattern - Glob 模式
     * @returns {HTMLElement|null}
     */
    _createRulesHint(pattern) {
        if (!pattern) return null;

        const hints = [];

        // 检测常见模式并生成说明
        if (pattern.includes('**')) {
            hints.push('** 递归匹配所有子目录');
        }
        if (pattern.includes('*') && !pattern.includes('**')) {
            hints.push('* 匹配任意字符（不含路径分隔符）');
        }
        if (pattern.includes('?')) {
            hints.push('? 匹配单个字符');
        }
        if (pattern.includes('[') && pattern.includes(']')) {
            hints.push('[] 匹配字符集');
        }
        if (pattern.startsWith('!')) {
            hints.push('! 排除模式');
        }

        if (hints.length === 0) return null;

        const hintEl = document.createElement('div');
        hintEl.className = 'text-[10px] text-zinc-500 mt-1 flex flex-wrap gap-1';

        hints.forEach(hint => {
            const span = document.createElement('span');
            span.className = 'bg-zinc-800/50 px-1 rounded';
            span.textContent = hint;
            hintEl.appendChild(span);
        });

        return hintEl;
    }
};

/**
 * 搜索结果渲染器
 * 用于 Grep/Glob 工具的结果显示
 */
export const SearchResultRenderer = {
    /**
     * 渲染搜索结果
     * @param {Object} options - 配置选项
     * @param {string} options.content - 结果内容
     * @param {boolean} [options.isFileList=false] - 是否为文件列表模式
     * @param {number} [options.maxLines=20] - 最大显示行数
     * @returns {HTMLElement}
     */
    render(options) {
        const { content, isFileList = false, maxLines = 20 } = options;

        // 空结果
        if (!content || content.trim().length === 0) {
            return this._renderEmptyResult();
        }

        const lines = content.split('\n').filter(l => l.trim());
        const truncated = lines.length > maxLines;
        const displayLines = truncated ? lines.slice(0, maxLines) : lines;

        if (isFileList) {
            return this._renderFileList(displayLines, truncated, lines.length - maxLines);
        }

        return this._renderMatchList(displayLines, truncated, lines.length - maxLines, lines.length);
    },

    /**
     * 渲染空结果
     * @returns {HTMLElement}
     */
    _renderEmptyResult() {
        const container = BaseRenderer.createContainer();

        const card = document.createElement('div');
        card.className = 'flex items-center gap-2 px-3 py-2 bg-zinc-800/30 border border-zinc-700/50 rounded-lg';

        const icon = document.createElement('span');
        icon.textContent = '🔍';
        icon.className = 'text-zinc-500';

        const text = document.createElement('span');
        text.className = 'text-xs text-zinc-400';
        text.textContent = 'No matches found';

        card.appendChild(icon);
        card.appendChild(text);
        container.appendChild(card);

        return container;
    },

    /**
     * 渲染文件列表
     * @param {string[]} displayLines - 显示的行
     * @param {boolean} truncated - 是否截断
     * @param {number} remaining - 剩余行数
     * @returns {HTMLElement}
     */
    _renderFileList(displayLines, truncated, remaining) {
        const container = BaseRenderer.createContainer();

        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 头部
        const header = BaseRenderer.createHeader({
            icon: '📁',
            iconClass: 'text-cyan-400',
            title: 'Files Found',
            extraContent: [
                this._createCountBadge(displayLines.length + (truncated ? remaining : 0), 'files')
            ]
        });

        // 文件列表
        const listEl = document.createElement('div');
        listEl.className = 'overflow-y-auto max-h-60';

        const ul = document.createElement('ul');
        ul.className = 'divide-y divide-zinc-800/50';

        displayLines.forEach(line => {
            const li = this._createFileItem(line);
            ul.appendChild(li);
        });

        listEl.appendChild(ul);

        // 截断提示
        if (truncated) {
            const moreEl = document.createElement('div');
            moreEl.className = 'px-3 py-2 text-xs text-zinc-500 border-t border-zinc-700/50';
            moreEl.textContent = `... ${remaining} more files`;
            listEl.appendChild(moreEl);
        }

        card.appendChild(header);
        card.appendChild(listEl);
        container.appendChild(card);

        return container;
    },

    /**
     * 创建文件列表项
     * @param {string} filePath - 文件路径
     * @returns {HTMLElement}
     */
    _createFileItem(filePath) {
        const li = document.createElement('li');
        li.className = 'group flex items-center gap-2 px-3 py-1.5 hover:bg-zinc-800/30';

        const icon = document.createElement('span');
        icon.textContent = '📄';
        icon.className = 'text-zinc-500 flex-shrink-0';

        const pathEl = document.createElement('span');
        pathEl.className = 'text-xs font-mono text-zinc-300 truncate flex-1';
        pathEl.textContent = filePath;

        li.appendChild(icon);
        li.appendChild(pathEl);

        // 复制按钮（hover 显示）
        const copyBtn = CopyButton.create(filePath, { title: '复制路径' });
        copyBtn.className = 'opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-zinc-700/50 rounded';
        li.appendChild(copyBtn);

        return li;
    },

    /**
     * 渲染匹配列表
     * @param {string[]} displayLines - 显示的行
     * @param {boolean} truncated - 是否截断
     * @param {number} remaining - 剩余行数
     * @param {number} totalCount - 总行数
     * @returns {HTMLElement}
     */
    _renderMatchList(displayLines, truncated, remaining, totalCount) {
        const container = BaseRenderer.createContainer();

        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 头部
        const header = BaseRenderer.createHeader({
            icon: '🔍',
            iconClass: 'text-amber-400',
            title: 'Results',
            extraContent: [
                this._createCountBadge(totalCount, 'matches')
            ]
        });

        // 内容
        const contentEl = document.createElement('div');
        contentEl.className = 'overflow-x-auto max-h-80 overflow-y-auto';

        const pre = document.createElement('pre');
        pre.className = 'text-xs font-mono p-3 text-zinc-300 whitespace-pre-wrap';
        pre.textContent = displayLines.join('\n');

        if (truncated) {
            const more = document.createElement('div');
            more.className = 'text-zinc-500 mt-2 pt-2 border-t border-zinc-700/50';
            more.textContent = `... ${remaining} more matches`;
            pre.appendChild(more);
        }

        contentEl.appendChild(pre);
        card.appendChild(header);
        card.appendChild(contentEl);
        container.appendChild(card);

        return container;
    },

    /**
     * 创建数量徽章
     * @param {number} count - 数量
     * @param {string} label - 标签
     * @returns {HTMLElement}
     */
    _createCountBadge(count, label) {
        const el = document.createElement('span');
        el.className = 'text-xs text-zinc-500 ml-auto';
        el.textContent = `${count} ${label}`;
        return el;
    }
};

// 默认导出
export default { GrepRenderer, GlobRenderer, SearchResultRenderer };
