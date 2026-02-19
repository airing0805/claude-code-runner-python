/**
 * Agent 监控模块
 * 负责加载和展示子代理信息
 */

const AgentMonitor = {
    /** 代理列表数据 */
    agents: [],
    /** 是否已加载数据 */
    isLoaded: false,
    /** 当前选中的代理 */
    selectedAgentId: null,
    /** 定时刷新间隔 */
    refreshInterval: null,

    /**
     * 初始化 Agent 监控模块
     */
    init() {
        this.bindEvents();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 刷新按钮
        const refreshBtn = document.getElementById("refresh-agents-btn");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => this.loadAgents());
        }

        // 状态过滤
        const statusFilter = document.getElementById("agent-status-filter");
        if (statusFilter) {
            statusFilter.addEventListener("change", (e) => {
                this.loadAgents({ status: e.target.value });
            });
        }

        // 创建测试代理按钮
        const createTestBtn = document.getElementById("create-test-agent-btn");
        if (createTestBtn) {
            createTestBtn.addEventListener("click", () => this.createTestAgent());
        }
    },

    /**
     * 当视图显示时加载数据
     */
    onShow() {
        if (!this.isLoaded) {
            this.loadAgents();
            this.isLoaded = true;
        }
        // 启动定时刷新
        this.startAutoRefresh();
    },

    /**
     * 视图隐藏时停止刷新
     */
    onHide() {
        this.stopAutoRefresh();
    },

    /**
     * 启动自动刷新
     */
    startAutoRefresh() {
        if (this.refreshInterval) return;
        this.refreshInterval = setInterval(() => {
            this.loadAgents();
        }, 5000); // 每 5 秒刷新一次
    },

    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    },

    /**
     * 加载代理列表
     */
    async loadAgents(filters = {}) {
        const agentList = document.getElementById("agent-list");
        if (!agentList) return;

        agentList.innerHTML = '<div class="loading-placeholder">加载中...</div>';

        try {
            // 构建查询参数
            const params = new URLSearchParams();
            if (filters.status && filters.status !== "all") {
                params.append("status", filters.status);
            }
            const queryString = params.toString();
            const url = `/api/agents${queryString ? "?" + queryString : ""}`;

            const response = await fetch(url);
            const data = await response.json();

            this.agents = data.agents || [];
            this.renderAgents();

            // 更新运行计数
            this.updateRunningCount(data.running_count);
        } catch (error) {
            console.error("加载代理列表失败:", error);
            agentList.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 渲染代理列表
     */
    renderAgents() {
        const agentList = document.getElementById("agent-list");
        if (!agentList) return;

        if (this.agents.length === 0) {
            agentList.innerHTML = '<div class="empty-placeholder">暂无代理</div>';
            return;
        }

        let html = '<table class="agent-table">';
        html += "<thead><tr>";
        html += "<th>任务描述</th>";
        html += "<th>状态</th>";
        html += "<th>进度</th>";
        html += "<th>开始时间</th>";
        html += "<th>操作</th>";
        html += "</tr></thead>";
        html += "<tbody>";

        for (const agent of this.agents) {
            const statusClass = this.getStatusClass(agent.status);
            const statusText = this.getStatusText(agent.status);

            html += "<tr>";
            html += `<td class="agent-prompt">${this.escapeHtml(agent.prompt)}</td>`;
            html += `<td><span class="agent-status ${statusClass}">${statusText}</span></td>`;
            html += `<td class="agent-progress">${agent.progress}%</td>`;
            html += `<td class="agent-time">${this.formatTime(agent.started_at)}</td>`;
            html += `<td class="agent-actions">`;
            html += `<button class="btn-icon" title="查看详情" onclick="AgentMonitor.showDetail('${agent.id}')">👁️</button>`;
            if (agent.status === "running") {
                html += `<button class="btn-icon btn-danger" title="终止" onclick="AgentMonitor.terminateAgent('${agent.id}')">⏹️</button>`;
            }
            html += `</td>`;
            html += "</tr>";
        }

        html += "</tbody></table>";
        agentList.innerHTML = html;
    },

    /**
     * 获取状态样式类
     */
    getStatusClass(status) {
        const statusMap = {
            running: "status-running",
            completed: "status-completed",
            terminated: "status-terminated",
            failed: "status-failed",
        };
        return statusMap[status] || "status-unknown";
    },

    /**
     * 获取状态文本
     */
    getStatusText(status) {
        const textMap = {
            running: "运行中",
            completed: "已完成",
            terminated: "已终止",
            failed: "失败",
        };
        return textMap[status] || status;
    },

    /**
     * 格式化时间
     */
    formatTime(isoString) {
        if (!isoString) return "-";
        const date = new Date(isoString);
        return date.toLocaleString("zh-CN", {
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    },

    /**
     * 更新运行计数
     */
    updateRunningCount(count) {
        const countEl = document.getElementById("running-agent-count");
        if (countEl) {
            countEl.textContent = count || 0;
        }
    },

    /**
     * 显示代理详情
     */
    async showDetail(agentId) {
        const agent = this.agents.find(a => a.id === agentId);
        if (!agent) {
            this.showToast("代理不存在");
            return;
        }

        this.selectedAgentId = agentId;

        // 显示详情对话框
        const dialog = document.getElementById("agent-detail-dialog");
        if (!dialog) return;

        // 填充基本信息
        document.getElementById("detail-agent-prompt").textContent = agent.prompt;
        document.getElementById("detail-agent-status").textContent = this.getStatusText(agent.status);
        document.getElementById("detail-agent-progress").textContent = agent.progress + "%";
        document.getElementById("detail-agent-started").textContent = this.formatTime(agent.started_at);
        document.getElementById("detail-agent-ended").textContent = agent.ended_at ? this.formatTime(agent.ended_at) : "-";

        // 添加工具使用列表
        const toolsList = document.getElementById("detail-agent-tools");
        if (agent.tools_used && agent.tools_used.length > 0) {
            toolsList.innerHTML = agent.tools_used.map(t => `<span class="tool-tag">${t}</span>`).join("");
        } else {
            toolsList.innerHTML = '<span class="empty-text">无</span>';
        }

        // 添加文件变更列表
        const filesList = document.getElementById("detail-agent-files");
        if (agent.files_changed && agent.files_changed.length > 0) {
            filesList.innerHTML = agent.files_changed.map(f => `<div class="file-item">${this.escapeHtml(f)}</div>`).join("");
        } else {
            filesList.innerHTML = '<span class="empty-text">无</span>';
        }

        // 加载日志
        await this.loadAgentLogs(agentId);

        // 显示对话框
        dialog.style.display = "flex";

        // 绑定关闭事件
        const closeBtn = document.getElementById("close-agent-detail-dialog");
        if (closeBtn) {
            closeBtn.onclick = () => {
                dialog.style.display = "none";
            };
        }

        // 对话框背景点击关闭
        dialog.onclick = (e) => {
            if (e.target === dialog) {
                dialog.style.display = "none";
            }
        };
    },

    /**
     * 加载代理日志
     */
    async loadAgentLogs(agentId) {
        const logsContainer = document.getElementById("detail-agent-logs");
        if (!logsContainer) return;

        logsContainer.innerHTML = '<div class="loading-placeholder">加载日志...</div>';

        try {
            const response = await fetch(`/api/agents/${agentId}/logs`);
            const text = await response.text();

            if (text) {
                logsContainer.innerHTML = `<pre class="logs-content">${this.escapeHtml(text)}</pre>`;
            } else {
                logsContainer.innerHTML = '<span class="empty-text">暂无日志</span>';
            }
        } catch (error) {
            console.error("加载日志失败:", error);
            logsContainer.innerHTML = '<span class="empty-text">加载失败</span>';
        }
    },

    /**
     * 终止代理
     */
    async terminateAgent(agentId) {
        if (!confirm("确定要终止这个代理吗？")) {
            return;
        }

        try {
            const response = await fetch(`/api/agents/${agentId}/terminate`, {
                method: "POST",
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "终止失败");
            }

            this.showToast("代理已终止");
            this.loadAgents();
        } catch (error) {
            console.error("终止代理失败:", error);
            this.showToast(error.message || "终止失败");
        }
    },

    /**
     * 创建测试代理
     */
    async createTestAgent() {
        try {
            const response = await fetch("/api/agents/debug/create?parent_task_id=test&prompt=测试代理任务", {
                method: "POST",
            });

            if (!response.ok) {
                throw new Error("创建失败");
            }

            this.showToast("测试代理已创建");
            this.loadAgents();
        } catch (error) {
            console.error("创建测试代理失败:", error);
            this.showToast(error.message || "创建失败");
        }
    },

    /**
     * HTML 转义
     */
    escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 显示提示消息
     */
    showToast(message) {
        if (typeof window.showToast === "function") {
            window.showToast(message);
            return;
        }

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
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 2000);
    },
};

// 添加样式
const agentMonitorStyle = document.createElement("style");
agentMonitorStyle.textContent = `
    .agent-table {
        width: 100%;
        border-collapse: collapse;
    }

    .agent-table th,
    .agent-table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid var(--border-color, #eee);
    }

    .agent-table th {
        font-weight: 600;
        background: var(--header-bg, #f5f5f5);
        font-size: 12px;
        color: var(--text-secondary, #666);
    }

    .agent-prompt {
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .agent-status {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
    }

    .status-running {
        background: #d4edda;
        color: #155724;
    }

    .status-completed {
        background: #cce5ff;
        color: #004085;
    }

    .status-terminated {
        background: #fff3cd;
        color: #856404;
    }

    .status-failed {
        background: #f8d7da;
        color: #721c24;
    }

    .status-unknown {
        background: #e2e3e5;
        color: #383d41;
    }

    .agent-progress {
        font-family: monospace;
    }

    .agent-time {
        font-size: 12px;
        color: var(--text-secondary, #666);
    }

    .agent-actions {
        display: flex;
        gap: 8px;
    }

    .btn-icon {
        background: none;
        border: none;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 14px;
    }

    .btn-icon:hover {
        background: var(--border-color, #eee);
    }

    .btn-danger {
        color: #dc3545;
    }

    /* 代理详情对话框 */
    .agent-detail-content {
        background: var(--card-bg, #fff);
        border-radius: 8px;
        padding: 24px;
        width: 90%;
        max-width: 700px;
        max-height: 90vh;
        overflow-y: auto;
    }

    .detail-section {
        margin-bottom: 20px;
    }

    .detail-section-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-secondary, #666);
        margin-bottom: 8px;
    }

    .detail-section-content {
        font-size: 14px;
    }

    .tool-tag {
        display: inline-block;
        padding: 4px 8px;
        background: var(--header-bg, #f5f5f5);
        border-radius: 4px;
        font-size: 12px;
        margin-right: 6px;
        margin-bottom: 6px;
    }

    .file-item {
        padding: 4px 8px;
        background: var(--header-bg, #f5f5f5);
        border-radius: 4px;
        font-size: 12px;
        margin-right: 6px;
        margin-bottom: 6px;
        font-family: monospace;
    }

    .logs-content {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 12px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 12px;
        max-height: 200px;
        overflow-y: auto;
        white-space: pre-wrap;
        word-break: break-all;
    }

    .empty-text {
        color: var(--text-secondary, #999);
        font-style: italic;
    }

    /* 过滤栏 */
    .agent-filter-bar {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 16px;
    }

    .agent-filter-bar label {
        font-size: 14px;
        color: var(--text-secondary, #666);
    }

    .agent-filter-bar select {
        padding: 6px 12px;
        border: 1px solid var(--border-color, #ddd);
        border-radius: 4px;
        font-size: 14px;
    }

    /* 统计卡片 */
    .agent-stats {
        display: flex;
        gap: 16px;
        margin-bottom: 16px;
    }

    .agent-stat-card {
        background: var(--header-bg, #f5f5f5);
        padding: 16px;
        border-radius: 8px;
        text-align: center;
        min-width: 100px;
    }

    .agent-stat-value {
        font-size: 24px;
        font-weight: 600;
        color: var(--primary-color, #007bff);
    }

    .agent-stat-label {
        font-size: 12px;
        color: var(--text-secondary, #666);
        margin-top: 4px;
    }
`;
document.head.appendChild(agentMonitorStyle);

// 导出模块
window.AgentMonitor = AgentMonitor;
