/**
 * TaskRenderer - 子任务渲染器
 * v0.5.3 - 工具渲染器重构
 */

import { BaseRenderer } from './base.js';

/**
 * Agent 颜色配置
 */
const AGENT_COLORS = {
    explore: { text: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/20' },
    plan: { text: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/20' },
    'claude-code-guide': { text: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
    'general-purpose': { text: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
    default: { text: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' }
};

/**
 * Task 工具渲染器
 * 显示子任务信息，包括 agent 类型、描述、prompt 等
 */
export const TaskRenderer = {
    /**
     * 获取 Agent 颜色配置
     * @param {string} agentType - Agent 类型
     * @returns {{ text: string, bg: string }}
     */
    getAgentColor(agentType) {
        const type = (agentType || '').toLowerCase();
        return AGENT_COLORS[type] || AGENT_COLORS.default;
    },

    /**
     * 渲染 Task 工具输入
     * @param {Object} input - 工具输入参数
     * @param {string} [input.description] - 任务描述
     * @param {string} input.prompt - 任务提示
     * @param {string} input.subagent_type - Agent 类型
     * @param {string} [input.model] - 模型
     * @param {boolean} [input.run_in_background] - 是否后台运行
     * @param {string} [input.resume] - 恢复的任务 ID
     * @returns {HTMLElement|null}
     */
    render(input) {
        if (!input) {
            return null;
        }

        const colors = this.getAgentColor(input.subagent_type);

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 创建卡片
        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 创建头部
        const header = this._createHeader(input, colors);
        card.appendChild(header);

        // 创建内容区域
        const contentEl = this._createContent(input, colors);
        card.appendChild(contentEl);

        container.appendChild(card);
        return container;
    },

    /**
     * 创建头部
     * @param {Object} input - 输入参数
     * @param {Object} colors - 颜色配置
     * @returns {HTMLElement}
     */
    _createHeader(input, colors) {
        const header = document.createElement('div');
        header.className = 'flex items-center gap-2 px-3 py-2 border-b border-zinc-700/50 bg-zinc-800/30';

        // Agent 图标
        const icon = document.createElement('span');
        icon.textContent = '🤖';
        icon.className = colors.text;

        // Agent 类型
        const typeEl = document.createElement('span');
        typeEl.className = `text-xs font-medium ${colors.text}`;
        typeEl.textContent = input.subagent_type || 'Agent';

        header.appendChild(icon);
        header.appendChild(typeEl);

        // 描述
        if (input.description) {
            const arrow = document.createElement('span');
            arrow.textContent = '→';
            arrow.className = 'text-zinc-600 text-xs';

            const descEl = document.createElement('span');
            descEl.className = 'text-xs text-zinc-400';
            descEl.textContent = input.description;

            header.appendChild(arrow);
            header.appendChild(descEl);
        }

        // 标签区域
        const tagsWrapper = document.createElement('div');
        tagsWrapper.className = 'flex items-center gap-1.5 ml-auto';

        // resume 标签
        if (input.resume) {
            tagsWrapper.appendChild(this._createTag('🔄 resume'));
        }

        // background 标签
        if (input.run_in_background) {
            tagsWrapper.appendChild(this._createTag('⏸️ background'));
        }

        // model 标签
        if (input.model) {
            tagsWrapper.appendChild(this._createTag(input.model));
        }

        if (tagsWrapper.children.length > 0) {
            header.appendChild(tagsWrapper);
        }

        return header;
    },

    /**
     * 创建标签
     * @param {string} text - 标签文本
     * @returns {HTMLElement}
     */
    _createTag(text) {
        const tag = document.createElement('span');
        tag.className = 'inline-flex items-center gap-1 text-[10px] text-zinc-500 bg-zinc-700/50 px-1.5 py-0.5 rounded';
        tag.textContent = text;
        return tag;
    },

    /**
     * 创建内容区域
     * @param {Object} input - 输入参数
     * @param {Object} colors - 颜色配置
     * @returns {HTMLElement}
     */
    _createContent(input, colors) {
        const contentEl = document.createElement('div');
        contentEl.className = 'p-3';

        // Prompt 容器
        const promptWrapper = document.createElement('div');
        promptWrapper.className = `flex items-start gap-2 px-3 py-2 rounded-lg border ${colors.bg}`;

        // 播放图标
        const playIcon = document.createElement('span');
        playIcon.textContent = '▶';
        playIcon.className = `${colors.text} mt-0.5 flex-shrink-0 text-xs`;

        // Prompt 文本
        const promptEl = document.createElement('p');
        promptEl.className = 'text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap';
        promptEl.textContent = input.prompt || '';

        promptWrapper.appendChild(playIcon);
        promptWrapper.appendChild(promptEl);
        contentEl.appendChild(promptWrapper);

        return contentEl;
    }
};

// 默认导出
export default TaskRenderer;
