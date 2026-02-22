/**
 * BashRenderer - Bash 命令工具渲染器
 * v0.5.3 - 工具渲染器重构
 */

import { BaseRenderer } from './base.js';

// 使用全局 CopyButton（由 copyButton.js 挂载到 window）
const CopyButton = window.CopyButton;

/**
 * Bash 工具输入渲染器
 * 显示命令内容和描述
 */
export const BashRenderer = {
    /**
     * 渲染 Bash 工具输入
     * @param {Object} input - 工具输入参数
     * @param {string} input.command - 命令内容
     * @param {string} [input.description] - 命令描述
     * @param {number} [input.timeout] - 超时时间
     * @returns {HTMLElement|null}
     */
    render(input) {
        if (!input || !input.command) {
            return null;
        }

        const command = input.command;
        const description = input.description;

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 创建卡片
        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 创建头部
        const header = BaseRenderer.createHeader({
            icon: '⌨️',
            iconClass: 'text-green-400',
            title: 'Command',
            extraContent: [
                this._createDescription(description),
                this._createCopyButton(command)
            ]
        });

        // 创建命令内容
        const contentEl = this._createCommandContent(command);

        card.appendChild(header);
        card.appendChild(contentEl);
        container.appendChild(card);

        return container;
    },

    /**
     * 创建描述元素
     * @param {string} description - 描述文本
     * @returns {HTMLElement|null}
     */
    _createDescription(description) {
        if (!description) return null;

        const el = document.createElement('span');
        el.className = 'text-xs text-zinc-500 truncate ml-1';
        el.textContent = `— ${description}`;
        return el;
    },

    /**
     * 创建复制按钮
     * @param {string} command - 命令内容
     * @returns {HTMLElement}
     */
    _createCopyButton(command) {
        const btn = CopyButton.create(command, {
            title: '复制命令',
            copiedTitle: '已复制'
        });
        btn.classList.add('p-1', 'hover:bg-zinc-700/50', 'rounded', 'transition-colors');
        return btn;
    },

    /**
     * 创建命令内容区域
     * @param {string} command - 命令内容
     * @param {number} [maxLength=50] - 显示的最大长度
     * @returns {HTMLElement}
     */
    _createCommandContent(command, maxLength = 50) {
        const contentEl = document.createElement('div');
        contentEl.className = 'p-3 overflow-x-auto';

        const wrapper = document.createElement('div');
        wrapper.className = 'flex items-start gap-2';

        const pre = document.createElement('pre');
        pre.className = 'text-xs font-mono m-0 p-0 text-zinc-200 whitespace-pre-wrap break-all';

        // 如果命令超长，显示截断预览
        const truncated = command.length > maxLength;
        const displayCommand = truncated ? command.slice(0, maxLength) + '...' : command;
        pre.textContent = displayCommand;

        // 如果有截断，添加完整命令的 tooltip
        if (truncated) {
            pre.title = command;
        }

        wrapper.appendChild(pre);
        contentEl.appendChild(wrapper);

        return contentEl;
    }
};

/**
 * BashResultRenderer - Bash 命令结果渲染器
 * 显示命令执行输出
 */
