/**
 * 工具多选组件模块
 * 处理工具权限的多选下拉框交互
 */

const ToolsMultiselect = {
    /**
     * 初始化工具多选组件
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    init(runner) {
        const dropdown = document.getElementById('tools-dropdown');
        const selectBtn = document.getElementById('tools-select-btn');

        if (!dropdown || !selectBtn) return;

        // 渲染工具选项
        this.renderToolOptions(runner);

        // 切换下拉框显示
        selectBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });

        // 点击外部关闭下拉框
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.tools-multiselect')) {
                dropdown.classList.remove('show');
            }
        });

        // 初始化选中状态
        this.updateToolsDisplay(runner);
    },

    /**
     * 渲染工具选项
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    renderToolOptions(runner) {
        const dropdown = document.getElementById('tools-dropdown');

        // 使用网格布局包装工具选项
        dropdown.innerHTML = `
            <div class="tools-grid">
                ${runner.availableTools.map((tool, index) => `
                    <div class="tool-option" data-index="${index}">
                        <input type="checkbox" id="tool-${tool.name}" ${tool.selected ? 'checked' : ''}>
                        <span class="tool-name" title="${tool.description}">${tool.name}</span>
                    </div>
                `).join('')}
            </div>
        `;

        // 绑定点击事件
        dropdown.querySelectorAll('.tool-option').forEach(option => {
            option.addEventListener('click', (e) => {
                const index = parseInt(option.dataset.index);
                const checkbox = option.querySelector('input[type="checkbox"]');

                // 如果点击的不是 checkbox 本身，切换 checkbox 状态
                if (e.target !== checkbox) {
                    checkbox.checked = !checkbox.checked;
                }

                runner.availableTools[index].selected = checkbox.checked;
                this.updateToolsDisplay(runner);
            });
        });
    },

    /**
     * 更新工具显示状态
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    updateToolsDisplay(runner) {
        const selectedText = document.querySelector('.selected-text');
        const selectedCount = document.querySelector('.tools-select-btn .selected-count');
        const toolsInput = document.getElementById('tools');

        if (!selectedText || !selectedCount || !toolsInput) return;

        const selectedTools = runner.availableTools.filter(t => t.selected);
        const count = selectedTools.length;
        const total = runner.availableTools.length;

        if (count === 0) {
            selectedText.textContent = '选择工具...';
            selectedCount.style.display = 'none';
            toolsInput.value = '';
        } else if (count === total) {
            selectedText.textContent = '全部工具';
            selectedCount.textContent = count;
            selectedCount.style.display = 'inline';
            toolsInput.value = runner.availableTools.map(t => t.name).join(',');
        } else {
            selectedText.textContent = selectedTools.slice(0, 2).map(t => t.name).join(', ') + (count > 2 ? '...' : '');
            selectedCount.textContent = count;
            selectedCount.style.display = 'inline';
            toolsInput.value = selectedTools.map(t => t.name).join(',');
        }
    },

    /**
     * 设置选中的工具（从工具字符串）
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} toolsString - 工具字符串，如 "Read,Write,Edit"
     */
    setSelectedTools(runner, toolsString) {
        const tools = toolsString ? toolsString.split(',').map(t => t.trim()) : [];

        runner.availableTools.forEach(tool => {
            tool.selected = tools.includes(tool.name);
        });

        // 更新 checkbox 状态
        runner.availableTools.forEach(tool => {
            const checkbox = document.getElementById(`tool-${tool.name}`);
            if (checkbox) {
                checkbox.checked = tool.selected;
            }
        });

        this.updateToolsDisplay(runner);
    },

    /**
     * 获取选中的工具列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @returns {Array<string>} 选中的工具名称数组
     */
    getSelectedTools(runner) {
        return runner.availableTools.filter(t => t.selected).map(t => t.name);
    }
};

// 导出到全局命名空间
window.ToolsMultiselect = ToolsMultiselect;
