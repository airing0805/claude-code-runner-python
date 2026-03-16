/**
 * 认证模块
 * 处理用户登录、注册、登出和令牌管理
 */

const Auth = {
    // 存储键名
    STORAGE_KEYS: {
        ACCESS_TOKEN: 'auth_access_token',
        REFRESH_TOKEN: 'auth_refresh_token',
        USER_INFO: 'auth_user_info',
        TOKEN_EXPIRES_AT: 'auth_token_expires_at'
    },

    // 当前用户信息
    currentUser: null,

    // 刷新令牌定时器
    refreshTimer: null,

    /**
     * 初始化认证模块
     */
    init() {
        // 页面加载时检查登录状态
        this.checkLoginState();

        // 设置令牌刷新定时器（每5分钟检查一次）
        this.refreshTimer = setInterval(() => {
            this.checkAndRefreshToken();
        }, 5 * 60 * 1000);

        // 拦截 fetch 请求，自动添加认证头
        this.interceptFetch();
    },

    /**
     * 拦截 fetch 请求，自动添加 Authorization 头
     */
    interceptFetch() {
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const url = args[0];
            const options = args[1] || {};

            // 如果是 API 请求且用户已登录，自动添加认证头
            if (typeof url === 'string' && url.startsWith('/api/') && !url.startsWith('/api/auth/')) {
                const token = this.getToken();
                if (token) {
                    options.headers = {
                        ...options.headers,
                        'Authorization': `Bearer ${token}`
                    };
                }
            }

            return originalFetch(...args);
        };
    },

    /**
     * 用户登录
     * @param {string} username - 用户名（邮箱）
     * @param {string} password - 密码
     * @returns {Promise<Object>} 登录结果
     */
    async login(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '登录失败');
            }

            const data = await response.json();

            // 存储令牌
            this.storeToken(data);

            // 获取用户信息
            await this.getCurrentUser();

            return { success: true };
        } catch (error) {
            console.error('登录失败:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * 用户注册
     * @param {string} username - 用户名（邮箱）
     * @param {string} password - 密码
     * @param {string} name - 显示名称
     * @returns {Promise<Object>} 注册结果
     */
    async register(username, password, name) {
        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password, name })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '注册失败');
            }

            const data = await response.json();

            return { success: true, data };
        } catch (error) {
            console.error('注册失败:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * 用户登出
     */
    logout() {
        // 清除存储
        localStorage.removeItem(this.STORAGE_KEYS.ACCESS_TOKEN);
        localStorage.removeItem(this.STORAGE_KEYS.REFRESH_TOKEN);
        localStorage.removeItem(this.STORAGE_KEYS.USER_INFO);
        localStorage.removeItem(this.STORAGE_KEYS.TOKEN_EXPIRES_AT);

        // 清除当前用户
        this.currentUser = null;

        // 清除刷新定时器
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }

        // 更新导航栏
        AuthUI.updateNavbar();
    },

    /**
     * 获取当前用户信息
     * @returns {Promise<Object>} 用户信息
     */
    async getCurrentUser() {
        try {
            const token = this.getToken();
            if (!token) {
                return null;
            }

            const response = await fetch('/api/auth/me', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                // Token 无效，清除存储
                this.logout();
                return null;
            }

            const user = await response.json();

            // 存储用户信息
            localStorage.setItem(this.STORAGE_KEYS.USER_INFO, JSON.stringify(user));
            this.currentUser = user;

            return user;
        } catch (error) {
            console.error('获取用户信息失败:', error);
            return null;
        }
    },

    /**
     * 检查登录状态
     */
    checkLoginState() {
        const token = this.getToken();
        const userInfo = localStorage.getItem(this.STORAGE_KEYS.USER_INFO);

        if (token && userInfo) {
            try {
                this.currentUser = JSON.parse(userInfo);
                // 验证令牌是否过期
                this.checkAndRefreshToken();
            } catch (error) {
                console.error('解析用户信息失败:', error);
                this.logout();
            }
        } else {
            this.currentUser = null;
        }

        // 更新导航栏
        AuthUI.updateNavbar();
    },

    /**
     * 检查并刷新令牌
     */
    async checkAndRefreshToken() {
        const expiresAt = localStorage.getItem(this.STORAGE_KEYS.TOKEN_EXPIRES_AT);
        if (!expiresAt) {
            return;
        }

        const now = Date.now();
        const expiresTime = parseInt(expiresAt);

        // 如果令牌将在10分钟内过期，则刷新
        if (expiresTime - now < 10 * 60 * 1000) {
            await this.refreshToken();
        } else if (now > expiresTime) {
            // 令牌已过期，登出
            this.logout();
        }
    },

    /**
     * 刷新访问令牌
     */
    async refreshToken() {
        try {
            const refreshToken = localStorage.getItem(this.STORAGE_KEYS.REFRESH_TOKEN);
            if (!refreshToken) {
                throw new Error('刷新令牌不存在');
            }

            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ refresh_token: refreshToken })
            });

            if (!response.ok) {
                throw new Error('刷新令牌失败');
            }

            const data = await response.json();

            // 存储新令牌
            this.storeToken(data);

            // 重新获取用户信息
            await this.getCurrentUser();
        } catch (error) {
            console.error('刷新令牌失败:', error);
            this.logout();
        }
    },

    /**
     * 存储令牌
     * @param {Object} tokenData - 令牌数据
     */
    storeToken(tokenData) {
        const expiresAt = Date.now() + (tokenData.expires_in * 1000);

        localStorage.setItem(this.STORAGE_KEYS.ACCESS_TOKEN, tokenData.access_token);
        localStorage.setItem(this.STORAGE_KEYS.REFRESH_TOKEN, tokenData.refresh_token);
        localStorage.setItem(this.STORAGE_KEYS.TOKEN_EXPIRES_AT, expiresAt.toString());
    },

    /**
     * 获取访问令牌
     * @returns {string|null} 访问令牌
     */
    getToken() {
        return localStorage.getItem(this.STORAGE_KEYS.ACCESS_TOKEN);
    },

    /**
     * 检查是否已登录
     * @returns {boolean} 是否已登录
     */
    isLoggedIn() {
        return this.currentUser !== null;
    },

    /**
     * 获取当前用户
     * @returns {Object|null} 当前用户信息
     */
    getUser() {
        return this.currentUser;
    }
};

// 导出到全局命名空间
window.Auth = Auth;
