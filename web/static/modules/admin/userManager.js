/**
 * 用户管理组件
 * 显示和管理用户列表
 */

const UserManager = {
    // 用户列表
    users: [];
    // 分页信息
    pagination: {
        page: 1,
        limit: 20,
        total: 0
    },
    // 容器元素
    container: null,
    // 当前选中的用户
    selectedUser: null,

    /**
     * 初始化组件
     * @param {HTMLElement} container - 容器元素
     */
    init(container) {
        this.container = container;
        this.render();
    }

    /**
     * 渲染组件
     */
    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="user-manager">
                <div class="user-manager-header">
                    <h3 class="user-manager-title">用户管理</h3>
                    <button class="user-manager-refresh-btn" id="user-refresh-btn">刷新</button>
                    <button class="user-manager-close-btn" id="user-close-btn">关闭</button>
                </div>
                <div class="user-list" id="user-list">
                    <div class="loading">加载中...</div>
                </div>
            </div>
        `;
    }

    /**
     * 加载用户列表
     * @param {number} page - 页码
     */
    async loadUsers(page = 1) {
        try {
            const user = Auth.getUser();
            if (!user) {
                this.showError('请先登录');
                return;
            }

            const result = await AdminAPI.getUserList(page, this.pagination.limit);

            this.users = result.users;
            this.pagination = {
                page: page,
                limit: this.pagination.limit,
                total: result.total
            };

            this.renderUsers();
        } catch (error) {
            this.showError(error.message || '加载失败');
        }
    },

    /**
     * 渲染用户列表
     */
    renderUsers() {
        const listEl = document.getElementById('user-list');
        if (!listEl) return;

        if (this.users.length === 0) {
            listEl.innerHTML = '<div class="empty-message">暂无用户</div>';
                return;
            }

        listEl.innerHTML = this.users.map(user => this.createUserItem(user)).join('');
    },

    /**
     * 创建用户项
     * @param {Object} user - 用户信息
     * @returns {string} HTML 字符串
     */
    createUserItem(user) {
        const statusClass = user.is_active ? 'active' : 'inactive';
        const statusText = user.is_active ? '启用' : '已禁用';
        const roleClass = user.is_admin ? 'admin' : 'user';
        const roleText = user.is_admin ? '管理员' : '普通用户';
        const lastLogin = user.last_login
            ? new Date(user.last_login).toLocaleString('zh-CN')
            : '从未登录';

        return `
            <div class="user-item ${user.is_active ? '' : 'inactive' }" data-user-id="${user.user_id}">
                <div class="user-info">
                    <div class="user-name">${this.escapeHtml(user.name)}</div>
                    <div class="user-username">${this.escapeHtml(user.username)}</div>
                    <div class="user-meta">
                        <div class="meta-item">
                            <span class="meta-label">状态:</span>
                            <span class="meta-value ${statusClass}">${statusText}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">角色:</span>
                            <span class="meta-value ${roleClass}">${roleText}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">创建时间:</span>
                            <span class="meta-value">${new Date(user.created_at).toLocaleString('zh-CN')}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">最后登录:</span>
                            <span class="meta-value">${lastLogin}</span>
                        </div>
                    </div>
                </div>
                <div class="user-actions">
                    <button class="user-action-btn toggle-status ${user.is_active ? 'disable' : 'enable' }" data-user-id="${user.user_id}" data-current-status="${user.is_active}">
                        ${user.is_active ? '禁用' : '启用' }
                    </button>
                </div>
            </div>
        `;
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 刷新按钮
        document.getElementById('user-refresh-btn')?.addEventListener('click', () => {
            this.loadUsers(this.pagination.page);
        });

        // 关闭按钮
        document.getElementById('user-close-btn')?.addEventListener('click', () => {
            if (this.container) {
                this.container.style.display = 'none';
            }
        });

        // 状态切换按钮事件 (使用事件委托)
        document.getElementById('user-list')?.addEventListener('click', async (e) => {
            if (e.target.classList.contains('toggle-status')) {
                const userId = e.target.dataset.userId;
                const currentStatus = e.target.dataset.currentStatus === 'true';
                const newStatus = !currentStatus;
                const action = newStatus ? '启用' : '禁用';

                if (confirm(`确定要${action}此用户吗?`)) {
                    await this.toggleUserStatus(userId, newStatus);
                }
            }
        });
    },

    /**
     * 切换用户状态
     * @param {string} userId - 用户 ID
     * @param {boolean} isActive - 是否激活
     */
    async toggleUserStatus(userId, isActive) {
        try {
            await AdminAPI.updateUserStatus(userId, isActive);
            // 更新本地数据
            const userIndex = this.users.findIndex(u => u.user_id === userId);
            if (userIndex !== -1) {
                this.users[userIndex].is_active = isActive;
                this.renderUsers();
            }
            this.showMessage(`用户已${isActive ? '启用' : '禁用'}`);
        } catch (error) {
            this.showError(error.message || '操作失败');
        }
    },

    /**
     * 显示错误信息
     * @param {string} message - 错误信息
     */
    showError(message) {
        const existingError = this.container.querySelector('.error-message');
        if (existingError) {
            existingError.textContent = message;
            existingError.style.display = 'block';
        } else {
            const errorEl = document.createElement('div');
            errorEl.className = 'error-message';
            errorEl.textContent = message;
            this.container.querySelector('.user-list').prepend(errorEl);
        }
    },

    /**
     * 显示提示信息
     * @param {string} message - 提示信息
     */
    showMessage(message) {
        const existingMessage = this.container.querySelector('.success-message');
        if (existingMessage) {
            existingMessage.textContent = message;
            existingMessage.style.display = 'block';
        } else {
            const messageEl = document.createElement('div');
            messageEl.className = 'success-message';
            messageEl.textContent = message;
            this.container.querySelector('.user-list').prepend(messageEl);
            setTimeout(() => messageEl.remove(), 3000);
        }
    },

    /**
     * HTML 转义
     * @param {string} text - 待转义的文本
     * @returns {string} 转义后的文本
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 导出到全局命名空间
window.UserManager = UserManager;
