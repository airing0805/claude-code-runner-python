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
     * 获取最近的会话ID
     * @param {string} workingDir - 工作目录（可选，默认使用当前输入的工作目录）
     * @returns {Promise<string|null>} 最近会话ID或null
     */
    static async getLatestSessionId(workingDir = null) {
        try {
            const dir = workingDir || this.app.workingDirInput?.value || '.';
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
            const workingDir = this.app.workingDirInput?.value || '.';
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
            const workingDir = this.app.workingDirInput?.value || '.';
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
        const workingDir = this.app.workingDirInput?.value || '.';

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

        // 更新UI状态
        if (latestSessionId) {
            this.app.continueConversationCheckbox.disabled = false;
            this.app.continueConversationCheckbox.title = `延续最近会话的对话历史 (${workingDir})`;
            // 如果复选框已勾选，更新resume字段
            if (this.app.continueConversationCheckbox.checked) {
                this.app.resumeInput.value = latestSessionId;
                this.app.resumeInput.title = latestSessionId;
            }
        } else {
            this.app.continueConversationCheckbox.disabled = true;
            this.app.continueConversationCheckbox.checked = false;
            this.app.continueConversationCheckbox.title = `无历史会话可继续 (${workingDir})`;
            this.app.resumeInput.value = '';
            this.app.resumeInput.title = '';
        }
    }

    /**
     * 处理"继续会话"复选框状态变化
     * @param {boolean} checked - 复选框是否勾选
     */
    static async handleContinueConversationChange(checked) {
        if (checked) {
            // 获取当前工作目录
            const workingDir = this.app.workingDirInput?.value || '.';

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
                this.app.resumeInput.value = latestSessionId;
                this.app.resumeInput.title = latestSessionId;
                console.log('[继续会话] 已勾选，自动填充会话ID:', latestSessionId);
            } else {
                // 没有最近的会话ID，取消勾选并提示
                this.app.continueConversationCheckbox.checked = false;
                Task.addMessage(this.app, 'text', '⚠️ 没有可继续的会话，请先执行一个任务');
                this.app.resumeInput.value = '';
                this.app.resumeInput.title = '';
            }
        } else {
            // 取消勾选时，清空 resume 字段
            this.app.resumeInput.value = '';
            this.app.resumeInput.title = '';
            console.log('[继续会话] 已取消，清空会话ID');
        }
    }

    /**
     * 处理工作目录变更
     */
    static async handleWorkingDirChange() {
        const newDir = this.app.workingDirInput?.value || '.';
        console.log('[继续会话] 工作目录已变更:', newDir);

        // 清空当前的 resume 值（因为会话可能不在新目录中）
        if (this.app.continueConversationCheckbox?.checked) {
            this.app.continueConversationCheckbox.checked = false;
            this.app.resumeInput.value = '';
            this.app.resumeInput.title = '';
        }

        // 强制刷新继续会话状态（获取新目录的最近会话）
        await this.updateContinueConversationState(true);
    }

    /**
     * 更新复选框启用状态
     * @param {boolean} enabled - 是否启用复选框
     */
    static updateContinueConversationCheckbox(enabled) {
        if (this.app.continueConversationCheckbox) {
            this.app.continueConversationCheckbox.disabled = !enabled;
            this.app.continueConversationCheckbox.title = enabled
                ? '延续最近会话的对话历史'
                : '当前会话模式下不可用';
        }
    }
}

// 导出模块
window.ContinueSessionManager = ContinueSessionManager;
