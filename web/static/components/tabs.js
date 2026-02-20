/**
 * 标签页组件模块
 * 处理标签页的创建、切换和关闭
 */

const Tabs = {
    /**
     * 创建新的任务标签页
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @returns {string} 新创建的标签页 ID
     */
    createNewSession(runner) {
        const tabId = `new-${++runner.tabCounter}`;
        const tabsBar = runner.tabsBar;
        const workingDir = runner.workingDirInput ? runner.workingDirInput.value : '';

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
        });

        // 切换到新标签
        this.switchToTab(runner, tabId);

        return tabId;
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
        });

        // 显示历史消息
        if (historyMessages.length > 0) {
            MessageRenderer.displayHistoryMessages(runner, historyMessages);
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
        const outputEl = runner.outputEl;

        // 更新标签高亮
        tabsBar.querySelectorAll('.tab-item').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });

        runner.activeTabId = tabId;

        // 重置多轮对话状态
        runner.currentRoundEl = null;
        runner.roundCounter = 0;

        // 先清空输出区，避免显示之前的内容
        outputEl.innerHTML = '';

        // 查找标签数据
        const tabData = runner.tabs.find(t => t.id === tabId);

        if (tabId === 'new' || (tabData && tabData.isNew)) {
            // 新任务标签 - 允许编辑
            runner.resumeInput.value = '';
            runner.resumeInput.title = '';
            document.getElementById('prompt').value = '';
            runner.currentSessionId = null;

            // 重置继续会话复选框
            document.getElementById('continue-conversation').checked = false;

            Session.setSessionEditable(runner, true);

            // 恢复工作目录（如果有保存的）
            if (tabData && tabData.workingDir) {
                WorkingDir.setWorkingDir(runner, tabData.workingDir);
            } else if (runner.defaultWorkingDir) {
                // 恢复默认工作目录
                runner.workingDirInput.value = runner.defaultWorkingDir;
            }

            // 显示占位符
            outputEl.innerHTML = '<div class="output-placeholder">执行任务后，输出将显示在这里...</div>';
            Task.hideStats(runner);
        } else if (tabData) {
            // 历史会话标签 - 禁止编辑
            runner.resumeInput.value = tabData.sessionId;
            runner.resumeInput.title = tabData.sessionId;
            runner.currentSessionId = tabData.sessionId;
            Session.setSessionEditable(runner, false);

            // 恢复工作目录
            if (tabData.workingDir) {
                WorkingDir.setWorkingDir(runner, tabData.workingDir);
            }

            // 显示历史消息
            if (tabData.messages && tabData.messages.length > 0) {
                MessageRenderer.displayHistoryMessages(runner, tabData.messages);
            } else {
                outputEl.innerHTML = '<div class="output-placeholder">暂无历史消息</div>';
            }
        }
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
