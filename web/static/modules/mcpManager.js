/**
 * MCP 服务器管理模块
 * 负责加载和展示 MCP 服务器信息
 */

const MCPManager = {
    /** 服务器列表数据 */
    servers: [],
    /** 是否已加载数据 */
    isLoaded: false,

    /**
     * 初始化 MCP 管理模块
     */
    init() {
        this.bindEvents();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 添加服务器按钮
        const addBtn = document.getElementById("add-mcp-server-btn");
        if (addBtn) {
            addBtn.addEventListener("click", () => this.showCreateDialog());
        }

        // 刷新按钮
        const refreshBtn = document.getElementById("refresh-mcp-btn");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => this.loadServers());
        }

        // 关闭对话框
        const closeDialogBtn = document.getElementById("close-mcp-dialog");
        if (closeDialogBtn) {
            closeDialogBtn.addEventListener("click", () => this.hideDialog());
        }

        // 对话框背景点击关闭
        const dialog = document.getElementById("mcp-dialog");
        if (dialog) {
            dialog.addEventListener("click", (e) => {
                if (e.target === dialog) {
                    this.hideDialog();
                }
            });
        }

        // 保存按钮
        const saveBtn = document.getElementById("save-mcp-server-btn");
        if (saveBtn) {
            saveBtn.addEventListener("click", () => this.saveServer());
        }

        // 连接类型切换
        const connectionType = document.getElementById("mcp-connection-type");
        if (connectionType) {
            connectionType.addEventListener("change", (e) => {
                this.toggleConnectionConfig(e.target.value);
            });
        }
    },

    /**
     * 当视图显示时加载数据
     */
    onShow() {
        if (!this.isLoaded) {
            this.loadServers();
            this.isLoaded = true;
        }
    },

    /**
     * 加载服务器列表
     */
    async loadServers() {
        const serverList = document.getElementById("mcp-server-list");
        if (!serverList) return;

        serverList.innerHTML = '<div class="loading-placeholder">加载中...</div>';

        try {
            const response = await fetch("/api/mcp/servers");
            const data = await response.json();

            this.servers = data.servers || [];
            this.renderServers();
        } catch (error) {
            console.error("加载 MCP 服务器列表失败:", error);
            serverList.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 渲染服务器列表
     */
    renderServers() {
        const serverList = document.getElementById("mcp-server-list");
        if (!serverList) return;

        if (this.servers.length === 0) {
            serverList.innerHTML = '<div class="empty-placeholder">暂无 MCP 服务器</div>';
            return;
        }

        let html = '<table class="mcp-server-table">';
        html += "<thead><tr>";
        html += "<th>名称</th>";
        html += "<th>类型</th>";
        html += "<th>状态</th>";
        html += "<th>操作</th>";
        html += "</tr></thead>";
        html += "<tbody>";

        for (const server of this.servers) {
            const statusClass = server.enabled ? "status-online" : "status-offline";
            const statusText = server.enabled ? "已启用" : "已禁用";

            html += "<tr>";
            html += `<td class="server-name">${this.escapeHtml(server.name)}</td>`;
            html += `<td class="server-type">${server.connection_type}</td>`;
            html += `<td><span class="server-status ${statusClass}">${statusText}</span></td>`;
            html += `<td class="server-actions">`;
            html += `<button class="btn-icon" title="编辑" onclick="MCPManager.showEditDialog('${server.id}')">✏️</button>`;
            html += `<button class="btn-icon" title="删除" onclick="MCPManager.deleteServer('${server.id}')">🗑️</button>`;
            html += `</td>`;
            html += "</tr>";
        }

        html += "</tbody></table>";
        serverList.innerHTML = html;
    },

    /**
     * 显示创建对话框
     */
    showCreateDialog() {
        this.currentServerId = null;
        document.getElementById("mcp-dialog-title").textContent = "添加 MCP 服务器";
        document.getElementById("mcp-server-name").value = "";
        document.getElementById("mcp-connection-type").value = "stdio";
        document.getElementById("mcp-command").value = "";
        document.getElementById("mcp-args").value = "";
        document.getElementById("mcp-url").value = "";
        this.toggleConnectionConfig("stdio");
        document.getElementById("mcp-enabled").checked = true;
        document.getElementById("mcp-dialog").style.display = "flex";
    },

    /**
     * 显示编辑对话框
     */
    async showEditDialog(serverId) {
        const server = this.servers.find(s => s.id === serverId);
        if (!server) {
            this.showToast("服务器不存在");
            return;
        }

        this.currentServerId = serverId;
        document.getElementById("mcp-dialog-title").textContent = "编辑 MCP 服务器";
        document.getElementById("mcp-server-name").value = server.name;
        document.getElementById("mcp-connection-type").value = server.connection_type;
        document.getElementById("mcp-command").value = server.config.command || "";
        document.getElementById("mcp-args").value = server.config.args ? server.config.args.join(" ") : "";
        document.getElementById("mcp-url").value = server.config.url || "";
        this.toggleConnectionConfig(server.connection_type);
        document.getElementById("mcp-enabled").checked = server.enabled;
        document.getElementById("mcp-dialog").style.display = "flex";
    },

    /**
     * 切换连接类型配置显示
     */
    toggleConnectionConfig(type) {
        const stdioConfig = document.getElementById("stdio-config");
        const httpConfig = document.getElementById("http-config");

        if (type === "stdio") {
            stdioConfig.style.display = "block";
            httpConfig.style.display = "none";
        } else {
            stdioConfig.style.display = "none";
            httpConfig.style.display = "block";
        }
    },

    /**
     * 隐藏对话框
     */
    hideDialog() {
        document.getElementById("mcp-dialog").style.display = "none";
    },

    /**
     * 保存服务器
     */
    async saveServer() {
        const name = document.getElementById("mcp-server-name").value.trim();
        const connectionType = document.getElementById("mcp-connection-type").value;
        const enabled = document.getElementById("mcp-enabled").checked;

        if (!name) {
            this.showToast("请输入服务器名称");
            return;
        }

        let config = {};

        if (connectionType === "stdio") {
            const command = document.getElementById("mcp-command").value.trim();
            const argsStr = document.getElementById("mcp-args").value.trim();
            const args = argsStr ? argsStr.split(/\s+/) : [];

            if (!command) {
                this.showToast("请输入命令");
                return;
            }

            config = { command, args };
        } else {
            const url = document.getElementById("mcp-url").value.trim();

            if (!url) {
                this.showToast("请输入 URL");
                return;
            }

            config = { url };
        }

        const payload = {
            name,
            connection_type: connectionType,
            config,
            enabled,
        };

        try {
            let response;
            if (this.currentServerId) {
                // 更新
                response = await fetch(`/api/mcp/servers/${this.currentServerId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
            } else {
                // 创建
                response = await fetch("/api/mcp/servers", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
            }

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "保存失败");
            }

            this.hideDialog();
            this.loadServers();
            this.showToast(this.currentServerId ? "服务器已更新" : "服务器已创建");
        } catch (error) {
            console.error("保存 MCP 服务器失败:", error);
            this.showToast(error.message || "保存失败");
        }
    },

    /**
     * 删除服务器
     */
    async deleteServer(serverId) {
        if (!confirm("确定要删除这个 MCP 服务器吗？")) {
            return;
        }

        try {
            const response = await fetch(`/api/mcp/servers/${serverId}`, {
                method: "DELETE",
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "删除失败");
            }

            this.loadServers();
            this.showToast("服务器已删除");
        } catch (error) {
            console.error("删除 MCP 服务器失败:", error);
            this.showToast(error.message || "删除失败");
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
const mcpStyle = document.createElement("style");
mcpStyle.textContent = `
    .mcp-server-table {
        width: 100%;
        border-collapse: collapse;
    }

    .mcp-server-table th,
    .mcp-server-table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid var(--border-color, #eee);
    }

    .mcp-server-table th {
        font-weight: 600;
        background: var(--header-bg, #f5f5f5);
        font-size: 12px;
        color: var(--text-secondary, #666);
    }

    .server-name {
        font-weight: 500;
    }

    .server-type {
        font-family: monospace;
        color: var(--text-secondary, #666);
    }

    .server-status {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
    }

    .status-online {
        background: #d4edda;
        color: #155724;
    }

    .status-offline {
        background: #f8d7da;
        color: #721c24;
    }

    .server-actions {
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

    /* 对话框样式 */
    .dialog-overlay {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }

    .dialog-content {
        background: var(--card-bg, #fff);
        border-radius: 8px;
        padding: 24px;
        width: 90%;
        max-width: 500px;
        max-height: 90vh;
        overflow-y: auto;
    }

    .dialog-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }

    .dialog-title {
        font-size: 18px;
        font-weight: 600;
        margin: 0;
    }

    .dialog-close {
        background: none;
        border: none;
        font-size: 20px;
        cursor: pointer;
        color: var(--text-secondary, #666);
    }

    .form-group {
        margin-bottom: 16px;
    }

    .form-label {
        display: block;
        font-weight: 500;
        margin-bottom: 6px;
        color: var(--text-primary, #333);
    }

    .form-input {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid var(--border-color, #ddd);
        border-radius: 6px;
        font-size: 14px;
        box-sizing: border-box;
    }

    .form-input:focus {
        outline: none;
        border-color: var(--primary-color, #007bff);
    }

    .form-checkbox {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .form-checkbox input {
        width: 18px;
        height: 18px;
    }

    .form-actions {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        margin-top: 24px;
    }

    .btn-primary {
        padding: 10px 20px;
        background: var(--primary-color, #007bff);
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
    }

    .btn-primary:hover {
        opacity: 0.9;
    }

    .btn-secondary {
        padding: 10px 20px;
        background: var(--border-color, #eee);
        color: var(--text-primary, #333);
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
    }

    .btn-secondary:hover {
        background: var(--border-color, #ddd);
    }

    .config-section {
        padding: 16px;
        background: var(--header-bg, #f5f5f5);
        border-radius: 6px;
        margin-top: 12px;
    }
`;
document.head.appendChild(mcpStyle);

// 导出模块
window.MCPManager = MCPManager;
