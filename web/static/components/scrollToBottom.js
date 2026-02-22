/**
 * ScrollToBottomButton - 滚动到底部按钮组件
 * v0.5.2 - 可复用组件开发
 */

const ScrollToBottomButton = {
    /**
     * 创建滚动到底部按钮
     * @param {HTMLElement} container - 要监听滚动的容器元素
     * @param {Object} options - 配置选项
     * @param {number} [options.threshold=100] - 显示按钮的滚动阈值(px)
     * @param {string} [options.text='最新'] - 按钮文本
     * @param {string} [options.className=''] - 额外的 CSS 类名
     * @param {Function} [options.onScroll] - 滚动完成后的回调
     * @returns {HTMLButtonElement}
     */
    create(container, options = {}) {
        const {
            threshold = 100,
            text = '最新',
            className = '',
            onScroll = null
        } = options;

        // 创建按钮元素
        const button = document.createElement('button');
        button.className = `scroll-to-bottom-btn ${className}`.trim();
        button.type = 'button';
        button.style.display = 'none'; // 初始隐藏

        button.innerHTML = `
            <span class="scroll-icon">↓</span>
            <span class="scroll-text">${text}</span>
        `;

        // 存储配置
        button._scrollToBottom = {
            container,
            threshold,
            onScroll
        };

        // 绑定点击事件
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            this.scrollToBottom(button);
        });

        // 监听容器滚动
        this.bindScrollListener(button, container, threshold);

        // 初始检查滚动位置
        this.updateVisibility(button, container, threshold);

        return button;
    },

    /**
     * 滚动到底部
     * @param {HTMLButtonElement} button - 按钮元素
     */
    scrollToBottom(button) {
        const config = button._scrollToBottom;
        if (!config) return;

        const { container, onScroll } = config;

        container.scrollTo({
            top: container.scrollHeight,
            behavior: 'smooth'
        });

        // 隐藏按钮
        button.style.display = 'none';

        // 调用回调
        if (onScroll) {
            onScroll();
        }
    },

    /**
     * 更新按钮可见性
     * @param {HTMLButtonElement} button - 按钮元素
     * @param {HTMLElement} container - 容器元素
     * @param {number} threshold - 阈值
     */
    updateVisibility(button, container, threshold) {
        const { scrollTop, scrollHeight, clientHeight } = container;
        const isNearBottom = scrollHeight - scrollTop - clientHeight > threshold;

        button.style.display = isNearBottom ? 'flex' : 'none';
    },

    /**
     * 绑定滚动监听器
     * @param {HTMLButtonElement} button - 按钮元素
     * @param {HTMLElement} container - 容器元素
     * @param {number} threshold - 阈值
     */
    bindScrollListener(button, container, threshold) {
        // 使用节流避免频繁触发
        let ticking = false;

        const handleScroll = () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    this.updateVisibility(button, container, threshold);
                    ticking = false;
                });
                ticking = true;
            }
        };

        container.addEventListener('scroll', handleScroll);

        // 存储监听器引用，便于销毁
        button._scrollToBottom._scrollHandler = handleScroll;
    },

    /**
     * 销毁按钮，移除事件监听
     * @param {HTMLButtonElement} button - 按钮元素
     */
    destroy(button) {
        const config = button._scrollToBottom;
        if (!config) return;

        const { container, _scrollHandler } = config;

        if (container && _scrollHandler) {
            container.removeEventListener('scroll', _scrollHandler);
        }

        button.remove();
    },

    /**
     * 强制显示按钮
     * @param {HTMLButtonElement} button - 按钮元素
     */
    show(button) {
        button.style.display = 'flex';
    },

    /**
     * 强制隐藏按钮
     * @param {HTMLButtonElement} button - 按钮元素
     */
    hide(button) {
        button.style.display = 'none';
    },

    /**
     * 检查是否在底部附近
     * @param {HTMLElement} container - 容器元素
     * @param {number} threshold - 阈值
     * @returns {boolean}
     */
    isNearBottom(container, threshold = 100) {
        const { scrollTop, scrollHeight, clientHeight } = container;
        return scrollHeight - scrollTop - clientHeight <= threshold;
    },

    /**
     * 创建固定在容器角落的滚动按钮
     * @param {HTMLElement} container - 要监听滚动的容器元素
     * @param {Object} options - 配置选项
     * @returns {HTMLButtonElement}
     */
    createFixed(container, options = {}) {
        const button = this.create(container, options);

        // 设置为固定定位
        button.classList.add('scroll-to-bottom-fixed');

        // 将按钮添加到容器的父元素或 body
        const parent = container.parentElement || document.body;
        parent.style.position = 'relative';
        parent.appendChild(button);

        return button;
    }
};

// 挂载到全局对象
window.ScrollToBottomButton = ScrollToBottomButton;
