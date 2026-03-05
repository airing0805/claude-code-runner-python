/**
 * 工具函数模块
 * 包含应用程序中使用的通用工具函数
 */

const Utils = {
    /**
     * HTML 转义，防止 XSS 攻击
     * @param {string} text - 要转义的文本
     * @returns {string} 转义后的文本
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 滚动输出区到底部
     * @param {HTMLElement} outputEl - 输出区元素
     */
    scrollToBottom(outputEl) {
        if (outputEl) {
            outputEl.scrollTop = outputEl.scrollHeight;
        }
    },

    /**
     * 格式化时间戳
     * @param {string|null} timestamp - ISO 时间戳
     * @returns {string} 格式化后的时间字符串
     */
    formatTime(timestamp) {
        if (!timestamp) return '';
        return new Date(timestamp).toLocaleTimeString();
    },

    /**
     * 格式化日期时间
     * @param {string|null} timestamp - ISO 时间戳
     * @returns {string} 格式化后的日期时间字符串
     */
    formatDateTime(timestamp) {
        if (!timestamp) return '未知时间';
        return new Date(timestamp).toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    /**
     * 判断是否为工具结果消息
     * @param {Object} message - 消息对象
     * @returns {boolean} 是否为工具结果
     */
    isToolResult(message) {
        const content = message.content || [];
        return content.some(block => block.type === 'tool_result');
    },

    /**
     * 从 content 数组中提取标题，排除 ide_selection 和 ide_opened_file 标签内容
     * @param {Array} content - 消息内容数组
     * @returns {string|null} 提取的标题
     */
    extractTitleFromContent(content) {
        if (!content || !Array.isArray(content)) {
            return null;
        }

        for (const block of content) {
            if (block.type === 'text' && block.text) {
                const text = block.text;
                // 跳过包含 ide_selection 或 ide_opened_file 的块
                if (/<ide_selection>|<ide_opened_file>/i.test(text)) {
                    continue;
                }
                return text.trim();
            }
        }

        return null;
    },

    /**
     * 截断过长的文本
     * @param {string} text - 要截断的文本
     * @param {number} maxLength - 最大长度
     * @returns {string} 截断后的文本
     */
    truncateText(text, maxLength = 500) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...\n[内容已截断]';
    },

    /**
     * 防抖函数
     * @param {Function} func - 要防抖的函数
     * @param {number} wait - 等待时间（毫秒）
     * @returns {Function} 防抖后的函数
     */
    debounce(func, wait = 300) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * 显示通知提示
     * @param {string} message - 通知消息
     * @param {string} type - 通知类型 (success, error, warning, info)
     */
    showNotification(message, type = 'info') {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // 添加到页面
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
            document.body.appendChild(container);
        }

        container.appendChild(notification);

        // 3秒后自动移除
        setTimeout(() => {
            notification.remove();
        }, 3000);
    },

    /**
     * 显示确认对话框
     * @param {string} message - 确认消息
     * @param {Object} options - 配置选项
     * @param {string} [options.title='确认'] - 对话框标题
     * @param {string} [options.confirmText='确定'] - 确认按钮文本
     * @param {string} [options.cancelText='取消'] - 取消按钮文本
     * @param {string} [options.type='warning'] - 对话框类型 (warning, danger, info)
     * @returns {Promise<boolean>} 用户是否确认
     */
    showConfirm(message, options = {}) {
        const {
            title = '确认',
            confirmText = '确定',
            cancelText = '取消',
            type = 'warning'
        } = options;

        return new Promise((resolve) => {
            // 查找或创建确认对话框
            let overlay = document.getElementById('confirm-dialog-overlay');

            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'confirm-dialog-overlay';
                overlay.className = 'dialog-overlay';
                overlay.innerHTML = `
                    <div class="dialog-content confirm-dialog">
                        <div class="confirm-dialog-body">
                            <span class="confirm-dialog-icon"></span>
                            <div class="confirm-dialog-content">
                                <h3 class="confirm-dialog-title"></h3>
                                <p class="confirm-dialog-message"></p>
                            </div>
                        </div>
                        <div class="dialog-footer">
                            <button class="btn btn-secondary confirm-dialog-cancel"></button>
                            <button class="btn btn-primary confirm-dialog-confirm"></button>
                        </div>
                    </div>
                `;
                document.body.appendChild(overlay);
            }

            // 获取元素
            const titleEl = overlay.querySelector('.confirm-dialog-title');
            const messageEl = overlay.querySelector('.confirm-dialog-message');
            const iconEl = overlay.querySelector('.confirm-dialog-icon');
            const confirmBtn = overlay.querySelector('.confirm-dialog-confirm');
            const cancelBtn = overlay.querySelector('.confirm-dialog-cancel');
            const dialogContent = overlay.querySelector('.confirm-dialog');

            // 设置内容
            titleEl.textContent = title;
            messageEl.textContent = message;
            confirmBtn.textContent = confirmText;
            cancelBtn.textContent = cancelText;

            // 设置类型样式
            dialogContent.className = `dialog-content confirm-dialog confirm-dialog-${type}`;

            // 设置图标
            const icons = {
                warning: '⚠️',
                danger: '🗑️',
                info: 'ℹ️'
            };
            iconEl.textContent = icons[type] || icons.warning;

            // 设置按钮样式
            confirmBtn.className = type === 'danger'
                ? 'btn btn-danger confirm-dialog-confirm'
                : 'btn btn-primary confirm-dialog-confirm';

            // 清理旧的事件监听器
            const newConfirmBtn = confirmBtn.cloneNode(true);
            const newCancelBtn = cancelBtn.cloneNode(true);
            confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
            cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);

            // 关闭对话框的函数
            const closeDialog = (result) => {
                overlay.classList.remove('active');
                resolve(result);
            };

            // 绑定事件
            newConfirmBtn.addEventListener('click', () => closeDialog(true));
            newCancelBtn.addEventListener('click', () => closeDialog(false));

            // 点击遮罩层关闭
            overlay.onclick = (e) => {
                if (e.target === overlay) {
                    closeDialog(false);
                }
            };

            // ESC 键关闭
            const handleEsc = (e) => {
                if (e.key === 'Escape') {
                    document.removeEventListener('keydown', handleEsc);
                    closeDialog(false);
                }
            };
            document.addEventListener('keydown', handleEsc);

            // 显示对话框
            overlay.classList.add('active');
        });
    }
};

// 导出到全局命名空间
window.Utils = Utils;
