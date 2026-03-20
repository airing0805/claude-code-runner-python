/**
 * 历史记录抽屉组件
 * 显示历史会话列表，支持点击继续会话
 *
 * v12.0.0.3.3 - 界面重构
 */

class HistoryDrawer {
    /**
     * 创建历史记录抽屉
     * @param {Object} options - 配置选项
     * @param {Function} [options.onSelect] - 选择会话回调
     * @param {Function} [options.onClose] - 关闭抽屉回调
     */
    constructor(options = {}) {
        this.options = {
            onSelect: null,
            onClose: null,
            ...options
        };

        // 状态
        this.isOpen = false;
        this.sessions = [];
        this.isLoading = false;
        this.currentSessionId = null;

        // DOM 元素引用
        this.overlay = null;
        this.drawer = null;
        this.closeBtn = null;
        this.sessionList = null;
        this.loadingEl = null;
        this.emptyEl = null;

        // 初始化
        this.init();
    }

    /**
     * 初始化组件
     */
    init() {
        this.cacheElements();
        this.bindEvents();
    }

    /**
     * 缓存 DOM 元素引用
     */
    cacheElements() {
        this.overlay = document.getElementById('history-drawer-overlay');
        this.drawer = document.querySelector('.history-drawer');
        this.closeBtn = document.querySelector('.history-drawer-close');
        this.sessionList = document.querySelector('.history-drawer-list');
        this.loadingEl = document.querySelector('.history-drawer-loading');
        this.emptyEl = document.querySelector('.history-drawer-empty');
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 保存事件处理函数的引用，以便后续移除
        this._boundCloseBtnClick = () => this.close();
        this._boundOverlayClick = (e) => {
            if (e.target === this.overlay) {
                this.close();
            }
        };
        this._boundEscKeyHandler = (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        };
        this._boundSessionListClick = (e) => {
            const sessionItem = e.target.closest('.history-session-item');
            if (sessionItem) {
                const sessionId = sessionItem.dataset.sessionId;
                if (sessionId) {
                    this.selectSession(sessionId);
                }
            }
        };

        // 关闭按钮点击
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', this._boundCloseBtnClick);
        }

        // 点击遮罩层关闭
        if (this.overlay) {
            this.overlay.addEventListener('click', this._boundOverlayClick);
        }

        // ESC 键关闭
        document.addEventListener('keydown', this._boundEscKeyHandler);

