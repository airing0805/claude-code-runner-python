/**
 * Claude Code Runner 前端交互 - 主入口
 * 按功能模块拆分的应用入口文件
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
        this.tabsBar = document.getElementById('tabs-bar');
        this.workingDirInput = document.getElementById('working-dir');
        this.workingDirList = document.getElementById('working-dir-list');
        this.resumeInput = document.getElementById('resume');
        this.continueConversationCheckbox = document.getElementById('continue-conversation');
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

        // 绑定示例任务按钮
        this.initExampleButtons();

        // 绑定新会话按钮
        this.newSessionBtn.addEventListener('click', async () => {
            await Tabs.createNewSession(this);
        });

        // 绑定"继续会话"复选框事件
        if (this.continueConversationCheckbox) {
            this.continueConversationCheckbox.addEventListener('change', (e) => {
                this.handleContinueConversationChange(e.target.checked);
            });
        }

        // 初始化"继续会话"复选框状态
        if (this.continueConversationCheckbox) {
            this.updateContinueConversationState();
        }

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

        // 绑定工作目录变更监听（用于更新继续会话复选框状态）
        if (this.workingDirInput) {
            this.workingDirInput.addEventListener('change', () => {
                this.handleWorkingDirChange();
            });
        }

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

        // 创建默认的"新任务"标签页
        Tabs.createNewSession(this);

        // v9.0.1: 初始化标签页快捷键和拖拽排序功能
        Tabs.init(this);

        // 恢复标签页排序
        Tabs._restoreTabOrder(this);

        // 快捷键
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                Task.runTask(this);
            }
        });
    }

    // ============== 继续会话功能 ==============

    /**
     * 获取最近的会话ID
     * @param {string} workingDir - 工作目录（可选，默认使用当前输入的工作目录）
     * @returns {Promise<string|null>} 最近会话ID或null
     */
    async getLatestSessionId(workingDir = null) {
        try {
            // v9.0.2: 使用传入的工作目录或当前输入的工作目录
            const dir = workingDir || this.workingDirInput?.value || '.';
            const encodedDir = encodeURIComponent(dir);
            const response = await fetch(`/api/sessions?working_dir=${encodedDir}&limit=1`);
            if (!response.ok) {
                console.warn('[继续会话] 获取最近会话失败:', response.status, response.statusText);
                return null;
            }
            const data = await response.json();
            if (data.sessions && data.sessions.length > 0) {
                const latestSession = data.sessions[0];
                return latestSession.id;
            }
            return null;
        } catch (error) {
            console.warn('[继续会话] 获取最近会话异常:', error);
            return null;
        }
    }

    /**
     * 更新"继续会话"复选框状态
     * @param {boolean} enabled - 是否启用复选框
     */
    updateContinueConversationCheckbox(enabled) {
        if (this.continueConversationCheckbox) {
            this.continueConversationCheckbox.disabled = !enabled;
            this.continueConversationCheckbox.title = enabled
                ? '延续最近会话的对话历史'
                : '当前会话模式下不可用';
        }
    }

    /**
     * 生成缓存 key（包含工作目录标识）
     * @param {string} workingDir - 工作目录
     * @returns {string} 缓存 key
     */
    _getCacheKey(workingDir) {
        // 使用简单的 hash 来区分不同工作目录
        const hash = workingDir.split('').reduce((a, b) => {
            a = ((a << 5) - a) + b.charCodeAt(0);
            return a & a;
        }, 0);
        return `claude_session_${Math.abs(hash)}`;
    }

    /**
     * 从本地存储获取缓存的最近会话ID（按工作目录区分）
     * @returns {string|null} 缓存的会话ID或null
     */
    getCachedLatestSessionId() {
        try {
            const workingDir = this.workingDirInput?.value || '.';
            const cacheKey = this._getCacheKey(workingDir);
            const cached = localStorage.getItem(cacheKey);
            const timestampKey = `${cacheKey}_timestamp`;
            const timestamp = localStorage.getItem(timestampKey);
            const now = Date.now();

            // 缓存有效期：1小时
            if (cached && timestamp && (now - parseInt(timestamp)) < 3600000) {
                return cached;
            }
            return null;
        } catch (error) {
            console.warn('[继续会话] 读取本地缓存失败:', error);
            return null;
        }
    }

    /**
     * 缓存最近会话ID到本地存储（按工作目录区分）
     * @param {string} sessionId - 会话ID
     */
    cacheLatestSessionId(sessionId) {
        try {
            const workingDir = this.workingDirInput?.value || '.';
            const cacheKey = this._getCacheKey(workingDir);
            const timestampKey = `${cacheKey}_timestamp`;
            localStorage.setItem(cacheKey, sessionId);
            localStorage.setItem(timestampKey, Date.now().toString());
        } catch (error) {
            console.warn('[继续会话] 缓存会话ID失败:', error);
        }
    }

    /**
     * 更新"继续会话"复选框状态和最近会话ID
     * @param {boolean} forceRefresh - 是否强制刷新（忽略缓存）
     */
    async updateContinueConversationState(forceRefresh = false) {
        const workingDir = this.workingDirInput?.value || '.';

        // 首先尝试从缓存获取（除非强制刷新）
        let latestSessionId = null;
        if (!forceRefresh) {
            latestSessionId = this.getCachedLatestSessionId();
        }

        // v9.0.2: 如果缓存不存在或已过期，从API获取（传递工作目录）
        if (!latestSessionId) {
            latestSessionId = await this.getLatestSessionId(workingDir);
            if (latestSessionId) {
                this.cacheLatestSessionId(latestSessionId);
            }
        }

        // 更新UI状态
        if (latestSessionId) {
            this.continueConversationCheckbox.disabled = false;
            this.continueConversationCheckbox.title = `延续最近会话的对话历史 (${workingDir})`;
            // 如果复选框已勾选，更新resume字段
            if (this.continueConversationCheckbox.checked) {
                this.resumeInput.value = latestSessionId;
                this.resumeInput.title = latestSessionId;
            }
        } else {
            this.continueConversationCheckbox.disabled = true;
            this.continueConversationCheckbox.checked = false;
            this.continueConversationCheckbox.title = `无历史会话可继续 (${workingDir})`;
            this.resumeInput.value = '';
            this.resumeInput.title = '';
        }
    }

    /**
     * 处理"继续会话"复选框状态变化
     * @param {boolean} checked - 复选框是否勾选
     */
    async handleContinueConversationChange(checked) {
        if (checked) {
            // v9.0.2: 获取当前工作目录
            const workingDir = this.workingDirInput?.value || '.';

            // 勾选时，获取最近会话ID并填充 resume 字段
            let latestSessionId = this.getCachedLatestSessionId();
            if (!latestSessionId) {
                // v9.0.2: 传递工作目录参数
                latestSessionId = await this.getLatestSessionId(workingDir);
                if (latestSessionId) {
                    this.cacheLatestSessionId(latestSessionId);
                }
            }

            if (latestSessionId) {
                this.resumeInput.value = latestSessionId;
                this.resumeInput.title = latestSessionId;
                console.log('[继续会话] 已勾选，自动填充会话ID:', latestSessionId);
            } else {
                // 没有最近的会话ID，取消勾选并提示
                this.continueConversationCheckbox.checked = false;
                Task.addMessage(this, 'text', '⚠️ 没有可继续的会话，请先执行一个任务');
                this.resumeInput.value = '';
                this.resumeInput.title = '';
            }
        } else {
            // 取消勾选时，清空 resume 字段
            this.resumeInput.value = '';
            this.resumeInput.title = '';
            console.log('[继续会话] 已取消，清空会话ID');
        }
    }

    /**
     * 处理工作目录变更
     */
    async handleWorkingDirChange() {
        const newDir = this.workingDirInput?.value || '.';
        console.log('[继续会话] 工作目录已变更:', newDir);

        // 清空当前的 resume 值（因为会话可能不在新目录中）
        if (this.continueConversationCheckbox?.checked) {
            this.continueConversationCheckbox.checked = false;
            this.resumeInput.value = '';
            this.resumeInput.title = '';
        }

        // 强制刷新继续会话状态（获取新目录的最近会话）
        await this.updateContinueConversationState(true);
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
