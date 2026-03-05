/**
 * 标签页组件模块
 * 处理标签页的创建、切换和关闭
 */

const Tabs = {
    /**
     * 创建新的任务标签页
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @returns {Promise<string>} 新创建的标签页 ID
     */
    async createNewSession(runner) {
        // 调用后端 API 结束当前会话
        if (runner.currentSessionId) {
            try {
                await fetch('/api/task/new-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: runner.currentSessionId }),
                });
                console.log('[Tabs] 已结束当前会话:', runner.currentSessionId);
            } catch (error) {
                console.error('[Tabs] 结束会话失败:', error);
            }
        }
        const tabId = `new-${++runner.tabCounter}`;
        const tabsBar = runner.tabsBar;
        const workingDir = runner.workingDirInput ? runner.workingDirInput.value : '';

        // 清空当前会话 ID
        runner.currentSessionId = null;

        // 启用"继续会话"复选框
        runner.updateContinueConversationCheckbox(true);
        // 取消勾选复选框
        if (runner.continueConversationCheckbox) {
            runner.continueConversationCheckbox.checked = false;
        }

        // 添加标签
        const tabEl = document.createElement('button');
        tabEl.className = 'tab-item';
        tabEl.dataset.tab = tabId;
        tabEl.innerHTML = `
            <span class="tab-icon">➕</span>
            <span class="tab-title">新任务</span>
            <button class="tab-close" title="关闭标签页">×</button>
        `;

        // 绑定标签点击事件
        tabEl.addEventListener('click', (e) => {
            if (!e.target.classList.contains('tab-close')) {
                this.switchToTab(runner, tabId);
            }
        });

        // 绑定关闭按钮
        tabEl.querySelector('.tab-close').addEventListener('click', (e) => {
            e.stopPropagation();
            this.closeTab(runner, tabId);
        });

        tabsBar.appendChild(tabEl);

        // 存储标签信息
        runner.tabs.push({
            id: tabId,
            sessionId: null,
            title: '新任务',
            messages: [],
            workingDir: workingDir,
            isNew: true,
            isRunning: false,  // 每个 tab 独立的运行状态
        });

        // 创建对应的输出容器
        this.createOutputContainer(runner, tabId);

        // 切换到新标签
        this.switchToTab(runner, tabId);

        return tabId;
    },

    /**
     * 创建tab对应的输出容器
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} tabId - tab ID
     */
    createOutputContainer(runner, tabId) {
        const outputContainer = document.createElement('div');
        outputContainer.id = `output-${tabId}`;
        outputContainer.className = 'session-output tab-output-container';
        outputContainer.style.display = 'none'; // 默认隐藏
        
        // 添加占位符
        outputContainer.innerHTML = '<div class="output-placeholder">执行任务后，输出将显示在这里...</div>';
        
        // 插入到主输出容器后面
        const mainOutput = document.getElementById('output');
        if (mainOutput) {
            mainOutput.parentNode.insertBefore(outputContainer, mainOutput.nextSibling);
        } else {
            // 如果没有主输出容器，添加到适当位置
            const sessionLayout = document.querySelector('.session-layout');
            if (sessionLayout) {
                sessionLayout.appendChild(outputContainer);
            }
        }
    },

    /**
     * 创建会话标签页
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} sessionId - 会话 ID
     * @param {string} title - 标签标题
     * @param {Array} historyMessages - 历史消息数组
     * @param {string} projectPath - 项目路径
     * @returns {string} 创建的标签页 ID
     */
    createSessionTab(runner, sessionId, title, historyMessages = [], projectPath = '') {
        const tabId = `session-${++runner.tabCounter}`;
        const tabsBar = runner.tabsBar;

        // 添加标签
        const tabEl = document.createElement('button');
        tabEl.className = 'tab-item';
        tabEl.dataset.tab = tabId;
        tabEl.dataset.sessionId = sessionId;
        tabEl.innerHTML = `
            <span class="tab-icon">💬</span>
            <span class="tab-title" title="${Utils.escapeHtml(title)}">${Utils.escapeHtml(title.substring(0, 15))}${title.length > 15 ? '...' : ''}</span>
            <button class="tab-close" title="关闭标签页">×</button>
        `;

        // 绑定标签点击事件
        tabEl.addEventListener('click', (e) => {
            if (!e.target.classList.contains('tab-close')) {
                this.switchToTab(runner, tabId);
            }
        });

        // 绑定关闭按钮
        tabEl.querySelector('.tab-close').addEventListener('click', (e) => {
            e.stopPropagation();
            this.closeTab(runner, tabId);
        });

        tabsBar.appendChild(tabEl);

        // 存储标签信息（包括历史消息和工作目录）
        runner.tabs.push({
            id: tabId,
            sessionId: sessionId,
            title: title,
            messages: historyMessages,
            workingDir: projectPath,
            isNew: false,
            isRunning: false,  // 每个 tab 独立的运行状态
        });

        // 创建对应的输出容器
        this.createOutputContainer(runner, tabId);

        // 显示历史消息到对应的容器
        if (historyMessages.length > 0) {
            MessageRenderer.displayHistoryMessagesToTab(runner, tabId, historyMessages);
        }

        // 更新会话 ID 输入框
        if (runner.resumeInput) {
            runner.resumeInput.value = sessionId;
            runner.resumeInput.title = sessionId;
        }
        runner.currentSessionId = sessionId;

        // 切换到新标签
        this.switchToTab(runner, tabId);

        return tabId;
    },

    /**
     * 切换到指定标签页
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} tabId - 标签页 ID
     */
    switchToTab(runner, tabId) {
        const tabsBar = runner.tabsBar;

        // 更新标签高亮
        tabsBar.querySelectorAll('.tab-item').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });

        runner.activeTabId = tabId;

        // 隐藏所有输出容器
        document.querySelectorAll('.tab-output-container').forEach(container => {
            container.style.display = 'none';
        });

        // 显示当前tab的输出容器
        const currentOutputContainer = document.getElementById(`output-${tabId}`);
        if (currentOutputContainer) {
            currentOutputContainer.style.display = 'block';
            runner.outputEl = currentOutputContainer; // 更新runner的outputEl引用
        } else {
            // 如果没有找到对应的容器，使用默认容器
            const defaultOutput = document.getElementById('output');
            if (defaultOutput) {
                defaultOutput.style.display = 'block';
                runner.outputEl = defaultOutput;
            }
        }

        // 重置多轮对话状态
        runner.currentRoundEl = null;
        runner.roundCounter = 0;

        // 查找标签数据
        const tabData = runner.tabs.find(t => t.id === tabId);

        if (tabId === 'new' || (tabData && tabData.isNew)) {
            // 新任务标签 - 允许编辑
            runner.resumeInput.value = '';
            runner.resumeInput.title = '';
            document.getElementById('prompt').value = '';
            runner.currentSessionId = null;

            Session.setSessionEditable(runner, true);
            // 启用"继续会话"复选框
            runner.updateContinueConversationCheckbox(true);
            // 取消勾选复选框
            if (runner.continueConversationCheckbox) {
                runner.continueConversationCheckbox.checked = false;
            }

            // 恢复工作目录（如果有保存的）
            if (tabData && tabData.workingDir) {
                WorkingDir.setWorkingDir(runner, tabData.workingDir);
            } else if (runner.defaultWorkingDir) {
                // 恢复默认工作目录
                runner.workingDirInput.value = runner.defaultWorkingDir;
            }

            // 显示占位符（如果容器为空）
            if (runner.outputEl && !runner.outputEl.querySelector('.conversation-round')) {
                runner.outputEl.innerHTML = '<div class="output-placeholder">执行任务后，输出将显示在这里...</div>';
            }
            Task.hideStats(runner);
        } else if (tabData) {
            // 历史会话标签 - 禁止编辑
            runner.resumeInput.value = tabData.sessionId;
            runner.resumeInput.title = tabData.sessionId;
            runner.currentSessionId = tabData.sessionId;
            Session.setSessionEditable(runner, false);
            // 禁用"继续会话"复选框（已通过 resume 指定会话）
            runner.updateContinueConversationCheckbox(false);
            // 取消勾选复选框
            if (runner.continueConversationCheckbox) {
                runner.continueConversationCheckbox.checked = false;
            }

            // 恢复工作目录
            if (tabData.workingDir) {
                WorkingDir.setWorkingDir(runner, tabData.workingDir);
            }

            // 如果容器为空，显示历史消息
            if (runner.outputEl && !runner.outputEl.querySelector('.conversation-round') && tabData.messages.length > 0) {
                MessageRenderer.displayHistoryMessagesToTab(runner, tabId, tabData.messages);
            } else if (runner.outputEl && tabData.messages.length === 0) {
                runner.outputEl.innerHTML = '<div class="output-placeholder">暂无历史消息</div>';
            }
        }

        // 在所有操作完成后，根据当前 tab 的运行状态更新按钮
        // 查找当前标签数据（可能已被上面的代码修改）
        const currentTabData = runner.tabs.find(t => t.id === tabId);
        const tabIsRunning = currentTabData ? (currentTabData.isRunning || false) : false;

        console.log('[Tabs] 切换 tab，更新按钮状态:', tabId, 'isRunning:', tabIsRunning);

        const sendBtn = document.getElementById('send-btn');
        const stopBtn = document.getElementById('stop-btn');
        if (sendBtn) sendBtn.disabled = tabIsRunning;
        if (stopBtn) stopBtn.style.display = tabIsRunning ? 'inline-block' : 'none';
    },

    /**
     * 关闭标签页
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} tabId - 标签页 ID
     */
    closeTab(runner, tabId) {
        // 不允许关闭默认的新任务标签
        if (tabId === 'new') return;

        const tabsBar = runner.tabsBar;

        // 移除标签
        const tabEl = tabsBar.querySelector(`[data-tab="${tabId}"]`);
        if (tabEl) tabEl.remove();

        // 移除对应的输出容器
        const outputContainer = document.getElementById(`output-${tabId}`);
        if (outputContainer) {
            outputContainer.remove();
        }

        // 从列表中移除
        runner.tabs = runner.tabs.filter(t => t.id !== tabId);

        // 如果关闭的是当前标签，切换到新任务标签
        if (runner.activeTabId === tabId) {
            this.switchToTab(runner, 'new');
        }
    }
};

// 导出到全局命名空间
window.Tabs = Tabs;