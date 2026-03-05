/**
 * 任务详情对话框模块
 * 模块拆分 - v7.0.10
 * 提供任务详情展示功能
 */

import { SchedulerUtils } from '../utils.js';
import { SchedulerState } from '../state.js';

/**
 * 任务详情对话框
 */
export const TaskDetailDialog = {
    /**
     * 显示任务详情
     */
    async show(taskId) {
        try {
            const response = await window.SchedulerAPI.getTaskDetail(taskId);
            const task = response.data || response;
            this.render(task);
            document.getElementById('task-detail-dialog').classList.add('active');
        } catch (error) {
            SchedulerUtils.showNotification('加载详情失败: ' + error.message, 'error');
        }
    },

    /**
     * 隐藏对话框
     */
    hide() {
        document.getElementById('task-detail-dialog').classList.remove('active');
    },

    /**
     * 渲染任务详情
     */
    render(task) {
        // 基本信息
        document.getElementById('detail-task-prompt').textContent = task.prompt || '-';

        // 状态
        const statusEl = document.getElementById('detail-task-status');
        statusEl.textContent = SchedulerUtils.getStatusText(task.status);
        statusEl.className = `status-value status-${task.status}`;

        // 时间信息
        document.getElementById('detail-task-started').textContent = task.started_at
            ? SchedulerUtils.formatDateTime(task.started_at)
            : '-';
        document.getElementById('detail-task-ended').textContent = task.finished_at
            ? SchedulerUtils.formatDateTime(task.finished_at)
            : '-';
        document.getElementById('detail-task-duration').textContent = task.duration_ms
            ? SchedulerUtils.formatDuration(task.duration_ms)
            : '-';

        // 工作目录
        document.getElementById('detail-task-working-dir').textContent = task.workspace || '默认工作空间';

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
            filesEl.innerHTML = task.files_changed.map(f =>
                `<div class="file-item" title="${SchedulerUtils.escapeHtml(f)}">${SchedulerUtils.escapeHtml(f)}</div>`
            ).join('');
        } else {
            filesEl.innerHTML = '<span class="empty-text">无</span>';
        }

        // 输出日志
        const outputEl = document.getElementById('detail-task-output');
        if (task.output) {
            outputEl.innerHTML = `<pre class="task-output-pre">${SchedulerUtils.escapeHtml(task.output)}</pre>`;
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

        // 存储当前任务ID以供其他操作使用
        this.currentTaskId = task.id;
        this.currentTask = task;
    },

    /**
     * 复制任务日志
     */
    copyLog() {
        const outputEl = document.getElementById('detail-task-output');
        const text = outputEl.textContent;

        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                SchedulerUtils.showNotification('日志已复制', 'success');
            }).catch(() => {
                SchedulerUtils.showNotification('复制失败', 'error');
            });
        } else {
            // 回退方案
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                SchedulerUtils.showNotification('日志已复制', 'success');
            } catch {
                SchedulerUtils.showNotification('复制失败', 'error');
            }
            document.body.removeChild(textarea);
        }
    },

    /**
     * 重试当前任务
     */
    async retry() {
        if (!this.currentTask) return;

        const task = this.currentTask;
        const allowedTools = task.allowed_tools
            ? (Array.isArray(task.allowed_tools) ? task.allowed_tools : task.allowed_tools.split(','))
            : null;

        try {
            await window.SchedulerAPI.addTask({
                prompt: task.prompt,
                workspace: task.workspace,
                timeout: task.timeout,
                allowed_tools: allowedTools,
                auto_approve: task.auto_approve,
            });
            SchedulerUtils.showNotification('任务已重新加入队列', 'success');
            this.hide();

            // 刷新队列
            if (window.Scheduler && typeof window.Scheduler.loadQueue === 'function') {
                await window.Scheduler.loadQueue();
            }
        } catch (error) {
            SchedulerUtils.showNotification('重试失败: ' + error.message, 'error');
        }
    },

    /**
     * 绑定对话框事件
     */
    bindEvents() {
        // 关闭按钮
        const closeBtn = document.getElementById('close-task-detail-dialog');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }

        const closeFooterBtn = document.getElementById('close-detail-btn');
        if (closeFooterBtn) {
            closeFooterBtn.addEventListener('click', () => this.hide());
        }

        // 复制日志按钮
        const copyLogBtn = document.getElementById('copy-task-log-btn');
        if (copyLogBtn) {
            copyLogBtn.addEventListener('click', () => this.copyLog());
        }

        // 输出日志折叠
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

        // 点击对话框外部关闭
        const dialog = document.getElementById('task-detail-dialog');
        if (dialog) {
            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) {
                    this.hide();
                }
            });
        }
    },
};

// 初始化时自动绑定事件
document.addEventListener('DOMContentLoaded', () => {
    TaskDetailDialog.bindEvents();
});

// 导出到全局命名空间
window.TaskDetailDialog = TaskDetailDialog;
