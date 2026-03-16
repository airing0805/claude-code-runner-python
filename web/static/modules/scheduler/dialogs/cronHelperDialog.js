/**
 * Cron 帮助对话框模块
 * 模块拆分 - v7.0.10
 * 提供 Cron 表达式的帮助和示例
 */

import { SchedulerUtils } from '../utils.js';

/**
 * Cron 帮助对话框
 */
export const CronHelperDialog = {
    // Cron 示例
    examples: [
        { expression: '*/5 * * * *', description: '每 5 分钟' },
        { expression: '0 * * * *', description: '每小时' },
        { expression: '0 */2 * * *', description: '每 2 小时' },
        { expression: '0 9 * * *', description: '每天上午 9:00' },
        { expression: '0 18 * * *', description: '每天下午 6:00' },
        { expression: '0 9,18 * * *', description: '每天上午 9:00 和下午 6:00' },
        { expression: '0 9 * * 1', description: '每周一上午 9:00' },
        { expression: '0 9 * * 1-5', description: '每周一到周五上午 9:00' },
        { expression: '0 0 * * *', description: '每天午夜 0:00' },
        { expression: '0 9 1 * *', description: '每月 1 号上午 9:00' },
    ],

    /**
     * 显示 Cron 帮助对话框
     */
    show() {
        // 渲染示例列表
        const examplesList = document.getElementById('cron-examples-list');
        if (examplesList) {
            examplesList.innerHTML = this.examples.map(ex => `
                <div class="cron-example-item" data-expression="${ex.expression}">
                    <code class="cron-example-expr">${ex.expression}</code>
                    <span class="cron-example-desc">${ex.description}</span>
                </div>
            `).join('');

            // 点击示例填充
            examplesList.querySelectorAll('.cron-example-item').forEach(item => {
                item.addEventListener('click', () => {
                    const expr = item.dataset.expression;
                    const cronInput = document.getElementById('scheduled-cron');
                    if (cronInput) {
                        cronInput.value = expr;
                        // 触发验证
                        if (window.Scheduler && typeof window.Scheduler.validateCron === 'function') {
                            window.Scheduler.validateCron(expr);
                        }
                    }
                    this.hide();
                });
            });
        }

        document.getElementById('cron-help-dialog').classList.add('active');
    },

    /**
     * 隐藏对话框
     */
    hide() {
        document.getElementById('cron-help-dialog').classList.remove('active');
    },

    /**
     * 绑定对话框事件
     */
    bindEvents() {
        const closeBtn = document.getElementById('close-cron-help-dialog');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }

        const closeFooterBtn = document.getElementById('close-cron-help-btn');
        if (closeFooterBtn) {
            closeFooterBtn.addEventListener('click', () => this.hide());
        }

        // 点击对话框外部关闭
        const dialog = document.getElementById('cron-help-dialog');
        if (dialog) {
            dialog.addEventListener('click', (e) => {
                if (e.target === dialog) {
                    this.hide();
                }
            });
        }
    },

    /**
     * 添加自定义示例
     */
    addExample(expression, description) {
        this.examples.push({ expression, description });
    },

    /**
     * 获取所有示例
     */
    getExamples() {
        return [...this.examples];
    },
};

// 初始化时自动绑定事件
document.addEventListener('DOMContentLoaded', () => {
    CronHelperDialog.bindEvents();
});

// 导出到全局命名空间
window.CronHelperDialog = CronHelperDialog;
