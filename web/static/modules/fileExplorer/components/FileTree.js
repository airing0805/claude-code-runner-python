/**
 * 文件树组件
 * 树形展示项目文件结构
 */

const FileTree = {
    /**
     * 渲染文件树
     * @param {Object} treeData - 目录树数据
     * @param {HTMLElement} container - 容器元素
     */
    render(treeData, container) {
        if (!treeData || !treeData.children) {
            container.innerHTML = '<div class="file-tree-empty">暂无文件</div>';
            return;
        }

        container.innerHTML = this.renderNode(treeData, 0);
        this.bindEvents(container);
    },

    /**
     * 渲染单个节点
     * @param {Object} node - 节点数据
     * @param {number} level - 层级
     * @returns {string}
     */
    renderNode(node, level) {
        const padding = level * 16;
        const isDir = node.type === 'directory';
        const isExpanded = FileExplorerState.isDirExpanded(node.path);
        const hasChildren = node.children && node.children.length > 0;

        let html = `
            <div class="file-tree-item" data-path="${this.escapeHtml(node.path)}" data-type="${node.type}" style="padding-left: ${padding}px">
                <span class="file-tree-icon">${isDir ? (isExpanded ? '▼' : '▶') : '📄'}</span>
                <span class="file-tree-name">${this.escapeHtml(node.name)}</span>
                ${!isDir && node.size ? `<span class="file-tree-size">${this.formatSize(node.size)}</span>` : ''}
            </div>
        `;

        // 渲染子节点
        if (isDir && isExpanded && hasChildren) {
            const sortedChildren = this.sortChildren(node.children);
            for (const child of sortedChildren) {
                html += this.renderNode(child, level + 1);
            }
        }

        return html;
    },

    /**
     * 对子节点排序（目录在前，文件在后，按名称排序）
     * @param {Array} children - 子节点数组
     * @returns {Array}
     */
    sortChildren(children) {
        return [...children].sort((a, b) => {
            // 目录在前
            if (a.type === 'directory' && b.type !== 'directory') return -1;
            if (a.type !== 'directory' && b.type === 'directory') return 1;
            // 按名称排序
            return a.name.localeCompare(b.name);
        });
    },

    /**
     * 绑定事件
     * @param {HTMLElement} container - 容器元素
     */
    bindEvents(container) {
        // 点击事件
        container.addEventListener('click', (e) => {
            const item = e.target.closest('.file-tree-item');
            if (!item) return;

            const path = item.dataset.path;
            const type = item.dataset.type;

            if (type === 'directory') {
                // 切换展开状态
                FileExplorerState.toggleDir(path);
                this.refresh();
            } else {
                // 读取文件
                this.loadFile(path);
            }
        });

        // 双击事件（目录展开/折叠）
        container.addEventListener('dblclick', (e) => {
            const item = e.target.closest('.file-tree-item');
            if (!item || item.dataset.type !== 'directory') return;

            const path = item.dataset.path;
            FileExplorerState.toggleDir(path);
            this.refresh();
        });
    },

    /**
     * 加载文件
     * @param {string} path - 文件路径
     */
    async loadFile(path) {
        FileExplorerState.setFileLoading(true);
        this.renderLoading();

        try {
            const response = await FileExplorerAPI.readFile(path);
            if (response.success) {
                FileExplorerState.setCurrentFile(path, response.data);
                FilePreview.render(response.data);
            } else {
                this.renderError(response.error || '加载文件失败');
            }
        } catch (error) {
            this.renderError('加载文件失败: ' + error.message);
        }
    },

    /**
     * 刷新文件树
     */
    refresh() {
        const container = document.getElementById('file-tree-container');
        if (container && FileExplorerState.tree.data) {
            this.render(FileExplorerState.tree.data, container);
        }
    },

    /**
     * 渲染加载状态
     */
    renderLoading() {
        const previewContainer = document.getElementById('file-preview-container');
        if (previewContainer) {
            previewContainer.innerHTML = '<div class="file-preview-loading">加载中...</div>';
        }
    },

    /**
     * 渲染错误状态
     * @param {string} message - 错误消息
     */
    renderError(message) {
        const previewContainer = document.getElementById('file-preview-container');
        if (previewContainer) {
            previewContainer.innerHTML = `<div class="file-preview-error">${this.escapeHtml(message)}</div>`;
        }
    },

    /**
     * 格式化文件大小
     * @param {number} bytes - 字节数
     * @returns {string}
     */
    formatSize(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        return `${size.toFixed(1)} ${units[unitIndex]}`;
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
window.FileTree = FileTree;
