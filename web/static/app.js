/**
 * Claude Code Runner 前端交互 - 主入口
 * 按功能模块拆分的应用入口文件
 * v12.0.0.3 - 界面重构：单会话模式
 */

class ClaudeCodeRunner {
    constructor() {
        // DOM 元素
        this.navMenu = document.getElementById('nav-menu');
        this.outputEl = document.getElementById('output-container-wrapper'); // 输出容器
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
        // v12: workingDirInput 和 workingDirList 已废弃，改用 WorkspaceCombo 组件
        // 保留这些属性是为了兼容旧代码，但初始化为 null
        this.workingDirInput = null;  // document.getElementById('working-dir') 在 v12 中不存在
        this.workingDirList = null;   // datalist 元素在 v12 中不存在
        this.workspaceComboContainer = document.getElementById('workspace-combo-container');
        this.workspaceCombo = null; // WorkspaceCombo 组件实例
        this.historySessionComboContainer = document.getElementById('history-session-combo-container');
        this.historySessionCombo = null; // HistorySessionCombo 组件实例
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

            // 历史会话状态
            historySessionSelected: null,  // 已选择的历史会话ID
            historySessions: [],           // 当前工作空间的历史会话列表

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
        // v12: defaultWorkingDir 将在 init() 中从 API 获取或使用当前工作目录
        this.defaultWorkingDir = '';  // 初始化为空，稍后在 init() 中设置

        // 初始化 state.workspace 为空，稍后在 init() 中设置
        this.state.workspace = this.defaultWorkingDir;

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


    async init() {
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
        // v12.0.0.4: 添加 resetSessionState 调用
        this.newSessionBtn.addEventListener('click', async () => {
            // 使用 Session 模块统一处理新会话清空逻辑
            if (typeof Session !== 'undefined') {
                await Session.clearCurrentSession(this);
            }
            // 重置会话状态（解锁工作空间等）
            this.resetSessionState();
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
        await this.initWorkspaceCombo();

        // v12.0.0.4: 初始化历史会话下拉组件（在工作空间控件之后）
        await this.initHistorySessionCombo();

        // 绑定工作目录变更监听（用于更新继续会话复选框状态）
        // 注意: this.workingDirInput 现在由 WorkspaceCombo 管理
        // 注意：需要在 historySessionCombo 初始化后再绑定 onChange，确保级联正确
        if (this.workspaceCombo) {
            this.workspaceCombo.onChange((value) => {
                // 更新 runner 实例中的工作目录值
                if (this.workingDirInput) {
                    this.workingDirInput.value = value;
                }
                this.state.workspace = value;

                // v12.0.0.4: 级联逻辑 - 工作空间变更时加载历史会话
                this.handleWorkspaceChange(value);

                ContinueSessionManager.handleWorkingDirChange();
            });

            // 手动触发一次 change 事件，处理初始工作空间
            // 确保在 historySessionCombo 初始化完成后触发
            const currentValue = this.workspaceCombo.getValue();
            console.log('[App] 手动触发初始工作空间变更', currentValue);
            if (currentValue) {
                this.state.workspace = currentValue;
                this.handleWorkspaceChange(currentValue);
            }
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

        // v12.0.0.7: 修复默认工作目录问题
        // 首先从后端获取实际的工作目录
        let actualWorkingDir = '';
        try {
            const statusResponse = await fetch('/api/status');
            if (statusResponse.ok) {
                const statusData = await statusResponse.json();
                if (statusData.working_dir) {
                    actualWorkingDir = statusData.working_dir;
                    console.log('[App] 从后端获取实际工作目录:', actualWorkingDir);
                }
            }
        } catch (error) {
            console.warn('[App] 获取后端工作目录失败:', error);
        }

        // 如果后端没有返回，尝试从项目列表中找到当前项目
        if (!actualWorkingDir) {
            try {
                const projectsResponse = await fetch('/api/projects?limit=100');
                if (projectsResponse.ok) {
                    const projectsData = await projectsResponse.json();
                    if (projectsData.projects && projectsData.projects.length > 0) {
                        // 使用第一个项目的工作目录作为默认值
                        actualWorkingDir = projectsData.projects[0].path;
                        console.log('[App] 从项目列表获取默认工作目录:', actualWorkingDir);
                    }
                }
            } catch (error) {
                console.warn('[App] 获取项目列表失败:', error);
            }
        }

        // 最后的备选方案：使用 "."
        if (!actualWorkingDir) {
            actualWorkingDir = '.';
            console.log('[App] 使用默认工作目录: .');
        }

        // 先加载工作目录历史
        await WorkingDir.loadWorkingDirs(this);

        // 设置默认工作目录：优先使用实际工作目录，然后使用历史记录中的第一个
        this.defaultWorkingDir = actualWorkingDir;
        if (this.workingDirs && this.workingDirs.length > 0) {
            // 如果历史记录中有与实际工作目录匹配的，保持实际工作目录
            // 否则使用历史记录的第一个
            const hasMatchingHistory = this.workingDirs.some(dir => {
                // 简单的路径比较（不区分大小写和斜杠）
                const normalizedDir = dir.replace(/\\/g, '/').toLowerCase();
                const normalizedActual = actualWorkingDir.replace(/\\/g, '/').toLowerCase();
                return normalizedDir === normalizedActual;
            });

            if (!hasMatchingHistory) {
                // 如果历史记录中没有匹配项，将实际工作目录添加到历史记录开头
                this.workingDirs.unshift(actualWorkingDir);
            }
        } else {
            // 如果没有历史记录，初始化历史记录
            this.workingDirs = [actualWorkingDir];
        }

        // 更新 state.workspace
        this.state.workspace = this.defaultWorkingDir;

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

        // 设置历史记录到组合控件
        if (this.workingDirs && this.workingDirs.length > 0) {
            this.workspaceCombo.setHistory(this.workingDirs);
        }

        console.log('[App] 工作空间组合控件已初始化，默认工作目录:', this.defaultWorkingDir);
    }

    /**
     * 初始化历史会话下拉组件
     * v12.0.0.4 - 级联下拉选择
     */
    async initHistorySessionCombo() {
        if (!this.historySessionComboContainer) {
            console.warn('[App] 历史会话下拉组件容器不存在');
            return;
        }

        // 清空容器
        this.historySessionComboContainer.innerHTML = '';

        // 检查 HistorySessionCombo 是否已定义
        if (typeof HistorySessionCombo === 'undefined') {
            console.error('[App] HistorySessionCombo 未定义，请检查脚本是否正确加载');
            return;
        }

        // 创建 HistorySessionCombo 实例
        this.historySessionCombo = new HistorySessionCombo(this.historySessionComboContainer, {
            placeholder: '选择历史会话',
            onChange: (sessionId, session) => {
                // 用户选择了历史会话
                this.handleHistorySessionSelect(sessionId, session);
            },
            onLoadSessions: async (workingDir) => {
                // 加载指定工作空间的历史会话列表
                const encodedDir = encodeURIComponent(workingDir);
                const response = await fetch(`/api/sessions?working_dir=${encodedDir}&limit=50`);
                if (!response.ok) {
                    console.error('[App] 加载历史会话失败:', response.status);
                    return [];
                }
                const data = await response.json();
                return data.sessions || [];
            }
        });

        // 初始状态：如果有工作空间则加载历史会话，否则禁用
        if (this.state.workspace) {
            // 有初始工作空间，加载历史会话
            await this.historySessionCombo.setWorkspace(this.state.workspace);
        } else {
            // 没有工作空间，禁用组件
            this.historySessionCombo.disable();
            if (this.historySessionCombo.input) {
                this.historySessionCombo.input.placeholder = '请先选择工作空间';
            }
        }
    }

    /**
     * 处理工作空间变更
     * v12.0.0.4 - 级联下拉选择
     * @param {string} workspace - 新工作空间路径
     */
    async handleWorkspaceChange(workspace) {
        console.log('[App] handleWorkspaceChange 被调用, workspace:', workspace);

        // 清空会话ID
        this.state.sessionId = null;
        this.state.sessionStatus = 'new';
        this.state.historySessionSelected = null;
        this.resumeInput.value = '';
        this.resumeInput.title = '';

        // 更新历史会话下拉组件 - 确保级联加载
        if (this.historySessionCombo) {
            console.log('[App] 调用 historySessionCombo.setWorkspace, workspace:', workspace);
            try {
                await this.historySessionCombo.setWorkspace(workspace);
                console.log('[App] historySessionCombo.setWorkspace 完成');
            } catch (error) {
                console.error('[App] historySessionCombo.setWorkspace 失败:', error);
            }
        } else {
            console.warn('[App] historySessionCombo 未初始化，无法加载历史会话');
        }

        // 启用继续会话复选框
        if (this.continueConversationCheckbox) {
            this.continueConversationCheckbox.disabled = false;
        }
    }

    /**
     * 处理历史会话选择
     * v12.0.0.4 - 级联下拉选择
     * @param {string} sessionId - 选中的会话ID
     * @param {Object} session - 会话数据
     */
    handleHistorySessionSelect(sessionId, session) {
        if (!sessionId || !session) {
            return;
        }

        console.log('[App] 选择历史会话:', sessionId, session);

        // 更新状态
        this.state.sessionId = sessionId;
        this.state.sessionStatus = 'resumed';
        this.state.historySessionSelected = sessionId;

        // 填充会话ID
        this.resumeInput.value = sessionId;
        this.resumeInput.title = sessionId;

        // 禁用继续会话复选框（已通过历史选择）
        if (this.continueConversationCheckbox) {
            this.continueConversationCheckbox.checked = false;
            this.continueConversationCheckbox.disabled = true;
        }

        // 加载历史消息（立即显示）
        this.loadSessionMessages(session);
    }

    /**
     * 加载历史会话消息
     * @param {Object} session - 会话数据
     */
    async loadSessionMessages(session) {
        if (typeof History !== 'undefined') {
            await History.loadSessionMessages(this, session.id);
        }
    }

    /**
     * 重置会话状态（用于"新会话"按钮）
     * v12.0.0.4 - 级联下拉选择
     */
    resetSessionState() {
        // 重置历史会话选择
        this.state.historySessionSelected = null;
        if (this.historySessionCombo) {
            this.historySessionCombo.clear();
        }

        // 启用继续会话复选框，但不勾选（确保创建新会话）
        if (this.continueConversationCheckbox) {
            this.continueConversationCheckbox.disabled = false;
            this.continueConversationCheckbox.checked = false;
        }
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
