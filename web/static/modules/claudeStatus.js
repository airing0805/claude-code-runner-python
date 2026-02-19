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
     * 加载工具文档
     */
    async loadToolsDocs() {
        const container = document.getElementById("tools-docs-list");
        if (!container) return;

        try {
            const response = await fetch("/api/claude/docs/tools");
            const data = await response.json();

            let html = '<div class="docs-accordion">';
            for (const tool of data.tools) {
                const modifiesClass = tool.modifies_files ? "tool-modifies" : "tool-readonly";
                html += `
                    <div class="docs-accordion-item">
                        <div class="docs-accordion-header">
                            <span class="docs-item-name">${tool.name}</span>
                            <span class="docs-item-category">${tool.category}</span>
                            <span class="docs-item-badge ${modifiesClass}">${tool.modifies_files ? '会修改文件' : '只读'}</span>
                            <span class="docs-accordion-arrow">▼</span>
                        </div>
                        <div class="docs-accordion-content">
                            <p class="docs-description">${tool.description}</p>
                            <div class="docs-section">
                                <h4>参数</h4>
                                <table class="docs-table">
                                    <thead>
                                        <tr>
                                            <th>名称</th>
                                            <th>类型</th>
                                            <th>必填</th>
                                            <th>说明</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${tool.parameters.map(p => `
                                            <tr>
                                                <td><code>${p.name}</code></td>
                                                <td>${p.type}</td>
                                                <td>${p.required ? '是' : '否'}</td>
                                                <td>${p.description}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                            <div class="docs-section">
                                <h4>示例</h4>
                                <pre class="docs-code"><code>${JSON.stringify(tool.example.input, null, 2)}</code></pre>
                                <p class="docs-example-desc">${tool.example.description}</p>
                            </div>
                        </div>
                    </div>
                `;
            }
            html += '</div>';

            container.innerHTML = html;
            this.bindDocsAccordion();
        } catch (error) {
            console.error("加载工具文档失败:", error);
            container.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 加载代理文档
     */
    async loadAgentsDocs() {
        const container = document.getElementById("agents-docs-list");
        if (!container) return;

        try {
            const response = await fetch("/api/claude/docs/agents");
            const data = await response.json();

            let html = '<div class="docs-grid">';
            for (const agent of data.agents) {
                html += `
                    <div class="docs-card">
                        <div class="docs-card-header">
                            <span class="docs-card-title">${agent.name}</span>
                        </div>
                        <div class="docs-card-body">
                            <p>${agent.description}</p>
                            <div class="docs-tags">
                                ${agent.use_cases.map(uc => `<span class="docs-tag">${uc}</span>`).join('')}
                            </div>
                        </div>
                    </div>
                `;
            }
            html += '</div>';

            container.innerHTML = html;
        } catch (error) {
            console.error("加载代理文档失败:", error);
            container.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 加载命令文档
     */
    async loadCommandsDocs() {
        const container = document.getElementById("commands-docs-list");
        if (!container) return;

        try {
            const response = await fetch("/api/claude/docs/commands");
            const data = await response.json();

            let html = '<div class="docs-commands-list">';
            for (const cmd of data.commands) {
                html += `
                    <div class="docs-command-item">
                        <div class="docs-command-header">
                            <code class="docs-command-name">${cmd.name}</code>
                            <span class="docs-command-usage">${cmd.usage}</span>
                        </div>
                        <div class="docs-command-body">
                            <p>${cmd.description}</p>
                            ${cmd.options && cmd.options.length > 0 ? `
                                <div class="docs-command-options">
                                    <h4>选项</h4>
                                    <table class="docs-table">
                                        <thead>
                                            <tr>
                                                <th>选项</th>
                                                <th>说明</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${cmd.options.map(o => `
                                                <tr>
                                                    <td><code>${o.name}</code></td>
                                                    <td>${o.description}</td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }
            html += '</div>';

            container.innerHTML = html;
        } catch (error) {
            console.error("加载命令文档失败:", error);
            container.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 加载最佳实践
     */
    async loadBestPractices() {
        const container = document.getElementById("best-practices-docs-list");
        if (!container) return;

        try {
            const response = await fetch("/api/claude/docs/best-practices");
            const data = await response.json();

            let html = `
                <div class="docs-best-practices">
                    <div class="docs-section">
                        <h3>🛠️ 工具选择建议</h3>
                        <div class="docs-practice-grid">
                            <div class="docs-practice-card">
                                <h4>📖 只读操作</h4>
                                <div class="docs-tools-list">
                                    ${data.tool_selection.read_only.map(t => `<span class="docs-tool-tag">${t}</span>`).join('')}
                                </div>
                                <p class="docs-practice-desc">用于查看和分析文件，不修改任何内容</p>
                            </div>
                            <div class="docs-practice-card">
                                <h4>✏️ 修改文件</h4>
                                <div class="docs-tools-list">
                                    ${data.tool_selection.modify_files.map(t => `<span class="docs-tool-tag">${t}</span>`).join('')}
                                </div>
                                <p class="docs-practice-desc">用于创建、编辑和删除文件</p>
                            </div>
                            <div class="docs-practice-card">
                                <h4>⚡ 执行命令</h4>
                                <div class="docs-tools-list">
                                    ${data.tool_selection.execute.map(t => `<span class="docs-tool-tag">${t}</span>`).join('')}
                                </div>
                                <p class="docs-practice-desc">用于执行系统命令和脚本</p>
                            </div>
                            <div class="docs-practice-card">
                                <h4>🔍 网络搜索</h4>
                                <div class="docs-tools-list">
                                    ${data.tool_selection.search.map(t => `<span class="docs-tool-tag">${t}</span>`).join('')}
                                </div>
                                <p class="docs-practice-desc">用于搜索网络和获取网页内容</p>
                            </div>
                        </div>
                    </div>

                    <div class="docs-section">
                        <h3>🔐 权限模式选择</h3>
                        <div class="docs-modes-grid">
                            ${data.permission_mode_guide.map(mode => `
                                <div class="docs-mode-card">
                                    <div class="docs-mode-name">${mode.mode}</div>
                                    <div class="docs-mode-scenario">${mode.scenario}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <div class="docs-section">
                        <h3>⚠️ 错误处理模式</h3>
                        <div class="docs-error-patterns">
                            <div class="docs-error-pattern">
                                <code>try-catch</code>
                                <span>${data.error_handling.try_catch}</span>
                            </div>
                            <div class="docs-error-pattern">
                                <code>logging</code>
                                <span>${data.error_handling.logging}</span>
                            </div>
                            <div class="docs-error-pattern">
                                <code>user_message</code>
                                <span>${data.error_handling.user_message}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            container.innerHTML = html;
        } catch (error) {
            console.error("加载最佳实践失败:", error);
            container.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 绑定文档手风琴展开/收起事件
     */
    bindDocsAccordion() {
        const headers = document.querySelectorAll('.docs-accordion-header');
        headers.forEach(header => {
            header.addEventListener('click', () => {
                const item = header.parentElement;
                item.classList.toggle('active');
            });
        });
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
        background: var(--card-bg, #1e293b);
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
        background: var(--header-bg, #334155);
        border-bottom: 1px solid var(--border-color, #334155);
    }

    .status-section-header h2 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary, #e2e8f0);
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
        color: var(--text-secondary, #94a3b8);
        font-weight: 500;
    }

    .status-value {
        font-size: 14px;
        color: var(--text-primary, #e2e8f0);
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
        border-bottom: 1px solid var(--border-color, #334155);
    }

    .env-table th {
        font-weight: 600;
        background: var(--header-bg, #334155);
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
    }

    .env-key {
        font-family: monospace;
        cursor: pointer;
        color: var(--text-primary, #e2e8f0);
    }

    .env-key:hover {
        color: var(--primary-color, #007bff);
    }

    .env-value {
        font-family: monospace;
        word-break: break-all;
    }

    .env-value-sensitive {
        color: var(--text-secondary, #94a3b8);
    }

    .loading-placeholder,
    .empty-placeholder,
    .error-placeholder {
        text-align: center;
        padding: 40px;
        color: var(--text-secondary, #94a3b8);
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
        background: var(--border-color, #334155);
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
        color: var(--text-secondary, #94a3b8);
    }

    .task-stats {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        padding-top: 16px;
        border-top: 1px solid var(--border-color, #334155);
    }

    .task-stat-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 12px;
        background: var(--header-bg, #334155);
        border-radius: 8px;
    }

    .task-stat-label {
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
        margin-bottom: 4px;
    }

    .task-stat-value {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-primary, #e2e8f0);
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
        background: var(--header-bg, #334155);
        border-radius: 8px;
        border-left: 4px solid var(--primary-color);
    }

    .permission-mode-name {
        font-weight: 600;
        font-size: 16px;
        color: var(--text-primary);
        margin-bottom: 8px;
    }

    .permission-mode-description {
        font-size: 14px;
        color: var(--text-secondary);
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
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        color: var(--text-secondary);
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
        color: var(--text-primary);
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--primary-color);
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
        background: var(--header-bg);
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
        color: var(--text-secondary);
    }

    .tool-item-badge {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 10px;
    }

    .tool-modifies {
        background: var(--warning-color);
        color: #fff;
    }

    .tool-readonly {
        background: var(--success-color);
        color: #fff;
    }

    /* v0.3.3 文档展示样式 */
    .docs-tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 20px;
        border-bottom: 1px solid var(--border-color, #334155);
        padding-bottom: 12px;
    }

    .docs-tab {
        padding: 8px 16px;
        border: none;
        background: transparent;
        color: var(--text-secondary, #94a3b8);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        border-radius: 6px;
        transition: all 0.2s ease;
    }

    .docs-tab:hover {
        background: var(--header-bg, #334155);
        color: var(--text-primary, #e2e8f0);
    }

    .docs-tab.active {
        background: var(--primary-color, #007bff);
        color: #fff;
    }

    .docs-tab-content {
        min-height: 200px;
    }

    .docs-tab-pane {
        display: none;
    }

    .docs-tab-pane.active {
        display: block;
    }

    /* 手风琴样式 */
    .docs-accordion {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .docs-accordion-item {
        background: var(--header-bg, #334155);
        border-radius: 8px;
        overflow: hidden;
    }

    .docs-accordion-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 16px;
        cursor: pointer;
        transition: background 0.2s ease;
    }

    .docs-accordion-header:hover {
        background: rgba(255, 255, 255, 0.05);
    }

    .docs-accordion-item.active .docs-accordion-arrow {
        transform: rotate(180deg);
    }

    .docs-accordion-arrow {
        margin-left: auto;
        font-size: 10px;
        color: var(--text-secondary, #94a3b8);
        transition: transform 0.2s ease;
    }

    .docs-accordion-content {
        display: none;
        padding: 0 16px 16px;
        border-top: 1px solid var(--border-color, #334155);
    }

    .docs-accordion-item.active .docs-accordion-content {
        display: block;
    }

    .docs-item-name {
        font-weight: 600;
        font-family: monospace;
        font-size: 15px;
        color: var(--text-primary, #e2e8f0);
    }

    .docs-item-category {
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
        padding: 2px 8px;
        background: var(--card-bg, #1e293b);
        border-radius: 10px;
    }

    .docs-item-badge {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 10px;
    }

    .docs-description {
        margin: 12px 0;
        color: var(--text-secondary, #94a3b8);
        line-height: 1.6;
    }

    .docs-section {
        margin-top: 16px;
    }

    .docs-section h4 {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary, #e2e8f0);
        margin-bottom: 8px;
    }

    .docs-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }

    .docs-table th,
    .docs-table td {
        padding: 8px 12px;
        text-align: left;
        border-bottom: 1px solid var(--border-color, #334155);
    }

    .docs-table th {
        font-weight: 600;
        color: var(--text-secondary, #94a3b8);
        background: var(--card-bg, #1e293b);
    }

    .docs-table code {
        font-family: monospace;
        font-size: 12px;
        padding: 2px 6px;
        background: var(--card-bg, #1e293b);
        border-radius: 4px;
        color: var(--primary-color, #007bff);
    }

    .docs-code {
        background: var(--card-bg, #1e293b);
        padding: 12px;
        border-radius: 6px;
        overflow-x: auto;
        margin: 8px 0;
    }

    .docs-code code {
        font-family: monospace;
        font-size: 12px;
        color: var(--text-primary, #e2e8f0);
    }

    .docs-example-desc {
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
        margin-top: 8px;
    }

    /* 网格布局 */
    .docs-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 16px;
    }

    .docs-card {
        background: var(--header-bg, #334155);
        border-radius: 8px;
        overflow: hidden;
    }

    .docs-card-header {
        padding: 12px 16px;
        background: rgba(0, 0, 0, 0.1);
    }

    .docs-card-title {
        font-weight: 600;
        font-family: monospace;
        font-size: 14px;
        color: var(--primary-color, #007bff);
    }

    .docs-card-body {
        padding: 16px;
    }

    .docs-card-body p {
        color: var(--text-secondary, #94a3b8);
        font-size: 13px;
        margin-bottom: 12px;
        line-height: 1.5;
    }

    .docs-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }

    .docs-tag {
        font-size: 11px;
        padding: 3px 8px;
        background: var(--card-bg, #1e293b);
        border-radius: 10px;
        color: var(--text-secondary, #94a3b8);
    }

    /* 命令列表样式 */
    .docs-commands-list {
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .docs-command-item {
        background: var(--header-bg, #334155);
        border-radius: 8px;
        overflow: hidden;
    }

    .docs-command-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 16px;
        background: rgba(0, 0, 0, 0.1);
        flex-wrap: wrap;
    }

    .docs-command-name {
        font-weight: 600;
        font-family: monospace;
        font-size: 14px;
        color: var(--primary-color, #007bff);
    }

    .docs-command-usage {
        font-size: 13px;
        color: var(--text-secondary, #94a3b8);
        font-family: monospace;
    }

    .docs-command-body {
        padding: 16px;
    }

    .docs-command-body p {
        color: var(--text-secondary, #94a3b8);
        line-height: 1.5;
    }

    .docs-command-options {
        margin-top: 16px;
    }

    .docs-command-options h4 {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary, #e2e8f0);
        margin-bottom: 8px;
    }

    /* 最佳实践样式 */
    .docs-best-practices {
        display: flex;
        flex-direction: column;
        gap: 24px;
    }

    .docs-best-practices h3 {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary, #e2e8f0);
        margin-bottom: 16px;
    }

    .docs-practice-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 16px;
    }

    .docs-practice-card {
        background: var(--header-bg, #334155);
        padding: 16px;
        border-radius: 8px;
    }

    .docs-practice-card h4 {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-primary, #e2e8f0);
        margin-bottom: 12px;
    }

    .docs-tools-list {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 8px;
    }

    .docs-tool-tag {
        font-size: 12px;
        font-family: monospace;
        padding: 3px 8px;
        background: var(--card-bg, #1e293b);
        border-radius: 4px;
        color: var(--primary-color, #007bff);
    }

    .docs-practice-desc {
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
        margin: 0;
    }

    .docs-modes-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 12px;
    }

    .docs-mode-card {
        background: var(--header-bg, #334155);
        padding: 14px;
        border-radius: 8px;
        border-left: 3px solid var(--primary-color, #007bff);
    }

    .docs-mode-name {
        font-weight: 600;
        font-family: monospace;
        font-size: 14px;
        color: var(--text-primary, #e2e8f0);
        margin-bottom: 4px;
    }

    .docs-mode-scenario {
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
    }

    .docs-error-patterns {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .docs-error-pattern {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: var(--header-bg, #334155);
        border-radius: 8px;
    }

    .docs-error-pattern code {
        font-family: monospace;
        font-size: 13px;
        font-weight: 600;
        color: var(--primary-color, #007bff);
        min-width: 100px;
    }

    .docs-error-pattern span {
        font-size: 13px;
        color: var(--text-secondary, #94a3b8);
    }

    /* 响应式布局 */
    @media (max-width: 768px) {
        .tools-usage-grid {
            grid-template-columns: 1fr;
        }

        .task-stats {
            grid-template-columns: repeat(2, 1fr);
        }

        .permission-modes-list {
            grid-template-columns: 1fr;
        }

        .tools-category-list {
            grid-template-columns: 1fr;
        }

        .tool-item {
            flex-wrap: wrap;
        }

        .tool-item-desc {
            order: 3;
            width: 100%;
            margin-top: 8px;
        }

        /* 文档展示响应式 */
        .docs-tabs {
            flex-wrap: wrap;
        }

        .docs-tab {
            flex: 1;
            min-width: 80px;
            text-align: center;
        }

        .docs-practice-grid,
        .docs-modes-grid {
            grid-template-columns: 1fr;
        }

        .docs-accordion-header {
            flex-wrap: wrap;
        }
    }
`;
document.head.appendChild(style);

// 导出模块
window.ClaudeStatus = ClaudeStatus;
