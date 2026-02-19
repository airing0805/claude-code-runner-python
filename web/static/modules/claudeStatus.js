/**
 * Claude 状态模块
 * 负责加载和展示 Claude Code 环境信息
 */

const ClaudeStatus = {
    /** 是否已加载数据 */
    isLoaded: false,

    /**
     * 初始化 Claude 状态模块
     */
    init() {
        this.bindEvents();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 刷新环境变量按钮
        const refreshBtn = document.getElementById("refresh-env-btn");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => this.loadEnvInfo());
        }
    },

    /**
     * 当视图显示时加载数据
     */
    onShow() {
        if (!this.isLoaded) {
            this.loadAllData();
            this.isLoaded = true;
        }
        // 加载 MCP 服务器数据
        if (typeof MCPManager !== 'undefined') {
            MCPManager.onShow();
        }
        // 加载插件数据
        if (typeof PluginManager !== 'undefined') {
            PluginManager.onShow();
        }
    },

    /**
     * 加载所有数据
     */
    async loadAllData() {
        await Promise.all([
            this.loadVersionInfo(),
            this.loadEnvInfo(),
            this.loadConfigInfo(),
            this.loadStatsInfo(),
            this.loadPermissionModes(),
            this.loadToolsList(),
        ]);
    },

    /**
     * 加载版本信息
     */
    async loadVersionInfo() {
        try {
            const response = await fetch("/api/claude/version");
            const data = await response.json();

            document.getElementById("cli-version").textContent = data.cli_version;
            document.getElementById("sdk-version").textContent = data.sdk_version;
            document.getElementById("os-info").textContent = `${data.runtime.os} ${data.runtime.os_version}`;
            document.getElementById("python-version").textContent = data.runtime.python_version;
        } catch (error) {
            console.error("加载版本信息失败:", error);
            this.showError("version-section", "加载版本信息失败");
        }
    },

    /**
     * 加载环境变量
     */
    async loadEnvInfo() {
        const envList = document.getElementById("env-list");
        if (!envList) return;

        envList.innerHTML = '<div class="loading-placeholder">加载中...</div>';

        try {
            const response = await fetch("/api/claude/env");
            const data = await response.json();

            const variables = data.variables;
            if (Object.keys(variables).length === 0) {
                envList.innerHTML = '<div class="empty-placeholder">暂无环境变量</div>';
                return;
            }

            // 按键排序
            const sortedKeys = Object.keys(variables).sort();

            let html = '<table class="env-table">';
            html += "<thead><tr><th>变量名</th><th>值</th></tr></thead>";
            html += "<tbody>";

            for (const key of sortedKeys) {
                const value = variables[key];
                const isSensitive = value === "***";
                const valueClass = isSensitive ? "env-value env-value-sensitive" : "env-value";

                html += `<tr>`;
                html += `<td class="env-key" title="点击复制" data-copy="${key}">${key}</td>`;
                html += `<td class="${valueClass}">${value}</td>`;
                html += `</tr>`;
            }

            html += "</tbody></table>";
            envList.innerHTML = html;

            // 绑定复制事件
            this.bindCopyEvents();
        } catch (error) {
            console.error("加载环境变量失败:", error);
            envList.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 加载配置信息
     */
    async loadConfigInfo() {
        try {
            const response = await fetch("/api/claude/config");
            const data = await response.json();

            document.getElementById("working-dir-config").textContent = data.working_dir;
            document.getElementById("permission-mode").textContent = data.default_permission_mode;
            document.getElementById("allowed-tools").textContent = data.allowed_tools.join(", ");
        } catch (error) {
            console.error("加载配置信息失败:", error);
            this.showError("config-section", "加载配置信息失败");
        }
    },

    /**
     * 加载工具使用统计
     */
    async loadStatsInfo() {
        const statsSection = document.getElementById("stats-section");
        if (!statsSection) return;

        try {
            const response = await fetch("/api/claude/stats");
            const data = await response.json();

            // 构建工具使用统计 HTML
            const toolsUsage = data.tools_usage;
            const sortedTools = Object.entries(toolsUsage).sort((a, b) => b[1] - a[1]);

            let html = '<div class="tools-usage-grid">';
            for (const [tool, count] of sortedTools) {
                const percentage = data.task_stats.total > 0
                    ? Math.round((count / data.task_stats.total) * 100)
                    : 0;
                html += `
                    <div class="tool-usage-item">
                        <span class="tool-name">${tool}</span>
                        <div class="tool-usage-bar">
                            <div class="tool-usage-fill" style="width: ${percentage}%"></div>
                        </div>
                        <span class="tool-count">${count}</span>
                    </div>
                `;
            }
            if (sortedTools.length === 0) {
                html += '<div class="empty-placeholder">暂无统计数据</div>';
            }
            html += '</div>';

            // 添加任务统计
            const taskStats = data.task_stats;
            html += `
                <div class="task-stats">
                    <div class="task-stat-item">
                        <span class="task-stat-label">总任务数</span>
                        <span class="task-stat-value">${taskStats.total}</span>
                    </div>
                    <div class="task-stat-item">
                        <span class="task-stat-label">成功</span>
                        <span class="task-stat-value task-stat-success">${taskStats.success}</span>
                    </div>
                    <div class="task-stat-item">
                        <span class="task-stat-label">失败</span>
                        <span class="task-stat-value task-stat-failed">${taskStats.failed}</span>
                    </div>
                    <div class="task-stat-item">
                        <span class="task-stat-label">平均耗时</span>
                        <span class="task-stat-value">${(taskStats.avg_duration_ms / 1000).toFixed(1)}s</span>
                    </div>
                    <div class="task-stat-item">
                        <span class="task-stat-label">总费用</span>
                        <span class="task-stat-value">$${taskStats.total_cost_usd.toFixed(4)}</span>
                    </div>
                    <div class="task-stat-item">
                        <span class="task-stat-label">文件变更</span>
                        <span class="task-stat-value">${data.files_changed}</span>
                    </div>
                </div>
            `;

            const content = statsSection.querySelector(".status-section-content");
            if (content) {
                content.innerHTML = html;
            }
        } catch (error) {
            console.error("加载统计信息失败:", error);
            this.showError("stats-section", "加载统计信息失败");
        }
    },

    /**
     * 加载权限模式说明
     */
    async loadPermissionModes() {
        const modesSection = document.getElementById("permission-modes-section");
        if (!modesSection) return;

        try {
            const response = await fetch("/api/claude/permission-modes");
            const data = await response.json();

            let html = '<div class="permission-modes-list">';
            for (const mode of data.modes) {
                html += `
                    <div class="permission-mode-card">
                        <div class="permission-mode-name">${mode.name}</div>
                        <div class="permission-mode-description">${mode.description}</div>
                        <div class="permission-mode-scenarios">
                            ${mode.scenarios.map(s => `<span class="scenario-tag">${s}</span>`).join('')}
                        </div>
                    </div>
                `;
            }
            html += '</div>';

            const content = modesSection.querySelector(".status-section-content");
            if (content) {
                content.innerHTML = html;
            }
        } catch (error) {
            console.error("加载权限模式失败:", error);
            this.showError("permission-modes-section", "加载权限模式失败");
        }
    },

    /**
     * 加载工具列表
     */
    async loadToolsList() {
        const toolsSection = document.getElementById("tools-list-section");
        if (!toolsSection) return;

        try {
            const response = await fetch("/api/tools");
            const data = await response.json();

            // 按分类分组
            const categories = {};
            for (const tool of data.tools) {
                const cat = tool.category || "其他";
                if (!categories[cat]) {
                    categories[cat] = [];
                }
                categories[cat].push(tool);
            }

            let html = '<div class="tools-list">';
            for (const [category, tools] of Object.entries(categories)) {
                html += `
                    <div class="tools-category">
                        <h3 class="tools-category-title">${category}</h3>
                        <div class="tools-category-list">
                `;
                for (const tool of tools) {
                    const modifiesClass = tool.modifies_files ? "tool-modifies" : "tool-readonly";
                    html += `
                        <div class="tool-item">
                            <span class="tool-item-name">${tool.name}</span>
                            <span class="tool-item-desc">${tool.description}</span>
                            <span class="tool-item-badge ${modifiesClass}">${tool.modifies_files ? '会修改文件' : '只读'}</span>
                        </div>
                    `;
                }
                html += '</div></div>';
            }
            html += '</div>';

            const content = toolsSection.querySelector(".status-section-content");
            if (content) {
                content.innerHTML = html;
            }
        } catch (error) {
            console.error("加载工具列表失败:", error);
            this.showError("tools-list-section", "加载工具列表失败");
        }
    },

    /**
     * 绑定复制事件
     */
    bindCopyEvents() {
        const envKeys = document.querySelectorAll(".env-key");
        envKeys.forEach((el) => {
            el.addEventListener("click", async () => {
                const text = el.dataset.copy;
                try {
                    await navigator.clipboard.writeText(text);
                    this.showToast(`已复制: ${text}`);
                } catch (err) {
                    console.error("复制失败:", err);
                }
            });
        });
    },

    /**
     * 显示错误信息
     */
    showError(sectionId, message) {
        const section = document.getElementById(sectionId);
        if (section) {
            const content = section.querySelector(".status-section-content");
            if (content) {
                content.innerHTML = `<div class="error-placeholder">${message}</div>`;
            }
        }
    },

    /**
     * 显示提示消息
     */
    showToast(message) {
        // 使用全局的 toast 函数（如果存在）
        if (typeof window.showToast === "function") {
            window.showToast(message);
            return;
        }

        // 简单的提示实现
        const toast = document.createElement("div");
        toast.className = "toast-message";
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            z-index: 10000;
            animation: fadeInOut 2s ease-in-out;
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 2000);
    },
};

