/**
 * 历史会话下拉组件
 * 用于选择工作空间下的历史会话
 *
 * v12.0.0.4 - 级联下拉选择
 */

class HistorySessionCombo {
    /**
     * 创建历史会话下拉组件
     * @param {HTMLElement} container - 容器元素
     * @param {Object} options - 配置选项
     * @param {string} [options.placeholder='选择历史会话'] - 占位符文本
     * @param {Function} [options.onChange] - 值变化回调
     * @param {Function} [options.onLoadSessions] - 加载会话列表回调
     * @param {boolean} [options.autoSelectFirst=false] - 加载后是否自动选择第一个会话
     */
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            placeholder: '选择历史会话',
            onChange: null,
            onLoadSessions: null,
            autoSelectFirst: false,
            ...options
        };

        // 当前值
        this.currentValue = null;
        this.currentSession = null;

        // 当前工作空间
        this.currentWorkspace = null;

        // 会话列表
        this.sessions = [];

        // 加载状态
        this.isLoading = false;

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
        console.log('[HistorySessionCombo] init 开始');
        this.render();
        console.log('[HistorySessionCombo] render 完成, wrapper:', this.wrapper);
        this.bindEvents();
        console.log('[HistorySessionCombo] init 完成');
    }

    /**
     * 渲染组件 HTML
     */
    render() {
        // 创建包装器
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'history-session-combo';

        // 创建输入组
        this.wrapper.innerHTML = `
            <div class="history-session-combo-input-group">
                <input
                    type="text"
                    class="history-session-combo-input"
                    placeholder="${this.options.placeholder}"
                    title="选择历史会话"
                    aria-label="历史会话"
                    autocomplete="off"
                    readonly
                    disabled
                />
                <button
                    type="button"
                    class="history-session-combo-dropdown-btn"
                    title="显示历史会话"
                    aria-label="显示历史会话列表"
                    aria-expanded="false"
                    disabled
                >
                    <span class="dropdown-icon">▼</span>
                </button>
            </div>
            <div class="history-session-combo-dropdown" role="listbox" aria-label="历史会话列表">
                <div class="history-session-combo-dropdown-content">
                    <div class="history-session-combo-empty">暂无历史会话</div>
                </div>
            </div>
        `;

        // 插入容器
        this.container.appendChild(this.wrapper);

        // 缓存 DOM 引用
        this.input = this.wrapper.querySelector('.history-session-combo-input');
        this.dropdown = this.wrapper.querySelector('.history-session-combo-dropdown');
        this.dropdownBtn = this.wrapper.querySelector('.history-session-combo-dropdown-btn');
        this.dropdownContent = this.wrapper.querySelector('.history-session-combo-dropdown-content');
    }

    /**
     * 渲染下拉选项
     * @returns {string} HTML 字符串
     */
    renderOptions() {
        if (this.isLoading) {
            return '<div class="history-session-combo-loading">加载中...</div>';
        }

        if (this.sessions.length === 0) {
            return '<div class="history-session-combo-empty">暂无历史会话</div>';
        }

        return this.sessions.map(session => {
            const sessionId = session.id || '';
            const summary = this._escapeHtml(session.summary || session.first_message || '无摘要');
            const time = this.formatRelativeTime(session.created_at || session.createdTime || session.timestamp);
            const messageCount = session.message_count || session.messageCount || 0;

            return `
                <div
                    class="history-session-combo-option"
                    data-value="${this._escapeHtml(sessionId)}"
                    data-session='${JSON.stringify(session).replace(/'/g, "&#39;")}'
                    role="option"
                    tabindex="0"
                >
                    <span class="option-summary" title="${summary}">${summary}</span>
                    <span class="option-meta">${time} · ${messageCount}条</span>
                </div>
            `;
        }).join('');
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 下拉按钮点击
        this.dropdownBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (!this.dropdownBtn.disabled) {
                this.toggleDropdown();
            }
        });

        // 输入框点击
        this.input.addEventListener('click', () => {
            if (!this.input.disabled) {
                this.toggleDropdown();
            }
        });

        // 选项点击（事件委托）
        this.dropdownContent.addEventListener('click', (e) => {
            const option = e.target.closest('.history-session-combo-option');
            if (option && !this.dropdownBtn.disabled) {
                const value = option.dataset.value;
                const sessionData = option.dataset.session;
                this.selectOption(value, sessionData);
            }
        });

        // 选项键盘导航
        this.dropdownContent.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const option = e.target.closest('.history-session-combo-option');
                if (option && !this.dropdownBtn.disabled) {
                    const value = option.dataset.value;
                    const sessionData = option.dataset.session;
                    this.selectOption(value, sessionData);
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
     * 处理键盘事件
     * @param {KeyboardEvent} e - 键盘事件
     */
    handleKeyDown(e) {
        if (this.input.disabled) return;

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

        const focused = this.dropdownContent.querySelector('.history-session-combo-option:focus');
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

        const focused = this.dropdownContent.querySelector('.history-session-combo-option:focus');
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
        return this.dropdownContent.querySelectorAll('.history-session-combo-option:not(.hidden)');
    }

    /**
     * 选择聚焦的选项
     */
    selectFocusedOption() {
        const focused = this.dropdownContent.querySelector('.history-session-combo-option:focus');
        if (focused) {
            const value = focused.dataset.value;
            const sessionData = focused.dataset.session;
            this.selectOption(value, sessionData);
        }
    }

    /**
     * 选择选项
     * @param {string} value - 选项值（会话ID）
     * @param {string} sessionDataJson - 会话数据 JSON 字符串
     */
    selectOption(value, sessionDataJson) {
        try {
            this.currentSession = sessionDataJson ? JSON.parse(sessionDataJson.replace(/&#39;/g, "'")) : null;
        } catch (e) {
            console.error('[HistorySessionCombo] 解析会话数据失败:', e);
            this.currentSession = null;
        }

        this.currentValue = value;

        // 显示简短摘要
        if (this.currentSession) {
            const summary = this.currentSession.summary || this.currentSession.first_message || '无摘要';
            // 截取前20个字符
            const shortSummary = summary.length > 20 ? summary.substring(0, 20) + '...' : summary;
            this.input.value = shortSummary;
            this.input.title = `会话ID: ${value}\n${summary}`;
        } else {
            this.input.value = value ? value.substring(0, 8) : '';
        }

        this.closeDropdown();
        this.triggerChange(value, this.currentSession);
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
    async openDropdown() {
        // 如果没有会话数据，先加载
        if (this.sessions.length === 0 && !this.isLoading && this.currentWorkspace) {
            await this.loadSessions(this.currentWorkspace);
        }

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
    }

    /**
     * 刷新选项列表
     */
    refreshOptions() {
        this.dropdownContent.innerHTML = this.renderOptions();
    }

    /**
     * 加载会话列表
     * @param {string} workingDir - 工作空间路径
     */
    async loadSessions(workingDir) {
        if (this.isLoading) return;

        this.isLoading = true;
        this.refreshOptions();

        // 触发加载回调
        if (typeof this.options.onLoadSessions === 'function') {
            try {
                const sessions = await this.options.onLoadSessions(workingDir);
                this.setSessions(sessions || []);
            } catch (error) {
                console.error('[HistorySessionCombo] 加载会话失败:', error);
                this.setSessions([]);
            }
        } else {
            // 默认尝试从 API 获取
            try {
                // 首先需要获取项目编码名称
                // 使用 projects API 获取项目列表
                const projectsResponse = await fetch('/api/projects?limit=100');
                const projectsResult = await projectsResponse.json();

                // 查找匹配当前工作目录的项目
                let projectEncodedName = null;
                if (projectsResult.projects && Array.isArray(projectsResult.projects)) {
                    // 标准化路径进行比较（更健壮的匹配）
                    const normalizedWorkingDir = this._normalizePath(workingDir);
                    console.log('[HistorySessionCombo] 标准化后的工作目录:', normalizedWorkingDir);

                    const matchingProject = projectsResult.projects.find(p => {
                        const normalizedProjectPath = this._normalizePath(p.path);
                        const matches = normalizedProjectPath === normalizedWorkingDir;
                        if (!matches) {
                            // 尝试更宽松的匹配：去掉末尾斜杠后比较
                            const trimmedWorking = normalizedWorkingDir.replace(/\/+$/, '');
                            const trimmedProject = normalizedProjectPath.replace(/\/+$/, '');
                            return trimmedWorking === trimmedProject;
                        }
                        return matches;
                    });

                    if (matchingProject) {
                        projectEncodedName = matchingProject.encoded_name;
                        console.log('[HistorySessionCombo] 找到匹配项目:', matchingProject.path, '编码名称:', projectEncodedName);
                    }
                }

                if (!projectEncodedName) {
                    console.warn('[HistorySessionCombo] 未找到匹配的项目，工作目录:', workingDir);
                    this.setSessions([]);
                    this.isLoading = false;
                    this.refreshOptions();
                    return;
                }

                // 使用项目编码名称获取会话列表
                const response = await fetch(
                    `/api/projects/${encodeURIComponent(projectEncodedName)}/sessions?limit=10&sort_by=timestamp&order=desc`
                );
                const result = await response.json();

                let sessions = [];
                // 支持多种响应格式
                if (result.sessions && Array.isArray(result.sessions)) {
                    // /api/projects/{name}/sessions 返回格式
                    sessions = result.sessions;
                } else if (Array.isArray(result)) {
                    // 直接返回数组
                    sessions = result;
                }

                console.log('[HistorySessionCombo] 加载会话列表成功，数量:', sessions.length);
                this.setSessions(sessions);
            } catch (error) {
                console.error('[HistorySessionCombo] API 请求失败:', error);
                this.setSessions([]);
            }
        }

        this.isLoading = false;
        this.refreshOptions();
    }

    /**
     * 标准化路径（用于比较）
     * @param {string} path - 原始路径
     * @returns {string} 标准化后的路径
     * @private
     */
    _normalizePath(path) {
        if (!path) return '';
        // 统一使用正斜杠，转小写，去除多余斜杠
        return path.replace(/\\/g, '/').replace(/\/+/g, '/').toLowerCase();
    }

    /**
     * 设置会话列表
     * @param {Array} sessions - 会话列表
     */
    setSessions(sessions) {
        this.sessions = sessions || [];
        this.refreshOptions();
    }

    /**
     * 清空当前值
     */
    clear() {
        this.currentValue = null;
        this.currentSession = null;
        this.input.value = '';
        this.input.title = '';
    }

    /**
     * 获取当前值
     * @returns {string|null} 当前会话ID
     */
    getValue() {
        return this.currentValue;
    }

    /**
     * 获取当前会话数据
     * @returns {Object|null} 当前会话完整数据
     */
    getSession() {
        return this.currentSession;
    }

    /**
     * 启用组件
     */
    enable() {
        if (this.input) {
            this.input.disabled = false;
        }
        if (this.dropdownBtn) {
            this.dropdownBtn.disabled = false;
        }
        if (this.wrapper) {
            this.wrapper.classList.remove('disabled');
        }
    }

    /**
     * 禁用组件
     */
    disable() {
        this.input.disabled = true;
        this.dropdownBtn.disabled = true;
        this.wrapper.classList.add('disabled');
        this.closeDropdown();
    }

    /**
     * 设置工作空间并加载历史会话
     * @param {string} workingDir - 工作空间路径
     */
    async setWorkspace(workingDir) {
        console.log('[HistorySessionCombo] setWorkspace 被调用, workingDir:', workingDir);

        // 保存当前工作空间
        this.currentWorkspace = workingDir;

        // 清空当前值
        this.clear();

        if (!workingDir) {
            console.warn('[HistorySessionCombo] workingDir 为空，禁用组件');
            // 工作空间为空，禁用组件
            this.disable();
            if (this.input) {
                this.input.placeholder = '请先选择工作空间';
            }
            this.setSessions([]);
            return;
        }

        console.log('[HistorySessionCombo] 启用组件并加载会话, workingDir:', workingDir);
        // 启用组件
        this.enable();
        if (this.input) {
            this.input.placeholder = this.options.placeholder;
        }

        // 加载该工作空间的历史会话
        await this.loadSessions(workingDir);
        console.log('[HistorySessionCombo] setWorkspace 完成');
    }

    /**
     * 监听值变化
     * @param {Function} callback - 回调函数，参数: (sessionId, sessionData)
     */
    onChange(callback) {
        this.options.onChange = callback;
    }

    /**
     * 触发变化回调
     * @param {string} value - 会话ID
     * @param {Object} session - 会话数据
     */
    triggerChange(value, session) {
        if (typeof this.options.onChange === 'function') {
            this.options.onChange(value, session);
        }
    }

    /**
     * 格式化相对时间
     * @param {string|number} timestamp - 时间戳或时间字符串
     * @returns {string} 相对时间字符串
     */
    formatRelativeTime(timestamp) {
        if (!timestamp) return '';

        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return '';

            const now = new Date();
            const diff = now - date;
            const dayMs = 24 * 60 * 60 * 1000;

            // 今天
            if (diff < dayMs && date.getDate() === now.getDate()) {
                return `今天 ${this.padZero(date.getHours())}:${this.padZero(date.getMinutes())}`;
            }

            // 昨天
            const yesterday = new Date(now);
            yesterday.setDate(yesterday.getDate() - 1);
            if (date.getDate() === yesterday.getDate()) {
                return `昨天`;
            }

            // 一周内
            if (diff < 7 * dayMs) {
                const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
                return days[date.getDay()];
            }

            // 更早
            return `${date.getMonth() + 1}/${date.getDate()}`;

        } catch (e) {
            return '';
        }
    }

    /**
     * 数字补零
     * @param {number} num - 数字
     * @returns {string} 补零后的字符串
     */
    padZero(num) {
        return num < 10 ? `0${num}` : `${num}`;
    }

    /**
     * 转义 HTML 特殊字符
     * @param {string} str - 原始字符串
     * @returns {string} 转义后的字符串
     */
    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
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
    }
}

// 导出到全局命名空间
window.HistorySessionCombo = HistorySessionCombo;
