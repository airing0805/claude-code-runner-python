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
     * 存储 runner 实例引用
     */
    _runner: null,

    /**
     * 对话框状态管理
     */
    _dialogStates: new Map(),

    /**
     * 显示问答对话框
     * @param {Object} runner - ClaudeCodeRunner 实例
     * @param {Object} questionData - 问答数据
     * @param {string} sessionId - 会话 ID
     */
    show(runner, questionData, sessionId) {
        // 输入验证
        if (!this._validateQuestionData(questionData)) {
            console.error('[AskUserQuestionDialog] Invalid question data:', questionData);
            return;
        }

        this._currentQuestion = questionData;
        this._sessionId = sessionId;
        this._runner = runner;

        // 创建对话框元素
        const dialogEl = this._createDialogElement(questionData);
        runner.outputEl.appendChild(dialogEl);

        // 初始化状态
        this._initializeDialogState(questionData.question_id, dialogEl);

        // 滚动到底部
        Utils.scrollToBottom(runner.outputEl);

        // 记录日志
        console.log('[AskUserQuestionDialog] Dialog shown:', {
            question_id: questionData.question_id,
            session_id: sessionId,
            type: questionData.type
        });
    },

    /**
     * 验证问题数据
     * @param {Object} questionData - 问题数据
     * @returns {boolean} 是否有效
     */
    _validateQuestionData(questionData) {
        if (!questionData || !questionData.question_id || !questionData.question_text) {
            return false;
        }
        
        // 验证选项
        if (questionData.options && !Array.isArray(questionData.options)) {
            return false;
        }
        
        // 验证类型
        const validTypes = ['multiple_choice', 'checkbox', 'text', 'boolean'];
        if (!validTypes.includes(questionData.type)) {
            return false;
        }
        
        return true;
    },

    /**
     * 初始化对话框状态
     * @param {string} questionId - 问题ID
     * @param {HTMLElement} dialogEl - 对话框元素
     */
    _initializeDialogState(questionId, dialogEl) {
        this._dialogStates.set(questionId, {
            element: dialogEl,
            status: 'showing',
            startTime: Date.now(),
            interactions: 0
        });
    },

    /**
     * 创建对话框 DOM 元素
     * @param {Object} questionData - 问答数据
     * @returns {HTMLElement} 对话框元素
     */
    _createDialogElement(questionData) {
        console.log('[Debug] _createDialogElement called with:', questionData);
        
        const container = document.createElement('div');
        container.className = 'assistant-msg assistant-msg-ask_user_question';
        container.dataset.questionId = questionData.question_id;
        container.dataset.createdAt = Date.now();

        const header = questionData.header || '请确认';
        const description = questionData.description || '';

        let optionsHtml = '';
        console.log('[Debug] Question type:', questionData.type);
        
        if (questionData.type === 'multiple_choice' || questionData.type === 'checkbox') {
            console.log('[Debug] Rendering multiple choice/checkbox options');
            optionsHtml = this._renderOptions(questionData);
        } else if (questionData.type === 'text') {
            console.log('[Debug] Rendering text input');
            optionsHtml = this._renderTextInput(questionData);
        } else if (questionData.type === 'boolean') {
            console.log('[Debug] Rendering boolean input');
            optionsHtml = this._renderBooleanInput(questionData);
        } else {
            console.log('[Debug] Unknown question type, rendering as text');
            optionsHtml = `<div class="unknown-type">未知问题类型: ${questionData.type}</div>`;
        }

        console.log('[Debug] Generated options HTML:', optionsHtml);

        // 添加进度指示器
        const progressHtml = this._renderProgressIndicator(questionData);

        container.innerHTML = `
            <div class="question-header">
                <span class="question-icon">💬</span>
                <span class="question-title">${Utils.escapeHtml(header)}</span>
                ${progressHtml}
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
            <div class="question-timer" data-timeout="${questionData.timeout_seconds || 300}"></div>
        `;

        // 启动倒计时
        this._startTimer(container, questionData);

        // 绑定事件
        this._bindEvents(container, questionData);

        // 验证DOM结构
        const optionsContainer = container.querySelector('.question-options');
        console.log('[Debug] Options container found:', !!optionsContainer);
        if (optionsContainer) {
            console.log('[Debug] Options container HTML:', optionsContainer.innerHTML);
        }

        return container;
    },

    /**
     * 渲染进度指示器
     * @param {Object} questionData - 问题数据
     * @returns {string} 进度HTML
     */
    _renderProgressIndicator(questionData) {
        if (questionData.multi_select && questionData.max_selections) {
            return `<span class="question-progress">最多选择 ${questionData.max_selections} 项</span>`;
        }
        return '';
    },

    /**
     * 启动倒计时
     * @param {HTMLElement} container - 容器元素
     * @param {Object} questionData - 问题数据
     */
    _startTimer(container, questionData) {
        const timerEl = container.querySelector('.question-timer');
        if (!timerEl || !questionData.timeout_seconds) return;

        let remaining = questionData.timeout_seconds;
        const updateTimer = () => {
            const minutes = Math.floor(remaining / 60);
            const seconds = remaining % 60;
            timerEl.textContent = `剩余时间: ${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            if (remaining <= 0) {
                this._handleTimeout(container, questionData);
                return;
            }
            
            remaining--;
        };

        updateTimer();
        const interval = setInterval(updateTimer, 1000);
        
        // 存储interval ID以便清理
        container.dataset.timerInterval = interval;
    },

    /**
     * 处理超时
     * @param {HTMLElement} container - 容器元素
     * @param {Object} questionData - 问题数据
     */
    _handleTimeout(container, questionData) {
        console.log('[AskUserQuestionDialog] Question timed out:', questionData.question_id);
        
        // 禁用所有交互
        this._disableDialog(container);
        container.classList.add('timed-out');
        
        // 更新按钮状态
        const confirmBtn = container.querySelector('.btn-confirm');
        if (confirmBtn) {
            confirmBtn.textContent = '已超时';
            confirmBtn.disabled = true;
        }
        
        // 可选：自动提交空答案
        // this._submitAnswer(container, questionData, null);
    },

    /**
     * 渲染选项
     * @param {Object} questionData - 问答数据
     * @returns {string} 选项 HTML
     */
    _renderOptions(questionData) {
        const isCheckbox = questionData.type === 'checkbox';
        const options = questionData.options || [];

        console.log('[Debug] _renderOptions called with:', questionData);
        console.log('[Debug] Options array:', options);

        if (options.length === 0) {
            return '<div class="no-options">暂无选项</div>';
        }

        const optionsHtml = options.map((opt, index) => {
            // 确保选项有id字段，如果没有则使用索引
            const optionId = opt.id || opt.value || `option_${index}`;
            console.log('[Debug] Rendering option:', opt);

            return `
                <label class="option-item ${isCheckbox ? 'checkbox' : 'radio'}" data-option-id="${optionId}">
                    <input
                        type="${isCheckbox ? 'checkbox' : 'radio'}"
                        name="question_${questionData.question_id}"
                        value="${Utils.escapeHtml(optionId)}"
                        ${opt.default ? 'checked' : ''}
                        data-option-index="${index}"
                    >
                    <span class="option-label">${Utils.escapeHtml(opt.label || opt.text || '未知选项')}</span>
                    ${opt.description ? `<span class="option-description">${Utils.escapeHtml(opt.description)}</span>` : ''}
                </label>
            `;
        }).join('');

        // 添加"其他"选项（允许用户输入自定义文字）
        const otherOptionHtml = `
            <label class="option-item radio" data-option-id="other">
                <input
                    type="radio"
                    name="question_${questionData.question_id}"
                    value="other"
                    data-option-index="-1"
                >
                <span class="option-label">其他</span>
            </label>
            <div class="other-input-container" style="display: none; margin-top: 8px; margin-left: 24px;">
                <textarea
                    class="question-other-input"
                    placeholder="请输入其他内容..."
                    data-question-id="${questionData.question_id}"
                    maxlength="500"
                    rows="2"
                ></textarea>
            </div>
        `;

        return optionsHtml + otherOptionHtml;
    },

    /**
     * 渲染文本输入框
     * @param {Object} questionData - 问答数据
     * @returns {string} 输入框 HTML
     */
    _renderTextInput(questionData) {
        const maxLength = questionData.max_length || 1000;
        return `
            <div class="text-input-container">
                <textarea
                    class="question-text-input"
                    placeholder="请输入..."
                    data-question-id="${questionData.question_id}"
                    maxlength="${maxLength}"
                ></textarea>
                <div class="input-counter">
                    <span class="char-count">0</span>/${maxLength}
                </div>
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
        const otherInputContainer = container.querySelector('.other-input-container');
        const otherRadio = container.querySelector('input[name^="question_"][value="other"]');
        const otherInput = container.querySelector('.question-other-input');

        console.log('[Debug] _bindEvents called with questionData:', questionData);
        console.log('[Debug] Found options container:', optionsContainer);
        console.log('[Debug] Found confirm button:', confirmBtn);

        // 选项变更事件
        const handleOptionChange = () => {
            console.log('[Debug] Option changed triggered');
            const hasSelection = this._hasSelection(container, questionData);
            const isValid = this._validateSelection(container, questionData);

            console.log('[Debug] hasSelection:', hasSelection, 'isValid:', isValid);
            console.log('[Debug] questionData.required:', questionData.required);

            // 处理"其他"选项的显示/隐藏
            if (otherInputContainer && otherRadio) {
                if (otherRadio.checked) {
                    otherInputContainer.style.display = 'block';
                    otherRadio.closest('.option-item').classList.add('other-selected');
                } else {
                    otherInputContainer.style.display = 'none';
                    otherRadio.closest('.option-item').classList.remove('other-selected');
                    // 清空其他输入
                    if (otherInput) otherInput.value = '';
                }
            }

            // 检查是否选择了"其他"选项且有输入内容
            const otherSelected = otherRadio && otherRadio.checked;
            const otherHasContent = otherInput && otherInput.value.trim().length > 0;
            const hasOtherContent = otherSelected && otherHasContent;

            if (confirmBtn) {
                // 如果有"其他"内容，也视为有效选择
                const effectiveSelection = hasSelection || hasOtherContent;
                const effectiveValid = isValid || hasOtherContent;
                confirmBtn.disabled = questionData.required && (!effectiveSelection || !effectiveValid);
                console.log('[Debug] Confirm button disabled:', confirmBtn.disabled, 'hasOtherContent:', hasOtherContent);
            }

            this._updateDialogState(questionData.question_id, 'interacting');

            // 处理追问
            this._handleFollowUpQuestions(container, questionData);
        };

        // 为每个选项单独绑定事件
        if (optionsContainer) {
            const inputs = optionsContainer.querySelectorAll('input[type="radio"], input[type="checkbox"]');
            console.log('[Debug] Found inputs:', inputs.length);
            
            inputs.forEach(input => {
                input.addEventListener('change', handleOptionChange);
            });
            
            // 也监听容器的change事件作为后备
            optionsContainer.addEventListener('change', handleOptionChange);
        }

        // 文本输入事件
        if (textInput) {
            const counter = container.querySelector('.char-count');
            textInput.addEventListener('input', (e) => {
                // 更新字符计数
                if (counter) {
                    counter.textContent = e.target.value.length;
                }

                const hasContent = e.target.value.trim().length > 0;
                const isValidLength = e.target.value.length <= (questionData.max_length || 1000);
                if (confirmBtn) {
                    confirmBtn.disabled = questionData.required && (!hasContent || !isValidLength);
                }

                this._updateDialogState(questionData.question_id, 'typing');
            });
        }

        // "其他"输入框事件
        if (otherInput) {
            otherInput.addEventListener('input', (e) => {
                const hasContent = e.target.value.trim().length > 0;
                if (confirmBtn) {
                    // 选择"其他"时必须有输入内容才能确认
                    const otherRadio = container.querySelector('input[name^="question_"][value="other"]');
                    const otherSelected = otherRadio && otherRadio.checked;
                    confirmBtn.disabled = questionData.required && (!otherSelected || !hasContent);
                }
                this._updateDialogState(questionData.question_id, 'typing');
            });
        }

        // 确认按钮事件
        if (confirmBtn) {
            confirmBtn.addEventListener('click', async () => {
                this._updateDialogState(questionData.question_id, 'submitting');
                await this._submitAnswer(container, questionData);
            });
        }

        // 取消按钮事件
        if (cancelBtn) {
            cancelBtn.addEventListener('click', async () => {
                this._updateDialogState(questionData.question_id, 'cancelled');
                await this._cancelAnswer(container, questionData);
            });
        }

        // ESC键取消
        container.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this._cancelAnswer(container, questionData);
            }
        });
    },

    /**
     * 验证选择是否符合要求
     * @param {HTMLElement} container - 对话框容器
     * @param {Object} questionData - 问答数据
     * @returns {boolean} 是否有效
     */
    _validateSelection(container, questionData) {
        if (questionData.type === 'checkbox' && questionData.multi_select) {
            const selected = container.querySelectorAll('input[name^="question_"]:checked');
            const count = selected.length;
            
            // 检查最小选择数
            if (count < (questionData.min_selections || 0)) {
                return false;
            }
            
            // 检查最大选择数
            if (questionData.max_selections && count > questionData.max_selections) {
                return false;
            }
        }
        return true;
    },

    /**
     * 检查是否有选项被选中
     * @param {HTMLElement} container - 对话框容器
     * @param {Object} questionData - 问答数据
     * @returns {boolean} 是否有选中
     */
    _hasSelection(container, questionData) {
        console.log('[Debug] _hasSelection checking for type:', questionData.type);
        
        if (questionData.type === 'text') {
            const input = container.querySelector('.question-text-input');
            const result = input && input.value.trim().length > 0;
            console.log('[Debug] Text input value:', input ? input.value : 'not found', 'result:', result);
            return result;
        }

        // 检查单选或多选按钮
        const inputs = container.querySelectorAll(`input[name="question_${questionData.question_id}"]`);
        console.log('[Debug] Found inputs for question:', questionData.question_id, 'count:', inputs.length);
        
        for (const input of inputs) {
            if (input.checked) {
                console.log('[Debug] Found checked input with value:', input.value);
                return true;
            }
        }
        
        console.log('[Debug] No checked inputs found');
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
            // 返回选项的 value（ID），而不是 label
            return Array.from(inputs).map(input => input.value);
        }

        if (questionData.type === 'boolean') {
            const input = container.querySelector('input[name^="question_"]:checked');
            return input ? input.value === 'true' : false;
        }

        // multiple_choice - 检查是否选择了"其他"选项
        const otherRadio = container.querySelector('input[name^="question_"][value="other"]');
        if (otherRadio && otherRadio.checked) {
            const otherInput = container.querySelector('.question-other-input');
            if (otherInput && otherInput.value.trim()) {
                return otherInput.value.trim();
            }
        }

        // 普通选项 - 返回选项的 label 而不是 ID，让 SDK 能理解用户的选择
        const input = container.querySelector('input[name^="question_"]:checked');
        if (input) {
            // 查找对应选项的 label
            const optionId = input.value;
            const option = questionData.options?.find(opt => opt.id === optionId);
            if (option && option.label) {
                return option.label;
            }
            // 如果找不到 label，回退到 value
            return input.value;
        }
        return '';
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
            <div class="follow-up-header">
                <span class="follow-up-icon">↪️</span>
                <span class="follow-up-title">${Utils.escapeHtml(followUp.header || '追问')}</span>
            </div>
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
        console.log('[Answer] ★ 用户选择的答案:', answer);
        console.log('[Answer] ★ 提交的数据:', {
            session_id: this._sessionId,
            question_id: questionData.question_id,
            answer: answer,
            follow_up_answers: followUpAnswers,
            raw_question_data: questionData.raw_question_data,  // 原始问题数据
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
                    raw_question_data: questionData.raw_question_data,  // 原始问题数据
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
        const inputs = container.querySelectorAll('input, button, textarea');
        inputs.forEach(input => {
            input.disabled = true;
        });
        container.classList.add('disabled');
        
        // 清理定时器
        const interval = container.dataset.timerInterval;
        if (interval) {
            clearInterval(parseInt(interval));
            delete container.dataset.timerInterval;
        }
    },

    /**
     * 启用对话框
     * @param {HTMLElement} container - 对话框容器
     */
    _enableDialog(container) {
        const inputs = container.querySelectorAll('input, button, textarea');
        inputs.forEach(input => {
            input.disabled = false;
        });
        container.classList.remove('disabled');
    },

    /**
     * 标记为已回答
     * @param {HTMLElement} container - 对话框容器
     */
    _markAsAnswered(container) {
        container.classList.add('answered');
        const confirmBtn = container.querySelector('.btn-confirm');
        if (confirmBtn) {
            confirmBtn.textContent = '已回答';
        }
    },

    /**
     * 更新对话框状态
     * @param {string} questionId - 问题ID
     * @param {string} status - 状态
     */
    _updateDialogState(questionId, status) {
        const state = this._dialogStates.get(questionId);
        if (state) {
            state.status = status;
            state.interactions++;
            console.log(`[Dialog State] ${questionId} -> ${status}`);
        }
    },

    /**
     * 隐藏对话框
     */
    hide() {
        this._currentQuestion = null;
        this._sessionId = null;
        this._runner = null;
        this._dialogStates.clear();
    },

    /**
     * 获取对话框状态
     * @param {string} questionId - 问题ID
     * @returns {Object|null} 状态对象
     */
    getDialogState(questionId) {
        return this._dialogStates.get(questionId) || null;
    }
};

// 导出到全局命名空间
window.AskUserQuestionDialog = AskUserQuestionDialog;
