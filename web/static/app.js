/**
 * Claude Code Runner 前端交互 - 主入口
 * 按功能模块拆分的应用入口文件
 */

class ClaudeCodeRunner {
    constructor() {
        // DOM 元素
        this.navMenu = document.getElementById('nav-menu');
        this.outputEl = document.getElementById('output');
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
        this.tabsBar = document.getElementById('tabs-bar');
        this.workingDirInput = document.getElementById('working-dir');
        this.workingDirList = document.getElementById('working-dir-list');
        this.resumeInput = document.getElementById('resume');
        this.newSessionBtn = document.getElementById('new-session-btn');

        // 状态
        this.abortController = null;
        this.reader = null;
        this.isRunning = false;
        this.currentSessionId = null;
        this.currentProject = null;
        this.currentView = Views.CURRENT_SESSION;
        this.projects = [];
        this.sessions = [];
        this.workingDirs = [];
        this.defaultWorkingDir = this.workingDirInput ? this.workingDirInput.value : '';

        // 标签页状态
        this.tabs = [];
        this.tabCounter = 0;
        this.activeTabId = 'new';

        // 多轮对话状态
        this.currentRoundEl = null;
        this.roundCounter = 0;

        // 工具列表（从 constants.js 获取）
        this.availableTools = JSON.parse(JSON.stringify(AVAILABLE_TOOLS));

        this.init();
    }

    init() {
        // 绑定菜单事件
        Navigation.init(this);

        // 绑定任务执行事件
        this.sendBtn.addEventListener('click', () => Task.runTask(this));
        this.stopBtn.addEventListener('click', () => Task.stopTask(this));
        this.clearBtn.addEventListener('click', () => Task.clearOutput(this));

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

        // 绑定示例任务按钮
        this.initExampleButtons();

        // 绑定新会话按钮
        this.newSessionBtn.addEventListener('click', () => Tabs.createNewSession(this));

        // 绑定标签页点击事件（事件委托）
        this.tabsBar.addEventListener('click', (e) => {
            const tabItem = e.target.closest('.tab-item');
            if (tabItem && !e.target.classList.contains('tab-close')) {
                const tabId = tabItem.dataset.tab;
                if (tabId) {
                    Tabs.switchToTab(this, tabId);
                }
            }
        });

        // 加载工作目录列表
        WorkingDir.loadWorkingDirs(this);

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

        // 快捷键
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                Task.runTask(this);
            }
        });
    }

    // ============== 示例任务 ==============

    initExampleButtons() {
        // 示例任务视图中的大按钮
        document.querySelectorAll('.btn-example-large').forEach(btn => {
            btn.addEventListener('click', () => {
                const prompt = btn.dataset.prompt;
                this.useExamplePrompt(prompt);
            });
        });
    }

    useExamplePrompt(prompt) {
        // 切换到当前会话视图
        Navigation.switchView(this, Views.CURRENT_SESSION);

        // 填充任务描述
        document.getElementById('prompt').value = prompt;

        // 聚焦到任务描述输入框
        document.getElementById('prompt').focus();
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    window.runner = new ClaudeCodeRunner();
});
