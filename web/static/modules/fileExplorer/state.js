/**
 * 文件浏览器状态管理
 */

const FileExplorerState = {
    // 当前路径
    currentPath: '.',

    // 目录树数据
    tree: {
        loaded: false,
        loading: false,
        data: null,
        expandedDirs: new Set(),
    },

    // 当前文件
    currentFile: {
        path: null,
        content: null,
        loading: false,
    },

    // 搜索
    search: {
        pattern: '',
        results: [],
        loading: false,
    },

    // UI 状态
    ui: {
        sidebarWidth: 250,
        showSearch: false,
    },

    // 设置目录树数据
    setTree(data) {
        this.tree.data = data;
        this.tree.loaded = true;
        this.tree.loading = false;
    },

    // 设置目录树加载状态
    setTreeLoading(loading) {
        this.tree.loading = loading;
    },

    // 切换目录展开状态
    toggleDir(path) {
        if (this.tree.expandedDirs.has(path)) {
            this.tree.expandedDirs.delete(path);
        } else {
            this.tree.expandedDirs.add(path);
        }
    },

    // 检查目录是否展开
    isDirExpanded(path) {
        return this.tree.expandedDirs.has(path);
    },

    // 设置当前文件
    setCurrentFile(path, content) {
        this.currentFile.path = path;
        this.currentFile.content = content;
        this.currentFile.loading = false;
    },

    // 设置文件加载状态
    setFileLoading(loading) {
        this.currentFile.loading = loading;
    },

    // 设置搜索结果
    setSearchResults(pattern, results) {
        this.search.pattern = pattern;
        this.search.results = results;
        this.search.loading = false;
    },

    // 设置搜索加载状态
    setSearchLoading(loading) {
        this.search.loading = loading;
    },

    // 切换搜索面板显示
    toggleSearch() {
        this.ui.showSearch = !this.ui.showSearch;
    },

    // 重置状态
    reset() {
        this.currentPath = '.';
        this.tree = {
            loaded: false,
            loading: false,
            data: null,
            expandedDirs: new Set(),
        };
        this.currentFile = {
            path: null,
            content: null,
            loading: false,
        };
        this.search = {
            pattern: '',
            results: [],
            loading: false,
        };
    },
};

// 导出到全局
window.FileExplorerState = FileExplorerState;
