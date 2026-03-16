/**
 * 技能系统管理模块
 * 负责加载和展示技能信息
 */

const SkillManager = {
    /** 技能列表数据 */
    skills: [],
    /** 分类列表 */
    categories: [],
    /** 当前选中的分类 */
    currentCategory: null,
    /** 是否已加载数据 */
    isLoaded: false,

    /**
     * 初始化技能管理模块
     */
    init() {
        this.bindEvents();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 刷新按钮
        const refreshBtn = document.getElementById("refresh-skills-btn");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => this.loadSkills());
        }

        // 详情对话框关闭
        const closeDetailBtn = document.getElementById("close-skill-detail");
        if (closeDetailBtn) {
            closeDetailBtn.addEventListener("click", () => this.hideDetailDialog());
        }

        // 对话框背景点击关闭
        const detailDialog = document.getElementById("skill-detail-dialog");
        if (detailDialog) {
            detailDialog.addEventListener("click", (e) => {
                if (e.target === detailDialog) {
                    this.hideDetailDialog();
                }
            });
        }
    },

    /**
     * 当视图显示时加载数据
     */
    onShow() {
        if (!this.isLoaded) {
            this.loadSkills();
            this.isLoaded = true;
        }
    },

    /**
     * 加载技能列表
     */
    async loadSkills() {
        const skillList = document.getElementById("skill-list");
        if (!skillList) return;

        skillList.innerHTML = '<div class="loading-placeholder">加载中...</div>';

        try {
            let url = "/api/skills";
            if (this.currentCategory) {
                url += `?category=${encodeURIComponent(this.currentCategory)}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            this.skills = data.skills || [];
            this.categories = data.categories || [];
            this.renderCategories();
            this.renderSkills();
        } catch (error) {
            console.error("加载技能列表失败:", error);
            skillList.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 渲染分类标签
     */
    renderCategories() {
        const categoryContainer = document.getElementById("skill-categories");
        if (!categoryContainer) return;

        let html = `<button class="category-btn ${!this.currentCategory ? 'active' : ''}"
                          data-category="">全部</button>`;

        for (const category of this.categories) {
            html += `<button class="category-btn ${this.currentCategory === category.name ? 'active' : ''}"
                            data-category="${this.escapeHtml(category.name)}">
                        ${this.escapeHtml(category.name)} (${category.count})
                     </button>`;
        }

        categoryContainer.innerHTML = html;

        // 使用事件委托绑定点击事件
        categoryContainer.onclick = (e) => {
            const btn = e.target.closest(".category-btn");
            if (!btn) return;

            const category = btn.dataset.category;
            // 处理空字符串和null的情况
            this.currentCategory = category || null;
            this.loadSkills();
        };
    },

    /**
     * 渲染技能列表
     */
    renderSkills() {
        const skillList = document.getElementById("skill-list");
        if (!skillList) return;

        if (this.skills.length === 0) {
            skillList.innerHTML = '<div class="empty-placeholder">暂无技能</div>';
            return;
        }

        let html = '<div class="skill-grid">';

        for (const skill of this.skills) {
            const statusClass = skill.is_enabled ? "skill-enabled" : "skill-disabled";
            const statusText = skill.is_enabled ? "已启用" : "已禁用";
            const toggleText = skill.is_enabled ? "禁用" : "启用";
            const toggleBtnClass = skill.is_enabled ? "btn-warning" : "btn-success";

            html += `
                <div class="skill-card">
                    <div class="skill-header">
                        <h3 class="skill-name">${this.escapeHtml(skill.name)}</h3>
                        <span class="skill-status ${statusClass}">${statusText}</span>
                    </div>
                    <div class="skill-category">${this.escapeHtml(skill.category)}</div>
                    <p class="skill-description">${this.escapeHtml(skill.description)}</p>
                    <div class="skill-meta">
                        <span class="skill-version">v${this.escapeHtml(skill.version)}</span>
                        ${skill.tags && skill.tags.length > 0
                            ? `<span class="skill-tags">${skill.tags.map(t => `#${t}`).join(" ")}</span>`
                            : ""}
                    </div>
                    <div class="skill-actions">
                        <button class="btn-link" onclick="SkillManager.showSkillDetail('${skill.skill_id}')">查看详情</button>
                        <button class="btn-sm ${toggleBtnClass}" onclick="SkillManager.toggleSkill('${skill.skill_id}', ${!skill.is_enabled})">
                            ${toggleText}
                        </button>
                    </div>
                </div>
            `;
        }

        html += '</div>';
        skillList.innerHTML = html;
    },

    /**
     * 显示技能详情
     */
    async showSkillDetail(skillId) {
        const detailDialog = document.getElementById("skill-detail-dialog");
        const detailContent = document.getElementById("skill-detail-content");
        if (!detailDialog || !detailContent) return;

        detailContent.innerHTML = '<div class="loading-placeholder">加载中...</div>';
        detailDialog.style.display = "flex";

        try {
            const response = await fetch(`/api/skills/${skillId}`);
            if (!response.ok) {
                throw new Error("技能不存在");
            }

            const skill = await response.json();
            this.renderSkillDetail(skill);
        } catch (error) {
            console.error("加载技能详情失败:", error);
            detailContent.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 渲染技能详情
     */
    renderSkillDetail(skill) {
        const detailContent = document.getElementById("skill-detail-content");
        if (!detailContent) return;

        const statusClass = skill.is_enabled ? "skill-enabled" : "skill-disabled";
        const statusText = skill.is_enabled ? "已启用" : "已禁用";
        const toggleText = skill.is_enabled ? "禁用" : "启用";
        const toggleBtnClass = skill.is_enabled ? "btn-warning" : "btn-success";

        let html = `
            <div class="skill-detail-header">
                <h2>${this.escapeHtml(skill.name)}</h2>
                <span class="skill-status ${statusClass}">${statusText}</span>
            </div>
            <div class="skill-detail-meta">
                <span>分类: ${this.escapeHtml(skill.category)}</span>
                <span>版本: ${this.escapeHtml(skill.version)}</span>
                <span>作者: ${this.escapeHtml(skill.author)}</span>
            </div>
            <p class="skill-detail-description">${this.escapeHtml(skill.description)}</p>
        `;

        // 标签
        if (skill.tags && skill.tags.length > 0) {
            html += `<div class="skill-detail-tags">${skill.tags.map(t => `<span class="tag">#${this.escapeHtml(t)}</span>`).join("")}</div>`;
        }

        // 参数
        if (skill.parameters && skill.parameters.length > 0) {
            html += `<h3>参数配置</h3><table class="detail-table">`;
            html += `<thead><tr><th>参数</th><th>类型</th><th>默认值</th><th>说明</th></tr></thead><tbody>`;
            for (const param of skill.parameters) {
                html += `<tr>
                    <td>${this.escapeHtml(param.name)}</td>
                    <td><code>${this.escapeHtml(param.type)}</code></td>
                    <td><code>${param.default !== null ? this.escapeHtml(String(param.default)) : "-"}</code></td>
                    <td>${this.escapeHtml(param.description)}</td>
                </tr>`;
            }
            html += `</tbody></table>`;
        }

        // 使用示例
        if (skill.examples && skill.examples.length > 0) {
            html += `<h3>使用示例</h3>`;
            for (const example of skill.examples) {
                html += `<div class="example-block">
                    <pre><code>${this.escapeHtml(example.code || "")}</code></pre>
                </div>`;
            }
        }

        // 权限
        if (skill.permissions && skill.permissions.length > 0) {
            html += `<h3>所需权限</h3><ul class="permission-list">`;
            for (const perm of skill.permissions) {
                html += `<li>${this.escapeHtml(perm)}</li>`;
            }
            html += `</ul>`;
        }

        // 文件路径
        html += `<div class="skill-detail-path"><small>文件路径: ${this.escapeHtml(skill.file_path)}</small></div>`;

        // 操作按钮
        html += `
            <div class="skill-detail-actions">
                <button class="btn ${toggleBtnClass}" onclick="SkillManager.toggleSkillFromDetail('${skill.skill_id}', ${!skill.is_enabled})">
                    ${toggleText}技能
                </button>
            </div>
        `;

        detailContent.innerHTML = html;
    },

    /**
     * 隐藏详情对话框
     */
    hideDetailDialog() {
        const detailDialog = document.getElementById("skill-detail-dialog");
        if (detailDialog) {
            detailDialog.style.display = "none";
        }
    },

    /**
     * 切换技能启用状态
     */
    async toggleSkill(skillId, enable) {
        try {
            const action = enable ? "enable" : "disable";
            const response = await fetch(`/api/skills/${skillId}/${action}`, {
                method: "POST",
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "操作失败");
            }

            this.showToast(enable ? "技能已启用" : "技能已禁用");
            this.loadSkills();
        } catch (error) {
            console.error("切换技能状态失败:", error);
            this.showToast(error.message || "操作失败");
        }
    },

    /**
     * 从详情对话框切换技能状态
     */
    toggleSkillFromDetail(skillId, enable) {
        this.toggleSkill(skillId, enable);
        this.hideDetailDialog();
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
const skillStyle = document.createElement("style");
skillStyle.textContent = `
    .skill-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 16px;
    }

    .skill-card {
        background: var(--card-bg, #1e293b);
        border: 1px solid var(--border-color, #eee);
        border-radius: 8px;
        padding: 16px;
        transition: box-shadow 0.2s;
    }

    .skill-card:hover {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .skill-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 8px;
    }

    .skill-name {
        font-size: 16px;
        font-weight: 600;
        margin: 0;
        color: var(--text-primary, #333);
    }

    .skill-status {
        font-size: 12px;
        padding: 2px 8px;
        border-radius: 10px;
        font-weight: 500;
    }

    .skill-enabled {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
    }

    .skill-disabled {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
    }

    .skill-category {
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
        margin-bottom: 8px;
    }

    .skill-description {
        font-size: 14px;
        color: var(--text-secondary, #94a3b8);
        margin: 0 0 12px 0;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .skill-meta {
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
        margin-bottom: 12px;
    }

    .skill-version {
        font-family: monospace;
        background: var(--header-bg, #334155);
        color: var(--text-secondary, #94a3b8);
        padding: 2px 6px;
        border-radius: 4px;
    }

    .skill-tags {
        margin-left: 8px;
        color: #38bdf8;
    }

    .skill-actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 12px;
        border-top: 1px solid var(--border-color, #eee);
    }

    .btn-link {
        background: none;
        border: none;
        color: var(--primary-color, #007bff);
        cursor: pointer;
        font-size: 14px;
        padding: 4px 8px;
    }

    .btn-link:hover {
        text-decoration: underline;
    }

    .btn-sm {
        padding: 6px 12px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
    }

    .btn-success {
        background: #28a745;
        color: white;
    }

    .btn-warning {
        background: #ffc107;
        color: #333;
    }

    /* 分类标签 */
    #skill-categories {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 16px;
    }

    .category-btn {
        padding: 6px 12px;
        border: 1px solid var(--border-color, #475569);
        background: var(--card-bg, #1e293b);
        border-radius: 16px;
        cursor: pointer;
        font-size: 13px;
        color: var(--text-secondary, #94a3b8);
        transition: all 0.2s;
    }

    .category-btn:hover {
        border-color: #7c3aed;
        color: #38bdf8;
    }

    .category-btn.active {
        background: var(--primary-color, #7c3aed);
        border-color: var(--primary-color, #7c3aed);
        color: white;
    }

    /* 详情对话框 */
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
        background: var(--card-bg, #1e293b);
        border-radius: 8px;
        padding: 24px;
        width: 90%;
        max-width: 600px;
        max-height: 80vh;
        overflow-y: auto;
    }

    .dialog-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    .dialog-title {
        margin: 0;
        font-size: 18px;
        color: var(--text-primary, #f1f5f9);
    }

    .dialog-close {
        background: none;
        border: none;
        font-size: 24px;
        color: var(--text-secondary, #94a3b8);
        cursor: pointer;
        padding: 0;
        line-height: 1;
    }

    .dialog-close:hover {
        color: var(--text-primary, #f1f5f9);
    }

    .skill-detail-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    .skill-detail-header h2 {
        margin: 0;
        font-size: 20px;
    }

    .skill-detail-meta {
        display: flex;
        gap: 16px;
        font-size: 13px;
        color: var(--text-secondary, #94a3b8);
        margin-bottom: 16px;
    }

    .skill-detail-description {
        margin: 0 0 16px 0;
        line-height: 1.6;
    }

    .skill-detail-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 16px;
    }

    .tag {
        background: var(--header-bg, #334155);
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        color: var(--text-secondary, #94a3b8);
    }

    .detail-table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
    }

    .detail-table th,
    .detail-table td {
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid var(--border-color, #eee);
        font-size: 13px;
    }

    .detail-table th {
        background: var(--header-bg, #334155);
        font-weight: 600;
    }

    .detail-table code {
        background: var(--header-bg, #334155);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 12px;
    }

    .example-block {
        background: var(--header-bg, #334155);
        border-radius: 6px;
        padding: 12px;
        margin: 8px 0;
        overflow-x: auto;
    }

    .example-block pre {
        margin: 0;
    }

    .example-block code {
        font-family: monospace;
        font-size: 13px;
    }

    .permission-list {
        margin: 8px 0;
        padding-left: 20px;
    }

    .permission-list li {
        margin: 4px 0;
    }

    .skill-detail-path {
        margin-top: 16px;
        color: var(--text-secondary, #94a3b8);
    }

    .skill-detail-actions {
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--border-color, #eee);
    }

    /* 通用样式 */
    .loading-placeholder,
    .error-placeholder,
    .empty-placeholder {
        text-align: center;
        padding: 40px;
        color: var(--text-secondary, #94a3b8);
    }

    .error-placeholder {
        color: #dc3545;
    }
`;
document.head.appendChild(skillStyle);

// 导出模块
window.SkillManager = SkillManager;
