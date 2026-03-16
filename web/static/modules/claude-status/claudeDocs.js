/**
 * Claude 文档展示模块
 * 负责加载和展示各种文档内容
 */

const ClaudeDocs = {
    /**
     * 加载工具文档
     */
    async loadToolsDocs() {
        const container = document.getElementById("tools-docs-list");
        if (!container) return;

        try {
            const response = await fetch("/api/claude/docs/tools");
            const data = await response.json();

            let html = '<div class="docs-accordion">';
            for (const tool of data.tools) {
                const modifiesClass = tool.modifies_files ? "tool-modifies" : "tool-readonly";
                html += `
                    <div class="docs-accordion-item">
                        <div class="docs-accordion-header">
                            <span class="docs-item-name">${tool.name}</span>
                            <span class="docs-item-category">${tool.category}</span>
                            <span class="docs-item-badge ${modifiesClass}">${tool.modifies_files ? '会修改文件' : '只读'}</span>
                            <span class="docs-accordion-arrow">▼</span>
                        </div>
                        <div class="docs-accordion-content">
                            <p class="docs-description">${tool.description}</p>
                            <div class="docs-section">
                                <h4>参数</h4>
                                <table class="docs-table">
                                    <thead>
                                        <tr>
                                            <th>名称</th>
                                            <th>类型</th>
                                            <th>必填</th>
                                            <th>说明</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${tool.parameters.map(p => `
                                            <tr>
                                                <td><code>${p.name}</code></td>
                                                <td>${p.type}</td>
                                                <td>${p.required ? '是' : '否'}</td>
                                                <td>${p.description}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                            <div class="docs-section">
                                <h4>示例</h4>
                                <pre class="docs-code"><code>${JSON.stringify(tool.example.input, null, 2)}</code></pre>
                                <p class="docs-example-desc">${tool.example.description}</p>
                            </div>
                        </div>
                    </div>
                `;
            }
            html += '</div>';

            container.innerHTML = html;
            this.bindDocsAccordion();
        } catch (error) {
            console.error("加载工具文档失败:", error);
            container.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 加载代理文档
     */
    async loadAgentsDocs() {
        const container = document.getElementById("agents-docs-list");
        if (!container) return;

        try {
            const response = await fetch("/api/claude/docs/agents");
            const data = await response.json();

            let html = '<div class="docs-grid">';
            for (const agent of data.agents) {
                html += `
                    <div class="docs-card">
                        <div class="docs-card-header">
                            <span class="docs-card-title">${agent.name}</span>
                        </div>
                        <div class="docs-card-body">
                            <p>${agent.description}</p>
                            <div class="docs-tags">
                                ${agent.use_cases.map(uc => `<span class="docs-tag">${uc}</span>`).join('')}
                            </div>
                        </div>
                    </div>
                `;
            }
            html += '</div>';

            container.innerHTML = html;
        } catch (error) {
            console.error("加载代理文档失败:", error);
            container.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 加载命令文档
     */
    async loadCommandsDocs() {
        const container = document.getElementById("commands-docs-list");
        if (!container) return;

        try {
            const response = await fetch("/api/claude/docs/commands");
            const data = await response.json();

            // 按类别分组命令
            const categories = {
                cli: { title: "CLI 启动命令", icon: "💻", commands: [] },
                slash: { title: "斜杠命令", icon: "⌨️", commands: [] },
                symbol: { title: "符号命令", icon: "🔣", commands: [] },
                shortcut: { title: "快捷键", icon: "⌘", commands: [] },
                file: { title: "项目文件", icon: "📄", commands: [] },
            };

            for (const cmd of data.commands) {
                if (categories[cmd.category]) {
                    categories[cmd.category].commands.push(cmd);
                }
            }

            let html = '<div class="docs-commands-container">';

            for (const [key, cat] of Object.entries(categories)) {
                if (cat.commands.length === 0) continue;

                html += `
                    <div class="docs-command-category">
                        <div class="docs-category-header">
                            <span class="docs-category-icon">${cat.icon}</span>
                            <span class="docs-category-title">${cat.title}</span>
                            <span class="docs-category-count">${cat.commands.length}</span>
                        </div>
                        <div class="docs-category-commands">
                `;

                for (const cmd of cat.commands) {
                    html += `
                        <div class="docs-command-item">
                            <div class="docs-command-header">
                                <code class="docs-command-name">${cmd.name}</code>
                                <span class="docs-command-usage">${cmd.usage}</span>
                            </div>
                            <div class="docs-command-body">
                                <p>${cmd.description}</p>
                                ${cmd.options && cmd.options.length > 0 ? `
                                    <div class="docs-command-options">
                                        <h4>选项</h4>
                                        <table class="docs-table">
                                            <thead>
                                                <tr>
                                                    <th>选项</th>
                                                    <th>说明</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                ${cmd.options.map(o => `
                                                    <tr>
                                                        <td><code>${o.name}</code></td>
                                                        <td>${o.description}</td>
                                                    </tr>
                                                `).join('')}
                                            </tbody>
                                        </table>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `;
                }

                html += '</div></div>';
            }

            html += '</div>';

            container.innerHTML = html;
            this.bindDocsAccordion();
        } catch (error) {
            console.error("加载命令文档失败:", error);
            container.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 加载最佳实践
     */
    async loadBestPractices() {
        const container = document.getElementById("best-practices-docs-list");
        if (!container) return;

        try {
            const response = await fetch("/api/claude/docs/best-practices");
            const data = await response.json();

            let html = `
                <div class="docs-best-practices">
                    <div class="docs-section">
                        <h3>🛠️ 工具选择建议</h3>
                        <div class="docs-practice-grid">
                            <div class="docs-practice-card">
                                <h4>📖 只读操作</h4>
                                <div class="docs-tools-list">
                                    ${data.tool_selection.read_only.map(t => `<span class="docs-tool-tag">${t}</span>`).join('')}
                                </div>
                                <p class="docs-practice-desc">用于查看和分析文件，不修改任何内容</p>
                            </div>
                            <div class="docs-practice-card">
                                <h4>✏️ 修改文件</h4>
                                <div class="docs-tools-list">
                                    ${data.tool_selection.modify_files.map(t => `<span class="docs-tool-tag">${t}</span>`).join('')}
                                </div>
                                <p class="docs-practice-desc">用于创建、编辑和删除文件</p>
                            </div>
                            <div class="docs-practice-card">
                                <h4>⚡ 执行命令</h4>
                                <div class="docs-tools-list">
                                    ${data.tool_selection.execute.map(t => `<span class="docs-tool-tag">${t}</span>`).join('')}
                                </div>
                                <p class="docs-practice-desc">用于执行系统命令和脚本</p>
                            </div>
                            <div class="docs-practice-card">
                                <h4>🔍 网络搜索</h4>
                                <div class="docs-tools-list">
                                    ${data.tool_selection.search.map(t => `<span class="docs-tool-tag">${t}</span>`).join('')}
                                </div>
                                <p class="docs-practice-desc">用于搜索网络和获取网页内容</p>
                            </div>
                        </div>
                    </div>

                    <div class="docs-section">
                        <h3>🔐 权限模式选择</h3>
                        <div class="docs-modes-grid">
                            ${data.permission_mode_guide.map(mode => `
                                <div class="docs-mode-card">
                                    <div class="docs-mode-name">${mode.mode}</div>
                                    <div class="docs-mode-scenario">${mode.scenario}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <div class="docs-section">
                        <h3>⚠️ 错误处理模式</h3>
                        <div class="docs-error-patterns">
                            <div class="docs-error-pattern">
                                <code>try-catch</code>
                                <span>${data.error_handling.try_catch}</span>
                            </div>
                            <div class="docs-error-pattern">
                                <code>logging</code>
                                <span>${data.error_handling.logging}</span>
                            </div>
                            <div class="docs-error-pattern">
                                <code>user_message</code>
                                <span>${data.error_handling.user_message}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            container.innerHTML = html;
        } catch (error) {
            console.error("加载最佳实践失败:", error);
            container.innerHTML = '<div class="error-placeholder">加载失败</div>';
        }
    },

    /**
     * 绑定文档手风琴展开/收起事件
     */
    bindDocsAccordion() {
        const headers = document.querySelectorAll('.docs-accordion-header');
        headers.forEach(header => {
            header.addEventListener('click', () => {
                const item = header.parentElement;
                item.classList.toggle('active');
            });
        });
    },
};

// 导出模块
window.ClaudeDocs = ClaudeDocs;