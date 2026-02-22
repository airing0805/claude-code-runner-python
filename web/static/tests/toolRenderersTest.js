/**
 * 工具渲染器集成测试
 * v0.5.3.6 - 集成与测试
 *
 * 在浏览器控制台中运行此脚本进行测试:
 * 1. 打开应用页面
 * 2. 打开浏览器开发者工具 (F12)
 * 3. 复制此脚本到控制台执行
 */

(function() {
    'use strict';

    const testResults = {
        passed: 0,
        failed: 0,
        errors: []
    };

    /**
     * 测试断言
     */
    function assert(condition, testName) {
        if (condition) {
            console.log(`✅ ${testName}`);
            testResults.passed++;
        } else {
            console.error(`❌ ${testName}`);
            testResults.failed++;
            testResults.errors.push(testName);
        }
    }

    /**
     * 测试套件
     */
    const tests = {
        /**
         * 测试渲染器是否加载
         */
        testRenderersLoaded() {
            assert(typeof window.ToolRenderers !== 'undefined', 'ToolRenderers 已加载');
            assert(typeof window.ToolRenderers.hasInputRenderer === 'function', 'hasInputRenderer 方法存在');
            assert(typeof window.ToolRenderers.hasResultRenderer === 'function', 'hasResultRenderer 方法存在');
            assert(typeof window.ToolRenderers.renderInput === 'function', 'renderInput 方法存在');
            assert(typeof window.ToolRenderers.renderResult === 'function', 'renderResult 方法存在');
        },

        /**
         * 测试输入渲染器注册
         */
        testInputRenderers() {
            const expectedRenderers = ['Read', 'Edit', 'Write', 'Bash', 'Grep', 'Glob', 'Task', 'TodoWrite', 'AskUserQuestion'];
            expectedRenderers.forEach(name => {
                assert(window.ToolRenderers.hasInputRenderer(name), `输入渲染器 ${name} 已注册`);
            });
        },

        /**
         * 测试结果渲染器注册
         */
        testResultRenderers() {
            const expectedRenderers = ['Read', 'Bash', 'Grep', 'Glob'];
            expectedRenderers.forEach(name => {
                const hasRenderer = window.ToolRenderers.hasResultRenderer(name);
                assert(hasRenderer, `结果渲染器 ${name} 已注册`);
            });
        },

        /**
         * 测试 Read 渲染器
         */
        testReadRenderer() {
            const input = {
                file_path: '/test/example.py',
                limit: 50
            };
            const element = window.ToolRenderers.renderInput('Read', input);
            assert(element !== null, 'Read 渲染器返回元素');
            assert(element instanceof HTMLElement, 'Read 渲染器返回 HTMLElement');

            // 测试结果渲染
            const resultOptions = {
                content: 'def hello():\n    print("Hello")',
                maxLines: 30
            };
            const resultElement = window.ToolRenderers.renderResult('Read', resultOptions);
            assert(resultElement !== null, 'Read 结果渲染器返回元素');
        },

        /**
         * 测试 Bash 渲染器
         */
        testBashRenderer() {
            const input = {
                command: 'npm install',
                description: '安装依赖'
            };
            const element = window.ToolRenderers.renderInput('Bash', input);
            assert(element !== null, 'Bash 渲染器返回元素');

            // 测试结果渲染
            const resultOptions = {
                content: 'added 100 packages in 2s',
                isError: false
            };
            const resultElement = window.ToolRenderers.renderResult('Bash', resultOptions);
            assert(resultElement !== null, 'Bash 结果渲染器返回元素');

            // 测试错误结果
            const errorOptions = {
                content: 'Error: command not found',
                isError: true
            };
            const errorElement = window.ToolRenderers.renderResult('Bash', errorOptions);
            assert(errorElement !== null, 'Bash 错误结果渲染器返回元素');
        },

        /**
         * 测试 Grep 渲染器
         */
        testGrepRenderer() {
            const input = {
                pattern: 'function',
                path: '/src',
                type: 'js'
            };
            const element = window.ToolRenderers.renderInput('Grep', input);
            assert(element !== null, 'Grep 渲染器返回元素');

            // 测试结果渲染
            const resultOptions = {
                content: 'file1.js:10:function hello() {\nfile2.js:5:function world() {',
                isFileList: false
            };
            const resultElement = window.ToolRenderers.renderResult('Grep', resultOptions);
            assert(resultElement !== null, 'Grep 结果渲染器返回元素');
        },

        /**
         * 测试 Glob 渲染器
         */
        testGlobRenderer() {
            const input = {
                pattern: '**/*.js',
                path: '/src'
            };
            const element = window.ToolRenderers.renderInput('Glob', input);
            assert(element !== null, 'Glob 渲染器返回元素');

            // 测试结果渲染
            const resultOptions = {
                content: 'src/index.js\nsrc/utils.js\nsrc/main.js',
                isFileList: true
            };
            const resultElement = window.ToolRenderers.renderResult('Glob', resultOptions);
            assert(resultElement !== null, 'Glob 结果渲染器返回元素');
        },

        /**
         * 测试 Edit 渲染器
         */
        testEditRenderer() {
            const input = {
                file_path: '/test/file.py',
                old_string: 'old code',
                new_string: 'new code'
            };
            const element = window.ToolRenderers.renderInput('Edit', input);
            assert(element !== null, 'Edit 渲染器返回元素');
        },

        /**
         * 测试 Write 渲染器
         */
        testWriteRenderer() {
            const input = {
                file_path: '/test/newfile.py',
                content: '# New file\nprint("Hello")'
            };
            const element = window.ToolRenderers.renderInput('Write', input);
            assert(element !== null, 'Write 渲染器返回元素');
        },

        /**
         * 测试 TodoWrite 渲染器
         */
        testTodoRenderer() {
            const input = {
                todos: [
                    { content: 'Task 1', status: 'completed', activeForm: 'Doing task 1' },
                    { content: 'Task 2', status: 'in_progress', activeForm: 'Doing task 2' },
                    { content: 'Task 3', status: 'pending', activeForm: 'Doing task 3' }
                ]
            };
            const element = window.ToolRenderers.renderInput('TodoWrite', input);
            assert(element !== null, 'TodoWrite 渲染器返回元素');
        },

        /**
         * 测试 Task 渲染器
         */
        testTaskRenderer() {
            const input = {
                subagent_type: 'general-purpose',
                description: 'Test task',
                prompt: 'This is a test prompt for the agent'
            };
            const element = window.ToolRenderers.renderInput('Task', input);
            assert(element !== null, 'Task 渲染器返回元素');
        },

        /**
         * 测试 AskQuestion 渲染器
         */
        testAskQuestionRenderer() {
            const input = {
                questions: [{
                    question: 'Choose an option?',
                    header: 'Selection',
                    options: [
                        { label: 'Option A', description: 'Description A' },
                        { label: 'Option B', description: 'Description B' }
                    ]
                }]
            };
            const element = window.ToolRenderers.renderInput('AskUserQuestion', input);
            assert(element !== null, 'AskQuestion 渲染器返回元素');
        },

        /**
         * 测试 CopyButton 组件
         */
        testCopyButton() {
            assert(typeof window.CopyButton !== 'undefined', 'CopyButton 组件已加载');
            assert(typeof window.CopyButton.create === 'function', 'CopyButton.create 方法存在');
            assert(typeof window.CopyButton.handleCopy === 'function', 'CopyButton.handleCopy 方法存在');

            const btn = window.CopyButton.create('test text', { title: 'Copy' });
            assert(btn instanceof HTMLElement, 'CopyButton 返回 HTMLElement');
        },

        /**
         * 测试 MarkdownRenderer 组件
         */
        testMarkdownRenderer() {
            assert(typeof window.MarkdownRenderer !== 'undefined', 'MarkdownRenderer 组件已加载');
            assert(typeof window.MarkdownRenderer.render === 'function', 'MarkdownRenderer.render 方法存在');
        },

        /**
         * 测试 MessageRenderer 集成
         */
        testMessageRendererIntegration() {
            assert(typeof window.MessageRenderer !== 'undefined', 'MessageRenderer 已加载');
            assert(typeof window.MessageRenderer._isToolRenderersAvailable === 'function', '_isToolRenderersAvailable 方法存在');
            assert(typeof window.MessageRenderer._normalizeToolName === 'function', '_normalizeToolName 方法存在');

            // 测试工具名称规范化
            const normalize = window.MessageRenderer._normalizeToolName;
            assert(normalize('read') === 'Read', '规范化小写工具名');
            assert(normalize('todowrite') === 'TodoWrite', '规范化特殊工具名');
            assert(normalize('Bash') === 'Bash', '保持正确大小写');
        }
    };

    /**
     * 运行所有测试
     */
    function runAllTests() {
        console.log('========== 工具渲染器集成测试 ==========');
        console.log('开始运行测试...\n');

        Object.keys(tests).forEach(testName => {
            console.log(`\n--- ${testName} ---`);
            try {
                tests[testName]();
            } catch (err) {
                console.error(`❌ ${testName} 抛出异常:`, err);
                testResults.failed++;
                testResults.errors.push(`${testName}: ${err.message}`);
            }
        });

        console.log('\n========== 测试结果 ==========');
        console.log(`通过: ${testResults.passed}`);
        console.log(`失败: ${testResults.failed}`);

        if (testResults.errors.length > 0) {
            console.log('\n失败的测试:');
            testResults.errors.forEach(err => console.log(`  - ${err}`));
        }

        console.log('\n测试完成!');
        return testResults;
    }

    // 暴露测试函数
    window.runToolRenderersTest = runAllTests;

    console.log('工具渲染器测试脚本已加载。运行 window.runToolRenderersTest() 开始测试。');
})();
