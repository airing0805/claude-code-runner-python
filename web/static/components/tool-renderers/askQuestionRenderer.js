/**
 * AskQuestionRenderer - 用户问答渲染器
 * v0.5.3 - 工具渲染器重构
 */

import { BaseRenderer } from './base.js';

// 使用全局 MarkdownRenderer（由 markdownRenderer.js 挂载到 window）
const MarkdownRenderer = window.MarkdownRenderer;

/**
 * AskQuestion 工具渲染器
 * 显示问题和选项列表
 */
export const AskQuestionRenderer = {
    /**
     * 渲染问答内容
     * @param {Object} input - 工具输入参数
     * @param {Array} input.questions - 问题数组
     * @param {string} input.questions[].header - 问题标题
     * @param {string} input.questions[].question - 问题内容
     * @param {Array} input.questions[].options - 选项数组
     * @param {boolean} input.questions[].multiSelect - 是否多选
     * @returns {HTMLElement|null}
     */
    render(input) {
        if (!input || !input.questions || input.questions.length === 0) {
            return null;
        }

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 多个问题时使用 space-y-3
        if (input.questions.length > 1) {
            container.classList.add('space-y-3');
        }

        // 渲染每个问题
        input.questions.forEach((question, index) => {
            const questionEl = this._renderQuestion(question, index);
            if (questionEl) {
                container.appendChild(questionEl);
            }
        });

        return container;
    },

    /**
     * 渲染单个问题
     * @param {Object} question - 问题数据
     * @param {number} index - 索引
     * @returns {HTMLElement}
     */
    _renderQuestion(question, index) {
        // 创建卡片
        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 创建头部
        const header = this._createHeader(question);
        card.appendChild(header);

        // 创建内容区域
        const contentEl = this._createContent(question);
        card.appendChild(contentEl);

        return card;
    },

    /**
     * 创建头部
     * @param {Object} question - 问题数据
     * @returns {HTMLElement}
     */
    _createHeader(question) {
        const extraContent = [];

        // 多选标签
        if (question.multiSelect) {
            const tag = document.createElement('span');
            tag.className = 'text-[10px] text-zinc-500 bg-zinc-700/50 px-1.5 py-0.5 rounded ml-auto';
            tag.textContent = 'Multi-select';
            extraContent.push(tag);
        }

        return BaseRenderer.createHeader({
            icon: '❓',
            iconClass: 'text-violet-400',
            title: question.header || 'Question',
            extraContent
        });
    },

    /**
     * 创建内容区域
     * @param {Object} question - 问题数据
     * @returns {HTMLElement}
     */
    _createContent(question) {
        const contentEl = document.createElement('div');
        contentEl.className = 'p-3 space-y-3';

        // 问题文本
        const questionText = document.createElement('p');
        questionText.className = 'text-sm text-zinc-200';
        questionText.textContent = question.question || '';
        contentEl.appendChild(questionText);

        // 选项列表
        if (question.options && question.options.length > 0) {
            const optionsEl = this._createOptions(question.options, question.multiSelect);
            contentEl.appendChild(optionsEl);
        }

        return contentEl;
    },

    /**
     * 创建选项列表
     * @param {Array} options - 选项数组
     * @param {boolean} multiSelect - 是否多选
     * @returns {HTMLElement}
     */
    _createOptions(options, multiSelect) {
        const wrapper = document.createElement('div');
        wrapper.className = 'space-y-2';

        options.forEach(option => {
            const optionEl = this._createOption(option, multiSelect);
            wrapper.appendChild(optionEl);
        });

        return wrapper;
    },

    /**
     * 创建单个选项
     * @param {Object} option - 选项数据
     * @param {boolean} multiSelect - 是否多选
     * @returns {HTMLElement}
     */
    _createOption(option, multiSelect) {
        const wrapper = document.createElement('div');
        wrapper.className = 'flex items-start gap-2 px-2 py-1.5 rounded bg-zinc-800/40 border border-zinc-700/30 hover:bg-zinc-800/60 transition-colors cursor-pointer';

        // 选项图标
        const icon = document.createElement('span');
        icon.className = 'text-violet-400/70 mt-0.5 flex-shrink-0 text-sm';
        icon.textContent = multiSelect ? '☑️' : '⬜';

        // 内容容器
        const content = document.createElement('div');
        content.className = 'min-w-0 flex-1';

        // 标签
        const label = document.createElement('div');
        label.className = 'text-xs font-medium text-zinc-200';
        label.textContent = option.label || '';

        content.appendChild(label);

        // 描述
        if (option.description) {
            const desc = document.createElement('div');
            desc.className = 'text-xs text-zinc-500 mt-0.5';
            desc.textContent = option.description;
            content.appendChild(desc);
        }

        // Markdown 预览（可选）
        if (option.markdown && MarkdownRenderer.isAvailable()) {
            const preview = document.createElement('div');
            preview.className = 'mt-1.5 p-2 bg-zinc-900/50 rounded border border-zinc-700/30';
            MarkdownRenderer.render(option.markdown, preview, {
                className: 'option-markdown-preview'
            });
            content.appendChild(preview);
        }

        wrapper.appendChild(icon);
        wrapper.appendChild(content);

        return wrapper;
    }
};

// 默认导出
export default AskQuestionRenderer;
