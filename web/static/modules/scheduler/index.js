/**
 * 任务调度主模块 (v7.0.10)
 * 整合所有子模块，提供统一的调度器功能
 */

// 导入子模块
import { SchedulerState } from './state.js';
import { SchedulerAPI } from './api.js';
import { SchedulerUtils } from './utils.js';
import { SchedulerRenderers } from './renderers/index.js';
// 对话框模块已自动绑定到 window 对象

/**
 * 调度器主模块
 */
const Scheduler = {
    // 导出状态和 API
    state: SchedulerState,
    api: SchedulerAPI,
    utils: SchedulerUtils,
    renderers: SchedulerRenderers,

    // 轮询定时器（已禁用自动轮询）
    refreshInterval: null,
    durationUpdateInterval: null,
    REFRESH_INTERVAL_MS: 5000,  // 5秒刷新一次（已禁用）
    DURATION_UPDATE_MS: 1000,  // 1秒更新运行时长（已禁用）

    // 页面可见性（已禁用）
    _isPageVisible: true,
    _shouldAutoRefresh: false,

    /**
     * 初始化模块
     */
    init() {
        this.bindEvents();
        this.initToolsMultiselect();
        // 轮询已禁用 // 自动
        console.log('[Scheduler] 模块初始化完成（手动刷新模式）');
    },

    // 页面可见性监听已禁用（自动轮询）

    /**
     * 绑定事件
     */
    bindEvents() {
        // 标签页切换
        const tabsContainer = document.getElementById('scheduler-tabs');
        if (tabsContainer) {
            tabsContainer.addEventListener('click', (e) => {
                const tab = e.target.closest('.scheduler-tab');
                if (tab) {
                    this.switchTab(tab.dataset.tab);
                }
            });
        }

        // 调度器控制按钮
        const startBtn = document.getElementById('scheduler-start-btn');
        const stopBtn = document.getElementById('scheduler-stop-btn');
        const refreshBtn = document.getElementById('scheduler-refresh-btn');

        if (startBtn) {
            startBtn.addEventListener('click', () => this.startScheduler());
        }
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopScheduler());
        }
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadAll());
        }

        // 添加任务按钮
        const addTaskBtn = document.getElementById('scheduler-add-task-btn');
        if (addTaskBtn) {
            addTaskBtn.addEventListener('click', () => {
                if (window.AddTaskDialog) {
                    window.AddTaskDialog.show();
                }
            });
        }

        // 清空队列按钮
        const clearQueueBtn = document.getElementById('scheduler-clear-queue-btn');
        if (clearQueueBtn) {
            clearQueueBtn.addEventListener('click', () => this.clearQueue());
        }

        // 添加定时任务按钮
        const addScheduledBtn = document.getElementById('scheduler-add-scheduled-btn');
        if (addScheduledBtn) {
            addScheduledBtn.addEventListener('click', () => {
                if (window.AddScheduledDialog) {
                    window.AddScheduledDialog.show();
                }
            });
        }
    },

    /**
     * 初始化工具多选组件
     */
    initToolsMultiselect() {
        // 任务对话框的工具选择
        const taskToolsBtn = document.getElementById('task-tools-select-btn');
        const taskToolsDropdown = document.getElementById('task-tools-dropdown');
        const taskToolsInput = document.getElementById('task-tools');

        if (taskToolsBtn && taskToolsDropdown) {
            this.setupToolsDropdown(taskToolsBtn, taskToolsDropdown, taskToolsInput);
        }

        // 定时任务对话框的工具选择
        const scheduledToolsBtn = document.getElementById('scheduled-tools-select-btn');
        const scheduledToolsDropdown = document.getElementById('scheduled-tools-dropdown');
        const scheduledToolsInput = document.getElementById('scheduled-tools');

        if (scheduledToolsBtn && scheduledToolsDropdown) {
                this.setupToolsDropdown(scheduledToolsBtn, scheduledToolsDropdown, scheduledToolsInput);
        }
    },

    /**
     * 设置工具下拉框
     */
    setupToolsDropdown(btn, dropdown, input) {
        // 渲染工具列表
        if (window.AVAILABLE_TOOLS) {
            const tools = window.AVAILABLE_TOOLS.map(tool => `
                <label class="tools-option">
                    <input type="checkbox" value="${tool.name}" ${tool.selected ? 'checked' : ''}>
                    <span>${tool.name}</span>
                    <span class="tools-option-desc">${tool.description || ''}</span>
                </label>
            `).join('');
            dropdown.innerHTML = tools;
        }

        // 切换下拉框
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });

        // 选择工具
        dropdown.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                this.updateToolsSelection(dropdown, btn, input);
            }
        });

        // 点击外部关闭
        document.addEventListener('click', () => {
            dropdown.classList.remove('show');
        });

        // 初始化选中状态
        this.updateToolsSelection(dropdown, btn, input);
    },

    /**
     * 更新工具选择状态
     */
    updateToolsSelection(dropdown, btn, input) {
        const checkboxes = dropdown.querySelectorAll('input[type="checkbox"]:checked');
        const count = checkboxes.length;
        const selectedText = btn.querySelector('.selected-text');
        const selectedCount = btn.querySelector('.selected-count');

        if (!selectedText || !selectedCount) {
            console.warn('[Scheduler] 工具选择按钮结构不完整', { btn, selectedText, selectedCount });
            return;
        }

        if (count === 0) {
            selectedText.textContent = '选择工具...';
            selectedCount.style.display = 'none';
        } else {
            selectedText.textContent = `已选择 ${count} 个工具`;
            selectedCount.textContent = count;
            selectedCount.style.display = 'inline';
        }

        // 更新隐藏输入
        const tools = Array.from(checkboxes).map(cb => cb.value);
        if (input) {
            input.value = tools.join(',');
        }
    },

    /**
     * 开始自动刷新（已禁用）
     */
    startAutoRefresh() {
        // 自动轮询已禁用
    },

    /**
     * 停止自动刷新（已禁用）
     */
    stopAutoRefresh() {
        // 自动轮询已禁用 - 保留函数以兼容外部调用
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        if (this.durationUpdateInterval) {
            clearInterval(this.durationUpdateInterval);
            this.durationUpdateInterval = null;
        }
        this._shouldAutoRefresh = false;
    },

    /**
     * 更新运行中任务的时长显示
     */
    updateRunningDurations() {
        const container = document.getElementById('scheduler-running-list');
        if (!container) return;

        const durationCells = container.querySelectorAll('.running-duration');
        durationCells.forEach(cell => {
            const startedAt = cell.dataset.startedAt;
            if (startedAt) {
                const startTime = new Date(startedAt).getTime();
                const elapsed = Date.now() - startTime;
                cell.textContent = SchedulerUtils.formatDuration(elapsed);
            }
        });
    },

    /**
     * 刷新当前标签页
     */
    async refreshCurrentTab() {
        switch (SchedulerState.activeTab) {
            case 'queue':
                await this.loadQueue();
                break;
            case 'scheduled':
                await this.loadScheduled();
                break;
            case 'running':
                await this.loadRunning();
                break;
            case 'completed':
                await this.loadCompleted();
                break;
            case 'failed':
                await this.loadFailed();
                break;
        }
        await this.loadSchedulerStatus();
    },

    /**
     * 加载所有数据
     */
    async loadAll() {
        SchedulerState.setLoading(true);
        try {
            await Promise.all([
                this.loadSchedulerStatus(),
                this.loadQueue(),
                this.loadScheduled(),
            ]);
        } finally {
            SchedulerState.setLoading(false);
        }
    },

    // ===== 标签页切换 =====

    /**
     * 切换标签页
     */
    async switchTab(tabName) {
        SchedulerState.setActiveTab(tabName);

        // 更新标签页高亮
        document.querySelectorAll('.scheduler-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // 切换内容区域
        document.querySelectorAll('.scheduler-tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.id === `scheduler-tab-${tabName}`);
        });

        // 加载对应数据
        switch (tabName) {
            case 'queue':
                await this.loadQueue();
                break;
            case 'scheduled':
                await this.loadScheduled();
                break;
            case 'running':
                await this.loadRunning();
                break;
            case 'completed':
                await this.loadCompleted();
                break;
            case 'failed':
                await this.loadFailed();
                break;
        }
    },

    // ===== API 调用 =====

    /**
     * 加载调度器状态
     */
    async loadSchedulerStatus() {
        try {
            const response = await SchedulerAPI.getStatus();
            const data = response.data || response;
            SchedulerState.setSchedulerStatus(data.is_running, data.last_check_time);
            this.renderSchedulerStatus();
        } catch (error) {
            console.error('[Scheduler] 加载调度器状态失败:', error);
        }
    },

    /**
     * 加载任务队列
     */
    async loadQueue() {
        try {
            const response = await SchedulerAPI.getQueue();
            const data = response.data || response;
            const items = Array.isArray(data) ? data : (data.items || []);
            SchedulerState.setQueue(items);
            SchedulerRenderers.renderQueueList();
            this.updateStats();
        } catch (error) {
            console.error('[Scheduler] 加载任务队列失败:', error);
            SchedulerRenderers.renderListError('scheduler-queue-list', '加载失败');
        }
    },

    /**
     * 加载定时任务
     */
    async loadScheduled() {
        try {
            const response = await SchedulerAPI.getScheduled();
            const data = response.data || response;
            const items = Array.isArray(data) ? data : (data.items || []);
            SchedulerState.setScheduled(items);
            SchedulerRenderers.renderScheduledList();
            this.updateStats();
        } catch (error) {
            console.error('[Scheduler] 加载定时任务失败:', error);
            SchedulerRenderers.renderListError('scheduler-scheduled-list', '加载失败');
        }
    },

    /**
     * 加载运行中任务
     */
    async loadRunning() {
        try {
            const response = await SchedulerAPI.getRunning();
            const data = response.data || response;
            const items = Array.isArray(data) ? data : (data.items || []);
            SchedulerState.setRunning(items);
            SchedulerRenderers.renderRunningList();
            this.updateStats();
        } catch (error) {
            console.error('[Scheduler] 加载运行中任务失败:', error);
            SchedulerRenderers.renderListError('scheduler-running-list', '加载失败');
        }
    },

    /**
     * 加载已完成任务
     */
    async loadCompleted(page = 1) {
        try {
            const response = await SchedulerAPI.getCompleted(page, SchedulerState.completed.limit);
            const data = response.data || response;
            SchedulerState.setCompleted({
                items: Array.isArray(data) ? data : (data.items || []),
                page: page,
                total: data.total || 0,
                limit: data.limit || SchedulerState.completed.limit,
            });
            SchedulerRenderers.renderCompletedList();
            SchedulerRenderers.renderPagination('completed-pagination', SchedulerState.completed, (p) => this.loadCompleted(p));
        } catch (error) {
            console.error('[Scheduler] 加载已完成任务失败:', error);
            SchedulerRenderers.renderListError('scheduler-completed-list', '加载失败');
        }
    },

    /**
     * 加载失败任务
     */
    async loadFailed(page = 1) {
        try {
            const response = await SchedulerAPI.getFailed(page, SchedulerState.failed.limit);
            const data = response.data || response;
            SchedulerState.setFailed({
                items: Array.isArray(data) ? data : (data.items || []),
                page: page,
                total: data.total || 0,
                limit: data.limit || SchedulerState.failed.limit,
            });
            SchedulerRenderers.renderFailedList();
            SchedulerRenderers.renderPagination('failed-pagination', SchedulerState.failed, (p) => this.loadFailed(p));
        } catch (error) {
            console.error('[Scheduler] 加载失败任务失败:', error);
            SchedulerRenderers.renderListError('scheduler-failed-list', '加载失败');
        }
    },

    // ===== 调度器控制 =====

    /**
     * 启动调度器
     */
    async startScheduler() {
        try {
            await SchedulerAPI.start();
            SchedulerUtils.showNotification('调度器已启动', 'success');
            await this.loadSchedulerStatus();
        } catch (error) {
            SchedulerUtils.showNotification('启动失败: ' + error.message, 'error');
        }
    },

    /**
     * 停止调度器
     */
    async stopScheduler() {
        try {
            await SchedulerAPI.stop();
            SchedulerUtils.showNotification('调度器已停止', 'success');
            await this.loadSchedulerStatus();
        } catch (error) {
            SchedulerUtils.showNotification('停止失败: ' + error.message, 'error');
        }
    },

    // ===== 任务操作 =====

    /**
     * 删除队列任务
     */
    async deleteTask(taskId) {
        if (!confirm('确定要删除这个任务吗？')) return;

        try {
            await SchedulerAPI.deleteTask(taskId);
            SchedulerUtils.showNotification('任务已删除', 'success');
            await this.loadQueue();
        } catch (error) {
            SchedulerUtils.showNotification('删除失败: ' + error.message, 'error');
        }
    },

    /**
     * 清空队列
     */
    async clearQueue() {
        if (!confirm('确定要清空任务队列吗？')) return;

        try {
            await SchedulerAPI.clearQueue();
            SchedulerUtils.showNotification('队列已清空', 'success');
            await this.loadQueue();
        } catch (error) {
            SchedulerUtils.showNotification('清空失败: ' + error.message, 'error');
        }
    },

    // ===== 定时任务操作 =====

    /**
     * 显示添加/编辑定时任务对话框
     */
    showAddScheduledDialog(task = null) {
        if (window.AddScheduledDialog) {
            window.AddScheduledDialog.show(task);
        }
    },

    /**
     * 切换定时任务启用状态
     */
    async toggleScheduled(taskId) {
        try {
            await SchedulerAPI.toggleScheduled(taskId);
            SchedulerUtils.showNotification('状态已更新', 'success');
            await this.loadScheduled();
        } catch (error) {
            SchedulerUtils.showNotification('操作失败: ' + error.message, 'error');
        }
    },

    /**
     * 立即执行定时任务
     */
    async runScheduledNow(taskId) {
        if (!confirm('确定要立即执行这个定时任务吗？')) return;

        try {
            await SchedulerAPI.runScheduledNow(taskId);
            SchedulerUtils.showNotification('任务已加入队列', 'success');
            await this.loadQueue();
        } catch (error) {
            SchedulerUtils.showNotification('执行失败: ' + error.message, 'error');
        }
    },

    /**
     * 删除定时任务
     */
    async deleteScheduled(taskId) {
        if (!confirm('确定要删除这个定时任务吗？')) return;

        try {
            await SchedulerAPI.deleteScheduled(taskId);
            SchedulerUtils.showNotification('定时任务已删除', 'success');
            await this.loadScheduled();
        } catch (error) {
            SchedulerUtils.showNotification('删除失败: ' + error.message, 'error');
        }
    },

    // ===== 任务详情 =====

    /**
     * 显示任务详情
     */
    async showTaskDetail(taskId) {
        if (window.TaskDetailDialog) {
            await window.TaskDetailDialog.show(taskId);
        }
    },

    /**
     * 重试失败任务
     */
    async retryTask(taskId) {
        try {
            const response = await SchedulerAPI.getTaskDetail(taskId);
            const task = response.data || response;

            const allowedTools = task.allowed_tools
                ? (Array.isArray(task.allowed_tools) ? task.allowed_tools : task.allowed_tools.split(','))
                : null;

            await SchedulerAPI.addTask({
                prompt: task.prompt,
                workspace: task.workspace,
                timeout: task.timeout,
                allowed_tools: allowedTools,
                auto_approve: task.auto_approve,
            });
            SchedulerUtils.showNotification('任务已重新加入队列', 'success');
            await this.loadQueue();
        } catch (error) {
            SchedulerUtils.showNotification('重试失败: ' + error.message, 'error');
        }
    },

    // ===== 渲染方法 =====

    /**
     * 渲染调度器状态
     */
    renderSchedulerStatus() {
        const { isRunning } = SchedulerState.scheduler;
        const icon = document.getElementById('scheduler-status-icon');
        const text = document.getElementById('scheduler-status-text');
        const startBtn = document.getElementById('scheduler-start-btn');
        const stopBtn = document.getElementById('scheduler-stop-btn');

        if (isRunning) {
            icon.textContent = '▶';
            icon.className = 'scheduler-status-icon running';
            text.textContent = '运行中';
            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-block';
        } else {
            icon.textContent = '⏸';
            icon.className = 'scheduler-status-icon stopped';
            text.textContent = '已停止';
            startBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
        }
    },

    /**
     * 更新统计信息
     */
    updateStats() {
        document.getElementById('scheduler-queue-count').textContent = SchedulerState.stats.queueCount;
        document.getElementById('scheduler-scheduled-count').textContent = SchedulerState.stats.scheduledCount;
        document.getElementById('scheduler-running-count').textContent = SchedulerState.stats.runningCount;
    },

    /**
     * 视图显示时调用
     */
    async onShow() {
        await this.loadAll();
        // 手动刷新模式 - 不启动自动轮询
    },

    /**
     * 视图隐藏时调用
     */
    onHide() {
        // 手动刷新模式 - 不停止轮询（因为没有启动）
    },
};

// 将Scheduler对象暴露到全局作用域，以便非模块脚本（如app.js）可以访问
window.Scheduler = Scheduler;

// ES6 模块导出
export { Scheduler };

// 初始化调度器（保持原有的初始化逻辑）
document.addEventListener('DOMContentLoaded', () => {
    Scheduler.init();
});
