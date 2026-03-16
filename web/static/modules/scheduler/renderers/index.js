/**
 * 渲染器模块
 * 模块拆分 - v7.0.10
 * 提供任务列表渲染功能
 */

import { SchedulerState } from '../state.js';
import { SchedulerUtils } from '../utils.js';

/**
 * 调度器渲染器
 */
export const SchedulerRenderers = {
    /**
     * 渲染任务队列列表
     */
    renderQueueList() {
        const container = document.getElementById('scheduler-queue-list');
        if (!container) {
            console.error('[Scheduler] 找不到 scheduler-queue-list 容器');
            return;
        }

        const items = SchedulerState.getFilteredQueue();

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">队列为空</div>';
            return;
        }

        const { sortBy, sortOrder } = SchedulerState;
        const headers = [
            { key: 'prompt', label: '描述', sortable: true },
            { key: 'source', label: '来源', sortable: false },
            { key: 'workspace', label: '工作空间', sortable: true },
            { key: 'created_at', label: '创建时间', sortable: true },
            { key: 'actions', label: '操作', sortable: false },
        ];

        container.innerHTML = `
            <table class="scheduler-table">
                <thead>
                    <tr>
                        ${headers.map(h => `
                            <th class="${h.sortable ? 'sortable' : ''}"
                                data-sort-key="${h.key}"
                                data-sort-order="${sortOrder}"
                            >
                                ${h.sortable ? `
                                    <span class="sort-icon">${sortBy === h.key ? (sortOrder === 'asc' ? '▲' : '▼') : ''}</span>
                                ` : ''}
                                ${h.label}
                            </th>
                        `).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${items.map(task => `
                        <tr>
                            <td class="task-prompt">${SchedulerUtils.truncate(task.prompt, 50)}</td>
                            <td>${SchedulerUtils.getSourceBadge(task.source, task.scheduled_name)}</td>
                            <td>${task.workspace || '默认工作空间'}</td>
                            <td>${SchedulerUtils.formatDateTime(task.created_at)}</td>
                            <td class="actions">
                                <button class="btn btn-small btn-danger" onclick="window.Scheduler.deleteTask('${task.id}')">🗑 删除</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        // 绑定排序事件
        this.bindTableSortEvents(container);
    },

    /**
     * 渲染定时任务列表
     */
    renderScheduledList() {
        const container = document.getElementById('scheduler-scheduled-list');
        if (!container) {
            console.error('[Scheduler] 找不到 scheduler-scheduled-list 容器');
            return;
        }

        const items = SchedulerState.getFilteredScheduled();

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无定时任务</div>';
            return;
        }

        const { sortBy, sortOrder } = SchedulerState;
        const headers = [
            { key: 'name', label: '名称', sortable: true },
            { key: 'workspace', label: '工作空间', sortable: true },
            { key: 'cron', label: 'Cron', sortable: false },
            { key: 'next_run', label: '下次运行', sortable: true },
            { key: 'status', label: '状态', sortable: false },
            { key: 'actions', label: '操作', sortable: false },
        ];

        container.innerHTML = `
        <div class="scheduled-toolbar">
            <input type="text"
                class="scheduled-search-input"
                id="scheduled-search-input"
                placeholder="搜索任务名称或描述..."
                value="${SchedulerState.filterText}">
            <div class="scheduled-filters">
                <select id="scheduled-status-filter" class="filter-select">
                    <option value="">全部状态</option>
                    <option value="enabled" ${SchedulerState.filterStatus === 'enabled' ? 'selected' : ''}>启用</option>
                    <option value="disabled" ${SchedulerState.filterStatus === 'disabled' ? 'selected' : ''}>禁用</option>
                </select>
            </div>
        </div>
        <table class="scheduler-table">
            <thead>
                <tr>
                    ${headers.map(h => `
                        <th class="${h.sortable ? 'sortable' : ''}"
                            data-sort-key="${h.key}"
                            data-sort-order="${sortOrder}"
                        >
                            ${h.sortable ? `
                                <span class="sort-icon">${sortBy === h.key ? (sortOrder === 'asc' ? '▲' : '▼') : ''}</span>
                            ` : ''}
                            ${h.label}
                        </th>
                    `).join('')}
                </tr>
            </thead>
            <tbody>
                ${items.map(task => `
                    <tr>
                        <td>${SchedulerUtils.escapeHtml(task.name)}</td>
                        <td><span class="workspace-badge">${task.workspace === '.' ? '默认工作空间' : SchedulerUtils.escapeHtml(task.workspace)}</span></td>
                        <td><code>${task.cron}</code></td>
                        <td>${task.next_run ? SchedulerUtils.formatDateTime(task.next_run) : '-'}</td>
                        <td>
                            <span class="status-badge ${task.enabled ? 'enabled' : 'disabled'}">
                                ${task.enabled ? '✓ 启用' : '✗ 禁用'}
                            </span>
                        </td>
                        <td class="actions">
                            <button class="btn btn-small" onclick="window.Scheduler.toggleScheduled('${task.id}')">
                                ${task.enabled ? '禁用' : '启用'}
                            </button>
                            <button class="btn btn-small" onclick="window.Scheduler.runScheduledNow('${task.id}')">▶ 执行</button>
                            <button class="btn btn-small" onclick="window.Scheduler.showAddScheduledDialog(SchedulerState.scheduled.find(t => t.id === '${task.id}'))">✎ 编辑</button>
                            <button class="btn btn-small btn-danger" onclick="window.Scheduler.deleteScheduled('${task.id}')">🗑</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        `;

        // 绑定排序和筛选事件
        this.bindTableSortEvents(container);
        this.bindFilterEvents();
    },

    /**
     * 渲染运行中任务列表
     */
    renderRunningList() {
        const container = document.getElementById('scheduler-running-list');
        if (!container) {
            console.error('[Scheduler] 找不到 scheduler-running-list 容器');
            return;
        }

        const items = SchedulerState.getSortedRunning();

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无运行中任务</div>';
            return;
        }

        container.innerHTML = `
            <table class="scheduler-table">
                <thead>
                    <tr>
                        <th>状态</th>
                        <th class="sortable" data-sort-key="prompt" data-sort-order="${SchedulerState.sortOrder}">
                            <span class="sort-icon">${SchedulerState.sortBy === 'prompt' ? (SchedulerState.sortOrder === 'asc' ? '▲' : '▼') : ''}</span>
                            描述
                        </th>
                        <th class="sortable" data-sort-key="started_at" data-sort-order="${SchedulerState.sortOrder}">
                            <span class="sort-icon">${SchedulerState.sortBy === 'started_at' ? (SchedulerState.sortOrder === 'asc' ? '▲' : '▼') : ''}</span>
                            运行时长
                        </th>
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
                            <td class="task-prompt">${SchedulerUtils.truncate(task.prompt, 50)}</td>
                            <td class="running-duration" data-started-at="${startedAt}">${SchedulerUtils.formatDuration(elapsed)}</td>
                            <td class="actions">
                                <button class="btn btn-small" onclick="window.Scheduler.showTaskDetail('${task.id}')">详情</button>
                            </td>
                        </tr>
                    `}).join('')}
                </tbody>
            </table>
        `;

        this.bindTableSortEvents(container);
    },

    /**
     * 渲染已完成任务列表
     */
    renderCompletedList() {
        const container = document.getElementById('scheduler-completed-list');
        if (!container) {
            console.error('[Scheduler] 找不到 scheduler-completed-list 容器');
            return;
        }

        const items = SchedulerState.getSortedCompleted();

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无已完成任务</div>';
            return;
        }

        container.innerHTML = `
            <table class="scheduler-table">
                <thead>
                    <tr>
                        <th>状态</th>
                        <th class="sortable" data-sort-key="prompt" data-sort-order="${SchedulerState.sortOrder}">
                            <span class="sort-icon">${SchedulerState.sortBy === 'prompt' ? (SchedulerState.sortOrder === 'asc' ? '▲' : '▼') : ''}</span>
                            描述
                        </th>
                        <th>来源</th>
                        <th class="sortable" data-sort-key="finished_at" data-sort-order="${SchedulerState.sortOrder}">
                            <span class="sort-icon">${SchedulerState.sortBy === 'finished_at' ? (SchedulerState.sortOrder === 'asc' ? '▲' : '▼') : ''}</span>
                            完成时间
                        </th>
                        <th class="sortable" data-sort-key="duration_ms" data-sort-order="${SchedulerState.sortOrder}">
                            <span class="sort-icon">${SchedulerState.sortBy === 'duration_ms' ? (SchedulerState.sortOrder === 'asc' ? '▲' : '▼') : ''}</span>
                            耗时
                        </th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map(task => `
                        <tr>
                            <td><span class="status-icon completed">✅</span></td>
                            <td class="task-prompt">${SchedulerUtils.truncate(task.prompt, 50)}</td>
                            <td>${SchedulerUtils.getSourceBadge(task.source, task.scheduled_name)}</td>
                            <td>${SchedulerUtils.formatDateTime(task.finished_at)}</td>
                            <td>${SchedulerUtils.formatDuration(task.duration_ms)}</td>
                            <td class="actions">
                                <button class="btn btn-small" onclick="window.Scheduler.showTaskDetail('${task.id}')">详情</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        this.bindTableSortEvents(container);
    },

    /**
     * 渲染失败任务列表
     */
    renderFailedList() {
        const container = document.getElementById('scheduler-failed-list');
        if (!container) {
            console.error('[Scheduler] 找不到 scheduler-failed-list 容器');
            return;
        }

        const items = SchedulerState.getSortedFailed();

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无失败任务</div>';
            return;
        }

        container.innerHTML = `
            <table class="scheduler-table">
                <thead>
                    <tr>
                        <th>状态</th>
                        <th class="sortable" data-sort-key="prompt" data-sort-order="${SchedulerState.sortOrder}">
                            <span class="sort-icon">${SchedulerState.sortBy === 'prompt' ? (SchedulerState.sortOrder === 'asc' ? '▲' : '▼') : ''}</span>
                            描述
                        </th>
                        <th>来源</th>
                        <th class="sortable" data-sort-key="error" data-sort-order="${SchedulerState.sortOrder}">
                            <span class="sort-icon">${SchedulerState.sortBy === 'error' ? (SchedulerState.sortOrder === 'asc' ? '▲' : '▼') : ''}</span>
                            错误信息
                        </th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map(task => `
                        <tr>
                            <td><span class="status-icon failed">❌</span></td>
                            <td class="task-prompt">${SchedulerUtils.truncate(task.prompt, 50)}</td>
                            <td>${SchedulerUtils.getSourceBadge(task.source, task.scheduled_name)}</td>
                            <td class="error-text">${SchedulerUtils.truncate(task.error, 30)}</td>
                            <td class="actions">
                                <button class="btn btn-small" onclick="window.Scheduler.showTaskDetail('${task.id}')">详情</button>
                                <button class="btn btn-small" onclick="window.Scheduler.retryTask('${task.id}')">重试</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        this.bindTableSortEvents(container);
    },

    /**
     * 渲染分页控件
     */
    renderPagination(containerId, data, loadFunction) {
        const container = document.getElementById(containerId);
        if (!container || data.total <= data.limit) {
            if (container) container.innerHTML = '';
            return;
        }

        const totalPages = Math.ceil(data.total / data.limit);
        const currentPage = data.page;

        let html = '<div class="pagination">';
        html += `<button class="pagination-btn" ${currentPage <= 1 ? 'disabled' : ''} onclick="${loadFunction}(${currentPage - 1})">上一页</button>`;
        html += `<span class="pagination-info">第 ${currentPage} / ${totalPages} 页 (共 ${data.total} 条)</span>`;
        html += `<button class="pagination-btn" ${currentPage >= totalPages ? 'disabled' : ''} onclick="${loadFunction}(${currentPage + 1})">下一页</button>`;
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

    /**
     * 绑定表格排序事件
     */
    bindTableSortEvents(container) {
        container.querySelectorAll('.scheduler-table th.sortable').forEach(th => {
            th.addEventListener('click', () => {
                const sortBy = th.dataset.sortKey;
                const currentOrder = th.dataset.sortOrder;
                const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';

                // 更新状态
                SchedulerState.setSorting(sortBy, newOrder);

                // 触发重新渲染
                if (window.Scheduler && typeof window.Scheduler.refreshCurrentTab === 'function') {
                    window.Scheduler.refreshCurrentTab();
                }
            });
        });
    },

    /**
     * 绑定筛选事件
     */
    bindFilterEvents() {
        const searchInput = document.getElementById('scheduled-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', SchedulerUtils.debounce((e) => {
                SchedulerState.setFilter(e.target.value);
                this.renderScheduledList();
            }, 300));
        }

        const statusFilter = document.getElementById('scheduled-status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                SchedulerState.filterStatus = e.target.value;
                this.renderScheduledList();
            });
        }
    },
};

// 导出到全局命名空间
window.SchedulerRenderers = SchedulerRenderers;
