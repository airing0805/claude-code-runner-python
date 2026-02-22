/**
 * 任务执行模块
 * 处理任务的执行、流式输出和状态管理
 *
 * v0.5.5 - SSE 连接优化
 * - 断线重连机制
 * - 指数退避策略
 * - 连接状态指示器
 */

// SSE 重连配置常量
const SSE_CONFIG = {
    BASE_RETRY_DELAY_MS: 1000,    // 基础重连延迟
    MAX_RETRY_DELAY_MS: 30000,    // 最大重连延迟
    MAX_RETRIES: 5,               // 最大重连次数
};

// 连接状态枚举
const ConnectionState = {
    CONNECTED: 'connected',       // 已连接
    CONNECTING: 'connecting',     // 连接中
    DISCONNECTED: 'disconnected', // 已断开
    RECONNECTING: 'reconnecting', // 重连中
};

const Task = {
    // 重连相关状态
    _retryCount: 0,
    _retryTimeout: null,
    _connectionState: ConnectionState.DISCONNECTED,
    _taskContext: null, // 保存当前任务上下文用于重连

    /**
     * 运行任务
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    async runTask(runner) {
        const prompt = document.getElementById('prompt').value.trim();
        if (!prompt) {
            this.addMessage(runner, 'error', '请输入任务描述');
            return;
        }

        const workingDir = runner.workingDirInput.value.trim();
        const tools = ToolsMultiselect.getSelectedTools(runner);
        const continueConversation = document.getElementById('continue-conversation').checked;
        // 优先使用用户输入的 resume，否则使用当前会话 ID（如果存在）
        const resume = runner.resumeInput.value.trim() || runner.currentSessionId || null;
        const permissionMode = runner.permissionSelect ? runner.permissionSelect.value : 'default';

        // 更新 UI 状态
        this.setRunning(runner, true);
        this.hideStats(runner);

        // 创建新的对话轮次
        await this.startNewRound(runner, prompt);

        await this.executeTask(runner, prompt, workingDir, tools, continueConversation, resume, permissionMode);
    },

    /**
     * 创建新的对话轮次
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} userPrompt - 用户输入的提示
     */
    async startNewRound(runner, userPrompt) {
        // 移除占位符
        const placeholder = runner.outputEl.querySelector('.output-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        // 增加轮次计数
        runner.roundCounter++;

        // 创建新的对话轮次容器
        const roundEl = document.createElement('div');
        roundEl.className = 'conversation-round';
        roundEl.id = `round-${runner.roundCounter}`;

        roundEl.innerHTML = `
            <div class="round-header">
                <span class="round-number">第 ${runner.roundCounter} 轮</span>
            </div>
            <div class="round-user">
                <div class="message-role user-role">👤 用户</div>
                <div class="message-content user-content">${Utils.escapeHtml(userPrompt)}</div>
            </div>
            <div class="round-assistant">
                <div class="message-role assistant-role">🤖 Claude</div>
                <div class="assistant-messages"></div>
            </div>
        `;

        runner.outputEl.appendChild(roundEl);
        runner.currentRoundEl = roundEl;

        // 滚动到底部
        Utils.scrollToBottom(runner.outputEl);

        // 清空输入框（在用户消息已添加到 DOM 后）
        document.getElementById('prompt').value = '';

        // 保存用户消息到会话历史
        const sessionId = runner.currentSessionId;
        if (sessionId) {
            const workingDir = runner.workingDirInput.value.trim() || null;
            try {
                await fetch(`/api/sessions/${sessionId}/messages`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sessionId,
                        role: 'user',
                        content: [{ type: 'text', text: userPrompt }],
                        working_dir: workingDir,
                    }),
                });
            } catch (error) {
                console.error('保存用户消息失败:', error);
            }
        }
    },

    /**
     * 使用会话 ID 运行任务
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} sessionId - 会话 ID
     * @param {string} prompt - 提示文本
     */
    async runTaskWithSession(runner, sessionId, prompt) {
        const workingDir = runner.workingDirInput.value.trim();
        const tools = ToolsMultiselect.getSelectedTools(runner);
        const permissionMode = runner.permissionSelect ? runner.permissionSelect.value : 'default';

        this.setRunning(runner, true);
        this.hideStats(runner);

        // 创建新的对话轮次
        await this.startNewRound(runner, prompt);

        await this.executeTask(runner, prompt, workingDir, tools, false, sessionId, permissionMode);
    },

    /**
     * 执行任务
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} prompt - 提示文本
     * @param {string} workingDir - 工作目录
     * @param {Array} tools - 工具列表
     * @param {boolean} continueConversation - 是否继续对话
     * @param {string|null} resume - 会话 ID
     * @param {string} permissionMode - 权限模式
     * @param {boolean} isReconnect - 是否为重连
     */
    async executeTask(runner, prompt, workingDir, tools, continueConversation, resume, permissionMode = 'default', isReconnect = false) {
        // 保存任务上下文用于重连
        this._taskContext = { prompt, workingDir, tools, continueConversation, resume, permissionMode };

        // 更新连接状态
        this._updateConnectionState(runner, isReconnect ? ConnectionState.RECONNECTING : ConnectionState.CONNECTING);

        try {
            runner.abortController = new AbortController();

            // ========== 前端调试日志 ==========
            console.log('[Task] ★ 发送请求到 /api/task/stream');
            console.log('[Task] ★ 请求参数 (完整):', {
                prompt: prompt,
                working_dir: workingDir,
                tools,
                continue_conversation: continueConversation,
                resume: resume,
                permission_mode: permissionMode,
            });
            console.log('[Task] ★ 当前 runner.currentSessionId:', runner.currentSessionId);
            console.log('[Task] ★ runner.resumeInput.value:', runner.resumeInput.value);

            const response = await fetch('/api/task/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt,
                    working_dir: workingDir || null,
                    tools,
                    continue_conversation: continueConversation,
                    resume: resume,
                    permission_mode: permissionMode,
                }),
                signal: runner.abortController.signal,
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            // 连接成功，更新状态
            this._updateConnectionState(runner, ConnectionState.CONNECTED);
            this._retryCount = 0; // 重置重连计数

            runner.reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await runner.reader.read();

                if (done) {
                    // 正常结束
                    this._updateConnectionState(runner, ConnectionState.DISCONNECTED);
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            // ========== 前端调试日志 ==========
                            console.log('[Task] ★ 收到 SSE 消息:', {
                                type: data.type,
                                session_id: data.session_id,
                                runner_currentSessionId: runner.currentSessionId,
                            });
                            this.handleStreamMessage(runner, data);
                        } catch (e) {
                            console.error('Parse error:', e);
                        }
                    }
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                // 用户主动停止，不重连
                this._updateConnectionState(runner, ConnectionState.DISCONNECTED);
                this._clearRetryTimeout();
                this.addMessage(runner, 'error', '任务已停止');
            } else {
                // 连接错误，尝试重连
                console.error('SSE 连接错误:', error);
                this._handleConnectionError(runner, error);
            }
        } finally {
            runner.abortController = null;
            runner.reader = null;
            this.setRunning(runner, false);
        }
    },

    /**
     * 处理连接错误，尝试重连
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Error} error - 错误对象
     */
    _handleConnectionError(runner, error) {
        // 清理当前连接
        if (runner.reader) {
            runner.reader.cancel().catch(() => {});
        }
        runner.reader = null;
        runner.abortController = null;

        // 检查是否可以重连
        if (this._retryCount < SSE_CONFIG.MAX_RETRIES) {
            const delay = this._calculateRetryDelay();
            this._retryCount++;

            console.log(`SSE 断线，${delay / 1000}秒后尝试第 ${this._retryCount} 次重连...`);
            this._updateConnectionState(runner, ConnectionState.RECONNECTING);

            // 显示重连提示
            this._showReconnectNotification(runner, delay, this._retryCount);

            // 设置重连定时器
            this._retryTimeout = setTimeout(() => {
                if (this._taskContext && runner.isRunning) {
                    const ctx = this._taskContext;
                    // 使用当前 session_id 进行重连
                    const resumeId = runner.currentSessionId || ctx.resume;
                    this.executeTask(
                        runner,
                        ctx.prompt,
                        ctx.workingDir,
                        ctx.tools,
                        ctx.continueConversation,
                        resumeId,
                        ctx.permissionMode,
                        true // 标记为重连
                    );
                }
            }, delay);
        } else {
            // 超过最大重连次数
            this._updateConnectionState(runner, ConnectionState.DISCONNECTED);
            this._showMaxRetriesExceeded(runner);
            this.addMessage(runner, 'error', `连接已断开，重试 ${SSE_CONFIG.MAX_RETRIES} 次后仍失败。请手动重试。`);
            this._taskContext = null;
        }
    },

    /**
     * 计算重连延迟（指数退避）
     * @returns {number} 延迟毫秒数
     */
    _calculateRetryDelay() {
        const delay = Math.min(
            SSE_CONFIG.BASE_RETRY_DELAY_MS * Math.pow(2, this._retryCount),
            SSE_CONFIG.MAX_RETRY_DELAY_MS
        );
        return delay;
    },

    /**
     * 清除重连定时器
     */
    _clearRetryTimeout() {
        if (this._retryTimeout) {
            clearTimeout(this._retryTimeout);
            this._retryTimeout = null;
        }
    },

    /**
     * 更新连接状态并通知 UI
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} state - 连接状态
     */
    _updateConnectionState(runner, state) {
        this._connectionState = state;
        this._updateConnectionIndicator(runner, state);
    },

    /**
     * 更新连接状态指示器 UI
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} state - 连接状态
     */
    _updateConnectionIndicator(runner, state) {
        const indicator = document.getElementById('connection-indicator');
        if (!indicator) return;

        const statusText = indicator.querySelector('.connection-status-text');
        const statusDot = indicator.querySelector('.connection-status-dot');
        const retryInfo = indicator.querySelector('.connection-retry-info');
        const reconnectBtn = indicator.querySelector('.connection-reconnect-btn');

        // 移除所有状态类
        indicator.classList.remove('state-connected', 'state-connecting', 'state-disconnected', 'state-reconnecting');

        switch (state) {
            case ConnectionState.CONNECTED:
                indicator.classList.add('state-connected');
                if (statusText) statusText.textContent = '已连接';
                if (statusDot) statusDot.textContent = '🟢';
                if (retryInfo) retryInfo.style.display = 'none';
                if (reconnectBtn) reconnectBtn.style.display = 'none';
                indicator.style.display = 'none'; // 连接成功时隐藏
                break;

            case ConnectionState.CONNECTING:
                indicator.classList.add('state-connecting');
                indicator.style.display = 'flex';
                if (statusText) statusText.textContent = '连接中...';
                if (statusDot) statusDot.textContent = '🟡';
                if (retryInfo) retryInfo.style.display = 'none';
                if (reconnectBtn) reconnectBtn.style.display = 'none';
                break;

            case ConnectionState.DISCONNECTED:
                indicator.classList.add('state-disconnected');
                indicator.style.display = 'flex';
                if (statusText) statusText.textContent = '已断开';
                if (statusDot) statusDot.textContent = '⚫';
                if (retryInfo) retryInfo.style.display = 'none';
                if (reconnectBtn) reconnectBtn.style.display = 'inline-block';
                break;

            case ConnectionState.RECONNECTING:
                indicator.classList.add('state-reconnecting');
                indicator.style.display = 'flex';
                if (statusText) statusText.textContent = '重连中...';
                if (statusDot) statusDot.textContent = '🟠';
                if (retryInfo) retryInfo.style.display = 'inline';
                if (reconnectBtn) reconnectBtn.style.display = 'none';
                break;
        }
    },

    /**
     * 显示重连通知
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {number} delay - 延迟毫秒数
     * @param {number} retryCount - 当前重连次数
     */
    _showReconnectNotification(runner, delay, retryCount) {
        const indicator = document.getElementById('connection-indicator');
        if (!indicator) return;

        const retryInfo = indicator.querySelector('.connection-retry-info');
        if (retryInfo) {
            const seconds = Math.ceil(delay / 1000);
            retryInfo.textContent = `(${seconds}秒后第 ${retryCount}/${SSE_CONFIG.MAX_RETRIES} 次重试)`;
            retryInfo.style.display = 'inline';

            // 倒计时更新
            let remaining = seconds;
            const countdownInterval = setInterval(() => {
                remaining--;
                if (remaining <= 0 || this._connectionState !== ConnectionState.RECONNECTING) {
                    clearInterval(countdownInterval);
                    return;
                }
                retryInfo.textContent = `(${remaining}秒后第 ${retryCount}/${SSE_CONFIG.MAX_RETRIES} 次重试)`;
            }, 1000);
        }
    },

    /**
     * 显示超过最大重连次数提示
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    _showMaxRetriesExceeded(runner) {
        const indicator = document.getElementById('connection-indicator');
        if (!indicator) return;

        const retryInfo = indicator.querySelector('.connection-retry-info');
        if (retryInfo) {
            retryInfo.textContent = '(已达最大重试次数)';
            retryInfo.style.display = 'inline';
        }
    },

    /**
     * 手动重连
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    manualReconnect(runner) {
        // 重置重连计数
        this._retryCount = 0;
        this._clearRetryTimeout();

        if (this._taskContext) {
            const ctx = this._taskContext;
            const resumeId = runner.currentSessionId || ctx.resume;

            // 设置运行状态
            this.setRunning(runner, true);
            this.hideStats(runner);

            // 重新执行任务
            this.executeTask(
                runner,
                ctx.prompt,
                ctx.workingDir,
                ctx.tools,
                ctx.continueConversation,
                resumeId,
                ctx.permissionMode,
                true
            );
        }
    },

    /**
     * 停止任务
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    stopTask(runner) {
        // 清除重连定时器
        this._clearRetryTimeout();
        // 清除任务上下文
        this._taskContext = null;
        // 重置重连计数
        this._retryCount = 0;

        if (runner.abortController) {
            runner.abortController.abort();
        }
        if (runner.reader) {
            runner.reader.cancel();
        }
        // 恢复输入框
        this._setInputEnabled(runner, true);

        // 更新连接状态
        this._updateConnectionState(runner, ConnectionState.DISCONNECTED);
    },

    /**
     * 处理流式消息
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} data - 消息数据
     */
    handleStreamMessage(runner, data) {
        const { type, content, timestamp, tool_name, tool_input, metadata, question, session_id } = data;

        // 更新 session_id（始终更新，以确保与服务器同步）
        if (session_id) {
            if (runner.currentSessionId && runner.currentSessionId !== session_id) {
                console.log('[Task] session_id 变化:', runner.currentSessionId, '->', session_id);
            }
            runner.currentSessionId = session_id;
        }

        switch (type) {
            case 'text':
                MessageRenderer.addAssistantMessage(runner, 'text', content, timestamp);
                break;

            case 'tool_use':
                let toolInfo = `🔧 ${tool_name}`;
                if (tool_input) {
                    const inputStr = JSON.stringify(tool_input, null, 2);
                    toolInfo += `\n${inputStr}`;
                }
                MessageRenderer.addAssistantMessage(runner, 'tool_use', toolInfo, timestamp);
                break;

            case 'ask_user_question':
                // 显示问答对话框时，禁用输入框和发送按钮
                this._setInputEnabled(runner, false);

                // 显示问答对话框
                if (question) {
                    // 优先使用根级别的 session_id，否则使用 runner 中的
                    const sessionId = session_id || runner.currentSessionId;
                    console.log('[Task] 显示问答对话框, session_id:', session_id, 'runner.currentSessionId:', runner.currentSessionId);
                    AskUserQuestionDialog.show(runner, question, sessionId);
                } else {
                    MessageRenderer.addAssistantMessage(runner, 'text', content, timestamp);
                }
                break;

            case 'error':
                // 错误时，恢复输入框
                this._setInputEnabled(runner, true);
                // 显示完整错误信息
                let errorMessage = content;
                if (data.error_detail) {
                    errorMessage = `${content}\n\n详细错误信息:\n${data.error_detail}`;
                    console.error('[Task] ★ 完整错误堆栈:', data.error_detail);
                }
                MessageRenderer.addAssistantMessage(runner, 'error', errorMessage, timestamp);
                break;

            case 'complete':
                // 任务完成时，恢复输入框
                this._setInputEnabled(runner, true);
                // 更新 session_id
                if (session_id) {
                    console.log('[Task] 任务完成, 更新 session_id:', session_id);
                    runner.currentSessionId = session_id;
                }
                MessageRenderer.addAssistantMessage(runner, 'complete', `✅ ${content}`, timestamp);
                if (metadata) {
                    this.showStats(runner, metadata);
                }
                break;

            default:
                MessageRenderer.addAssistantMessage(runner, 'text', content, timestamp);
        }
    },

    /**
     * 添加消息（兼容旧接口）
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} type - 消息类型
     * @param {string} content - 消息内容
     * @param {string|null} timestamp - 时间戳
     */
    addMessage(runner, type, content, timestamp = null) {
        // 如果有当前对话轮次，添加到轮次中
        if (runner.currentRoundEl) {
            MessageRenderer.addAssistantMessage(runner, type, content, timestamp);
            return;
        }

        // 否则使用旧的方式添加消息
        const placeholder = runner.outputEl.querySelector('.output-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        const msgEl = document.createElement('div');
        msgEl.className = `message message-${type}`;
        const timeStr = Utils.formatTime(timestamp);

        msgEl.innerHTML = `
            <span class="timestamp">${timeStr}</span>
            <span class="content">${Utils.escapeHtml(content)}</span>
        `;

        runner.outputEl.appendChild(msgEl);
        Utils.scrollToBottom(runner.outputEl);
    },

    /**
     * 显示统计信息
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} metadata - 元数据
     */
    showStats(runner, metadata) {
        runner.statsSection.style.display = 'block';

        const status = metadata.is_error ? '❌ 失败' : '✅ 成功';
        document.getElementById('stat-status').textContent = status;
        document.getElementById('stat-status').style.color = metadata.is_error ? '#ef4444' : '#10b981';

        const duration = metadata.duration_ms || 0;
        document.getElementById('stat-duration').textContent = `${(duration / 1000).toFixed(2)}s`;

        const cost = metadata.cost_usd || 0;
        document.getElementById('stat-cost').textContent = `$${cost.toFixed(4)}`;

        const sessionEl = document.getElementById('stat-session');
        if (metadata.session_id) {
            sessionEl.textContent = metadata.session_id.substring(0, 12) + '...';
            sessionEl.title = metadata.session_id;
            sessionEl.style.cursor = 'pointer';
            sessionEl.onclick = () => {
                navigator.clipboard.writeText(metadata.session_id);
                this.addMessage(runner, 'info', `📋 会话 ID 已复制: ${metadata.session_id}`);
            };

            // 更新会话ID显示和标签标题
            const newSessionId = metadata.session_id;

            // 如果是新任务标签，更新为会话标签
            if (runner.activeTabId === 'new' || (runner.tabs.find(t => t.id === runner.activeTabId)?.isNew)) {
                // 从第一个用户消息提取标题
                const prompt = document.getElementById('prompt').value.trim();
                const tabTitle = prompt.substring(0, 30) || `会话 ${newSessionId.substring(0, 8)}`;

                // 更新当前标签
                const tabData = runner.tabs.find(t => t.id === runner.activeTabId);
                if (tabData) {
                    tabData.sessionId = newSessionId;
                    tabData.title = tabTitle;
                    tabData.isNew = false;

                    // 更新标签元素
                    const tabEl = runner.tabsBar.querySelector(`[data-tab="${runner.activeTabId}"]`);
                    if (tabEl) {
                        tabEl.dataset.sessionId = newSessionId;
                        const iconEl = tabEl.querySelector('.tab-icon');
                        const titleEl = tabEl.querySelector('.tab-title');
                        if (iconEl) iconEl.textContent = '💬';
                        if (titleEl) {
                            titleEl.textContent = tabTitle.substring(0, 15) + (tabTitle.length > 15 ? '...' : '');
                            titleEl.title = tabTitle;
                        }
                    }
                }
            }

            // 更新会话ID显示
            Session.updateSessionDisplay(runner, newSessionId, null);
            Session.setSessionEditable(runner, false);
        } else {
            sessionEl.textContent = '-';
            sessionEl.title = '';
            sessionEl.onclick = null;
        }
    },

    /**
     * 隐藏统计信息
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    hideStats(runner) {
        runner.statsSection.style.display = 'none';
    },

    /**
     * 清空输出
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    clearOutput(runner) {
        // 清空输出区
        runner.outputEl.innerHTML = '<div class="output-placeholder">执行任务后，输出将显示在这里...</div>';

        // 隐藏统计信息
        this.hideStats(runner);

        // 重置多轮对话状态
        runner.currentRoundEl = null;
        runner.roundCounter = 0;

        // 如果是新任务标签，清空输入
        const tabData = runner.tabs.find(t => t.id === runner.activeTabId);
        if (runner.activeTabId === 'new' || (tabData && tabData.isNew)) {
            document.getElementById('prompt').value = '';
            runner.resumeInput.value = '';
            runner.resumeInput.title = '';
            runner.currentSessionId = null;
        }
    },

    /**
     * 设置运行状态
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {boolean} running - 是否正在运行
     */
    setRunning(runner, running) {
        runner.isRunning = running;
        if (running) {
            // 执行中：显示停止按钮，隐藏发送按钮
            runner.sendBtn.style.display = 'none';
            runner.stopBtn.style.display = 'inline-block';
        } else {
            // 未执行：显示发送按钮，隐藏停止按钮
            runner.sendBtn.style.display = 'inline-block';
            runner.stopBtn.style.display = 'none';
        }
    },

    /**
     * 设置输入框启用/禁用状态
     * 用于问答交互时禁用输入框
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {boolean} enabled - 是否启用
     */
    _setInputEnabled(runner, enabled) {
        if (runner.promptInput) {
            runner.promptInput.disabled = !enabled;
        }
        if (runner.sendBtn) {
            runner.sendBtn.disabled = !enabled;
        }
    }
};

// 导出到全局命名空间
window.Task = Task;
