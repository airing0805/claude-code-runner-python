/**
 * 认证UI模块
 * 处理登录/注册对话框和导航栏更新
 */

const AuthUI = {
    /**
     * 初始化认证UI
     */
    init() {
        // 初始化登录对话框
        this.initLoginDialog();

        // 初始化注册对话框
        this.initRegisterDialog();

        // 初始化导航栏
        this.updateNavbar();
    },

    /**
     * 初始化登录对话框
     */
    initLoginDialog() {
        const loginBtn = document.getElementById('auth-login-btn');
        const dialog = document.getElementById('login-dialog');
        const closeBtn = document.getElementById('login-dialog-close');
        const form = document.getElementById('login-form');
        const registerLink = document.getElementById('login-to-register');

        if (!loginBtn || !dialog || !form) return;

        // 打开登录对话框
        loginBtn.addEventListener('click', () => {
            this.openDialog('login');
        });

        // 关闭对话框
        closeBtn.addEventListener('click', () => {
            this.closeDialog('login');
        });

        // 点击背景关闭
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog) {
                this.closeDialog('login');
            }
        });

        // 跳转到注册
        if (registerLink) {
            registerLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.closeDialog('login');
                this.openDialog('register');
            });
        }

        // 提交登录表单
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('login-username').value.trim();
            const password = document.getElementById('login-password').value;
            const errorEl = document.getElementById('login-error');
            const submitBtn = document.getElementById('login-submit');

            // 验证输入
            if (!username || !password) {
                if (errorEl) {
                    errorEl.textContent = '请输入用户名和密码';
                    errorEl.style.display = 'block';
                }
                return;
            }

            // 显示加载状态
            submitBtn.disabled = true;
            submitBtn.textContent = '登录中...';
            if (errorEl) errorEl.style.display = 'none';

            // 执行登录
            const result = await Auth.login(username, password);

            // 恢复按钮状态
            submitBtn.disabled = false;
            submitBtn.textContent = '登录';

            if (result.success) {
                // 登录成功，关闭对话框
                this.closeDialog('login');
                // 清空表单
                form.reset();
            } else {
                // 登录失败，显示错误
                if (errorEl) {
                    errorEl.textContent = result.error || '登录失败';
                    errorEl.style.display = 'block';
                }
            }
        });
    },

    /**
     * 初始化注册对话框
     */
    initRegisterDialog() {
        const registerBtn = document.getElementById('auth-register-btn');
        const dialog = document.getElementById('register-dialog');
        const closeBtn = document.getElementById('register-dialog-close');
        const form = document.getElementById('register-form');
        const loginLink = document.getElementById('register-to-login');

        if (!registerBtn || !dialog || !form) return;

        // 打开注册对话框
        registerBtn.addEventListener('click', () => {
            this.openDialog('register');
        });

        // 关闭对话框
        closeBtn.addEventListener('click', () => {
            this.closeDialog('register');
        });

        // 点击背景关闭
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog) {
                this.closeDialog('register');
            }
        });

        // 跳转到登录
        if (loginLink) {
            loginLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.closeDialog('register');
                this.openDialog('login');
            });
        }

        // 密码输入框实时验证
        const passwordInput = document.getElementById('register-password');
        const confirmInput = document.getElementById('register-confirm-password');
        const passwordHint = document.getElementById('password-strength-hint');

        if (passwordInput && passwordHint) {
            passwordInput.addEventListener('input', () => {
                const strength = this.checkPasswordStrength(passwordInput.value);
                passwordHint.textContent = strength.message;
                passwordHint.className = 'password-hint ' + strength.className;
            });
        }

        if (confirmInput && passwordInput) {
            confirmInput.addEventListener('input', () => {
                const match = passwordInput.value === confirmInput.value;
                if (confirmInput.value && !match) {
                    confirmInput.setCustomValidity('密码不一致');
                } else {
                    confirmInput.setCustomValidity('');
                }
            });
        }

        // 提交注册表单
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('register-username').value.trim();
            const password = document.getElementById('register-password').value;
            const confirmPassword = document.getElementById('register-confirm-password').value;
            const name = document.getElementById('register-name').value.trim();
            const errorEl = document.getElementById('register-error');
            const submitBtn = document.getElementById('register-submit');

            // 验证输入
            if (!username || !password || !name) {
                if (errorEl) {
                    errorEl.textContent = '请填写所有必填字段';
                    errorEl.style.display = 'block';
                }
                return;
            }

            // 验证邮箱格式
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(username)) {
                if (errorEl) {
                    errorEl.textContent = '请输入有效的邮箱地址';
                    errorEl.style.display = 'block';
                }
                return;
            }

            // 验证密码强度
            const strength = this.checkPasswordStrength(password);
            if (!strength.valid) {
                if (errorEl) {
                    errorEl.textContent = strength.message;
                    errorEl.style.display = 'block';
                }
                return;
            }

            // 验证密码确认
            if (password !== confirmPassword) {
                if (errorEl) {
                    errorEl.textContent = '两次输入的密码不一致';
                    errorEl.style.display = 'block';
                }
                return;
            }

            // 显示加载状态
            submitBtn.disabled = true;
            submitBtn.textContent = '注册中...';
            if (errorEl) errorEl.style.display = 'none';

            // 执行注册
            const result = await Auth.register(username, password, name);

            // 恢复按钮状态
            submitBtn.disabled = false;
            submitBtn.textContent = '注册';

            if (result.success) {
                // 注册成功，关闭对话框并打开登录对话框
                this.closeDialog('register');
                // 清空表单
                form.reset();
                // 自动登录
                await Auth.login(username, password);
            } else {
                // 注册失败，显示错误
                if (errorEl) {
                    errorEl.textContent = result.error || '注册失败';
                    errorEl.style.display = 'block';
                }
            }
        });
    },

    /**
     * 检查密码强度
     * @param {string} password - 密码
     * @returns {Object} 强度信息
     */
    checkPasswordStrength(password) {
        if (!password) {
            return { valid: false, message: '', className: '' };
        }

        if (password.length < 8) {
            return {
                valid: false,
                message: '密码至少需要8位',
                className: 'weak'
            };
        }

        const hasLetter = /[a-zA-Z]/.test(password);
        const hasNumber = /[0-9]/.test(password);

        if (!hasLetter || !hasNumber) {
            return {
                valid: false,
                message: '密码必须包含字母和数字',
                className: 'weak'
            };
        }

        if (password.length >= 12) {
            return {
                valid: true,
                message: '密码强度：强',
                className: 'strong'
            };
        }

        return {
            valid: true,
            message: '密码强度：中等',
            className: 'medium'
        };
    },

    /**
     * 打开对话框
     * @param {string} type - 对话框类型 (login/register)
     */
    openDialog(type) {
        const dialog = document.getElementById(`${type}-dialog`);
        if (dialog) {
            dialog.classList.add('active');
            // 聚焦到第一个输入框
            const firstInput = dialog.querySelector('input[type="text"], input[type="password"]');
            if (firstInput) {
                firstInput.focus();
            }
        }
    },

    /**
     * 关闭对话框
     * @param {string} type - 对话框类型 (login/register)
     */
    closeDialog(type) {
        const dialog = document.getElementById(`${type}-dialog`);
        if (dialog) {
            dialog.classList.remove('active');
            // 清空表单和错误信息
            const form = document.getElementById(`${type}-form`);
            const errorEl = document.getElementById(`${type}-error`);
            if (form) form.reset();
            if (errorEl) {
                errorEl.textContent = '';
                errorEl.style.display = 'none';
            }
        }
    },

    /**
     * 检查当前用户是否为管理员
     * @returns {boolean} 是否为管理员
     */
    isAdmin() {
        const user = Auth.getUser();
        return user && user.is_admin === true;
    },

    /**
     * 更新导航栏
     */
    updateNavbar() {
        const authSection = document.getElementById('auth-section');
        if (!authSection) return;

        if (Auth.isLoggedIn()) {
            // 已登录状态
            const user = Auth.getUser();
            const adminBtn = this.isAdmin()
                ? `<button class="auth-btn auth-admin-btn" id="auth-admin-btn" title="管理">管理</button>`
                : '';

            authSection.innerHTML = `
                ${adminBtn}
                <div class="auth-user">
                    <span class="auth-user-icon">👤</span>
                    <span class="auth-user-name" title="${this.escapeHtml(user.name)}">${this.escapeHtml(user.name)}</span>
                    <button class="auth-logout-btn" id="auth-logout-btn" title="登出">登出</button>
                </div>
            `;

            // 绑定登出事件
            const logoutBtn = document.getElementById('auth-logout-btn');
            if (logoutBtn) {
                logoutBtn.addEventListener('click', () => {
                    if (confirm('确定要登出吗？')) {
                        Auth.logout();
                    }
                });
            }

            // 绑定管理按钮事件
            const adminBtnEl = document.getElementById('auth-admin-btn');
            if (adminBtnEl) {
                adminBtnEl.addEventListener('click', () => {
                    this.openAdminPanel();
                });
            }
        } else {
            // 未登录状态 - 不显示登录/注册按钮
            authSection.innerHTML = `
                <span class="auth-guest">访客模式</span>
            `;
        }
    },

    /**
     * 打开管理员面板
     */
    openAdminPanel() {
        // 检查是否有管理面板容器
        let adminContainer = document.getElementById('admin-panel-container');
        if (!adminContainer) {
            // 创建管理面板容器
            adminContainer = document.createElement('div');
            adminContainer.id = 'admin-panel-container';
            document.querySelector('.main-content')?.appendChild(adminContainer);
        }

        // 初始化管理模块
        if (window.AdminModule) {
            window.AdminModule.init(adminContainer);
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
window.AuthUI = AuthUI;
