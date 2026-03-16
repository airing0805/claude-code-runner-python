/**
 * CopyButton - 复制按钮组件
 * v0.5.2 - 可复用组件开发
 */

const CopyButton = {
    /**
     * 创建复制按钮元素
     * @param {string} text - 要复制的文本
     * @param {Object} options - 配置选项
     * @param {string} [options.className=''] - 额外的 CSS 类名
     * @param {string} [options.title='复制'] - 鼠标悬停提示
     * @param {string} [options.copiedTitle='已复制'] - 复制成功后的提示
     * @param {number} [options.duration=1500] - 复制成功状态持续时间(ms)
     * @returns {HTMLButtonElement}
     */
    create(text, options = {}) {
        const {
            className = '',
            title = '复制',
            copiedTitle = '已复制',
            duration = 1500
        } = options;

        const button = document.createElement('button');
        button.className = `btn-tool copy-btn ${className}`.trim();
        button.type = 'button';
        button.title = title;
        button.dataset.text = text;
        button.dataset.copiedTitle = copiedTitle;
        button.dataset.duration = duration;

        // 默认图标 (复制图标)
        button.innerHTML = `
            <span class="copy-icon">📋</span>
            <span class="copy-success" style="display: none;">✓</span>
        `;

        // 绑定点击事件
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            this.handleCopy(button, text, duration);
        });

        return button;
    },

    /**
     * 处理复制逻辑
     * @param {HTMLButtonElement} button - 按钮元素
     * @param {string} text - 要复制的文本
     * @param {number} duration - 复制成功状态持续时间(ms)
     */
    async handleCopy(button, text, duration = 1500) {
        // 如果已经处于复制状态，不再重复处理
        if (button.classList.contains('copied')) {
            return;
        }

        try {
            // 优先使用 Clipboard API
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
            } else {
                // Fallback 方案：使用 textarea + execCommand
                this.fallbackCopy(text);
            }

            // 显示复制成功状态
            this.showCopiedState(button, duration);
        } catch (err) {
            console.error('复制失败:', err);
            // 尝试 fallback 方案
            try {
                this.fallbackCopy(text);
                this.showCopiedState(button, duration);
            } catch (fallbackErr) {
                console.error('Fallback 复制也失败:', fallbackErr);
            }
        }
    },

    /**
     * Fallback 复制方案（兼容旧浏览器）
     * @param {string} text - 要复制的文本
     */
    fallbackCopy(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        textarea.style.top = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        textarea.setSelectionRange(0, text.length);
        const success = document.execCommand('copy');
        document.body.removeChild(textarea);
        if (!success) {
            throw new Error('execCommand copy failed');
        }
    },

    /**
     * 显示复制成功状态
     * @param {HTMLButtonElement} button - 按钮元素
     * @param {number} duration - 持续时间(ms)
     */
    showCopiedState(button, duration = 1500) {
        const copyIcon = button.querySelector('.copy-icon');
        const copySuccess = button.querySelector('.copy-success');

        button.classList.add('copied');
        button.title = button.dataset.copiedTitle || '已复制';

        if (copyIcon) copyIcon.style.display = 'none';
        if (copySuccess) copySuccess.style.display = 'inline';

        // 定时恢复原状态
        setTimeout(() => {
            button.classList.remove('copied');
            button.title = button.dataset.title || '复制';

            if (copyIcon) copyIcon.style.display = 'inline';
            if (copySuccess) copySuccess.style.display = 'none';
        }, duration);
    },

    /**
     * 为现有元素绑定复制功能
     * @param {HTMLElement} element - 要绑定的元素
     * @param {string|Function} getText - 要复制的文本或获取文本的函数
     * @param {Object} options - 配置选项
     */
    bind(element, getText, options = {}) {
        const { duration = 1500, copiedTitle = '已复制' } = options;

        element.addEventListener('click', async (e) => {
            e.stopPropagation();

            const text = typeof getText === 'function' ? getText() : getText;
            await this.handleCopy(element, text, duration);
        });
    }
};

// 挂载到全局对象
window.CopyButton = CopyButton;
