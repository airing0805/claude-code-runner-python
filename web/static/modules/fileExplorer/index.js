/**
 * 文件浏览器主模块
 * 整合所有子模块，提供统一的文件浏览功能
 */

// 导入子模块（已通过 script 标签加载）
// import { FileExplorerAPI } from './api.js';
// import { FileExplorerState } from './state.js';
// import { FileTree } from './components/FileTree.js';
// import { FilePreview } from './components/FilePreview.js';
// import { Breadcrumb } from './components/Breadcrumb.js';
// import { SearchBox } from './components/SearchBox.js';

/**
 * 文件浏览器主模块
 */
const FileExplorer = {
    // 模块名称
    name: 'fileExplorer',

    // 视图元素 ID
    viewId: 'file-explorer-view',

    /**
     * 初始化模块
     */
    init() {
        console.log('[FileExplorer] 初始化文件浏览器模块');
        this.ensureContainer();
        this.bindEvents();
    },

    /**
     * 确保容器存在
     */
    ensureContainer() {
        let container = document.getElementById(this.viewId);
        if (!container) {
            // 尝试从现有视图获取或创建
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                container = document.createElement('div');
                container.id = this.viewId;
                container.className = 'file-explorer-view';
                container.style.display = 'none';
                mainContent.appendChild(container);
            }
        }
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 搜索按钮
        const searchToggleBtn = document.getElementById('file-explorer-search-toggle');
        if (searchToggleBtn) {
            searchToggleBtn.addEventListener('click', () => {
                const searchContainer = document.getElementById('file-explorer-search');
                if (searchContainer) {
                    searchContainer.classList.toggle('show');
                }
            });
        }

        // 刷新按钮
        const refreshBtn = document.getElementById('file-explorer-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadTree(FileExplorerState.currentPath);
            });
        }
    },

    /**
     * 视图显示时调用
     */
    async onShow() {
        await this.loadTree('.');
    },

    /**
     * 视图隐藏时调用
     */
    onHide() {
        // 可以在这里停止轮询等
    },

    /**
     * 加载目录树
     * @param {string} path - 目录路径
     */
    async loadTree(path = '.') {
        const treeContainer = document.getElementById('file-tree-container');
        if (treeContainer) {
            treeContainer.innerHTML = '<div class="file-tree-loading">加载中...</div>';
        }

        FileExplorerState.setTreeLoading(true);
        FileExplorerState.currentPath = path;

        try {
            const response = await FileExplorerAPI.getTree(path, 3, false);

            if (response.success) {
                FileExplorerState.setTree(response.data);
                this.renderTree();
                this.renderBreadcrumb(path);
            } else {
                this.renderTreeError(response.error || '加载失败');
            }
        } catch (error) {
            this.renderTreeError('加载失败: ' + error.message);
        }
    },

    /**
     * 渲染目录树
     */
    renderTree() {
        const container = document.getElementById('file-tree-container');
        if (!container) return;

        if (FileExplorerState.tree.loading) {
            container.innerHTML = '<div class="file-tree-loading">加载中...</div>';
            return;
        }

        if (FileExplorerState.tree.data) {
            FileTree.render(FileExplorerState.tree.data, container);
        } else {
            container.innerHTML = '<div class="file-tree-empty">暂无数据</div>';
        }
    },

    /**
     * 渲染目录树错误
     * @param {string} message - 错误消息
     */
    renderTreeError(message) {
        const container = document.getElementById('file-tree-container');
        if (container) {
            container.innerHTML = `<div class="file-tree-error">${message}</div>`;
        }
    },

    /**
     * 渲染面包屑
     * @param {string} path - 当前路径
     */
    renderBreadcrumb(path) {
        Breadcrumb.render(path);
    },

    /**
     * 加载文件
     * @param {string} path - 文件路径
     */
    async loadFile(path) {
        FileExplorerState.setFileLoading(true);

        const previewContainer = document.getElementById('file-preview-container');
        if (previewContainer) {
            previewContainer.innerHTML = '<div class="file-preview-loading">加载中...</div>';
        }

        try {
            const response = await FileExplorerAPI.readFile(path);

            if (response.success) {
                FileExplorerState.setCurrentFile(path, response.data);
                FilePreview.render(response.data);
            } else {
                this.renderFileError(response.error || '加载文件失败');
            }
        } catch (error) {
            this.renderFileError('加载文件失败: ' + error.message);
        }
    },

    /**
     * 渲染文件错误
     * @param {string} message - 错误消息
     */
    renderFileError(message) {
        const container = document.getElementById('file-preview-container');
        if (container) {
            container.innerHTML = `<div class="file-preview-error">${message}</div>`;
        }
    },
};

// 导出到全局
window.FileExplorer = FileExplorer;
