/**
 * 调度器工具模块
 * 模块拆分 - v7.0.10
 * 提供工具函数和辅助方法
 */

const SchedulerUtils = {
    /**
     * 转义 HTML 特殊字符
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 截断文本
     */
    truncate(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
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
            return `${hours}小时${minutes % 60}分`;
        }
        if (minutes > 0) {
            return `${minutes}分${seconds % 60}秒`;
        }
        return `${seconds}秒`;
    },

    /**
     * 获取来源徽章
     */
    getSourceBadge(source, scheduledName) {
        if (source === 'scheduled' && scheduledName) {
            return `<span class="source-badge source-scheduled" title="${this.escapeHtml(scheduledName)}">定时任务</span>`;
        } else if (source === 'immediate') {
            return '<span class="source-badge source-immediate">立即执行</span>';
        } else {
            return '<span class="source-badge source-manual">手动添加</span>';
        }
    },

    /**
     * 获取状态文本
     */
    getStatusText(status) {
        const statusMap = {
            'queued': '等待中',
            'running': '运行中',
            'completed': '已完成',
            'failed': '失败',
            'cancelled': '已取消',
        };
        return statusMap[status] || status;
    },

    /**
     * 显示通知消息
     */
    showNotification(message, type = 'info', duration = 3000) {
        // 使用全局的 Utils.showNotification 如果可用
        if (window.Utils && typeof window.Utils.showNotification === 'function') {
            window.Utils.showNotification(message, type);
        } else {
            // 回退到控制台
            console.log(`[${type}] ${message}`);
        }
    },

    /**
     * 检查对象是否为纯对象
     */
    isPlainObject(obj) {
        return obj && typeof obj === 'object' && !Array.isArray(obj) && obj.constructor === Object;
    },

    /**
     * 合并对象（不可变）
     */
    merge(target, source) {
        const output = { ...target };
        for (const key in source) {
            if (source.hasOwnProperty(key)) {
                output[key] = this.isPlainObject(source[key])
                    ? this.merge({}, source[key])
                    : source[key];
            }
        }
        return output;
    },

    /**
     * 防抖函数
     */
    debounce(func, wait) {
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
     * 节流函数
     */
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func(...args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * 深度克隆对象
     */
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        if (obj instanceof Date) {
            return new Date(obj.getTime());
        }
        if (obj instanceof Array) {
            return obj.map(item => this.deepClone(item));
        }
        if (this.isPlainObject(obj)) {
            const clonedObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    clonedObj[key] = this.deepClone(obj[key]);
                }
            }
            return clonedObj;
        }
        return obj;
    },
};

// 导出到全局命名空间
window.SchedulerUtils = SchedulerUtils;
