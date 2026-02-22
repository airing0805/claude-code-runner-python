/**
 * 消息渲染模块
 * 处理历史消息和实时消息的渲染
 *
 * v0.5.3.6: 完善工具渲染器集成
 * v0.5.4: 消息渲染增强 - 内容截断、动画、思考块、工具图标/预览系统
 */

const MessageRenderer = {
    /**
     * 内容截断配置
     */
    _truncationConfig: {
        maxLines: 30,           // 默认显示行数
        maxChars: 5000,         // 默认最大字符数
        previewLines: 3,        // 预览行数
    },

    /**
     * 自动展开的工具类型
     */
    _autoExpandTools: ['todowrite', 'askuserquestion', 'task'],

    /**
     * 检查工具渲染器是否可用
     * @returns {boolean}
     */
    _isToolRenderersAvailable() {
        return typeof window.ToolRenderers !== 'undefined';
    },

    /**
     * 检查工具图标系统是否可用
     * @returns {boolean}
     */
    _isToolIconsAvailable() {
        return typeof window.ToolIcons !== 'undefined';
    },

    /**
     * 检查工具预览系统是否可用
     * @returns {boolean}
     */
    _isToolPreviewAvailable() {
        return typeof window.ToolPreview !== 'undefined';
    },

    /**
     * 获取工具图标
     * @param {string} toolName - 工具名称
     * @returns {string} 图标
     */
    _getToolIcon(toolName) {
        if (this._isToolIconsAvailable()) {
            return window.ToolIcons.getToolIcon(toolName);
        }
        // 回退到默认图标
        return '🔧';
    },

    /**
     * 获取工具预览文本
     * @param {string} toolName - 工具名称
     * @param {Object} input - 工具输入
     * @returns {string|null} 预览文本
     */
    _getToolPreview(toolName, input) {
        if (this._isToolPreviewAvailable()) {
            return window.ToolPreview.getToolPreview(toolName, input);
        }
        return null;
    },

    /**
     * 规范化工具名称（首字母大写）
     * v0.5.3.6: 确保与注册表中的名称一致
     * @param {string} toolName - 原始工具名称
     * @returns {string} 规范化后的名称
     */
    _normalizeToolName(toolName) {
        if (!toolName) return '';
        // 处理特殊工具名称
        const specialNames = {
            'todowrite': 'TodoWrite',
            'askuserquestion': 'AskUserQuestion',
            'websearch': 'WebSearch',
            'webfetch': 'WebFetch',
        };
        const lowerName = toolName.toLowerCase();
        if (specialNames[lowerName]) {
            return specialNames[lowerName];
        }
        // 默认首字母大写
        return toolName.charAt(0).toUpperCase() + toolName.slice(1);
    },

    /**
     * 显示历史消息
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Array} messages - 消息数组
     */
    displayHistoryMessages(runner, messages) {
        // 清空输出区并显示历史消息
        runner.outputEl.innerHTML = '';
        runner.currentRoundEl = null;
        runner.roundCounter = 0;

        if (messages.length === 0) {
            runner.outputEl.innerHTML = '<div class="output-placeholder">暂无历史消息</div>';
            return;
        }

        // 按轮次分组消息
        const rounds = this._groupByRounds(messages);

        rounds.forEach((round, index) => {
            const roundEl = this._createRoundElement(runner, round, index + 1);
            runner.outputEl.appendChild(roundEl);
        });

        // 更新轮次计数器
        runner.roundCounter = rounds.length;

        // 滚动到底部
        Utils.scrollToBottom(runner.outputEl);
    },

    /**
     * 按轮次分组消息
     * 基于 permissionMode 判断新的对话轮次
     * @param {Array} messages - 消息数组
     * @returns {Array} 分组后的轮次数组
     */
    _groupByRounds(messages) {
        const rounds = [];
        let currentRound = null;

        messages.forEach(msg => {
            if (msg.role === 'user') {
                // 1. permissionMode 存在 = 新会话（最可靠）
                if (msg.permissionMode) {
                    currentRound = { user: msg, assistant: [] };
                    rounds.push(currentRound);
                }
                // 2. 检查是否为 tool_result（继续当前对话）
                else if (Utils.isToolResult(msg)) {
                    if (currentRound) {
                        currentRound.assistant.push(msg);
                    } else {
                        // 没有当前轮次，作为新轮次处理
                        currentRound = { user: msg, assistant: [] };
                        rounds.push(currentRound);
                    }
                }
                // 3. 其他情况作为新轮次
                else {
                    currentRound = { user: msg, assistant: [] };
                    rounds.push(currentRound);
                }
            } else if (currentRound && msg.role === 'assistant') {
                currentRound.assistant.push(msg);
            }
        });

        return rounds;
    },

    /**
     * 创建对话轮次元素
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} round - 轮次数据
     * @param {number} roundNumber - 轮次编号
     * @returns {HTMLElement} 轮次 DOM 元素
     */
    _createRoundElement(runner, round, roundNumber) {
        const roundEl = document.createElement('div');
        roundEl.className = 'conversation-round message-fade-in';
        roundEl.id = `round-${roundNumber}`;

        // 渲染用户消息
        const userContent = this._renderUserContent(round.user);
        // 渲染 AI 响应
        const assistantContent = this._renderAssistantMessages(round.assistant);

        roundEl.innerHTML = `
            <div class="round-header">
                <span class="round-number">第 ${roundNumber} 轮</span>
            </div>
            <div class="round-user">
                <div class="message-role user-role">👤 用户</div>
                <div class="message-content user-content">${userContent}</div>
            </div>
            <div class="round-assistant">
                <div class="message-role assistant-role">🤖 Claude</div>
                <div class="assistant-messages">${assistantContent}</div>
            </div>
        `;

        return roundEl;
    },

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
                    return this._renderToolResultBlock(block);
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
                return this._renderThinkingBlock(block);
            case 'tool_use':
                return this._renderToolUseBlock(block);
            case 'tool_result':
                return this._renderToolResultBlock(block);
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
        const needsTruncation = lines.length > this._truncationConfig.maxLines;

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
        const maxLines = this._truncationConfig.maxLines;
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
                <button class="content-expand-btn" onclick="MessageRenderer._toggleContentExpand('${blockId}', this, ${hiddenLines})">
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
    },

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
            <div class="thinking-block message-fade-in" id="${blockId}">
                <button class="tool-button tool-button-thinking" onclick="MessageRenderer._toggleThinking('${blockId}')">
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
    },

    /**
     * 渲染工具调用块（v0.5.4 增强 - 工具图标和预览系统）
     * @param {Object} block - 工具调用块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderToolUseBlock(block) {
        const rawToolName = block.tool_name || 'Unknown';
        const toolName = this._normalizeToolName(rawToolName);
        const toolInput = block.tool_input || {};
        const toolNameLower = rawToolName.toLowerCase();

        // v0.5.4: 获取工具图标和预览
        const toolIcon = this._getToolIcon(rawToolName);
        const toolPreview = this._getToolPreview(rawToolName, toolInput);

        // v0.5.4: 检查是否应该自动展开
        const shouldAutoExpand = this._autoExpandTools.some(t => toolNameLower.includes(t));

        // v0.5.4: 检查是否有专用渲染器
        const hasSpecialRenderer = this._isToolRenderersAvailable() &&
            window.ToolRenderers.hasInputRenderer(toolName);

        // 如果有专用渲染器且应该自动展开
        if (shouldAutoExpand && hasSpecialRenderer) {
            try {
                const renderedEl = window.ToolRenderers.renderInput(toolName, toolInput);
                if (renderedEl) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'assistant-msg assistant-msg-tool_use message-fade-in';
                    wrapper.innerHTML = `
                        <button class="tool-button tool-button-input expanded" onclick="this.classList.toggle('expanded')">
                            <span class="tool-button-icon">${toolIcon}</span>
                            <span class="tool-button-preview">${Utils.escapeHtml(rawToolName)}</span>
                            ${toolPreview ? `<span class="tool-button-preview">${Utils.escapeHtml(toolPreview)}</span>` : ''}
                        </button>
                        <div class="tool-content-expanded">
                    `;
                    wrapper.appendChild(renderedEl);
                    wrapper.innerHTML += '</div>';
                    return wrapper.outerHTML;
                }
            } catch (err) {
                console.warn(`ToolRenderer error for ${toolName}:`, err);
            }
        }

        // 生成唯一 ID
        const blockId = `tool-use-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

        // v0.5.4: 默认渲染为可折叠的工具按钮
        const hasInput = toolInput && Object.keys(toolInput).length > 0;

        return `
            <div class="assistant-msg assistant-msg-tool_use message-fade-in" id="${blockId}">
                <button class="tool-button tool-button-input ${shouldAutoExpand ? 'expanded' : ''}"
                        onclick="MessageRenderer._toggleToolUse('${blockId}', ${shouldAutoExpand})"
                        ${!hasInput ? 'disabled' : ''}>
                    <span class="tool-button-icon">${toolIcon}</span>
                    <span class="tool-button-preview">${Utils.escapeHtml(rawToolName)}</span>
                    ${toolPreview ? `<span class="tool-button-preview">${Utils.escapeHtml(toolPreview)}</span>` : ''}
                    ${hasInput && !shouldAutoExpand ? '<span class="tool-button-toggle">▶</span>' : ''}
                </button>
                <div class="tool-content-expanded" style="display: ${shouldAutoExpand && hasInput ? 'block' : 'none'};">
                    ${this._renderToolUseContent(toolName, toolInput, hasSpecialRenderer)}
                </div>
            </div>
        `;
    },

    /**
     * 渲染工具调用内容（v0.5.4）
     * @param {string} toolName - 规范化后的工具名称
     * @param {Object} toolInput - 工具输入
     * @param {boolean} hasSpecialRenderer - 是否有专用渲染器
     * @returns {string} 渲染后的 HTML
     */
    _renderToolUseContent(toolName, toolInput, hasSpecialRenderer) {
        if (hasSpecialRenderer) {
            try {
                const renderedEl = window.ToolRenderers.renderInput(toolName, toolInput);
                if (renderedEl) {
                    return renderedEl.outerHTML;
                }
            } catch (err) {
                console.warn(`ToolRenderer error for ${toolName}:`, err);
            }
        }

        // 默认 JSON 渲染
        const inputJson = JSON.stringify(toolInput, null, 2);
        return `<pre class="tool-input">${Utils.escapeHtml(inputJson)}</pre>`;
    },

    /**
     * 切换工具调用展开/收起（v0.5.4）
     * @param {string} blockId - 块元素 ID
     * @param {boolean} startExpanded - 初始是否展开
     */
    _toggleToolUse(blockId, startExpanded) {
        const block = document.getElementById(blockId);
        if (!block) return;

        const btn = block.querySelector('.tool-button');
        const content = block.querySelector('.tool-content-expanded');
        const toggle = btn.querySelector('.tool-button-toggle');

        if (!content) return;

        if (content.style.display === 'none') {
            content.style.display = 'block';
            btn.classList.add('expanded');
            if (toggle) toggle.textContent = '▼';
        } else {
            content.style.display = 'none';
            btn.classList.remove('expanded');
            if (toggle) toggle.textContent = '▶';
        }
    },

    /**
     * 工具结果样式配置
     */
    _toolResultStyles: {
        Read: {
            icon: '📄',
            class: 'tool-result-read',
            label: '文件内容',
            maxLength: 2000,
        },
        Write: {
            icon: '✍️',
            class: 'tool-result-write',
            label: '写入成功',
            maxLength: 500,
        },
        Edit: {
            icon: '✏️',
            class: 'tool-result-edit',
            label: '编辑成功',
            maxLength: 500,
        },
        Bash: {
            icon: '💻',
            class: 'tool-result-bash',
            label: '终端输出',
            maxLength: 3000,
        },
        Glob: {
            icon: '📁',
            class: 'tool-result-glob',
            label: '文件列表',
            maxLength: 1500,
        },
        Grep: {
            icon: '🔍',
            class: 'tool-result-grep',
            label: '搜索结果',
            maxLength: 2000,
        },
        WebSearch: {
            icon: '🌐',
            class: 'tool-result-web',
            label: '搜索结果',
            maxLength: 3000,
        },
        WebFetch: {
            icon: '📥',
            class: 'tool-result-web',
            label: '网页内容',
            maxLength: 5000,
        },
        Task: {
            icon: '🤖',
            class: 'tool-result-task',
            label: '子代理结果',
            maxLength: 2000,
        },
    },

    /**
     * 获取工具结果样式配置
     * @param {string} toolName - 工具名称
     * @returns {Object} 样式配置
     */
    _getToolResultStyle(toolName) {
        return this._toolResultStyles[toolName] || {
            icon: '🔧',
            class: 'tool-result-default',
            label: '结果',
            maxLength: 500,
        };
    },

    /**
     * 渲染工具结果块（v0.5.4 增强）
     * @param {Object} block - 工具结果块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderToolResultBlock(block) {
        const isError = block.is_error;
        const rawToolName = block.tool_name || '';
        const toolName = this._normalizeToolName(rawToolName);
        const content = block.content || '';

        // v0.5.4: 检查内容是否为空
        const hasContent = content && content.trim().length > 0;
        const contentPreview = hasContent ? content.slice(0, 60) + (content.length > 60 ? '...' : '') : null;

        // 生成唯一 ID
        const blockId = `tool-result-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

        // v0.5.4: 使用新的工具按钮样式
        const btnClass = isError ? 'tool-button-error' : 'tool-button-result';
        const icon = isError ? '❌' : '✅';
        const label = isError ? 'error' : 'result';

        // 如果没有内容，显示简洁的成功/错误状态
        if (!hasContent) {
            return `
                <div class="assistant-msg assistant-msg-tool_result message-fade-in">
                    <button class="tool-button ${btnClass}" disabled>
                        <span class="tool-button-icon">${icon}</span>
                        <span class="tool-button-preview">${label}</span>
                    </button>
                </div>
            `;
        }

        // v0.5.4: 尝试使用专用渲染器
        if (this._isToolRenderersAvailable() && window.ToolRenderers.hasResultRenderer(toolName)) {
            try {
                const options = {
                    content,
                    isError,
                    isFileList: toolName === 'Glob' || toolName.toLowerCase() === 'glob',
                    maxLines: 30,
                    maxChars: 5000
                };
                const renderedEl = window.ToolRenderers.renderResult(toolName, options);
                if (renderedEl) {
                    // 包装为可折叠的按钮
                    return `
                        <div class="assistant-msg assistant-msg-tool_result message-fade-in" id="${blockId}">
                            <button class="tool-button ${btnClass}" onclick="MessageRenderer._toggleToolResult('${blockId}')">
                                <span class="tool-button-icon">${icon}</span>
                                <span class="tool-button-preview">${label}</span>
                                ${contentPreview ? `<span class="tool-button-preview">${Utils.escapeHtml(contentPreview)}</span>` : ''}
                                <span class="tool-button-toggle">▶</span>
                            </button>
                            <div class="tool-content-expanded" style="display: none;">
                                ${renderedEl.outerHTML}
                            </div>
                        </div>
                    `;
                }
            } catch (err) {
                console.warn(`ToolRenderer error for ${toolName} result:`, err);
            }
        }

        // 获取工具对应的样式配置
        const style = this._getToolResultStyle(toolName);

        // 截断过长的结果
        const displayContent = Utils.truncateText(content, style.maxLength);
        const hasMore = displayContent.length < content.length;

        // 根据工具类型选择不同的渲染模板
        const resultContent = this._renderToolResultByType(toolName, style, isError, displayContent, content);

        return `
            <div class="assistant-msg assistant-msg-tool_result message-fade-in" id="${blockId}">
                <button class="tool-button ${btnClass}" onclick="MessageRenderer._toggleToolResult('${blockId}')">
                    <span class="tool-button-icon">${isError ? '❌' : style.icon}</span>
                    <span class="tool-button-preview">${isError ? 'error' : style.label}</span>
                    ${contentPreview ? `<span class="tool-button-preview">${Utils.escapeHtml(contentPreview)}</span>` : ''}
                    <span class="tool-button-toggle">▶</span>
                </button>
                <div class="tool-content-expanded" style="display: none;">
                    ${resultContent}
                    ${hasMore ? '<div class="result-truncated">... 内容过长，已截断</div>' : ''}
                </div>
            </div>
        `;
    },

    /**
     * 切换工具结果展开/收起（v0.5.4）
     * @param {string} blockId - 块元素 ID
     */
    _toggleToolResult(blockId) {
        const block = document.getElementById(blockId);
        if (!block) return;

        const btn = block.querySelector('.tool-button');
        const content = block.querySelector('.tool-content-expanded');
        const toggle = btn.querySelector('.tool-button-toggle');

        if (!content) return;

        if (content.style.display === 'none') {
            content.style.display = 'block';
            btn.classList.add('expanded');
            if (toggle) toggle.textContent = '▼';
        } else {
            content.style.display = 'none';
            btn.classList.remove('expanded');
            if (toggle) toggle.textContent = '▶';
        }
    },

    /**
     * 根据工具类型渲染结果
     * @param {string} toolName - 工具名称
     * @param {Object} style - 样式配置
     * @param {boolean} isError - 是否错误
     * @param {string} displayContent - 显示内容（已截断）
     * @param {string} fullContent - 完整内容
     * @returns {string} 渲染后的 HTML
     */
    _renderToolResultByType(toolName, style, isError, displayContent, fullContent) {
        const baseClass = isError ? 'assistant-msg-error' : `assistant-msg ${style.class}`;

        // 特殊处理：Read 工具显示代码行号
        if (toolName === 'Read') {
            return this._renderReadResult(baseClass, style, isError, displayContent, fullContent);
        }

        // 特殊处理：Bash 工具显示终端样式
        if (toolName === 'Bash') {
            return this._renderBashResult(baseClass, style, isError, displayContent, fullContent);
        }

        // 特殊处理：Grep 工具显示行号和高亮
        if (toolName === 'Grep') {
            return this._renderGrepResult(baseClass, style, isError, displayContent, fullContent);
        }

        // 特殊处理：Glob 工具显示文件列表
        if (toolName === 'Glob') {
            return this._renderGlobResult(baseClass, style, isError, displayContent, fullContent);
        }

        // 默认渲染
        const label = isError ? '❌ 错误' : `${style.icon} ${style.label}`;

        return `
            <div class="${baseClass}">
                <span class="result-label">${label}</span>
                <div class="result-content">
                    <pre>${Utils.escapeHtml(displayContent)}</pre>
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Read 工具结果（代码风格）
     */
    _renderReadResult(baseClass, style, isError, displayContent, fullContent) {
        const lines = displayContent.split('\n');

        const linesHtml = lines.map((line, index) => {
            const lineNum = index + 1;
            const lineClass = lineNum % 2 === 0 ? 'line-even' : 'line-odd';
            return `<div class="code-line ${lineClass}"><span class="line-number">${lineNum}</span><span class="line-content">${Utils.escapeHtml(line)}</span></div>`;
        }).join('');

        return `
            <div class="${baseClass}">
                <span class="result-label">${style.icon} ${style.label}</span>
                <div class="result-content code-block">
                    <div class="code-lines">${linesHtml}</div>
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Bash 工具结果（终端风格）
     */
    _renderBashResult(baseClass, style, isError, displayContent, fullContent) {
        return `
            <div class="${baseClass}">
                <span class="result-label">${style.icon} ${style.label}</span>
                <div class="result-content terminal-block">
                    <div class="terminal-prompt"><span class="prompt-symbol">❯</span> bash</div>
                    <pre class="terminal-output">${Utils.escapeHtml(displayContent)}</pre>
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Grep 工具结果（搜索结果风格）
     */
    _renderGrepResult(baseClass, style, isError, displayContent, fullContent) {
        const lines = displayContent.split('\n');

        const linesHtml = lines.map((line) => {
            // 匹配文件名:行号:内容的格式
            const match = line.match(/^([^:]+):(\d+):(.*)$/);
            if (match) {
                const [, file, lineNum, content] = match;
                return `<div class="grep-line"><span class="grep-file">${Utils.escapeHtml(file)}</span>:<span class="grep-line-num">${lineNum}</span>:<span class="grep-content">${Utils.escapeHtml(content)}</span></div>`;
            }
            return `<div class="grep-line"><span class="grep-content">${Utils.escapeHtml(line)}</span></div>`;
        }).join('');

        return `
            <div class="${baseClass}">
                <span class="result-label">${style.icon} ${style.label}</span>
                <div class="result-content grep-block">
                    <div class="grep-lines">${linesHtml}</div>
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Glob 工具结果（文件列表风格）
     */
    _renderGlobResult(baseClass, style, isError, displayContent, fullContent) {
        const files = displayContent.split('\n').filter(f => f.trim());

        const filesHtml = files.map(file => {
            const ext = file.split('.').pop() || '';
            const icon = this._getFileIcon(ext);
            return `<div class="file-item"><span class="file-icon">${icon}</span><span class="file-path">${Utils.escapeHtml(file)}</span></div>`;
        }).join('');

        return `
            <div class="${baseClass}">
                <span class="result-label">${style.icon} ${style.label} (${files.length} 个文件)</span>
                <div class="result-content files-block">
                    <div class="files-list">${filesHtml}</div>
                </div>
            </div>
        `;
    },

    /**
     * 获取文件图标
     */
    _getFileIcon(ext) {
        const iconMap = {
            js: '🟨',
            ts: '🔷',
            py: '🐍',
            json: '📋',
            md: '📝',
            html: '🌐',
            css: '🎨',
            txt: '📄',
            yml: '⚙️',
            yaml: '⚙️',
            toml: '⚙️',
            gitignore: '🔒',
            env: '🔐',
        };
        return iconMap[ext] || '📄';
    },

    /**
     * 添加助手消息到当前轮次
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} type - 消息类型
     * @param {string} content - 消息内容
     * @param {string|null} timestamp - 时间戳
     */
    addAssistantMessage(runner, type, content, timestamp = null) {
        if (!runner.currentRoundEl) {
            // 如果没有当前轮次，创建一个
            Task.startNewRound(runner, '(继续对话)');
        }

        const messagesContainer = runner.currentRoundEl.querySelector('.assistant-messages');

        const msgEl = document.createElement('div');
        msgEl.className = `assistant-msg assistant-msg-${type} message-fade-in`;

        const timeStr = Utils.formatTime(timestamp);
        msgEl.innerHTML = `
            <span class="timestamp">${timeStr}</span>
            <span class="content">${Utils.escapeHtml(content)}</span>
        `;

        messagesContainer.appendChild(msgEl);
        Utils.scrollToBottom(runner.outputEl);
    }
};

// 导出到全局命名空间
window.MessageRenderer = MessageRenderer;
