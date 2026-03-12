/**
 * Claude Code Runner 前端交互 - 主入口
 * 按功能模块拆分的应用入口文件
 * v12.0.0.3 - 界面重构：单会话模式
 */

class ClaudeCodeRunner {
    constructor() {
        // DOM 元素
        this.navMenu = document.getElementById('nav-menu');
        this.outputEl = null; // 不再直接引用固定的output元素
        this.sendBtn = document.getElementById('send-btn');
        this.stopBtn = document.getElementById('stop-btn');
        this.clearBtn = document.getElementById('clear-btn');
        this.promptInput = document.getElementById('prompt');
        this.permissionSelect = document.getElementById('permission-mode');
        this.statsSection = document.getElementById('task-stats-floating');
        this.projectList = document.getElementById('project-list');
        this.sessionList = document.getElementById('session-list');
        this.historyProjects = document.getElementById('history-projects');
        this.historySessions = document.getElementById('history-sessions');
        this.workingDirInput = document.getElementById('working-dir');
        this.workspaceComboContainer = document.getElementById('workspace-combo-container');
        this.workspaceCombo = null; // WorkspaceCombo 组件实例
        this.resumeInput = document.getElementById('resume');
        this.continueConversationCheckbox = document.getElementById('continue-conversation');
        this.newSessionBtn = document.getElementById('new-session-btn');

        // v12 状态管理 - 单会话模式
        this.state = {
            // 会话状态
            sessionId: null,           // 当前会话 ID（null 表示新会话）
            sessionStatus: 'new',      // new, running, completed, resumed

            // 工作空间状态
            workspace: '',             // 当前工作空间路径
            workspaceHistory: [],      // 历史工作空间列表

            // 消息状态
            messages: [],              // 当前会话的消息列表
            isStreaming: false,        // 是否正在流式输出

            // UI 状态
            historyDrawerOpen: false,  // 历史抽屉是否打开

            // 工具配置
            toolConfig: {
                enabledTools: [],      // 启用的工具列表
                permissionMode: 'auto' // 权限模式
            }
        };

        // 任务执行状态
        this.abortController = null;
        this.reader = null;
        this.isRunning = false;

        // 其他状态
        this.currentProject = null;
        this.currentView = Views.CURRENT_SESSION;
        this.projects = [];
        this.sessions = [];
        this.workingDirs = [];
        this.defaultWorkingDir = this.workingDirInput ? this.workingDirInput.value : '';

        // 多轮对话状态
        this.currentRoundEl = null;
        this.roundCounter = 0;

        // 工具列表（从 constants.js 获取）
        this.availableTools = JSON.parse(JSON.stringify(AVAILABLE_TOOLS));

        // 兼容性：currentSessionId 指向 state.sessionId
        Object.defineProperty(this, 'currentSessionId', {
            get: function() { return this.state.sessionId; },
            set: function(value) { this.state.sessionId = value; }
        });

        this.init();
    }


