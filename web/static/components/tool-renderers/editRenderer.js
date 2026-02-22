/**
 * EditRenderer / WriteRenderer - 编辑/写入工具渲染器
 * v0.5.3.3 - 编辑工具渲染器
 * v0.5.7 - Diff 可视化支持
 */

import { BaseRenderer } from './base.js';

// 使用全局 CopyButton（由 copyButton.js 挂载到 window）
const CopyButton = window.CopyButton;

/**
 * DiffHelper - Diff 解析和渲染辅助工具
 */
const DiffHelper = {
    /**
     * 检查 jsdiff 库是否可用
     * @returns {boolean}
     */
    isDiffAvailable() {
        return typeof Diff !== 'undefined' && Diff.createTwoFilesPatch;
    },

    /**
     * 解析 diff 文本为结构化数据
     * @param {string} diffText - unified diff 格式的文本
     * @returns {Array<{type: string, content: string, oldLine?: number, newLine?: number}>}
     */
    parseDiff(diffText) {
        const lines = diffText.split('\n');
        const result = [];
        let oldLineNum = 0;
        let newLineNum = 0;

        for (const line of lines) {
            // 解析 hunk header (@@ -start,count +start,count @@)
            if (line.startsWith('@@')) {
                const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
                if (match) {
                    oldLineNum = parseInt(match[1], 10);
                    newLineNum = parseInt(match[2], 10);
                }
                result.push({ type: 'header', content: line });
                continue;
            }

            // 跳过文件头
            if (line.startsWith('---') || line.startsWith('+++') || line.startsWith('diff --git') || line.startsWith('index ')) {
                continue;
            }

            // 添加行
            if (line.startsWith('+')) {
                result.push({
                    type: 'add',
                    content: line.slice(1),
                    newLine: newLineNum++
                });
                continue;
            }

            // 删除行
            if (line.startsWith('-')) {
                result.push({
                    type: 'remove',
                    content: line.slice(1),
                    oldLine: oldLineNum++
                });
                continue;
            }

            // 上下文行
            if (line.startsWith(' ') || line === '') {
                result.push({
                    type: 'context',
                    content: line.startsWith(' ') ? line.slice(1) : '',
                    oldLine: oldLineNum++,
                    newLine: newLineNum++
                });
            }
        }

        return result;
    },

    /**
     * 计算差异统计
     * @param {Array} parsedLines - 解析后的差异行
     * @returns {{added: number, removed: number}}
     */
    calculateStats(parsedLines) {
        return {
            added: parsedLines.filter(l => l.type === 'add').length,
            removed: parsedLines.filter(l => l.type === 'remove').length
        };
    },

    /**
     * 生成 unified diff
     * @param {string} fileName - 文件名
     * @param {string} oldStr - 原始字符串
     * @param {string} newStr - 新字符串
     * @param {number} context - 上下文行数
     * @returns {string|null}
     */
    createPatch(fileName, oldStr, newStr, context = 3) {
        if (!this.isDiffAvailable()) {
            return null;
        }

        try {
            return Diff.createTwoFilesPatch(
                `a/${fileName}`,
                `b/${fileName}`,
                oldStr || '',
                newStr || '',
                '',
                '',
                { context }
            );
        } catch (e) {
            console.error('Diff 生成失败:', e);
            return null;
        }
    },

    /**
     * 检测是否需要折叠（差异行数过多）
     * @param {Array} parsedLines - 解析后的差异行
     * @param {number} threshold - 阈值
     * @returns {boolean}
     */
    needsCollapse(parsedLines, threshold = 30) {
        return parsedLines.length > threshold;
    }
};

/**
 * EditRenderer - 文件编辑结果渲染器
 *
 * 功能：
 * - 显示文件路径（最后两级目录）
 * - 使用 jsdiff 生成 unified diff
 * - 渲染差异结果（添加/删除/上下文行）
 * - 显示行号
 * - 支持长差异折叠
 */
