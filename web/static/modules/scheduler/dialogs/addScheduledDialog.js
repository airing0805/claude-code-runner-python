/**
 * 添加定时任务对话框模块
 * 模块拆分 - v7.0.10
 * 提供创建和编辑定时任务的功能
 */

import { SchedulerUtils } from '../utils.js';
import { SchedulerState } from '../state.js';

/**
 * 添加定时任务对话框
 */
export const AddScheduledDialog = {
    /**
     * 显示对话框
     * @param {Object|null} task - 编辑时传入现有任务，创建时传 null
     */
    show(task = null) {
        SchedulerState.editingScheduledId = task ? task.id : null;

        // 更新对话框标题
        document.getElementById('scheduled-dialog-title').textContent =
            task ? '编辑定时任务' : '添加定时任务';

        // 填充表单
        document.getElementById('scheduled-task-id').value = task?.id || '';
        document.getElementById('scheduled-name').value = task?.name || '';
        document.getElementById('scheduled-cron').value = task?.cron || '';
        document.getElementById('scheduled-prompt').value = task?.prompt || '';
        document.getElementById('scheduled-working-dir').value = task?.workspace || '';
        document.getElementById('scheduled-timeout').value = (task?.timeout || 600000) / 1000;
        document.getElementById('scheduled-auto-approve').checked = task?.auto_approve || false;
        document.getElementById('scheduled-enabled').checked = task?.enabled !== false;

        // 设置工具选择
        this.setToolSelection(task);

        // 加载工作空间列表
        this.loadWorkspaceList();

        // 验证 Cron 表达式
        if (task?.cron) {
            this.validateCron(task.cron);
        } else {
            document.getElementById('cron-preview').style.display = 'none';
            document.getElementById('cron-error').style.display = 'none';
        }

        document.getElementById('add-scheduled-dialog').classList.add('active');

        // 聚焦到名称输入框
        setTimeout(() => {
            document.getElementById('scheduled-name').focus();
        }, 100);
    },

    /**
     * 隐藏对话框
     */
    hide() {
        document.getElementById('add-scheduled-dialog').classList.remove('active');
        SchedulerState.editingScheduledId = null;
    },

    /**
     * 设置工具选择
     */
    setToolSelection(task) {
        const dropdown = document.getElementById('scheduled-tools-dropdown');
        if (!dropdown) return;

        let tools;
        if (task?.allowed_tools) {
            tools = Array.isArray(task.allowed_tools) ? task.allowed_tools : task.allowed_tools.split(',');
        } else if (window.AVAILABLE_TOOLS) {
            tools = window.AVAILABLE_TOOLS.filter(t => t.selected).map(t => t.name);
        } else {
            tools = [];
        }

        const checkboxes = dropdown.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => {
            cb.checked = tools.includes(cb.value);
        });

        this.updateToolsSelection();
    },

    /**
     * 更新工具选择状态
     */
    updateToolsSelection() {
        const dropdown = document.getElementById('scheduled-tools-dropdown');
        const btn = document.getElementById('scheduled-tools-select-btn');
        const input = document.getElementById('scheduled-tools');

        if (!dropdown || !btn || !input) return;

        const checkboxes = dropdown.querySelectorAll('input[type="checkbox"]:checked');
        const count = checkboxes.length;

        const selectedText = btn.querySelector('.selected-text');
        const selectedCount = btn.querySelector('.selected-count');

        if (!selectedText || !selectedCount) {
            console.warn('[AddScheduledDialog] 工具选择按钮结构不完整');
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
        input.value = tools.join(',');
    },

    /**
     * 加载工作空间列表
     */
    async loadWorkspaceList() {
        try {
            const response = await window.SchedulerAPI.getProjects();
            const data = response.json ? await response.json() : response;
            const projects = data.projects || [];

            const listEl = document.getElementById('scheduled-workspace-list');
            if (!listEl || !projects.length) {
                if (listEl) listEl.innerHTML = '<span class="empty-text">暂无项目</span>';
                return;
            }

            listEl.innerHTML = projects.map(project => {
                const isDefault = project.path === '.' || project.path === '' || project.path === '默认工作空间';
                return `
                    <div class="workspace-item" data-path="${SchedulerUtils.escapeHtml(project.path)}">
                        <div class="workspace-item-info">
                            <span class="workspace-item-name">${SchedulerUtils.escapeHtml(project.name || project.path)}</span>
                            <span class="workspace-item-path">${project.path}</span>
                            ${isDefault ? '<span class="workspace-item-default">(默认)</span>' : ''}
                        </div>
                    </div>
                `;
            }).join('');

            // 点击工作空间项目自动填入输入框
            listEl.querySelectorAll('.workspace-item').forEach(item => {
                item.addEventListener('click', () => {
                    const path = item.dataset.path;
                    const inputEl = document.getElementById('scheduled-working-dir');
                    if (inputEl) {
                        inputEl.value = path === '默认工作空间' ? '' : path;
                    }
                });
            });
        } catch (error) {
            console.error('[AddScheduledDialog] 加载工作空间列表失败:', error);
        }
    },

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
            const result = await window.SchedulerAPI.validateCron(expression);
            const data = result.data || result;

            if (data.valid) {
                preview.style.display = 'flex';
                error.style.display = 'none';
                nextRun.textContent = data.next_run
                    ? SchedulerUtils.formatDateTime(data.next_run)
                    : '-';
                return true;
            } else {
                preview.style.display = 'none';
                error.style.display = 'block';
                error.textContent = data.error || '无效的 Cron 表达式';
                return false;
            }
        } catch (err) {
            preview.style.display = 'none';
            error.style.display = 'block';
            error.textContent = err.message || '无效的 Cron 表达式';
            return false;
        }
    },

    /**
     * 保存定时任务
     */
    async save() {
        const name = document.getElementById('scheduled-name').value.trim();
        const cronExpression = document.getElementById('scheduled-cron').value.trim();
        const prompt = document.getElementById('scheduled-prompt').value.trim();

        if (!name) {
            SchedulerUtils.showNotification('请输入任务名称', 'error');
            return;
        }
        if (!cronExpression) {
            SchedulerUtils.showNotification('请输入 Cron 表达式', 'error');
            return;
        }
        if (!prompt) {
            SchedulerUtils.showNotification('请输入任务描述', 'error');
            return;
        }

        // 保存前验证 Cron 表达式
        const cronValid = await this.validateCron(cronExpression);
        if (!cronValid) {
            SchedulerUtils.showNotification('请先修正 Cron 表达式错误', 'error');
            return;
        }

        // 获取工具列表并转为数组
        const toolsValue = document.getElementById('scheduled-tools').value;
        const allowedTools = toolsValue ? toolsValue.split(',').map(t => t.trim()).filter(t => t) : null;

        const task = {
            name,
            cron: cronExpression,
            prompt,
            workspace: document.getElementById('scheduled-working-dir').value.trim() || null,
            timeout: parseInt(document.getElementById('scheduled-timeout').value) * 1000,
            allowed_tools: allowedTools,
            auto_approve: document.getElementById('scheduled-auto-approve').checked,
            enabled: document.getElementById('scheduled-enabled').checked,
        };

        try {
            if (SchedulerState.editingScheduledId) {
                await window.SchedulerAPI.updateScheduled(SchedulerState.editingScheduledId, task);
                SchedulerUtils.showNotification('定时任务已更新', 'success');
            } else {
                await window.SchedulerAPI.addScheduled(task);
                SchedulerUtils.showNotification('定时任务已创建', 'success');
            }
            this.hide();

            // 刷新定时任务列表
            if (window.Scheduler && typeof window.Scheduler.loadScheduled === 'function') {
                await window.Scheduler.loadScheduled();
            }
        } catch (error) {
            SchedulerUtils.showNotification('保存失败: ' + error.message, 'error');
        }
    },

    /**
     * 绑定对话框事件
     */
    bindEvents() {
        // 关闭按钮
        const closeBtn = document.getElementById('close-add-scheduled-dialog');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }

        const cancelBtn = document.getElementById('cancel-add-scheduled-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hide());
        }

        const confirmBtn = document.getElementById('confirm-add-scheduled-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.save());
        }

        // Cron 表达式输入
        const cronInput = document.getElementById('scheduled-cron');
        if (cronInput) {
            cronInput.addEventListener('input', SchedulerUtils.debounce((e) => {
                this.validateCron(e.target.value);
            }, 300));
        }

        // Cron 帮助按钮
        const cronHelpBtn = document.getElementById('cron-help-btn');
        if (cronHelpBtn) {
            cronHelpBtn.addEventListener('click', () => {
                if (window.CronHelperDialog) {
                    window.CronHelperDialog.show();
                }
            });
        }

        // 工具选择下拉框
        const toolsBtn = document.getElementById('scheduled-tools-select-btn');
        const toolsDropdown = document.getElementById('scheduled-tools-dropdown');
        if (toolsBtn && toolsDropdown) {
            // 渲染工具列表
            this.renderToolsDropdown(toolsDropdown);

            // 切换下拉框
            toolsBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toolsDropdown.classList.toggle('show');
            });

            // 选择工具
            toolsDropdown.addEventListener('change', () => {
                this.updateToolsSelection();
            });

            // 点击外部关闭
            document.addEventListener('click', () => {
                toolsDropdown.classList.remove('show');
            });
        }

        // 点击对话框外部关闭
        const dialog = document.getElementById('add-scheduled-dialog');
        if (dialog) {
            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) {
                    this.hide();
                }
            });
        }
    },

    /**
     * 渲染工具下拉框
     */
    renderToolsDropdown(dropdown) {
        if (!window.AVAILABLE_TOOLS) {
            dropdown.innerHTML = '<div class="empty-text">暂无可用工具</div>';
            return;
        }

        dropdown.innerHTML = window.AVAILABLE_TOOLS.map(tool => `
            <label class="tools-option">
                <input type="checkbox" value="${tool.name}" ${tool.selected ? 'checked' : ''}>
                <span>${tool.name}</span>
                <span class="tools-option-desc">${tool.description || ''}</span>
            </label>
        `).join('');
    },
};

// 初始化时自动绑定事件
document.addEventListener('DOMContentLoaded', () => {
    AddScheduledDialog.bindEvents();
});

// 导出到全局命名空间
window.AddScheduledDialog = AddScheduledDialog;
