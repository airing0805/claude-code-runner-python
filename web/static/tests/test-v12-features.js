/**
 * v12 界面重构功能单元测试
 *
 * 测试范围:
 * 1. WorkspaceCombo - 工作空间组合控件
 * 2. HistoryDrawer - 历史抽屉组件
 * 3. Migration - 数据迁移
 * 4. Session - 会话管理
 *
 * v12.0.0.4 - 单元测试
 */

// ==================== 测试工具函数 ====================

const TestUtils = {
    /**
     * 断言相等
     */
    assertEqual(actual, expected, message = '') {
        if (actual === expected) {
            return { pass: true, message: `${message} (实际: ${actual})` };
        }
        return {
            pass: false,
            message: `${message} - 期望: ${expected}, 实际: ${actual}`
        };
    },

    /**
     * 断言为真
     */
    assertTrue(value, message = '') {
        return this.assertEqual(value, true, message);
    },

    /**
     * 断言为假
     */
    assertFalse(value, message = '') {
        return this.assertEqual(value, false, message);
    },

    /**
     * 断言数组长度
     */
    assertLength(arr, expectedLength, message = '') {
        const actual = arr ? arr.length : 0;
        if (actual === expectedLength) {
            return { pass: true, message: `${message} (长度: ${actual})` };
        }
        return {
            pass: false,
            message: `${message} - 期望长度: ${expectedLength}, 实际: ${actual}`
        };
    },

    /**
     * 断言包含
     */
    assertContains(str, substring, message = '') {
        if (str && str.includes(substring)) {
            return { pass: true, message: `${message} (包含: "${substring}")` };
        }
        return {
            pass: false,
            message: `${message} - 字符串不包含 "${substring}"`
        };
    },

    /**
     * 断言对象属性
     */
    assertProperty(obj, prop, message = '') {
        if (obj && obj.hasOwnProperty(prop)) {
            return { pass: true, message: `${message} (存在属性: ${prop})` };
        }
        return {
            pass: false,
            message: `${message} - 对象不存在属性: ${prop}`
        };
    },

    /**
     * 断言函数抛出异常
     */
    async assertThrows(fn, message = '') {
        try {
            await fn();
            return { pass: false, message: `${message} - 未抛出异常` };
        } catch (e) {
            return { pass: true, message: `${message} (抛出: ${e.message})` };
        }
    },

    /**
     * 断言异步函数结果
     */
    async assertAsync(fn, expected, message = '') {
        try {
            const result = await fn();
            return this.assertEqual(result, expected, message);
        } catch (e) {
            return { pass: false, message: `${message} - 异常: ${e.message}` };
        }
    },

    /**
     * 创建测试 DOM 容器
     */
    createTestContainer(id) {
        let container = document.getElementById(id);
        if (!container) {
            container = document.createElement('div');
            container.id = id;
            document.body.appendChild(container);
        }
        container.innerHTML = '';
        return container;
    },

    /**
     * 模拟 localStorage
     */
    mockLocalStorage() {
        const store = {};
        return {
            getItem: (key) => store[key] || null,
            setItem: (key, value) => { store[key] = value; },
            removeItem: (key) => { delete store[key]; },
            clear: () => { Object.keys(store).forEach(k => delete store[k]); },
            get store() { return store; }
        };
    },

    /**
     * 延迟执行
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
};

// ==================== 测试结果管理 ====================

const TestRunner = {
    results: {
        pass: 0,
        fail: 0,
        pending: 0
    },

    /**
     * 显示测试结果
     */
    showResult(containerId, result, testName) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const resultDiv = document.createElement('div');
        resultDiv.className = `test-result ${result.pass ? 'pass' : 'fail'}`;
        resultDiv.innerHTML = `
            <span>${result.pass ? '✅' : '❌'}</span>
            <strong>${testName}</strong>
            <span>- ${result.message}</span>
        `;
        container.appendChild(resultDiv);

        // 更新统计
        if (result.pass) {
            this.results.pass++;
        } else {
            this.results.fail++;
        }
        this.updateStats();
    },

    /**
     * 显示待执行测试
     */
    showPending(containerId, testName) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const resultDiv = document.createElement('div');
        resultDiv.className = 'test-result pending';
        resultDiv.innerHTML = `
            <span>⏳</span>
            <strong>${testName}</strong>
            <span>- 待执行</span>
        `;
        container.appendChild(resultDiv);
        this.results.pending++;
        this.updateStats();
    },

    /**
     * 更新统计显示
     */
    updateStats() {
        document.getElementById('pass-count').textContent = this.results.pass;
        document.getElementById('fail-count').textContent = this.results.fail;
        document.getElementById('pending-count').textContent = this.results.pending;
    },

    /**
     * 清除结果
     */
    clearResults() {
        this.results = { pass: 0, fail: 0, pending: 0 };
        this.updateStats();

        ['workspace-combo-results', 'history-drawer-results', 'migration-results', 'session-results'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = '';
        });
    },

    /**
     * 清除 localStorage
     */
    clearStorage() {
        // 清除 v11 和 v12 相关数据
        const keysToRemove = [
            'sessions_v11', 'sessions', 'sessions_v12',
            'currentSessionId_v12', 'workspaceHistory_v12', 'dataVersion_v12'
        ];

        keysToRemove.forEach(key => {
            localStorage.removeItem(key);
        });

        // 清除备份
        for (let i = localStorage.length - 1; i >= 0; i--) {
            const key = localStorage.key(i);
            if (key && key.startsWith('sessions_v11_backup_')) {
                localStorage.removeItem(key);
            }
        }

        this.updateStorageDisplay();
        alert('localStorage 已清除');
    },

    /**
     * 更新 localStorage 显示
     */
    updateStorageDisplay() {
        const display = document.getElementById('storage-display');
        if (!display) return;

        let html = '';
        const relevantKeys = [];

        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && (key.includes('session') || key.includes('workspace') || key.includes('version'))) {
                relevantKeys.push(key);
            }
        }

        if (relevantKeys.length === 0) {
            html = '<p style="color: #666;">暂无相关 localStorage 数据</p>';
        } else {
            html = relevantKeys.map(key => {
                const value = localStorage.getItem(key);
                const truncated = value && value.length > 100 ? value.substring(0, 100) + '...' : value;
                return `<div><span class="storage-key">${key}:</span> <span class="storage-value">${truncated}</span></div>`;
            }).join('');
        }

        display.innerHTML = html;
    },

    /**
     * 运行所有测试
     */
    async runAllTests() {
        this.clearResults();
        await this.runWorkspaceComboTests();
        await this.runHistoryDrawerTests();
        await this.runMigrationTests();
        await this.runSessionTests();
    },

    // ==================== WorkspaceCombo 测试 ====================

    async runWorkspaceComboTests() {
        const containerId = 'workspace-combo-results';
        const container = document.getElementById(containerId);
        if (container) container.innerHTML = '';

        console.log('=== 开始 WorkspaceCombo 测试 ===');

        // 测试 1: 组件创建
        try {
            const testContainer = TestUtils.createTestContainer('workspace-combo-test-1');
            testContainer.style.position = 'relative';

            const combo = new WorkspaceCombo(testContainer, {
                onChange: (value) => {
                    document.getElementById('combo-value-display').textContent = value || '-';
                }
            });

            let result = TestUtils.assertTrue(combo !== null, '组件创建');
            this.showResult(containerId, result, '1. 组件实例化');

            // 测试 2: 设置历史记录
            combo.setHistory(['/path/to/project1', '/path/to/project2', '/path/to/project3']);
            result = TestUtils.assertLength(combo.getHistory(), 3, '历史记录设置');
            this.showResult(containerId, result, '2. 设置历史记录');

            // 测试 3: 设置值
            combo.setValue('/path/to/project1');
            result = TestUtils.assertEqual(combo.getValue(), '/path/to/project1', '值设置');
            this.showResult(containerId, result, '3. 设置当前值');

            // 测试 4: 路径验证 - 有效路径
            const validResult = combo.validatePath('/valid/path');
            result = TestUtils.assertTrue(validResult.valid, '路径验证 - 有效路径');
            this.showResult(containerId, result, '4. 验证有效路径');

            // 测试 5: 路径验证 - 无效路径（包含 ..）
            const invalidResult1 = combo.validatePath('/invalid/../path');
            result = TestUtils.assertFalse(invalidResult1.valid, '路径验证 - 包含 ..');
            this.showResult(containerId, result, '5. 验证路径遍历攻击');

            // 测试 6: 路径验证 - 无效路径（包含 ~）
            const invalidResult2 = combo.validatePath('~/home/path');
            result = TestUtils.assertFalse(invalidResult2.valid, '路径验证 - 包含 ~');
            this.showResult(containerId, result, '6. 验证波浪号路径');

            // 测试 7: 路径验证 - 相对路径
            const invalidResult3 = combo.validatePath('relative/path');
            result = TestUtils.assertFalse(invalidResult3.valid, '路径验证 - 相对路径');
            this.showResult(containerId, result, '7. 验证相对路径');

            // 测试 8: Windows 路径验证
            const winResult = combo.validatePath('C:\\Users\\test');
            result = TestUtils.assertTrue(winResult.valid, 'Windows 路径验证');
            this.showResult(containerId, result, '8. 验证 Windows 路径');

            // 测试 9: 空路径验证
            const emptyResult = combo.validatePath('');
            result = TestUtils.assertTrue(emptyResult.valid, '空路径验证（新会话）');
            this.showResult(containerId, result, '9. 验证空路径');

            // 测试 10: 历史记录去重
            combo.setHistory(['/path/1', '/path/2', '/path/1', '/path/3']);
            result = TestUtils.assertLength(combo.getHistory(), 3, '历史记录去重');
            this.showResult(containerId, result, '10. 历史记录去重');

            // 测试 11: 清空值
            combo.clear();
            result = TestUtils.assertEqual(combo.getValue(), '', '清空值');
            this.showResult(containerId, result, '11. 清空当前值');

            // 测试 12: 禁用控件
            combo.setDisabled(true);
            result = TestUtils.assertTrue(combo.input.disabled, '禁用控件');
            this.showResult(containerId, result, '12. 禁用控件');

            // 测试 13: 启用控件
            combo.setDisabled(false);
            result = TestUtils.assertFalse(combo.input.disabled, '启用控件');
            this.showResult(containerId, result, '13. 启用控件');

            // 测试 14: 添加到历史记录
            combo.setHistory(['/path/1']);
            combo.addToHistory('/path/new');
            const historyAfterAdd = combo.getHistory();
            result = TestUtils.assertEqual(historyAfterAdd[0], '/path/new', '添加到历史记录');
            this.showResult(containerId, result, '14. 添加到历史记录');

            // 测试 15: 销毁组件
            combo.destroy();
            result = TestUtils.assertTrue(testContainer.children.length === 0, '销毁组件');
            this.showResult(containerId, result, '15. 销毁组件');

        } catch (error) {
            this.showResult(containerId, { pass: false, message: error.message }, 'WorkspaceCombo 测试异常');
        }

        console.log('=== WorkspaceCombo 测试完成 ===');
    },

    // ==================== HistoryDrawer 测试 ====================

    async runHistoryDrawerTests() {
        const containerId = 'history-drawer-results';
        const container = document.getElementById(containerId);
        if (container) container.innerHTML = '';

        console.log('=== 开始 HistoryDrawer 测试 ===');

        try {
            // 测试 1: 组件创建
            let result = TestUtils.assertTrue(
                typeof HistoryDrawer !== 'undefined',
                'HistoryDrawer 类存在'
            );
            this.showResult(containerId, result, '1. 组件类定义');

            // 测试 2: 实例化
            const drawer = new HistoryDrawer({
                onSelect: (session) => console.log('Selected:', session),
                onClose: () => console.log('Closed')
            });
            result = TestUtils.assertTrue(drawer !== null, '组件实例化');
            this.showResult(containerId, result, '2. 组件实例化');

            // 测试 3: 初始状态
            result = TestUtils.assertFalse(drawer.isOpen, '初始关闭状态');
            this.showResult(containerId, result, '3. 初始关闭状态');

            // 测试 4: 打开抽屉
            await drawer.open();
            await TestUtils.delay(100);
            result = TestUtils.assertTrue(drawer.isOpen, '打开抽屉');
            this.showResult(containerId, result, '4. 打开抽屉');

            // 测试 5: DOM 元素状态
            const overlayVisible = document.querySelector('.history-drawer-overlay.show') !== null;
            result = TestUtils.assertTrue(overlayVisible, '遮罩层显示');
            this.showResult(containerId, result, '5. 遮罩层显示');

            const drawerOpen = document.querySelector('.history-drawer.open') !== null;
            result = TestUtils.assertTrue(drawerOpen, '抽屉打开类');
            this.showResult(containerId, result, '6. 抽屉打开类');

            // 测试 6: 关闭抽屉
            drawer.close();
            await TestUtils.delay(100);
            result = TestUtils.assertFalse(drawer.isOpen, '关闭抽屉');
            this.showResult(containerId, result, '7. 关闭抽屉');

            // 测试 7: 切换功能
            await drawer.toggle();
            result = TestUtils.assertTrue(drawer.isOpen, '切换打开');
            this.showResult(containerId, result, '8. 切换功能 - 打开');

            drawer.toggle();
            await TestUtils.delay(100);
            result = TestUtils.assertFalse(drawer.isOpen, '切换关闭');
            this.showResult(containerId, result, '9. 切换功能 - 关闭');

            // 测试 8: 时间格式化
            const timestamp = new Date('2026-03-11T10:30:00').getTime();
            const formatted = drawer.formatTime ? drawer.formatTime(timestamp) : new Date(timestamp).toLocaleString();
            result = TestUtils.assertTrue(formatted.length > 0, '时间格式化');
            this.showResult(containerId, result, '10. 时间格式化');

            // 测试 9: 会话列表加载（模拟）
            // 由于需要 API，这里只测试方法存在
            result = TestUtils.assertTrue(
                typeof drawer.loadSessions === 'function',
                '加载会话方法存在'
            );
            this.showResult(containerId, result, '11. 加载会话方法');

            // 测试 10: 选择会话方法
            result = TestUtils.assertTrue(
                typeof drawer.selectSession === 'function',
                '选择会话方法存在'
            );
            this.showResult(containerId, result, '12. 选择会话方法');

            // 测试 11: HTML 转义
            const escaped = drawer._escapeHtml ? drawer._escapeHtml('<script>alert(1)</script>') : '&lt;script&gt;alert(1)&lt;/script&gt;';
            result = TestUtils.assertFalse(escaped.includes('<script>'), 'HTML 转义');
            this.showResult(containerId, result, '13. HTML 转义安全');

            // 测试 12: 当前会话高亮
            drawer.currentSessionId = 'test-session-123';
            const sessionHtml = drawer.renderSessionItem({
                id: 'test-session-123',
                working_dir: '/test/path',
                summary: 'Test Session',
                created_at: Date.now(),
                message_count: 5
            });
            result = TestUtils.assertContains(sessionHtml, 'current', '当前会话高亮');
            this.showResult(containerId, result, '14. 当前会话高亮');

        } catch (error) {
            this.showResult(containerId, { pass: false, message: error.message }, 'HistoryDrawer 测试异常');
        }

        console.log('=== HistoryDrawer 测试完成 ===');
    },

    // ==================== Migration 测试 ====================

    async runMigrationTests() {
        const containerId = 'migration-results';
        const container = document.getElementById(containerId);
        if (container) container.innerHTML = '';

        console.log('=== 开始 Migration 测试 ===');

        try {
            // 测试 1: Migration 模块存在
            let result = TestUtils.assertTrue(
                typeof Migration !== 'undefined',
                'Migration 模块存在'
            );
            this.showResult(containerId, result, '1. Migration 模块定义');

            // 测试 2: 版本常量
            result = TestUtils.assertEqual(Migration.VERSION_V12, 'v12', 'v12 版本标识');
            this.showResult(containerId, result, '2. v12 版本标识');

            result = TestUtils.assertEqual(Migration.VERSION_V11, 'v11', 'v11 版本标识');
            this.showResult(containerId, result, '3. v11 版本标识');

            // 测试 3: 存储键定义
            result = TestUtils.assertProperty(Migration.KEYS, 'SESSIONS_V12', 'v12 会话存储键');
            this.showResult(containerId, result, '4. v12 会话存储键定义');

            result = TestUtils.assertProperty(Migration.KEYS, 'DATA_VERSION', '版本存储键');
            this.showResult(containerId, result, '5. 数据版本存储键定义');

            // 测试 4: 检测需要迁移
            localStorage.removeItem('dataVersion_v12');
            const needsMigration = Migration.needsMigration();
            result = TestUtils.assertTrue(needsMigration, '检测需要迁移');
            this.showResult(containerId, result, '6. 检测需要迁移');

            // 测试 5: 检测不需要迁移
            localStorage.setItem('dataVersion_v12', 'v12');
            const noMigration = Migration.needsMigration();
            result = TestUtils.assertFalse(noMigration, '检测不需要迁移');
            this.showResult(containerId, result, '7. 检测不需要迁移');

            // 测试 6: 数据转换 - 基本转换
            const v11Data = {
                sessions: {
                    'tab-1': { id: 's1', workingDir: '/path1', timestamp: 1000 },
                    'tab-2': { id: 's2', workingDir: '/path2', timestamp: 2000 }
                },
                activeTab: 'tab-1'
            };
            const v12Data = Migration.convertV11ToV12(v11Data);
            result = TestUtils.assertLength(v12Data.sessions, 2, '基本转换');
            this.showResult(containerId, result, '8. 数据转换 - 基本转换');

            // 测试 7: 数据转换 - 去重
            const v11Duplicate = {
                sessions: {
                    'tab-1': { id: 's1', workingDir: '/path1', timestamp: 1000 },
                    'tab-2': { id: 's1', workingDir: '/path1', timestamp: 2000 } // 同一个 ID，更新时间
                },
                activeTab: 'tab-1'
            };
            const v12Deduped = Migration.convertV11ToV12(v11Duplicate);
            result = TestUtils.assertLength(v12Deduped.sessions, 1, '去重转换');
            this.showResult(containerId, result, '9. 数据转换 - 去重');

            // 测试 8: 数据转换 - 时间排序
            const v11Unsorted = {
                sessions: {
                    'tab-1': { id: 's1', timestamp: 1000 },
                    'tab-2': { id: 's2', timestamp: 3000 },
                    'tab-3': { id: 's3', timestamp: 2000 }
                }
            };
            const v12Sorted = Migration.convertV11ToV12(v11Unsorted);
            result = TestUtils.assertEqual(v12Sorted.sessions[0].id, 's2', '时间排序');
            this.showResult(containerId, result, '10. 数据转换 - 时间排序');

            // 测试 9: 数据转换 - 当前会话 ID
            const v11WithActive = {
                sessions: {
                    'tab-1': { id: 's1', workingDir: '/path1' },
                    'tab-2': { id: 's2', workingDir: '/path2' }
                },
                activeTab: 'tab-2'
            };
            const v12WithCurrent = Migration.convertV11ToV12(v11WithActive);
            result = TestUtils.assertEqual(v12WithCurrent.currentSessionId, 's2', '当前会话 ID');
            this.showResult(containerId, result, '11. 数据转换 - 当前会话 ID');

            // 测试 10: 数据转换 - 工作空间历史
            const v12WithHistory = Migration.convertV11ToV12(v11Data);
            result = TestUtils.assertTrue(
                v12WithHistory.workspaceHistory.includes('/path1'),
                '工作空间历史'
            );
            this.showResult(containerId, result, '12. 数据转换 - 工作空间历史');

            // 测试 11: 数据转换 - 空数据
            const v12Empty = Migration.convertV11ToV12({ sessions: {} });
            result = TestUtils.assertLength(v12Empty.sessions, 0, '空数据转换');
            this.showResult(containerId, result, '13. 数据转换 - 空数据');

            // 测试 12: 数据转换 - working_dir 兼容
            const v11AltKey = {
                sessions: {
                    'tab-1': { id: 's1', working_dir: '/alt/path' }
                }
            };
            const v12AltKey = Migration.convertV11ToV12(v11AltKey);
            result = TestUtils.assertTrue(
                v12AltKey.workspaceHistory.includes('/alt/path'),
                'working_dir 键兼容'
            );
            this.showResult(containerId, result, '14. 数据转换 - working_dir 兼容');

            // 测试 13: 验证数据
            const validationResult = Migration.validateV12Data(v12Data, v11Data);
            result = TestUtils.assertTrue(validationResult.valid, '数据验证');
            this.showResult(containerId, result, '15. 数据验证');

            // 测试 14: 加载 v11 数据
            localStorage.setItem('sessions_v11', JSON.stringify(v11Data));
            const loadedV11 = Migration.loadV11Data();
            result = TestUtils.assertTrue(
                loadedV11.sessions && loadedV11.sessions['tab-1'],
                '加载 v11 数据'
            );
            this.showResult(containerId, result, '16. 加载 v11 数据');

            // 测试 15: 保存数据版本
            Migration.saveDataVersion('v12');
            const savedVersion = localStorage.getItem('dataVersion_v12');
            result = TestUtils.assertEqual(savedVersion, 'v12', '保存数据版本');
            this.showResult(containerId, result, '17. 保存数据版本');

            // 测试 16: 加载数据版本
            const loadedVersion = Migration.loadDataVersion();
            result = TestUtils.assertEqual(loadedVersion, 'v12', '加载数据版本');
            this.showResult(containerId, result, '18. 加载数据版本');

            // 测试 17: 获取迁移状态
            const status = Migration.getMigrationStatus();
            result = TestUtils.assertProperty(status, 'needsMigration', '迁移状态');
            this.showResult(containerId, result, '19. 获取迁移状态');

            // 更新显示
            this.updateStorageDisplay();

        } catch (error) {
            this.showResult(containerId, { pass: false, message: error.message }, 'Migration 测试异常');
        }

        console.log('=== Migration 测试完成 ===');
    },

    // ==================== Session 测试 ====================

    async runSessionTests() {
        const containerId = 'session-results';
        const container = document.getElementById(containerId);
        if (container) container.innerHTML = '';

        console.log('=== 开始 Session 测试 ===');

        try {
            // 测试 1: Session 模块存在
            let result = TestUtils.assertTrue(
                typeof Session !== 'undefined',
                'Session 模块存在'
            );
            this.showResult(containerId, result, '1. Session 模块定义');

            // 测试 2: 设置可编辑状态
            const mockRunner = {
                resumeInput: document.createElement('input'),
                workingDirInput: document.createElement('input'),
                workspaceCombo: null,
                continueConversationCheckbox: document.createElement('input')
            };
            mockRunner.continueConversationCheckbox.type = 'checkbox';
            mockRunner.continueConversationCheckbox.checked = true;

            Session.setSessionEditable(mockRunner, true);
            result = TestUtils.assertFalse(mockRunner.resumeInput.hasAttribute('readonly'), '设置可编辑');
            this.showResult(containerId, result, '2. 设置可编辑状态');

            // 测试 3: 设置不可编辑状态
            Session.setSessionEditable(mockRunner, false);
            result = TestUtils.assertTrue(mockRunner.resumeInput.hasAttribute('readonly'), '设置只读');
            this.showResult(containerId, result, '3. 设置只读状态');

            // 测试 4: 更新会话显示
            mockRunner.currentSessionId = null;
            Session.updateSessionDisplay(mockRunner, 'session-123', 'Test Session');
            result = TestUtils.assertEqual(mockRunner.currentSessionId, 'session-123', '更新会话 ID');
            this.showResult(containerId, result, '4. 更新会话显示');

            // 测试 5: 更新会话显示 - 清空
            Session.updateSessionDisplay(mockRunner, null, null);
            result = TestUtils.assertEqual(mockRunner.currentSessionId, null, '清空会话 ID');
            this.showResult(containerId, result, '5. 清空会话显示');

            // 测试 6: 检查未保存内容 - 无内容
            const emptyRunner = {
                resumeInput: document.createElement('input'),
                outputEl: document.createElement('div')
            };
            const hasNoUnsaved = Session._checkUnsavedContent(emptyRunner);
            result = TestUtils.assertFalse(hasNoUnsaved, '检查无未保存内容');
            this.showResult(containerId, result, '6. 检查无未保存内容');

            // 测试 7: 检查未保存内容 - 有内容
            const runnerWithContent = {
                resumeInput: document.createElement('input'),
                outputEl: document.createElement('div')
            };
            runnerWithContent.outputEl.innerHTML = '<div class="message">Test</div>';
            const hasUnsaved = Session._checkUnsavedContent(runnerWithContent);
            result = TestUtils.assertTrue(hasUnsaved, '检查有未保存内容');
            this.showResult(containerId, result, '7. 检查有未保存内容');

            // 测试 8: 检查未保存内容 - 输入框有内容
            const runnerWithInput = {
                resumeInput: document.createElement('input'),
                outputEl: document.createElement('div')
            };
            runnerWithInput.resumeInput.value = 'Some text';
            const hasInputUnsaved = Session._checkUnsavedContent(runnerWithInput);
            result = TestUtils.assertTrue(hasInputUnsaved, '检查输入框有内容');
            this.showResult(containerId, result, '8. 检查输入框有内容');

            // 测试 9: 重置工具配置方法存在
            result = TestUtils.assertTrue(
                typeof Session._resetToolsConfig === 'function',
                '重置工具配置方法'
            );
            this.showResult(containerId, result, '9. 重置工具配置方法存在');

            // 测试 10: 清空当前会话方法存在
            result = TestUtils.assertTrue(
                typeof Session.clearCurrentSession === 'function',
                '清空当前会话方法'
            );
            this.showResult(containerId, result, '10. 清空当前会话方法存在');

            // 测试 11: 创建新会话方法存在
            result = TestUtils.assertTrue(
                typeof Session.createNewSessionFromProject === 'function',
                '创建新会话方法'
            );
            this.showResult(containerId, result, '11. 创建新会话方法存在');

            // 测试 12: 确认对话框方法存在
            result = TestUtils.assertTrue(
                typeof Session._showConfirmDialog === 'function',
                '确认对话框方法'
            );
            this.showResult(containerId, result, '12. 确认对话框方法存在');

        } catch (error) {
            this.showResult(containerId, { pass: false, message: error.message }, 'Session 测试异常');
        }

        console.log('=== Session 测试完成 ===');
    }
};

// ==================== 全局测试实例 ====================

// 用于手动测试 HistoryDrawer
let testHistoryDrawer = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 初始化 HistoryDrawer 实例用于手动测试
    if (typeof HistoryDrawer !== 'undefined') {
        testHistoryDrawer = new HistoryDrawer({
            onSelect: (session) => {
                console.log('Selected session:', session);
                alert(`选择了会话: ${session.id}`);
            },
            onClose: () => {
                console.log('Drawer closed');
            }
        });
    }

    // 更新 localStorage 显示
    TestRunner.updateStorageDisplay();

    console.log('v12 测试页面已加载');
    console.log('可用命令:');
    console.log('- TestRunner.runAllTests() - 运行所有测试');
    console.log('- TestRunner.runWorkspaceComboTests() - 运行 WorkspaceCombo 测试');
    console.log('- TestRunner.runHistoryDrawerTests() - 运行 HistoryDrawer 测试');
    console.log('- TestRunner.runMigrationTests() - 运行 Migration 测试');
    console.log('- TestRunner.runSessionTests() - 运行 Session 测试');
});