export const EditRenderer = {
    /**
     * 渲染 Edit 工具输入
     * @param {Object} input - 工具输入参数
     * @param {string} input.file_path - 文件路径
     * @param {string} input.old_string - 原始字符串
     * @param {string} input.new_string - 新字符串
     * @returns {HTMLElement|null}
     */
    render(input) {
        if (!input || !input.file_path) {
            return null;
        }

        const { file_path, old_string = '', new_string = '' } = input;
        const fileName = BaseRenderer.getFileName(file_path);

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 创建卡片
        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 尝试使用 Diff 可视化
        const diffText = DiffHelper.createPatch(fileName, old_string, new_string, 3);

        if (diffText) {
            // 使用 Diff 可视化渲染
            const parsedLines = DiffHelper.parseDiff(diffText);
            const stats = DiffHelper.calculateStats(parsedLines);

            // 创建头部
            const header = this._createHeader(fileName, stats, new_string);
            card.appendChild(header);

            // 创建 Diff 内容
            const diffContent = this._createDiffContent(parsedLines);
            card.appendChild(diffContent);
        } else {
            // 降级为预览模式
            const oldLines = old_string ? old_string.split('\n') : [];
            const newLines = new_string ? new_string.split('\n') : [];
            const stats = {
                added: newLines.length,
                removed: oldLines.length
            };

            // 创建头部
            const header = this._createHeader(fileName, stats, new_string);
            card.appendChild(header);

            // 创建预览内容
            const previewContent = this._createPreviewContent(old_string, new_string);
            if (previewContent) {
                card.appendChild(previewContent);
            }
        }

        container.appendChild(card);

        // 保存数据
        container.dataset.editData = JSON.stringify({
            file_path,
            old_string,
            new_string,
            hasDiffSupport: DiffHelper.isDiffAvailable()
        });

        return container;
    },

    /**
     * 创建头部
     * @param {string} fileName - 文件名
     * @param {{added: number, removed: number}} stats - 统计信息
     * @param {string} newString - 新字符串（用于复制）
     * @returns {HTMLElement}
     */
    _createHeader(fileName, stats, newString) {
        const header = BaseRenderer.createHeader({
            icon: '✏️',
            iconClass: 'text-blue-400',
            title: fileName,
            titleClass: 'font-mono text-zinc-300',
            extraContent: []
        });

        // 创建右侧统计区域
        const statsWrapper = document.createElement('div');
        statsWrapper.className = 'flex items-center gap-2 ml-auto';

        // 添加行数 (+)
        if (stats.added > 0) {
            const addedBadge = document.createElement('span');
            addedBadge.className = 'flex items-center gap-0.5 text-xs text-emerald-400';
            addedBadge.innerHTML = `<span>+</span><span>${stats.added}</span>`;
            statsWrapper.appendChild(addedBadge);
        }

        // 删除行数 (-)
        if (stats.removed > 0) {
            const removedBadge = document.createElement('span');
            removedBadge.className = 'flex items-center gap-0.5 text-xs text-rose-400';
            removedBadge.innerHTML = `<span>-</span><span>${stats.removed}</span>`;
            statsWrapper.appendChild(removedBadge);
        }

        // 复制按钮（复制 new_string）
        const copyBtn = CopyButton.create(newString, {
            title: '复制新内容',
            copiedTitle: '已复制'
        });
        copyBtn.classList.add('p-1', 'hover:bg-zinc-700/50', 'rounded', 'transition-colors');
        statsWrapper.appendChild(copyBtn);

        header.appendChild(statsWrapper);
        return header;
    },

    /**
     * 创建 Diff 内容区域
     * @param {Array} parsedLines - 解析后的差异行
     * @returns {HTMLElement}
     */
    _createDiffContent(parsedLines) {
        const wrapper = document.createElement('div');
        wrapper.className = 'diff-content-wrapper overflow-x-auto max-h-80 overflow-y-auto';
        wrapper.dataset.expanded = 'false';

        const pre = document.createElement('div');
        pre.className = 'text-xs font-mono p-0';

        // 检查是否需要折叠
        const needsCollapse = DiffHelper.needsCollapse(parsedLines, 30);
        const displayLines = needsCollapse ? parsedLines.slice(0, 30) : parsedLines;
        const hiddenCount = parsedLines.length - displayLines.length;

        displayLines.forEach((line, index) => {
            const lineEl = this._createDiffLine(line, index);
            pre.appendChild(lineEl);
        });

        wrapper.appendChild(pre);

        // 添加展开更多按钮
        if (needsCollapse) {
            const expandBtn = this._createExpandButton(wrapper, parsedLines, 30);
            wrapper.appendChild(expandBtn);

            // 添加折叠提示
            const hint = document.createElement('div');
            hint.className = 'diff-collapse-hint px-3 py-1 text-xs text-zinc-500 bg-zinc-800/50 border-t border-zinc-700/30';
            hint.textContent = `... 还有 ${hiddenCount} 行差异`;
            wrapper.appendChild(hint);
        }

        return wrapper;
    },

    /**
     * 创建单行差异元素
     * @param {Object} line - 行数据
     * @param {number} index - 索引
     * @returns {HTMLElement}
     */
    _createDiffLine(line, index) {
        const lineEl = document.createElement('div');
        lineEl.className = 'diff-line flex';

        if (line.type === 'header') {
            // hunk header
            lineEl.className += ' diff-hunk-header';
            lineEl.innerHTML = `
                <span class="diff-header-content px-3 py-1 bg-sky-900/20 text-sky-300 border-y border-sky-900/30 w-full">
                    ${BaseRenderer.escapeHtml(line.content)}
                </span>
            `;
            return lineEl;
        }

        // 行号列
        const lineNumCol = document.createElement('span');
        lineNumCol.className = 'diff-line-numbers flex select-none border-r border-zinc-700/30 bg-zinc-900/50';

        // 旧行号
        const oldNum = document.createElement('span');
        oldNum.className = 'diff-old-num min-w-[2rem] text-right pr-2 text-zinc-600';
        oldNum.textContent = line.oldLine || '';

        // 新行号
        const newNum = document.createElement('span');
        newNum.className = 'diff-new-num min-w-[2rem] text-right pr-2 text-zinc-600';
        newNum.textContent = line.newLine || '';

        lineNumCol.appendChild(oldNum);
        lineNumCol.appendChild(newNum);

        // 内容列
        const contentCol = document.createElement('span');
        contentCol.className = 'diff-line-content flex-1 px-2 py-0.5 whitespace-pre-wrap';

        if (line.type === 'add') {
            lineEl.className += ' diff-line-add';
            lineEl.classList.add('bg-emerald-900/20');
            contentCol.innerHTML = `
                <span class="select-none text-emerald-600 mr-2">+</span>
                <span class="text-emerald-300">${BaseRenderer.escapeHtml(line.content) || ' '}</span>
            `;
            lineEl.style.borderLeft = '2px solid #10b981';
        } else if (line.type === 'remove') {
            lineEl.className += ' diff-line-remove';
            lineEl.classList.add('bg-rose-900/20');
            contentCol.innerHTML = `
                <span class="select-none text-rose-600 mr-2">-</span>
                <span class="text-rose-300">${BaseRenderer.escapeHtml(line.content) || ' '}</span>
            `;
            lineEl.style.borderLeft = '2px solid #f43f5e';
        } else {
            // context
            lineEl.className += ' diff-line-context';
            contentCol.innerHTML = `
                <span class="select-none text-zinc-600 mr-2"> </span>
                <span class="text-zinc-400">${BaseRenderer.escapeHtml(line.content) || ' '}</span>
            `;
        }

        lineEl.appendChild(lineNumCol);
        lineEl.appendChild(contentCol);

        return lineEl;
    },

    /**
     * 创建展开按钮
     * @param {HTMLElement} wrapper - 包装器元素
     * @param {Array} allLines - 所有差异行
     * @param {number} initialCount - 初始显示数量
     * @returns {HTMLElement}
     */
    _createExpandButton(wrapper, allLines, initialCount) {
        const btn = document.createElement('button');
        btn.className = 'diff-expand-btn w-full px-3 py-2 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/30 transition-colors flex items-center justify-center gap-1 border-t border-zinc-700/30';
        btn.innerHTML = `
            <span class="expand-icon">▼</span>
            <span class="expand-text">展开全部差异 (${allLines.length} 行)</span>
        `;

        let expanded = false;
        btn.addEventListener('click', () => {
            if (!expanded) {
                // 展开
                wrapper.dataset.expanded = 'true';
                const pre = wrapper.querySelector('.font-mono');
                pre.innerHTML = '';

                allLines.forEach((line, index) => {
                    const lineEl = this._createDiffLine(line, index);
                    pre.appendChild(lineEl);
                });

                // 隐藏折叠提示
                const hint = wrapper.querySelector('.diff-collapse-hint');
                if (hint) hint.style.display = 'none';

                btn.innerHTML = `
                    <span class="expand-icon">▲</span>
                    <span class="expand-text">收起差异</span>
                `;
                expanded = true;
            } else {
                // 收起
                wrapper.dataset.expanded = 'false';
                const pre = wrapper.querySelector('.font-mono');
                pre.innerHTML = '';

                allLines.slice(0, initialCount).forEach((line, index) => {
                    const lineEl = this._createDiffLine(line, index);
                    pre.appendChild(lineEl);
                });

                // 显示折叠提示
                const hint = wrapper.querySelector('.diff-collapse-hint');
                if (hint) hint.style.display = 'block';

                btn.innerHTML = `
                    <span class="expand-icon">▼</span>
                    <span class="expand-text">展开全部差异 (${allLines.length} 行)</span>
                `;
                expanded = false;
            }
        });

        return btn;
    },

    /**
     * 创建预览内容区域（降级模式）
     * @param {string} oldStr - 原始字符串
     * @param {string} newStr - 新字符串
     * @returns {HTMLElement|null}
     */
    _createPreviewContent(oldStr, newStr) {
        if (!oldStr && !newStr) return null;

        const contentEl = document.createElement('div');
        contentEl.className = 'overflow-x-auto max-h-80 overflow-y-auto';

        const pre = document.createElement('pre');
        pre.className = 'text-xs font-mono p-0';

        // 显示 old_string 预览（前 3 行）
        if (oldStr) {
            const oldLines = oldStr.split('\n').slice(0, 3);
            const hasMoreOld = oldStr.split('\n').length > 3;

            oldLines.forEach(line => {
                const div = document.createElement('div');
                div.className = 'px-3 py-0.5 bg-rose-900/20 text-rose-300 border-l-2 border-rose-500';
                div.innerHTML = `<span class="select-none text-rose-600 mr-2">-</span>${BaseRenderer.escapeHtml(line) || ' '}`;
                pre.appendChild(div);
            });

            if (hasMoreOld) {
                const moreEl = document.createElement('div');
                moreEl.className = 'px-3 py-0.5 text-rose-500/50 text-[10px]';
                moreEl.textContent = `... ${oldStr.split('\n').length - 3} more lines`;
                pre.appendChild(moreEl);
            }
        }

        // 显示 new_string 预览（前 3 行）
        if (newStr) {
            const newLines = newStr.split('\n').slice(0, 3);
            const hasMoreNew = newStr.split('\n').length > 3;

            newLines.forEach(line => {
                const div = document.createElement('div');
                div.className = 'px-3 py-0.5 bg-emerald-900/20 text-emerald-300 border-l-2 border-emerald-500';
                div.innerHTML = `<span class="select-none text-emerald-600 mr-2">+</span>${BaseRenderer.escapeHtml(line) || ' '}`;
                pre.appendChild(div);
            });

            if (hasMoreNew) {
                const moreEl = document.createElement('div');
                moreEl.className = 'px-3 py-0.5 text-emerald-500/50 text-[10px]';
                moreEl.textContent = `... ${newStr.split('\n').length - 3} more lines`;
                pre.appendChild(moreEl);
            }
        }

        contentEl.appendChild(pre);
        return contentEl;
    }
};

