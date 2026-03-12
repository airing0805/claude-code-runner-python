/**
 * 文件浏览器 API 模块
 * 提供与后端文件 API 交互的功能
 */

const FileExplorerAPI = {
    /**
     * 获取目录文件树
     * @param {string} path - 目录路径
     * @param {number} depth - 递归深度
     * @param {boolean} includeHidden - 是否包含隐藏文件
     * @returns {Promise}
     */
    getTree(path = '.', depth = 2, includeHidden = false) {
        const params = new URLSearchParams({
            path,
            depth: depth.toString(),
            include_hidden: includeHidden.toString(),
        });
        return fetch(`/api/files/tree?${params}`)
            .then(res => res.json());
    },

    /**
     * 读取文件内容
     * @param {string} path - 文件路径
     * @param {number} startLine - 起始行号
     * @param {number} limit - 读取行数
     * @returns {Promise}
     */
    readFile(path, startLine = 1, limit = 500) {
        const params = new URLSearchParams({
            path,
            start_line: startLine.toString(),
            limit: limit.toString(),
        });
        return fetch(`/api/files/read?${params}`)
            .then(res => res.json());
    },

    /**
     * 搜索文件
     * @param {string} pattern - Glob 模式
     * @param {string} path - 搜索目录
     * @param {number} limit - 限制结果数量
     * @returns {Promise}
     */
    searchFiles(pattern, path = '.', limit = 100) {
        const params = new URLSearchParams({
            pattern,
            path,
            limit: limit.toString(),
        });
        return fetch(`/api/files/search?${params}`)
            .then(res => res.json());
    },

    /**
     * 获取文件信息
     * @param {string} path - 文件路径
     * @returns {Promise}
     */
    getFileInfo(path) {
        const params = new URLSearchParams({ path });
        return fetch(`/api/files/info?${params}`)
            .then(res => res.json());
    },

    /**
     * Glob 模式查询
     * @param {string} pattern - Glob 模式
     * @param {string} path - 搜索目录
     * @param {number} limit - 限制结果数量
     * @returns {Promise}
     */
    globFiles(pattern, path = '.', limit = 100) {
        return fetch('/api/files/glob', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ pattern, path, limit }),
        }).then(res => res.json());
    },
};

// 导出到全局
window.FileExplorerAPI = FileExplorerAPI;
