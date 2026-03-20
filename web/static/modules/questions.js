/**
 * 提问历史记录模块 (v8.0.2)
 * 管理提问历史记录的展示和交互
 */

const Questions = {
    // 分页状态
    projectsPage: 1,
    projectsLimit: 20,
    questionsPage: 1,
    questionsLimit: 20,
    projectsTotal: 0,
    questionsTotal: 0,

    // 虚拟列表实例
    projectVirtualList: null,
    questionVirtualList: null,

    // 懒加载状态
    projectsHasMore: true,
    questionsHasMore: true,
    isLoadingProjects: false,
    isLoadingQuestions: false,

    // 列表项高度（用于虚拟滚动）
    ITEM_HEIGHT_PROJECT: 76,
    ITEM_HEIGHT_QUESTION: 80,  // 提问项高度稍大，因为需要显示更多内容

    // 事件委托标记
    eventsInitialized: false,

    // 当前选中的项目
    currentProject: null,

    // 文本截断长度
    TEXT_TRUNCATE_LENGTH: 200,

    /**
     * 初始化模块
     */
    init() {
        this.bindEvents();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 返回项目列表按钮
        const backBtn = document.getElementById('questions-back-to-projects');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                this.showProjectsList();
            });
        }
    },

    /**
     * 视图显示时调用
     */
    onShow() {
        // 初始化全局事件委托
        this.initGlobalEvents();

        // 加载项目列表
        this.loadProjects();
    },

    /**
     * 视图隐藏时调用
     */
    onHide() {
        // 清理虚拟列表
        if (this.projectVirtualList) {
            this.projectVirtualList.destroy();
            this.projectVirtualList = null;
        }
        if (this.questionVirtualList) {
            this.questionVirtualList.destroy();
            this.questionVirtualList = null;
        }
    },

    /**
     * 显示项目列表
     */
    showProjectsList() {
        const projectsSection = document.getElementById('questions-projects');
        const questionsSection = document.getElementById('questions-list-section');

        if (projectsSection) projectsSection.style.display = 'flex';
        if (questionsSection) questionsSection.style.display = 'none';

        this.currentProject = null;
    },

    /**
     * 显示提问列表
     */
    showQuestionsList() {
        const projectsSection = document.getElementById('questions-projects');
        const questionsSection = document.getElementById('questions-list-section');

        if (projectsSection) projectsSection.style.display = 'none';
        if (questionsSection) questionsSection.style.display = 'flex';
    },

    /**
     * 初始化全局事件委托（只执行一次）
     */
    initGlobalEvents() {
        if (this.eventsInitialized) return;
        this.eventsInitialized = true;

        // 项目列表容器事件委托
        const projectContainer = document.querySelector('.questions-project-list-container');
        if (projectContainer) {
            projectContainer.addEventListener('click', (e) => {
                // 项目信息点击 - 进入提问列表
                const projectInfo = e.target.closest('.question-project-info');
                if (projectInfo) {
                    const item = projectInfo.closest('.question-project-item');
                    if (item && item.dataset.name) {
                        this.selectProject(item.dataset.name);
                    }
                }
            });
        }

        // 提问列表容器事件委托
        const questionContainer = document.querySelector('.questions-list-container');
        if (questionContainer) {
            questionContainer.addEventListener('click', (e) => {
                // 复制按钮点击
                const copyBtn = e.target.closest('.btn-copy-question');
                if (copyBtn) {
                    e.stopPropagation();
                    const fullText = copyBtn.dataset.fullText;
                    if (fullText) {
                        this.copyToClipboard(fullText, copyBtn);
                    }
                    return;
                }

                // 展开/收起按钮点击
                const expandBtn = e.target.closest('.btn-expand-question');
                if (expandBtn) {
                    e.stopPropagation();
                    const textEl = expandBtn.closest('.question-text');
                    if (textEl) {
                        this.toggleTextExpand(textEl, expandBtn);
                    }
                    return;
                }

                // 提问项点击 - 继续会话
                const questionItem = e.target.closest('.question-item');
                if (questionItem && questionItem.dataset.sessionId) {
                    this.continueSession(questionItem.dataset.sessionId);
                }
            });
        }
    },

    /**
     * 初始化项目列表虚拟滚动
     */
    initProjectVirtualList() {
        // 如果已存在实例，先销毁
        if (this.projectVirtualList) {
            this.projectVirtualList.destroy();
            this.projectVirtualList = null;
        }

        const container = document.querySelector('.questions-project-list-container');
        if (!container) return;

        this.projectVirtualList = VirtualList.create({
            container: container,
            itemHeight: this.ITEM_HEIGHT_PROJECT,
            overscan: 5,
            renderItem: (project, index) => this.renderProjectItem(project, index),
            onLoadMore: () => this.loadMoreProjects(),
            loadMoreThreshold: 200,
        });
    },

    /**
     * 初始化提问列表虚拟滚动
     */
    initQuestionVirtualList() {
        // 如果已存在实例，先销毁
        if (this.questionVirtualList) {
            this.questionVirtualList.destroy();
            this.questionVirtualList = null;
        }

        const container = document.querySelector('.questions-list-container');
        if (!container) return;

        this.questionVirtualList = VirtualList.create({
            container: container,
            itemHeight: this.ITEM_HEIGHT_QUESTION,
            overscan: 5,
            renderItem: (question, index) => this.renderQuestionItem(question, index),
            onLoadMore: () => this.loadMoreQuestions(),
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
        item.className = 'question-project-item virtual-list-item';
        item.dataset.name = project.encoded_name;
        item.dataset.path = Utils.escapeHtml(project.path);

        item.innerHTML = `
            <div class="question-project-info">
                <span class="project-path" title="${Utils.escapeHtml(project.path)}">${Utils.escapeHtml(project.path)}</span>
                <div class="project-meta">
                    <span class="question-count">${project.session_count || 0} 个提问</span>
                </div>
            </div>
            <span class="project-arrow">→</span>
        `;

        return item;
    },

    /**
     * 渲染单个提问列表项
     * @param {Object} question - 提问数据
     * @param {number} index - 索引
     * @returns {HTMLElement}
     */
    renderQuestionItem(question, index) {
        const item = document.createElement('div');
        item.className = 'question-item virtual-list-item';
        item.dataset.sessionId = question.session_id;

        const fullText = question.question_text || '';
        const truncatedText = this.truncateText(fullText, this.TEXT_TRUNCATE_LENGTH);
        const needsExpand = fullText.length > this.TEXT_TRUNCATE_LENGTH;
        const timeDisplay = question.time_display || this.formatTime(question.timestamp);

        item.innerHTML = `
            <div class="question-text" data-expanded="false" data-full-text="${Utils.escapeHtml(fullText)}">
                <span class="text-content">${Utils.escapeHtml(truncatedText)}</span>
                ${needsExpand ? '<button class="btn-expand-question" title="展开">展开</button>' : ''}
            </div>
            <div class="question-meta">
                <span class="question-time" data-timestamp="${question.timestamp}">${timeDisplay}</span>
                <button class="btn-copy-question" data-full-text="${Utils.escapeHtml(fullText)}" title="复制提问">📋</button>
            </div>
        `;

        return item;
    },

    /**
     * 加载项目列表
     * @param {number} page - 页码
     */
    async loadProjects(page = 1) {
        this.projectsPage = page;
        this.projectsHasMore = true;
        this.isLoadingProjects = false;

        // 显示加载状态
        if (page === 1) {
            if (this.projectVirtualList) {
                this.projectVirtualList.clear();
                this.projectVirtualList.setLoading(true);
            } else {
                const container = document.querySelector('.questions-project-list-container');
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
                this.initProjectVirtualList();
                this.projectVirtualList.setItems(projects);
                this.projectVirtualList.setHasMore(this.projectsHasMore);
            } else {
                // 追加数据
                this.projectVirtualList.setItems(projects, true);
                this.projectVirtualList.setHasMore(this.projectsHasMore);
            }

            // 更新分页信息显示
            this.renderProjectsPagination();

        } catch (error) {
            const container = document.querySelector('.questions-project-list-container');
            if (container) {
                container.innerHTML = `<div class="empty-placeholder">加载失败: ${error.message}</div>`;
            }
        }
    },

    /**
     * 加载更多项目
     */
    async loadMoreProjects() {
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
            this.projectVirtualList.setItems(projects, true);
            this.projectVirtualList.setHasMore(this.projectsHasMore);

            // 更新分页信息显示
            this.renderProjectsPagination();

        } catch (error) {
            console.error('加载更多项目失败:', error);
        } finally {
            this.isLoadingProjects = false;
            this.projectVirtualList.setLoading(false);
        }
    },

    /**
     * 渲染项目分页控件（改为状态显示）
     */
    renderProjectsPagination() {
        const paginationEl = document.getElementById('questions-projects-pagination');
        if (!paginationEl) return;

        const loadedCount = this.projectVirtualList ? this.projectVirtualList.getItems().length : 0;

        let html = `
            <span class="pagination-info">
                已加载 ${loadedCount} / ${this.projectsTotal} 个项目
                ${this.projectsHasMore ? '<span class="load-more-hint">滚动加载更多</span>' : ''}
            </span>
        `;

        paginationEl.innerHTML = html;
    },

    /**
     * 选择项目
     * @param {string} projectName - 项目名称
     */
    selectProject(projectName) {
        this.currentProject = projectName;
        this.questionsPage = 1;
        this.questionsHasMore = true;
        this.isLoadingQuestions = false;
        this.showQuestionsList();
        this.loadProjectQuestions(projectName);
    },

    /**
     * 加载项目提问列表
     * @param {string} projectName - 项目名称
     * @param {number} page - 页码
     */
    async loadProjectQuestions(projectName, page = 1) {
        this.questionsPage = page;
        this.questionsHasMore = true;
        this.isLoadingQuestions = false;

        // 显示加载状态
        if (page === 1) {
            if (this.questionVirtualList) {
                this.questionVirtualList.clear();
                this.questionVirtualList.setLoading(true);
            } else {
                const container = document.querySelector('.questions-list-container');
                if (container) {
                    container.innerHTML = '<div class="loading-placeholder">加载中...</div>';
                }
            }
        }

        const titleEl = document.getElementById('current-questions-project-title');
        if (titleEl) titleEl.textContent = '加载中...';

        try {
            const response = await fetch(`/api/projects/${encodeURIComponent(projectName)}/questions?page=${page}&limit=${this.questionsLimit}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // 检查响应格式
            if (!data.success) {
                throw new Error(data.error || '获取提问列表失败');
            }

            const questions = data.data?.items || [];
            this.questionsTotal = data.data?.total || 0;
            this.questionsPage = data.data?.page || 1;

            // 判断是否还有更多数据
            this.questionsHasMore = this.questionsPage * this.questionsLimit < this.questionsTotal;

            // 更新标题
            if (titleEl) {
                titleEl.textContent = data.data?.project_path || projectName;
            }

            if (page === 1) {
                // 首次加载，初始化虚拟列表
                this.initQuestionVirtualList();
                this.questionVirtualList.setItems(questions);
                this.questionVirtualList.setHasMore(this.questionsHasMore);
            } else {
                // 追加数据
                this.questionVirtualList.setItems(questions, true);
                this.questionVirtualList.setHasMore(this.questionsHasMore);
            }

            // 更新分页信息显示
            this.renderQuestionsPagination();

        } catch (error) {
            const container = document.querySelector('.questions-list-container');
            if (container) {
                container.innerHTML = `<div class="empty-placeholder">加载失败: ${error.message}</div>`;
            }
            if (titleEl) {
                titleEl.textContent = '加载失败';
            }
        }
    },

    /**
     * 加载更多提问
     */
    async loadMoreQuestions() {
        if (this.isLoadingQuestions || !this.questionsHasMore || !this.currentProject) return;

        this.isLoadingQuestions = true;
        this.questionVirtualList.setLoading(true);

        try {
            const nextPage = this.questionsPage + 1;
            const response = await fetch(`/api/projects/${encodeURIComponent(this.currentProject)}/questions?page=${nextPage}&limit=${this.questionsLimit}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            const questions = data.data?.items || [];
            this.questionsPage = data.data?.page || nextPage;
            this.questionsTotal = data.data?.total || 0;

            // 判断是否还有更多数据
            this.questionsHasMore = this.questionsPage * this.questionsLimit < this.questionsTotal;

            // 追加数据
            this.questionVirtualList.setItems(questions, true);
            this.questionVirtualList.setHasMore(this.questionsHasMore);

            // 更新分页信息显示
            this.renderQuestionsPagination();

        } catch (error) {
            console.error('加载更多提问失败:', error);
        } finally {
            this.isLoadingQuestions = false;
            this.questionVirtualList.setLoading(false);
        }
    },

    /**
     * 渲染提问分页控件（改为状态显示）
     */
    renderQuestionsPagination() {
        const paginationEl = document.getElementById('questions-pagination');
        if (!paginationEl) return;

        const loadedCount = this.questionVirtualList ? this.questionVirtualList.getItems().length : 0;

        let html = `
            <span class="pagination-info">
                已加载 ${loadedCount} / ${this.questionsTotal} 个提问
                ${this.questionsHasMore ? '<span class="load-more-hint">滚动加载更多</span>' : ''}
            </span>
        `;

        paginationEl.innerHTML = html;
    },

    /**
     * 继续会话
     * @param {string} sessionId - 会话 ID
     */
    async continueSession(sessionId) {
        // 使用 History 模块的 continueSession 方法
        const runner = window.runner;
        if (runner && typeof History !== 'undefined') {
            // 切换到当前会话视图
            Navigation.switchView(runner, Views.CURRENT_SESSION);
            // 继续会话
            await History.continueSession(runner, sessionId);
        }
    },

    /**
     * 复制文本到剪贴板
     * @param {string} text - 要复制的文本
     * @param {HTMLElement} btn - 触发按钮
     */
    async copyToClipboard(text, btn) {
        try {
            // 优先使用 Clipboard API
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
            } else {
                // fallback: 使用旧版方法
                this._copyToClipboardFallback(text);
            }
            // 显示成功提示
            const originalText = btn.textContent;
            btn.textContent = '✓';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.textContent = originalText;
                btn.classList.remove('copied');
            }, 2000);
        } catch (error) {
            console.error('复制失败:', error);
            // 显示错误提示
            alert('复制失败，请手动选择复制');
        }
    },

    /**
     * 复制文本到剪贴板（fallback 方案）
     * @param {string} text - 要复制的文本
     */
    _copyToClipboardFallback(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
        } finally {
            document.body.removeChild(textarea);
        }
    },

    /**
     * 切换文本展开/收起
     * @param {HTMLElement} textEl - 文本容器元素
     * @param {HTMLElement} btn - 按钮
     */
    toggleTextExpand(textEl, btn) {
        const isExpanded = textEl.dataset.expanded === 'true';
        const fullText = textEl.dataset.fullText;
        const textContent = textEl.querySelector('.text-content');

        if (isExpanded) {
            // 收起
            textContent.textContent = this.truncateText(fullText, this.TEXT_TRUNCATE_LENGTH);
            btn.textContent = '展开';
            textEl.dataset.expanded = 'false';
        } else {
            // 展开
            textContent.textContent = fullText;
            btn.textContent = '收起';
            textEl.dataset.expanded = 'true';
        }
    },

    /**
     * 截断文本
     * @param {string} text - 原始文本
     * @param {number} maxLength - 最大长度
     * @returns {string}
     */
    truncateText(text, maxLength) {
        if (!text || text.length <= maxLength) {
            return text || '';
        }
        return text.substring(0, maxLength) + '...';
    },

    /**
     * 格式化时间
     * @param {string} timestamp - ISO 格式时间戳
     * @returns {string}
     */
    formatTime(timestamp) {
        if (!timestamp) return '未知时间';

        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;

            // 小于 1 分钟
            if (diff < 60000) {
                return '刚刚';
            }

            // 小于 1 小时
            if (diff < 3600000) {
                return `${Math.floor(diff / 60000)} 分钟前`;
            }

            // 小于 24 小时
            if (diff < 86400000) {
                return `${Math.floor(diff / 3600000)} 小时前`;
            }

            // 昨天
            const yesterday = new Date(now);
            yesterday.setDate(yesterday.getDate() - 1);
            if (date.toDateString() === yesterday.toDateString()) {
                const hours = date.getHours().toString().padStart(2, '0');
                const minutes = date.getMinutes().toString().padStart(2, '0');
                return `昨天 ${hours}:${minutes}`;
            }

            // 小于 7 天
            if (diff < 604800000) {
                return `${Math.floor(diff / 86400000)} 天前`;
            }

            // >= 7 天
            const year = date.getFullYear();
            const month = (date.getMonth() + 1).toString().padStart(2, '0');
            const day = date.getDate().toString().padStart(2, '0');
            const hours = date.getHours().toString().padStart(2, '0');
            const minutes = date.getMinutes().toString().padStart(2, '0');

            return `${year}-${month}-${day} ${hours}:${minutes}`;
        } catch (error) {
            return '未知时间';
        }
    },

    /**
     * 显示问答卡片对话框
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} question - 问题数据
     * @param {Function} onAnswer - 答案回调函数
     */
    showQuestionCard(runner, question, onAnswer) {
        const questionText = question.question_text || '请回答问题';
        const questionType = question.type || 'single_choice';
        const options = question.options || [];

        // 构建选项 HTML
        let optionsHtml = '';
        if (options.length > 0) {
            optionsHtml = options.map((opt, idx) => `
                <div class="question-option" data-value="${Utils.escapeHtml(opt.id || String(idx))}">
                    <input type="${questionType === 'single_choice' ? 'radio' : 'checkbox'}"
                           name="question_option"
                           id="q_option_${idx}"
                           value="${Utils.escapeHtml(opt.id || String(idx))}">
                    <label for="q_option_${idx}">
                        <span class="option-label">${Utils.escapeHtml(opt.label || opt.description || '选项' + (idx + 1))}</span>
                        ${opt.description ? `<span class="option-desc">${Utils.escapeHtml(opt.description)}</span>` : ''}
                    </label>
                </div>
            `).join('');
        }

        // 创建对话框
        const dialog = document.createElement('div');
        dialog.className = 'question-dialog-overlay';
        dialog.innerHTML = `
            <div class="question-dialog">
                <div class="question-dialog-header">
                    <span class="question-icon">❓</span>
                    <span class="question-title">${question.header || '需要您的回答'}</span>
                </div>
                <div class="question-dialog-body">
                    <div class="question-text">${Utils.escapeHtml(questionText)}</div>
                    ${question.description ? `<div class="question-description">${Utils.escapeHtml(question.description)}</div>` : ''}
                    <div class="question-options">${optionsHtml}</div>
                    ${questionType !== 'text_input' ? '' : `
                        <div class="question-text-input">
                            <textarea id="question_custom_answer" rows="3" placeholder="请输入您的回答..."></textarea>
                        </div>
                    `}
                </div>
                <div class="question-dialog-footer">
                    <button class="btn btn-primary question-submit">确定</button>
                    <button class="btn btn-secondary question-cancel">取消</button>
                </div>
            </div>
        `;

        // 添加样式（如果还没有）
        this._injectQuestionDialogStyles();

        // 添加到 body
        document.body.appendChild(dialog);

        // 绑定事件
        const submitBtn = dialog.querySelector('.question-submit');
        const cancelBtn = dialog.querySelector('.question-cancel');

        submitBtn.addEventListener('click', () => {
            let answer = null;

            if (questionType === 'text_input') {
                answer = dialog.querySelector('#question_custom_answer')?.value;
            } else if (questionType === 'multiple_choice') {
                const checked = dialog.querySelectorAll('input[name="question_option"]:checked');
                answer = Array.from(checked).map(cb => cb.value);
            } else {
                const checked = dialog.querySelector('input[name="question_option"]:checked');
                answer = checked ? checked.value : null;
            }

            if (answer !== null && answer !== '') {
                document.body.removeChild(dialog);
                onAnswer(answer);
            } else {
                alert('请选择一个选项或输入回答');
            }
        });

        cancelBtn.addEventListener('click', () => {
            document.body.removeChild(dialog);
            onAnswer(false);
        });

        // ESC 键关闭
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                document.body.removeChild(dialog);
                document.removeEventListener('keydown', escHandler);
                onAnswer(false);
            }
        };
        document.addEventListener('keydown', escHandler);
    },

    /**
     * 注入问答对话框样式
     * @private
     */
    _injectQuestionDialogStyles() {
        if (document.getElementById('question-dialog-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'question-dialog-styles';
        styles.textContent = `
            .question-dialog-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            }
            .question-dialog {
                background: var(--bg-primary, #fff);
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow: auto;
            }
            .question-dialog-header {
                padding: 16px 20px;
                border-bottom: 1px solid var(--border-color, #e5e7eb);
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .question-icon { font-size: 20px; }
            .question-title { font-weight: 600; font-size: 16px; }
            .question-dialog-body { padding: 20px; }
            .question-text { font-size: 15px; line-height: 1.6; margin-bottom: 12px; }
            .question-description { font-size: 13px; color: #666; margin-bottom: 16px; }
            .question-options { display: flex; flex-direction: column; gap: 8px; }
            .question-option {
                display: flex;
                align-items: flex-start;
                gap: 8px;
                padding: 10px 12px;
                border: 1px solid var(--border-color, #e5e7eb);
                border-radius: 8px;
                cursor: pointer;
                transition: background 0.2s;
            }
            .question-option:hover { background: var(--bg-hover, #f3f4f6); }
            .question-option input { margin-top: 3px; }
            .question-option label { flex: 1; cursor: pointer; }
            .option-label { font-weight: 500; }
            .option-desc { display: block; font-size: 12px; color: #666; margin-top: 2px; }
            .question-text-input textarea {
                width: 100%;
                padding: 10px;
                border: 1px solid var(--border-color, #e5e7eb);
                border-radius: 8px;
                font-size: 14px;
                resize: vertical;
            }
            .question-dialog-footer {
                padding: 16px 20px;
                border-top: 1px solid var(--border-color, #e5e7eb);
                display: flex;
                justify-content: flex-end;
                gap: 10px;
            }
        `;
        document.head.appendChild(styles);
    },
};

// 导出到全局命名空间
window.Questions = Questions;
