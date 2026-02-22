/**
 * ReadRenderer - 文件读取工具渲染器
 * v0.5.3.2 - 核心工具渲染器
 *
 * 用于渲染 Read 工具的输入参数（tool_use）
 * 结果内容（tool_result）由 FileContentRenderer 渲染
 */

import { BaseRenderer } from './base.js';

// 使用全局 CopyButton（由 copyButton.js 挂载到 window）
const CopyButton = window.CopyButton;

/**
 * Read 工具输入渲染器
 * 显示文件路径、语言标识、读取范围等信息
 */
export const ReadRenderer = {
    /**
     * 渲染 Read 工具输入
     * @param {Object} input - 工具输入参数
     * @param {string} input.file_path - 文件路径
     * @param {number} [input.offset] - 起始行号
     * @param {number} [input.limit] - 读取行数限制
     * @returns {HTMLElement|null}
     */
    render(input) {
        if (!input || !input.file_path) {
            return null;
        }

        const fileName = BaseRenderer.getFileName(input.file_path);
        const fullFileName = this._getFullFileName(input.file_path);
        const ext = BaseRenderer.getFileExtension(input.file_path);
        const language = ext ? BaseRenderer.getLanguageFromExt(ext) : null;

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 创建卡片
        const card = document.createElement('div');
        card.className = 'read-tool-card bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 创建头部
        const header = BaseRenderer.createHeader({
            icon: '📄',
            iconClass: 'text-sky-400',
            title: fileName,
            titleClass: 'font-mono text-zinc-300 cursor-pointer hover:text-cyan-400 transition-colors',
            badges: language ? [{ text: language, class: 'text-zinc-400' }] : [],
            extraContent: this._createExtraContent(input)
        });

        // 添加 title 属性显示完整路径
        const titleEl = header.querySelector('.tool-title');
        if (titleEl) {
            titleEl.title = fullFileName;
            // 添加点击事件复制完整路径
            titleEl.style.cursor = 'pointer';
            titleEl.addEventListener('click', (e) => {
                e.stopPropagation();
                CopyButton.handleCopy(titleEl, input.file_path, 1500);
            });
        }

        // 如果有读取范围参数，添加参数说明区域
        if (input.offset || input.limit) {
            const paramsEl = this._createParamsSection(input);
            card.appendChild(paramsEl);
        }

        card.appendChild(header);
        container.appendChild(card);

        return container;
    },

    /**
     * 获取完整文件名（显示最后两级目录）
     * @param {string} filePath - 文件路径
     * @returns {string}
     */
    _getFullFileName(filePath) {
        if (!filePath) return '';
        const parts = filePath.replace(/\\/g, '/').split('/');
        return parts.slice(-2).join('/');
    },

    /**
     * 创建额外内容（行号信息、复制按钮）
     * @param {Object} input - 输入参数
     * @returns {HTMLElement[]}
     */
    _createExtraContent(input) {
        const extras = [];

        // 行号范围信息
        if (input.offset || input.limit) {
            const info = document.createElement('span');
            info.className = 'text-xs text-zinc-500 mr-2';

            const parts = [];
            if (input.offset) {
                parts.push(`从第 ${input.offset} 行`);
            }
            if (input.limit) {
                parts.push(`读取 ${input.limit} 行`);
            }
            info.textContent = parts.join('，');
            extras.push(info);
        }

        // 复制路径按钮
        const copyBtn = CopyButton.create(input.file_path, {
            title: '复制路径',
            copiedTitle: '已复制'
        });
        copyBtn.classList.add('p-1', 'hover:bg-zinc-700/50', 'rounded', 'transition-colors');
        extras.push(copyBtn);

        return extras;
    },

    /**
     * 创建参数说明区域
     * @param {Object} input - 输入参数
     * @returns {HTMLElement}
     */
    _createParamsSection(input) {
        const section = document.createElement('div');
        section.className = 'read-params-section px-3 py-2 border-b border-zinc-700/50 bg-zinc-800/20 text-xs text-zinc-400';

        const params = [];

        if (input.offset) {
            params.push(`<span class="text-zinc-500">offset:</span> <span class="text-amber-400">${input.offset}</span>`);
        }
        if (input.limit) {
            params.push(`<span class="text-zinc-500">limit:</span> <span class="text-emerald-400">${input.limit}</span>`);
        }

        section.innerHTML = params.join(' <span class="text-zinc-600 mx-1">|</span> ');
        return section;
    }
};

