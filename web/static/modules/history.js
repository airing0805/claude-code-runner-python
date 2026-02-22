/**
 * 历史记录管理模块
 * 处理项目列表和会话历史的加载与显示
 * v0.5.6: 增加虚拟滚动和懒加载支持
 */

const History = {
    // 分页状态
    projectsPage: 1,
    projectsLimit: 20,
    sessionsPage: 1,
    sessionsLimit: 20,
    projectsTotal: 0,
    sessionsTotal: 0,

    // 虚拟列表实例
    projectVirtualList: null,
    sessionVirtualList: null,

    // 懒加载状态
    projectsHasMore: true,
    sessionsHasMore: true,
    isLoadingProjects: false,
    isLoadingSessions: false,

    // 列表项高度（用于虚拟滚动）
    ITEM_HEIGHT_PROJECT: 76,
    ITEM_HEIGHT_SESSION: 76,

    // 事件委托标记
    eventsInitialized: false,

    /**
     * 显示项目列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    showProjectsList(runner) {
        runner.historyProjects.style.display = 'flex';
        runner.historySessions.style.display = 'none';
        runner.currentProject = null;
        // 返回项目列表时重新加载数据，确保显示最新的会话数量
        this.loadProjects(runner);
    },

    /**
     * 显示会话列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    showSessionsList(runner) {
        runner.historyProjects.style.display = 'none';
        runner.historySessions.style.display = 'flex';
    },

    /**
     * 初始化全局事件委托（只执行一次）
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    initGlobalEvents(runner) {
        if (this.eventsInitialized) return;
        this.eventsInitialized = true;

        // 项目列表容器事件委托
        const projectContainer = document.querySelector('.project-list-container');
        projectContainer.addEventListener('click', (e) => {
            // 项目信息点击 - 进入会话列表
            const projectInfo = e.target.closest('.project-info');
            if (projectInfo) {
                const item = projectInfo.closest('.project-item');
                if (item && item.dataset.name) {
                    this.selectProject(runner, item.dataset.name);
                }
                return;
            }

            // 新会话按钮点击
            const newSessionBtn = e.target.closest('.btn-new-project-session');
            if (newSessionBtn) {
                e.stopPropagation();
                Session.createNewSessionFromProject(runner, newSessionBtn.dataset.path);
            }
        });

        // 会话列表容器事件委托
        const sessionContainer = document.querySelector('.session-list-container');
        sessionContainer.addEventListener('click', (e) => {
            // 继续会话按钮点击
            const continueBtn = e.target.closest('.btn-continue');
            if (continueBtn) {
                e.stopPropagation();
                const item = continueBtn.closest('.session-item');
                if (item && item.dataset.id) {
                    this.continueSession(runner, item.dataset.id);
                }
            }
        });
    },

    /**
     * 初始化项目列表虚拟滚动
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    initProjectVirtualList(runner) {
        // 初始化全局事件委托
        this.initGlobalEvents(runner);

        // 如果已存在实例，先销毁
        if (this.projectVirtualList) {
            this.projectVirtualList.destroy();
            this.projectVirtualList = null;
        }

        const container = document.querySelector('.project-list-container');
        if (!container) return;

        this.projectVirtualList = VirtualList.create({
            container: container,
            itemHeight: this.ITEM_HEIGHT_PROJECT,
            overscan: 5,
            renderItem: (project, index) => this.renderProjectItem(project, index),
            onLoadMore: () => this.loadMoreProjects(runner),
            loadMoreThreshold: 200,
        });
    },

    /**
     * 初始化会话列表虚拟滚动
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    initSessionVirtualList(runner) {
        // 初始化全局事件委托
        this.initGlobalEvents(runner);

        // 如果已存在实例，先销毁
        if (this.sessionVirtualList) {
            this.sessionVirtualList.destroy();
            this.sessionVirtualList = null;
        }

        const container = document.querySelector('.session-list-container'); // .session-list-container

        this.sessionVirtualList = VirtualList.create({
            container: container,
            itemHeight: this.ITEM_HEIGHT_SESSION,
            overscan: 5,
            renderItem: (session, index) => this.renderSessionItem(session, index, runner),
            onLoadMore: () => this.loadMoreSessions(runner),
            loadMoreThreshold: 200,
        });
    },

    /**
     * 渲染单个项目列表项
     * @param {Object} project - 项目数据
     * @param {number} index - 索引
     * @returns {HTMLElement}
     */
    renderProjectItem(project, index) {
        const item = document.createElement('div');
        item.className = 'project-item virtual-list-item';
        item.dataset.name = project.encoded_name;
        item.dataset.path = Utils.escapeHtml(project.path);

        const toolsHtml = project.tools && project.tools.length > 0
            ? `<span class="project-tools" title="使用的工具: ${project.tools.join(', ')}">${project.tools.slice(0, 4).join(', ')}${project.tools.length > 4 ? '...' : ''}</span>`
            : '';

        item.innerHTML = `
            <div class="project-info">
                <span class="project-path" title="${Utils.escapeHtml(project.path)}">${Utils.escapeHtml(project.path)}</span>
                <div class="project-meta">
                    <span class="project-count">${project.session_count} 个会话</span>
                    ${toolsHtml}
                </div>
            </div>
            <button class="btn btn-new-project-session" data-path="${Utils.escapeHtml(project.path)}" title="在此项目中创建新会话">➕ 新会话</button>
        `;

        return item;
    },

    /**
     * 渲染单个会话列表项
     * @param {Object} session - 会话数据
     * @param {number} index - 索引
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @returns {HTMLElement}
     */
    renderSessionItem(session, index, runner) {
        const item = document.createElement('div');
        item.className = `session-item virtual-list-item ${session.id === runner.currentSessionId ? 'selected' : ''}`;
        item.dataset.id = session.id;

        const time = session.timestamp ? Utils.formatDateTime(session.timestamp) : '未知时间';

        item.innerHTML = `
            <div class="session-title">${Utils.escapeHtml(session.title)}</div>
            <div class="session-meta">${time} · ${session.message_count || 0} 条消息</div>
            <div class="session-actions">
                <button class="btn btn-primary btn-continue">继续此会话</button>
            </div>
        `;

        return item;
    },

    /**
     * 加载项目列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {number} page - 页码
     */
    async loadProjects(runner, page = 1) {
        this.projectsPage = page;
        this.projectsHasMore = true;
        this.isLoadingProjects = false;

        // 显示加载状态
        if (page === 1) {
            // 如果虚拟列表已存在，显示加载状态
            if (this.projectVirtualList) {
                this.projectVirtualList.clear();
                this.projectVirtualList.setLoading(true);
            } else {
                // 首次加载，直接在容器中显示加载状态
                const container = document.querySelector('.project-list-container');
                if (container) {
                    container.innerHTML = '<div class="loading-placeholder">加载中...</div>';
                }
            }
        }

        try {
            const response = await fetch(`/api/projects?page=${page}&limit=${this.projectsLimit}`);
            const data = await response.json();

            const projects = data.projects || [];
            this.projectsTotal = data.total || 0;
            this.projectsPage = data.page || 1;

            // 判断是否还有更多数据
            this.projectsHasMore = this.projectsPage * this.projectsLimit < this.projectsTotal;

            if (page === 1) {
                // 首次加载，初始化虚拟列表
                runner.projects = projects;
                this.initProjectVirtualList(runner);
                this.projectVirtualList.setItems(projects);
                this.projectVirtualList.setHasMore(this.projectsHasMore);
            } else {
                // 追加数据
                runner.projects = [...runner.projects, ...projects];
                this.projectVirtualList.setItems(projects, true);
                this.projectVirtualList.setHasMore(this.projectsHasMore);
            }

            // 更新分页信息显示
            this.renderProjectsPagination(runner);

            // 同时更新工作目录列表
            runner.workingDirs = runner.projects.map(p => p.path);
            const defaultDir = runner.workingDirInput ? runner.workingDirInput.value : '';
            if (defaultDir && !runner.workingDirs.includes(defaultDir)) {
                runner.workingDirs.unshift(defaultDir);
            }
            if (typeof WorkingDir !== 'undefined') {
                WorkingDir.renderWorkingDirOptions(runner);
            }

        } catch (error) {
            const container = document.querySelector('.project-list-container');
            if (container) {
                container.innerHTML = `<div class="empty-placeholder">加载失败: ${error.message}</div>`;
            }
        }
    },

    /**
     * 加载更多项目
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    async loadMoreProjects(runner) {
        if (this.isLoadingProjects || !this.projectsHasMore) return;

        this.isLoadingProjects = true;
        this.projectVirtualList.setLoading(true);

        try {
            const nextPage = this.projectsPage + 1;
            const response = await fetch(`/api/projects?page=${nextPage}&limit=${this.projectsLimit}`);
            const data = await response.json();

            const projects = data.projects || [];
            this.projectsPage = data.page || nextPage;
            this.projectsTotal = data.total || 0;

            // 判断是否还有更多数据
            this.projectsHasMore = this.projectsPage * this.projectsLimit < this.projectsTotal;

            // 追加数据
            runner.projects = [...runner.projects, ...projects];
            this.projectVirtualList.setItems(projects, true);
            this.projectVirtualList.setHasMore(this.projectsHasMore);

            // 更新分页信息显示
            this.renderProjectsPagination(runner);

        } catch (error) {
            console.error('加载更多项目失败:', error);
        } finally {
            this.isLoadingProjects = false;
            this.projectVirtualList.setLoading(false);
        }
    },

    /**
     * 渲染项目分页控件（改为状态显示）
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    renderProjectsPagination(runner) {
        const paginationEl = document.getElementById('projects-pagination');
        if (!paginationEl) return;

        const loadedCount = runner.projects ? runner.projects.length : 0;

        // 显示加载状态信息，而不是分页按钮
        let html = `
            <span class="pagination-info">
                已加载 ${loadedCount} / ${this.projectsTotal} 个项目
                ${this.projectsHasMore ? '<span class="load-more-hint">滚动加载更多</span>' : ''}
            </span>
        `;

        paginationEl.innerHTML = html;
    },

    /**
     * 跳转到指定项目页（保留兼容性，但不推荐使用）
     * @param {number} page - 页码
     */
    goToProjectsPage(page) {
        const runner = window.runner;
        if (!runner) return;

        // 使用传统分页方式（销毁虚拟滚动）
        const totalPages = Math.ceil(this.projectsTotal / this.projectsLimit);
        if (page < 1 || page > totalPages) return;

        // 销毁虚拟列表，使用传统加载
        if (this.projectVirtualList) {
            this.projectVirtualList.destroy();
            this.projectVirtualList = null;
        }

        this.loadProjects(runner, page);
    },

    /**
     * 选择项目
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} projectName - 项目名称
     */
    selectProject(runner, projectName) {
        runner.currentProject = projectName;
        this.sessionsPage = 1;
        this.sessionsHasMore = true;
        this.isLoadingSessions = false;
        this.showSessionsList(runner);
        this.loadProjectSessions(runner, projectName);
    },

    /**
     * 加载项目会话列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} projectName - 项目名称
     * @param {number} page - 页码
     */
    async loadProjectSessions(runner, projectName, page = 1) {
        this.sessionsPage = page;
        this.sessionsHasMore = true;
        this.isLoadingSessions = false;

        // 显示加载状态
        if (page === 1) {
            // 如果虚拟列表已存在，显示加载状态
            if (this.sessionVirtualList) {
                this.sessionVirtualList.clear();
                this.sessionVirtualList.setLoading(true);
            } else {
                // 首次加载，直接在容器中显示加载状态
                const container = document.querySelector('.session-list-container');
                if (container) {
                    container.innerHTML = '<div class="loading-placeholder">加载中...</div>';
                }
            }
        }
        document.getElementById('current-project-title').textContent = '加载中...';

        try {
            const response = await fetch(`/api/projects/${encodeURIComponent(projectName)}/sessions?page=${page}&limit=${this.sessionsLimit}`);
            const data = await response.json();

            const sessions = data.sessions || [];
            this.sessionsTotal = data.total || 0;
            this.sessionsPage = data.page || 1;

            // 判断是否还有更多数据
            this.sessionsHasMore = this.sessionsPage * this.sessionsLimit < this.sessionsTotal;

            document.getElementById('current-project-title').textContent = data.project_path || projectName;

            if (page === 1) {
                // 首次加载，初始化虚拟列表
                runner.sessions = sessions;
                this.initSessionVirtualList(runner);
                this.sessionVirtualList.setItems(sessions);
                this.sessionVirtualList.setHasMore(this.sessionsHasMore);
            } else {
                // 追加数据
                runner.sessions = [...runner.sessions, ...sessions];
                this.sessionVirtualList.setItems(sessions, true);
                this.sessionVirtualList.setHasMore(this.sessionsHasMore);
            }

            // 更新分页信息显示
            this.renderSessionsPagination(runner);

        } catch (error) {
            const container = document.querySelector('.session-list-container');
            if (container) {
                container.innerHTML = `<div class="empty-placeholder">加载失败: ${error.message}</div>`;
            }
        }
    },

    /**
     * 加载更多会话
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    async loadMoreSessions(runner) {
        if (this.isLoadingSessions || !this.sessionsHasMore || !runner.currentProject) return;

        this.isLoadingSessions = true;
        this.sessionVirtualList.setLoading(true);

        try {
            const nextPage = this.sessionsPage + 1;
            const response = await fetch(`/api/projects/${encodeURIComponent(runner.currentProject)}/sessions?page=${nextPage}&limit=${this.sessionsLimit}`);
            const data = await response.json();

            const sessions = data.sessions || [];
            this.sessionsPage = data.page || nextPage;
            this.sessionsTotal = data.total || 0;

            // 判断是否还有更多数据
            this.sessionsHasMore = this.sessionsPage * this.sessionsLimit < this.sessionsTotal;

            // 追加数据
            runner.sessions = [...runner.sessions, ...sessions];
            this.sessionVirtualList.setItems(sessions, true);
            this.sessionVirtualList.setHasMore(this.sessionsHasMore);

            // 更新分页信息显示
            this.renderSessionsPagination(runner);

        } catch (error) {
            console.error('加载更多会话失败:', error);
        } finally {
            this.isLoadingSessions = false;
            this.sessionVirtualList.setLoading(false);
        }
    },

    /**
     * 渲染会话分页控件（改为状态显示）
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    renderSessionsPagination(runner) {
        const paginationEl = document.getElementById('sessions-pagination');
        if (!paginationEl) return;

        const loadedCount = runner.sessions ? runner.sessions.length : 0;

        // 显示加载状态信息，而不是分页按钮
        let html = `
            <span class="pagination-info">
                已加载 ${loadedCount} / ${this.sessionsTotal} 个会话
                ${this.sessionsHasMore ? '<span class="load-more-hint">滚动加载更多</span>' : ''}
            </span>
        `;

        paginationEl.innerHTML = html;
    },

    /**
     * 跳转到指定会话页（保留兼容性，但不推荐使用）
     * @param {string} projectName - 项目名称
     * @param {number} page - 页码
     */
    goToSessionsPage(projectName, page) {
        const totalPages = Math.ceil(this.sessionsTotal / this.sessionsLimit);
        if (page < 1 || page > totalPages) return;

        const runner = window.runner;
        if (runner) {
            // 销毁虚拟列表，使用传统加载
            if (this.sessionVirtualList) {
                this.sessionVirtualList.destroy();
                this.sessionVirtualList = null;
            }

            this.loadProjectSessions(runner, projectName, page);
        }
    },

    /**
     * 继续会话
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} sessionId - 会话 ID
     */
    async continueSession(runner, sessionId) {
        runner.currentSessionId = sessionId;

        // 检查是否已有该会话的标签
        const existingTab = runner.tabs.find(t => t.sessionId === sessionId);
        if (existingTab) {
            Navigation.switchView(runner, Views.CURRENT_SESSION);
            Tabs.switchToTab(runner, existingTab.id);
            return;
        }

        // 加载会话历史消息
        try {
            const response = await fetch(`/api/sessions/${sessionId}/messages`);

            // 检查 HTTP 状态
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            // 验证 messages 是数组
            let messages = [];
            if (Array.isArray(data.messages)) {
                messages = data.messages;
            } else if (data.messages) {
                console.warn('messages 不是数组:', data.messages);
            }

            const projectPath = data.project_path || '';

            // 从第一条用户消息的 content 数组中提取文本标题，排除 ide_selection 标签
            let title = `会话 ${sessionId.substring(0, 8)}`;
            if (messages.length > 0 && messages[0].content) {
                const extractedTitle = Utils.extractTitleFromContent(messages[0].content);
                if (extractedTitle) {
                    title = extractedTitle.substring(0, 50);
                }
            }

            // 切换到当前会话视图
            Navigation.switchView(runner, Views.CURRENT_SESSION);

            // 创建新标签页
            Tabs.createSessionTab(runner, sessionId, title, messages, projectPath);

            // 填充会话信息
            runner.resumeInput.value = sessionId;
            runner.resumeInput.title = sessionId;
            document.getElementById('continue-conversation').checked = false;

            // 设置工作目录并禁用编辑
            if (projectPath) {
                WorkingDir.setWorkingDir(runner, projectPath);
            }
            Session.setSessionEditable(runner, false);
        } catch (error) {
            console.error('加载会话历史失败:', error);
            // 即使加载失败也创建标签
            Navigation.switchView(runner, Views.CURRENT_SESSION);
            Tabs.createSessionTab(runner, sessionId, `会话 ${sessionId.substring(0, 8)}`, [], '');
            runner.resumeInput.value = sessionId;
            runner.resumeInput.title = sessionId;
            Session.setSessionEditable(runner, false);
        }
    }
};

// 导出到全局命名空间
window.History = History;
