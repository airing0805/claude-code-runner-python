/**
 * Claude 状态管理核心模块
 * 负责加载和管理 Claude Code 环境信息
 */

const ClaudeStatusCore = {
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

        // 文档 tab 切换
        this.bindDocsTabs();
    },

    /**
     * 绑定文档 tab 切换事件
     */
    bindDocsTabs() {
        const tabs = document.querySelectorAll('.docs-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.dataset.tab;
                this.switchDocsTab(targetTab);
            });
        });
    },

    /**
     * 切换文档 tab
     */
    switchDocsTab(targetTab) {
        // 更新 tab 按钮状态
        document.querySelectorAll('.docs-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === targetTab);
        });

        // 更新 tab 内容显示
        document.querySelectorAll('.docs-tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.id === targetTab);
        });
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
     * 当文档视图显示时加载文档数据
     */
    onDocsShow() {
        if (!this.isLoaded) {
            this.loadAllData();
            this.isLoaded = true;
        }
        // 绑定文档 tab 切换事件（如果还未绑定）
        this.bindDocsTabs();
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
            this.loadToolsDocs(),
            this.loadAgentsDocs(),
            this.loadCommandsDocs(),
            this.loadBestPractices(),
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
        const statsSection = document.getElementById("tools-usage-section");
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
                html += '<div class="empty-placeholder">暂无统计数据<br><small>执行任务后，这里将显示工具使用统计</small></div>';
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
            this.showError("tools-usage-section", "加载统计信息失败");
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

// 导出模块
window.ClaudeStatusCore = ClaudeStatusCore;