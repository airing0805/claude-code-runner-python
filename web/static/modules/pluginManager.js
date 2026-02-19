/**
 * 插件管理模块
 * 负责加载和展示 Claude Code 插件信息
 */

const PluginManager = {
    /** 插件列表数据 */
    plugins: [],
    /** 是否已加载数据 */
    isLoaded: false,

    /**
     * 初始化插件管理模块
     */
    init() {
        this.bindEvents();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 刷新按钮
        const refreshBtn = document.getElementById("refresh-plugins-btn");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => this.loadPlugins());
        }
    },

    /**
     * 当视图显示时加载数据
     */
    onShow() {
        if (!this.isLoaded) {
            this.loadPlugins();
            this.isLoaded = true;
        }
    },

    /**
     * 获取插件列表容器
     * 优先查找独立视图容器，其次查找 claude-status 中的容器
     */
    getPluginListContainer() {
        // 优先查找独立视图容器
        let container = document.getElementById("plugin-list-view");
        if (container && container.closest('.view-panel')?.classList.contains('active')) {
            return container;
        }
        // 其次查找 claude-status 中的容器
        container = document.getElementById("plugin-list");
        if (container && container.closest('.view-panel')?.classList.contains('active')) {
            return container;
        }
        // 任意一个容器存在即可
        return document.getElementById("plugin-list-view") || document.getElementById("plugin-list");
    },

    /**
     * 加载插件列表
     */
    async loadPlugins() {
        const pluginList = this.getPluginListContainer();
        if (!pluginList) return;

        pluginList.innerHTML = '<div class="loading-placeholder">加载中...</div>';

        try {
            const response = await fetch("/api/claude/plugins");
            const data = await response.json();

            this.plugins = data.plugins || [];
            this.renderPlugins();
        } catch (error) {
            console.error("加载插件列表失败:", error);
            pluginList.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 渲染插件列表
     */
    renderPlugins() {
        const pluginList = this.getPluginListContainer();
        if (!pluginList) return;

        if (this.plugins.length === 0) {
            pluginList.innerHTML = '<div class="empty-placeholder">暂无插件</div>';
            return;
        }

        let html = '<table class="plugin-table">';
        html += "<thead><tr><th>名称</th><th>描述</th><th>版本</th><th>作者</th><th>状态</th><th>操作</th></tr></thead>";
        html += "<tbody>";

        for (const plugin of this.plugins) {
            const statusBadge = plugin.is_enabled
                ? '<span class="status-badge status-enabled">已启用</span>'
                : '<span class="status-badge status-disabled">已禁用</span>';

            const actionButton = plugin.is_enabled
                ? `<button class="btn btn-sm btn-outline" onclick="PluginManager.disablePlugin('${plugin.id}')">禁用</button>`
                : `<button class="btn btn-sm btn-primary" onclick="PluginManager.enablePlugin('${plugin.id}')">启用</button>`;

            const builtinBadge = plugin.is_builtin
                ? '<span class="builtin-badge">内置</span>'
                : '';

            html += `<tr>`;
            html += `<td class="plugin-name">${this.escapeHtml(plugin.name)} ${builtinBadge}</td>`;
            html += `<td class="plugin-desc">${this.escapeHtml(plugin.description)}</td>`;
            html += `<td class="plugin-version">${this.escapeHtml(plugin.version)}</td>`;
            html += `<td class="plugin-author">${this.escapeHtml(plugin.author)}</td>`;
            html += `<td class="plugin-status">${statusBadge}</td>`;
            html += `<td class="plugin-actions">${actionButton}</td>`;
            html += `</tr>`;
        }

        html += "</tbody></table>";
        pluginList.innerHTML = html;
    },

    /**
     * 启用插件
     */
    async enablePlugin(pluginId) {
        try {
            const response = await fetch(`/api/claude/plugins/${pluginId}/enable`, {
                method: "POST",
            });
            const data = await response.json();

            if (data.success) {
                this.showToast(`插件已启用`);
                this.loadPlugins(); // 刷新列表
            } else {
                this.showToast(`启用失败: ${data.message}`, true);
            }
        } catch (error) {
            console.error("启用插件失败:", error);
            this.showToast("启用插件失败", true);
        }
    },

    /**
     * 禁用插件
     */
    async disablePlugin(pluginId) {
        try {
            const response = await fetch(`/api/claude/plugins/${pluginId}/disable`, {
                method: "POST",
            });
            const data = await response.json();

            if (data.success) {
                this.showToast(`插件已禁用`);
                this.loadPlugins(); // 刷新列表
            } else {
                this.showToast(`禁用失败: ${data.message}`, true);
            }
        } catch (error) {
            console.error("禁用插件失败:", error);
            this.showToast("禁用插件失败", true);
        }
    },

    /**
     * HTML 转义
     */
    escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 显示提示消息
     */
    showToast(message, isError = false) {
        if (typeof window.showToast === "function") {
            window.showToast(message);
            return;
        }

        const toast = document.createElement("div");
        toast.className = "toast-message";
        if (isError) {
            toast.style.background = "rgba(220, 53, 69, 0.9)";
        }
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

// 添加样式
const pluginStyle = document.createElement("style");
pluginStyle.textContent = `
    .plugin-table {
        width: 100%;
        border-collapse: collapse;
    }

    .plugin-table th,
    .plugin-table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid var(--border-color, #eee);
    }

    .plugin-table th {
        font-weight: 600;
        background: var(--header-bg, #334155);
        font-size: 12px;
        color: var(--text-secondary, #666);
    }

    .plugin-name {
        font-weight: 500;
    }

    .plugin-desc {
        color: var(--text-secondary, #666);
        font-size: 13px;
        max-width: 250px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .plugin-version {
        font-family: monospace;
        color: var(--text-secondary, #666);
    }

    .plugin-author {
        color: var(--text-secondary, #666);
    }

    .plugin-status {
        text-align: center;
    }

    .plugin-actions {
        text-align: center;
    }

    .status-badge {
        display: inline-block;
        font-size: 12px;
        padding: 4px 8px;
        border-radius: 12px;
    }

    .status-enabled {
        background: #d4edda;
        color: #155724;
    }

    .status-disabled {
        background: #f8d7da;
        color: #721c24;
    }

    .builtin-badge {
        display: inline-block;
        font-size: 10px;
        padding: 2px 6px;
        background: #e2e3e5;
        color: #383d41;
        border-radius: 8px;
        margin-left: 8px;
    }

    .btn-sm {
        padding: 4px 12px;
        font-size: 12px;
    }

    .btn-outline {
        background: transparent;
        border: 1px solid var(--border-color, #ccc);
        color: var(--text-primary, #333);
        border-radius: 4px;
        cursor: pointer;
    }

    .btn-outline:hover {
        background: var(--header-bg, #334155);
    }

    .btn-primary {
        background: var(--primary-color, #007bff);
        border: 1px solid var(--primary-color, #007bff);
        color: white;
        border-radius: 4px;
        cursor: pointer;
    }

    .btn-primary:hover {
        background: #0056b3;
        border-color: #0056b3;
    }
`;
document.head.appendChild(pluginStyle);

// 导出模块
window.PluginManager = PluginManager;
