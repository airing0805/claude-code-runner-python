/**
 * 会话信息栏组件
 * 处理会话信息显示、复制、消息计数和创建时间
 */

const SessionInfoBar = {
    // 消息计数
    messageCount: 0,

    // 创建时间
    createdTime: null,

    /**
     * 初始化会话信息栏组件
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    init(runner) {
        this.runner = runner;
        this.bindEvents();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 会话 ID 复制功能
        const sessionIdInput = document.getElementById('resume');
        if (sessionIdInput) {
            sessionIdInput.addEventListener('click', () => {
                this.copySessionId(sessionIdInput);
            });

            // 双击复制
            sessionIdInput.addEventListener('dblclick', () => {
                this.copySessionId(sessionIdInput);
            });
        }

        // 监听会话变化，更新消息计数和创建时间
        this.updateSessionInfo();
    },

    /**
     * 复制会话 ID
     * @param {HTMLElement} input - 会话 ID 输入框
     */
    async copySessionId(input) {
        const sessionId = input.value;
        if (!sessionId) {
            this.showErrorFeedback(input, '无会话ID可复制');
            return;
        }

        try {
            await navigator.clipboard.writeText(sessionId);
            // 显示复制成功提示
            this.showCopyFeedback(input);
            console.log('[会话信息栏] 会话ID已复制:', sessionId);
        } catch (err) {
            console.warn('[会话信息栏] 剪贴板复制失败，尝试降级方案:', err);
            // 降级方案：使用传统方法
            this.fallbackCopy(input);
        }
    },

    /**
     * 降级复制方法
     * @param {HTMLElement} input - 会话 ID 输入框
     */
    fallbackCopy(input) {
        const sessionId = input.value;
        if (!sessionId) {
            this.showErrorFeedback(input, '无会话ID可复制');
            return;
        }

        // 选中文本
        input.select();
        input.setSelectionRange(0, 99999);

        try {
            document.execCommand('copy');
            this.showCopyFeedback(input);
        } catch (err) {
            console.error('[会话信息栏] 降级复制失败:', err);
            this.showErrorFeedback(input, '复制失败，请手动选中复制');
        }
    },

    /**
     * 显示复制反馈
     * @param {HTMLElement} input - 输入框
     */
    showCopyFeedback(input) {
        const originalTitle = input.title;
        const originalClass = input.className;
        input.title = '已复制!';
        input.classList.add('copied');

        setTimeout(() => {
            input.title = originalTitle;
            input.className = originalClass;
        }, 1500);
    },

    /**
     * 显示错误反馈
     * @param {HTMLElement} input - 输入框
     * @param {string} message - 错误消息
     */
    showErrorFeedback(input, message) {
        const originalTitle = input.title;
        const originalClass = input.className;
        input.title = message;
        input.classList.add('copy-error');

        // 添加错误样式
        input.style.borderColor = 'var(--rose-500)';

        setTimeout(() => {
            input.title = originalTitle;
            input.className = originalClass;
            input.style.borderColor = '';
        }, 2000);
    },

    /**
     * 更新会话信息显示
     * @param {Object} sessionData - 会话数据
     */
    updateSessionInfo(sessionData = {}) {
        // 更新消息计数
        if (sessionData.messageCount !== undefined) {
            this.setMessageCount(sessionData.messageCount);
        } else {
            this.setMessageCount(0);
        }

        // 更新创建时间
        if (sessionData.createdTime !== undefined) {
            this.setCreatedTime(sessionData.createdTime);
        } else {
            this.setCreatedTime(null);
        }
    },

    /**
     * 设置消息计数
     * @param {number} count - 消息数量
     */
    setMessageCount(count) {
        this.messageCount = count;
        const countEl = document.getElementById('session-message-count');
        if (countEl) {
            const valueEl = countEl.querySelector('.info-stat-value');
            if (valueEl) {
                valueEl.textContent = count;
            }
        }
    },

    /**
     * 设置创建时间
     * @param {string|null} timestamp - ISO 时间戳
     */
    setCreatedTime(timestamp) {
        this.createdTime = timestamp;
        const timeEl = document.getElementById('session-created-time');
        if (timeEl) {
            const valueEl = timeEl.querySelector('.info-stat-value');
            if (valueEl) {
                if (timestamp) {
                    valueEl.textContent = this.formatTime(timestamp);
                } else {
                    valueEl.textContent = '-';
                }
            }
        }
    },

    /**
     * 格式化时间显示
     * @param {string} timestamp - ISO 时间戳
     * @returns {string} 格式化后的时间
     */
    formatTime(timestamp) {
        if (!timestamp) return '-';

        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;

            // 小于 1 分钟
            if (diff < 60000) {
                return '刚刚';
            }

            // 小于 1 小时
            if (diff < 3600000) {
                const minutes = Math.floor(diff / 60000);
                return `${minutes} 分钟前`;
            }

            // 小于 24 小时
            if (diff < 86400000) {
                const hours = Math.floor(diff / 3600000);
                return `${hours} 小时前`;
            }

            // 小于 7 天
            if (diff < 604800000) {
                const days = Math.floor(diff / 86400000);
                return `${days} 天前`;
            }

            // 超过 7 天，显示日期
            return date.toLocaleDateString('zh-CN', {
                month: 'short',
                day: 'numeric'
            });
        } catch (e) {
            return '-';
        }
    },

    /**
     * 增加消息计数
     */
    incrementMessageCount() {
        this.setMessageCount(this.messageCount + 1);
    },

    /**
     * 重置会话信息
     */
    reset() {
        this.setMessageCount(0);
        this.setCreatedTime(null);
    }
};

/**
 * 任务输入框组件
 * 处理输入框的聚焦/失焦状态和多行输入
 */

