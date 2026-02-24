/**
 * 钩子管理模块
 * 负责加载和展示钩子配置信息
 */

const HooksManager = {
    /** 钩子列表数据 */
    hooks: [],
    /** 钩子类型数据 */
    hookTypes: [],
    /** 是否已加载数据 */
    isLoaded: false,
    /** 当前编辑的钩子 ID */
    currentHookId: null,

    /**
     * 初始化钩子管理模块
     */
    init() {
        this.bindEvents();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 添加钩子按钮
        const addBtn = document.getElementById("add-hook-btn");
        if (addBtn) {
            addBtn.addEventListener("click", () => this.showCreateDialog());
        }

        // 刷新按钮
        const refreshBtn = document.getElementById("refresh-hooks-btn");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => this.loadHooks());
        }

        // 关闭对话框
        const closeDialogBtn = document.getElementById("close-hook-dialog");
        if (closeDialogBtn) {
            closeDialogBtn.addEventListener("click", () => this.hideDialog());
        }

        // 对话框背景点击关闭
        const dialog = document.getElementById("hook-dialog");
        if (dialog) {
            dialog.addEventListener("click", (e) => {
                if (e.target === dialog) {
                    this.hideDialog();
                }
            });
        }

        // 取消按钮
        const cancelBtn = document.getElementById("cancel-hook-dialog-btn");
        if (cancelBtn) {
            cancelBtn.addEventListener("click", () => this.hideDialog());
        }

        // 保存按钮
        const saveBtn = document.getElementById("save-hook-btn");
        if (saveBtn) {
            saveBtn.addEventListener("click", () => this.saveHook());
        }
    },

    /**
     * 当视图显示时加载数据
     */
    onShow() {
        if (!this.isLoaded) {
            this.loadHooks();
            this.loadHookTypes();
            this.isLoaded = true;
        }
    },

    /**
     * 加载钩子列表
     */
    async loadHooks() {
        const hookList = document.getElementById("hook-list");
        if (!hookList) return;

        hookList.innerHTML = '<div class="loading-placeholder">加载中...</div>';

        try {
            const response = await fetch("/api/claude/hooks");
            const data = await response.json();

            this.hooks = data.hooks || [];
            this.renderHooks();
        } catch (error) {
            console.error("加载钩子列表失败:", error);
            hookList.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 加载钩子类型说明
     */
    async loadHookTypes() {
        const hookTypesInfo = document.getElementById("hook-types-info");
        if (!hookTypesInfo) return;

        try {
            const response = await fetch("/api/claude/hooks/types");
            const data = await response.json();

            this.hookTypes = data.hook_types || [];
            this.renderHookTypes();
        } catch (error) {
            console.error("加载钩子类型失败:", error);
        }
    },

    /**
     * 渲染钩子类型说明
     */
    renderHookTypes() {
        const hookTypesInfo = document.getElementById("hook-types-info");
        if (!hookTypesInfo) return;

        if (this.hookTypes.length === 0) {
            hookTypesInfo.innerHTML = "";
            return;
        }

        let html = '<div class="hook-types-list">';
        html += "<h4>钩子类型说明</h4>";
        html += "<ul>";

        for (const hookType of this.hookTypes) {
            html += `<li><strong>${hookType.name}</strong>: ${hookType.description} - ${hookType.example}</li>`;
        }

        html += "</ul>";
        html += "</div>";

        hookTypesInfo.innerHTML = html;
    },

    /**
     * 渲染钩子列表
     */
    renderHooks() {
        const hookList = document.getElementById("hook-list");
        if (!hookList) return;

        if (this.hooks.length === 0) {
            hookList.innerHTML = '<div class="empty-placeholder">暂无钩子配置</div>';
            return;
        }

        let html = '<table class="hook-table">';
        html += "<thead><tr>";
        html += "<th>名称</th>";
        html += "<th>类型</th>";
        html += "<th>触发工具</th>";
        html += "<th>操作</th>";
        html += "<th>状态</th>";
        html += "<th>操作</th>";
        html += "</tr></thead>";
        html += "<tbody>";

        for (const hook of this.hooks) {
            const statusClass = hook.enabled ? "status-enabled" : "status-disabled";
            const statusText = hook.enabled ? "启用" : "禁用";
            const toolsText = hook.config.tools && hook.config.tools.length > 0
                ? hook.config.tools.join(", ")
                : "所有工具";

            html += "<tr>";
            html += `<td class="hook-name">${this.escapeHtml(hook.name)}</td>`;
            html += `<td class="hook-type">${this.escapeHtml(hook.type)}</td>`;
            html += `<td class="hook-tools">${this.escapeHtml(toolsText)}</td>`;
            html += `<td class="hook-action">${hook.config.action === "allow" ? "允许" : "阻止"}</td>`;
            html += `<td><span class="hook-status ${statusClass}">${statusText}</span></td>`;
            html += `<td class="hook-actions">`;
            html += `<button class="btn-icon" title="编辑" onclick="HooksManager.showEditDialog('${hook.id}')">✏️</button>`;
            html += `<button class="btn-icon" title="删除" onclick="HooksManager.deleteHook('${hook.id}')">🗑️</button>`;
            html += `</td>`;
            html += "</tr>";
        }

        html += "</tbody></table>";
        hookList.innerHTML = html;
    },

    /**
     * 显示创建对话框
     */
    showCreateDialog() {
        this.currentHookId = null;
        document.getElementById("hook-dialog-title").textContent = "添加钩子";
        document.getElementById("hook-id").value = "";
        document.getElementById("hook-name").value = "";
        document.getElementById("hook-tools").value = "";
        document.getElementById("hook-action").value = "allow";
        document.getElementById("hook-notification").checked = false;
        document.getElementById("hook-enabled").checked = true;
        
        // 动态填充钩子类型下拉菜单
        this.populateHookTypesSelect();
        
        document.getElementById("hook-dialog").style.display = "flex";
    },

    /**
     * 显示编辑对话框
     */
    async showEditDialog(hookId) {
        const hook = this.hooks.find(h => h.id === hookId);
        if (!hook) {
            this.showToast("钩子不存在");
            return;
        }

        this.currentHookId = hookId;
        document.getElementById("hook-dialog-title").textContent = "编辑钩子";
        document.getElementById("hook-id").value = hook.id;
        document.getElementById("hook-name").value = hook.name;
        document.getElementById("hook-tools").value = hook.config.tools ? hook.config.tools.join(", ") : "";
        document.getElementById("hook-action").value = hook.config.action;
        document.getElementById("hook-notification").checked = hook.config.notification;
        document.getElementById("hook-enabled").checked = hook.enabled;
        
        // 动态填充钩子类型下拉菜单
        this.populateHookTypesSelect();
        // 设置当前选中的值
        document.getElementById("hook-type").value = hook.type;
        
        document.getElementById("hook-dialog").style.display = "flex";
    },

    /**
     * 动态填充钩子类型下拉菜单
     */
    populateHookTypesSelect() {
        const selectElement = document.getElementById("hook-type");
        if (!selectElement) return;

        // 清空现有选项
        selectElement.innerHTML = "";

        // 如果已经有钩子类型数据，直接使用
        if (this.hookTypes && this.hookTypes.length > 0) {
            this.hookTypes.forEach(hookType => {
                const option = document.createElement("option");
                option.value = hookType.name;
                option.textContent = `${hookType.name} - ${hookType.description}`;
                selectElement.appendChild(option);
            });
            // 设置默认选中第一个选项
            if (selectElement.options.length > 0) {
                selectElement.selectedIndex = 0;
            }
        } else {
            // 如果没有数据，从API加载
            this.loadHookTypesForSelect();
        }
    },

    /**
     * 从API加载钩子类型并填充下拉菜单
     */
    async loadHookTypesForSelect() {
        try {
            const response = await fetch("/api/claude/hooks/types");
            const data = await response.json();
            
            this.hookTypes = data.hook_types || [];
            
            // 填充下拉菜单
            const selectElement = document.getElementById("hook-type");
            if (!selectElement) return;
            
            selectElement.innerHTML = "";
            this.hookTypes.forEach(hookType => {
                const option = document.createElement("option");
                option.value = hookType.name;
                option.textContent = `${hookType.name} - ${hookType.description}`;
                selectElement.appendChild(option);
            });
        } catch (error) {
            console.error("加载钩子类型失败:", error);
            // 如果加载失败，使用默认选项
            const defaultOptions = [
                { value: "PreToolUse", text: "PreToolUse - 工具执行前触发" },
                { value: "PostToolUse", text: "PostToolUse - 工具执行后触发" },
                { value: "Stop", text: "Stop - 会话结束时触发" },
                { value: "SessionStart", text: "SessionStart - 会话开始时触发" },
                { value: "Notification", text: "Notification - 通知事件触发" }
            ];
            
            const selectElement = document.getElementById("hook-type");
            if (selectElement) {
                selectElement.innerHTML = "";
                defaultOptions.forEach(optionData => {
                    const option = document.createElement("option");
                    option.value = optionData.value;
                    option.textContent = optionData.text;
                    selectElement.appendChild(option);
                });
            }
        }
    },

    /**
     * 隐藏对话框
     */
    hideDialog() {
        document.getElementById("hook-dialog").style.display = "none";
    },

    /**
     * 保存钩子
     */
    async saveHook() {
        const name = document.getElementById("hook-name").value.trim();
        const type = document.getElementById("hook-type").value;
        const toolsStr = document.getElementById("hook-tools").value.trim();
        const action = document.getElementById("hook-action").value;
        const notification = document.getElementById("hook-notification").checked;
        const enabled = document.getElementById("hook-enabled").checked;

        if (!name) {
            this.showToast("请输入钩子名称");
            return;
        }

        // 解析工具列表
        const tools = toolsStr ? toolsStr.split(",").map(t => t.trim()).filter(t => t) : [];

        const hook = {
            id: this.currentHookId || "",
            name,
            type,
            enabled,
            config: {
                tools,
                action,
                notification,
            },
        };

        // 获取当前所有钩子，更新或添加
        let updatedHooks = [...this.hooks];
        if (this.currentHookId) {
            // 更新现有钩子
            const index = updatedHooks.findIndex(h => h.id === this.currentHookId);
            if (index !== -1) {
                updatedHooks[index] = hook;
            }
        } else {
            // 添加新钩子
            hook.id = "hook_" + Date.now().toString(36);
            updatedHooks.push(hook);
        }

        try {
            const response = await fetch("/api/claude/hooks", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(updatedHooks),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "保存失败");
            }

            this.hideDialog();
            this.loadHooks();
            this.showToast(this.currentHookId ? "钩子已更新" : "钩子已创建");
        } catch (error) {
            console.error("保存钩子失败:", error);
            this.showToast(error.message || "保存失败");
        }
    },

    /**
     * 删除钩子
     */
    async deleteHook(hookId) {
        if (!confirm("确定要删除这个钩子吗？")) {
            return;
        }

        // 过滤掉要删除的钩子
        const updatedHooks = this.hooks.filter(h => h.id !== hookId);

        try {
            const response = await fetch("/api/claude/hooks", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(updatedHooks),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "删除失败");
            }

            this.loadHooks();
            this.showToast("钩子已删除");
        } catch (error) {
            console.error("删除钩子失败:", error);
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
const hooksStyle = document.createElement("style");
hooksStyle.textContent = `
    .hook-table {
        width: 100%;
        border-collapse: collapse;
    }

    .hook-table th,
    .hook-table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid var(--border-color, #334155);
    }

    .hook-table th {
        font-weight: 600;
        background: var(--header-bg, #1e293b);
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
    }

    .hook-name {
        font-weight: 500;
        color: var(--text-primary, #f1f5f9);
    }

    .hook-type {
        font-family: monospace;
        color: var(--text-secondary, #94a3b8);
    }

    .hook-tools {
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
    }

    .hook-action {
        font-size: 12px;
        color: var(--text-primary, #f1f5f9);
    }

    .hook-status {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
    }

    .status-enabled {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
    }

    .status-disabled {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
    }

    .hook-actions {
        display: flex;
        gap: 8px;
    }

    .hook-types-list {
        margin-bottom: 16px;
        padding: 12px;
        background: var(--card-bg, #1e293b);
        border-radius: 6px;
        border: 1px solid var(--border-color, #334155);
    }

    .hook-types-list h4 {
        margin: 0 0 8px 0;
        font-size: 14px;
        color: var(--text-primary, #f1f5f9);
    }

    .hook-types-list ul {
        margin: 0;
        padding-left: 20px;
    }

    .hook-types-list li {
        margin: 4px 0;
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
    }

    .hook-types-list strong {
        color: var(--accent-color, #38bdf8);
    }

    .hooks-actions-bar {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
    }

    .hook-list-container {
        margin-top: 16px;
    }

    /* 表格行悬停效果 */
    .hook-table tbody tr:hover {
        background: var(--hover-bg, rgba(255, 255, 255, 0.05));
    }

    /* 空状态和加载状态 */
    .empty-placeholder,
    .loading-placeholder,
    .error-placeholder {
        padding: 24px;
        text-align: center;
        color: var(--text-secondary, #94a3b8);
        background: var(--card-bg, #1e293b);
        border-radius: 6px;
    }
`;
document.head.appendChild(hooksStyle);

// 导出模块
window.HooksManager = HooksManager;
