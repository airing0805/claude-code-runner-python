/**
 * 管理员模块 - 主入口
 * 整合用户管理和 API 密钥管理功能
 */

const AdminModule = {
    // 用户管理组件
    userManager: null,
    // API 密钥管理组件
    apiKeyManager: null;
    // 容器元素
    container: null,

    /**
     * 初始化模块
     * @param {HTMLElement} container - 容器元素
     */
    init(container) {
        this.container = container;

        // 创建子组件
        this.userManager = new UserManager();
        this.apiKeyManager = new APIKeyManager();

        // 初始化子组件
        const userManagerContainer = document.createElement('div');
        userManagerContainer.className = 'admin-section';
        userManagerContainer.id = 'user-manager-container';

        const apiKeyContainer = document.createElement('div');
        apiKeyContainer.className = 'admin-section';
        apiKeyContainer.id = 'api-key-container';
        apiKeyContainer.style.display = 'none';

        this.container.appendChild(userManagerContainer);
        this.container.appendChild(apiKeyContainer);

        // 初始化用户管理组件
        this.userManager.init(userManagerContainer);

        // 初始化 API 密钥管理组件
        this.apiKeyManager.init(apiKeyContainer);

        // 绑定标签切换事件
        this.bindTabEvents();
    },

    /**
     * 绑定标签切换事件
     */
    bindTabEvents() {
        const tabs = this.container.querySelectorAll('.admin-tab');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;

                // 隐藏所有内容区
                this.container.querySelectorAll('.admin-section').forEach(section => {
                    section.style.display = 'none';
                });

                // 显示选中的内容区
                const targetSection = this.container.querySelector(`#${tabName}-container`);
                if (targetSection) {
                    targetSection.style.display = 'block';
                }
            });
        });
    },

    /**
     * 显示用户管理
     */
    showUserManager() {
        // 鿷新标签状态
        this.container.querySelectorAll('.admin-tab').forEach(tab => {
            tab.classList.remove('active');
        });

        // 激活用户管理标签
        const userManagerTab = this.container.querySelector('[data-tab="users"]');
        if (userManagerTab) {
            userManagerTab.classList.add('active');
        }

        // 显示用户管理区域
        const userManagerContainer = document.getElementById('user-manager-container');
        if (userManagerContainer) {
            userManagerContainer.style.display = 'block';
        }
    },

    /**
     * 显示 API 密钥管理
     */
    showAPIKeyManager() {
        // 刷新标签状态
        this.container.querySelectorAll('.admin-tab').forEach(tab => {
            tab.classList.remove('active');
        });

        // 激活 API 密钥标签
        const apiKeyTab = this.container.querySelector('[data-tab="api-keys"]');
        if (apiKeyTab) {
            apiKeyTab.classList.add('active');
        }

        // 显示 API 密钥区域
        const apiKeyContainer = document.getElementById('api-key-container');
        if (apiKeyContainer) {
            apiKeyContainer.style.display = 'block';
        }
    }
}

// 导出到全局命名空间
window.AdminModule = AdminModule;
