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
    }
};

// 导出到全局命名空间
window.Utils = Utils;
