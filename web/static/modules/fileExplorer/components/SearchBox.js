/**
 * 搜索框组件
 * 支持 Glob 模式搜索文件
 */

const SearchBox = {
    _debounceTimer: null,

    /**
     * 初始化搜索框
     */
    init() {
        const container = document.getElementById('file-explorer-search');
        if (!container) return;

        this.render(container);
        this.bindEvents(container);
    },

    /**
     * 渲染搜索框
     * @param {HTMLElement} container - 容器元素
     */
    render(container) {
        container.innerHTML = `
            <div class="search-box">
                <input type="text"
                       class="search-input"
                       placeholder="搜索文件 (如 *.py, src/**/*.js)"
                       id="file-search-input">
                <button class="search-btn" id="file-search-btn">搜索</button>
            </div>
            <div class="search-results" id="file-search-results"></div>
        `;
    },

    /**
     * 绑定事件
     * @param {HTMLElement} container - 容器元素
     */
    bindEvents(container) {
        const input = container.querySelector('#file-search-input');
        const btn = container.querySelector('#file-search-btn');

        // 搜索按钮点击
        btn.addEventListener('click', () => {
            this.performSearch(input.value);
        });

        // 回车搜索
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch(input.value);
            }
        });

        // 输入防抖
        input.addEventListener('input', () => {
            this.debounce(() => {
                if (input.value.length >= 2) {
                    this.performSearch(input.value);
                }
            }, 300);
        });

        // 点击结果项跳转到文件
        const resultsContainer = container.querySelector('#file-search-results');
        resultsContainer.addEventListener('click', (e) => {
            const item = e.target.closest('.search-result-item');
            if (item) {
                const path = item.dataset.path;
                // 获取目录路径并加载
                const dirPath = path.substring(0, path.lastIndexOf('/')) || '.';
                const fileName = path.substring(path.lastIndexOf('/') + 1);

                // 加载目录
                FileExplorer.loadTree(dirPath).then(() => {
                    // 查找并点击文件
                    this.highlightFile(fileName);
                });
            }
        });
    },

    /**
     * 执行搜索
     * @param {string} pattern - 搜索模式
     */
    async performSearch(pattern) {
        if (!pattern || pattern.length < 1) {
            this.clearResults();
            return;
        }

        const resultsContainer = document.getElementById('file-search-results');
        resultsContainer.innerHTML = '<div class="search-loading">搜索中...</div>';

        try {
            const response = await FileExplorerAPI.searchFiles(pattern, '.', 50);

            if (response.success) {
                this.renderResults(response.data);
            } else {
                resultsContainer.innerHTML = `<div class="search-error">${this.escapeHtml(response.error || '搜索失败')}</div>`;
            }
        } catch (error) {
            resultsContainer.innerHTML = `<div class="search-error">搜索失败: ${this.escapeHtml(error.message)}</div>`;
        }
    },

    /**
     * 渲染搜索结果
     * @param {Object} data - 搜索结果数据
     */
    renderResults(data) {
        const resultsContainer = document.getElementById('file-search-results');

        if (!data.matches || data.matches.length === 0) {
            resultsContainer.innerHTML = '<div class="search-empty">没有找到匹配的文件</div>';
            return;
        }

        const html = data.matches.map(item => `
            <div class="search-result-item" data-path="${this.escapeHtml(item.path)}">
                <span class="search-result-icon">📄</span>
                <span class="search-result-name">${this.escapeHtml(item.name)}</span>
                <span class="search-result-path">${this.escapeHtml(item.path)}</span>
            </div>
        `).join('');

        resultsContainer.innerHTML = html;
    },

    /**
     * 清除搜索结果
     */
    clearResults() {
        const resultsContainer = document.getElementById('file-search-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }
    },

    /**
     * 高亮文件
     * @param {string} fileName - 文件名
     */
    highlightFile(fileName) {
        // 查找文件树中的文件项并高亮
        const items = document.querySelectorAll('.file-tree-item');
        items.forEach(item => {
            if (item.dataset.type === 'file' && item.querySelector('.file-tree-name')?.textContent === fileName) {
                item.classList.add('file-tree-highlight');
                setTimeout(() => item.classList.remove('file-tree-highlight'), 2000);
            }
        });
    },

    /**
     * 防抖
     * @param {Function} func - 函数
     * @param {number} delay - 延迟（毫秒）
     */
    debounce(func, delay) {
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(func, delay);
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
window.SearchBox = SearchBox;