export const BashResultRenderer = {
    /**
     * 渲染 Bash 命令结果
     * @param {Object} options - 配置选项
     * @param {string} options.content - 输出内容
     * @param {boolean} [options.isError=false] - 是否错误输出
     * @param {number} [options.maxLines=30] - 最大显示行数
     * @param {number} [options.duration] - 执行时间（毫秒）
     * @returns {HTMLElement}
     */
    render(options) {
        const { content, isError = false, maxLines = 30, duration } = options;

        // 空输出
        if (!content || content.trim().length === 0) {
            return this._renderEmptyResult();
        }

        const lines = content.split('\n');
        const truncated = lines.length > maxLines;
        const displayLines = truncated ? lines.slice(0, maxLines) : lines;

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 创建卡片（根据错误状态设置样式）
        const card = document.createElement('div');
        card.className = isError
            ? 'bg-rose-950/20 border border-rose-900/30 rounded-lg overflow-hidden'
            : 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 创建头部
        const header = this._createHeader(isError, lines.length, content, duration);
        card.appendChild(header);

        // 创建内容区域
        const contentEl = this._createContent(displayLines, truncated, lines.length - maxLines, isError);
        card.appendChild(contentEl);

        container.appendChild(card);
        return container;
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
        icon.textContent = '✅';
        icon.className = 'text-teal-400';

        const text = document.createElement('span');
        text.className = 'text-xs text-zinc-400';
        text.textContent = 'Command completed successfully (no output)';

        card.appendChild(icon);
        card.appendChild(text);
        container.appendChild(card);

        return container;
    },

    /**
     * 创建头部
     * @param {boolean} isError - 是否错误
     * @param {number} lineCount - 行数
     * @param {string} content - 输出内容（用于复制）
     * @param {number} [duration] - 执行时间（毫秒）
     * @returns {HTMLElement}
     */
    _createHeader(isError, lineCount, content, duration) {
        const extraContent = [];

        // 行数
        extraContent.push(this._createLineCount(lineCount));

        // 执行时间
        if (duration !== undefined && duration !== null) {
            extraContent.push(this._createDuration(duration));
        }

        // 复制按钮
        if (content && content.trim()) {
            extraContent.push(this._createCopyButton(content));
        }

        return BaseRenderer.createHeader({
            icon: isError ? '⚠️' : '▶️',
            iconClass: isError ? 'text-rose-400' : 'text-teal-400',
            title: isError ? 'Error Output' : 'Output',
            titleClass: isError ? 'text-rose-300' : 'text-zinc-300',
            extraContent: extraContent
        });
    },

    /**
     * 创建行数显示
     * @param {number} count - 行数
     * @returns {HTMLElement}
     */
    _createLineCount(count) {
        const el = document.createElement('span');
        el.className = 'text-xs text-zinc-500 ml-auto';
        el.textContent = `${count} lines`;
        return el;
    },

    /**
     * 创建执行时间显示
     * @param {number} duration - 执行时间（毫秒）
     * @returns {HTMLElement}
     */
    _createDuration(duration) {
        const el = document.createElement('span');
        el.className = 'text-xs text-zinc-500';
        el.textContent = BaseRenderer.formatDuration(duration);
        return el;
    },

    /**
     * 创建复制按钮
     * @param {string} content - 要复制的内容
     * @returns {HTMLElement}
     */
    _createCopyButton(content) {
        const btn = CopyButton.create(content, {
            title: '复制输出',
            copiedTitle: '已复制'
        });
        btn.classList.add('p-1', 'hover:bg-zinc-700/50', 'rounded', 'transition-colors');
        return btn;
    },

    /**
     * 创建内容区域
     * @param {string[]} displayLines - 显示的行
     * @param {boolean} truncated - 是否截断
     * @param {number} remaining - 剩余行数
     * @param {boolean} isError - 是否错误
     * @returns {HTMLElement}
     */
    _createContent(displayLines, truncated, remaining, isError) {
        const contentEl = document.createElement('div');
        contentEl.className = 'overflow-x-auto max-h-80 overflow-y-auto';

        const pre = document.createElement('pre');
        pre.className = isError
            ? 'text-xs font-mono p-3 whitespace-pre-wrap break-all text-rose-200/80'
            : 'text-xs font-mono p-3 whitespace-pre-wrap break-all text-zinc-300';
        pre.textContent = displayLines.join('\n');

        if (truncated) {
            const more = document.createElement('div');
            more.className = 'text-zinc-500 mt-2 pt-2 border-t border-zinc-700/50';
            more.textContent = `... ${remaining} more lines`;
            pre.appendChild(more);
        }

        contentEl.appendChild(pre);
        return contentEl;
    }
};

// 默认导出
export default { BashRenderer, BashResultRenderer };