    init() {
        // v12.0.0.3.5: 数据迁移（在最开始执行）
        this.runMigrationIfNeeded();

        // 初始化认证模块
        if (typeof Auth !== 'undefined') {
            Auth.init();
        }

        // 初始化认证UI模块
        if (typeof AuthUI !== 'undefined') {
            AuthUI.init();
        }

        // 绑定菜单事件
        Navigation.init(this);

        // 绑定任务执行事件
        this.sendBtn.addEventListener('click', () => Task.runTask(this));
        this.stopBtn.addEventListener('click', () => Task.stopTask(this));
        this.clearBtn.addEventListener('click', () => Task.clearOutput(this));

        // v0.5.5 - 绑定连接状态指示器事件
        const reconnectBtn = document.querySelector('.connection-reconnect-btn');
        if (reconnectBtn) {
            reconnectBtn.addEventListener('click', () => Task.manualReconnect(this));
        }

        // 绑定 Enter 键发送事件
        this.promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!this.sendBtn.disabled) {
                    Task.runTask(this);
                }
            }
        });

        // 初始化工具多选组件
        ToolsMultiselect.init(this);

        // 初始化会话信息栏组件
        if (typeof SessionInfoBar !== 'undefined') {
            SessionInfoBar.init(this);
        }

        // 初始化任务输入框组件
        if (typeof TaskInput !== 'undefined') {
            TaskInput.init(this);
        }

        // 初始化权限模式下拉组件
        if (typeof PermissionModeSelect !== 'undefined') {
            PermissionModeSelect.init(this);
        }

        // 绑定新会话按钮 - 清空当前会话开始新任务
        // v12.0.0.3.4: 使用 Session.clearCurrentSession 统一处理
        this.newSessionBtn.addEventListener('click', async () => {
            // 使用 Session 模块统一处理新会话清空逻辑
            if (typeof Session !== 'undefined') {
                await Session.clearCurrentSession(this);
            }
        });

        // 绑定"继续会话"复选框事件
        if (this.continueConversationCheckbox) {
            // 初始化继续会话模块
            ContinueSessionManager.init(this);

            this.continueConversationCheckbox.addEventListener('change', (e) => {
                ContinueSessionManager.handleContinueConversationChange(e.target.checked);
            });
        }

        // 初始化"继续会话"复选框状态
        if (this.continueConversationCheckbox) {
            ContinueSessionManager.updateContinueConversationState();
        }

        // 初始化工作空间组合控件
        this.initWorkspaceCombo();

        // 绑定工作目录变更监听（用于更新继续会话复选框状态）
        // 注意: this.workingDirInput 现在由 WorkspaceCombo 管理
        if (this.workspaceCombo) {
            this.workspaceCombo.onChange((value) => {
                // 更新 runner 实例中的工作目录值
                this.workingDirInput.value = value;
                ContinueSessionManager.handleWorkingDirChange();
            });
        }

        // v12.0.0.3.3: 初始化历史记录抽屉
        this.initHistoryDrawer();

        // 初始化 Claude 状态模块
        if (typeof ClaudeStatus !== 'undefined') {
            ClaudeStatus.init();
        }

        // 初始化 MCP 管理模块
        if (typeof MCPManager !== 'undefined') {
            MCPManager.init();
        }

        // 初始化钩子管理模块
        if (typeof HooksManager !== 'undefined') {
            HooksManager.init();
        }

        // 初始化技能管理模块
        if (typeof SkillManager !== 'undefined') {
            SkillManager.init();
        }

        // 初始化 Agent 监控模块
        if (typeof AgentMonitor !== 'undefined') {
            AgentMonitor.init();
        }

        // 初始化插件管理模块
        if (typeof PluginManager !== 'undefined') {
            PluginManager.init();
        }

        // 初始化任务调度模块
        if (typeof Scheduler !== 'undefined') {
            Scheduler.init();
        }

        // 初始化示例任务模块
        ExampleTasks.init(this);

        // v12.0.0.3: 移除 Tab 系统，改为单会话模式

        // 快捷键
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                Task.runTask(this);
            }
        });
    }

    /**
     * 初始化工作空间组合控件
     */
    async initWorkspaceCombo() {
        if (!this.workspaceComboContainer) {
            console.warn('[App] 工作空间组合控件容器不存在');
            return;
        }

        // 清空容器
        this.workspaceComboContainer.innerHTML = '';

        // 创建 WorkspaceCombo 实例
        this.workspaceCombo = new WorkspaceCombo(this.workspaceComboContainer, {
            value: this.defaultWorkingDir,
            placeholder: '选择或输入工作空间路径',
            onChange: (value) => {
                // 这个回调在 init() 中已经绑定了
            },
            onValidate: (result) => {
                // 可以在这里处理验证结果，例如显示提示
                console.log('[App] 工作空间验证:', result);
            }
        });

        // 加载工作目录历史
        await WorkingDir.loadWorkingDirs(this);

        // 设置历史记录到组合控件
        if (this.workingDirs && this.workingDirs.length > 0) {
            this.workspaceCombo.setHistory(this.workingDirs);
        }

        console.log('[App] 工作空间组合控件已初始化');
    }

    /**
     * 初始化历史记录抽屉
     * v12.0.0.3.3
     */
    initHistoryDrawer() {
        if (typeof HistoryDrawer === 'undefined') {
            console.warn('[App] HistoryDrawer 组件未定义');
            return;
        }

        this.historyDrawer = new HistoryDrawer({
            onSelect: (session) => {
                // 当用户选择一个会话时，继续该会话
                if (typeof History !== 'undefined') {
                    History.continueSession(this, session.id);
                }
            },
            onClose: () => {
                // 抽屉关闭时可以做一些清理工作
            }
        });

        console.log('[App] 历史记录抽屉已初始化');
    }

    /**
     * 执行数据迁移（如果需要）
     * v12.0.0.3.5
     */
    async runMigrationIfNeeded() {
        if (typeof Migration !== 'undefined') {
            const migrated = await Migration.runMigration(this);
            if (migrated) {
                console.log('[App] 数据迁移已完成');
            }
        }
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    window.runner = new ClaudeCodeRunner();
});
