/**
 * 面包屑导航组件
 * 显示当前路径，支持点击跳转
 */

const Breadcrumb = {
    /**
     * 渲染面包屑导航
     * @param {string} path - 当前路径
     */
    render(path) {
        const container = document.getElementById('file-explorer-breadcrumb');
        if (!container) return;

        const parts = this.parsePath(path);
        const html = parts.map((part, index) => {
            const isLast = index === parts.length - 1;
            const partPath = index === 0 ? '.' : this.buildPath(parts.slice(0, index + 1));

            return isLast
                ? `<span class="breadcrumb-item breadcrumb-current">${this.escapeHtml(part)}</span>`
                : `<a href="#" class="breadcrumb-item" data-path="${this.escapeHtml(partPath)}">${this.escapeHtml(part)}</a>`;
        }).join('<span class="breadcrumb-separator">/</span>');

        container.innerHTML = html;
        this.bindEvents(container);
    },

    /**
     * 解析路径为部分
     * @param {string} path - 路径
     * @returns {Array}
     */
    parsePath(path) {
        if (!path || path === '.' || path === './') {
            return ['root'];
        }
        // 移除开头的 ./ 或 /
        path = path.replace(/^[./]+/, '');
        if (!path) {
            return ['root'];
        }
        return path.split('/').filter(p => p);
    },

    /**
     * 构建路径
     * @param {Array} parts - 路径部分
     * @returns {string}
     */
    buildPath(parts) {
        if (parts.length === 0 || (parts.length === 1 && parts[0] === 'root')) {
            return '.';
        }
        return './' + parts.join('/');
    },

    /**
     * 绑定事件
     * @param {HTMLElement} container - 容器元素
     */
    bindEvents(container) {
        container.addEventListener('click', async (e) => {
            const item = e.target.closest('.breadcrumb-item');
            if (!item || item.classList.contains('breadcrumb-current')) return;

            e.preventDefault();
            const path = item.dataset.path;

            // 重新加载目录树
            await FileExplorer.loadTree(path);
        });
    },

    /**
     * HTML 转义
     * @param {string} str - 字符串
     * @returns {string}
     */
    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },
};

// 导出到全局
window.Breadcrumb = Breadcrumb;
