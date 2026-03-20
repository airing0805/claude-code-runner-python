/**
 * 工作目录管理模块
 * 处理工作目录的加载、选择和设置
 *
 * v12.0.0.3.2 - 更新支持 WorkspaceCombo 组件
 * v12.0.0.4 - 移除对 workingDirInput 和 workingDirList 的依赖
 */

const WorkingDir = {
    /**
     * 加载工作目录列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    async loadWorkingDirs(runner) {
        try {
            const response = await fetch('/api/projects');
            const data = await response.json();
            const projects = data.projects || [];

            // 提取所有项目路径作为工作目录选项
            runner.workingDirs = projects.map(p => p.path);

            // v12: workingDirInput 已废弃，默认值在 app.js 的 initWorkspaceCombo 中设置

            // 更新 WorkspaceCombo 组件的历史记录
            if (runner.workspaceCombo) {
                runner.workspaceCombo.setHistory(runner.workingDirs);
            }
        } catch (error) {
            console.error('加载工作目录失败:', error);
            // 确保即使加载失败，workingDirs 也是一个数组
            if (!runner.workingDirs) {
                runner.workingDirs = [];
            }
        }
    },

    /**
     * 设置工作目录
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} path - 工作目录路径
     */
    setWorkingDir(runner, path) {
        if (!path) return;

        // 如果路径不在列表中，添加到列表开头
        if (!runner.workingDirs.includes(path)) {
            runner.workingDirs.unshift(path);
            // 更新 WorkspaceCombo 组件的历史记录
            if (runner.workspaceCombo) {
                runner.workspaceCombo.setHistory(runner.workingDirs);
            }
        }

        // 更新 WorkspaceCombo 的值
        if (runner.workspaceCombo) {
            runner.workspaceCombo.setValue(path);
        }
    },

    /**
     * 渲染工作目录选项（兼容旧版本）
     * v12.0.0.4: 工作目录由 WorkspaceCombo 组件管理，此方法保留用于兼容
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    renderWorkingDirOptions(runner) {
        // v12: 工作目录由 WorkspaceCombo 组件管理
        // 此方法保留用于兼容旧代码调用（如 history.js）
        // 更新 WorkspaceCombo 组件的历史记录
        if (runner.workspaceCombo && runner.workingDirs) {
            runner.workspaceCombo.setHistory(runner.workingDirs);
        }
    }
};

// 导出到全局命名空间
window.WorkingDir = WorkingDir;
