/**
 * 添加任务对话框模块
 * 模块拆分 - v7.0.10
 * 提供添加任务到队列的功能
 */

import { SchedulerUtils } from '../utils.js';
import { SchedulerState } from '../state.js';

/**
 * 添加任务对话框
 */
export const AddTaskDialog = {
    /**
     * 显示对话框
     */
    show() {
        // 重置表单
        document.getElementById('task-prompt').value = '';
        document.getElementById('task-working-dir').value = '';
        document.getElementById('task-timeout').value = '600';
        document.getElementById('task-auto-approve').checked = false;

        // 重置工具选择
        this.resetToolSelection();

        // 加载工作空间列表
        this.loadWorkspaceList();

        document.getElementById('add-task-dialog').classList.add('active');

        // 聚焦到文本框
        setTimeout(() => {
            document.getElementById('task-prompt').focus();
        }, 100);
    },

    /**
     * 隐藏对话框
     */
    hide() {
        document.getElementById('add-task-dialog').classList.remove('active');
    },

    /**
     * 重置工具选择
     */
    resetToolSelection() {
        const dropdown = document.getElementById('task-tools-dropdown');
        if (!dropdown) return;

        const checkboxes = dropdown.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach((cb, i) => {
            if (window.AVAILABLE_TOOLS && window.AVAILABLE_TOOLS[i]) {
                cb.checked = window.AVAILABLE_TOOLS[i].selected || false;
            }
        });

        this.updateToolsSelection();
    },

    /**
     * 更新工具选择状态
     */
    updateToolsSelection() {
        const dropdown = document.getElementById('task-tools-dropdown');
        const btn = document.getElementById('task-tools-select-btn');
        const input = document.getElementById('task-tools');

        if (!dropdown || !btn || !input) return;

        const checkboxes = dropdown.querySelectorAll('input[type="checkbox"]:checked');
        const count = checkboxes.length;

        const selectedText = btn.querySelector('.selected-text');
        const selectedCount = btn.querySelector('.selected-count');

        if (!selectedText || !selectedCount) {
            console.warn('[AddTaskDialog] 工具选择按钮结构不完整');
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
            const data = await response.json ? await response.json() : response;
            const projects = data.projects || [];

            const listEl = document.getElementById('task-workspace-list');
            if (!listEl) return;

            if (!projects.length) {
                listEl.innerHTML = '<span class="empty-text">暂无项目</span>';
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
                    const inputEl = document.getElementById('task-working-dir');
                    if (inputEl) {
                        inputEl.value = path === '默认工作空间' ? '' : path;
                    }
                });
            });
        } catch (error) {
            console.error('[AddTaskDialog] 加载工作空间列表失败:', error);
        }
    },

    /**
     * 提交任务
     */
    async submit() {
        const prompt = document.getElementById('task-prompt').value.trim();
        if (!prompt) {
            SchedulerUtils.showNotification('请输入任务描述', 'error');
            return;
        }

        // 获取工具列表并转为数组
        const toolsValue = document.getElementById('task-tools').value;
        const allowedTools = toolsValue ? toolsValue.split(',').map(t => t.trim()).filter(t => t) : null;

        const task = {
            prompt,
            workspace: document.getElementById('task-working-dir').value.trim() || null,
            timeout: parseInt(document.getElementById('task-timeout').value) * 1000,
            allowed_tools: allowedTools,
            auto_approve: document.getElementById('task-auto-approve').checked,
        };

        try {
            await window.SchedulerAPI.addTask(task);
            SchedulerUtils.showNotification('任务已添加到队列', 'success');
            this.hide();

            // 刷新队列
            if (window.Scheduler && typeof window.Scheduler.loadQueue === 'function') {
                await window.Scheduler.loadQueue();
            }
        } catch (error) {
            SchedulerUtils.showNotification('添加失败: ' + error.message, 'error');
        }
    },

    /**
     * 绑定对话框事件
     */
    bindEvents() {
        // 关闭按钮
        const closeBtn = document.getElementById('close-add-task-dialog');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }

        const cancelBtn = document.getElementById('cancel-add-task-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hide());
        }

        const confirmBtn = document.getElementById('confirm-add-task-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.submit());
        }

        // 工具选择下拉框
        const toolsBtn = document.getElementById('task-tools-select-btn');
        const toolsDropdown = document.getElementById('task-tools-dropdown');
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
        }

        // 点击对话框外部关闭
        const dialog = document.getElementById('add-task-dialog');
        if (dialog) {
            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) {
                    this.hide();
                }
            });
        }

        // 点击外部关闭下拉框
        document.addEventListener('click', () => {
            if (toolsDropdown) {
                toolsDropdown.classList.remove('show');
            }
        });
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
    AddTaskDialog.bindEvents();
});

// 导出到全局命名空间
window.AddTaskDialog = AddTaskDialog;
