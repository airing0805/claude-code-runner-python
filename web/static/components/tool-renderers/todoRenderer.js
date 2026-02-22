/**
 * TodoRenderer - Todo 列表渲染器
 * v0.5.3 - 工具渲染器重构
 */

import { BaseRenderer } from './base.js';

// 使用全局 MarkdownRenderer（由 markdownRenderer.js 挂载到 window）
const MarkdownRenderer = window.MarkdownRenderer;

/**
 * Todo 工具渲染器
 * 显示任务列表，带状态图标和进度条
 */
export const TodoRenderer = {
    /**
     * 状态图标映射
     */
    statusIcons: {
        completed: { icon: '✅', class: 'text-emerald-400' },
        in_progress: { icon: '⏳', class: 'text-amber-400 animate-spin-slow' },
        pending: { icon: '⭕', class: 'text-zinc-500' }
    },

    /**
     * 状态样式映射
     */
    statusClasses: {
        completed: 'text-zinc-400 line-through',
        in_progress: 'text-amber-200',
        pending: 'text-zinc-300'
    },

    /**
     * 渲染 Todo 列表
     * @param {Object} options - 配置选项
     * @param {Array} options.todos - Todo 项数组
     * @param {string} options.todos[].content - 任务内容
     * @param {string} options.todos[].status - 任务状态 (pending/in_progress/completed)
     * @returns {HTMLElement|null}
     */
    render(options) {
        const { todos } = options;

        if (!todos || todos.length === 0) {
            return null;
        }

        const completedCount = todos.filter(t => t.status === 'completed').length;
        const totalCount = todos.length;
        const progress = (completedCount / totalCount) * 100;

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 创建卡片
        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 创建头部
        const header = this._createHeader(completedCount, totalCount, progress);
        card.appendChild(header);

        // 创建列表
        const list = this._createTodoList(todos);
        card.appendChild(list);

        container.appendChild(card);
        return container;
    },

    /**
     * 创建头部
     * @param {number} completed - 已完成数
     * @param {number} total - 总数
     * @param {number} progress - 进度百分比
     * @returns {HTMLElement}
     */
    _createHeader(completed, total, progress) {
        const header = BaseRenderer.createHeader({
            icon: '📋',
            iconClass: 'text-violet-400',
            title: 'Tasks',
            extraContent: [
                this._createProgress(completed, total, progress)
            ]
        });

        return header;
    },

    /**
     * 创建进度显示
     * @param {number} completed - 已完成数
     * @param {number} total - 总数
     * @param {number} progress - 进度百分比
     * @returns {HTMLElement}
     */
    _createProgress(completed, total, progress) {
        const wrapper = document.createElement('div');
        wrapper.className = 'flex items-center gap-2 ml-auto';

        // 数字显示
        const countEl = document.createElement('span');
        countEl.className = 'text-xs text-zinc-500';
        countEl.textContent = `${completed}/${total}`;

        // 进度条
        const barOuter = document.createElement('div');
        barOuter.className = 'w-16 h-1.5 bg-zinc-700 rounded-full overflow-hidden';

        const barInner = document.createElement('div');
        barInner.className = 'h-full bg-violet-500 transition-all duration-300';
        barInner.style.width = `${progress}%`;

        barOuter.appendChild(barInner);
        wrapper.appendChild(countEl);
        wrapper.appendChild(barOuter);

        return wrapper;
    },

    /**
     * 创建 Todo 列表
     * @param {Array} todos - Todo 项数组
     * @returns {HTMLElement}
     */
    _createTodoList(todos) {
        const ul = document.createElement('ul');
        ul.className = 'divide-y divide-zinc-800/50';

        todos.forEach((todo, index) => {
            const li = this._createTodoItem(todo, index);
            ul.appendChild(li);
        });

        return ul;
    },

    /**
     * 创建 Todo 项
     * @param {Object} todo - Todo 数据
     * @param {number} index - 索引
     * @returns {HTMLElement}
     */
    _createTodoItem(todo, index) {
        const statusInfo = this.statusIcons[todo.status] || this.statusIcons.pending;
        const textClass = this.statusClasses[todo.status] || this.statusClasses.pending;

        const li = document.createElement('li');
        li.className = 'flex items-start gap-2.5 px-3 py-2 hover:bg-zinc-800/20 transition-colors';

        // 状态图标
        const iconEl = document.createElement('span');
        iconEl.className = `mt-0.5 flex-shrink-0 ${statusInfo.class}`;
        iconEl.textContent = statusInfo.icon;

        // 内容 - 支持 Markdown 渲染
        const contentEl = document.createElement('span');
        contentEl.className = `text-xs leading-relaxed ${textClass}`;

        // 使用 Markdown 渲染内容
        if (MarkdownRenderer.isAvailable() && this._hasMarkdown(todo.content)) {
            MarkdownRenderer.render(todo.content, contentEl, {
                className: 'todo-markdown inline-markdown'
            });
        } else {
            contentEl.textContent = todo.content;
        }

        li.appendChild(iconEl);
        li.appendChild(contentEl);

        return li;
    },

    /**
     * 检测内容是否包含 Markdown 语法
     * @param {string} content - 内容
     * @returns {boolean}
     */
    _hasMarkdown(content) {
        if (!content) return false;
        // 检测常见的 Markdown 语法
        const mdPatterns = [
            /\*\*.+\*\*/,           // **bold**
            /\*.+\*/,               // *italic*
            /`.+`/,                 // `code`
            /\[.+?\]\(.+?\)/,       // [link](url)
            /^[-*+]\s/,             // list
            /\n/,                   // 换行（可能包含多行内容）
        ];
        return mdPatterns.some(pattern => pattern.test(content));
    }
};

// 默认导出
export default TodoRenderer;
