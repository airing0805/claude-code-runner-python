/**
 * 调度器 API 模块
 * 模块拆分 - v7.0.10
 * 封装调度器相关的 API 调用
 */

const SchedulerAPI = {
    // ===== 调度器控制 =====

    /**
     * 获取调度器状态
     */
    getStatus() {
        return this._fetch('/api/scheduler/status');
    },

    /**
     * 启动调度器
     */
    async start() {
        const response = await this._fetch('/api/scheduler/start', { method: 'POST' });
        return response;
    },

    /**
     * 停止调度器
     */
    async stop() {
        const response = await this._fetch('/api/scheduler/stop', { method: 'POST' });
        return response;
    },

    // ===== 任务队列 =====

    /**
     * 获取任务队列
     */
    getQueue() {
        return this._fetch('/api/scheduler/tasks');
    },

    /**
     * 添加任务到队列
     */
    async addTask(task) {
        return this._fetch('/api/scheduler/tasks', {
            method: 'POST',
            body: JSON.stringify(task),
        });
    },

    /**
     * 删除任务
     */
    async deleteTask(taskId) {
        return this._fetch(`/api/scheduler/tasks/${taskId}`, {
            method: 'DELETE',
        });
    },

    /**
     * 清空任务队列
     */
    async clearQueue() {
        return this._fetch('/api/scheduler/tasks/clear', {
            method: 'DELETE',
        });
    },

    /**
     * 批量删除任务
     */
    async batchDeleteTasks(taskIds) {
        return this._fetch('/api/scheduler/tasks/batch', {
            method: 'POST',
            body: JSON.stringify({ task_ids: taskIds, action: 'delete' }),
        });
    },

    // ===== 定时任务 =====

    /**
     * 获取定时任务列表
     */
    getScheduled() {
        return this._fetch('/api/scheduler/scheduled-tasks');
    },

    /**
     * 创建定时任务
     */
    async addScheduled(task) {
        return this._fetch('/api/scheduler/scheduled-tasks', {
            method: 'POST',
            body: JSON.stringify(task),
        });
    },

    /**
     * 更新定时任务
     */
    async updateScheduled(taskId, updates) {
        return this._fetch(`/api/scheduler/scheduled-tasks/${taskId}`, {
            method: 'PATCH',
            body: JSON.stringify(updates),
        });
    },

    /**
     * 删除定时任务
     */
    async deleteScheduled(taskId) {
        return this._fetch(`/api/scheduler/scheduled-tasks/${taskId}`, {
            method: 'DELETE',
        });
    },

    /**
     * 切换定时任务启用状态
     */
    async toggleScheduled(taskId) {
        return this._fetch(`/api/scheduler/scheduled-tasks/${taskId}/toggle`, {
            method: 'POST',
        });
    },

    /**
     * 立即执行定时任务
     */
    async runScheduledNow(taskId) {
        return this._fetch(`/api/scheduler/scheduled-tasks/${taskId}/run`, {
            method: 'POST',
        });
    },

    // ===== 任务状态 =====

    /**
     * 获取运行中任务
     */
    getRunning() {
        return this._fetch('/api/scheduler/tasks/running');
    },

    /**
     * 获取已完成任务
     */
    getCompleted(page = 1, limit = 20) {
        const params = new URLSearchParams({ page, limit });
        return this._fetch(`/api/scheduler/tasks/completed?${params}`);
    },

    /**
     * 获取失败任务
     */
    getFailed(page = 1, limit = 20) {
        const params = new URLSearchParams({ page, limit });
        return this._fetch(`/api/scheduler/tasks/failed?${params}`);
    },

    /**
     * 获取任务详情
     */
    getTaskDetail(taskId) {
        return this._fetch(`/api/scheduler/tasks/${taskId}`);
    },

    /**
     * 取消任务
     */
    async cancelTask(taskId) {
        return this._fetch(`/api/scheduler/tasks/${taskId}/cancel`, {
            method: 'POST',
        });
    },

    // ===== Cron 验证 =====

    /**
     * 验证 Cron 表达式
     */
    async validateCron(expression) {
        return this._fetch('/api/scheduler/validate-cron', {
            method: 'POST',
            body: JSON.stringify({ cron: expression }),
        });
    },

    /**
     * 获取 Cron 示例
     */
    getCronExamples() {
        return this._fetch('/api/scheduler/cron-examples');
    },

    // ===== 辅助功能 =====

    /**
     * 获取项目列表（工作空间）
     */
    getProjects() {
        return this._fetch('/api/projects');
    },

    /**
     * 私有方法: 统一的 fetch 封装
     */
    async _fetch(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers,
            },
        };

        const response = await fetch(url, mergedOptions);

        // 处理非成功响应
        if (!response.ok) {
            let errorMessage = `请求失败: ${response.status}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorData.detail?.error || errorMessage;
            } catch {
                // 无法解析错误响应，使用默认消息
            }
            throw new Error(errorMessage);
        }

        // 处理空响应
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        }

        return response;
    },
};

// 导出到全局命名空间（兼容非模块脚本）
window.SchedulerAPI = SchedulerAPI;

// ES6 模块导出（用于模块导入）
export { SchedulerAPI };
