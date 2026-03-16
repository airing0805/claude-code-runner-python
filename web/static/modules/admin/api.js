/**
 * 管理员 API 模块
 * 射装管理员相关的 API 调用
 */

const AdminAPI = {
    /**
     * 获取用户列表
     * @param {number} page - 页码
     * @param {number} limit - 每页数量
     * @returns {Promise<Object>} 用户列表响应
     */
    async getUserList(page = 1, limit = 20) {
        const token = Auth.getToken();
        const response = await fetch(`/api/admin/users?page=${page}&limit=${limit}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '获取用户列表失败');
        }

        return await response.json();
    },

    /**
     * 更新用户状态
     * @param {string} userId - 用户 ID
     * @param {boolean} isActive - 是否激活
     * @returns {Promise<void>}
     */
    async updateUserStatus(userId, isActive) {
        const token = Auth.getToken();
        const response = await fetch(`/api/admin/users/${userId}/status`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_active: isActive })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '更新用户状态失败');
        }
    },

    /**
     * 删除用户
     * @param {string} userId - 用户 ID
     * @returns {Promise<void>}
     */
    async deleteUser(userId) {
        const token = Auth.getToken();
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '删除用户失败');
        }
    },

    /**
     * 重置用户密码
     * @param {string} userId - 用户 ID
     * @param {string} newPassword - 新密码
     * @returns {Promise<Object>} 重置结果
     */
    async resetUserPassword(userId, newPassword) {
        const token = Auth.getToken();
        const response = await fetch(`/api/admin/users/${userId}/reset-password`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ new_password: newPassword })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '重置密码失败');
        }

        return await response.json();
    },

    /**
     * 获取 API 密钥列表
     * @param {string} userId - 用户 ID（可选，不传则获取所有）
     * @returns {Promise<Object>} 密钥列表响应
     */
    async getAPIKeyList(userId = null) {
        const token = Auth.getToken();
        let url = '/api/admin/api-keys';
        if (userId) {
            url += `?user_id=${userId}`;
        }

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '获取密钥列表失败');
        }

        return await response.json();
    },

    /**
     * 创建 API 密钥
     * @param {string} name - 密钥名称
     * @param {string} permissions - 权限类型
     * @param {string} userId - 用户 ID
     * @returns {Promise<Object>} 创建结果
     */
    async createAPIKey(name, permissions, userId) {
        const token = Auth.getToken();
        const response = await fetch('/api/admin/api-keys', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                permissions: permissions,
                user_id: userId
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '创建密钥失败');
        }

        return await response.json();
    },

    /**
     * 撤销 API 密钥
     * @param {string} keyId - 密钥 ID
     * @returns {Promise<void>}
     */
    async revokeAPIKey(keyId) {
        const token = Auth.getToken();
        const response = await fetch(`/api/admin/api-keys/${keyId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '撤销密钥失败');
        }
    }
};

// 导出到全局命名空间
window.AdminAPI = AdminAPI;
