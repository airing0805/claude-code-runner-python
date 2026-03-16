/**
 * 文件预览组件
 * 显示文件内容和元信息
 */

const FilePreview = {
    /**
     * 渲染文件预览
     * @param {Object} fileData - 文件数据
     */
    render(fileData) {
        const container = document.getElementById('file-preview-container');
        if (!container) return;

        if (!fileData) {
            container.innerHTML = '<div class="file-preview-empty">请选择文件查看</div>';
            return;
        }

        const html = `
            <div class="file-preview-header">
                <div class="file-preview-info">
                    <span class="file-preview-name">${this.escapeHtml(fileData.name)}</span>
                    <span class="file-preview-meta">
                        ${fileData.size_formatted || this.formatSize(fileData.size)} |
                        ${fileData.total_lines} 行 |
                        ${fileData.encoding || 'utf-8'}
                    </span>
                </div>
            </div>
            <div class="file-preview-content">
                <pre><code class="language-${this.getLanguage(fileData.name)}">${this.escapeHtml(fileData.content)}</code></pre>
            </div>
            ${fileData.has_more ? `
                <div class="file-preview-footer">
                    <button class="file-preview-load-more" data-path="${this.escapeHtml(fileData.path)}">
                        加载更多 (还有 ${fileData.total_lines - 500} 行)
                    </button>
                </div>
            ` : ''}
        `;

        container.innerHTML = html;
        this.bindEvents(container);
        this.highlightCode();
    },

    /**
     * 绑定事件
     * @param {HTMLElement} container - 容器元素
     */
    bindEvents(container) {
        // 加载更多
        const loadMoreBtn = container.querySelector('.file-preview-load-more');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', async (e) => {
                const path = e.target.dataset.path;
                const currentContent = FileExplorerState.currentFile.content;
                const currentLines = currentContent.split('\n').length;

                const response = await FileExplorerAPI.readFile(path, currentLines + 1, 500);
                if (response.success) {
                    const newContent = currentContent + '\n' + response.data.content;
                    FileExplorerState.currentFile.content = newContent;
                    this.render({
                        ...response.data,
                        content: newContent,
                    });
                }
            });
        }
    },

    /**
     * 代码高亮（使用 Prism.js 如果可用）
     */
    highlightCode() {
        if (typeof Prism !== 'undefined') {
            Prism.highlightAll();
        }
    },

    /**
     * 根据文件扩展名获取语言
     * @param {string} filename - 文件名
     * @returns {string}
     */
    getLanguage(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const langMap = {
            'js': 'javascript',
            'ts': 'typescript',
            'jsx': 'jsx',
            'tsx': 'tsx',
            'py': 'python',
            'rb': 'ruby',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'h': 'c',
            'hpp': 'cpp',
            'go': 'go',
            'rs': 'rust',
            'sql': 'sql',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'sh': 'bash',
            'bash': 'bash',
        };
        return langMap[ext] || 'plaintext';
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
window.FilePreview = FilePreview;