        // 会话列表点击（事件委托）
        if (this.sessionList) {
            this.sessionList.addEventListener('click', this._boundSessionListClick);
        }
    }

    /**
     * 销毁组件
     */
    destroy() {
        // 移除事件监听器
        if (this.closeBtn && this._boundCloseBtnClick) {
            this.closeBtn.removeEventListener('click', this._boundCloseBtnClick);
        }
        if (this.overlay && this._boundOverlayClick) {
            this.overlay.removeEventListener('click', this._boundOverlayClick);
        }
        if (this._boundEscKeyHandler) {
            document.removeEventListener('keydown', this._boundEscKeyHandler);
        }
        if (this.sessionList && this._boundSessionListClick) {
            this.sessionList.removeEventListener('click', this._boundSessionListClick);
        }

        // 清理事件处理函数引用
        this._boundCloseBtnClick = null;
        this._boundOverlayClick = null;
        this._boundEscKeyHandler = null;
        this._boundSessionListClick = null;

        // 清理 DOM 元素引用
        this.overlay = null;
        this.drawer = null;
        this.closeBtn = null;
        this.sessionList = null;
        this.loadingEl = null;
        this.emptyEl = null;
        this.sessions = [];
    }

    /**
     * 打开抽屉
     */
    async open() {
        if (this.isOpen) return;

        this.isOpen = true;

        // 显示遮罩层和抽屉
        if (this.overlay) {
            this.overlay.classList.add('show');
        }
        if (this.drawer) {
            this.drawer.classList.add('open');
        }

        // 禁止背景滚动
        document.body.style.overflow = 'hidden';

        // 加载会话列表
        await this.loadSessions();
    }

    /**
     * 关闭抽屉
     */
    close() {
        if (!this.isOpen) return;

        this.isOpen = false;

        // 隐藏遮罩层和抽屉
        if (this.overlay) {
            this.overlay.classList.remove('show');
        }
        if (this.drawer) {
            this.drawer.classList.remove('open');
        }

        // 恢复背景滚动
        document.body.style.overflow = '';

        // 触发关闭回调
        if (typeof this.options.onClose === 'function') {
            this.options.onClose();
        }
    }

    /**
     * 切换抽屉显示
     */
    async toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            await this.open();
        }
    }

    /**
     * 加载会话列表
     */
    async loadSessions() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading();

        try {
            // 获取当前工作目录（从全局 runner 实例）
            const runner = window.runner;
            const workingDir = runner?.workingDirInput?.value || runner?.state?.workspace || '';

            // 调用后端 API 获取会话列表
            const url = workingDir
                ? `/api/sessions?working_dir=${encodeURIComponent(workingDir)}&limit=50`
                : `/api/sessions?limit=50`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            // 处理响应数据
            if (result.success && Array.isArray(result.data)) {
                // 格式: { success: true, data: [...] }
                this.sessions = result.data;
            } else if (Array.isArray(result.sessions)) {
                // 格式: { sessions: [...], total: 10, ... } (后端实际返回的格式)
                this.sessions = result.sessions;
            } else if (Array.isArray(result)) {
                // 兼容直接返回数组的情况
                this.sessions = result;
            } else {
                this.sessions = [];
            }

            console.log('[HistoryDrawer] 加载会话列表成功，数量:', this.sessions.length);
            this.renderSessions();

        } catch (error) {
            console.error('[HistoryDrawer] 加载会话列表失败:', error);
            this.sessions = [];
            this.showError('加载会话列表失败');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    /**
     * 渲染会话列表
     */
    renderSessions() {
        if (!this.sessionList) return;

        if (this.sessions.length === 0) {
            this.showEmpty();
            this.sessionList.innerHTML = '';
            return;
        }

        this.hideEmpty();

        // 构建会话列表 HTML
        const html = this.sessions.map(session => this.renderSessionItem(session)).join('');
        this.sessionList.innerHTML = html;
    }

    /**
     * 渲染单个会话项
     * @param {Object} session - 会话数据
     * @returns {string} HTML 字符串
     */
    renderSessionItem(session) {
        const sessionId = this._escapeHtml(session.id || '');
        const workingDir = this._escapeHtml(session.working_dir || session.workingDir || '');
        const summary = this._escapeHtml(session.summary || session.first_message || '无摘要');
        const createdTime = this.formatTime(session.created_at || session.createdTime || session.timestamp);
        const messageCount = session.message_count || session.messageCount || 0;
        const isCurrentSession = this.currentSessionId === sessionId;

        return `
            <div
                class="history-session-item ${isCurrentSession ? 'current' : ''}"
                data-session-id="${sessionId}"
                role="button"
                tabindex="0"
                aria-label="会话: ${summary}"
            >
                <div class="session-header">
                    <span class="session-date">${createdTime}</span>
                    <span class="session-count">${messageCount} 条消息</span>
                </div>
                <div class="session-summary" title="${summary}">${summary}</div>
                <div class="session-path" title="${workingDir}">
                    <span class="path-icon">📁</span>
                    <span class="path-text">${workingDir || '未指定'}</span>
                </div>
            </div>
        `;
    }

    /**
     * 选择会话
     * @param {string} sessionId - 会话 ID
     */
    selectSession(sessionId) {
        const session = this.sessions.find(s => s.id === sessionId);
        if (!session) {
            console.warn('[HistoryDrawer] 未找到会话:', sessionId);
            return;
        }

        // 关闭抽屉
        this.close();

        // 触发选择回调
        if (typeof this.options.onSelect === 'function') {
            this.options.onSelect(session);
        }
    }

    /**
     * 设置当前会话 ID
     * @param {string} sessionId - 会话 ID
     */
    setCurrentSession(sessionId) {
        this.currentSessionId = sessionId;

        // 更新列表中的当前会话标记
        if (this.sessionList) {
            const items = this.sessionList.querySelectorAll('.history-session-item');
            items.forEach(item => {
                if (item.dataset.sessionId === sessionId) {
                    item.classList.add('current');
                } else {
                    item.classList.remove('current');
                }
            });
        }
    }

    /**
     * 显示加载状态
     */
    showLoading() {
        if (this.loadingEl) {
            this.loadingEl.style.display = 'flex';
        }
        if (this.sessionList) {
            this.sessionList.style.display = 'none';
        }
    }

    /**
     * 隐藏加载状态
     */
    hideLoading() {
        if (this.loadingEl) {
            this.loadingEl.style.display = 'none';
        }
        if (this.sessionList) {
            this.sessionList.style.display = 'block';
        }
    }

    /**
     * 显示空状态
     */
    showEmpty() {
        if (this.emptyEl) {
            this.emptyEl.style.display = 'flex';
        }
        if (this.sessionList) {
            this.sessionList.style.display = 'none';
        }
    }

    /**
     * 隐藏空状态
     */
    hideEmpty() {
        if (this.emptyEl) {
            this.emptyEl.style.display = 'none';
        }
    }

    /**
     * 显示错误信息
     * @param {string} message - 错误信息
     */
    showError(message) {
        if (this.emptyEl) {
            this.emptyEl.innerHTML = `
                <div class="empty-icon">❌</div>
                <div class="empty-text">${this._escapeHtml(message)}</div>
            `;
            this.showEmpty();
        }
    }

    /**
     * 格式化时间
     * @param {string|number} timestamp - 时间戳或时间字符串
     * @returns {string} 格式化后的时间
     */
    formatTime(timestamp) {
        if (!timestamp) return '未知时间';

        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) {
                return '未知时间';
            }

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
                return `昨天 ${this.padZero(date.getHours())}:${this.padZero(date.getMinutes())}`;
            }

            // 一周内
            if (diff < 7 * dayMs) {
                const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
                return `${days[date.getDay()]} ${this.padZero(date.getHours())}:${this.padZero(date.getMinutes())}`;
            }

            // 更早
            return `${date.getMonth() + 1}/${date.getDate()} ${this.padZero(date.getHours())}:${this.padZero(date.getMinutes())}`;

        } catch (e) {
            return '未知时间';
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
}

// 导出到全局命名空间
window.HistoryDrawer = HistoryDrawer;
