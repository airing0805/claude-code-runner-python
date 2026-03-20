/**
 * Task 对象 v12
 * 处理任务执行、SSE 流式输出、状态管理
 */

/**
 * 全局 Task 对象
 * 注意：app.js 中通过 Task.runTask(this) 调用
 */
const Task = {
    // SSE 连接状态
    _eventSource: null,
    _isStreaming: false,
    _currentSessionId: null,

    /**
     * 执行任务 (SSE 流式输出)
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    async runTask(runner) {
        console.log('[Task] runTask 开始执行');

        // 检查是否正在执行
        if (this._isStreaming) {
            console.warn('[Task] 任务正在执行中，忽略重复请求');
            return;
        }

        // 获取输入
        const promptInput = document.getElementById('prompt');
        const prompt = promptInput?.value?.trim();

        if (!prompt) {
            this.addMessage(runner, 'error', '请输入任务描述');
            return;
        }

        // 获取工作目录
        const workingDir = runner.workspaceCombo?.getValue?.() ||
                          runner.workingDirInput?.value ||
                          '.';

        // 获取工具列表
        const selectedTools = this.getSelectedTools(runner);

        // 获取权限模式
        const permissionMode = document.getElementById('permission-mode')?.value || 'default';

        // 获取 resume 参数
        let resume = runner.resumeInput?.value?.trim() || null;
        const continueConversation = runner.continueConversationCheckbox?.checked || false;

        // v12.0.0.6: 修复会话逻辑
        // 1. 如果用户通过历史会话下拉选择了会话，则恢复该会话 (historySessionSelected 有值)
        // 2. 如果用户勾选了"继续会话"，则恢复最近的会话 (continueConversation=true)
        // 3. 如果用户没有选择历史会话，也没有勾选"继续会话"，则创建新会话

        // 检查用户是否通过历史会话下拉明确选择了会话
        const historySessionSelected = runner.state?.historySessionSelected;

        // 判断是否应该恢复会话：
        // - 用户勾选了"继续会话" (continueConversation=true)
        // - 或者用户通过历史会话下拉明确选择了会话 (historySessionSelected 有值)
        const shouldResumeSession = continueConversation || historySessionSelected;

        // 如果不应该恢复会话，清空 resume 参数
        if (!shouldResumeSession) {
            resume = null;
        }

        // 创建新会话的条件：
        // - 没有勾选"继续会话"
        // - 没有通过历史会话下拉选择会话
        // - 没有 resume 值
        const newSession = !continueConversation && !historySessionSelected && !resume;

        // 设置流式传输标志（防止重复请求）
        this._isStreaming = true;

        // 更新 runner 状态
        runner.state.isStreaming = true;
        runner.state.sessionStatus = 'running';
        TaskModule.updateIsStreamingState(runner, true);

        // 更新 UI
        this._updateUI(runner, { isRunning: true, prompt });

        try {
            // 发起 SSE 请求，使用 AbortController 实现超时控制
            this._abortController = new AbortController();
            const timeoutId = setTimeout(() => {
                if (this._abortController) {
                    this._abortController.abort();
                    console.error('[Task] 请求超时');
                }
            }, 300000); // 5分钟超时

            const response = await fetch('/api/task/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt,
                    working_dir: workingDir,
                    tools: selectedTools,
                    permission_mode: permissionMode,
                    resume,
                    continue_conversation: continueConversation,
                    new_session: newSession,
                }),
                signal: this._abortController.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorText = await response.text().catch(() => '未知错误');
                throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
            }

            // 验证 Content-Type
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('text/event-stream')) {
                console.warn('[Task] 无效 Content-Type:', contentType);
                // 如果不是 SSE，可能是错误响应
                if (contentType && contentType.includes('application/json')) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || errorData.message || '服务器返回错误');
                }
            }

            // 处理 SSE 流
            await this._processStream(runner, response);

        } catch (error) {
            console.error('[Task] 执行任务失败:', error);
            this.addMessage(runner, 'error', `执行失败: ${error.message}`);
            this._updateUI(runner, { isRunning: false, error: true });
        } finally {
            runner.state.isStreaming = false;
            TaskModule.updateIsStreamingState(runner, false);
            this._isStreaming = false;
            // 确保 UI 状态被重置（防止 promptInput 一直保持 disabled 状态）
            this._updateUI(runner, { isRunning: false });
        }
    },

    /**
     * 停止任务执行
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    async stopTask(runner) {
        console.log('[Task] stopTask 被调用');

        if (this._eventSource) {
            this._eventSource.close();
            this._eventSource = null;
        }

        this._isStreaming = false;
        runner.state.isStreaming = false;
        TaskModule.updateIsStreamingState(runner, false);

        // 发送停止信号到后端
        if (this._currentSessionId) {
            try {
                await fetch(`/api/task/session/${this._currentSessionId}/stop`, {
                    method: 'POST',
                });
            } catch (e) {
                console.warn('[Task] 停止会话请求失败:', e);
            }
        }

        this._updateUI(runner, { isRunning: false });
        this.addMessage(runner, 'info', '任务已停止');
    },

    /**
     * 清空输出区域
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    clearOutput(runner) {
        console.log('[Task] clearOutput 清空输出');

        // 清空输出容器
        const outputContainer = this._getOutputContainer(runner);
        if (outputContainer) {
            outputContainer.innerHTML = '';
        }

        // 重置轮次计数器
        runner.currentRoundEl = null;
        runner.roundCounter = 0;

        // 重置状态
        runner.state.messages = [];
        runner.state.sessionId = null;
        runner.state.sessionStatus = 'new';

        // 更新 UI
        this._updateUI(runner, { isRunning: false, hasOutput: false });
    },

    /**
     * 手动重连
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    manualReconnect(runner) {
        console.log('[Task] manualReconnect 手动重连');
        // 如果有当前会话 ID，可以尝试重新连接
        if (this._currentSessionId) {
            this.addMessage(runner, 'info', '正在重新连接...');
            // TODO: 实现重连逻辑
        } else {
            this.addMessage(runner, 'info', '没有可重连的会话');
        }
    },

    /**
     * 添加消息到输出区域
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} type - 消息类型 (text, thinking, tool_use, tool_result, error, complete, info)
     * @param {string} content - 消息内容
     * @param {Object} extra - 额外数据
     */
    addMessage(runner, type, content, extra = {}) {
        const outputContainer = this._getOutputContainer(runner);
        if (!outputContainer) return;

        // 确保有当前轮次
        if (!runner.currentRoundEl) {
            this.startNewRound(runner, '(新任务)');
        }

        // 根据消息类型确定 CSS 类名
        let messageClass = `assistant-msg assistant-msg-${type} message-fade-in`;
        if (type === 'thinking') {
            messageClass += ' message-thinking';
        } else if (type === 'tool_use') {
            messageClass += ' message-tool_use';
        } else if (type === 'tool_result') {
            messageClass += ' message-tool_result';
            // 如果 is_error 为 true，添加错误样式
            if (extra.is_error) {
                messageClass += ' message-error';
            }
        } else if (type === 'error') {
            messageClass += ' message-error';
        } else if (type === 'complete') {
            messageClass += ' message-complete';
        } else if (type === 'info') {
            messageClass += ' message-info';
        } else if (type === 'ask_user_question') {
            messageClass += ' message-ask-question';
        }

        // 创建消息元素
        const msgEl = document.createElement('div');
        msgEl.className = messageClass;

        // 根据消息类型决定是否显示时间戳
        // text 和 thinking 类型不显示时间戳（实时流式消息，避免频繁更新造成视觉干扰）
        const showTimestamp = type !== 'text' && type !== 'thinking';
        const timeStr = extra.timestamp ? Utils.formatTime(extra.timestamp) : Utils.formatTime(new Date().toISOString());

        // 处理工具调用显示
        let toolInfo = '';
        if (extra.tool_name) {
            toolInfo = `<span class="tool-name">[${extra.tool_name}]</span> `;
        }

        // 根据是否显示时间戳构建不同的 HTML 结构
        if (showTimestamp) {
            msgEl.innerHTML = `
                <span class="timestamp">${timeStr}</span>
                <span class="content">${toolInfo}${Utils.escapeHtml(content)}</span>
            `;
        } else {
            msgEl.innerHTML = `
                <span class="content">${toolInfo}${Utils.escapeHtml(content)}</span>
            `;
        }

        // 添加到消息容器
        const messagesContainer = runner.currentRoundEl?.querySelector('.assistant-messages');
        if (messagesContainer) {
            messagesContainer.appendChild(msgEl);
        } else {
            outputContainer.appendChild(msgEl);
        }

        // 滚动到底部
        Utils.scrollToBottom(outputContainer);

        // 保存消息到状态
        if (runner.state) {
            if (!runner.state.messages) {
                runner.state.messages = [];
            }
            runner.state.messages.push({
                role: 'assistant',
                type,
                content,
                timestamp: extra.timestamp || new Date().toISOString(),
                ...extra,
            });
        }
    },

    /**
     * 开始新轮次
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} title - 轮次标题
     */
    startNewRound(runner, title) {
        const outputContainer = this._getOutputContainer(runner);
        if (!outputContainer) return;

        runner.roundCounter++;
        const roundNumber = runner.roundCounter;

        const roundEl = document.createElement('div');
        roundEl.className = 'conversation-round message-fade-in';
        roundEl.id = `round-${roundNumber}`;

        roundEl.innerHTML = `
            <div class="round-header">
                <button class="round-toggle" onclick="MessageRendererCore._toggleRoundCollapse('round-${roundNumber}')">
                    <span class="round-toggle-icon">▼</span>
                </button>
                <span class="round-number">第 ${roundNumber} 轮 ${title || ''}</span>
            </div>
            <div class="round-content">
                <div class="round-user" style="display: none;">
                    <div class="message-role user-role">👤 用户</div>
                    <div class="message-content user-content"></div>
                </div>
                <div class="round-assistant">
                    <div class="message-role assistant-role">🤖 Claude</div>
                    <div class="assistant-messages"></div>
                </div>
            </div>
        `;

        outputContainer.appendChild(roundEl);
        runner.currentRoundEl = roundEl;

        // 滚动到底部
        Utils.scrollToBottom(outputContainer);

        return roundEl;
    },

    /**
     * 获取选中的工具列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @returns {Array} 选中的工具名称数组
     */
    getSelectedTools(runner) {
        const selectedTools = [];

        if (runner.availableTools) {
            runner.availableTools.forEach(tool => {
                if (tool.selected !== false) {
                    selectedTools.push(tool.name);
                }
            });
        }

        return selectedTools;
    },

    /**
     * 处理 SSE 流
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Response} response - Fetch 响应对象
     */
    async _processStream(runner, response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        runner.reader = reader;

        // 确保有输出容器
        const outputContainer = this._getOutputContainer(runner);
        if (!runner.currentRoundEl && outputContainer) {
            this.startNewRound(runner, '');
        }

        try {
            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // 处理缓冲区的行
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        try {
                            const msg = JSON.parse(data);
                            await this._handleStreamMessage(runner, msg);
                        } catch (e) {
                            console.warn('[Task] 解析 SSE 消息失败:', e, data);
                        }
                    }
                }
            }
        } finally {
            runner.reader = null;
        }
    },

    /**
     * 处理 SSE 消息
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} msg - 消息对象
     */
    async _handleStreamMessage(runner, msg) {
        // 更新会话 ID
        if (msg.session_id) {
            this._currentSessionId = msg.session_id;
            runner.state.sessionId = msg.session_id;
            // 安全地更新 resumeInput
            if (runner.resumeInput) {
                runner.resumeInput.value = msg.session_id;
                runner.resumeInput.title = msg.session_id;
            }
            TaskModule.updateSessionIdState(runner, msg.session_id);
        }

        // 根据消息类型处理
        switch (msg.type) {
            case 'text':
            case 'thinking':
            case 'tool_use':
            case 'tool_result':
            case 'info':
                this.addMessage(runner, msg.type, msg.content || '', {
                    timestamp: msg.timestamp,
                    tool_name: msg.tool_name,
                    tool_input: msg.tool_input,
                    is_error: msg.is_error,
                });
                break;

            case 'error':
                this.addMessage(runner, 'error', msg.content || '未知错误', {
                    timestamp: msg.timestamp,
                });
                this._updateUI(runner, { isRunning: false, error: true });
                break;

            case 'complete':
                this.addMessage(runner, 'complete', msg.content || '任务完成', {
                    timestamp: msg.timestamp,
                });

                // 更新会话信息栏
                if (typeof SessionInfoBar !== 'undefined') {
                    SessionInfoBar.updateSessionInfo({
                        messageCount: runner.state.messages?.length || 0,
                        createdTime: msg.timestamp,
                    });
                }

                this._updateUI(runner, { isRunning: false, hasOutput: true });

                // 更新悬浮统计
                if (msg.metadata) {
                    this._updateStats(runner, msg.metadata);
                }
                break;

            case 'ask_user_question':
                // 显示问答消息
                this.addMessage(runner, 'ask_user_question', msg.content || '', {
                    timestamp: msg.timestamp,
                });

                // 显示问答对话框
                if (msg.question) {
                    this._showQuestionDialog(runner, msg);
                }
                break;

            default:
                console.warn('[Task] 未知消息类型:', msg.type);
        }
    },

    /**
     * 显示问答对话框
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} msg - 包含问题数据的消息
     */
    async _showQuestionDialog(runner, msg) {
        const question = msg.question;
        if (!question) return;

        // 更新会话状态为等待
        runner.state.isWaitingAnswer = true;
        runner.state.pendingQuestionId = question.question_id;

        // 使用 Questions 模块显示问答卡片
        if (typeof Questions !== 'undefined' && Questions.showQuestionCard) {
            Questions.showQuestionCard(runner, question, async (answer) => {
                // 用户选择答案后提交
                await this._submitAnswer(runner, question, answer);
            });
        } else {
            // 简单的确认对话框
            const answer = confirm(question.question_text + '\n\n点击确定继续');
            if (answer) {
                await this._submitAnswer(runner, question, true);
            }
        }
    },

    /**
     * 提交答案
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} question - 问题数据
     * @param {*} answer - 用户答案
     */
    async _submitAnswer(runner, question, answer) {
        try {
            const response = await fetch('/api/task/answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this._currentSessionId,
                    question_id: question.question_id,
                    answer,
                    raw_question_data: question.raw_question_data,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            runner.state.isWaitingAnswer = false;
            runner.state.pendingQuestionId = null;

        } catch (error) {
            console.error('[Task] 提交答案失败:', error);
            this.addMessage(runner, 'error', `提交答案失败: ${error.message}`);
        }
    },

    /**
     * 更新统计信息
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} metadata - 元数据
     */
    _updateStats(runner, metadata) {
        const statsSection = document.getElementById('task-stats-floating');
        if (!statsSection) return;

        statsSection.style.display = 'flex';

        // 更新各统计项
        if (metadata.cost_usd !== undefined) {
            const costEl = document.getElementById('stat-cost');
            if (costEl) costEl.textContent = `$${metadata.cost_usd.toFixed(4)}`;
        }

        if (metadata.duration_ms !== undefined) {
            const durationEl = document.getElementById('stat-duration');
            if (durationEl) {
                const seconds = Math.round(metadata.duration_ms / 1000);
                durationEl.textContent = `${seconds}s`;
            }
        }

        if (metadata.session_id) {
            const sessionEl = document.getElementById('stat-session');
            if (sessionEl) {
                sessionEl.textContent = metadata.session_id.substring(0, 8);
                sessionEl.title = metadata.session_id;
            }
        }
    },

    /**
     * 更新 UI 状态
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} state - 状态对象
     */
    _updateUI(runner, state) {
        const sendBtn = document.getElementById('send-btn');
        const stopBtn = document.getElementById('stop-btn');
        const promptInput = document.getElementById('prompt');

        if (state.isRunning !== undefined) {
            if (sendBtn) sendBtn.style.display = state.isRunning ? 'none' : 'inline-flex';
            if (stopBtn) stopBtn.style.display = state.isRunning ? 'inline-flex' : 'none';
            if (promptInput) promptInput.disabled = state.isRunning;
        }

        if (state.error !== undefined) {
            const statusEl = document.getElementById('stat-status');
            if (statusEl) {
                statusEl.textContent = state.error ? 'failed' : 'running';
            }
        }

        if (state.hasOutput !== undefined) {
            const statsSection = document.getElementById('task-stats-floating');
            if (statsSection && runner.state.messages?.length > 0) {
                statsSection.style.display = 'flex';
            }
        }
    },

    /**
     * 获取输出容器
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @returns {HTMLElement} 输出容器元素
     */
    _getOutputContainer(runner) {
        // 优先使用 runner.outputEl
        if (runner.outputEl) return runner.outputEl;

        // 尝试查找输出容器
        let container = document.getElementById('output-container-wrapper');
        if (!container) {
            container = document.querySelector('.output-container');
        }
        if (!container) {
            container = document.querySelector('.session-bottom-container');
        }

        // 如果还是没有，创建默认容器
        if (!container) {
            container = document.createElement('div');
            container.className = 'output-container';
            const inputContainer = document.querySelector('.session-input-container');
            if (inputContainer) {
                inputContainer.parentNode.insertBefore(container, inputContainer);
            }
        }

        runner.outputEl = container;
        return container;
    },
};

// 导出到全局命名空间
window.Task = Task;

// 同时保留 TaskModule 供其他模块使用
const TaskModule = {
    updateIsStreamingState(runner, isStreaming) {
        runner.state.isStreaming = isStreaming;
    },

    updateSessionIdState(runner, sessionId) {
        runner.state.sessionId = sessionId;
        runner.state.sessionStatus = sessionId ? 'resumed' : 'new';
    },

    updateWorkspaceState(runner, workspace) {
        runner.state.workspace = workspace;
        if (workspace && typeof WorkspaceCombo !== 'undefined') {
            const history = runner.state.workspaceHistory || [];
            if (!history.includes(workspace)) {
                history.unshift(workspace);
                if (history.length > 10) {
                    history.pop();
                }
                runner.state.workspaceHistory = history;
            }
        }
    },
};

window.TaskModule = TaskModule;
