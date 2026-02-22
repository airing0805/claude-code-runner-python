/**
 * AskUserQuestion 对话框组件
 * 处理问答消息的渲染和用户交互
 */

const AskUserQuestionDialog = {
    /**
     * 当前活跃的问答对话框数据
     */
    _currentQuestion: null,

    /**
     * 存储 session_id
     */
    _sessionId: null,

    /**
     * 显示问答对话框
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} questionData - 问答数据
     * @param {string} sessionId - 会话 ID
     */
    show(runner, questionData, sessionId) {
        this._currentQuestion = questionData;
        this._sessionId = sessionId;

        // 创建对话框元素
        const dialogEl = this._createDialogElement(questionData);
        runner.outputEl.appendChild(dialogEl);

        // 滚动到底部
        Utils.scrollToBottom(runner.outputEl);
    },

    /**
     * 创建对话框 DOM 元素
     * @param {Object} questionData - 问答数据
     * @returns {HTMLElement} 对话框元素
     */
    _createDialogElement(questionData) {
        const container = document.createElement('div');
        container.className = 'assistant-msg assistant-msg-ask_user_question';
        container.dataset.questionId = questionData.question_id;

        const header = questionData.header || '请确认';
        const description = questionData.description || '';

        let optionsHtml = '';
        if (questionData.type === 'multiple_choice' || questionData.type === 'checkbox') {
            optionsHtml = this._renderOptions(questionData);
        } else if (questionData.type === 'text') {
            optionsHtml = this._renderTextInput(questionData);
        } else if (questionData.type === 'boolean') {
            optionsHtml = this._renderBooleanInput(questionData);
        }

        container.innerHTML = `
            <div class="question-header">
                <span class="question-icon">💬</span>
                <span class="question-title">${Utils.escapeHtml(header)}</span>
            </div>
            <div class="question-content">
                <div class="question-text">${Utils.escapeHtml(questionData.question_text)}</div>
                ${description ? `<div class="question-description">${Utils.escapeHtml(description)}</div>` : ''}
                <div class="question-options">${optionsHtml}</div>
            </div>
            <div class="question-actions">
                <button class="btn-cancel" type="button">取消</button>
                <button class="btn-confirm" type="button" disabled>确认</button>
            </div>
            <div class="follow-up-questions-container"></div>
        `;

        // 绑定事件
        this._bindEvents(container, questionData);

        return container;
    },

    /**
     * 渲染选项
     * @param {Object} questionData - 问答数据
     * @returns {string} 选项 HTML
     */
    _renderOptions(questionData) {
        const isCheckbox = questionData.type === 'checkbox';
        const options = questionData.options || [];

        return options.map(opt => `
            <label class="option-item ${isCheckbox ? 'checkbox' : 'radio'}">
                <input
                    type="${isCheckbox ? 'checkbox' : 'radio'}"
                    name="question_${questionData.question_id}"
                    value="${Utils.escapeHtml(opt.id)}"
                    ${opt.default ? 'checked' : ''}
                >
                <span class="option-label">${Utils.escapeHtml(opt.label)}</span>
                ${opt.description ? `<span class="option-description">${Utils.escapeHtml(opt.description)}</span>` : ''}
            </label>
        `).join('');
    },

    /**
     * 渲染文本输入框
     * @param {Object} questionData - 问答数据
     * @returns {string} 输入框 HTML
     */
    _renderTextInput(questionData) {
        return `
            <div class="text-input-container">
                <input
                    type="text"
                    class="question-text-input"
                    placeholder="请输入..."
                    data-question-id="${questionData.question_id}"
                >
            </div>
        `;
    },

    /**
     * 渲染布尔输入（是/否）
     * @param {Object} questionData - 问答数据
     * @returns {string} 布尔输入 HTML
     */
    _renderBooleanInput(questionData) {
        return `
            <label class="option-item radio">
                <input
                    type="radio"
                    name="question_${questionData.question_id}"
                    value="true"
                >
                <span class="option-label">是</span>
            </label>
            <label class="option-item radio">
                <input
                    type="radio"
                    name="question_${questionData.question_id}"
                    value="false"
                    checked
                >
                <span class="option-label">否</span>
            </label>
        `;
    },

    /**
     * 绑定事件
     * @param {HTMLElement} container - 对话框容器
     * @param {Object} questionData - 问答数据
     */
    _bindEvents(container, questionData) {
        const confirmBtn = container.querySelector('.btn-confirm');
        const cancelBtn = container.querySelector('.btn-cancel');
        const optionsContainer = container.querySelector('.question-options');
        const textInput = container.querySelector('.question-text-input');

        // 选项变更事件
        const handleOptionChange = () => {
            const hasSelection = this._hasSelection(container, questionData);
            confirmBtn.disabled = questionData.required && !hasSelection;

            // 处理追问
            this._handleFollowUpQuestions(container, questionData);
        };

        optionsContainer.addEventListener('change', handleOptionChange);

        // 文本输入事件
        if (textInput) {
            textInput.addEventListener('input', () => {
                confirmBtn.disabled = questionData.required && !textInput.value.trim();
            });
        }

        // 确认按钮事件
        confirmBtn.addEventListener('click', () => {
            this._submitAnswer(container, questionData);
        });

        // 取消按钮事件
        cancelBtn.addEventListener('click', () => {
            this._cancelAnswer(container, questionData);
        });
    },

    /**
     * 检查是否有选项被选中
     * @param {HTMLElement} container - 对话框容器
     * @param {Object} questionData - 问答数据
     * @returns {boolean} 是否有选中
     */
    _hasSelection(container, questionData) {
        if (questionData.type === 'text') {
            const input = container.querySelector('.question-text-input');
            return input && input.value.trim().length > 0;
        }

        const inputs = container.querySelectorAll('input[name^="question_"]');
        for (const input of inputs) {
            if (input.checked) {
                return true;
            }
        }
        return false;
    },

    /**
     * 获取用户答案
     * @param {HTMLElement} container - 对话框容器
     * @param {Object} questionData - 问答数据
     * @returns {string|array|boolean} 用户答案
     */
    _getAnswer(container, questionData) {
        if (questionData.type === 'text') {
            const input = container.querySelector('.question-text-input');
            return input ? input.value.trim() : '';
        }

        if (questionData.type === 'checkbox') {
            const inputs = container.querySelectorAll('input[name^="question_"]:checked');
            return Array.from(inputs).map(input => input.value);
        }

        if (questionData.type === 'boolean') {
            const input = container.querySelector('input[name^="question_"]:checked');
            return input ? input.value === 'true' : false;
        }

        // multiple_choice
        const input = container.querySelector('input[name^="question_"]:checked');
        return input ? input.value : '';
    },

    /**
     * 处理追问问题
     * @param {HTMLElement} container - 对话框容器
     * @param {Object} questionData - 问答数据
     */
    _handleFollowUpQuestions(container, questionData) {
        const followUpContainer = container.querySelector('.follow-up-questions-container');
        if (!followUpContainer || !questionData.follow_up_questions) {
            return;
        }

        // 获取当前选中的选项
        const selectedOptions = [];
        const inputs = container.querySelectorAll('input[name^="question_"]:checked');
        inputs.forEach(input => selectedOptions.push(input.value));

        // 清空追问容器
        followUpContainer.innerHTML = '';

        // 显示相关追问
        for (const selectedOpt of selectedOptions) {
            const followUps = questionData.follow_up_questions[selectedOpt];
            if (followUps && followUps.length > 0) {
                for (const followUp of followUps) {
                    const followUpEl = this._createFollowUpElement(followUp);
                    followUpContainer.appendChild(followUpEl);
                }
            }
        }
    },

    /**
     * 创建追问元素
     * @param {Object} followUp - 追问数据
     * @returns {HTMLElement} 追问元素
     */
    _createFollowUpElement(followUp) {
        const el = document.createElement('div');
        el.className = 'follow-up-question';
        el.dataset.questionId = followUp.question_id;

        let optionsHtml = '';
        if (followUp.type === 'multiple_choice' || followUp.type === 'checkbox') {
            optionsHtml = this._renderOptions(followUp);
        } else if (followUp.type === 'text') {
            optionsHtml = this._renderTextInput(followUp);
        } else if (followUp.type === 'boolean') {
            optionsHtml = this._renderBooleanInput(followUp);
        }

        el.innerHTML = `
            <div class="follow-up-text">${Utils.escapeHtml(followUp.question_text)}</div>
            <div class="follow-up-options">${optionsHtml}</div>
        `;

        return el;
    },

    /**
     * 提交答案
     * @param {HTMLElement} container - 对话框容器
     * @param {Object} questionData - 问答数据
     */
    async _submitAnswer(container, questionData) {
        const answer = this._getAnswer(container, questionData);

        // 收集追问答案
        const followUpAnswers = {};
        const followUpEls = container.querySelectorAll('.follow-up-question');
        followUpEls.forEach(el => {
            const followUpId = el.dataset.questionId;
            const followUpData = this._findFollowUpData(questionData, followUpId);
            if (followUpData) {
                const followUpAnswer = this._getAnswer(el, followUpData);
                followUpAnswers[followUpId] = followUpAnswer;
            }
        });

        // 发送答案到服务器
        // ========== 前端调试日志 ==========
        console.log('[Answer] ★★★★★ 提交答案 ★★★★★');
        console.log('[Answer] ★ this._sessionId:', this._sessionId);
        console.log('[Answer] ★ questionData:', questionData);
        console.log('[Answer] ★ runner.currentSessionId:', this._runner.currentSessionId);
        console.log('[Answer] ★ 提交的数据:', {
            session_id: this._sessionId,
            question_id: questionData.question_id,
            answer: answer,
            follow_up_answers: followUpAnswers,
        });

        try {
            const response = await fetch('/api/task/answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this._sessionId,
                    question_id: questionData.question_id,
                    answer: answer,
                    follow_up_answers: followUpAnswers,
                }),
            });

            const result = await response.json();
            console.log('[Answer] 响应:', result);

            if (result.success) {
                console.log('[Answer] 提交成功');
                // 禁用对话框，显示已回答状态
                this._disableDialog(container);
                container.classList.add('answered');

                // 更改确认按钮为"处理中..."
                const confirmBtn = container.querySelector('.btn-confirm');
                if (confirmBtn) {
                    confirmBtn.textContent = '处理中...';
                }
            } else {
                console.error('[Answer] 提交失败:', result.message);
                alert('提交失败: ' + result.message);
            }
        } catch (error) {
            console.error('[Answer] 提交答案失败:', error);
            alert('提交失败，请重试');
        }
    },

    /**
     * 查找追问数据
     * @param {Object} questionData - 父问题数据
     * @param {string} followUpId - 追问 ID
     * @returns {Object|null} 追问数据
     */
    _findFollowUpData(questionData, followUpId) {
        if (!questionData.follow_up_questions) {
            return null;
        }

        for (const questions of Object.values(questionData.follow_up_questions)) {
            for (const q of questions) {
                if (q.question_id === followUpId) {
                    return q;
                }
            }
        }
        return null;
    },

    /**
     * 取消答案
     * @param {HTMLElement} container - 对话框容器
     * @param {Object} questionData - 问答数据
     */
    async _cancelAnswer(container, questionData) {
        try {
            await fetch('/api/task/answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this._sessionId,
                    question_id: questionData.question_id,
                    answer: null,  // 表示取消
                }),
            });

            // 禁用对话框
            this._disableDialog(container);
            container.classList.add('cancelled');
        } catch (error) {
            console.error('取消失败:', error);
        }
    },

    /**
     * 禁用对话框
     * @param {HTMLElement} container - 对话框容器
     */
    _disableDialog(container) {
        const inputs = container.querySelectorAll('input, button');
        inputs.forEach(input => input.disabled = true);
        container.classList.add('disabled');
    },

    /**
     * 隐藏对话框
     */
    hide() {
        this._currentQuestion = null;
        this._sessionId = null;
    },
};

// 导出到全局命名空间
window.AskUserQuestionDialog = AskUserQuestionDialog;
