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
        console.log('[_renderUserContent] 渲染用户消息:', message);

        if (!message.content || message.content.length === 0) {
            console.log('[_renderUserContent] 无内容，返回占位符');
            return '<span class="empty-content">(无内容)</span>';
        }

        console.log('[_renderUserContent] 内容块数量:', message.content.length);

        const result = message.content.map(block => {
            console.log('[_renderUserContent] 处理内容块:', block.type, block);
            switch (block.type) {
                case 'text':
                    return Utils.escapeHtml(block.text || '');
                case 'tool_result':
                    return MessageRendererTools._renderToolResultBlock(block);
                default:
                    console.warn('[_renderUserContent] 未知内容块类型:', block.type);
                    return '';
            }
        }).join('');

        console.log('[_renderUserContent] 渲染结果长度:', result.length);
        return result;
    },

    /**
     * 渲染 AI 响应消息
     * @param {Array} messages - AI 消息数组
     * @returns {string} 渲染后的 HTML
     */
    _renderAssistantMessages(messages) {
        console.log('[_renderAssistantMessages] 渲染助手消息:', messages.length, '条');

        if (!messages || messages.length === 0) {
            console.log('[_renderAssistantMessages] 无消息，返回空字符串');
            return '';
        }

        // 合并所有消息的内容块
        const allBlocks = messages.flatMap(msg => {
            const blocks = msg.content || [];
            console.log('[_renderAssistantMessages] 消息内容块数量:', blocks.length);
            // 为每个块添加时间戳
            return blocks.map(block => ({ ...block, timestamp: msg.timestamp }));
        });

        console.log('[_renderAssistantMessages] 总内容块数量:', allBlocks.length);

        const result = allBlocks.map(block => {
            console.log('[_renderAssistantMessages] 处理内容块:', block.type, block);
            return this._renderContentBlock(block, false);
        }).join('');

        console.log('[_renderAssistantMessages] 渲染结果长度:', result.length);
        return result;
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
            case 'complete':
                return this._renderCompleteBlock(block);
            case 'info':
                return this._renderInfoBlock(block);
            case 'ask_user_question':
                return this._renderAskUserQuestionBlock(block);
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

        // text 类型默认不显示时间戳（避免频繁更新造成视觉干扰）
        const showTimestamp = false;

        if (needsTruncation) {
            return this._renderTruncatedText(timeStr, lines, isUser, showTimestamp);
        }

        if (showTimestamp) {
            return `
                <div class="assistant-msg assistant-msg-text message-fade-in message-text">
                    <span class="timestamp">${timeStr}</span>
                    <div class="content">${Utils.escapeHtml(text)}</div>
                </div>
            `;
        } else {
            return `
                <div class="assistant-msg assistant-msg-text message-fade-in message-text">
                    <div class="content">${Utils.escapeHtml(text)}</div>
                </div>
            `;
        }
    },

    /**
     * 渲染截断的文本块（v0.5.4）
     * @param {string} timeStr - 时间字符串
     * @param {Array} lines - 文本行数组
     * @param {boolean} isUser - 是否为用户消息
     * @param {boolean} showTimestamp - 是否显示时间戳
     * @returns {string} 渲染后的 HTML
     */
    _renderTruncatedText(timeStr, lines, isUser, showTimestamp = false) {
        const maxLines = MessageRendererCore._truncationConfig.maxLines;
        const hiddenLines = lines.length - maxLines;
        const displayLines = lines.slice(0, maxLines);

        // 生成唯一 ID
        const blockId = `text-block-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

        const displayContent = displayLines.map(line => Utils.escapeHtml(line)).join('\n');

        if (showTimestamp) {
            return `
                <div class="assistant-msg assistant-msg-text message-fade-in message-text" id="${blockId}">
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
        } else {
            return `
                <div class="assistant-msg assistant-msg-text message-fade-in message-text" id="${blockId}">
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
        }
    },

    /**
     * 渲染完成消息块（PQ-011, PQ-012）
     * @param {Object} block - 完成消息块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderCompleteBlock(block) {
        const timeStr = Utils.formatTime(block.timestamp);
        const content = block.content || '任务完成';
        const metadata = block.metadata || {};
        
        // 获取 files_changed 和 tools_used
        const filesChanged = metadata.files_changed || [];
        const toolsUsed = metadata.tools_used || [];
        
        // 构建文件变更HTML
        let filesHtml = '';
        if (filesChanged.length > 0) {
            const fileItems = filesChanged.map(file => 
                `<div class="file-item" title="点击复制路径" onclick="Utils.copyToClipboard('${Utils.escapeHtml(file)}')">${Utils.escapeHtml(file)}</div>`
            ).join('');
            filesHtml = `
                <div class="complete-section">
                    <div class="complete-section-header">
                        <span class="section-title">📁 文件变更 (${filesChanged.length})</span>
                        <button class="copy-all-btn" onclick="Utils.copyToClipboard(${JSON.stringify(filesChanged.join('\\n'))})">
                            📋 复制全部
                        </button>
                    </div>
                    <div class="files-list">${fileItems}</div>
                </div>
            `;
        }
        
        // 构建工具使用HTML
        let toolsHtml = '';
        if (toolsUsed.length > 0) {
            const toolItems = toolsUsed.map(tool => {
                const toolName = tool.name || tool;
                const toolCount = tool.count || 1;
                const toolIcon = MessageRendererTools._getToolIcon(toolName.toLowerCase());
                return `<span class="tool-tag" title="${Utils.escapeHtml(toolName)}">${toolIcon} ${Utils.escapeHtml(toolName)}${toolCount > 1 ? ` (${toolCount})` : ''}</span>`;
            }).join('');
            toolsHtml = `
                <div class="complete-section">
                    <div class="complete-section-header">
                        <span class="section-title">🔧 工具使用 (${toolsUsed.length})</span>
                    </div>
                    <div class="tools-list">${toolItems}</div>
                </div>
            `;
        }
        
        // 统计信息
        const costUsd = metadata.cost_usd !== undefined ? metadata.cost_usd : null;
        const durationMs = metadata.duration_ms !== undefined ? metadata.duration_ms : null;
        let statsHtml = '';
        if (costUsd !== null || durationMs !== null) {
            const costStr = costUsd !== null ? `$${costUsd.toFixed(4)}` : '';
            const durationStr = durationMs !== null ? `${durationMs}ms` : '';
            const statsItems = [];
            if (costStr) statsItems.push(`费用: ${costStr}`);
            if (durationStr) statsItems.push(`耗时: ${durationStr}`);
            if (statsItems.length > 0) {
                statsHtml = `<div class="complete-stats">${statsItems.join(' • ')}</div>`;
            }
        }

        return `
            <div class="assistant-msg assistant-msg-complete message-fade-in message-complete">
                <span class="timestamp">${timeStr}</span>
                <div class="complete-content">
                    <div class="complete-message">${Utils.escapeHtml(content)}</div>
                    ${statsHtml}
                    ${toolsHtml}
                    ${filesHtml}
                </div>
            </div>
        `;
    },

    /**
     * 渲染信息消息块
     * @param {Object} block - 信息消息块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderInfoBlock(block) {
        const timeStr = Utils.formatTime(block.timestamp);
        const content = block.content || '';
        return `
            <div class="assistant-msg assistant-msg-info message-fade-in message-info">
                <span class="timestamp">${timeStr}</span>
                <div class="content">${Utils.escapeHtml(content)}</div>
            </div>
        `;
    },

    /**
     * 渲染用户问答消息块
     * @param {Object} block - 用户问答消息块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderAskUserQuestionBlock(block) {
        const timeStr = Utils.formatTime(block.timestamp);
        const content = block.content || '等待用户回答...';
        return `
            <div class="assistant-msg assistant-msg-ask_user_question message-fade-in message-ask-question">
                <span class="timestamp">${timeStr}</span>
                <div class="content">${Utils.escapeHtml(content)}</div>
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