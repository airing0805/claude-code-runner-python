/**
 * Task 模块 v12
 * 处理任务状态更新相关功能
 */

const TaskModule = {
    /**
     * 更新状态中的 isStreaming
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {boolean} isStreaming - 是否正在流式输出
     */
    updateIsStreamingState(runner, isStreaming) {
        runner.state.isStreaming = isStreaming;
    },

    /**
     * 更新状态中的 sessionId
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} sessionId - 会话 ID
     */
    updateSessionIdState(runner, sessionId) {
        runner.state.sessionId = sessionId;
        runner.state.sessionStatus = sessionId ? 'resumed' : 'new';
    },

    /**
     * 更新状态中的 workspace
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} workspace - 工作空间路径
     */
    updateWorkspaceState(runner, workspace) {
        runner.state.workspace = workspace;
        // 添加到工作空间历史记录
        if (workspace && typeof WorkspaceCombo !== 'undefined') {
            const history = runner.state.workspaceHistory || [];
            if (!history.includes(workspace)) {
                history.unshift(workspace);
                // 最多保留 10 条
                if (history.length > 10) {
                    history.pop();
                }
                runner.state.workspaceHistory = history;
            }
        }
    },
};
