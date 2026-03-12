/**
 * 日志查看器模块 (v7.1.0)
 * 管理任务日志的展示、搜索和实时更新
 */

const LogViewer = {
    // 状态
    state: {
        taskId: null,
        activeTab: 'normal',  // 'normal' | 'error'
        logs: [],
        page: 1,
        total: 0,
        pages: 0,
        limit: 100,
        loading: false,
        searchKeyword: '',
        isSearchMode: false,
        autoScroll: true,
    },

    // 虚拟列表实例
    virtualList: null,

    // SSE 连接
    eventSource: null,
    retryCount: 0,
    maxRetries: 5,

    /**
     * 初始化日志查看器
     * @param {string} taskId - 任务 ID
     */
    init(taskId) {
        this.state.taskId = taskId;
        this.state.activeTab = 'normal';
        this.state.page = 1;
        this.state.logs = [];
        this.state.searchKeyword = '';
        this.state.isSearchMode = false;
        this.state.autoScroll = true;

        // 初始化虚拟列表
        this.initVirtualList();

        this.bindEvents();
        this.loadLogs();
    },

    /**
     * 初始化虚拟列表
     */
    initVirtualList() {
        const container = document.getElementById('detail-task-logs');
        if (!container) return;

        // 如果已有实例，先销毁
        if (this.virtualList) {
            this.virtualList.destroy();
            this.virtualList = null;
        }

        // 创建虚拟列表实例
        this.virtualList = VirtualList.create({
            container: container,
            itemHeight: 24,  // 日志行高
            overscan: 10,
            renderItem: (log, index) => {
                const time = this.formatTime(log.timestamp);
                const lineNumber = log.line_number || (index + 1);
                const content = this.state.isSearchMode
                    ? this.highlightMatches(log.content, this.state.searchKeyword)
                    : this.escapeHtml(log.content);

                const div = document.createElement('div');
                div.className = `log-entry ${log.type}`;
                div.dataset.index = index;
                div.innerHTML = `
                    <span class="log-line-number">${lineNumber}</span>
                    <span class="log-time">${time}</span>
                    <span class="log-content">${content}</span>
                `;
                return div;
            },
            onLoadMore: () => {
                // 分页模式下，加载更多
                if (this.state.page < this.state.pages) {
                    this.state.page++;
                    this.loadLogs(true);
                }
            },
            loadMoreThreshold: 200,
        });
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 标签页切换 (任务详情对话框内的标签页)
        const tabsContainer = document.querySelector('.log-tabs');
        if (tabsContainer) {
            tabsContainer.addEventListener('click', (e) => {
                const tab = e.target.closest('.log-tab-btn');
                if (tab && tab.dataset.logTab) {
                    this.switchTab(tab.dataset.logTab);
                }
                // 实时日志按钮
                if (e.target.closest('#btn-realtime-logs')) {
                    this.toggleRealtime();
                }
            });
        }

        // 搜索按钮
        const searchBtn = document.getElementById('log-search-btn');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.performSearch());
        }

        // 搜索输入框回车
        const searchInput = document.getElementById('log-search-input');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSearch();
                }
            });
        }

        // 关闭对话框时断开 SSE
        const closeBtn = document.getElementById('close-task-detail-dialog');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.disconnectSSE());
        }

        // 关闭详情按钮
        const closeDetailBtn = document.getElementById('close-detail-btn');
        if (closeDetailBtn) {
            closeDetailBtn.addEventListener('click', () => this.disconnectSSE());
        }
    },

    /**
     * 切换标签页
     * @param {string} type - 日志类型 'normal' | 'error'
     */
    switchTab(type) {
        if (this.state.activeTab === type) return;

        // 断开实时日志
        this.disconnectSSE();

        this.state.activeTab = type;
        this.state.page = 1;
        this.state.searchKeyword = '';
        this.state.isSearchMode = false;
        this.state.logs = [];

        // 更新 UI
        this.updateTabUI();

        // 加载日志
        this.loadLogs();
    },

    /**
     * 切换实时日志
     */
    toggleRealtime() {
        const btn = document.getElementById('btn-realtime-logs');
        if (!btn) return;

        if (btn.classList.contains('active')) {
            // 关闭实时日志
            this.disconnectSSE();
            btn.classList.remove('active');
        } else {
            // 开启实时日志
            btn.classList.add('active');
            this.connectSSE(this.state.taskId, 'all');
        }
    },

    /**
     * 更新标签页 UI
     */
    updateTabUI() {
        const tabs = document.querySelectorAll('.log-tab-btn');
        tabs.forEach(tab => {
            if (tab.dataset.logTab === this.state.activeTab) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // 更新标签页计数器
        this.updateTabCounts();

        // 清除搜索
        const searchInput = document.getElementById('log-search-input');
        if (searchInput) {
            searchInput.value = '';
        }
    },

    /**
     * 更新标签页计数器
     */
    async updateTabCounts() {
        if (!this.state.taskId) return;

        try {
            const response = await fetch(`/api/scheduler/tasks/${this.state.taskId}/logs/count`);
            const result = await response.json();

            if (result.success) {
                const normalCount = document.getElementById('log-normal-count');
                const errorCount = document.getElementById('log-error-count');

                if (normalCount) {
                    normalCount.textContent = `(${result.data.stdout || 0})`;
                }
                if (errorCount) {
                    errorCount.textContent = `(${result.data.stderr || 0})`;
                }
            }
        } catch (error) {
            console.error('获取日志数量失败:', error);
        }
    },

    /**
     * 加载日志
     */
    /**
     * 加载日志
     * @param {boolean} append - 是否追加模式
     */
    async loadLogs(append = false) {
        if (!this.state.taskId || this.state.loading) return;

        this.state.loading = true;
        this.updateLoadingUI(true);

        try {
            const logType = this.state.activeTab === 'normal' ? 'stdout' : 'stderr';
            const url = `/api/scheduler/tasks/${this.state.taskId}/logs/${logType}?page=${this.state.page}&limit=${this.state.limit}`;

            const response = await fetch(url);
            const result = await response.json();

            if (result.success) {
                if (append) {
                    // 追加模式：合并日志
                    this.state.logs = [...this.state.logs, ...(result.data.items || [])];
                } else {
                    this.state.logs = result.data.items || [];
                }
                this.state.total = result.data.total || 0;
                this.state.pages = result.data.pages || 0;

                this.renderLogs(append);
                this.updatePaginationUI();
            } else {
                Utils.showNotification('加载日志失败: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('加载日志失败:', error);
            Utils.showNotification('加载日志失败: ' + error.message, 'error');
        } finally {
            this.state.loading = false;
            this.updateLoadingUI(false);
        }
    },

    /**
     * 渲染日志列表
     * @param {boolean} append - 是否追加模式（加载更多）
     */
    renderLogs(append = false) {
        const container = document.getElementById('detail-task-logs');
        if (!container) return;

        // 如果没有虚拟列表实例，创建一个
        if (!this.virtualList) {
            this.initVirtualList();
        }

        if (this.state.logs.length === 0 && !append) {
            // 空状态
            if (this.virtualList) {
                this.virtualList.clear();
            }
            container.innerHTML = '<div class="empty-text">暂无日志</div>';
            return;
        }

        // 使用虚拟列表渲染
        if (append) {
            // 追加模式（加载更多）
            this.virtualList.appendItems(this.state.logs);
        } else {
            // 替换模式
            this.virtualList.setItems(this.state.logs);
        }

        // 自动滚动到底部
        if (this.state.autoScroll) {
            this.scrollToBottom();
        }
    },

    /**
     * 格式化时间
     * @param {string} timestamp - ISO 时间戳
     * @returns {string} 格式化的时间
     */
    formatTime(timestamp) {
        if (!timestamp) return '--:--:--';
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('zh-CN', { hour12: false });
        } catch {
            return '--:--:--';
        }
    },

    /**
     * 高亮匹配文本
     * @param {string} content - 原始内容
     * @param {string} keyword - 关键字
     * @returns {string} 高亮后的 HTML
     */
    highlightMatches(content, keyword) {
        if (!keyword || !content) return this.escapeHtml(content);

        const escapedContent = this.escapeHtml(content);
        const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedKeyword})`, 'gi');

        return escapedContent.replace(regex, '<mark>$1</mark>');
    },

    /**
     * HTML 转义
     * @param {string} text - 原始文本
     * @returns {string} 转义后的文本
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 执行搜索
     */
    async performSearch() {
        const searchInput = document.getElementById('log-search-input');
        const keyword = searchInput?.value.trim();

        if (!keyword) {
            this.clearSearch();
            return;
        }

        this.state.searchKeyword = keyword;
        this.state.isSearchMode = true;
        this.state.page = 1;

        this.state.loading = true;
        this.updateLoadingUI(true);

        try {
            const logType = this.state.activeTab === 'normal' ? 'stdout' : 'stderr';
            const url = `/api/scheduler/tasks/${this.state.taskId}/logs/search?keyword=${encodeURIComponent(keyword)}&log_type=${logType}&page=${this.state.page}&limit=${this.state.limit}`;

            const response = await fetch(url);
            const result = await response.json();

            if (result.success) {
                this.state.logs = result.data.items || [];
                this.state.total = result.data.total || 0;
                this.state.pages = result.data.pages || 0;

                this.renderLogs();
                this.updatePaginationUI(true);
            } else {
                Utils.showNotification('搜索失败: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('搜索失败:', error);
            Utils.showNotification('搜索失败: ' + error.message, 'error');
        } finally {
            this.state.loading = false;
            this.updateLoadingUI(false);
        }
    },

    /**
     * 清除搜索
     */
    clearSearch() {
        this.state.searchKeyword = '';
        this.state.isSearchMode = false;

        const searchInput = document.getElementById('log-search-input');
        if (searchInput) {
            searchInput.value = '';
        }

        this.loadLogs();
    },

    /**
     * 跳转到指定页
     * @param {number} page - 页码
     */
    goToPage(page) {
        if (page < 1 || page > this.state.pages) return;

        this.state.page = page;

        if (this.state.isSearchMode) {
            this.performSearch();
        } else {
            this.loadLogs();
        }
    },

    /**
     * 更新分页 UI
     * @param {boolean} isSearch - 是否在搜索模式
     */
    updatePaginationUI(isSearch = false) {
        const pageInfo = document.getElementById('log-page-info');
        const prevBtn = document.getElementById('log-prev-page');
        const nextBtn = document.getElementById('log-next-page');

        if (pageInfo) {
            pageInfo.textContent = `${this.state.page} / ${this.state.pages || 1}`;
        }

        if (prevBtn) {
            prevBtn.disabled = this.state.page <= 1;
        }

        if (nextBtn) {
            nextBtn.disabled = this.state.page >= this.state.pages;
        }

        // 显示搜索结果数
        if (isSearch) {
            const searchInfo = document.getElementById('log-search-info');
            if (searchInfo) {
                searchInfo.textContent = `找到 ${this.state.total} 个匹配`;
                searchInfo.style.display = 'block';
            }
        } else {
            const searchInfo = document.getElementById('log-search-info');
            if (searchInfo) {
                searchInfo.style.display = 'none';
            }
        }
    },

    /**
     * 更新加载状态 UI
     * @param {boolean} loading - 是否加载中
     */
    updateLoadingUI(loading) {
        const container = document.getElementById('log-list-container');
        if (!container) return;

        if (loading) {
            if (!container.querySelector('.loading-indicator')) {
                container.innerHTML = '<div class="loading-indicator">加载中...</div>';
            }
        }
    },

    /**
     * 连接 SSE 获取实时日志
     * @param {string} taskId - 任务 ID
     * @param {string} logType - 日志类型过滤
     */
    connectSSE(taskId, logType = 'all') {
        this.disconnectSSE();

        const url = `/api/scheduler/tasks/${taskId}/logs/stream?log_type=${logType}`;
        this.eventSource = new EventSource(url);

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.message === '已连接到日志流') {
                    console.log('SSE 连接成功');
                    this.updateConnectionStatus('connected');
                }
            } catch (e) {
                // 忽略解析错误
            }
        };

        this.eventSource.addEventListener('log', (event) => {
            try {
                const logEntry = JSON.parse(event.data);
                this.handleNewLog(logEntry);
            } catch (e) {
                console.error('解析日志失败:', e);
            }
        });

        this.eventSource.addEventListener('complete', (event) => {
            try {
                const data = JSON.parse(event.data);
                Utils.showNotification(data.message || '任务已完成', 'info');
            } catch (e) {
                // 忽略
            }
        });

        this.eventSource.addEventListener('error', (event) => {
            try {
                const data = JSON.parse(event.data);
                Utils.showNotification(data.message || '任务执行失败', 'error');
            } catch (e) {
                // 忽略
            }
            this.updateConnectionStatus('disconnected');
        });

        this.eventSource.addEventListener('close', (event) => {
            this.updateConnectionStatus('disconnected');
        });

        this.eventSource.onerror = () => {
            this.handleSSEError();
        };

        this.updateConnectionStatus('connecting');
    },

    /**
     * 处理新日志
     * @param {Object} logEntry - 日志条目
     */
    handleNewLog(logEntry) {
        const logType = this.state.activeTab === 'normal' ? 'stdout' : 'stderr';

        // 根据当前标签页过滤
        if (logEntry.type !== logType) return;

        // 添加到列表
        this.state.logs.push(logEntry);
        this.state.total++;

        // 追加到虚拟列表
        if (this.virtualList) {
            this.virtualList.setItems([logEntry], true);
        } else {
            this.renderLogs();
        }

        // 自动滚动
        if (this.state.autoScroll !== false) {
            this.scrollToBottom();
        }
    },

    /**
     * 处理 SSE 错误
     */
    handleSSEError() {
        if (this.retryCount < this.maxRetries) {
            this.retryCount++;
            const delay = Math.min(3000 * this.retryCount, 15000);
            this.updateConnectionStatus('reconnecting', this.retryCount);

            setTimeout(() => {
                if (this.state.taskId) {
                    const logType = this.state.activeTab === 'normal' ? 'stdout' : 'stderr';
                    this.connectSSE(this.state.taskId, logType);
                }
            }, delay);
        } else {
            this.updateConnectionStatus('disconnected');
            Utils.showNotification('实时日志连接失败', 'error');
        }
    },

    /**
     * 断开 SSE 连接
     */
    disconnectSSE() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.retryCount = 0;
        this.updateConnectionStatus('disconnected');
    },

    /**
     * 更新连接状态
     * @param {string} status - 状态 'connected' | 'disconnected' | 'connecting' | 'reconnecting'
     * @param {number} retryCount - 重试次数
     */
    updateConnectionStatus(status, retryCount = 0) {
        const statusEl = document.getElementById('log-connection-status');
        if (!statusEl) return;

        const statusMap = {
            connected: { text: '已连接', class: 'connected' },
            disconnected: { text: '已断开', class: 'disconnected' },
            connecting: { text: '连接中...', class: 'connecting' },
            reconnecting: { text: `重连中 (${retryCount})...`, class: 'connecting' },
        };

        const info = statusMap[status] || statusMap.disconnected;
        statusEl.textContent = info.text;
        statusEl.className = `connection-status ${info.class}`;
    },

    /**
     * 滚动到底部
     */
    scrollToBottom() {
        const container = document.getElementById('detail-task-logs');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    },

    /**
     * 销毁日志查看器
     */
    destroy() {
        // 销毁虚拟列表
        if (this.virtualList) {
            this.virtualList.destroy();
            this.virtualList = null;
        }

        this.disconnectSSE();
        this.state.taskId = null;
        this.state.logs = [];
    },
};

// 导出到全局
window.LogViewer = LogViewer;
