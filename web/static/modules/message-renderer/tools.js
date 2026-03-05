/**
 * 工具渲染器模块
 * 处理工具调用和工具结果的渲染逻辑
 */

const MessageRendererTools = {
    /**
     * 检查工具渲染器是否可用
     * @returns {boolean}
     */
    _isToolRenderersAvailable() {
        return typeof window.ToolRenderers !== 'undefined';
    },

    /**
     * 检查工具图标系统是否可用
     * @returns {boolean}
     */
    _isToolIconsAvailable() {
        return typeof window.ToolIcons !== 'undefined';
    },

    /**
     * 检查工具预览系统是否可用
     * @returns {boolean}
     */
    _isToolPreviewAvailable() {
        return typeof window.ToolPreview !== 'undefined';
    },

    /**
     * 获取工具图标
     * @param {string} toolName - 工具名称
     * @returns {string} 图标
     */
    _getToolIcon(toolName) {
        if (this._isToolIconsAvailable()) {
            return window.ToolIcons.getToolIcon(toolName);
        }
        // 回退到默认图标
        return '🔧';
    },

    /**
     * 获取工具预览文本
     * @param {string} toolName - 工具名称
     * @param {Object} input - 工具输入
     * @returns {string|null} 预览文本
     */
    _getToolPreview(toolName, input) {
        if (this._isToolPreviewAvailable()) {
            return window.ToolPreview.getToolPreview(toolName, input);
        }
        return null;
    },

    /**
     * 规范化工具名称（首字母大写）
     * v0.5.3.6: 确保与注册表中的名称一致
     * @param {string} toolName - 原始工具名称
     * @returns {string} 规范化后的名称
     */
    _normalizeToolName(toolName) {
        if (!toolName) return '';
        // 处理特殊工具名称
        const specialNames = {
            'todowrite': 'TodoWrite',
            'websearch': 'WebSearch',
            'webfetch': 'WebFetch',
        };
        const lowerName = toolName.toLowerCase();
        if (specialNames[lowerName]) {
            return specialNames[lowerName];
        }
        // 默认首字母大写
        return toolName.charAt(0).toUpperCase() + toolName.slice(1);
    },

    /**
     * 渲染工具调用块（v0.5.4 增强 - 工具图标和预览系统）
     * @param {Object} block - 工具调用块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderToolUseBlock(block) {
        const rawToolName = block.tool_name || 'Unknown';
        const toolName = this._normalizeToolName(rawToolName);
        const toolInput = block.tool_input || {};
        const toolNameLower = rawToolName.toLowerCase();

        // v0.5.4: 获取工具图标和预览
        const toolIcon = this._getToolIcon(rawToolName);
        const toolPreview = this._getToolPreview(rawToolName, toolInput);

        // v0.5.4: 检查是否应该自动展开
        const shouldAutoExpand = MessageRendererCore._autoExpandTools.some(t => toolNameLower.includes(t));

        // v0.5.4: 检查是否有专用渲染器
        const hasSpecialRenderer = this._isToolRenderersAvailable() &&
            window.ToolRenderers.hasInputRenderer(toolName);

        // 获取工具颜色类
        const toolColorClass = this._isToolIconsAvailable() ? window.ToolIcons.getToolColorClass(rawToolName) : 'tool-color-default';

        // 如果有专用渲染器且应该自动展开
        if (shouldAutoExpand && hasSpecialRenderer) {
            try {
                const renderedEl = window.ToolRenderers.renderInput(toolName, toolInput);
                if (renderedEl) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'assistant-msg assistant-msg-tool_use message-fade-in message-tool_use';
                    wrapper.innerHTML = `
                        <button class="tool-button tool-button-input ${toolColorClass} expanded" onclick="this.classList.toggle('expanded')">
                            <span class="tool-button-icon">${toolIcon}</span>
                            <span class="tool-button-preview">${Utils.escapeHtml(rawToolName)}</span>
                            ${toolPreview ? `<span class="tool-button-preview">${Utils.escapeHtml(toolPreview)}</span>` : ''}
                        </button>
                        <div class="tool-content-expanded">
                    `;
                    wrapper.appendChild(renderedEl);
                    wrapper.innerHTML += '</div>';
                    return wrapper.outerHTML;
                }
            } catch (err) {
                console.warn(`ToolRenderer error for ${toolName}:`, err);
            }
        }

        // 生成唯一 ID
        const blockId = `tool-use-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

        // v0.5.4: 默认渲染为可折叠的工具按钮
        const hasInput = toolInput && Object.keys(toolInput).length > 0;

        return `
            <div class="assistant-msg assistant-msg-tool_use message-fade-in message-tool_use ${toolColorClass}" id="${blockId}">
                <button class="tool-button tool-button-input ${shouldAutoExpand ? 'expanded' : ''}"
                        onclick="MessageRendererTools._toggleToolUse('${blockId}', ${shouldAutoExpand})"
                        ${!hasInput ? 'disabled' : ''}>
                    <span class="tool-button-icon">${toolIcon}</span>
                    <span class="tool-button-preview">${Utils.escapeHtml(rawToolName)}</span>
                    ${toolPreview ? `<span class="tool-button-preview">${Utils.escapeHtml(toolPreview)}</span>` : ''}
                    ${hasInput && !shouldAutoExpand ? '<span class="tool-button-toggle">▶</span>' : ''}
                </button>
                <div class="tool-content-expanded" style="display: ${shouldAutoExpand && hasInput ? 'block' : 'none'};">
                    ${this._renderToolUseContent(toolName, toolInput, hasSpecialRenderer)}
                </div>
            </div>
        `;
    },

    /**
     * 渲染工具调用内容（v0.5.4）
     * @param {string} toolName - 规范化后的工具名称
     * @param {Object} toolInput - 工具输入
     * @param {boolean} hasSpecialRenderer - 是否有专用渲染器
     * @returns {string} 渲染后的 HTML
     */
    _renderToolUseContent(toolName, toolInput, hasSpecialRenderer) {
        if (hasSpecialRenderer) {
            try {
                const renderedEl = window.ToolRenderers.renderInput(toolName, toolInput);
                if (renderedEl) {
                    return renderedEl.outerHTML;
                }
            } catch (err) {
                console.warn(`ToolRenderer error for ${toolName}:`, err);
            }
        }

        // 默认 JSON 渲染
        const inputJson = JSON.stringify(toolInput, null, 2);
        return `<pre class="tool-input">${Utils.escapeHtml(inputJson)}</pre>`;
    },

    /**
     * 切换工具调用展开/收起（v0.5.4）
     * @param {string} blockId - 块元素 ID
     * @param {boolean} startExpanded - 初始是否展开
     */
    _toggleToolUse(blockId, startExpanded) {
        const block = document.getElementById(blockId);
        if (!block) return;

        const btn = block.querySelector('.tool-button');
        const content = block.querySelector('.tool-content-expanded');
        const toggle = btn.querySelector('.tool-button-toggle');

        if (!content) return;

        if (content.style.display === 'none') {
            content.style.display = 'block';
            btn.classList.add('expanded');
            if (toggle) toggle.textContent = '▼';
        } else {
            content.style.display = 'none';
            btn.classList.remove('expanded');
            if (toggle) toggle.textContent = '▶';
        }
    },

    /**
     * 渲染工具结果块（v0.5.4 增强）
     * @param {Object} block - 工具结果块数据
     * @returns {string} 渲染后的 HTML
     */
    _renderToolResultBlock(block) {
        const isError = block.is_error;
        const rawToolName = block.tool_name || '';
        const toolName = this._normalizeToolName(rawToolName);
        let content = block.content || '';

        // 确保 content 是字符串（处理非字符串类型的情况）
        if (typeof content !== 'string') {
            content = String(content);
        }

        // v0.5.4: 检查内容是否为空
        const hasContent = content && content.trim().length > 0;
        const contentPreview = hasContent ? content.slice(0, 60) + (content.length > 60 ? '...' : '') : null;

        // 生成唯一 ID
        const blockId = `tool-result-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

        // 获取工具颜色类
        const toolColorClass = this._isToolIconsAvailable() && !isError
            ? window.ToolIcons.getToolColorClass(rawToolName)
            : (isError ? 'tool-color-rose' : 'tool-color-green');

        // v0.5.4: 使用新的工具按钮样式
        const btnClass = isError ? 'tool-button-error' : 'tool-button-result';
        const icon = isError ? '❌' : '✅';
        const label = isError ? 'error' : 'result';

        // 如果没有内容，显示简洁的成功/错误状态
        if (!hasContent) {
            return `
                <div class="assistant-msg assistant-msg-tool_result message-fade-in message-tool_result ${toolColorClass}">
                    <button class="tool-button ${btnClass} ${toolColorClass}" disabled>
                        <span class="tool-button-icon">${icon}</span>
                        <span class="tool-button-preview">${label}</span>
                    </button>
                </div>
            `;
        }

        // v0.5.4: 尝试使用专用渲染器
        if (this._isToolRenderersAvailable() && window.ToolRenderers.hasResultRenderer(toolName)) {
            try {
                const options = {
                    content,
                    isError,
                    isFileList: toolName === 'Glob' || toolName.toLowerCase() === 'glob',
                    maxLines: 30,
                    maxChars: 5000
                };
                const renderedEl = window.ToolRenderers.renderResult(toolName, options);
                if (renderedEl) {
                    // 包装为可折叠的按钮
                    return `
                        <div class="assistant-msg assistant-msg-tool_result message-fade-in message-tool_result ${toolColorClass}" id="${blockId}">
                            <button class="tool-button ${btnClass} ${toolColorClass}" onclick="MessageRendererTools._toggleToolResult('${blockId}')">
                                <span class="tool-button-icon">${icon}</span>
                                <span class="tool-button-preview">${label}</span>
                                ${contentPreview ? `<span class="tool-button-preview">${Utils.escapeHtml(contentPreview)}</span>` : ''}
                                <span class="tool-button-toggle">▶</span>
                            </button>
                            <div class="tool-content-expanded" style="display: none;">
                                ${renderedEl.outerHTML}
                            </div>
                        </div>
                    `;
                }
            } catch (err) {
                console.warn(`ToolRenderer error for ${toolName} result:`, err);
            }
        }

        // 获取工具对应的样式配置
        const style = MessageRendererToolResults._getToolResultStyle(toolName);

        // 截断过长的结果
        const displayContent = Utils.truncateText(content, style.maxLength);
        const hasMore = displayContent.length < content.length;

        // 根据工具类型选择不同的渲染模板
        const resultContent = MessageRendererToolResults._renderToolResultByType(toolName, style, isError, displayContent, content);

        return `
            <div class="assistant-msg assistant-msg-tool_result message-fade-in message-tool_result ${toolColorClass}" id="${blockId}">
                <button class="tool-button ${btnClass} ${toolColorClass}" onclick="MessageRendererTools._toggleToolResult('${blockId}')">
                    <span class="tool-button-icon">${isError ? '❌' : style.icon}</span>
                    <span class="tool-button-preview">${isError ? 'error' : style.label}</span>
                    ${contentPreview ? `<span class="tool-button-preview">${Utils.escapeHtml(contentPreview)}</span>` : ''}
                    <span class="tool-button-toggle">▶</span>
                </button>
                <div class="tool-content-expanded" style="display: none;">
                    ${resultContent}
                    ${hasMore ? '<div class="result-truncated">... 内容过长，已截断</div>' : ''}
                </div>
            </div>
        `;
    },

    /**
     * 切换工具结果展开/收起（v0.5.4）
     * @param {string} blockId - 块元素 ID
     */
    _toggleToolResult(blockId) {
        const block = document.getElementById(blockId);
        if (!block) return;

        const btn = block.querySelector('.tool-button');
        const content = block.querySelector('.tool-content-expanded');
        const toggle = btn.querySelector('.tool-button-toggle');

        if (!content) return;

        if (content.style.display === 'none') {
            content.style.display = 'block';
            btn.classList.add('expanded');
            if (toggle) toggle.textContent = '▼';
        } else {
            content.style.display = 'none';
            btn.classList.remove('expanded');
            if (toggle) toggle.textContent = '▶';
        }
    }
};

// 导出到全局命名空间
window.MessageRendererTools = MessageRendererTools;
