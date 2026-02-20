/**
 * 消息渲染模块
 * 处理历史消息和实时消息的渲染
 */

const MessageRenderer = {
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
        roundEl.className = 'conversation-round';
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
            switch (block.type) {
                case 'text':
                    return this._renderTextBlock(block);
                case 'thinking':
                    return this._renderThinkingBlock(block);
                case 'tool_use':
                    return this._renderToolUseBlock(block);
                case 'tool_result':
                    return this._renderToolResultBlock(block);
                default:
                    return '';
            }
        }).join('');
    },

    /**
     * 渲染文本块
     * @param {Object} block - 文本块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderTextBlock(block) {
        const timeStr = Utils.formatTime(block.timestamp);
        return `
            <div class="assistant-msg assistant-msg-text">
                <span class="timestamp">${timeStr}</span>
                <div class="content">${Utils.escapeHtml(block.text || '')}</div>
            </div>
        `;
    },

    /**
     * 渲染思考块（可折叠）
     * @param {Object} block - 思考块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderThinkingBlock(block) {
        const thinking = block.thinking || '';
        if (!thinking) return '';

        const timeStr = Utils.formatTime(block.timestamp);
        const preview = thinking.substring(0, 100) + (thinking.length > 100 ? '...' : '');

        return `
            <div class="assistant-msg assistant-msg-thinking">
                <div class="thinking-header" onclick="this.parentElement.classList.toggle('expanded')">
                    <span class="timestamp">${timeStr}</span>
                    <span class="thinking-icon">💭</span>
                    <span class="thinking-title">思考过程</span>
                    <span class="thinking-toggle">▶</span>
                </div>
                <div class="thinking-preview">${Utils.escapeHtml(preview)}</div>
                <div class="thinking-content">${Utils.escapeHtml(thinking)}</div>
            </div>
        `;
    },

    /**
     * 渲染工具调用块
     * @param {Object} block - 工具调用块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderToolUseBlock(block) {
        const timeStr = Utils.formatTime(block.timestamp);
        const toolName = block.tool_name || 'Unknown';
        const toolInput = block.tool_input || {};
        const inputJson = JSON.stringify(toolInput, null, 2);

        return `
            <div class="assistant-msg assistant-msg-tool_use">
                <span class="timestamp">${timeStr}</span>
                <div class="tool-header">
                    <span class="tool-icon">🔧</span>
                    <span class="tool-name">${Utils.escapeHtml(toolName)}</span>
                </div>
                <div class="tool-input">
                    <pre>${Utils.escapeHtml(inputJson)}</pre>
                </div>
            </div>
        `;
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
     * 渲染工具结果块
     * @param {Object} block - 工具结果块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderToolResultBlock(block) {
        const isError = block.is_error;
        const toolName = block.tool_name || '';
        const content = block.content || '';

        // 获取工具对应的样式配置
        const style = this._getToolResultStyle(toolName);

        // 截断过长的结果
        const displayContent = Utils.truncateText(content, style.maxLength);

        // 根据工具类型选择不同的渲染模板
        return this._renderToolResultByType(toolName, style, isError, displayContent, content);
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
        const hasMore = displayContent.length < fullContent.length;

        return `
            <div class="${baseClass}">
                <span class="result-label">${label}</span>
                <div class="result-content">
                    <pre>${Utils.escapeHtml(displayContent)}</pre>
                    ${hasMore ? '<div class="result-truncated">... 内容过长，已截断</div>' : ''}
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Read 工具结果（代码风格）
     */
    _renderReadResult(baseClass, style, isError, displayContent, fullContent) {
        const hasMore = displayContent.length < fullContent.length;
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
                    ${hasMore ? '<div class="result-truncated">... 内容过长，已截断</div>' : ''}
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Bash 工具结果（终端风格）
     */
    _renderBashResult(baseClass, style, isError, displayContent, fullContent) {
        const hasMore = displayContent.length < fullContent.length;
        const prompt = isError ? '$' : '❯';

        return `
            <div class="${baseClass}">
                <span class="result-label">${style.icon} ${style.label}</span>
                <div class="result-content terminal-block">
                    <div class="terminal-prompt"><span class="prompt-symbol">❯</span> bash</div>
                    <pre class="terminal-output">${Utils.escapeHtml(displayContent)}</pre>
                    ${hasMore ? '<div class="result-truncated">... 内容过长，已截断</div>' : ''}
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Grep 工具结果（搜索结果风格）
     */
    _renderGrepResult(baseClass, style, isError, displayContent, fullContent) {
        const hasMore = displayContent.length < fullContent.length;
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
                    ${hasMore ? '<div class="result-truncated">... 内容过长，已截断</div>' : ''}
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Glob 工具结果（文件列表风格）
     */
    _renderGlobResult(baseClass, style, isError, displayContent, fullContent) {
        const hasMore = displayContent.length < fullContent.length;
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
                    ${hasMore ? '<div class="result-truncated">... 内容过长，已截断</div>' : ''}
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
        msgEl.className = `assistant-msg assistant-msg-${type}`;

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
