/**
 * 历史记录管理模块
 * 处理项目列表和会话历史的加载与显示
 */

const History = {
    /**
     * 显示项目列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    showProjectsList(runner) {
        runner.historyProjects.style.display = 'block';
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
        runner.historySessions.style.display = 'block';
    },

    /**
     * 加载项目列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    async loadProjects(runner) {
        try {
            const response = await fetch('/api/projects');
            const data = await response.json();
            runner.projects = data.projects || [];
            this.renderProjectList(runner);

            // 同时更新工作目录列表
            runner.workingDirs = runner.projects.map(p => p.path);
            const defaultDir = runner.workingDirInput.value;
            if (defaultDir && !runner.workingDirs.includes(defaultDir)) {
                runner.workingDirs.unshift(defaultDir);
            }
            WorkingDir.renderWorkingDirOptions(runner);
        } catch (error) {
            runner.projectList.innerHTML = `<div class="empty-placeholder">加载失败: ${error.message}</div>`;
        }
    },

    /**
     * 渲染项目列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    renderProjectList(runner) {
        if (runner.projects.length === 0) {
            runner.projectList.innerHTML = '<div class="empty-placeholder">暂无项目</div>';
            return;
        }

        runner.projectList.innerHTML = runner.projects.map(project => {
            const toolsHtml = project.tools && project.tools.length > 0
                ? `<span class="project-tools" title="使用的工具: ${project.tools.join(', ')}">${project.tools.slice(0, 4).join(', ')}${project.tools.length > 4 ? '...' : ''}</span>`
                : '';

            return `
                <div class="project-item" data-name="${project.encoded_name}" data-path="${Utils.escapeHtml(project.path)}">
                    <div class="project-info">
                        <span class="project-path" title="${Utils.escapeHtml(project.path)}">${Utils.escapeHtml(project.path)}</span>
                        <div class="project-meta">
                            <span class="project-count">${project.session_count} 个会话</span>
                            ${toolsHtml}
                        </div>
                    </div>
                    <button class="btn btn-new-project-session" data-path="${Utils.escapeHtml(project.path)}" title="在此项目中创建新会话">➕ 新会话</button>
                </div>
            `;
        }).join('');

        // 绑定项目点击事件（点击项目信息区域进入会话列表）
        runner.projectList.querySelectorAll('.project-item .project-info').forEach(info => {
            info.addEventListener('click', () => {
                const item = info.closest('.project-item');
                this.selectProject(runner, item.dataset.name);
            });
        });

        // 绑定新会话按钮点击事件
        runner.projectList.querySelectorAll('.btn-new-project-session').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                Session.createNewSessionFromProject(runner, btn.dataset.path);
            });
        });
    },

    /**
     * 选择项目
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} projectName - 项目名称
     */
    selectProject(runner, projectName) {
        runner.currentProject = projectName;
        this.showSessionsList(runner);
        this.loadProjectSessions(runner, projectName);
    },

    /**
     * 加载项目会话列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {string} projectName - 项目名称
     */
    async loadProjectSessions(runner, projectName) {
        // 清空缓存，确保每次都重新加载最新数据
        runner.sessions = [];
        runner.sessionList.innerHTML = '<div class="loading-placeholder">加载中...</div>';
        document.getElementById('current-project-title').textContent = '加载中...';

        try {
            const response = await fetch(`/api/projects/${encodeURIComponent(projectName)}/sessions`);
            const data = await response.json();
            runner.sessions = data.sessions || [];
            document.getElementById('current-project-title').textContent = data.project_path || projectName;
            this.renderSessionList(runner);
        } catch (error) {
            runner.sessionList.innerHTML = `<div class="empty-placeholder">加载失败: ${error.message}</div>`;
        }
    },

    /**
     * 渲染会话列表
     * @param {Object} runner - ClaudeCodeRunner 实例
     */
    renderSessionList(runner) {
        if (runner.sessions.length === 0) {
            runner.sessionList.innerHTML = '<div class="empty-placeholder">暂无历史会话</div>';
            return;
        }

        runner.sessionList.innerHTML = runner.sessions.map(session => {
            const time = session.timestamp ? Utils.formatDateTime(session.timestamp) : '未知时间';
            const isSelected = session.id === runner.currentSessionId;

            return `
                <div class="session-item ${isSelected ? 'selected' : ''}" data-id="${session.id}">
                    <div class="session-title">${Utils.escapeHtml(session.title)}</div>
                    <div class="session-meta">${time} · ${session.message_count || 0} 条消息</div>
                    <div class="session-actions">
                        <button class="btn btn-primary btn-continue">继续此会话</button>
                    </div>
                </div>
            `;
        }).join('');

        // 绑定点击事件
        runner.sessionList.querySelectorAll('.session-item').forEach(item => {
            const continueBtn = item.querySelector('.btn-continue');
            continueBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.continueSession(runner, item.dataset.id);
            });
        });
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