// 添加淡入淡出动画
const style = document.createElement("style");
style.textContent = `
    @keyframes fadeInOut {
        0% { opacity: 0; transform: translateX(-50%) translateY(10px); }
        15% { opacity: 1; transform: translateX(-50%) translateY(0); }
        85% { opacity: 1; transform: translateX(-50%) translateY(0); }
        100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
    }

    .status-section {
        background: var(--card-bg, #fff);
        border-radius: 8px;
        margin-bottom: 20px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .status-section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 20px;
        background: var(--header-bg, #f5f5f5);
        border-bottom: 1px solid var(--border-color, #eee);
    }

    .status-section-header h2 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary, #333);
    }

    .status-section-content {
        padding: 20px;
    }

    .status-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;
    }

    .status-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .status-item-full {
        grid-column: 1 / -1;
    }

    .status-label {
        font-size: 12px;
        color: var(--text-secondary, #666);
        font-weight: 500;
    }

    .status-value {
        font-size: 14px;
        color: var(--text-primary, #333);
        word-break: break-all;
    }

    .env-table {
        width: 100%;
        border-collapse: collapse;
    }

    .env-table th,
    .env-table td {
        padding: 10px 12px;
        text-align: left;
        border-bottom: 1px solid var(--border-color, #eee);
    }

    .env-table th {
        font-weight: 600;
        background: var(--header-bg, #f5f5f5);
        font-size: 12px;
        color: var(--text-secondary, #666);
    }

    .env-key {
        font-family: monospace;
        cursor: pointer;
        color: var(--text-primary, #333);
    }

    .env-key:hover {
        color: var(--primary-color, #007bff);
    }

    .env-value {
        font-family: monospace;
        word-break: break-all;
    }

    .env-value-sensitive {
        color: var(--text-secondary, #666);
    }

    .loading-placeholder,
    .empty-placeholder,
    .error-placeholder {
        text-align: center;
        padding: 40px;
        color: var(--text-secondary, #666);
    }

    .error-placeholder {
        color: var(--error-color, #dc3545);
    }

    /* v0.3.2 工具统计样式 */
    .tools-usage-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 12px;
        margin-bottom: 20px;
    }

    .tool-usage-item {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .tool-usage-item .tool-name {
        font-weight: 500;
        min-width: 80px;
    }

    .tool-usage-bar {
        flex: 1;
        height: 8px;
        background: var(--border-color, #eee);
        border-radius: 4px;
        overflow: hidden;
    }

    .tool-usage-fill {
        height: 100%;
        background: var(--primary-color, #007bff);
        border-radius: 4px;
        transition: width 0.3s ease;
    }

    .tool-usage-item .tool-count {
        min-width: 30px;
        text-align: right;
        font-family: monospace;
        color: var(--text-secondary, #666);
    }

    .task-stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        padding-top: 16px;
        border-top: 1px solid var(--border-color, #eee);
    }

    .task-stat-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 12px;
        background: var(--header-bg, #f5f5f5);
        border-radius: 8px;
    }

    .task-stat-label {
        font-size: 12px;
        color: var(--text-secondary, #666);
        margin-bottom: 4px;
    }

    .task-stat-value {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-primary, #333);
    }

    .task-stat-success {
        color: var(--success-color, #28a745);
    }

    .task-stat-failed {
        color: var(--error-color, #dc3545);
    }

    /* 权限模式样式 */
    .permission-modes-list {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 16px;
    }

    .permission-mode-card {
        padding: 16px;
        background: var(--header-bg, #f5f5f5);
        border-radius: 8px;
        border-left: 4px solid var(--primary-color, #007bff);
    }

    .permission-mode-name {
        font-weight: 600;
        font-size: 16px;
        color: var(--text-primary, #333);
        margin-bottom: 8px;
    }

    .permission-mode-description {
        font-size: 14px;
        color: var(--text-secondary, #666);
        margin-bottom: 12px;
    }

    .permission-mode-scenarios {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }

    .scenario-tag {
        font-size: 12px;
        padding: 2px 8px;
        background: var(--card-bg, #fff);
        border: 1px solid var(--border-color, #eee);
        border-radius: 12px;
        color: var(--text-secondary, #666);
    }

    /* 工具列表样式 */
    .tools-list {
        display: flex;
        flex-direction: column;
        gap: 20px;
    }

    .tools-category-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-primary, #333);
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--primary-color, #007bff);
    }

    .tools-category-list {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 12px;
    }

    .tool-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: var(--header-bg, #f5f5f5);
        border-radius: 8px;
    }

    .tool-item-name {
        font-weight: 600;
        font-family: monospace;
        min-width: 80px;
    }

    .tool-item-desc {
        flex: 1;
        font-size: 13px;
        color: var(--text-secondary, #666);
    }

    .tool-item-badge {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 10px;
    }

    .tool-modifies {
        background: #fff3cd;
        color: #856404;
    }

    .tool-readonly {
        background: #d4edda;
        color: #155724;
    }
`;
document.head.appendChild(style);

// 导出模块
window.ClaudeStatus = ClaudeStatus;
