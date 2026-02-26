/**
 * 任务调度模块 (v0.6.4)
 * 管理任务队列、定时任务和任务状态
 */

const Scheduler = {
    // 状态
    state: {
        scheduler: {
            isRunning: false,
            lastCheckTime: null,
        },
        stats: {
            queueCount: 0,
            scheduledCount: 0,
            runningCount: 0,
        },
        activeTab: 'queue',
        queue: [],
        scheduled: [],
        running: [],
        completed: { items: [], page: 1, total: 0, limit: 20 },
        failed: { items: [], page: 1, total: 0, limit: 20 },
        loading: false,
    },

    // 轮询定时器
    refreshInterval: null,
    durationUpdateInterval: null,  // 运行时长更新定时器
    REFRESH_INTERVAL_MS: 5000,  // 5秒刷新一次
    DURATION_UPDATE_MS: 1000,  // 1秒更新运行时长

    // Cron 示例
    cronExamples: [
        { expression: '0 9 * * *', description: '每天上午 9:00' },
        { expression: '0 18 * * *', description: '每天下午 6:00' },
        { expression: '0 9,18 * * *', description: '每天上午 9:00 和下午 6:00' },
        { expression: '0 9 * * 1', description: '每周一上午 9:00' },
        { expression: '0 9 * * 1-5', description: '每周一到周五上午 9:00' },
        { expression: '0 0 * * *', description: '每天午夜 0:00' },
        { expression: '0 */2 * * *', description: '每 2 小时' },
        { expression: '*/30 * * * *', description: '每 30 分钟' },
        { expression: '0 9 1 * *', description: '每月 1 号上午 9:00' },
    ],

    // 编辑中的定时任务 ID
    editingScheduledId: null,

    /**
     * 初始化模块
     */
    init() {
        this.bindEvents();
        this.initToolsMultiselect();
    },

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
            addTaskBtn.addEventListener('click', () => this.showAddTaskDialog());
        }

        // 清空队列按钮
        const clearQueueBtn = document.getElementById('scheduler-clear-queue-btn');
        if (clearQueueBtn) {
            clearQueueBtn.addEventListener('click', () => this.clearQueue());
        }

        // 添加定时任务按钮
        const addScheduledBtn = document.getElementById('scheduler-add-scheduled-btn');
        if (addScheduledBtn) {
            addScheduledBtn.addEventListener('click', () => this.showAddScheduledDialog());
        }

        // 对话框关闭按钮
        this.bindDialogEvents();

        // Cron 表达式输入
        const cronInput = document.getElementById('scheduled-cron');
        if (cronInput) {
            cronInput.addEventListener('input', Utils.debounce(() => {
                this.validateCron(cronInput.value);
            }, 300));
        }

        // Cron 帮助按钮
        const cronHelpBtn = document.getElementById('cron-help-btn');
        if (cronHelpBtn) {
            cronHelpBtn.addEventListener('click', () => this.showCronHelpDialog());
        }

        // 详情对话框日志折叠
        const outputToggle = document.getElementById('detail-output-toggle');
        if (outputToggle) {
            outputToggle.addEventListener('click', () => {
                const content = document.getElementById('detail-task-output');
                const icon = outputToggle.querySelector('.collapse-icon');
                if (content) {
                    content.classList.toggle('collapsed');
                    if (icon) {
                        icon.textContent = content.classList.contains('collapsed') ? '▶' : '▼';
                    }
                }
            });
        }

        // 复制日志按钮
        const copyLogBtn = document.getElementById('copy-task-log-btn');
        if (copyLogBtn) {
            copyLogBtn.addEventListener('click', () => this.copyTaskLog());
        }
    },

    /**
     * 绑定对话框事件
     */
    bindDialogEvents() {
        // 添加任务对话框
        const addTaskDialog = document.getElementById('add-task-dialog');
        const closeAddTaskDialog = document.getElementById('close-add-task-dialog');
        const cancelAddTaskBtn = document.getElementById('cancel-add-task-btn');
        const confirmAddTaskBtn = document.getElementById('confirm-add-task-btn');

        if (closeAddTaskDialog) {
            closeAddTaskDialog.addEventListener('click', () => this.hideAddTaskDialog());
        }
        if (cancelAddTaskBtn) {
            cancelAddTaskBtn.addEventListener('click', () => this.hideAddTaskDialog());
        }
        if (confirmAddTaskBtn) {
            confirmAddTaskBtn.addEventListener('click', () => this.addTask());
        }

        // 添加定时任务对话框
        const addScheduledDialog = document.getElementById('add-scheduled-dialog');
        const closeAddScheduledDialog = document.getElementById('close-add-scheduled-dialog');
        const cancelAddScheduledBtn = document.getElementById('cancel-add-scheduled-btn');
        const confirmAddScheduledBtn = document.getElementById('confirm-add-scheduled-btn');

        if (closeAddScheduledDialog) {
            closeAddScheduledDialog.addEventListener('click', () => this.hideAddScheduledDialog());
        }
        if (cancelAddScheduledBtn) {
            cancelAddScheduledBtn.addEventListener('click', () => this.hideAddScheduledDialog());
        }
        if (confirmAddScheduledBtn) {
            confirmAddScheduledBtn.addEventListener('click', () => this.saveScheduledTask());
        }

        // 任务详情对话框
        const taskDetailDialog = document.getElementById('task-detail-dialog');
        const closeTaskDetailDialog = document.getElementById('close-task-detail-dialog');
        const closeDetailBtn = document.getElementById('close-detail-btn');

        if (closeTaskDetailDialog) {
            closeTaskDetailDialog.addEventListener('click', () => this.hideTaskDetailDialog());
        }
        if (closeDetailBtn) {
            closeDetailBtn.addEventListener('click', () => this.hideTaskDetailDialog());
        }

        // Cron 帮助对话框
        const cronHelpDialog = document.getElementById('cron-help-dialog');
        const closeCronHelpDialog = document.getElementById('close-cron-help-dialog');
        const closeCronHelpBtn = document.getElementById('close-cron-help-btn');

        if (closeCronHelpDialog) {
            closeCronHelpDialog.addEventListener('click', () => this.hideCronHelpDialog());
        }
        if (closeCronHelpBtn) {
            closeCronHelpBtn.addEventListener('click', () => this.hideCronHelpDialog());
        }

        // 点击对话框外部关闭
        [addTaskDialog, addScheduledDialog, taskDetailDialog, cronHelpDialog].forEach(dialog => {
            if (dialog) {
                dialog.addEventListener('click', (e) => {
                    if (e.target === dialog) {
                        dialog.classList.remove('active');
                    }
                });
            }
        });
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
        const tools = AVAILABLE_TOOLS.map(tool => `
            <label class="tools-option">
                <input type="checkbox" value="${tool.name}" ${tool.selected ? 'checked' : ''}>
                <span>${tool.name}</span>
                <span class="tools-option-desc">${tool.description}</span>
            </label>
        `).join('');
        dropdown.innerHTML = tools;

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
     * 视图显示时调用
     */
    async onShow() {
        await this.loadAll();
        this.startAutoRefresh();
    },

    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        this.stopAutoRefresh();
        this.refreshInterval = setInterval(() => {
            this.refreshCurrentTab();
        }, this.REFRESH_INTERVAL_MS);
        // 运行时长实时更新
        this.durationUpdateInterval = setInterval(() => {
            this.updateRunningDurations();
        }, this.DURATION_UPDATE_MS);
    },

    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        if (this.durationUpdateInterval) {
            clearInterval(this.durationUpdateInterval);
            this.durationUpdateInterval = null;
        }
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
                cell.textContent = this.formatDuration(elapsed);
            }
        });
    },

    /**
     * 刷新当前标签页
     */
    async refreshCurrentTab() {
        switch (this.state.activeTab) {
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
        this.state.loading = true;
        try {
            await Promise.all([
                this.loadSchedulerStatus(),
                this.loadQueue(),
            ]);
        } finally {
            this.state.loading = false;
        }
    },

    // ===== 标签页切换 =====

    /**
     * 切换标签页
     */
    async switchTab(tabName) {
        this.state.activeTab = tabName;

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
            const data = await SchedulerAPI.getStatus();
            this.state.scheduler.isRunning = data.is_running;
            this.state.scheduler.lastCheckTime = data.last_check_time;
            this.renderSchedulerStatus();
        } catch (error) {
            console.error('加载调度器状态失败:', error);
        }
    },

    /**
     * 加载任务队列
     */
    async loadQueue() {
        try {
            const data = await SchedulerAPI.getQueue();
            this.state.queue = data.items || [];
            this.state.stats.queueCount = this.state.queue.length;
            this.renderQueueList();
            this.updateStats();
        } catch (error) {
            console.error('加载任务队列失败:', error);
            this.renderListError('scheduler-queue-list', '加载失败');
        }
    },

    /**
     * 加载定时任务
     */
    async loadScheduled() {
        try {
            const data = await SchedulerAPI.getScheduled();
            this.state.scheduled = data.items || [];
            this.state.stats.scheduledCount = this.state.scheduled.length;
            this.renderScheduledList();
            this.updateStats();
        } catch (error) {
            console.error('加载定时任务失败:', error);
            this.renderListError('scheduler-scheduled-list', '加载失败');
        }
    },

    /**
     * 加载运行中任务
     */
    async loadRunning() {
        try {
            const data = await SchedulerAPI.getRunning();
            this.state.running = data.items || [];
            this.state.stats.runningCount = this.state.running.length;
            this.renderRunningList();
            this.updateStats();
        } catch (error) {
            console.error('加载运行中任务失败:', error);
            this.renderListError('scheduler-running-list', '加载失败');
        }
    },

    /**
     * 加载已完成任务
     */
    async loadCompleted(page = 1) {
        try {
            this.state.completed.page = page;
            const data = await SchedulerAPI.getCompleted(page, this.state.completed.limit);
            this.state.completed.items = data.items || [];
            this.state.completed.total = data.total || 0;
            this.renderCompletedList();
            this.renderPagination('completed-pagination', this.state.completed, (p) => this.loadCompleted(p));
        } catch (error) {
            console.error('加载已完成任务失败:', error);
            this.renderListError('scheduler-completed-list', '加载失败');
        }
    },

    /**
     * 加载失败任务
     */
    async loadFailed(page = 1) {
        try {
            this.state.failed.page = page;
            const data = await SchedulerAPI.getFailed(page, this.state.failed.limit);
            this.state.failed.items = data.items || [];
            this.state.failed.total = data.total || 0;
            this.renderFailedList();
            this.renderPagination('failed-pagination', this.state.failed, (p) => this.loadFailed(p));
        } catch (error) {
            console.error('加载失败任务失败:', error);
            this.renderListError('scheduler-failed-list', '加载失败');
        }
    },

    // ===== 调度器控制 =====

    /**
     * 启动调度器
     */
    async startScheduler() {
        try {
            await SchedulerAPI.start();
            Utils.showNotification('调度器已启动', 'success');
            await this.loadSchedulerStatus();
        } catch (error) {
            Utils.showNotification('启动失败: ' + error.message, 'error');
        }
    },

    /**
     * 停止调度器
     */
    async stopScheduler() {
        try {
            await SchedulerAPI.stop();
            Utils.showNotification('调度器已停止', 'success');
            await this.loadSchedulerStatus();
        } catch (error) {
            Utils.showNotification('停止失败: ' + error.message, 'error');
        }
    },

    // ===== 任务操作 =====

    /**
     * 显示添加任务对话框
     */
    showAddTaskDialog() {
        // 重置表单
        document.getElementById('task-prompt').value = '';
        document.getElementById('task-working-dir').value = '';
        document.getElementById('task-timeout').value = '600';
        document.getElementById('task-auto-approve').checked = false;

        // 重置工具选择
        const dropdown = document.getElementById('task-tools-dropdown');
        const checkboxes = dropdown.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach((cb, i) => {
            cb.checked = AVAILABLE_TOOLS[i]?.selected || false;
        });
        this.updateToolsSelection(
            dropdown,
            document.getElementById('task-tools-select-btn'),
            document.getElementById('task-tools')
        );

        document.getElementById('add-task-dialog').classList.add('active');
    },

    /**
     * 隐藏添加任务对话框
     */
    hideAddTaskDialog() {
        document.getElementById('add-task-dialog').classList.remove('active');
    },

    /**
     * 添加任务到队列
     */
    async addTask() {
        const prompt = document.getElementById('task-prompt').value.trim();
        if (!prompt) {
            Utils.showNotification('请输入任务描述', 'error');
            return;
        }

        const task = {
            prompt,
            working_dir: document.getElementById('task-working-dir').value.trim() || null,
            timeout: parseInt(document.getElementById('task-timeout').value) * 1000,
            tools: document.getElementById('task-tools').value || null,
            auto_approve: document.getElementById('task-auto-approve').checked,
        };

        try {
            await SchedulerAPI.addTask(task);
            Utils.showNotification('任务已添加到队列', 'success');
            this.hideAddTaskDialog();
            await this.loadQueue();
        } catch (error) {
            Utils.showNotification('添加失败: ' + error.message, 'error');
        }
    },

    /**
     * 删除队列任务
     */
    async deleteTask(taskId) {
        if (!confirm('确定要删除这个任务吗？')) return;

        try {
            await SchedulerAPI.deleteTask(taskId);
            Utils.showNotification('任务已删除', 'success');
            await this.loadQueue();
        } catch (error) {
            Utils.showNotification('删除失败: ' + error.message, 'error');
        }
    },

    /**
     * 清空队列
     */
    async clearQueue() {
        if (!confirm('确定要清空任务队列吗？')) return;

        try {
            await SchedulerAPI.clearQueue();
            Utils.showNotification('队列已清空', 'success');
            await this.loadQueue();
        } catch (error) {
            Utils.showNotification('清空失败: ' + error.message, 'error');
        }
    },

    // ===== 定时任务操作 =====

    /**
     * 显示添加定时任务对话框
     */
    showAddScheduledDialog(task = null) {
        this.editingScheduledId = task ? task.id : null;

        // 更新对话框标题
        document.getElementById('scheduled-dialog-title').textContent =
            task ? '编辑定时任务' : '添加定时任务';

        // 填充表单
        document.getElementById('scheduled-task-id').value = task?.id || '';
        document.getElementById('scheduled-name').value = task?.name || '';
        document.getElementById('scheduled-cron').value = task?.cron_expression || '';
        document.getElementById('scheduled-prompt').value = task?.prompt || '';
        document.getElementById('scheduled-working-dir').value = task?.working_dir || '';
        document.getElementById('scheduled-timeout').value = (task?.timeout || 600000) / 1000;
        document.getElementById('scheduled-auto-approve').checked = task?.auto_approve || false;
        document.getElementById('scheduled-enabled').checked = task?.enabled !== false;

        // 设置工具选择
        const tools = task?.tools ? task.tools.split(',') : AVAILABLE_TOOLS.filter(t => t.selected).map(t => t.name);
        const dropdown = document.getElementById('scheduled-tools-dropdown');
        const checkboxes = dropdown.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => {
            cb.checked = tools.includes(cb.value);
        });
        this.updateToolsSelection(
            dropdown,
            document.getElementById('scheduled-tools-select-btn'),
            document.getElementById('scheduled-tools')
        );

        // 验证 Cron 表达式
        if (task?.cron_expression) {
            this.validateCron(task.cron_expression);
        } else {
            document.getElementById('cron-preview').style.display = 'none';
            document.getElementById('cron-error').style.display = 'none';
        }

        document.getElementById('add-scheduled-dialog').classList.add('active');
    },

    /**
     * 隐藏添加定时任务对话框
     */
    hideAddScheduledDialog() {
        document.getElementById('add-scheduled-dialog').classList.remove('active');
        this.editingScheduledId = null;
    },

    /**
     * 保存定时任务
     */
    async saveScheduledTask() {
        const name = document.getElementById('scheduled-name').value.trim();
        const cronExpression = document.getElementById('scheduled-cron').value.trim();
        const prompt = document.getElementById('scheduled-prompt').value.trim();

        if (!name) {
            Utils.showNotification('请输入任务名称', 'error');
            return;
        }
        if (!cronExpression) {
            Utils.showNotification('请输入 Cron 表达式', 'error');
            return;
        }
        if (!prompt) {
            Utils.showNotification('请输入任务描述', 'error');
            return;
        }

        const task = {
            name,
            cron_expression: cronExpression,
            prompt,
            working_dir: document.getElementById('scheduled-working-dir').value.trim() || null,
            timeout: parseInt(document.getElementById('scheduled-timeout').value) * 1000,
            tools: document.getElementById('scheduled-tools').value || null,
            auto_approve: document.getElementById('scheduled-auto-approve').checked,
            enabled: document.getElementById('scheduled-enabled').checked,
        };

        try {
            if (this.editingScheduledId) {
                await SchedulerAPI.updateScheduled(this.editingScheduledId, task);
                Utils.showNotification('定时任务已更新', 'success');
            } else {
                await SchedulerAPI.addScheduled(task);
                Utils.showNotification('定时任务已创建', 'success');
            }
            this.hideAddScheduledDialog();
            await this.loadScheduled();
        } catch (error) {
            Utils.showNotification('保存失败: ' + error.message, 'error');
        }
    },

    /**
     * 切换定时任务启用状态
     */
    async toggleScheduled(taskId) {
        try {
            await SchedulerAPI.toggleScheduled(taskId);
            Utils.showNotification('状态已更新', 'success');
            await this.loadScheduled();
        } catch (error) {
            Utils.showNotification('操作失败: ' + error.message, 'error');
        }
    },

    /**
     * 立即执行定时任务
     */
    async runScheduledNow(taskId) {
        if (!confirm('确定要立即执行这个定时任务吗？')) return;

        try {
            await SchedulerAPI.runScheduledNow(taskId);
            Utils.showNotification('任务已加入队列', 'success');
            await this.loadQueue();
        } catch (error) {
            Utils.showNotification('执行失败: ' + error.message, 'error');
        }
    },

    /**
     * 删除定时任务
     */
    async deleteScheduled(taskId) {
        if (!confirm('确定要删除这个定时任务吗？')) return;

        try {
            await SchedulerAPI.deleteScheduled(taskId);
            Utils.showNotification('定时任务已删除', 'success');
            await this.loadScheduled();
        } catch (error) {
            Utils.showNotification('删除失败: ' + error.message, 'error');
        }
    },

    // ===== Cron 验证 =====

    /**
     * 验证 Cron 表达式
     */
    async validateCron(expression) {
        const preview = document.getElementById('cron-preview');
        const error = document.getElementById('cron-error');
        const nextRun = document.getElementById('cron-next-run');

        if (!expression) {
            preview.style.display = 'none';
            error.style.display = 'none';
            return false;
        }

        try {
            const result = await SchedulerAPI.validateCron(expression);
            if (result.valid) {
                preview.style.display = 'flex';
                error.style.display = 'none';
                nextRun.textContent = result.next_run
                    ? this.formatDateTime(result.next_run)
                    : '-';
                return true;
            } else {
                preview.style.display = 'none';
                error.style.display = 'block';
                error.textContent = result.error || '无效的 Cron 表达式';
                return false;
            }
        } catch (err) {
            preview.style.display = 'none';
            error.style.display = 'block';
            error.textContent = '验证失败';
            return false;
        }
    },

    /**
     * 显示 Cron 帮助对话框
     */
    async showCronHelpDialog() {
        // 渲染示例列表
        const examplesList = document.getElementById('cron-examples-list');
        if (examplesList) {
            examplesList.innerHTML = this.cronExamples.map(ex => `
                <div class="cron-example-item" data-expression="${ex.expression}">
                    <code class="cron-example-expr">${ex.expression}</code>
                    <span class="cron-example-desc">${ex.description}</span>
                </div>
            `).join('');

            // 点击示例填充
            examplesList.querySelectorAll('.cron-example-item').forEach(item => {
                item.addEventListener('click', () => {
                    const expr = item.dataset.expression;
                    document.getElementById('scheduled-cron').value = expr;
                    this.validateCron(expr);
                    this.hideCronHelpDialog();
                });
            });
        }

        document.getElementById('cron-help-dialog').classList.add('active');
    },

    /**
     * 隐藏 Cron 帮助对话框
     */
    hideCronHelpDialog() {
        document.getElementById('cron-help-dialog').classList.remove('active');
    },

    // ===== 任务详情 =====

    /**
     * 显示任务详情
     */
    async showTaskDetail(taskId) {
        try {
            const task = await SchedulerAPI.getTaskDetail(taskId);
            this.renderTaskDetail(task);
            document.getElementById('task-detail-dialog').classList.add('active');
        } catch (error) {
            Utils.showNotification('加载详情失败: ' + error.message, 'error');
        }
    },

    /**
     * 隐藏任务详情对话框
     */
    hideTaskDetailDialog() {
        document.getElementById('task-detail-dialog').classList.remove('active');
    },

    /**
     * 渲染任务详情
     */
    renderTaskDetail(task) {
        document.getElementById('detail-task-prompt').textContent = task.prompt || '-';
        document.getElementById('detail-task-status').textContent = this.getStatusText(task.status);
        document.getElementById('detail-task-status').className = `status-value status-${task.status}`;
        document.getElementById('detail-task-started').textContent = task.started_at
            ? this.formatDateTime(task.started_at)
            : '-';
        document.getElementById('detail-task-ended').textContent = task.ended_at
            ? this.formatDateTime(task.ended_at)
            : '-';
        document.getElementById('detail-task-duration').textContent = task.duration_ms
            ? this.formatDuration(task.duration_ms)
            : '-';
        document.getElementById('detail-task-working-dir').textContent = task.working_dir || '默认目录';

        // 工具使用
        const toolsEl = document.getElementById('detail-task-tools');
        if (task.tools_used && task.tools_used.length > 0) {
            toolsEl.innerHTML = task.tools_used.map(t => `<span class="tool-tag">${t}</span>`).join('');
        } else {
            toolsEl.innerHTML = '<span class="empty-text">无</span>';
        }

        // 文件变更
        const filesEl = document.getElementById('detail-task-files');
        if (task.files_changed && task.files_changed.length > 0) {
            filesEl.innerHTML = task.files_changed.map(f => `<div class="file-item">${f}</div>`).join('');
        } else {
            filesEl.innerHTML = '<span class="empty-text">无</span>';
        }

        // 输出日志
        const outputEl = document.getElementById('detail-task-output');
        if (task.output) {
            outputEl.innerHTML = `<pre class="task-output-pre">${this.escapeHtml(task.output)}</pre>`;
        } else {
            outputEl.innerHTML = '<span class="empty-text">暂无日志</span>';
        }

        // 错误信息
        const errorSection = document.getElementById('detail-error-section');
        const errorEl = document.getElementById('detail-task-error');
        if (task.error) {
            errorSection.style.display = 'block';
            errorEl.textContent = task.error;
        } else {
            errorSection.style.display = 'none';
        }
    },

    /**
     * 复制任务日志
     */
    copyTaskLog() {
        const outputEl = document.getElementById('detail-task-output');
        const text = outputEl.textContent;
        navigator.clipboard.writeText(text).then(() => {
            Utils.showNotification('日志已复制', 'success');
        }).catch(() => {
            Utils.showNotification('复制失败', 'error');
        });
    },

    /**
     * 重试失败任务
     */
    async retryTask(taskId) {
        try {
            // 重新添加任务到队列
            const task = await SchedulerAPI.getTaskDetail(taskId);
            await SchedulerAPI.addTask({
                prompt: task.prompt,
                working_dir: task.working_dir,
                timeout: task.timeout,
                tools: task.tools,
                auto_approve: task.auto_approve,
            });
            Utils.showNotification('任务已重新加入队列', 'success');
            await this.loadQueue();
        } catch (error) {
            Utils.showNotification('重试失败: ' + error.message, 'error');
        }
    },

    // ===== 渲染方法 =====

    /**
     * 渲染调度器状态
     */
    renderSchedulerStatus() {
        const { isRunning } = this.state.scheduler;
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
        document.getElementById('scheduler-queue-count').textContent = this.state.stats.queueCount;
        document.getElementById('scheduler-scheduled-count').textContent = this.state.stats.scheduledCount;
        document.getElementById('scheduler-running-count').textContent = this.state.stats.runningCount;
    },

    /**
     * 渲染任务队列列表
     */
    renderQueueList() {
        const container = document.getElementById('scheduler-queue-list');
        const items = this.state.queue;

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">队列为空</div>';
            return;
        }

        container.innerHTML = `
            <table class="scheduler-table">
                <thead>
                    <tr>
                        <th>描述</th>
                        <th>工作目录</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map(task => `
                        <tr>
                            <td class="task-prompt">${this.truncate(task.prompt, 50)}</td>
                            <td>${task.working_dir || '默认'}</td>
                            <td>${this.formatDateTime(task.created_at)}</td>
                            <td class="actions">
                                <button class="btn btn-small btn-danger" onclick="Scheduler.deleteTask('${task.id}')">🗑 删除</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    },

    /**
     * 渲染定时任务列表
     */
    renderScheduledList() {
        const container = document.getElementById('scheduler-scheduled-list');
        const items = this.state.scheduled;

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无定时任务</div>';
            return;
        }

        container.innerHTML = `
            <table class="scheduler-table">
                <thead>
                    <tr>
                        <th>名称</th>
                        <th>Cron</th>
                        <th>下次运行</th>
                        <th>状态</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map(task => `
                        <tr>
                            <td>${this.escapeHtml(task.name)}</td>
                            <td><code>${task.cron_expression}</code></td>
                            <td>${task.next_run ? this.formatDateTime(task.next_run) : '-'}</td>
                            <td>
                                <span class="status-badge ${task.enabled ? 'enabled' : 'disabled'}">
                                    ${task.enabled ? '✓ 启用' : '✗ 禁用'}
                                </span>
                            </td>
                            <td class="actions">
                                <button class="btn btn-small" onclick="Scheduler.toggleScheduled('${task.id}')">
                                    ${task.enabled ? '禁用' : '启用'}
                                </button>
                                <button class="btn btn-small" onclick="Scheduler.runScheduledNow('${task.id}')">▶ 执行</button>
                                <button class="btn btn-small" onclick="Scheduler.showAddScheduledDialog(Scheduler.state.scheduled.find(t => t.id === '${task.id}'))">✎ 编辑</button>
                                <button class="btn btn-small btn-danger" onclick="Scheduler.deleteScheduled('${task.id}')">🗑</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    },

    /**
     * 渲染运行中任务列表
     */
    renderRunningList() {
        const container = document.getElementById('scheduler-running-list');
        const items = this.state.running;

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无运行中任务</div>';
            return;
        }

        container.innerHTML = `
            <table class="scheduler-table">
                <thead>
                    <tr>
                        <th>状态</th>
                        <th>描述</th>
                        <th>运行时长</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map(task => {
                        const startedAt = task.started_at || new Date().toISOString();
                        const elapsed = Date.now() - new Date(startedAt).getTime();
                        return `
                        <tr>
                            <td><span class="status-icon running">🔄</span></td>
                            <td class="task-prompt">${this.truncate(task.prompt, 50)}</td>
                            <td class="running-duration" data-started-at="${startedAt}">${this.formatDuration(elapsed)}</td>
                            <td class="actions">
                                <button class="btn btn-small" onclick="Scheduler.showTaskDetail('${task.id}')">详情</button>
                            </td>
                        </tr>
                    `}).join('')}
                </tbody>
            </table>
        `;
    },

    /**
     * 渲染已完成任务列表
     */
    renderCompletedList() {
        const container = document.getElementById('scheduler-completed-list');
        const items = this.state.completed.items;

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无已完成任务</div>';
            return;
        }

        container.innerHTML = `
            <table class="scheduler-table">
                <thead>
                    <tr>
                        <th>状态</th>
                        <th>描述</th>
                        <th>完成时间</th>
                        <th>耗时</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map(task => `
                        <tr>
                            <td><span class="status-icon completed">✅</span></td>
                            <td class="task-prompt">${this.truncate(task.prompt, 50)}</td>
                            <td>${this.formatDateTime(task.ended_at)}</td>
                            <td>${this.formatDuration(task.duration_ms)}</td>
                            <td class="actions">
                                <button class="btn btn-small" onclick="Scheduler.showTaskDetail('${task.id}')">详情</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    },

    /**
     * 渲染失败任务列表
     */
    renderFailedList() {
        const container = document.getElementById('scheduler-failed-list');
        const items = this.state.failed.items;

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无失败任务</div>';
            return;
        }

        container.innerHTML = `
            <table class="scheduler-table">
                <thead>
                    <tr>
                        <th>状态</th>
                        <th>描述</th>
                        <th>错误信息</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map(task => `
                        <tr>
                            <td><span class="status-icon failed">❌</span></td>
                            <td class="task-prompt">${this.truncate(task.prompt, 50)}</td>
                            <td class="error-text">${this.truncate(task.error, 30)}</td>
                            <td class="actions">
                                <button class="btn btn-small" onclick="Scheduler.showTaskDetail('${task.id}')">详情</button>
                                <button class="btn btn-small" onclick="Scheduler.retryTask('${task.id}')">重试</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    },

    /**
     * 渲染分页控件
     */
    renderPagination(containerId, data, onPageChange) {
        const container = document.getElementById(containerId);
        if (!container || data.total <= data.limit) {
            if (container) container.innerHTML = '';
            return;
        }

        const totalPages = Math.ceil(data.total / data.limit);
        const currentPage = data.page;

        let html = '<div class="pagination">';
        html += `<button class="pagination-btn" ${currentPage <= 1 ? 'disabled' : ''} onclick="Scheduler.loadCompleted(${currentPage - 1})">上一页</button>`;
        html += `<span class="pagination-info">第 ${currentPage} / ${totalPages} 页</span>`;
        html += `<button class="pagination-btn" ${currentPage >= totalPages ? 'disabled' : ''} onclick="Scheduler.loadCompleted(${currentPage + 1})">下一页</button>`;
        html += '</div>';

        container.innerHTML = html;
    },

    /**
     * 渲染列表加载错误
     */
    renderListError(containerId, message) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `<div class="error-state">${message}</div>`;
        }
    },

    // ===== 工具方法 =====

    /**
     * 获取状态文本
     */
    getStatusText(status) {
        const statusMap = {
            'pending': '待执行',
            'running': '运行中',
            'completed': '已完成',
            'failed': '失败',
            'cancelled': '已取消',
        };
        return statusMap[status] || status;
    },

    /**
     * 格式化日期时间
     */
    formatDateTime(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    },

    /**
     * 格式化持续时间
     */
    formatDuration(ms) {
        if (!ms) return '-';
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) {
            return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    },

    /**
     * 截断文本
     */
    truncate(text, maxLength) {
        if (!text) return '-';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    },

    /**
     * HTML 转义
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

/**
 * 调度器 API 封装
 */
