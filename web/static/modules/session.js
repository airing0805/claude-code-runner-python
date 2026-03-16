/**
 * 会话管理模块
 * 处理会话状态的设置和显示
 * v12.0.0.3 - 移除 Tab 系统，改为单会话模式
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
            // v12: 工作空间由 WorkspaceCombo 管理
            if (runner.workspaceCombo) {
                runner.workspaceCombo.setDisabled(false);
            }
        } else {
            resumeInput.setAttribute('readonly', true);
            resumeInput.classList.remove('editable');
            // v12: 工作空间由 WorkspaceCombo 管理
            if (runner.workspaceCombo) {
                runner.workspaceCombo.setDisabled(true);
            }
        }

        // 同时更新"继续会话"复选框状态
        if (typeof ContinueSessionManager !== 'undefined') {
            ContinueSessionManager.updateContinueConversationCheckbox(editable);
        }
        // 取消勾选复选框
        if (runner.continueConversationCheckbox && !editable) {
            runner.continueConversationCheckbox.checked = false;
        }
    },

    /**
     * 更新会话显示
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string|null} sessionId - 会话 ID
     * @param {string|null} title - 会话标题（v12: 不再用于 Tab，保留用于日志）
     * @param {Object|null} sessionData - 会话数据（包含 messageCount, createdTime 等）
     */
    updateSessionDisplay(runner, sessionId, title, sessionData = null) {
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

        // v12: 不再需要更新 Tab 标题
    },

    /**
     * 创建新会话（从项目路径）
     * v12: 简化为单会话模式
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} projectPath - 项目路径
     */
    createNewSessionFromProject(runner, projectPath) {
        // 切换到当前会话视图
        Navigation.switchView(runner, Views.CURRENT_SESSION);

        // 设置工作目录为选中的项目路径
        WorkingDir.setWorkingDir(runner, projectPath);

        // v12: 更新工作空间组合控件
        if (runner.workspaceCombo) {
            runner.workspaceCombo.setValue(projectPath);
        }

        // 重置会话信息栏
        if (typeof SessionInfoBar !== 'undefined') {
            SessionInfoBar.reset();
        }

        // 聚焦到任务输入框
        document.getElementById('prompt').focus();
    },

    /**
     * 清空当前会话
     * v12.0.0.3.4: 新增方法，用于新会话功能
     * 实现需求：清空提示词、消息区域、重置会话ID、取消勾选"继续会话"
     * 保持工作空间不变
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {boolean} skipConfirm - 是否跳过确认对话框
     * @returns {Promise<boolean>} 是否成功清空
     */
    async clearCurrentSession(runner, skipConfirm = false) {
        // 检查是否有未保存的内容
        const hasUnsavedContent = this._checkUnsavedContent(runner);

        // 如果有未保存内容且未跳过确认，显示确认对话框
        if (hasUnsavedContent && !skipConfirm) {
            const confirmed = await this._showConfirmDialog();
            if (!confirmed) {
                return false;
            }
        }

        // 调用后端 API 结束当前会话
        if (runner.currentSessionId) {
            try {
                await fetch('/api/task/new-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: runner.currentSessionId }),
                });
                console.log('[Session] 已结束当前会话:', runner.currentSessionId);
            } catch (error) {
                console.error('[Session] 结束会话失败:', error);
                // 继续执行清空操作，即使 API 调用失败
            }
        }

        // 清空会话 ID
        runner.currentSessionId = null;
        runner.resumeInput.value = '';
        runner.resumeInput.title = '';

        // 清空输出区域
        if (typeof Task !== 'undefined') {
            Task.clearOutput(runner);
        }

        // 清空输入框
        const promptInput = document.getElementById('prompt');
        if (promptInput) {
            promptInput.value = '';
        }

        // 重置工具配置为默认状态（全选）
        this._resetToolsConfig(runner);

        // 启用"继续会话"复选框
        if (typeof ContinueSessionManager !== 'undefined') {
            ContinueSessionManager.updateContinueConversationCheckbox(true);
        }
        if (runner.continueConversationCheckbox) {
            runner.continueConversationCheckbox.checked = false;
        }

        // 允许编辑
        this.setSessionEditable(runner, true);

        // 重置会话信息栏
        if (typeof SessionInfoBar !== 'undefined') {
            SessionInfoBar.reset();
        }

        // 工作空间保持不变（由 WorkspaceCombo 管理）

        return true;
    },

    /**
     * 检查是否有未保存的内容
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @returns {boolean} 是否有未保存内容
     * @private
     */
    _checkUnsavedContent(runner) {
        // 检查输出区域是否有内容
        const outputContainer = document.querySelector('.output-container');
        if (outputContainer && outputContainer.children.length > 0) {
            return true;
        }

        // 检查输入框是否有内容
        const promptInput = document.getElementById('prompt');
        if (promptInput && promptInput.value.trim()) {
            return true;
        }

        return false;
    },

    /**
     * 显示确认对话框
     * @returns {Promise<boolean>} 用户是否确认
     * @private
     */
    async _showConfirmDialog() {
        // 使用浏览器原生确认对话框
        return confirm('当前会话未保存，是否确定新建会话？');
    },

    /**
     * 重置工具配置为默认状态（全选）
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @private
     */
    _resetToolsConfig(runner) {
        if (typeof ToolsMultiselect !== 'undefined' && runner.availableTools) {
            // 将所有工具设置为选中状态（默认行为）
            runner.availableTools.forEach(tool => {
                tool.selected = true;
            });

            // 更新 UI 显示
            ToolsMultiselect.updateToolsDisplay(runner);

            // 更新所有 checkbox 状态
            runner.availableTools.forEach(tool => {
                const checkbox = document.getElementById(`tool-${tool.name}`);
                if (checkbox) {
                    checkbox.checked = true;
                }
            });
        }
    }
};

// 导出到全局命名空间
window.Session = Session;
