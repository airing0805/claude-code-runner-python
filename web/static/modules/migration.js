/**
 * 数据迁移模块
 * 处理 v11 到 v12 的数据格式转换
 *
 * v12.0.0.3.5 - 界面重构
 */

const Migration = {
    // 数据版本标识
    VERSION_V11: 'v11',
    VERSION_V12: 'v12',

    // 存储键名
    KEYS: {
        SESSIONS_V12: 'sessions_v12',
        CURRENT_SESSION_ID_V12: 'currentSessionId_v12',
        WORKSPACE_HISTORY_V12: 'workspaceHistory_v12',
        DATA_VERSION: 'dataVersion_v12',
        // v11 兼容键
        SESSIONS_V11: 'sessions_v11',
        SESSIONS_LEGACY: 'sessions',
        // 备份键前缀
        BACKUP_PREFIX: 'sessions_v11_backup_'
    },

    // 迁移状态
    _isMigrating: false,
    _modalElement: null,

    /**
     * 检测是否需要迁移
     * @returns {boolean}
     */
    needsMigration() {
        const version = this.loadDataVersion();
        return version !== this.VERSION_V12;
    },

    /**
     * 执行迁移
     * @param {Object} runner - ClaudeCodeRunner 实例（可选）
     * @returns {Promise<boolean>} 迁移是否成功
     */
    async runMigration(runner = null) {
        if (!this.needsMigration()) {
            console.log('[Migration] 数据已是 v12 格式，无需迁移');
            return false;
        }

        // 防止重复迁移
        if (this._isMigrating) {
            console.log('[Migration] 迁移正在进行中...');
            return false;
        }

        this._isMigrating = true;
        console.log('[Migration] 开始数据迁移...');

        try {
            // 步骤 1: 显示迁移进度
            this.showMigrationProgress(10, '正在准备数据迁移...');

            // 步骤 2: 读取 v11 数据
            await this._delay(100);
            this.showMigrationProgress(30, '正在读取历史数据...');
            const v11Data = this.loadV11Data();
            console.log('[Migration] 读取到 v11 数据:', v11Data);

            // 步骤 3: 转换数据
            await this._delay(100);
            this.showMigrationProgress(60, '正在转换数据格式...');
            const v12Data = this.convertV11ToV12(v11Data);
            console.log('[Migration] 转换后的 v12 数据:', v12Data);

            // 步骤 4: 验证数据
            await this._delay(100);
            this.showMigrationProgress(75, '正在验证数据完整性...');
            const validationResult = this.validateV12Data(v12Data, v11Data);
            if (!validationResult.valid) {
                console.warn('[Migration] 数据验证警告:', validationResult.warnings);
            }

            // 步骤 5: 保存 v12 数据
            await this._delay(100);
            this.showMigrationProgress(90, '正在保存迁移数据...');
            this.saveV12Data(v12Data);

            // 步骤 6: 备份原数据
            this.backupV11Data(v11Data);

            // 步骤 7: 更新版本标识
            this.saveDataVersion(this.VERSION_V12);

            // 步骤 8: 完成
            this.showMigrationProgress(100, '数据迁移完成！');

            // 延迟隐藏进度条
            await this._delay(1500);
            this.hideMigrationProgress();

            console.log('[Migration] 数据迁移完成');
            this._isMigrating = false;

            return true;

        } catch (error) {
            console.error('[Migration] 迁移失败:', error);
            this._isMigrating = false;

            // 执行回滚
            await this.rollback(error);

            return false;
        }
    },

    /**
     * 延迟函数
     * @param {number} ms - 延迟毫秒数
     * @returns {Promise<void>}
     * @private
     */
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    /**
     * 读取 v11 数据
     * @returns {Object} v11 数据对象
     */
    loadV11Data() {
        // 尝试从 v11 键读取
        const v11Data = localStorage.getItem(this.KEYS.SESSIONS_V11);
        if (v11Data) {
            try {
                return JSON.parse(v11Data);
            } catch (e) {
                console.warn('[Migration] v11 数据解析失败:', e);
            }
        }

        // 尝试从旧键读取
        const legacyData = localStorage.getItem(this.KEYS.SESSIONS_LEGACY);
        if (legacyData) {
            try {
                const parsed = JSON.parse(legacyData);
                // 检查是否为 v11 格式（对象类型，包含 sessions 属性或直接是会话映射）
                if (typeof parsed === 'object' && !Array.isArray(parsed)) {
                    return parsed;
                }
            } catch (e) {
                console.warn('[Migration] 旧数据解析失败:', e);
            }
        }

        // 返回空数据
        return { sessions: {}, activeTab: null };
    },

    /**
     * 验证 v12 数据
     * @param {Object} v12Data - v12 数据
     * @param {Object} v11Data - v11 原始数据（用于对比）
     * @returns {Object} 验证结果 { valid: boolean, warnings: string[] }
     */
    validateV12Data(v12Data, v11Data) {
        const result = {
            valid: true,
            warnings: []
        };

        // 检查会话数量
        const v11SessionCount = Object.keys(v11Data.sessions || {}).filter(key => {
            const session = v11Data.sessions[key];
            return session && session.id;
        }).length;
        const v12SessionCount = v12Data.sessions.length;

        if (v12SessionCount < v11SessionCount) {
            result.warnings.push(`会话数量减少: ${v11SessionCount} -> ${v12SessionCount}（可能是去重）`);
        }

        // 检查会话 ID 唯一性
        const sessionIds = v12Data.sessions.map(s => s.id);
        const uniqueIds = new Set(sessionIds);
        if (uniqueIds.size !== sessionIds.length) {
            result.warnings.push('存在重复的会话 ID');
            result.valid = false;
        }

        // 检查当前会话 ID 是否有效
        if (v12Data.currentSessionId) {
            const currentSessionExists = v12Data.sessions.some(s => s.id === v12Data.currentSessionId);
            if (!currentSessionExists) {
                result.warnings.push('当前会话 ID 不存在于会话列表中');
                // 自动修复：设置为第一个会话
                if (v12Data.sessions.length > 0) {
                    v12Data.currentSessionId = v12Data.sessions[0].id;
                }
            }
        }

        return result;
    },

    /**
     * 转换 v11 数据为 v12 格式
     * @param {Object} v11Data - v11 数据
     * @returns {Object} v12 数据
     */
    convertV11ToV12(v11Data) {
        const v12Data = {
            sessions: [],
            currentSessionId: null,
            workspaceHistory: []
        };

        // 获取会话列表
        const sessions = v11Data.sessions || v11Data;
        const sessionMap = new Map();

        // 遍历并去重
        if (typeof sessions === 'object' && !Array.isArray(sessions)) {
            for (const [key, session] of Object.entries(sessions)) {
                if (!session || !session.id) continue;

                // 去重处理 - 保留最新的版本
                if (sessionMap.has(session.id)) {
                    const existing = sessionMap.get(session.id);
                    if ((session.timestamp || 0) > (existing.timestamp || 0)) {
                        sessionMap.set(session.id, session);
                    }
                } else {
                    sessionMap.set(session.id, session);
                }
            }
        }

        // 转为数组并排序（按时间降序）
        v12Data.sessions = Array.from(sessionMap.values())
            .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

        // 设置当前会话 ID
        const activeTab = v11Data.activeTab;
        if (activeTab && sessions[activeTab]) {
            v12Data.currentSessionId = sessions[activeTab].id;
        } else if (v12Data.sessions.length > 0) {
            // 默认选择第一个会话
            v12Data.currentSessionId = v12Data.sessions[0].id;
        }

        // 构建工作空间历史
        const workspaceSet = new Set();
        v12Data.sessions.forEach(session => {
            const workingDir = session.workingDir || session.working_dir;
            if (workingDir) {
                workspaceSet.add(workingDir);
            }
        });
        v12Data.workspaceHistory = Array.from(workspaceSet).slice(0, 10);

        return v12Data;
    },

    /**
     * 保存 v12 数据
     * @param {Object} v12Data - v12 数据
     */
    saveV12Data(v12Data) {
        try {
            // 保存会话列表
            localStorage.setItem(this.KEYS.SESSIONS_V12, JSON.stringify(v12Data.sessions));

            // 保存当前会话 ID
            if (v12Data.currentSessionId) {
                localStorage.setItem(this.KEYS.CURRENT_SESSION_ID_V12, v12Data.currentSessionId);
            }

            // 保存工作空间历史
            localStorage.setItem(this.KEYS.WORKSPACE_HISTORY_V12, JSON.stringify(v12Data.workspaceHistory));

            console.log('[Migration] v12 数据已保存');
        } catch (e) {
            console.error('[Migration] 保存 v12 数据失败:', e);
            throw new Error('保存数据失败: ' + e.message);
        }
    },

    /**
     * 备份 v11 数据
     * @param {Object} v11Data - v11 数据
     */
    backupV11Data(v11Data) {
        const backupKey = `${this.KEYS.SESSIONS_V11}_backup_${Date.now()}`;
        try {
            localStorage.setItem(backupKey, JSON.stringify(v11Data));
            console.log('[Migration] v11 数据已备份到:', backupKey);
        } catch (e) {
            console.warn('[Migration] 备份 v11 数据失败:', e);
            // 备份失败不应阻止迁移继续
        }
    },

    /**
     * 保存数据版本
     * @param {string} version - 版本标识
     */
    saveDataVersion(version) {
        try {
            localStorage.setItem(this.KEYS.DATA_VERSION, version);
            console.log('[Migration] 数据版本已更新为:', version);
        } catch (e) {
            console.error('[Migration] 保存数据版本失败:', e);
        }
    },

    /**
     * 读取数据版本
     * @returns {string} 版本标识
     */
    loadDataVersion() {
        return localStorage.getItem(this.KEYS.DATA_VERSION) || this.VERSION_V11;
    },

    /**
     * 清理旧数据（谨慎使用）
     * @param {boolean} keepBackup - 是否保留备份
     */
    cleanupOldData(keepBackup = true) {
        console.log('[Migration] 开始清理旧数据...');

        const keysToRemove = [
            this.KEYS.SESSIONS_V11,
            this.KEYS.SESSIONS_LEGACY
        ];

        keysToRemove.forEach(key => {
            try {
                localStorage.removeItem(key);
                console.log('[Migration] 已清理:', key);
            } catch (e) {
                console.warn('[Migration] 清理失败:', key, e);
            }
        });

        // 可选：清理旧备份（保留最近 3 个）
        if (!keepBackup) {
            this._cleanupOldBackups(3);
        }
    },

    /**
     * 清理旧的备份数据
     * @param {number} keepCount - 保留的备份数量
     * @private
     */
    _cleanupOldBackups(keepCount = 3) {
        const backupPrefix = `${this.KEYS.SESSIONS_V11}_backup_`;
        const backups = [];

        // 收集所有备份键
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(backupPrefix)) {
                const timestamp = parseInt(key.split('_backup_')[1], 10);
                if (!isNaN(timestamp)) {
                    backups.push({ key, timestamp });
                }
            }
        }

        // 按时间排序（最新的在前）
        backups.sort((a, b) => b.timestamp - a.timestamp);

        // 删除超出保留数量的备份
        const toRemove = backups.slice(keepCount);
        toRemove.forEach(backup => {
            try {
                localStorage.removeItem(backup.key);
                console.log('[Migration] 已清理旧备份:', backup.key);
            } catch (e) {
                console.warn('[Migration] 清理备份失败:', backup.key, e);
            }
        });
    },

    // ==================== 迁移进度显示 ====================

    /**
     * 显示迁移进度
     * @param {number} progress - 进度百分比 (0-100)
     * @param {string} message - 进度消息
     */
    showMigrationProgress(progress, message) {
        let modal = document.querySelector('.migration-modal');

        if (!modal) {
            modal = this._createMigrationModal();
        }

        const progressBar = modal.querySelector('.progress-fill');
        const progressText = modal.querySelector('.progress-text');
        const messageText = modal.querySelector('.migration-message');

        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        if (progressText) {
            progressText.textContent = `${progress}%`;
        }
        if (messageText) {
            messageText.textContent = message;
        }

        // 确保模态框可见
        modal.style.display = 'flex';
    },

    /**
     * 隐藏迁移进度
     */
    hideMigrationProgress() {
        const modal = document.querySelector('.migration-modal');
        if (modal) {
            modal.style.display = 'none';
            // 可选：移除 DOM 元素
            // modal.remove();
        }
    },

    /**
     * 创建迁移进度模态框
     * @returns {HTMLElement} 模态框元素
     * @private
     */
    _createMigrationModal() {
        const modal = document.createElement('div');
        modal.className = 'migration-modal';
        modal.innerHTML = `
            <div class="migration-content">
                <div class="migration-icon">⏳</div>
                <h3 class="migration-title">数据迁移中...</h3>
                <p class="migration-message">正在准备数据迁移...</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
                <p class="progress-text">0%</p>
                <p class="migration-hint">请勿刷新页面</p>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    },

    // ==================== 错误处理和回滚 ====================

    /**
     * 显示迁移错误
     * @param {Error|string} error - 错误对象或错误消息
     * @param {Function} onRetry - 重试回调（可选）
     * @param {Function} onSkip - 跳过回调（可选）
     */
    showMigrationError(error, onRetry = null, onSkip = null) {
        this.hideMigrationProgress();

        let modal = document.querySelector('.migration-error-modal');

        if (!modal) {
            modal = this._createMigrationErrorModal();
        }

        const errorMessage = modal.querySelector('.error-message');
        const retryBtn = modal.querySelector('.retry-btn');
        const skipBtn = modal.querySelector('.skip-btn');

        if (errorMessage) {
            errorMessage.textContent = error instanceof Error ? error.message : error;
        }

        // 绑定重试按钮
        if (retryBtn && onRetry) {
            retryBtn.onclick = () => {
                modal.style.display = 'none';
                onRetry();
            };
            retryBtn.style.display = 'inline-block';
        } else if (retryBtn) {
            retryBtn.style.display = 'none';
        }

        // 绑定跳过按钮
        if (skipBtn && onSkip) {
            skipBtn.onclick = () => {
                modal.style.display = 'none';
                onSkip();
            };
            skipBtn.style.display = 'inline-block';
        } else if (skipBtn) {
            skipBtn.style.display = 'none';
        }

        modal.style.display = 'flex';
    },

    /**
     * 隐藏迁移错误模态框
     */
    hideMigrationError() {
        const modal = document.querySelector('.migration-error-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    },

    /**
     * 创建迁移错误模态框
     * @returns {HTMLElement} 模态框元素
     * @private
     */
    _createMigrationErrorModal() {
        const modal = document.createElement('div');
        modal.className = 'migration-error-modal';
        modal.innerHTML = `
            <div class="migration-error-content">
                <div class="migration-error-icon">❌</div>
                <h3 class="migration-error-title">数据迁移失败</h3>
                <p class="migration-error-desc">迁移过程中出现错误，已自动恢复到旧版本数据。</p>
                <p class="error-message">未知错误</p>
                <div class="error-actions">
                    <button class="retry-btn">重试</button>
                    <button class="skip-btn">跳过</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    },

    /**
     * 执行回滚
     * @param {Error|string} error - 导致回滚的错误
     * @returns {Promise<void>}
     */
    async rollback(error) {
        console.log('[Migration] 开始执行回滚...');

        try {
            // 查找最新的备份
            const backupKey = this._findLatestBackup();

            if (backupKey) {
                console.log('[Migration] 找到备份:', backupKey);
                const backupData = localStorage.getItem(backupKey);

                if (backupData) {
                    // 恢复备份到 v11 键
                    localStorage.setItem(this.KEYS.SESSIONS_V11, backupData);
                    console.log('[Migration] 已从备份恢复 v11 数据');
                }
            }

            // 清理可能已写入的 v12 数据
            this._cleanupV12Data();

            // 重置版本标识
            this.saveDataVersion(this.VERSION_V11);

            console.log('[Migration] 回滚完成');

        } catch (rollbackError) {
            console.error('[Migration] 回滚过程中出现错误:', rollbackError);
        }

        // 显示错误信息
        this.showMigrationError(error,
            // 重试回调
            () => this.runMigration(),
            // 跳过回调
            () => {
                this.hideMigrationError();
                // 强制设置为 v12，跳过迁移
                this.saveDataVersion(this.VERSION_V12);
                console.log('[Migration] 已跳过迁移，强制设置为 v12');
            }
        );
    },

    /**
     * 查找最新的备份
     * @returns {string|null} 备份键名
     * @private
     */
    _findLatestBackup() {
        const backupPrefix = `${this.KEYS.SESSIONS_V11}_backup_`;
        let latestBackup = null;
        let latestTimestamp = 0;

        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(backupPrefix)) {
                const timestamp = parseInt(key.split('_backup_')[1], 10);
                if (!isNaN(timestamp) && timestamp > latestTimestamp) {
                    latestTimestamp = timestamp;
                    latestBackup = key;
                }
            }
        }

        return latestBackup;
    },

    /**
     * 清理 v12 数据
     * @private
     */
    _cleanupV12Data() {
        const v12Keys = [
            this.KEYS.SESSIONS_V12,
            this.KEYS.CURRENT_SESSION_ID_V12,
            this.KEYS.WORKSPACE_HISTORY_V12
        ];

        v12Keys.forEach(key => {
            try {
                localStorage.removeItem(key);
                console.log('[Migration] 已清理 v12 数据:', key);
            } catch (e) {
                console.warn('[Migration] 清理 v12 数据失败:', key, e);
            }
        });
    },

    // ==================== 公共 API ====================

    /**
     * 获取迁移状态
     * @returns {Object} 迁移状态信息
     */
    getMigrationStatus() {
        return {
            needsMigration: this.needsMigration(),
            currentVersion: this.loadDataVersion(),
            isMigrating: this._isMigrating,
            hasV11Data: this._hasV11Data(),
            hasV12Data: this._hasV12Data()
        };
    },

    /**
     * 检查是否存在 v11 数据
     * @returns {boolean}
     * @private
     */
    _hasV11Data() {
        const v11Data = localStorage.getItem(this.KEYS.SESSIONS_V11);
        const legacyData = localStorage.getItem(this.KEYS.SESSIONS_LEGACY);
        return !!(v11Data || legacyData);
    },

    /**
     * 检查是否存在 v12 数据
     * @returns {boolean}
     * @private
     */
    _hasV12Data() {
        const v12Data = localStorage.getItem(this.KEYS.SESSIONS_V12);
        return !!v12Data;
    },

    /**
     * 手动触发迁移（用于测试或用户手动操作）
     * @returns {Promise<boolean>}
     */
    async forceMigration() {
        // 重置版本标识以触发迁移
        this.saveDataVersion(this.VERSION_V11);
        return this.runMigration();
    }
};

// 导出到全局命名空间
window.Migration = Migration;
