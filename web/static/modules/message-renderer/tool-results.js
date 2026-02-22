/**
 * 工具结果渲染器模块
 * 专门处理各种工具结果类型的渲染
 */

const MessageRendererToolResults = {
    /**
     * 工具结果样式配置
     */
    _toolResultStyles: {
        Read: {
            icon: '📄',
            class: 'tool-result-read',
            label: '文件内容',
            maxLength: 2000,
        },
        Write: {
            icon: '✍️',
            class: 'tool-result-write',
            label: '写入成功',
            maxLength: 500,
        },
        Edit: {
            icon: '✏️',
            class: 'tool-result-edit',
            label: '编辑成功',
            maxLength: 500,
        },
        Bash: {
            icon: '💻',
            class: 'tool-result-bash',
            label: '终端输出',
            maxLength: 3000,
        },
        Glob: {
            icon: '📁',
            class: 'tool-result-glob',
            label: '文件列表',
            maxLength: 1500,
        },
        Grep: {
            icon: '🔍',
            class: 'tool-result-grep',
            label: '搜索结果',
            maxLength: 2000,
        },
        WebSearch: {
            icon: '🌐',
            class: 'tool-result-web',
            label: '搜索结果',
            maxLength: 3000,
        },
        WebFetch: {
            icon: '📥',
            class: 'tool-result-web',
            label: '网页内容',
            maxLength: 5000,
        },
        Task: {
            icon: '🤖',
            class: 'tool-result-task',
            label: '子代理结果',
            maxLength: 2000,
        },
    },

    /**
     * 获取工具结果样式配置
     * @param {string} toolName - 工具名称
     * @returns {Object} 样式配置
     */
    _getToolResultStyle(toolName) {
        return this._toolResultStyles[toolName] || {
            icon: '🔧',
            class: 'tool-result-default',
            label: '结果',
            maxLength: 500,
        };
    },

    /**
     * 根据工具类型渲染结果
     * @param {string} toolName - 工具名称
     * @param {Object} style - 样式配置
     * @param {boolean} isError - 是否错误
     * @param {string} displayContent - 显示内容（已截断）
     * @param {string} fullContent - 完整内容
     * @returns {string} 渲染后的 HTML
     */
    _renderToolResultByType(toolName, style, isError, displayContent, fullContent) {
        const baseClass = isError ? 'assistant-msg-error' : `assistant-msg ${style.class}`;

        // 特殊处理：Read 工具显示代码行号
        if (toolName === 'Read') {
            return this._renderReadResult(baseClass, style, isError, displayContent, fullContent);
        }

        // 特殊处理：Bash 工具显示终端样式
        if (toolName === 'Bash') {
            return this._renderBashResult(baseClass, style, isError, displayContent, fullContent);
        }

        // 特殊处理：Grep 工具显示行号和高亮
        if (toolName === 'Grep') {
            return this._renderGrepResult(baseClass, style, isError, displayContent, fullContent);
        }

        // 特殊处理：Glob 工具显示文件列表
        if (toolName === 'Glob') {
            return this._renderGlobResult(baseClass, style, isError, displayContent, fullContent);
        }

        // 默认渲染
        const label = isError ? '❌ 错误' : `${style.icon} ${style.label}`;

        return `
            <div class="${baseClass}">
                <span class="result-label">${label}</span>
                <div class="result-content">
                    <pre>${Utils.escapeHtml(displayContent)}</pre>
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Read 工具结果（代码风格）
     */
    _renderReadResult(baseClass, style, isError, displayContent, fullContent) {
        const lines = displayContent.split('\n');

        const linesHtml = lines.map((line, index) => {
            const lineNum = index + 1;
            const lineClass = lineNum % 2 === 0 ? 'line-even' : 'line-odd';
            return `<div class="code-line ${lineClass}"><span class="line-number">${lineNum}</span><span class="line-content">${Utils.escapeHtml(line)}</span></div>`;
        }).join('');

        return `
            <div class="${baseClass}">
                <span class="result-label">${style.icon} ${style.label}</span>
                <div class="result-content code-block">
                    <div class="code-lines">${linesHtml}</div>
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Bash 工具结果（终端风格）
     */
    _renderBashResult(baseClass, style, isError, displayContent, fullContent) {
        return `
            <div class="${baseClass}">
                <span class="result-label">${style.icon} ${style.label}</span>
                <div class="result-content terminal-block">
                    <div class="terminal-prompt"><span class="prompt-symbol">❯</span> bash</div>
                    <pre class="terminal-output">${Utils.escapeHtml(displayContent)}</pre>
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Grep 工具结果（搜索结果风格）
     */
    _renderGrepResult(baseClass, style, isError, displayContent, fullContent) {
        const lines = displayContent.split('\n');

        const linesHtml = lines.map((line) => {
            // 匹配文件名:行号:内容的格式
            const match = line.match(/^([^:]+):(\d+):(.*)$/);
            if (match) {
                const [, file, lineNum, content] = match;
                return `<div class="grep-line"><span class="grep-file">${Utils.escapeHtml(file)}</span>:<span class="grep-line-num">${lineNum}</span>:<span class="grep-content">${Utils.escapeHtml(content)}</span></div>`;
            }
            return `<div class="grep-line"><span class="grep-content">${Utils.escapeHtml(line)}</span></div>`;
        }).join('');

        return `
            <div class="${baseClass}">
                <span class="result-label">${style.icon} ${style.label}</span>
                <div class="result-content grep-block">
                    <div class="grep-lines">${linesHtml}</div>
                </div>
            </div>
        `;
    },

    /**
     * 渲染 Glob 工具结果（文件列表风格）
     */
    _renderGlobResult(baseClass, style, isError, displayContent, fullContent) {
        const files = displayContent.split('\n').filter(f => f.trim());

        const filesHtml = files.map(file => {
            const ext = file.split('.').pop() || '';
            const icon = this._getFileIcon(ext);
            return `<div class="file-item"><span class="file-icon">${icon}</span><span class="file-path">${Utils.escapeHtml(file)}</span></div>`;
        }).join('');

        return `
            <div class="${baseClass}">
                <span class="result-label">${style.icon} ${style.label} (${files.length} 个文件)</span>
                <div class="result-content files-block">
                    <div class="files-list">${filesHtml}</div>
                </div>
            </div>
        `;
    },

    /**
     * 获取文件图标
     */
    _getFileIcon(ext) {
        const iconMap = {
            js: '🟨',
            ts: '🔷',
            py: '🐍',
            json: '📋',
            md: '📝',
            html: '🌐',
            css: '🎨',
            txt: '📄',
            yml: '⚙️',
            yaml: '⚙️',
            toml: '⚙️',
            gitignore: '🔒',
            env: '🔐',
        };
        return iconMap[ext] || '📄';
    }
};

// 导出到全局命名空间
window.MessageRendererToolResults = MessageRendererToolResults;