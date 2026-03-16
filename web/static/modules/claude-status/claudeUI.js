/**
 * Claude UI 组件模块
 * 负责UI相关的交互组件和样式管理
 */

const ClaudeUI = {
    /**
     * 初始化UI组件
     */
    init() {
        this.injectStyles();
    },

    /**
     * 注入CSS样式
     */
    injectStyles() {
        const style = document.createElement("style");
        style.textContent = `
            @keyframes fadeInOut {
                0% { opacity: 0; transform: translateX(-50%) translateY(10px); }
                15% { opacity: 1; transform: translateX(-50%) translateY(0); }
                85% { opacity: 1; transform: translateX(-50%) translateY(0); }
                100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
            }

            .status-section {
                background: var(--card-bg, #1e293b);
                border-radius: 8px;
                margin-bottom: 20px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }

            .status-section-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px 20px;
                background: var(--header-bg, #334155);
                border-bottom: 1px solid var(--border-color, #334155);
            }

            .status-section-header h2 {
                margin: 0;
                font-size: 16px;
                font-weight: 600;
                color: var(--text-primary, #e2e8f0);
            }

            .status-section-content {
                padding: 20px;
            }

            .status-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
            }

            .status-item {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }

            .status-item-full {
                grid-column: 1 / -1;
            }

            .status-label {
                font-size: 12px;
                color: var(--text-secondary, #94a3b8);
                font-weight: 500;
            }

            .status-value {
                font-size: 14px;
                color: var(--text-primary, #e2e8f0);
                word-break: break-all;
            }

            .env-table {
                width: 100%;
                border-collapse: collapse;
            }

            .env-table th,
            .env-table td {
                padding: 10px 12px;
                text-align: left;
                border-bottom: 1px solid var(--border-color, #334155);
            }

            .env-table th {
                font-weight: 600;
                background: var(--header-bg, #334155);
                font-size: 12px;
                color: var(--text-secondary, #94a3b8);
            }

            .env-key {
                font-family: monospace;
                cursor: pointer;
                color: var(--text-primary, #e2e8f0);
            }

            .env-key:hover {
                color: var(--primary-color, #007bff);
            }

            .env-value {
                font-family: monospace;
                word-break: break-all;
            }

            .env-value-sensitive {
                color: var(--text-secondary, #94a3b8);
            }

            .loading-placeholder,
            .empty-placeholder,
            .error-placeholder {
                text-align: center;
                padding: 40px;
                color: var(--text-secondary, #94a3b8);
            }

            .error-placeholder {
                color: var(--error-color, #dc3545);
            }

            /* v0.3.2 工具统计样式 */
            .tools-usage-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 12px;
                margin-bottom: 20px;
            }

            .tool-usage-item {
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .tool-usage-item .tool-name {
                font-weight: 500;
                min-width: 80px;
            }

            .tool-usage-bar {
                flex: 1;
                height: 8px;
                background: var(--border-color, #334155);
                border-radius: 4px;
                overflow: hidden;
            }

            .tool-usage-fill {
                height: 100%;
                background: var(--primary-color, #007bff);
                border-radius: 4px;
                transition: width 0.3s ease;
            }

            .tool-usage-item .tool-count {
                min-width: 30px;
                text-align: right;
                font-family: monospace;
                color: var(--text-secondary, #94a3b8);
            }

            .task-stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 12px;
                padding-top: 16px;
                border-top: 1px solid var(--border-color, #334155);
            }

            .task-stat-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 12px;
                background: var(--header-bg, #334155);
                border-radius: 8px;
            }

            .task-stat-label {
                font-size: 12px;
                color: var(--text-secondary, #94a3b8);
                margin-bottom: 4px;
            }

            .task-stat-value {
                font-size: 18px;
                font-weight: 600;
                color: var(--text-primary, #e2e8f0);
            }

            .task-stat-success {
                color: var(--success-color, #28a745);
            }

            .task-stat-failed {
                color: var(--error-color, #dc3545);
            }

            /* 权限模式样式 */
            .permission-modes-list {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 16px;
            }

            .permission-mode-card {
                padding: 16px;
                background: var(--header-bg, #334155);
                border-radius: 8px;
                border-left: 4px solid var(--primary-color);
            }

            .permission-mode-name {
                font-weight: 600;
                font-size: 16px;
                color: var(--text-primary);
                margin-bottom: 8px;
            }

            .permission-mode-description {
                font-size: 14px;
                color: var(--text-secondary);
                margin-bottom: 12px;
            }

            .permission-mode-scenarios {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
            }

            .scenario-tag {
                font-size: 12px;
                padding: 2px 8px;
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                color: var(--text-secondary);
            }

            /* 工具列表样式 */
            .tools-list {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            .tools-category-title {
                font-size: 14px;
                font-weight: 600;
                color: var(--text-primary);
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 2px solid var(--primary-color);
            }

            .tools-category-list {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 12px;
            }

            .tool-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px;
                background: var(--header-bg);
                border-radius: 8px;
            }

            .tool-item-name {
                font-weight: 600;
                font-family: monospace;
                min-width: 80px;
            }

            .tool-item-desc {
                flex: 1;
                font-size: 13px;
                color: var(--text-secondary);
            }

            .tool-item-badge {
                font-size: 11px;
                padding: 2px 8px;
                border-radius: 10px;
            }

            .tool-modifies {
                background: var(--warning-color);
                color: #fff;
            }

            .tool-readonly {
                background: var(--success-color);
                color: #fff;
            }

            /* v0.3.3 文档展示样式 */
            .docs-tabs {
                display: flex;
                gap: 8px;
                margin-bottom: 20px;
                border-bottom: 1px solid var(--border-color, #334155);
                padding-bottom: 12px;
            }

            .docs-tab {
                padding: 8px 16px;
                border: none;
                background: transparent;
                color: var(--text-secondary, #94a3b8);
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                border-radius: 6px;
                transition: all 0.2s ease;
            }

            .docs-tab:hover {
                background: var(--header-bg, #334155);
                color: var(--text-primary, #e2e8f0);
            }

            .docs-tab.active {
                background: var(--primary-color, #007bff);
                color: #fff;
            }

            .docs-tab-content {
                min-height: 200px;
            }

            .docs-tab-pane {
                display: none;
            }

            .docs-tab-pane.active {
                display: block;
            }

            /* 手风琴样式 */
            .docs-accordion {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .docs-accordion-item {
                background: var(--header-bg, #334155);
                border-radius: 8px;
                overflow: hidden;
            }

            .docs-accordion-header {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 14px 16px;
                cursor: pointer;
                transition: background 0.2s ease;
            }

            .docs-accordion-header:hover {
                background: rgba(255, 255, 255, 0.05);
            }

            .docs-accordion-item.active .docs-accordion-arrow {
                transform: rotate(180deg);
            }

            .docs-accordion-arrow {
                margin-left: auto;
                font-size: 10px;
                color: var(--text-secondary, #94a3b8);
                transition: transform 0.2s ease;
            }

            .docs-accordion-content {
                display: none;
                padding: 0 16px 16px;
                border-top: 1px solid var(--border-color, #334155);
            }

            .docs-accordion-item.active .docs-accordion-content {
                display: block;
            }

            .docs-item-name {
                font-weight: 600;
                font-family: monospace;
                font-size: 15px;
                color: var(--text-primary, #e2e8f0);
            }

            .docs-item-category {
                font-size: 12px;
                color: var(--text-secondary, #94a3b8);
                padding: 2px 8px;
                background: var(--card-bg, #1e293b);
                border-radius: 10px;
            }

            .docs-item-badge {
                font-size: 11px;
                padding: 2px 8px;
                border-radius: 10px;
            }

            .docs-description {
                margin: 12px 0;
                color: var(--text-secondary, #94a3b8);
                line-height: 1.6;
            }

            .docs-section {
                margin-top: 16px;
            }

            .docs-section h4 {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-primary, #e2e8f0);
                margin-bottom: 8px;
            }

            .docs-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
            }

            .docs-table th,
            .docs-table td {
                padding: 8px 12px;
                text-align: left;
                border-bottom: 1px solid var(--border-color, #334155);
            }

            .docs-table th {
                font-weight: 600;
                color: var(--text-secondary, #94a3b8);
                background: var(--card-bg, #1e293b);
            }

            .docs-table code {
                font-family: monospace;
                font-size: 12px;
                padding: 2px 6px;
                background: var(--card-bg, #1e293b);
                border-radius: 4px;
                color: #86efac;
            }

            .docs-code {
                background: var(--card-bg, #1e293b);
                padding: 12px;
                border-radius: 6px;
                overflow-x: auto;
                margin: 8px 0;
            }

            .docs-code code {
                font-family: monospace;
                font-size: 12px;
                color: var(--text-primary, #e2e8f0);
            }

            .docs-example-desc {
                font-size: 12px;
                color: var(--text-secondary, #94a3b8);
                margin-top: 8px;
            }

            /* 网格布局 */
            .docs-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 16px;
            }

            .docs-card {
                background: var(--header-bg, #334155);
                border-radius: 8px;
                overflow: hidden;
            }

            .docs-card-header {
                padding: 12px 16px;
                background: rgba(0, 0, 0, 0.1);
            }

            .docs-card-title {
                font-weight: 600;
                font-family: monospace;
                font-size: 14px;
                color: #fbbf24;
            }

            .docs-card-body {
                padding: 16px;
            }

            .docs-card-body p {
                color: var(--text-secondary, #94a3b8);
                font-size: 13px;
                margin-bottom: 12px;
                line-height: 1.5;
            }

            .docs-tags {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
            }

            .docs-tag {
                font-size: 11px;
                padding: 3px 8px;
                background: var(--card-bg, #1e293b);
                border-radius: 10px;
                color: var(--text-secondary, #94a3b8);
            }

            /* 命令列表样式 */
            .docs-commands-list {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }

            /* 分类命令容器 */
            .docs-commands-container {
                display: flex;
                flex-direction: column;
                gap: 24px;
            }

            .docs-command-category {
                background: var(--header-bg, #334155);
                border-radius: 12px;
                overflow: hidden;
            }

            .docs-category-header {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 14px 18px;
                background: linear-gradient(135deg, rgba(0, 123, 255, 0.15) 0%, rgba(0, 123, 255, 0.05) 100%);
                border-bottom: 1px solid var(--border-color, #334155);
            }

            .docs-category-icon {
                font-size: 18px;
            }

            .docs-category-title {
                font-weight: 600;
                font-size: 15px;
                color: var(--text-primary, #e2e8f0);
                flex: 1;
            }

            .docs-category-count {
                font-size: 12px;
                padding: 2px 10px;
                background: var(--primary-color, #007bff);
                color: #fff;
                border-radius: 12px;
                font-weight: 500;
            }

            .docs-category-commands {
                display: flex;
                flex-direction: column;
                gap: 12px;
                padding: 16px;
            }

            .docs-command-item {
                background: var(--card-bg, #1e293b);
                border-radius: 8px;
                overflow: hidden;
                transition: all 0.2s ease;
            }

            .docs-command-item:hover {
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            }

            .docs-command-item {
                background: var(--header-bg, #334155);
                border-radius: 8px;
                overflow: hidden;
            }

            .docs-command-header {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 14px 16px;
                background: rgba(0, 0, 0, 0.1);
                flex-wrap: wrap;
            }

            .docs-command-name {
                font-weight: 600;
                font-family: monospace;
                font-size: 14px;
                color: #fbbf24;
            }

            .docs-command-usage {
                font-size: 13px;
                color: var(--text-secondary, #94a3b8);
                font-family: monospace;
            }

            .docs-command-body {
                padding: 16px;
            }

            .docs-command-body p {
                color: var(--text-secondary, #94a3b8);
                line-height: 1.5;
            }

            .docs-command-options {
                margin-top: 16px;
            }

            .docs-command-options h4 {
                font-size: 13px;
                font-weight: 600;
                color: var(--text-primary, #e2e8f0);
                margin-bottom: 8px;
            }

            /* 最佳实践样式 */
            .docs-best-practices {
                display: flex;
                flex-direction: column;
                gap: 24px;
            }

            .docs-best-practices h3 {
                font-size: 16px;
                font-weight: 600;
                color: var(--text-primary, #e2e8f0);
                margin-bottom: 16px;
            }

            .docs-practice-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
                gap: 16px;
            }

            .docs-practice-card {
                background: var(--header-bg, #334155);
                padding: 16px;
                border-radius: 8px;
            }

            .docs-practice-card h4 {
                font-size: 14px;
                font-weight: 600;
                color: var(--text-primary, #e2e8f0);
                margin-bottom: 12px;
            }

            .docs-tools-list {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                margin-bottom: 8px;
            }

            .docs-tool-tag {
                font-size: 12px;
                font-family: monospace;
                padding: 3px 8px;
                background: var(--card-bg, #1e293b);
                border-radius: 4px;
                color: #86efac;
            }

            .docs-practice-desc {
                font-size: 12px;
                color: var(--text-secondary, #94a3b8);
                margin: 0;
            }

            .docs-modes-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                gap: 12px;
            }

            .docs-mode-card {
                background: var(--header-bg, #334155);
                padding: 14px;
                border-radius: 8px;
                border-left: 3px solid var(--primary-color, #007bff);
            }

            .docs-mode-name {
                font-weight: 600;
                font-family: monospace;
                font-size: 14px;
                color: var(--text-primary, #e2e8f0);
                margin-bottom: 4px;
            }

            .docs-mode-scenario {
                font-size: 12px;
                color: var(--text-secondary, #94a3b8);
            }

            .docs-error-patterns {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .docs-error-pattern {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 16px;
                background: var(--header-bg, #334155);
                border-radius: 8px;
            }

            .docs-error-pattern code {
                font-family: monospace;
                font-size: 13px;
                font-weight: 600;
                color: #86efac;
                min-width: 100px;
            }

            .docs-error-pattern span {
                font-size: 13px;
                color: var(--text-secondary, #94a3b8);
            }

            /* 响应式布局 */
            @media (max-width: 768px) {
                .tools-usage-grid {
                    grid-template-columns: 1fr;
                }

                .task-stats {
                    grid-template-columns: repeat(2, 1fr);
                }

                .permission-modes-list {
                    grid-template-columns: 1fr;
                }

                .tools-category-list {
                    grid-template-columns: 1fr;
                }

                .tool-item {
                    flex-wrap: wrap;
                }

                .tool-item-desc {
                    order: 3;
                    width: 100%;
                    margin-top: 8px;
                }

                /* 文档展示响应式 */
                .docs-tabs {
                    flex-wrap: wrap;
                }

                .docs-tab {
                    flex: 1;
                    min-width: 80px;
                    text-align: center;
                }

                .docs-practice-grid,
                .docs-modes-grid {
                    grid-template-columns: 1fr;
                }

                .docs-accordion-header {
                    flex-wrap: wrap;
                }
            }
        `;
        document.head.appendChild(style);
    },

    /**
     * 显示提示消息
     */
    showToast(message) {
        // 使用全局的 toast 函数（如果存在）
        if (typeof window.showToast === "function") {
            window.showToast(message);
            return;
        }

        // 简单的提示实现
        const toast = document.createElement("div");
        toast.className = "toast-message";
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            z-index: 10000;
            animation: fadeInOut 2s ease-in-out;
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 2000);
    },
};

// 导出模块
window.ClaudeUI = ClaudeUI;