const TaskInput = {
    // 输入框元素
    inputElement: null,

    // 状态
    isFocused: false,

    /**
     * 初始化任务输入框组件
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    init(runner) {
        this.runner = runner;
        this.inputElement = document.getElementById('prompt');
        if (this.inputElement) {
            this.bindEvents();
        }
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 聚焦事件
        this.inputElement.addEventListener('focus', () => {
            this.onFocus();
        });

        // 失焦事件
        this.inputElement.addEventListener('blur', () => {
            this.onBlur();
        });

        // 输入事件 - 动态调整高度
        this.inputElement.addEventListener('input', () => {
            this.adjustHeight();
        });

        // 初始调整高度
        this.adjustHeight();
    },

    /**
     * 聚焦处理
     */
    onFocus() {
        this.isFocused = true;
        this.inputElement.classList.add('input-focused');
        this.inputElement.classList.remove('input-blurred');

        // 触发自定义事件
        this.inputElement.dispatchEvent(new CustomEvent('task-input:focus', {
            bubbles: true,
            detail: { isFocused: true }
        }));
    },

    /**
     * 失焦处理
     */
    onBlur() {
        this.isFocused = false;
        this.inputElement.classList.remove('input-focused');
        this.inputElement.classList.add('input-blurred');

        // 触发自定义事件
        this.inputElement.dispatchEvent(new CustomEvent('task-input:blur', {
            bubbles: true,
            detail: { isFocused: false }
        }));
    },

    /**
     * 动态调整输入框高度
     */
    adjustHeight() {
        // 重置高度以获取正确的 scrollHeight
        this.inputElement.style.height = 'auto';

        // 计算新高度
        const newHeight = Math.min(
            Math.max(this.inputElement.scrollHeight, 44), // 最小高度
            150 // 最大高度
        );

        this.inputElement.style.height = newHeight + 'px';
    },

    /**
     * 获取输入值
     * @returns {string} 输入的文本
     */
    getValue() {
        return this.inputElement ? this.inputElement.value : '';
    },

    /**
     * 设置输入值
     * @param {string} value - 要设置的文本
     */
    setValue(value) {
        if (this.inputElement) {
            this.inputElement.value = value;
            this.adjustHeight();
        }
    },

    /**
     * 清空输入
     */
    clear() {
        this.setValue('');
    },

    /**
     * 聚焦输入框
     */
    focus() {
        if (this.inputElement) {
            this.inputElement.focus();
        }
    },

    /**
     * 失焦输入框
     */
    blur() {
        if (this.inputElement) {
            this.inputElement.blur();
        }
    },

    /**
     * 检查输入是否为空
     * @returns {boolean} 是否为空
     */
    isEmpty() {
        return this.getValue().trim() === '';
    }
};

/**
 * 权限模式下拉组件
 * 处理权限模式选择和默认值设置
 */

const PermissionModeSelect = {
    // 下拉框元素
    selectElement: null,

    // 默认权限模式
    defaultMode: 'default',

    // 可用权限模式
    availableModes: [
        { value: 'default', label: 'default - 默认' },
        { value: 'acceptEdits', label: 'acceptEdits - 接受编辑' },
        { value: 'plan', label: 'plan - 计划模式' },
        { value: 'bypassPermissions', label: 'bypassPermissions - 绕过权限' }
    ],

    /**
     * 初始化权限模式下拉组件
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    init(runner) {
        this.runner = runner;
        this.selectElement = document.getElementById('permission-mode');
        if (this.selectElement) {
            this.bindEvents();
            this.renderOptions();
            this.setDefaultValue();
        }
    },

    /**
     * 渲染选项
     */
    renderOptions() {
        // 如果 HTML 中已有选项，不重新渲染
        if (this.selectElement.options.length > 0) {
            return;
        }

        // 渲染选项
        this.availableModes.forEach(mode => {
            const option = document.createElement('option');
            option.value = mode.value;
            option.textContent = mode.label;
            this.selectElement.appendChild(option);
        });
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        this.selectElement.addEventListener('change', () => {
            this.onModeChange();
        });
    },

    /**
     * 权限模式变更处理
     */
    onModeChange() {
        const selectedMode = this.getValue();
        console.log('[权限模式] 已选择:', selectedMode);

        // 触发自定义事件
        this.selectElement.dispatchEvent(new CustomEvent('permission-mode:change', {
            bubbles: true,
            detail: { mode: selectedMode }
        }));
    },

    /**
     * 设置默认值
     */
    setDefaultValue() {
        this.setValue(this.defaultMode);
    },

    /**
     * 获取当前选中的权限模式
     * @returns {string} 权限模式值
     */
    getValue() {
        return this.selectElement ? this.selectElement.value : this.defaultMode;
    },

    /**
     * 设置权限模式
     * @param {string} mode - 权限模式值
     */
    setValue(mode) {
        if (this.selectElement) {
            // 验证模式是否有效
            const validMode = this.availableModes.some(m => m.value === mode);
            if (validMode) {
                this.selectElement.value = mode;
            } else {
                console.warn('[权限模式] 无效的模式:', mode, '，使用默认值');
                this.selectElement.value = this.defaultMode;
            }
        }
    },

    /**
     * 获取权限模式描述
     * @param {string} mode - 权限模式值
     * @returns {string} 模式描述
     */
    getModeDescription(mode) {
        const modeObj = this.availableModes.find(m => m.value === mode);
        return modeObj ? modeObj.label : '未知模式';
    },

    /**
     * 重置为默认值
     */
    reset() {
        this.setValue(this.defaultMode);
    }
};

// 导出到全局命名空间
window.SessionInfoBar = SessionInfoBar;
window.TaskInput = TaskInput;
window.PermissionModeSelect = PermissionModeSelect;
