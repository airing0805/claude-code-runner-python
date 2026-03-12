/**
 * 工作空间组合控件
 * 支持下拉选择历史工作空间和手动输入新路径
 *
 * v12.0.0.3.2 - 界面重构
 */

class WorkspaceCombo {
    /**
     * 创建工作空间组合控件
     * @param {HTMLElement} container - 容器元素
     * @param {Object} options - 配置选项
     * @param {string} [options.value=''] - 初始值
     * @param {string[]} [options.history=[]] - 历史工作空间列表
     * @param {string} [options.placeholder='选择或输入工作空间路径'] - 占位符文本
     * @param {Function} [options.onChange] - 值变化回调
     * @param {Function} [options.onValidate] - 路径验证回调
     */
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            value: '',
            history: [],
            placeholder: '选择或输入工作空间路径',
            onChange: null,
            onValidate: null,
            ...options
        };

        // 当前值
        this.currentValue = this.options.value;

        // 历史记录（去重）
        this.history = this._deduplicateHistory(this.options.history);

        // 是否展开下拉
        this.isOpen = false;

        // DOM 元素引用
        this.wrapper = null;
        this.input = null;
        this.dropdown = null;
        this.dropdownBtn = null;

        // 初始化
        this.init();
    }

    /**
     * 初始化组件
     */
    init() {
        this.render();
        this.bindEvents();
        this.setValue(this.options.value);
    }

    /**
     * 渲染组件 HTML
     */
    render() {
        // 创建包装器
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'workspace-combo';

        // 创建输入组
        this.wrapper.innerHTML = `
            <div class="workspace-combo-input-group">
                <input
                    type="text"
                    class="workspace-combo-input"
                    placeholder="${this.options.placeholder}"
                    title="选择或输入工作空间路径"
                    aria-label="工作空间路径"
                    autocomplete="off"
                />
                <button
                    type="button"
                    class="workspace-combo-dropdown-btn"
                    title="显示历史工作空间"
                    aria-label="显示历史工作空间列表"
                    aria-expanded="false"
                >
                    <span class="dropdown-icon">▼</span>
                </button>
            </div>
            <div class="workspace-combo-dropdown" role="listbox" aria-label="工作空间历史列表">
                <div class="workspace-combo-dropdown-content">
                    ${this.renderOptions()}
                </div>
            </div>
            <div class="workspace-combo-validation" aria-live="polite"></div>
        `;

        // 插入容器
        this.container.appendChild(this.wrapper);

        // 缓存 DOM 引用
        this.input = this.wrapper.querySelector('.workspace-combo-input');
        this.dropdown = this.wrapper.querySelector('.workspace-combo-dropdown');
        this.dropdownBtn = this.wrapper.querySelector('.workspace-combo-dropdown-btn');
        this.dropdownContent = this.wrapper.querySelector('.workspace-combo-dropdown-content');
        this.validationEl = this.wrapper.querySelector('.workspace-combo-validation');
    }

    /**
     * 渲染下拉选项
     * @returns {string} HTML 字符串
     */
    renderOptions() {
        if (this.history.length === 0) {
            return '<div class="workspace-combo-empty">暂无历史记录</div>';
        }

        return this.history.map(path => `
            <div
                class="workspace-combo-option"
                data-value="${this._escapeHtml(path)}"
                role="option"
                tabindex="0"
            >
                <span class="option-icon">📁</span>
                <span class="option-text" title="${this._escapeHtml(path)}">${this._escapeHtml(path)}</span>
            </div>
        `).join('');
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 输入框事件
        this.input.addEventListener('input', (e) => {
            this.handleInputChange(e.target.value);
        });

        this.input.addEventListener('focus', () => {
            this.wrapper.classList.add('focused');
        });

        this.input.addEventListener('blur', () => {
            this.wrapper.classList.remove('focused');
            // 延迟关闭下拉，以便点击选项
            setTimeout(() => {
                if (!this.wrapper.contains(document.activeElement)) {
                    this.closeDropdown();
                }
            }, 150);

            // 失去焦点时验证路径
            this.validatePath(this.input.value);
        });

        // 下拉按钮点击
        this.dropdownBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleDropdown();
        });

        // 选项点击（事件委托）
        this.dropdownContent.addEventListener('click', (e) => {
            const option = e.target.closest('.workspace-combo-option');
            if (option) {
                const value = option.dataset.value;
                this.selectOption(value);
            }
        });

        // 选项键盘导航
        this.dropdownContent.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const option = e.target.closest('.workspace-combo-option');
                if (option) {
                    this.selectOption(option.dataset.value);
                }
            }
        });

        // 点击外部关闭下拉
        document.addEventListener('click', (e) => {
            if (!this.wrapper.contains(e.target)) {
                this.closeDropdown();
            }
        });

        // 键盘导航
        this.input.addEventListener('keydown', (e) => {
            this.handleKeyDown(e);
        });
    }

    /**
     * 处理输入变化
     * @param {string} value - 输入值
     */
    handleInputChange(value) {
        this.currentValue = value;
        this.triggerChange(value);

        // 高亮匹配的选项
        this.highlightMatchingOptions(value);
    }

    /**
     * 高亮匹配的选项
     * @param {string} value - 当前输入值
     */
    highlightMatchingOptions(value) {
        const options = this.dropdownContent.querySelectorAll('.workspace-combo-option');
        const lowerValue = value.toLowerCase();

        options.forEach(option => {
            const optionValue = option.dataset.value.toLowerCase();
            if (optionValue.includes(lowerValue)) {
                option.classList.remove('hidden');
            } else {
                option.classList.add('hidden');
            }
        });
    }

    /**
     * 处理键盘事件
     * @param {KeyboardEvent} e - 键盘事件
     */
    handleKeyDown(e) {
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (!this.isOpen) {
                    this.openDropdown();
                } else {
                    this.focusNextOption();
                }
                break;

            case 'ArrowUp':
                e.preventDefault();
                if (this.isOpen) {
                    this.focusPrevOption();
                }
                break;

            case 'Enter':
                if (this.isOpen) {
                    e.preventDefault();
                    this.selectFocusedOption();
                }
                break;

            case 'Escape':
                this.closeDropdown();
                break;
        }
    }

    /**
     * 聚焦下一个选项
     */
    focusNextOption() {
        const visibleOptions = this.getVisibleOptions();
        if (visibleOptions.length === 0) return;

        const focused = this.dropdownContent.querySelector('.workspace-combo-option:focus');
        if (!focused) {
            visibleOptions[0].focus();
        } else {
            const index = Array.from(visibleOptions).indexOf(focused);
            const nextIndex = (index + 1) % visibleOptions.length;
            visibleOptions[nextIndex].focus();
        }
    }

    /**
     * 聚焦上一个选项
     */
    focusPrevOption() {
        const visibleOptions = this.getVisibleOptions();
        if (visibleOptions.length === 0) return;

        const focused = this.dropdownContent.querySelector('.workspace-combo-option:focus');
        if (!focused) {
            visibleOptions[visibleOptions.length - 1].focus();
        } else {
            const index = Array.from(visibleOptions).indexOf(focused);
            const prevIndex = (index - 1 + visibleOptions.length) % visibleOptions.length;
            visibleOptions[prevIndex].focus();
        }
    }

    /**
     * 获取可见的选项
     * @returns {NodeList} 可见的选项元素
     */
    getVisibleOptions() {
        return this.dropdownContent.querySelectorAll('.workspace-combo-option:not(.hidden)');
    }

    /**
     * 选择聚焦的选项
     */
    selectFocusedOption() {
        const focused = this.dropdownContent.querySelector('.workspace-combo-option:focus');
        if (focused) {
            this.selectOption(focused.dataset.value);
        }
    }

    /**
     * 选择选项
     * @param {string} value - 选项值
     */
    selectOption(value) {
        this.setValue(value);
        this.closeDropdown();
        this.validatePath(value);
    }

    /**
     * 切换下拉显示
     */
    toggleDropdown() {
        if (this.isOpen) {
            this.closeDropdown();
        } else {
            this.openDropdown();
        }
    }

    /**
     * 打开下拉
     */
    openDropdown() {
        this.isOpen = true;
        this.dropdown.classList.add('open');
        this.dropdownBtn.setAttribute('aria-expanded', 'true');
        this.dropdownBtn.querySelector('.dropdown-icon').textContent = '▲';

        // 重新渲染选项
        this.refreshOptions();
    }

    /**
     * 关闭下拉
     */
    closeDropdown() {
        this.isOpen = false;
        this.dropdown.classList.remove('open');
        this.dropdownBtn.setAttribute('aria-expanded', 'false');
        this.dropdownBtn.querySelector('.dropdown-icon').textContent = '▼';

        // 显示所有选项（重置过滤）
        const options = this.dropdownContent.querySelectorAll('.workspace-combo-option');
        options.forEach(option => option.classList.remove('hidden'));
    }

    /**
     * 刷新选项列表
     */
    refreshOptions() {
        this.dropdownContent.innerHTML = this.renderOptions();
    }

    /**
     * 设置值
     * @param {string} path - 工作空间路径
     */
    setValue(path) {
        this.currentValue = path || '';
        this.input.value = this.currentValue;
        this.triggerChange(this.currentValue);
    }

    /**
     * 获取当前值
     * @returns {string} 当前工作空间路径
     */
    getValue() {
        return this.currentValue;
    }

    /**
     * 设置历史记录
     * @param {string[]} history - 历史工作空间列表
     */
    setHistory(history) {
        this.history = this._deduplicateHistory(history);
        this.refreshOptions();
    }

    /**
     * 获取历史记录
     * @returns {string[]} 历史工作空间列表
     */
    getHistory() {
        return [...this.history];
    }

    /**
     * 添加到历史记录
     * @param {string} path - 工作空间路径
     */
    addToHistory(path) {
        if (!path) return;

        // 移除重复项
        const index = this.history.indexOf(path);
        if (index > -1) {
            this.history.splice(index, 1);
        }

        // 添加到开头
        this.history.unshift(path);

        // 限制最多 20 条
        if (this.history.length > 20) {
            this.history = this.history.slice(0, 20);
        }

        this.refreshOptions();
    }

    /**
     * 清空当前值
     */
    clear() {
        this.setValue('');
        this.validationEl.textContent = '';
        this.validationEl.className = 'workspace-combo-validation';
    }

    /**
     * 监听值变化
     * @param {Function} callback - 回调函数
     */
    onChange(callback) {
        this.options.onChange = callback;
    }

    /**
     * 监听验证结果
     * @param {Function} callback - 回调函数
     */
    onValidate(callback) {
        this.options.onValidate = callback;
    }

    /**
     * 触发变化回调
     * @param {string} value - 新值
     */
    triggerChange(value) {
        if (typeof this.options.onChange === 'function') {
            this.options.onChange(value);
        }
    }

    /**
     * 验证路径
     * @param {string} path - 工作空间路径
     * @returns {Object} 验证结果 {valid: boolean, error?: string}
     */
    validatePath(path) {
        // 空路径视为有效（新会话）
        if (!path) {
            this.showValidation('', '');
            return { valid: true };
        }

        // 检查路径格式
        const result = this._validatePathFormat(path);

        // 显示验证结果
        this.showValidation(
            result.valid ? '' : result.error,
            result.valid ? '' : 'error'
        );

        // 触发验证回调
        if (typeof this.options.onValidate === 'function') {
            this.options.onValidate(result);
        }

        return result;
    }

    /**
     * 验证路径格式
     * @param {string} path - 路径
     * @returns {Object} 验证结果
     */
    _validatePathFormat(path) {
        if (!path || typeof path !== 'string') {
            return { valid: false, error: '路径格式不正确' };
        }

        // 防止路径遍历攻击
        if (path.includes('..') || path.includes('~')) {
            return { valid: false, error: '路径包含非法字符' };
        }

        // 验证路径格式（支持 Unix 和 Windows）
        // Unix: 以 / 开头
        // Windows: 以盘符开头（如 C:\）
        const isUnixPath = path.startsWith('/');
        const isWindowsPath = /^[A-Za-z]:[\\\/]/.test(path);

        if (!isUnixPath && !isWindowsPath) {
            return { valid: false, error: '路径格式不正确（需要绝对路径）' };
        }

        return { valid: true };
    }

    /**
     * 显示验证结果
     * @param {string} message - 消息
     * @param {string} type - 类型 ('', 'error', 'success')
     */
    showValidation(message, type) {
        this.validationEl.textContent = message;
        this.validationEl.className = `workspace-combo-validation ${type}`;

        // 更新输入框状态
        if (type === 'error') {
            this.input.classList.add('invalid');
        } else {
            this.input.classList.remove('invalid');
        }
    }

    /**
     * 禁用控件
     * @param {boolean} disabled - 是否禁用
     */
    setDisabled(disabled) {
        this.input.disabled = disabled;
        this.dropdownBtn.disabled = disabled;

        if (disabled) {
            this.wrapper.classList.add('disabled');
        } else {
            this.wrapper.classList.remove('disabled');
        }
    }

    /**
     * 销毁组件
     */
    destroy() {
        if (this.wrapper && this.wrapper.parentNode) {
            this.wrapper.parentNode.removeChild(this.wrapper);
        }

        this.wrapper = null;
        this.input = null;
        this.dropdown = null;
        this.dropdownBtn = null;
        this.dropdownContent = null;
        this.validationEl = null;
    }

    /**
     * 历史记录去重
     * @param {string[]} history - 历史记录
     * @returns {string[]} 去重后的历史记录
     */
    _deduplicateHistory(history) {
        const seen = new Set();
        return history.filter(item => {
            if (seen.has(item)) {
                return false;
            }
            seen.add(item);
            return true;
        });
    }

    /**
     * 转义 HTML 特殊字符
     * @param {string} str - 原始字符串
     * @returns {string} 转义后的字符串
     */
    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

// 导出到全局命名空间
window.WorkspaceCombo = WorkspaceCombo;
