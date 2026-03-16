/**
 * 核心消息渲染器模块
 * 处理基础的消息渲染逻辑、轮次管理
 *
 * v0.5.3.6: 完善工具渲染器集成
 * v0.5.4: 消息渲染增强 - 内容截断、动画,思考块、工具图标/预览系统
 * v9.0.1: 添加轮次折叠/展开状态管理
 */

const MessageRendererCore = {
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
    _autoExpandTools: ['todowrite', 'task'],

    /**
     * 轮次折叠状态存储 (按会话ID区分)
     */
    _collapseState: {},

    /**
     * 默认折叠状态(对于较旧的轮次)
     */
    _defaultCollapseOlderRounds: true,

    /**
     * 获取轮次折叠状态
     * @param {string} sessionId - 会话ID
     * @param {number} roundNumber - 轮次编号
     * @returns {boolean} 是否折叠
     */
    _getRoundCollapseState(sessionId, roundNumber) {
        const key = sessionId || 'default';
        if (!this._collapseState[key]) {
            // 默认:较新的轮次展开,较旧的轮次折叠
            return this._defaultCollapseOlderRounds && roundNumber > 1;
        }
        return this._collapseState[key][roundNumber] ?? (this._defaultCollapseOlderRounds && roundNumber > 1);
    },

    /**
     * 设置轮次折叠状态
     * @param {string} sessionId - 会话ID
     * @param {number} roundNumber - 轮次编号
     * @param {boolean} collapsed - 是否折叠
     */
    _setRoundCollapseState(sessionId, roundNumber, collapsed) {
        const key = sessionId || 'default';
        if (!this._collapseState[key]) {
            this._collapseState[key] = {};
        }
        this._collapseState[key][roundNumber] = collapsed;
    },

    /**
     * 保存折叠状态到本地存储
     * @param {string} sessionId - 会话ID
     */
    _saveCollapseState(sessionId) {
        try {
            const key = sessionId || 'default';
            if (this._collapseState[key]) {
                localStorage.setItem(`claude_round_collapse_${key}`, JSON.stringify(this._collapseState[key]));
            }
        } catch (error) {
            console.warn('[MessageRenderer] 保存折叠状态失败:', error);
        }
    },

    /**
     * 从本地存储加载折叠状态
     * @param {string} sessionId - 会话ID
     */
    _loadCollapseState(sessionId) {
        try {
            const key = sessionId || 'default';
            const saved = localStorage.getItem(`claude_round_collapse_${key}`);
            if (saved) {
                this._collapseState[key] = JSON.parse(saved);
            }
        } catch (error) {
            console.warn('[MessageRenderer] 加载折叠状态失败:', error);
        }
    },

    /**
     * 切换轮次折叠/展开状态
     * @param {string} roundId - 轮次元素ID
     */
    _toggleRoundCollapse(roundId) {
        const roundEl = document.getElementById(roundId);
        if (!roundEl) return;

        const content = roundEl.querySelector('.round-content');
        const toggle = roundEl.querySelector('.round-toggle-icon');

        const isCollapsed = roundEl.classList.contains('collapsed');

        if (isCollapsed) {
            // 展开
            roundEl.classList.remove('collapsed');
            if (content) content.style.display = '';
            if (toggle) toggle.textContent = '▼';
        } else {
            // 折叠
            roundEl.classList.add('collapsed');
            if (content) content.style.display = 'none';
            if (toggle) toggle.textContent = '▶';
        }

        // 保存状态
        const roundNumber = parseInt(roundId.replace('round-', ''));
        const runner = window.runner;
        if (runner && runner.currentSessionId) {
            this._setRoundCollapseState(runner.currentSessionId, roundNumber, !isCollapsed);
            this._saveCollapseState(runner.currentSessionId);
        }
    },

    /**
     * v12: 显示历史消息 (单会话模式)
     * 使用 runner.state.messages 作为消息源
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Array} messages - 消息数组
     */
    displayHistoryMessages(runner, messages) {
        console.log('[displayHistoryMessages] 开始渲染历史消息:', messages.length, '条消息');
        console.log('[displayHistoryMessages] 消息详情:', messages);

        // 使用 runner.state.sessionId 加载折叠状态
        const sessionId = runner.state.sessionId;
        this._loadCollapseState(sessionId);

        // 清空输出区并显示历史消息
        runner.outputEl.innerHTML = '';
        runner.currentRoundEl = null;
        runner.roundCounter = 0;

        if (!messages || messages.length === 0) {
            runner.outputEl.innerHTML = '<div class="output-placeholder">暂无历史消息</div>';
            return;
        }

        // 按轮次分组消息
        const rounds = this._groupByRounds(messages);
        console.log('[displayHistoryMessages] 分组后轮次数:', rounds.length);

        rounds.forEach((round, index) => {
            const roundEl = this._createRoundElement(runner, round, index + 1);
            runner.outputEl.appendChild(roundEl);
        });

        // 更新轮次计数器
        runner.roundCounter = rounds.length;
        console.log('[displayHistoryMessages] 渲染完成,共', rounds.length, '轮');

        // 滚动到底部
        Utils.scrollToBottom(runner.outputEl);
    },

    /**
     * @deprecated v12: 此方法已废弃, 请使用 displayHistoryMessages
     * 显示历史消息到指定tab
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} tabId - 目标tab ID
     * @param {Array} messages - 消息数组
     */
    displayHistoryMessagesToTab(runner, tabId, messages) {
        console.warn('[MessageRenderer] displayHistoryMessagesToTab 已废弃,请使用 displayHistoryMessages');
        // 直接调用新方法
        this.displayHistoryMessages(runner, messages);
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
            // 处理用户消息
            if (msg.role === 'user') {
                // 1. permissionMode 存在 = 新会话 (最可靠)
                if (msg.permissionMode) {
                    currentRound = { user: msg, assistant: [] };
                    rounds.push(currentRound);
                }
                // 2. 检查是否为工具结果 (包含 tool_result 内容块)
                // 只有当用户消息实际上包含工具结果内容时才继续当前对话
                else if (Utils.isToolResult(msg)) {
                    if (currentRound) {
                        // 将工具结果添加到当前轮次的助手消息中
                        currentRound.assistant.push(msg);
                    } else {
                        // 没有当前轮次,作为新轮次处理
                        currentRound = { user: msg, assistant: [] };
                        rounds.push(currentRound);
                    }
                }
                // 3. 其他情况作为新轮次
                else {
                    currentRound = { user: msg, assistant: [] };
                    rounds.push(currentRound);
                }
            }
            // 处理助手消息
            else if (msg.role === 'assistant') {
                if (currentRound) {
                    currentRound.assistant.push(msg);
                } else {
                    // 没有当前轮次 (这种情况不应该发生), 创建新轮次
                    currentRound = { user: { role: 'user', content: [] }, assistant: [msg] };
                    rounds.push(currentRound);
                }
            }
            // 处理其他类型的消息 (如工具结果, role 可能是 'tool' 或其他)
            else {
                if (currentRound) {
                    // 添加到当前轮次的助手消息中
                    currentRound.assistant.push(msg);
                }
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
        console.log('[_createRoundElement] 创建轮次', roundNumber, ':', round);

        const roundEl = document.createElement('div');
        roundEl.className = 'conversation-round message-fade-in';
        roundEl.id = `round-${roundNumber}`;

        // v12: 使用 runner.state.sessionId 获取折叠状态
        const sessionId = runner.state.sessionId;
        const isCollapsed = this._getRoundCollapseState(sessionId, roundNumber);

        // 渲染用户消息
        const userContent = MessageRendererContent._renderUserContent(round.user);
        console.log('[_createRoundElement] 用户内容渲染结果:', userContent);

        // 渲染 AI 响应
        const assistantContent = MessageRendererContent._renderAssistantMessages(round.assistant);
        console.log('[_createRoundElement] 助手内容渲染结果:', assistantContent);

        // v9.0.1: 添加折叠/展开功能
        const collapseIcon = isCollapsed ? '▶' : '▼';

        roundEl.innerHTML = `
            <div class="round-header">
                <button class="round-toggle" onclick="MessageRendererCore._toggleRoundCollapse('round-${roundNumber}')">
                    <span class="round-toggle-icon">${collapseIcon}</span>
                </button>
                <span class="round-number">第 ${roundNumber} 轮</span>
            </div>
            <div class="round-content" style="display: ${isCollapsed ? 'none' : ''};">
                <div class="round-user">
                    <div class="message-role user-role">👤 用户</div>
                    <div class="message-content user-content">${userContent}</div>
                </div>
                <div class="round-assistant">
                    <div class="message-role assistant-role">🤖 Claude</div>
                    <div class="assistant-messages">${assistantContent}</div>
                </div>
            </div>
        `;

        // 如果初始状态为折叠, 添加 collapsed 类
        if (isCollapsed) {
            roundEl.classList.add('collapsed');
        }


        return roundEl;
    },

    /**
     * v12: 添加助手消息到当前轮次 (单会话模式)
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} type - 消息类型
     * @param {string} content - 消息内容
     * @param {string|null} timestamp - 时间戳
     */
    addAssistantMessage(runner, type, content, timestamp = null) {
        // 确保有当前轮次
        if (!runner.currentRoundEl) {
            // 如果没有当前轮次, 创建一个
            Task.startNewRound(runner, '(继续对话)');
        }

        // 找到消息容器
        const messagesContainer = runner.currentRoundEl.querySelector('.assistant-messages');

        if (!messagesContainer) {
            console.warn('[addAssistantMessage] 未找到消息容器');
            return;
        }

        const msgEl = document.createElement('div');
        // 根据消息类型添加对应的CSS类名
        let messageClass = `assistant-msg assistant-msg-${type} message-fade-in`;
        if (type === 'text') {
            messageClass += ' message-text';
        } else if (type === 'thinking') {
            messageClass += ' message-thinking';
        } else if (type === 'tool_use') {
            messageClass += ' message-tool_use';
        } else if (type === 'tool_result') {
            messageClass += ' message-tool_result';
        } else if (type === 'error') {
            messageClass += ' message-error';
        } else if (type === 'complete') {
            messageClass += ' message-complete';
        } else if (type === 'info') {
            messageClass += ' message-info';
        } else if (type === 'ask_user_question') {
            messageClass += ' message-ask_user_question';
        }

        msgEl.className = messageClass;

        const timeStr = Utils.formatTime(timestamp);
        msgEl.innerHTML = `
            <span class="timestamp">${timeStr}</span>
            <span class="content">${Utils.escapeHtml(content)}</span>
        `;

        messagesContainer.appendChild(msgEl);

        // 同时保存消息到状态
        if (runner.state) {
            if (!runner.state.messages) {
                runner.state.messages = [];
            }
            runner.state.messages.push({
                role: 'assistant',
                type: type,
                content: content,
                timestamp: timestamp || new Date().toISOString()
            });
        }

        // 滚动到底部
        Utils.scrollToBottom(runner.outputEl);
    }
};


// 导出到全局命名空间
window.MessageRendererCore = MessageRendererCore;