/**
 * FileContentRenderer - 文件内容渲染器
 * 显示文件内容，带行号、展开/收起功能
 * v0.5.3.2 - 核心工具渲染器
 */
export const FileContentRenderer = {
    // 默认截断行数
    DEFAULT_MAX_LINES: 30,

    /**
     * 渲染文件内容
     * @param {Object} options - 配置选项
     * @param {string} options.content - 文件内容
     * @param {string} [options.fileName] - 文件名
     * @param {number} [options.maxLines] - 最大显示行数（默认 30）
     * @param {boolean} [options.showCopyButton=true] - 是否显示复制按钮
     * @param {boolean} [options.enableHighlight=false] - 是否启用语法高亮
     * @returns {HTMLElement|null}
     */
    render(options) {
        const {
            content,
            fileName,
            maxLines = this.DEFAULT_MAX_LINES,
            showCopyButton = true,
            enableHighlight = false
        } = options;

        if (!content) {
            return null;
        }

        const lines = content.split('\n');
        const truncated = lines.length > maxLines;

        const ext = fileName ? BaseRenderer.getFileExtension(fileName) : '';
        const language = ext ? BaseRenderer.getLanguageFromExt(ext) : null;

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 创建卡片
        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 创建头部
        const headerExtras = [this._createLineCount(lines.length)];
        if (showCopyButton) {
            headerExtras.push(this._createCopyButton(content));
        }

        const header = BaseRenderer.createHeader({
            icon: '📄',
            iconClass: 'text-sky-400',
            title: 'File Content',
            badges: language ? [{ text: language }] : [],
            extraContent: headerExtras
        });

        // 创建内容区域
        const contentEl = document.createElement('div');
        contentEl.className = 'file-content-wrapper overflow-x-auto overflow-y-auto';
        contentEl.dataset.expanded = 'false';
        contentEl.dataset.maxLines = maxLines;
        contentEl.dataset.fullContent = content;

        // 创建表格（带行号）- 初始只显示截断的内容
        const displayLines = truncated ? lines.slice(0, maxLines) : lines;
        const table = this._createLineTable(displayLines, enableHighlight, ext);
        table.className = 'file-content-table w-full text-xs font-mono';
        contentEl.appendChild(table);

        // 展开更多/收起按钮区域
        if (truncated) {
            const toggleWrapper = document.createElement('div');
            toggleWrapper.className = 'file-content-toggle px-3 py-2 text-xs border-t border-zinc-700/50 flex items-center justify-between';

            const infoEl = document.createElement('span');
            infoEl.className = 'text-zinc-500 file-content-info';
            infoEl.textContent = `... ${lines.length - maxLines} more lines`;

            const toggleBtn = document.createElement('button');
            toggleBtn.type = 'button';
            toggleBtn.className = 'file-content-toggle-btn text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1';
            toggleBtn.innerHTML = '<span>展开更多</span><span class="toggle-icon">▼</span>';
            toggleBtn.addEventListener('click', () => this._toggleContent(contentEl, lines, enableHighlight, ext));

            toggleWrapper.appendChild(infoEl);
            toggleWrapper.appendChild(toggleBtn);
            contentEl.appendChild(toggleWrapper);
        }

        card.appendChild(header);
        card.appendChild(contentEl);
        container.appendChild(card);

        return container;
    },

    /**
     * 创建复制按钮
     * @param {string} content - 要复制的内容
     * @returns {HTMLButtonElement}
     */
    _createCopyButton(content) {
        const btn = CopyButton.create(content, {
            title: '复制内容',
            copiedTitle: '已复制'
        });
        btn.classList.add('p-1', 'hover:bg-zinc-700/50', 'rounded', 'transition-colors');
        return btn;
    },

    /**
     * 创建行数显示
     * @param {number} count - 行数
     * @returns {HTMLElement}
     */
    _createLineCount(count) {
        const el = document.createElement('span');
        el.className = 'text-xs text-zinc-500 ml-auto';
        el.textContent = `${count} lines`;
        return el;
    },

    /**
     * 创建带行号的表格
     * @param {string[]} lines - 行内容数组
     * @param {boolean} enableHighlight - 是否启用语法高亮
     * @param {string} ext - 文件扩展名
     * @returns {HTMLTableElement}
     */
    _createLineTable(lines, enableHighlight = false, ext = '') {
        const table = document.createElement('table');
        table.className = 'w-full text-xs font-mono';

        const tbody = document.createElement('tbody');

        lines.forEach((line, index) => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-zinc-800/30';

            // 行号
            const tdNum = document.createElement('td');
            tdNum.className = 'select-none text-right pr-3 pl-3 py-0.5 text-zinc-600 border-r border-zinc-800 w-10 sticky left-0 bg-zinc-900/70';
            tdNum.textContent = index + 1;

            // 内容
            const tdContent = document.createElement('td');
            tdContent.className = 'pl-3 pr-3 py-0.5 text-zinc-300 whitespace-pre';

            // 语法高亮接口：如果启用了高亮且有 highlight.js，则使用
            if (enableHighlight && typeof hljs !== 'undefined' && ext) {
                const langClass = this._getHighlightJsLanguage(ext);
                if (langClass) {
                    tdContent.innerHTML = this._highlightLine(line, langClass);
                } else {
                    tdContent.textContent = line || ' ';
                }
            } else {
                tdContent.textContent = line || ' ';
            }

            tr.appendChild(tdNum);
            tr.appendChild(tdContent);
            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        return table;
    },

    /**
     * 切换内容展开/收起状态
     * @param {HTMLElement} contentEl - 内容容器元素
     * @param {string[]} lines - 所有行内容
     * @param {boolean} enableHighlight - 是否启用语法高亮
     * @param {string} ext - 文件扩展名
     */
    _toggleContent(contentEl, lines, enableHighlight, ext) {
        const isExpanded = contentEl.dataset.expanded === 'true';
        const maxLines = parseInt(contentEl.dataset.maxLines, 10);
        const table = contentEl.querySelector('.file-content-table');
        const infoEl = contentEl.querySelector('.file-content-info');
        const toggleBtn = contentEl.querySelector('.file-content-toggle-btn');
        const toggleIcon = toggleBtn.querySelector('.toggle-icon');

        if (isExpanded) {
            // 收起
            const displayLines = lines.slice(0, maxLines);
            const newTable = this._createLineTable(displayLines, enableHighlight, ext);
            newTable.className = 'file-content-table w-full text-xs font-mono';
            table.replaceWith(newTable);

            infoEl.textContent = `... ${lines.length - maxLines} more lines`;
            toggleBtn.querySelector('span:not(.toggle-icon)').textContent = '展开更多';
            toggleIcon.textContent = '▼';
            contentEl.dataset.expanded = 'false';

            // 移除高度限制
            contentEl.style.maxHeight = '24rem';
        } else {
            // 展开
            const newTable = this._createLineTable(lines, enableHighlight, ext);
            newTable.className = 'file-content-table w-full text-xs font-mono';
            table.replaceWith(newTable);

            infoEl.textContent = `共 ${lines.length} 行`;
            toggleBtn.querySelector('span:not(.toggle-icon)').textContent = '收起';
            toggleIcon.textContent = '▲';
            contentEl.dataset.expanded = 'true';

            // 移除高度限制以显示全部内容
            contentEl.style.maxHeight = 'none';
        }
    },

    /**
     * 获取 highlight.js 语言标识
     * @param {string} ext - 文件扩展名
     * @returns {string|null}
     */
    _getHighlightJsLanguage(ext) {
        const langMap = {
            'js': 'javascript',
            'jsx': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'py': 'python',
            'rb': 'ruby',
            'go': 'go',
            'rs': 'rust',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'css': 'css',
            'scss': 'scss',
            'html': 'html',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'sql': 'sql',
            'sh': 'bash',
            'bash': 'bash',
            'toml': 'toml',
            'xml': 'xml'
        };
        return langMap[ext] || null;
    },

    /**
     * 对单行代码进行语法高亮
     * @param {string} line - 代码行
     * @param {string} langClass - 语言类名
     * @returns {string}
     */
    _highlightLine(line, langClass) {
        if (!line) return ' ';
        try {
            // 使用 highlight.js 高亮（如果可用）
            if (typeof hljs !== 'undefined') {
                const result = hljs.highlight(line, { language: langClass, ignoreIllegals: true });
                return result.value;
            }
        } catch (e) {
            // 高亮失败，返回原始文本
        }
        return BaseRenderer.escapeHtml(line);
    }
};

// 默认导出
export default { ReadRenderer, FileContentRenderer };
