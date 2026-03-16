/**
 * MarkdownRenderer - Markdown 渲染组件
 * v0.5.2 - 可复用组件开发
 *
 * 依赖: marked.js (CDN), CopyButton (全局变量)
 */

const MarkdownRenderer = {
    /**
     * 渲染 Markdown 内容到指定容器
     * @param {string} content - Markdown 内容
     * @param {HTMLElement} container - 目标容器元素
     * @param {Object} options - 配置选项
     * @param {boolean} [options.breaks=true] - 是否支持换行
     * @param {boolean} [options.gfm=true] - 是否启用 GitHub Flavored Markdown
     * @param {boolean} [options.sanitize=true] - 是否转义 HTML (防 XSS)
     * @param {string} [options.className='markdown-body'] - 容器 CSS 类名
     */
    render(content, container, options = {}) {
        const {
            breaks = true,
            gfm = true,
            sanitize = true,
            className = 'markdown-body'
        } = options;

        // 检查 marked.js 是否可用
        if (typeof marked === 'undefined') {
            console.warn('MarkdownRenderer: marked.js 未加载，回退到纯文本');
            container.textContent = content;
            container.className = className;
            return;
        }

        // 配置 marked 选项
        marked.setOptions({
            breaks,
            gfm,
            // 注意: marked v5+ 已移除 sanitize 选项，需要使用自定义渲染器
        });

        // 创建自定义渲染器
        const renderer = this.createCustomRenderer();

        // 使用自定义渲染器
        const parsed = marked.parse(content, { renderer });

        // 设置容器内容
        container.innerHTML = parsed;
        container.className = className;

        // 后处理：为代码块添加复制按钮
        this.postProcess(container);
    },

    /**
     * 创建自定义 marked 渲染器
     * @returns {marked.Renderer}
     */
    createCustomRenderer() {
        const renderer = new marked.Renderer();

        // 标题渲染
        renderer.heading = (data) => {
            const { depth, text } = data;
            const sizes = {
                1: 'text-base font-semibold mt-3 mb-1.5',
                2: 'text-sm font-semibold mt-3 mb-1.5',
                3: 'text-[13px] font-medium mt-3 mb-1.5',
                4: 'text-[13px] font-medium mt-2 mb-1',
                5: 'text-[13px] font-medium mt-2 mb-1',
                6: 'text-[13px] font-medium mt-2 mb-1'
            };
            const sizeClass = sizes[depth] || sizes[6];
            return `<h${depth} class="markdown-h${depth} ${sizeClass}">${text}</h${depth}>`;
        };

        // 段落渲染
        renderer.paragraph = (text) => {
            return `<p class="markdown-p text-[13px] leading-relaxed my-2">${text}</p>`;
        };

        // 链接渲染
        renderer.link = (href, title, text) => {
            const titleAttr = title ? ` title="${title}"` : '';
            return `<a href="${href}"${titleAttr} target="_blank" rel="noopener noreferrer" class="markdown-link">${text}</a>`;
        };

        // 强调渲染
        renderer.strong = (text) => {
            return `<strong class="markdown-strong">${text}</strong>`;
        };

        renderer.em = (text) => {
            return `<em class="markdown-em">${text}</em>`;
        };

        // 行内代码渲染
        renderer.codespan = (code) => {
            return `<code class="markdown-code-inline">${code}</code>`;
        };

        // 代码块渲染 (带语言标识)
        renderer.code = (code, language) => {
            const lang = language || 'text';
            const langLabel = this.getLanguageLabel(lang);
            const prismLang = this.getPrismLanguage(lang);

            return `
                <div class="markdown-code-block" data-language="${lang}">
                    <div class="markdown-code-header">
                        <span class="markdown-code-lang">${langLabel}</span>
                        <button class="btn-tool copy-code-btn" data-code="${this.escapeHtml(code)}" title="复制代码">
                            <span class="copy-icon">📋</span>
                            <span class="copy-success" style="display: none;">✓</span>
                        </button>
                    </div>
                    <pre class="markdown-pre"><code class="language-${prismLang}">${code}</code></pre>
                </div>
            `;
        };

        // 列表渲染
        renderer.list = (body, ordered) => {
            const tag = ordered ? 'ol' : 'ul';
            return `<${tag} class="markdown-${tag}">${body}</${tag}>`;
        };

        renderer.listitem = (text) => {
            return `<li class="markdown-li">${text}</li>`;
        };

        // 引用块渲染
        renderer.blockquote = (quote) => {
            return `<blockquote class="markdown-blockquote">${quote}</blockquote>`;
        };

        // 水平线渲染
        renderer.hr = () => {
            return '<hr class="markdown-hr">';
        };

        // 表格渲染
        renderer.table = (header, body) => {
            return `
                <div class="markdown-table-wrapper">
                    <table class="markdown-table">
                        <thead class="markdown-thead">${header}</thead>
                        <tbody>${body}</tbody>
                    </table>
                </div>
            `;
        };

        renderer.tablerow = (content) => {
            return `<tr class="markdown-tr">${content}</tr>`;
        };

        renderer.tablecell = (content, flags) => {
            const tag = flags.header ? 'th' : 'td';
            const align = flags.align ? ` style="text-align:${flags.align}"` : '';
            return `<${tag} class="markdown-${tag}"${align}>${content}</${tag}>`;
        };

        return renderer;
    },

    /**
     * 后处理：为代码块绑定复制事件并应用语法高亮
     * @param {HTMLElement} container - 容器元素
     */
    postProcess(container) {
        // 绑定代码块复制按钮
        const copyButtons = container.querySelectorAll('.copy-code-btn');
        copyButtons.forEach(button => {
            const code = button.dataset.code;
            button.addEventListener('click', async (e) => {
                e.stopPropagation();
                // 使用全局 CopyButton
                if (window.CopyButton) {
                    await window.CopyButton.handleCopy(button, code, 1500);
                }
            });
        });

        // 应用 Prism.js 语法高亮
        if (typeof Prism !== 'undefined') {
            Prism.highlightAllUnder(container);
        }
    },

    /**
     * 获取语言标签（用于代码块头部）
     * @param {string} lang - 语言标识
     * @returns {string}
     */
    getLanguageLabel(lang) {
        const labels = {
            'js': 'JavaScript',
            'javascript': 'JavaScript',
            'ts': 'TypeScript',
            'typescript': 'TypeScript',
            'py': 'Python',
            'python': 'Python',
            'rb': 'Ruby',
            'ruby': 'Ruby',
            'go': 'Go',
            'rust': 'Rust',
            'java': 'Java',
            'c': 'C',
            'cpp': 'C++',
            'csharp': 'C#',
            'cs': 'C#',
            'php': 'PHP',
            'swift': 'Swift',
            'kt': 'Kotlin',
            'kotlin': 'Kotlin',
            'scala': 'Scala',
            'html': 'HTML',
            'css': 'CSS',
            'scss': 'SCSS',
            'less': 'Less',
            'json': 'JSON',
            'xml': 'XML',
            'yaml': 'YAML',
            'yml': 'YAML',
            'md': 'Markdown',
            'markdown': 'Markdown',
            'sql': 'SQL',
            'sh': 'Shell',
            'bash': 'Bash',
            'zsh': 'Zsh',
            'powershell': 'PowerShell',
            'dockerfile': 'Dockerfile',
            'docker': 'Docker',
            'makefile': 'Makefile',
            'toml': 'TOML',
            'ini': 'INI',
            'diff': 'Diff',
            'text': 'Text',
            'plaintext': 'Text'
        };
        return labels[lang.toLowerCase()] || lang.toUpperCase();
    },

    /**
     * 获取 Prism.js 语言标识
     * @param {string} lang - 语言标识
     * @returns {string}
     */
    getPrismLanguage(lang) {
        const prismMap = {
            'js': 'javascript',
            'javascript': 'javascript',
            'ts': 'typescript',
            'typescript': 'typescript',
            'py': 'python',
            'python': 'python',
            'rb': 'ruby',
            'ruby': 'ruby',
            'go': 'go',
            'rust': 'rust',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'csharp': 'csharp',
            'cs': 'csharp',
            'php': 'php',
            'swift': 'swift',
            'kt': 'kotlin',
            'kotlin': 'kotlin',
            'scala': 'scala',
            'html': 'html',
            'css': 'css',
            'scss': 'scss',
            'less': 'less',
            'json': 'json',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'markdown': 'markdown',
            'sql': 'sql',
            'sh': 'bash',
            'bash': 'bash',
            'zsh': 'bash',
            'powershell': 'powershell',
            'dockerfile': 'docker',
            'docker': 'docker',
            'makefile': 'makefile',
            'toml': 'toml',
            'ini': 'ini',
            'diff': 'diff',
            'text': 'plaintext',
            'plaintext': 'plaintext',
            'git': 'git',
        };
        return prismMap[lang.toLowerCase()] || 'plaintext';
    },

    /**
     * HTML 转义（防 XSS）
     * @param {string} text - 原始文本
     * @returns {string}
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 创建独立的 Markdown 容器
     * @param {string} content - Markdown 内容
     * @param {Object} options - 配置选项
     * @returns {HTMLDivElement}
     */
    create(content, options = {}) {
        const container = document.createElement('div');
        this.render(content, container, options);
        return container;
    },

    /**
     * 检查 marked.js 是否可用
     * @returns {boolean}
     */
    isAvailable() {
        return typeof marked !== 'undefined';
    }
};

// 挂载到全局对象
window.MarkdownRenderer = MarkdownRenderer;
