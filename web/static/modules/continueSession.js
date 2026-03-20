/**
 * 继续会话模块
 * 处理会话延续、缓存和状态管理
 */

class ContinueSessionManager {
    /**
     * 初始化继续会话管理器
     * @param {ClaudeCodeRunner} app - 应用实例
     */
    static init(app) {
        this.app = app;
    }

    /**
     * 获取当前工作目录
     * @returns {string} 当前工作目录
     */
    static _getCurrentWorkingDir() {
        // v12: 优先使用 state.workspace，其次使用 workspaceCombo，最后使用 workingDirInput
        return this.app.state?.workspace ||
               this.app.workspaceCombo?.getValue?.() ||
               this.app.workingDirInput?.value ||
               '.';
    }

    /**
     * 获取最近的会话ID
     * @param {string} workingDir - 工作目录（可选，默认使用当前输入的工作目录）
     * @returns {Promise<string|null>} 最近会话ID或null
     */
    static async getLatestSessionId(workingDir = null) {
        try {
            const dir = workingDir || this._getCurrentWorkingDir();
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
     * 生成缓存 key（包含工作目录标识）
     * @param {string} workingDir - 工作目录
     * @returns {string} 缓存 key
     */
    static _getCacheKey(workingDir) {
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
    static getCachedLatestSessionId() {
        try {
            // v12.0.0.6: 使用统一的 _getCurrentWorkingDir() 方法获取工作目录
            const workingDir = this._getCurrentWorkingDir();
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
    static cacheLatestSessionId(sessionId) {
        try {
            // v12.0.0.6: 使用统一的 _getCurrentWorkingDir() 方法获取工作目录
            const workingDir = this._getCurrentWorkingDir();
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
    static async updateContinueConversationState(forceRefresh = false) {
        const workingDir = this._getCurrentWorkingDir();

        // 首先尝试从缓存获取（除非强制刷新）
        let latestSessionId = null;
        if (!forceRefresh) {
            latestSessionId = this.getCachedLatestSessionId();
        }

        // 如果缓存不存在或已过期，从API获取（传递工作目录）
        if (!latestSessionId) {
            latestSessionId = await this.getLatestSessionId(workingDir);
            if (latestSessionId) {
                this.cacheLatestSessionId(latestSessionId);
            }
        }

        // 更新UI状态 - 添加安全检查
        const checkbox = this.app.continueConversationCheckbox;
        const resumeInput = this.app.resumeInput;

        if (!checkbox) {
            console.warn('[继续会话] continueConversationCheckbox 未找到');
            return;
        }

        if (latestSessionId) {
            checkbox.disabled = false;
            checkbox.title = `延续最近会话的对话历史 (${workingDir})`;
            // 如果复选框已勾选，更新resume字段
            if (checkbox.checked && resumeInput) {
                resumeInput.value = latestSessionId;
                resumeInput.title = latestSessionId;
            }
        } else {
            checkbox.disabled = true;
            checkbox.checked = false;
            checkbox.title = `无历史会话可继续 (${workingDir})`;
            if (resumeInput) {
                resumeInput.value = '';
                resumeInput.title = '';
            }
        }
    }

    /**
     * 处理"继续会话"复选框状态变化
     * @param {boolean} checked - 复选框是否勾选
     */
    static async handleContinueConversationChange(checked) {
        const checkbox = this.app.continueConversationCheckbox;
        const resumeInput = this.app.resumeInput;

        if (checked) {
            // 获取当前工作目录
            const workingDir = this._getCurrentWorkingDir();

            // 勾选时，获取最近会话ID并填充 resume 字段
            let latestSessionId = this.getCachedLatestSessionId();
            if (!latestSessionId) {
                // 传递工作目录参数
                latestSessionId = await this.getLatestSessionId(workingDir);
                if (latestSessionId) {
                    this.cacheLatestSessionId(latestSessionId);
                }
            }

            if (latestSessionId) {
                if (resumeInput) {
                    resumeInput.value = latestSessionId;
                    resumeInput.title = latestSessionId;
                }
                console.log('[继续会话] 已勾选，自动填充会话ID:', latestSessionId);
            } else {
                // 没有最近的会话ID，取消勾选并提示
                if (checkbox) {
                    checkbox.checked = false;
                }
                // 安全调用 Task.addMessage
                if (typeof Task !== 'undefined' && Task.addMessage) {
                    Task.addMessage(this.app, 'text', '⚠️ 没有可继续的会话，请先执行一个任务');
                } else {
                    console.warn('[继续会话] 没有可继续的会话，请先执行一个任务');
                }
                if (resumeInput) {
                    resumeInput.value = '';
                    resumeInput.title = '';
                }
            }
        } else {
            // 取消勾选时，清空 resume 字段
            if (resumeInput) {
                resumeInput.value = '';
                resumeInput.title = '';
            }
            console.log('[继续会话] 已取消，清空会话ID');
        }
    }

    /**
     * 处理工作目录变更
     */
    static async handleWorkingDirChange() {
        const newDir = this._getCurrentWorkingDir();
        console.log('[继续会话] 工作目录已变更:', newDir);

        const checkbox = this.app.continueConversationCheckbox;
        const resumeInput = this.app.resumeInput;

        // 清空当前的 resume 值（因为会话可能不在新目录中）
        if (checkbox?.checked) {
            checkbox.checked = false;
            if (resumeInput) {
                resumeInput.value = '';
                resumeInput.title = '';
            }
        }

        // 强制刷新继续会话状态（获取新目录的最近会话）
        await this.updateContinueConversationState(true);
    }

    /**
     * 更新复选框启用状态
     * @param {boolean} enabled - 是否启用复选框
     */
    static updateContinueConversationCheckbox(enabled) {
        const checkbox = this.app.continueConversationCheckbox;
        if (checkbox) {
            checkbox.disabled = !enabled;
            checkbox.title = enabled
                ? '延续最近会话的对话历史'
                : '当前会话模式下不可用';
        }
    }
}

// 导出模块
window.ContinueSessionManager = ContinueSessionManager;
