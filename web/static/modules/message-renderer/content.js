/**
 * 内容块渲染器模块
 * 处理各种内容块类型的渲染逻辑
 */

const MessageRendererContent = {
    /**
     * 渲染用户消息内容
     * @param {Object} message - 用户消息对象
     * @returns {string} 渲染后的 HTML
     */
    _renderUserContent(message) {
        if (!message.content || message.content.length === 0) {
            return '<span class="empty-content">(无内容)</span>';
        }

        return message.content.map(block => {
            switch (block.type) {
                case 'text':
                    return Utils.escapeHtml(block.text || '');
                case 'tool_result':
                    return MessageRendererTools._renderToolResultBlock(block);
                default:
                    return '';
            }
        }).join('');
    },

    /**
     * 渲染 AI 响应消息
     * @param {Array} messages - AI 消息数组
     * @returns {string} 渲染后的 HTML
     */
    _renderAssistantMessages(messages) {
        if (!messages || messages.length === 0) {
            return '';
        }

        // 合并所有消息的内容块
        const allBlocks = messages.flatMap(msg => {
            const blocks = msg.content || [];
            // 为每个块添加时间戳
            return blocks.map(block => ({ ...block, timestamp: msg.timestamp }));
        });

        return allBlocks.map(block => {
            return this._renderContentBlock(block, false);
        }).join('');
    },

    /**
     * 渲染内容块（v0.5.4 ContentBlockRenderer）
     * @param {Object} block - 内容块数据
     * @param {boolean} isUser - 是否为用户消息
     * @returns {string} 渲染后的 HTML
     */
    _renderContentBlock(block, isUser = false) {
        switch (block.type) {
            case 'text':
                return this._renderTextBlock(block, isUser);
            case 'thinking':
                return MessageRendererThinking._renderThinkingBlock(block);
            case 'tool_use':
                return MessageRendererTools._renderToolUseBlock(block);
            case 'tool_result':
                return MessageRendererTools._renderToolResultBlock(block);
            default:
                return '';
        }
    },

    /**
     * 渲染文本块
     * @param {Object} block - 文本块数据
     * @param {boolean} isUser - 是否为用户消息
     * @returns {string} 渲染后的 HTML
     */
    _renderTextBlock(block, isUser = false) {
        const timeStr = Utils.formatTime(block.timestamp);
        const text = block.text || '';

        // v0.5.4: 检查是否需要截断
        const lines = text.split('\n');
        const needsTruncation = lines.length > MessageRendererCore._truncationConfig.maxLines;

        if (needsTruncation) {
            return this._renderTruncatedText(timeStr, lines, isUser);
        }

        return `
            <div class="assistant-msg assistant-msg-text message-fade-in">
                <span class="timestamp">${timeStr}</span>
                <div class="content">${Utils.escapeHtml(text)}</div>
            </div>
        `;
    },

    /**
     * 渲染截断的文本块（v0.5.4）
     * @param {string} timeStr - 时间字符串
     * @param {Array} lines - 文本行数组
     * @param {boolean} isUser - 是否为用户消息
     * @returns {string} 渲染后的 HTML
     */
    _renderTruncatedText(timeStr, lines, isUser) {
        const maxLines = MessageRendererCore._truncationConfig.maxLines;
        const hiddenLines = lines.length - maxLines;
        const displayLines = lines.slice(0, maxLines);

        // 生成唯一 ID
        const blockId = `text-block-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

        const displayContent = displayLines.map(line => Utils.escapeHtml(line)).join('\n');

        return `
            <div class="assistant-msg assistant-msg-text message-fade-in" id="${blockId}">
                <span class="timestamp">${timeStr}</span>
                <div class="content content-collapsible collapsed">
                    <pre>${displayContent}</pre>
                </div>
                <div class="content-truncated-hint">
                    <span>... 还有 ${hiddenLines} 行</span>
                </div>
                <button class="content-expand-btn" onclick="MessageRendererContent._toggleContentExpand('${blockId}', this, ${hiddenLines})">
                    <span class="expand-icon">▼</span>
                    <span class="expand-text">展开更多</span>
                </button>
            </div>
        `;
    },

    /**
     * 切换内容展开/收起（v0.5.4）
     * @param {string} blockId - 块元素 ID
     * @param {HTMLElement} btn - 按钮元素
     * @param {number} hiddenLines - 隐藏的行数
     */
    _toggleContentExpand(blockId, btn, hiddenLines) {
        const block = document.getElementById(blockId);
        if (!block) return;

        const content = block.querySelector('.content-collapsible');
        const hint = block.querySelector('.content-truncated-hint');
        const expandText = btn.querySelector('.expand-text');

        if (content.classList.contains('collapsed')) {
            // 展开
            content.classList.remove('collapsed');
            content.classList.add('expanded');
            btn.classList.add('expanded');
            if (hint) hint.style.display = 'none';
            if (expandText) expandText.textContent = '收起';
        } else {
            // 收起
            content.classList.remove('expanded');
            content.classList.add('collapsed');
            btn.classList.remove('expanded');
            if (hint) hint.style.display = 'inline-flex';
            if (expandText) expandText.textContent = '展开更多';

            // 滚动到块顶部
            block.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
};

// 导出到全局命名空间
window.MessageRendererContent = MessageRendererContent;