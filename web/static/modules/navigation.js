/**
 * 导航模块
 * 处理视图切换和导航菜单交互
 */

const Navigation = {
    /**
     * 初始化导航
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    init(runner) {
        // 菜单项点击
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                this.switchView(runner, view);
            });
        });

        // 收起/展开菜单
        const navToggle = document.getElementById('nav-toggle');
        if (navToggle) {
            navToggle.addEventListener('click', () => {
                runner.navMenu.classList.toggle('collapsed');
            });
        }

        // 移动端菜单切换
        const menuToggle = document.getElementById('menu-toggle');
        if (menuToggle) {
            menuToggle.addEventListener('click', () => {
                runner.navMenu.classList.toggle('open');
            });
        }

        const menuToggleHistory = document.getElementById('menu-toggle-history');
        if (menuToggleHistory) {
            menuToggleHistory.addEventListener('click', () => {
                runner.navMenu.classList.toggle('open');
            });
        }

        const menuToggleExamples = document.getElementById('menu-toggle-examples');
        if (menuToggleExamples) {
            menuToggleExamples.addEventListener('click', () => {
                runner.navMenu.classList.toggle('open');
            });
        }

        const menuToggleClaudeStatus = document.getElementById('menu-toggle-claude-status');
        if (menuToggleClaudeStatus) {
            menuToggleClaudeStatus.addEventListener('click', () => {
                runner.navMenu.classList.toggle('open');
            });
        }

        const menuToggleAgentMonitor = document.getElementById('menu-toggle-agent-monitor');
        if (menuToggleAgentMonitor) {
            menuToggleAgentMonitor.addEventListener('click', () => {
                runner.navMenu.classList.toggle('open');
            });
        }

        // 返回项目列表
        const backToProjects = document.getElementById('back-to-projects');
        if (backToProjects) {
            backToProjects.addEventListener('click', () => {
                History.showProjectsList(runner);
            });
        }
    },

    /**
     * 切换视图
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} view - 视图名称
     */
    switchView(runner, view) {
        runner.currentView = view;

        // 更新菜单高亮
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.view === view);
        });

        // 切换视图
        document.querySelectorAll('.view-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        const viewPanel = document.getElementById(`view-${view}`);
        if (viewPanel) {
            viewPanel.classList.add('active');
        }

        // 如果是历史记录视图，重置并加载项目列表
        if (view === Views.HISTORY) {
            // 直接设置显示状态，不调用 showProjectsList（避免重复加载）
            runner.historyProjects.style.display = 'block';
            runner.historySessions.style.display = 'none';
            runner.currentProject = null;
            // 重新加载项目列表
            runner.projects = [];
            History.loadProjects(runner);
        }

        // 如果是 Claude 状态视图，加载状态数据
        if (view === Views.CLAUDE_STATUS) {
            if (typeof ClaudeStatus !== 'undefined') {
                ClaudeStatus.onShow();
            }
            if (typeof MCPManager !== 'undefined') {
                MCPManager.onShow();
            }
            if (typeof HooksManager !== 'undefined') {
                HooksManager.onShow();
            }
        }

        // 如果是 Agent 监控视图，加载代理数据
        if (view === Views.AGENT_MONITOR) {
            if (typeof AgentMonitor !== 'undefined') {
                AgentMonitor.onShow();
            }
        }

        // 如果是技能管理视图，加载技能数据
        if (view === Views.SKILLS) {
            if (typeof SkillManager !== 'undefined') {
                SkillManager.onShow();
            }
        }

        // 移动端收起菜单
        if (window.innerWidth <= 768) {
            runner.navMenu.classList.remove('open');
        }
    }
};

// 导出到全局命名空间
window.Navigation = Navigation;