const SchedulerAPI = {
    // 调度器控制
    getStatus: () => fetch('/api/scheduler/status').then(r => r.json()),
    start: () => fetch('/api/scheduler/start', { method: 'POST' }).then(r => r.json()),
    stop: () => fetch('/api/scheduler/stop', { method: 'POST' }).then(r => r.json()),

    // 任务队列
    getQueue: () => fetch('/api/tasks').then(r => r.json()),
    addTask: (task) => fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(task)
    }).then(r => r.json()),
    deleteTask: (id) => fetch(`/api/tasks/${id}`, { method: 'DELETE' }),
    clearQueue: () => fetch('/api/tasks/clear', { method: 'DELETE' }),

    // 定时任务
    getScheduled: () => fetch('/api/scheduled-tasks').then(r => r.json()),
    addScheduled: (task) => fetch('/api/scheduled-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(task)
    }).then(r => r.json()),
    updateScheduled: (id, updates) => fetch(`/api/scheduled-tasks/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
    }).then(r => r.json()),
    deleteScheduled: (id) => fetch(`/api/scheduled-tasks/${id}`, { method: 'DELETE' }),
    toggleScheduled: (id) => fetch(`/api/scheduled-tasks/${id}/toggle`, { method: 'POST' }),
    runScheduledNow: (id) => fetch(`/api/scheduled-tasks/${id}/run`, { method: 'POST' }),

    // 任务状态
    getRunning: () => fetch('/api/tasks/running').then(r => r.json()),
    getCompleted: (page = 1, limit = 20) => fetch(`/api/tasks/completed?page=${page}&limit=${limit}`).then(r => r.json()),
    getFailed: (page = 1, limit = 20) => fetch(`/api/tasks/failed?page=${page}&limit=${limit}`).then(r => r.json()),
    getTaskDetail: (id) => fetch(`/api/tasks/${id}`).then(r => r.json()),

    // Cron 验证
    validateCron: (expr) => fetch('/api/scheduler/validate-cron', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cron: expr })
    }).then(r => r.json()),
    getCronExamples: () => fetch('/api/scheduler/cron-examples').then(r => r.json()),
};

// 导出到全局命名空间
window.Scheduler = Scheduler;
window.SchedulerAPI = SchedulerAPI;
