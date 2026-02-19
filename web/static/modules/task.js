/**
 * 任务执行模块
 * 处理任务的执行、流式输出和状态管理
 */

const Task = {
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
        const resume = runner.resumeInput.value.trim() || null;

        // 更新 UI 状态
        this.setRunning(runner, true);
        this.hideStats(runner);

        // 创建新的对话轮次
        this.startNewRound(runner, prompt);

        await this.executeTask(runner, prompt, workingDir, tools, continueConversation, resume);
    },

    /**
     * 创建新的对话轮次
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} userPrompt - 用户输入的提示
     */
    startNewRound(runner, userPrompt) {
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

        this.setRunning(runner, true);
        this.hideStats(runner);

        // 创建新的对话轮次
        this.startNewRound(runner, prompt);

        await this.executeTask(runner, prompt, workingDir, tools, false, sessionId);
    },

    /**
     * 执行任务
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} prompt - 提示文本
     * @param {string} workingDir - 工作目录
     * @param {Array} tools - 工具列表
     * @param {boolean} continueConversation - 是否继续对话
     * @param {string|null} resume - 会话 ID
     */
    async executeTask(runner, prompt, workingDir, tools, continueConversation, resume) {
        try {
            runner.abortController = new AbortController();

            const response = await fetch('/api/task/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt,
                    working_dir: workingDir || null,
                    tools,
                    continue_conversation: continueConversation,
                    resume: resume,
                }),
                signal: runner.abortController.signal,
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            runner.reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await runner.reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            this.handleStreamMessage(runner, data);
                        } catch (e) {
                            console.error('Parse error:', e);
                        }
                    }
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                this.addMessage(runner, 'error', '任务已停止');
            } else {
                this.addMessage(runner, 'error', `请求失败: ${error.message}`);
            }
        } finally {
            runner.abortController = null;
            runner.reader = null;
            this.setRunning(runner, false);
        }
    },

    /**
     * 停止任务
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    stopTask(runner) {
        if (runner.abortController) {
            runner.abortController.abort();
        }
        if (runner.reader) {
            runner.reader.cancel();
        }
    },

    /**
     * 处理流式消息
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} data - 消息数据
     */
    handleStreamMessage(runner, data) {
        const { type, content, timestamp, tool_name, tool_input, metadata } = data;

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

            case 'error':
                MessageRenderer.addAssistantMessage(runner, 'error', content, timestamp);
                break;

            case 'complete':
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
        runner.runBtn.disabled = running;
        runner.stopBtn.disabled = !running;
        runner.runBtn.innerHTML = running ? '⏳ 执行中...' : '▶ 执行';
    }
};

// 导出到全局命名空间
window.Task = Task;
