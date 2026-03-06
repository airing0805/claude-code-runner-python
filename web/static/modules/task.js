/**
 * 任务执行模块
 * 处理任务的执行、流式输出和状态管理
 *
 * v0.5.5 - SSE 连接优化
 * - 断线重连机制
 * - 指数退避策略
 * - 连接状态指示器
 * 
 * v0.5.6 - 状态管理和错误处理增强
 * - 完善的问答状态跟踪
 * - 增强的错误处理和恢复机制
 * - 会话状态持久化
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

// 任务状态枚举
const TaskStatus = {
    IDLE: 'idle',                 // 空闲
    RUNNING: 'running',           // 运行中
    PAUSED: 'paused',             // 暂停
    COMPLETED: 'completed',       // 完成
    ERROR: 'error'                // 错误
};

const Task = {
    // 重连相关状态
    _retryCount: 0,
    _retryTimeout: null,
    _connectionState: ConnectionState.DISCONNECTED,
    _taskContext: null, // 保存当前任务上下文用于重连
    _taskStatus: TaskStatus.IDLE, // 任务状态
    _sessionStartTime: null,      // 会话开始时间
    _taskTabId: null,            // 任务所属的 tab ID

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

        // 检查"继续会话"复选框状态
        const continueConversationChecked = runner.continueConversationCheckbox
            ? runner.continueConversationCheckbox.checked
            : false;

        // 确定要使用的 resume 参数
        // 优先级：1. "继续会话"复选框勾选 -> 使用 currentSessionId
        //         2. 用户手动输入的 resumeInput 值
        //         3. null（新会话）
        let resume = null;
        let newSession = false;
        let resumeInputValue = ''; // 在作用域外声明变量

        if (continueConversationChecked) {
            // 勾选"继续会话"复选框：使用最近会话ID
            resume = runner.currentSessionId || null;
            newSession = false;
            console.log('[Task] 使用"继续会话"模式:', resume);
        } else {
            // 未勾选复选框：使用 resumeInput 的值
            resumeInputValue = runner.resumeInput.value.trim();
            resume = resumeInputValue || runner.currentSessionId || null;

            // new_session: 是否创建新会话
            // 只有当 resumeInput 与 currentSessionId 不同时才创建新会话
            // 如果 resumeInput 为空或与 currentSessionId 一致，说明是继续当前会话
            newSession = resumeInputValue && resumeInputValue !== runner.currentSessionId;
        }

        const permissionMode = runner.permissionSelect ? runner.permissionSelect.value : 'default';

        // 调试日志
        console.log('[Task] 发送消息前状态:', {
            continueConversationChecked,
            resumeInputValue,
            currentSessionId: runner.currentSessionId,
            finalResume: resume,
            newSession,
        });

        // 记录任务所属的 tab ID
        this._taskTabId = runner.activeTabId;

        // 更新 UI 状态
        this.setRunning(runner, true);
        this.hideStats(runner);
        this._taskStatus = TaskStatus.RUNNING;
        this._sessionStartTime = Date.now();

        // 创建新的对话轮次
        await this.startNewRound(runner, prompt);

        await this.executeTask(runner, prompt, workingDir, tools, resume, permissionMode, newSession);
    },

    /**
     * 添加用户消息到对话
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} userPrompt - 用户输入的提示
     */
    async startNewRound(runner, userPrompt) {
        // 移除占位符
        const placeholder = runner.outputEl.querySelector('.output-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        // 创建新的对话轮次容器
        runner.roundCounter++;

        const roundEl = document.createElement('div');
        roundEl.className = 'conversation-round';
        roundEl.id = `round-${runner.roundCounter}`;

        // v9.0.1: 新轮次默认展开
        const collapseIcon = '▼';

        roundEl.innerHTML = `
            <div class="round-header">
                <button class="round-toggle" onclick="MessageRendererCore._toggleRoundCollapse('round-${runner.roundCounter}')">
                    <span class="round-toggle-icon">${'▼'}</span>
                </button>
                <span class="round-number">第 ${runner.roundCounter} 轮</span>
                <span class="round-timestamp">${new Date().toLocaleString()}</span>
            </div>
            <div class="round-content">
                <div class="round-user">
                    <div class="message-role user-role">👤 用户</div>
                    <div class="message-content user-content">${Utils.escapeHtml(userPrompt)}</div>
                </div>
                <div class="round-assistant">
                    <div class="message-role assistant-role">🤖 Claude</div>
                    <div class="assistant-messages"></div>
                </div>
            </div>
        `;

        runner.outputEl.appendChild(roundEl);
        runner.currentRoundEl = roundEl;
        const assistantMessagesEl = roundEl.querySelector('.assistant-messages');

        // 滚动到底部
        Utils.scrollToBottom(runner.outputEl);

        // 清空输入框（在用户消息已添加到 DOM 后）
        document.getElementById('prompt').value = '';

        // 保存用户消息到当前 tab
        const currentTab = runner.tabs.find(t => t.id === runner.activeTabId);
        if (currentTab) {
            // 构造用户消息对象
            const userMessage = {
                role: 'user',
                content: [{ type: 'text', text: userPrompt }],
                permissionMode: runner.permissionSelect ? runner.permissionSelect.value : 'default',
                timestamp: new Date().toISOString(),
            };
            currentTab.messages.push(userMessage);
            console.log('[Task] 保存用户消息到 tab:', currentTab.id, '消息数:', currentTab.messages.length);
        }

        // 保存用户消息到会话历史（后端）
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

        // 记录任务所属的 tab ID
        this._taskTabId = runner.activeTabId;

        this.setRunning(runner, true);
        this.hideStats(runner);
        this._taskStatus = TaskStatus.RUNNING;

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
     * @param {string|null} resume - 会话 ID
     * @param {string} permissionMode - 权限模式
     * @param {boolean} isReconnect - 是否为重连
     * @param {boolean} newSession - 是否创建新会话
     */
    async executeTask(runner, prompt, workingDir, tools, resume, permissionMode = 'default', isReconnect = false, newSession = false) {
        // 保存任务上下文用于重连
        this._taskContext = { prompt, workingDir, tools, resume, permissionMode };

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
                    resume: resume,
                    permission_mode: permissionMode,
                    new_session: newSession,
                }),
                signal: runner.abortController.signal,
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // 连接成功，更新状态
            this._updateConnectionState(runner, ConnectionState.CONNECTED);
            this._retryCount = 0; // 重置重连计数
            this._taskStatus = TaskStatus.RUNNING;

            runner.reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await runner.reader.read();

                if (done) {
                    // 正常结束
                    this._updateConnectionState(runner, ConnectionState.DISCONNECTED);
                    this._taskStatus = TaskStatus.COMPLETED;
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
                            await this.handleStreamMessage(runner, data);
                        } catch (e) {
                            console.error('Parse error:', e, 'Line:', line);
                            this.addMessage(runner, 'error', `消息解析错误: ${e.message}`);
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
                this._taskStatus = TaskStatus.IDLE;
            } else {
                // 连接错误，尝试重连
                console.error('SSE 连接错误:', error);
                this._taskStatus = TaskStatus.ERROR;
                await this._handleConnectionError(runner, error);
            }
        } finally {
            runner.abortController = null;
            runner.reader = null;
            this.setRunning(runner, false);

            // 清除任务所属的 tab ID
            this._taskTabId = null;

            // 记录会话结束时间
            if (this._sessionStartTime) {
                const duration = Date.now() - this._sessionStartTime;
                console.log(`[Session] 会话结束，总时长: ${Math.round(duration/1000)}秒`);
                this._sessionStartTime = null;
            }
        }
    },

    /**
     * 处理连接错误，尝试重连
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Error} error - 错误对象
     */
    async _handleConnectionError(runner, error) {
        // 清理当前连接
        if (runner.reader) {
            runner.reader.cancel().catch(() => {});
        }
        runner.reader = null;
        runner.abortController = null;

        // v9.0.2: 生成错误详情
        let errorDetail = '网络连接中断';
        if (error.message) {
            // 简化错误信息，避免泄露技术细节
            if (error.message.includes('network') || error.message.includes('fetch')) {
                errorDetail = '网络连接失败，请检查网络';
            } else if (error.message.includes('timeout')) {
                errorDetail = '连接超时，请稍后重试';
            } else if (error.message.includes('abort')) {
                errorDetail = '请求被中止';
            } else {
                errorDetail = '服务器连接中断';
            }
        }

        // 检查是否可以重连
        if (this._retryCount < SSE_CONFIG.MAX_RETRIES) {
            const delay = this._calculateRetryDelay();
            this._retryCount++;

            console.log(`SSE 断线，${delay / 1000}秒后尝试第 ${this._retryCount} 次重连...`);
            this._updateConnectionState(runner, ConnectionState.RECONNECTING);

            // 显示重连提示
            this._showReconnectNotification(runner, delay, this._retryCount);

            // v9.0.2: 显示更友好的错误提示
            this.addMessage(runner, 'info', `${errorDetail}，正在尝试重连 (${this._retryCount}/${SSE_CONFIG.MAX_RETRIES})...`);

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
                        resumeId,
                        ctx.permissionMode,
                        true, // 标记为重连
                        false // 重连不创建新会话
                    );
                }
            }, delay);
        } else {
            // 超过最大重连次数
            this._updateConnectionState(runner, ConnectionState.DISCONNECTED);
            this._showMaxRetriesExceeded(runner);

            // v9.0.2: 更详细的错误提示，包含可能的原因和建议
            let errorMsg = `连接失败：重试 ${SSE_CONFIG.MAX_RETRIES} 次后仍无法连接到服务器。`;
            errorMsg += '\n可能原因：';
            errorMsg += '\n- 网络连接不稳定';
            errorMsg += '\n- 服务器暂时不可用';
            errorMsg += '\n- 防火墙或代理设置';
            errorMsg += '\n\n建议：请检查网络连接后，点击右上角的"重新连接"按钮重试。';

            this.addMessage(runner, 'error', errorMsg);
            this._taskContext = null;
            this._taskStatus = TaskStatus.ERROR;
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

        // 清除内联样式，让 CSS 类控制显示
        indicator.style.removeProperty('display');

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
            this._taskStatus = TaskStatus.RUNNING;

            // 重新执行任务
            this.executeTask(
                runner,
                ctx.prompt,
                ctx.workingDir,
                ctx.tools,
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
        // 重置任务状态
        this._taskStatus = TaskStatus.IDLE;

        if (runner.abortController) {
            runner.abortController.abort();
        }
        if (runner.reader) {
            runner.reader.cancel();
        }

        // 正确更新运行状态（会更新对应 tab 的状态和按钮）
        this.setRunning(runner, false);

        // 更新连接状态
        this._updateConnectionState(runner, ConnectionState.DISCONNECTED);
    },

    /**
     * 处理流式消息
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} data - 消息数据
     */
    async handleStreamMessage(runner, data) {
        const { type, content, timestamp, tool_name, tool_input, metadata, question, session_id } = data;

        // 获取当前任务所属的 tab（通过 currentSessionId 查找）
        let taskTab = null;
        if (runner.currentSessionId) {
            taskTab = runner.tabs.find(t => t.sessionId === runner.currentSessionId);
        }
        // 如果找不到（新会话还没设置 sessionId），使用当前激活的 tab
        if (!taskTab) {
            taskTab = runner.tabs.find(t => t.id === runner.activeTabId);
        }

        // 更新 session_id（始终更新，以确保与服务器同步）
        if (session_id) {
            if (runner.currentSessionId && runner.currentSessionId !== session_id) {
                console.log('[Task] session_id 变化:', runner.currentSessionId, '->', session_id);
            }
            runner.currentSessionId = session_id;

            // 回显会话 ID 到 UI
            runner.resumeInput.value = session_id;
            runner.resumeInput.title = session_id;
            runner.resumeInput.removeAttribute('readonly'); // 允许编辑（如果需要）
            runner.resumeInput.classList.add('editable');

            // 同时更新任务所属标签的标题和 sessionId
            if (taskTab) {
                taskTab.sessionId = session_id;
                const tabEl = runner.tabsBar.querySelector(`[data-tab="${taskTab.id}"]`);
                if (tabEl) {
                    const titleEl = tabEl.querySelector('.tab-title');
                    if (titleEl) {
                        titleEl.textContent = `会话 ${session_id.substring(0, 8)}...`;
                        titleEl.title = session_id;
                    }
                }
            }

            console.log('[Task] 回显会话 ID:', session_id);
        }

        switch (type) {
            case 'text':
                this._saveMessageToTab(runner, taskTab, 'text', content, timestamp);
                break;

            case 'tool_use':
                let toolInfo = `🔧 ${tool_name}`;
                if (tool_input) {
                    const inputStr = JSON.stringify(tool_input, null, 2);
                    toolInfo += `\n${inputStr}`;
                }
                this._saveMessageToTab(runner, taskTab, 'tool_use', toolInfo, timestamp);
                break;

            case 'ask_user_question':
                // 问答消息，显示为普通文本
                if (content) {
                    this._saveMessageToTab(runner, taskTab, 'text', content, timestamp);
                }
                break;

            case 'error':
                // 错误时，恢复输入框
                this._setInputEnabled(runner, true);
                this._taskStatus = TaskStatus.ERROR;

                // 显示完整错误信息
                let errorMessage = content;
                if (data.error_detail) {
                    errorMessage = `${content}\n\n详细错误信息:\n${data.error_detail}`;
                    console.error('[Task] ★ 完整错误堆栈:', data.error_detail);
                }
                this._saveMessageToTab(runner, taskTab, 'error', errorMessage, timestamp);
                break;

            case 'complete':
                // 任务完成时，恢复输入框
                this._setInputEnabled(runner, true);
                this._taskStatus = TaskStatus.COMPLETED;

                // 显示统计信息（包含会话ID和继续会话按钮）
                if (metadata) {
                    this.showStats(runner, metadata);
                    runner.currentSessionId = metadata.session_id || runner.currentSessionId;

                    // 更新最近会话ID缓存
                    if (metadata.session_id && typeof runner.cacheLatestSessionId === 'function') {
                        runner.cacheLatestSessionId(metadata.session_id);
                    }
                }
                break;

            default:
                console.warn('[Task] 未知消息类型:', type);
                break;
        }
    },

    /**
     * 将消息保存到 tab，并根据当前激活 tab 决定是否渲染
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} tab - 目标 tab 对象
     * @param {string} type - 消息类型
     * @param {string} content - 消息内容
     * @param {string} timestamp - 时间戳
     */
    _saveMessageToTab(runner, tab, type, content, timestamp) {
        if (!tab) return;

        // 保存消息到 tab 的 messages 数组
        // 暂时简单保存文本消息，避免复杂的消息结构
        const messageObj = {
            role: 'assistant',
            type: type,
            content: type === 'text' ? content : '',
            timestamp: timestamp || new Date().toISOString(),
        };

        // 如果是 tool_use，需要特殊处理
        if (type === 'tool_use') {
            messageObj.content = content;
        }

        tab.messages.push(messageObj);

        // 只有当前激活的 tab 是该任务对应的 tab 时才渲染
        if (runner.activeTabId === tab.id) {
            MessageRenderer.addAssistantMessage(runner, type, content, timestamp);
        }
        // 注意：如果当前激活的tab不是目标tab，消息不会实时显示
        // 但会在切换到该tab时通过历史消息重新渲染
    },

    /**
     * 获取任务状态
     * @returns {string} 任务状态
     */
    getTaskStatus() {
        return this._taskStatus;
    },

    /**
     * 设置运行状态
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {boolean} running - 是否运行中
     */
    setRunning(runner, running) {
        const sendBtn = document.getElementById('send-btn');
        const stopBtn = document.getElementById('stop-btn');

        // 优先使用任务所属的 tab ID，否则使用当前激活的 tab
        const targetTabId = this._taskTabId || runner.activeTabId;
        const targetTab = runner.tabs.find(t => t.id === targetTabId);

        // 更新目标 tab 的运行状态
        if (targetTab) {
            targetTab.isRunning = running;
        }

        // 检查是否有任何 tab 在运行
        const anyTabRunning = runner.tabs.some(t => t.isRunning);

        // 更新全局状态
        runner.isRunning = anyTabRunning;

        // 根据当前激活 tab 的运行状态决定按钮状态
        const currentTab = runner.tabs.find(t => t.id === runner.activeTabId);
        const currentTabRunning = currentTab ? currentTab.isRunning : false;

        if (sendBtn) sendBtn.disabled = currentTabRunning;
        if (stopBtn) stopBtn.style.display = currentTabRunning ? 'inline-block' : 'none';
    },

    /**
     * 设置输入框启用状态
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {boolean} enabled - 是否启用
     */
    _setInputEnabled(runner, enabled) {
        const promptInput = document.getElementById('prompt');
        const sendBtn = document.getElementById('send-btn');

        // 获取当前激活 tab 的运行状态
        const currentTab = runner.tabs.find(t => t.id === runner.activeTabId);
        const tabIsRunning = currentTab ? currentTab.isRunning : false;

        if (promptInput) promptInput.disabled = !enabled;
        // 只有当前 tab 在运行时才禁用发送按钮（其他 tab 可以正常发送）
        if (sendBtn) sendBtn.disabled = tabIsRunning;
    },

    /**
     * 显示统计信息
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} metadata - 元数据
     */
    showStats(runner, metadata) {
        const statsEl = document.querySelector('.stats-floating');
        if (!statsEl) return;

        const cost = metadata.cost_usd ? `$${metadata.cost_usd.toFixed(4)}` : 'N/A';
        const duration = metadata.duration_ms ? `${(metadata.duration_ms / 1000).toFixed(1)}s` : 'N/A';
        const sessionId = metadata.session_id || 'N/A';

        // 显示会话ID短版本
        const shortSessionId = sessionId !== 'N/A' ? sessionId.substring(0, 8) + '...' : 'N/A';

        statsEl.innerHTML = `
            <div class="stat-item">
                <span class="stat-label">耗时:</span>
                <span class="stat-value">${duration}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">费用:</span>
                <span class="stat-value">${cost}</span>
            </div>
            <div class="stat-item session-id-item">
                <span class="stat-label">会话ID:</span>
                <span class="stat-value session-id-display" title="点击复制完整ID: ${sessionId}">${shortSessionId}</span>
            </div>
        `;

        statsEl.style.display = 'flex';

        // 添加复制功能
        const sessionIdDisplay = statsEl.querySelector('.session-id-display');
        if (sessionIdDisplay) {
            sessionIdDisplay.addEventListener('click', () => {
                navigator.clipboard.writeText(sessionId).then(() => {
                    sessionIdDisplay.textContent = '✓ 已复制';
                    setTimeout(() => {
                        sessionIdDisplay.textContent = shortSessionId;
                    }, 2000);
                });
            });
        }
    },

    /**
     * 隐藏统计信息
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    hideStats(runner) {
        const statsEl = document.querySelector('.stats-floating');
        if (statsEl) {
            statsEl.style.display = 'none';
        }
    },

    /**
     * 添加消息到输出区域
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} type - 消息类型
     * @param {string} content - 消息内容
     * @param {string} timestamp - 时间戳
     */
    addMessage(runner, type, content, timestamp = null) {
        MessageRenderer.addAssistantMessage(runner, type, content, timestamp);
    }
};

// 导出到全局命名空间
window.Task = Task;