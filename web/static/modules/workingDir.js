/**
 * 工作目录管理模块
 * 处理工作目录的加载、选择和设置
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

            // 添加默认工作目录（如果不在列表中）
            const defaultDir = runner.workingDirInput ? runner.workingDirInput.value : '';
            if (defaultDir && !runner.workingDirs.includes(defaultDir)) {
                runner.workingDirs.unshift(defaultDir);
            }

            this.renderWorkingDirOptions(runner);
        } catch (error) {
            console.error('加载工作目录失败:', error);
        }
    },

    /**
     * 渲染工作目录选项
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    renderWorkingDirOptions(runner) {
        if (!runner.workingDirInput || !runner.workingDirList) return;
        const currentValue = runner.workingDirInput.value;
        runner.workingDirList.innerHTML = '';

        runner.workingDirs.forEach(dir => {
            const option = document.createElement('option');
            option.value = dir;
            runner.workingDirList.appendChild(option);
        });

        // 恢复选中值
        if (currentValue && runner.workingDirs.includes(currentValue)) {
            runner.workingDirInput.value = currentValue;
        }
    },

    /**
     * 设置工作目录
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} path - 工作目录路径
     */
    setWorkingDir(runner, path) {
        // 如果路径不在列表中，添加到列表开头
        if (path && !runner.workingDirs.includes(path)) {
            runner.workingDirs.unshift(path);
            this.renderWorkingDirOptions(runner);
        }
        runner.workingDirInput.value = path;
        runner.workingDirInput.title = path;  // 更新 tooltip
    }
};

// 导出到全局命名空间
window.WorkingDir = WorkingDir;
