/**
 * 调度器状态管理模块
 * 模块拆分 - v7.0.10
 * 职责: 管理任务调度器的状态
 */

const SchedulerState = {
    // 调度器运行状态
    scheduler: {
        isRunning: false,
        lastCheckTime: null,
    },

    // 统计数据
    stats: {
        queueCount: 0,
        scheduledCount: 0,
        runningCount: 0,
    },

    // 当前活跃的标签页
    activeTab: 'queue',

    // 各类任务列表
    queue: [],
    scheduled: [],
    running: [],
    completed: { items: [], page: 1, total: 0, limit: 20 },
    failed: { items: [], page: 1, total: 0, limit: 20 },

    // UI 状态
    loading: false,
    sortBy: 'created_at',     // 排序字段
    sortOrder: 'desc',        // 排序方向
    filterText: '',           // 筛选文本
    filterWorkspace: '',      // 筛选工作空间
    filterStatus: '',         // 筛选状态（定时任务用）
    selectedTaskIds: [],      // 选中的任务ID列表
    lastRefreshTime: null,   // 上次刷新时间
    editingScheduledId: null, // 编辑中的定时任务 ID

    /**
     * 重置状态
     */
    reset() {
        this.scheduler = {
            isRunning: false,
            lastCheckTime: null,
        };
        this.stats = {
            queueCount: 0,
            scheduledCount: 0,
            runningCount: 0,
        };
        this.activeTab = 'queue';
        this.queue = [];
        this.scheduled = [];
        this.running = [];
        this.completed = { items: [], page: 1, total: 0, limit: 20 };
        this.failed = { items: [], page: 1, total: 0, limit: 20 };
        this.loading = false;
        this.sortBy = 'created_at';
        this.sortOrder = 'desc';
        this.filterText = '';
        this.filterWorkspace = '';
        this.filterStatus = '';
        this.selectedTaskIds = [];
        this.lastRefreshTime = null;
        this.editingScheduledId = null;
    },

    /**
     * 更新调度器状态
     */
    setSchedulerStatus(isRunning, lastCheckTime) {
        this.scheduler.isRunning = isRunning;
        this.scheduler.lastCheckTime = lastCheckTime;
    },

    /**
     * 更新统计信息
     */
    setStats(queueCount, scheduledCount, runningCount) {
        this.stats.queueCount = queueCount;
        this.stats.scheduledCount = scheduledCount;
        this.stats.runningCount = runningCount;
    },

    /**
     * 切换标签页
     */
    setActiveTab(tabName) {
        this.activeTab = tabName;
    },

    /**
     * 设置队列列表
     */
    setQueue(items) {
        this.queue = items;
        this.stats.queueCount = items.length;
    },

    /**
     * 设置定时任务列表
     */
    setScheduled(items) {
        this.scheduled = items;
        this.stats.scheduledCount = items.length;
    },

    /**
     * 设置运行中任务列表
     */
    setRunning(items) {
        this.running = items;
        this.stats.runningCount = items.length;
    },

    /**
     * 设置已完成任务列表
     */
    setCompleted(data) {
        this.completed = {
            items: Array.isArray(data) ? data : (data.items || []),
            page: data.page || 1,
            total: data.total || 0,
            limit: data.limit || 20,
        };
    },

    /**
     * 设置失败任务列表
     */
    setFailed(data) {
        this.failed = {
            items: Array.isArray(data) ? data : (data.items || []),
            page: data.page || 1,
            total: data.total || 0,
            limit: data.limit || 20,
        };
    },

    /**
     * 设置加载状态
     */
    setLoading(loading) {
        this.loading = loading;
    },

    /**
     * 设置排序参数
     */
    setSorting(sortBy, sortOrder) {
        this.sortBy = sortBy;
        this.sortOrder = sortOrder;
    },

    /**
     * 设置筛选参数
     */
    setFilter(filterText, filterWorkspace, filterStatus) {
        this.filterText = filterText || '';
        this.filterWorkspace = filterWorkspace || '';
        this.filterStatus = filterStatus || '';
    },

    /**
     * 设置选中的任务ID
     */
    setSelectedTaskIds(ids) {
        this.selectedTaskIds = Array.isArray(ids) ? ids : [ids];
    },

    /**
     * 获取当前活跃标签页
     */
    getActiveTab() {
        return this.activeTab;
    },

    /**
     * 获取队列列表
     */
    getQueue() {
        return this.queue;
    },

    /**
     * 获取定时任务列表
     */
    getScheduled() {
        return this.scheduled;
    },

    /**
     * 获取运行中任务列表
     */
    getRunning() {
        return this.running;
    },

    /**
     * 获取已完成任务列表
     */
    getCompleted() {
        return this.completed.items;
    },

    /**
     * 获取失败任务列表
     */
    getFailed() {
        return this.failed.items;
    },

    /**
     * 获取排序后的队列列表
     */
    getSortedQueue() {
        return this.getSortedList(this.queue);
    },

    /**
     * 获取排序后的定时任务列表
     */
    getSortedScheduled() {
        return this.getSortedList(this.scheduled);
    },

    /**
     * 获取排序后的运行中任务列表
     */
    getSortedRunning() {
        return this.getSortedList(this.running);
    },

    /**
     * 获取排序后的已完成任务列表
     */
    getSortedCompleted() {
        return this.getSortedList(this.completed.items);
    },

    /**
     * 获取排序后的失败任务列表
     */
    getSortedFailed() {
        return this.getSortedList(this.failed.items);
    },

    /**
     * 通用排序方法
     * @param {Array} items - 要排序的列表
     * @returns {Array} 排序后的列表
     */
    getSortedList(items) {
        if (!items || items.length === 0) return [];

        const { sortBy, sortOrder } = this;
        return [...items].sort((a, b) => {
            let aVal = a[sortBy];
            let bVal = b[sortBy];

            // 处理 undefined 或 null 检查
            if (aVal === undefined || aVal === null) aVal = '';
            if (bVal === undefined || bVal === null) bVal = '';

            // 比较排序
            if (sortOrder === 'asc') {
                return aVal < bVal ? -1 : 1;
            } else {
                return bVal < aVal ? -1 : 1;
            }
        });
    },

    /**
     * 获取筛选后的队列列表
     */
    getFilteredQueue() {
        return this.getFilteredList(this.queue);
    },

    /**
     * 获取筛选后的定时任务列表
     */
    getFilteredScheduled() {
        return this.getFilteredList(this.scheduled);
    },

    /**
     * 通用筛选方法
     * @param {Array} items - 要筛选的列表
     * @returns {Array} 筛选后的列表
     */
    getFilteredList(items) {
        if (!items || items.length === 0) return [];

        let { filterText, filterWorkspace, filterStatus } = this;

        return items.filter(item => {
            // 文本筛选（搜索任务描述、名称）
            if (filterText) {
                const searchText = filterText.toLowerCase();
                const prompt = (item.prompt || '').toLowerCase();
                const name = (item.name || '').toLowerCase();
                if (!prompt.includes(searchText) && !name.includes(searchText)) {
                    return false;
                }
            }

            // 工作空间筛选
            if (filterWorkspace) {
                const workspace = (item.workspace || '').toLowerCase();
                if (workspace !== filterWorkspace.toLowerCase()) {
                    return false;
                }
            }

            // 状态筛选（仅用于定时任务）
            if (filterStatus && item.enabled !== undefined) {
                const isEnabled = item.enabled ? 'enabled' : 'disabled';
                if (isEnabled !== filterStatus) {
                    return false;
                }
            }

            return true;
        });
    },
};

// 导出到全局命名空间
window.SchedulerState = SchedulerState;
