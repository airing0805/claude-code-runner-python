/**
 * CollapsiblePanel - 可折叠面板组件
 * v0.5.2 - 可复用组件开发
 */

const CollapsiblePanel = {
    /**
     * 创建可折叠面板
     * @param {Object} options - 配置选项
     * @param {string} [options.title=''] - 标题文本
     * @param {string} [options.icon=''] - 标题图标 (emoji 或 HTML)
     * @param {HTMLElement|string} [options.content=''] - 面板内容 (元素或 HTML 字符串)
     * @param {boolean} [options.expanded=false] - 初始是否展开
     * @param {string} [options.className=''] - 额外的 CSS 类名
     * @param {string} [options.headerClassName=''] - 标题栏额外的 CSS 类名
     * @param {string} [options.contentClassName=''] - 内容区额外的 CSS 类名
     * @param {Function} [options.onToggle] - 切换状态时的回调
     * @returns {HTMLDivElement}
     */
    create(options = {}) {
        const {
            title = '',
            icon = '',
            content = '',
            expanded = false,
            className = '',
            headerClassName = '',
            contentClassName = '',
            onToggle = null
        } = options;

        // 主容器
        const panel = document.createElement('div');
        panel.className = `collapsible-panel ${className}`.trim();
        if (expanded) {
            panel.classList.add('expanded');
        }

        // 标题栏
        const header = document.createElement('div');
        header.className = `collapsible-header ${headerClassName}`.trim();

        // 标题内容
        const headerContent = document.createElement('div');
        headerContent.className = 'collapsible-header-content';

        if (icon) {
            const iconEl = document.createElement('span');
            iconEl.className = 'collapsible-icon';
            iconEl.innerHTML = icon;
            headerContent.appendChild(iconEl);
        }

        if (title) {
            const titleEl = document.createElement('span');
            titleEl.className = 'collapsible-title';
            titleEl.textContent = title;
            headerContent.appendChild(titleEl);
        }

        // 展开箭头
        const toggle = document.createElement('span');
        toggle.className = 'collapsible-toggle';
        toggle.innerHTML = '▶';

        header.appendChild(headerContent);
        header.appendChild(toggle);

        // 内容区
        const contentWrapper = document.createElement('div');
        contentWrapper.className = `collapsible-content ${contentClassName}`.trim();

        if (typeof content === 'string') {
            contentWrapper.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            contentWrapper.appendChild(content);
        }

        // 组装面板
        panel.appendChild(header);
        panel.appendChild(contentWrapper);

        // 绑定点击事件
        header.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle(panel, onToggle);
        });

        // 存储状态
        panel._collapsible = {
            expanded,
            onToggle
        };

        return panel;
    },

    /**
     * 切换展开/收起状态
     * @param {HTMLElement} panel - 面板元素
     * @param {Function} [onToggle] - 可选的回调函数
     */
    toggle(panel, onToggle = null) {
        const isExpanded = panel.classList.contains('expanded');

        if (isExpanded) {
            this.collapse(panel);
        } else {
            this.expand(panel);
        }

        // 调用回调
        const callback = onToggle || panel._collapsible?.onToggle;
        if (callback) {
            callback(!isExpanded, panel);
        }
    },

    /**
     * 展开面板
     * @param {HTMLElement} panel - 面板元素
     */
    expand(panel) {
        panel.classList.add('expanded');
        if (panel._collapsible) {
            panel._collapsible.expanded = true;
        }
    },

    /**
     * 收起面板
     * @param {HTMLElement} panel - 面板元素
     */
    collapse(panel) {
        panel.classList.remove('expanded');
        if (panel._collapsible) {
            panel._collapsible.expanded = false;
        }
    },

    /**
     * 检查面板是否展开
     * @param {HTMLElement} panel - 面板元素
     * @returns {boolean}
     */
    isExpanded(panel) {
        return panel.classList.contains('expanded');
    },

    /**
     * 更新面板内容
     * @param {HTMLElement} panel - 面板元素
     * @param {HTMLElement|string} content - 新内容
     */
    updateContent(panel, content) {
        const contentWrapper = panel.querySelector('.collapsible-content');
        if (!contentWrapper) return;

        if (typeof content === 'string') {
            contentWrapper.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            contentWrapper.innerHTML = '';
            contentWrapper.appendChild(content);
        }
    },

    /**
     * 更新面板标题
     * @param {HTMLElement} panel - 面板元素
     * @param {string} title - 新标题
     * @param {string} [icon] - 新图标
     */
    updateTitle(panel, title, icon) {
        const titleEl = panel.querySelector('.collapsible-title');
        const iconEl = panel.querySelector('.collapsible-icon');

        if (titleEl && title) {
            titleEl.textContent = title;
        }

        if (iconEl && icon !== undefined) {
            iconEl.innerHTML = icon;
        }
    },

    /**
     * 从现有元素初始化可折叠功能
     * @param {HTMLElement} container - 容器元素
     * @param {Object} options - 配置选项
     */
    init(container, options = {}) {
        const { expanded = false, onToggle = null } = options;

        // 查找标题栏和内容区
        const header = container.querySelector('.collapsible-header');
        const content = container.querySelector('.collapsible-content');

        if (!header || !content) {
            console.warn('CollapsiblePanel: 未找到必要的子元素');
            return;
        }

        // 设置初始状态
        if (expanded) {
            container.classList.add('expanded');
        }

        // 存储状态
        container._collapsible = {
            expanded,
            onToggle
        };

        // 绑定点击事件
        header.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle(container, onToggle);
        });
    }
};

// 挂载到全局对象
window.CollapsiblePanel = CollapsiblePanel;
