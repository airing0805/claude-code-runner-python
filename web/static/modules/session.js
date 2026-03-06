/**
 * 会话管理模块
 * 处理会话状态的设置和显示
 */

const Session = {
    /**
     * 设置会话是否可编辑
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {boolean} editable - 是否可编辑
     */
    setSessionEditable(runner, editable) {
        const resumeInput = runner.resumeInput;
        const workingDirInput = runner.workingDirInput;

        if (editable) {
            resumeInput.removeAttribute('readonly');
            resumeInput.classList.add('editable');
            workingDirInput.disabled = false;
            workingDirInput.readOnly = false;
        } else {
            resumeInput.setAttribute('readonly', true);
            resumeInput.classList.remove('editable');
            workingDirInput.disabled = true;
        }

        // 同时更新"继续会话"复选框状态
        runner.updateContinueConversationCheckbox(editable);
        // 取消勾选复选框
        if (runner.continueConversationCheckbox && !editable) {
            runner.continueConversationCheckbox.checked = false;
        }
    },

    /**
     * 更新会话显示
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string|null} sessionId - 会话 ID
     * @param {string|null} tabTitle - 标签标题
     * @param {Object|null} sessionData - 会话数据（包含 messageCount, createdTime 等）
     */
    updateSessionDisplay(runner, sessionId, tabTitle, sessionData = null) {
        // 更新会话ID输入框
        runner.resumeInput.value = sessionId || '';
        runner.resumeInput.title = sessionId || '';
        runner.currentSessionId = sessionId;

        // 更新会话信息栏（消息计数、创建时间）
        if (typeof SessionInfoBar !== 'undefined') {
            SessionInfoBar.updateSessionInfo({
                messageCount: sessionData?.messageCount || 0,
                createdTime: sessionData?.createdTime || null
            });
        }

        // 更新当前标签标题
        if (tabTitle && runner.activeTabId !== 'new') {
            const tabEl = runner.tabsBar.querySelector(`[data-tab="${runner.activeTabId}"]`);
            if (tabEl) {
                const titleEl = tabEl.querySelector('.tab-title');
                if (titleEl) {
                    titleEl.textContent = tabTitle.substring(0, 15) + (tabTitle.length > 15 ? '...' : '');
                    titleEl.title = tabTitle;
                }
            }

            // 更新标签数据
            const tabData = runner.tabs.find(t => t.id === runner.activeTabId);
            if (tabData) {
                tabData.title = tabTitle;
                tabData.sessionId = sessionId;
            }
        }
    },

    /**
     * 创建新会话（从项目路径）
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} projectPath - 项目路径
     */
    createNewSessionFromProject(runner, projectPath) {
        // 切换到当前会话视图
        Navigation.switchView(runner, Views.CURRENT_SESSION);

        // 创建新标签页
        const tabId = Tabs.createNewSession(runner);

        // 设置工作目录为选中的项目路径
        WorkingDir.setWorkingDir(runner, projectPath);

        // 更新标签页的工作目录
        const tabData = runner.tabs.find(t => t.id === tabId);
        if (tabData) {
            tabData.workingDir = projectPath;
        }

        // 重置会话信息栏
        if (typeof SessionInfoBar !== 'undefined') {
            SessionInfoBar.reset();
        }

        // 聚焦到任务输入框
        document.getElementById('prompt').focus();
    }
};

// 导出到全局命名空间
window.Session = Session;
