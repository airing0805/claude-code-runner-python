/**
 * 思考块渲染器模块
 * 专门处理 AI 思考内容的渲染和交互
 */

const MessageRendererThinking = {
    /**
     * 渲染思考块（v0.5.4 增强 - 可折叠，amber 色调）
     * @param {Object} block - 思考块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderThinkingBlock(block) {
        const thinking = block.thinking || '';
        if (!thinking) return '';

        // 生成唯一 ID
        const blockId = `thinking-block-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

        return `
            <div class="assistant-msg assistant-msg-thinking message-fade-in message-thinking" id="${blockId}">
                <button class="tool-button tool-button-thinking" onclick="MessageRendererThinking._toggleThinking('${blockId}')">
                    <span class="tool-button-icon">💡</span>
                    <span class="tool-button-preview">thinking</span>
                    <span class="tool-button-toggle">▶</span>
                </button>
                <div class="thinking-block-content" style="display: none;">
                    ${Utils.escapeHtml(thinking)}
                </div>
            </div>
        `;
    },

    /**
     * 切换思考块展开/收起（v0.5.4）
     * @param {string} blockId - 块元素 ID
     */
    _toggleThinking(blockId) {
        const block = document.getElementById(blockId);
        if (!block) return;

        const content = block.querySelector('.thinking-block-content');
        const btn = block.querySelector('.tool-button');
        const toggle = btn.querySelector('.tool-button-toggle');

        if (content.style.display === 'none') {
            content.style.display = 'block';
            btn.classList.add('expanded');
            if (toggle) toggle.textContent = '▼';
        } else {
            content.style.display = 'none';
            btn.classList.remove('expanded');
            if (toggle) toggle.textContent = '▶';
        }
    }
};

// 导出到全局命名空间
window.MessageRendererThinking = MessageRendererThinking;