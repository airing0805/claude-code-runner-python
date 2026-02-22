/**
 * 核心消息渲染器模块
 * 处理基础的消息渲染逻辑和轮次管理
 *
 * v0.5.3.6: 完善工具渲染器集成
 * v0.5.4: 消息渲染增强 - 内容截断、动画、思考块、工具图标/预览系统
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
    _autoExpandTools: ['todowrite', 'askuserquestion', 'task'],

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
        const userContent = MessageRendererContent._renderUserContent(round.user);
        // 渲染 AI 响应
        const assistantContent = MessageRendererContent._renderAssistantMessages(round.assistant);

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
window.MessageRendererCore = MessageRendererCore;