/**
 * WriteRenderer - 文件写入结果渲染器
 *
 * 功能：
 * - 显示文件路径（最后两级目录）
 * - 显示写入内容预览（前 10 行）
 * - 显示写入总行数
 * - 添加 CopyButton（复制完整内容）
 */
export const WriteRenderer = {
    /**
     * 渲染 Write 工具输入
     * @param {Object} input - 工具输入参数
     * @param {string} input.file_path - 文件路径
     * @param {string} input.content - 写入内容
     * @returns {HTMLElement|null}
     */
    render(input) {
        if (!input || !input.file_path) {
            return null;
        }

        const { file_path, content = '' } = input;
        const fileName = BaseRenderer.getFileName(file_path);
        const ext = BaseRenderer.getFileExtension(file_path);
        const language = BaseRenderer.getLanguageFromExt(ext);

        // 计算行数
        const lines = content.split('\n');
        const lineCount = lines.length;

        // 创建容器
        const container = BaseRenderer.createContainer();

        // 创建卡片
        const card = document.createElement('div');
        card.className = 'bg-zinc-900/70 border border-zinc-700/50 rounded-lg overflow-hidden';

        // 创建头部
        const header = BaseRenderer.createHeader({
            icon: '📝',
            iconClass: 'text-emerald-400',
            title: fileName,
            titleClass: 'font-mono text-zinc-300',
            badges: language ? [{ text: language, class: 'text-emerald-400 bg-emerald-400/10' }] : [],
            extraContent: []
        });

        // 创建右侧统计区域
        const statsWrapper = document.createElement('div');
        statsWrapper.className = 'flex items-center gap-2 ml-auto';

        // 行数统计
        const linesBadge = document.createElement('span');
        linesBadge.className = 'text-xs text-zinc-500';
        linesBadge.textContent = `${lineCount} lines`;
        statsWrapper.appendChild(linesBadge);

        // 复制按钮（复制完整内容）
        const copyBtn = CopyButton.create(content, {
            title: '复制内容',
            copiedTitle: '已复制'
        });
        copyBtn.classList.add('p-1', 'hover:bg-zinc-700/50', 'rounded', 'transition-colors');
        statsWrapper.appendChild(copyBtn);

        header.appendChild(statsWrapper);
        card.appendChild(header);

        // 创建内容预览区域
        const contentArea = this._createContentPreview(content, lines);
        if (contentArea) {
            card.appendChild(contentArea);
        }

        container.appendChild(card);
        return container;
    },

    /**
     * 创建内容预览
     * @param {string} content - 完整内容
     * @param {string[]} lines - 行数组
     * @returns {HTMLElement|null}
     */
    _createContentPreview(content, lines) {
        if (!content) return null;

        const contentEl = document.createElement('div');
        contentEl.className = 'overflow-x-auto max-h-60 overflow-y-auto';

        const pre = document.createElement('div');
        pre.className = 'text-xs font-mono p-0';

        // 显示前 10 行
        const previewLines = 10;
        const displayLines = lines.slice(0, previewLines);
        const hasMore = lines.length > previewLines;

        displayLines.forEach((line, index) => {
            const lineEl = document.createElement('div');
            lineEl.className = 'flex px-3 py-0.5 hover:bg-zinc-800/30';

            // 行号
            const lineNum = document.createElement('span');
            lineNum.className = 'text-zinc-600 min-w-[2rem] text-right pr-3 select-none';
            lineNum.textContent = index + 1;

            // 行内容
            const lineContent = document.createElement('span');
            lineContent.className = 'text-zinc-300 whitespace-pre-wrap break-all flex-1';
            lineContent.textContent = line || ' ';

            lineEl.appendChild(lineNum);
            lineEl.appendChild(lineContent);
            pre.appendChild(lineEl);
        });

        if (hasMore) {
            const moreEl = document.createElement('div');
            moreEl.className = 'px-3 py-2 text-zinc-500 text-xs border-t border-zinc-700/30';
            moreEl.textContent = `... ${lines.length - previewLines} more lines`;
            pre.appendChild(moreEl);
        }

        contentEl.appendChild(pre);
        return contentEl;
    }
};

// 导出 DiffHelper 供其他模块使用
export { DiffHelper };

// 默认导出
export default { EditRenderer, WriteRenderer, DiffHelper };
