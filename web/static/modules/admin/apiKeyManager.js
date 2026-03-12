/**
 * API 密钥管理组件
 * 显示和管理用户的 API 密钥
 */

const APIKeyManager = {
    // API 密钥列表
    keys: [],
    // 当前选中的密钥
    selectedKey: null,
    // 容器元素
    container: null,

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
            <div class="api-key-manager">
                <div class="api-key-header">
                    <h3 class="api-key-title">API 密钥管理</h3>
                    <button class="api-key-create-btn" id="api-key-create-btn">+ 创建新密钥</button>
                <button class="api-key-refresh-btn" id="api-key-refresh-btn">刷新</button>
                <button class="api-key-close-btn" id="api-key-close-btn">关闭</button>
                </div>
                <div class="api-key-list" id="api-key-list">
                    <div class="loading">加载中...</div>
                </div>
            </div>
        `;
    },

    /**
     * 加载 API 密钥列表
     */
    async loadKeys() {
        try {
            const user = Auth.getUser();
            if (!user) {
                this.showError('请先登录');
                return;
            }

            const keys = await AdminAPI.getAPIKeys(user.user_id);

            this.keys = keys;
            this.renderKeys();
        } catch (error) {
            this.showError(error.message || '加载失败');
        }
    },

    /**
     * 渲染密钥列表
     */
    renderKeys() {
        const listEl = document.getElementById('api-key-list');
        if (!listEl) return;

        if (this.keys.length === 0) {
            listEl.innerHTML = '<div class="empty-message">暂无 API 密钥</div>';
                return;
            }

        listEl.innerHTML = this.keys.map(key => this.createKeyItem(key)).join('');
    },

    /**
     * 创建密钥项
     * @param {Object} key - 密钥信息
     * @returns {string} HTML 字符串
     */
    createKeyItem(key) {
        const statusClass = key.is_active ? 'active' : 'inactive';
        const statusText = key.is_active ? '启用' : '已禁用';
        const lastUsed = key.last_used_at
            ? new Date(key.last_used_at).toLocaleString('zh-CN')
            : '从未使用';

        const expires = key.expires_at
            ? new Date(key.expires_at).toLocaleString('zh-CN')
            : '永久有效';

        return `
            <div class="api-key-item ${key.is_active ? '' : 'inactive' } data-key-id="${key.key_id}">
                <div class="api-key-info">
                    <div class="api-key-name">${this.escapeHtml(key.name)}</div>
                    <div class="api-key-prefix">
                        <span class="prefix-label">前缀:</span>
                        <span class="prefix-value">${this.escapeHtml(key.prefix)}</span>
                    </div>
                    <div class="api-key-meta">
                        <div class="meta-item">
                            <span class="meta-label">状态:</span>
                            <span class="meta-value ${statusClass}">${statusText}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">权限:</span>
                            <span class="meta-value">${this.escapeHtml(key.permissions)}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">创建:</span>
                            <span class="meta-value">${new Date(key.created_at).toLocaleString('zh-CN')}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">最后使用:</span>
                            <span class="meta-value">${lastUsed}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">过期时间:</span>
                            <span class="meta-value">${expires}</span>
                        </div>
                    </div>
                </div>
                <div class="api-key-actions">
                    <button class="api-key-action-btn revoke" data-key-id="${key.key_id}" title="撤销密钥">
                        撤销
                    </button>
                </div>
            </div>
        `;
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 创建密钥按钮
        document.getElementById('api-key-create-btn')?.addEventListener('click', () => {
            this.showCreateDialog();
        });

        // 刷新按钮
        document.getElementById('api-key-refresh-btn')?.addEventListener('click', () => {
            this.loadKeys();
        });

        // 关闭按钮
        document.getElementById('api-key-close-btn')?.addEventListener('click', () => {
            if (this.container) {
                this.container.style.display = 'none';
            }
        });

        // 撤销按钮事件 (使用事件委托)
        listEl.addEventListener('click', async (e) => {
            if (e.target.classList.contains('revoke')) {
                const keyId = e.target.dataset.keyId;
                if (confirm('确定要撤销此密钥吗？')) {
                    await this.revokeKey(keyId);
                }
            }
        });
    },

    /**
     * 撤销密钥
     * @param {string} keyId - 密钥 ID
     */
    async revokeKey(keyId) {
        try {
            await AdminAPI.revokeAPIKey(keyId);
            this.keys = this.keys.filter(k => k.key_id !== keyId);
            this.renderKeys();
            this.showMessage('密钥已撤销');
        } catch (error) {
            this.showError(error.message || '撤销失败');
        }
    },

    /**
     * 显示创建密钥对话框
     */
    showCreateDialog() {
        const dialog = document.createElement('div');
        dialog.className = 'api-key-dialog';
        dialog.innerHTML = `
            <div class="dialog-content">
                <div class="dialog-header">
                    <h3>创建新 API 密钥</h3>
                    <button class="dialog-close-btn">&times;</button>
                </div>
                <div class="dialog-body">
                    <div class="form-group">
                        <label for="api-key-name-input">密钥名称</label>
                        <input type="text" id="api-key-name-input" placeholder="例如： 开发环境密钥">
                    </div>
                    <div class="form-group">
                        <label for="api-key-permissions-select">权限</label>
                        <select id="api-key-permissions-select">
                            <option value="read_write">读写</option>
                            <option value="read_only">只读</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="api-key-user-select">用户 ID</label>
                        <input type="text" id="api-key-user-input" placeholder="用户 ID">
                    </div>
                </div>
                <div class="dialog-footer">
                    <button class="dialog-btn cancel" id="api-key-cancel-dialog">取消</button>
                    <button class="dialog-btn primary" id="api-key-confirm-create">创建</button>
                </div>
            </div>
        `;

        document.body.appendChild(dialog);

        // 绑定事件
        document.getElementById('api-key-cancel-dialog').addEventListener('click', () => {
                dialog.remove();
            });

        document.getElementById('api-key-confirm-create').addEventListener('click', async () => {
                const name = document.getElementById('api-key-name-input').value.trim();
                const permissions = document.getElementById('api-key-permissions-select').value;
                const userId = document.getElementById('api-key-user-input').value.trim();

                if (!name) {
                    this.showError('请输入密钥名称');
                    return;
                }

                if (!userId) {
                    this.showError('请输入用户 ID');
                    return;
                }

                try {
                    const result = await AdminAPI.createAPIKey(name, permissions, userId);
                    dialog.remove();
                    // 显示完整密钥（只显示一次)
                    this.showFullKey(result.key, result.name);
                    await this.loadKeys();
                } catch (error) {
                    this.showError(error.message || '创建失败');
                }
            });
        });
    },

    /**
     * 显示完整密钥对话框
     * @param {string} key - 密钥
     * @param {string} name - 密钥名称
     */
    showFullKey(key, name) {
        const dialog = document.createElement('div');
        dialog.className = 'api-key-dialog full-key-dialog';
        dialog.innerHTML = `
            <div class="dialog-content">
                <div class="dialog-header">
                    <h3>API 密钥已创建</h3>
                    <button class="dialog-close-btn">&times;</button>
                </div>
                <div class="dialog-body">
                    <div class="warning-message">
                        <p><strong>重要提示:</strong> 请立即复制并安全保存您的 API 密钥。 此密钥只会显示一次!</p>
                    <div class="full-key-container">
                        <code class="full-key" id="full-key-display">${this.escapeHtml(key)}</code>
                        <button class="copy-key-btn" id="copy-full-key">复制密钥</button>
                    </div>
                    <p class="key-info">
                        <strong>密钥名称:</strong> ${this.escapeHtml(name)} |
                    </p>
                </div>
                <div class="dialog-footer">
                    <button class="dialog-btn primary" id="close-full-key-dialog">我已保存</button>
                </div>
            </div>
        `;

        document.body.appendChild(dialog);

        // 绑定事件
        document.getElementById('close-full-key-dialog').addEventListener('click', () => {
            dialog.remove();
        });

        document.getElementById('copy-full-key').addEventListener('click', async () => {
            const keyEl = document.getElementById('full-key-display');
            await navigator.clipboard.writeText(keyEl.textContent);
            const btn = document.getElementById('copy-full-key');
            btn.textContent = '已复制!';
            setTimeout(() => {
                btn.textContent = '复制密钥';
            }, 2000);
        });

        document.getElementById('dialog-close-btn').addEventListener('click', () => {
            dialog.remove();
        });
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
            this.container.querySelector('.api-key-list').prepend(errorEl);
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
            this.container.querySelector('.api-key-list').prepend(messageEl);
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
};

// 导出到全局命名空间
window.APIKeyManager = APIKeyManager;
