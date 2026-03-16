/**
 * 消息渲染器模块测试文件
 * 验证各模块是否正确加载和功能是否正常
 */

// 测试模块加载
function testModuleLoading() {
    const modules = [
        'MessageRendererCore',
        'MessageRendererContent', 
        'MessageRendererThinking',
        'MessageRendererTools',
        'MessageRendererToolResults',
        'MessageRenderer'
    ];
    
    console.log('=== 模块加载测试 ===');
    modules.forEach(moduleName => {
        if (typeof window[moduleName] !== 'undefined') {
            console.log(`✓ ${moduleName} 加载成功`);
        } else {
            console.error(`✗ ${moduleName} 加载失败`);
        }
    });
}

// 测试核心功能
function testCoreFunctionality() {
    console.log('\n=== 核心功能测试 ===');
    
    // 测试配置访问
    try {
        console.log('截断配置:', MessageRenderer.truncationConfig);
        console.log('自动展开工具:', MessageRenderer.autoExpandTools);
        console.log('✓ 配置访问正常');
    } catch (e) {
        console.error('✗ 配置访问异常:', e.message);
    }
    
    // 测试方法存在性
    const methods = [
        'displayHistoryMessages',
        'addAssistantMessage'
    ];
    
    methods.forEach(method => {
        if (typeof MessageRenderer[method] === 'function') {
            console.log(`✓ 方法 ${method} 存在`);
        } else {
            console.error(`✗ 方法 ${method} 不存在`);
        }
    });
}

// 测试工具相关功能
function testToolFunctionality() {
    console.log('\n=== 工具功能测试 ===');
    
    try {
        // 测试工具名称规范化
        const testNames = ['read', 'WRITE', 'bash', 'unknown_tool'];
        testNames.forEach(name => {
            const normalized = MessageRenderer._normalizeToolName(name);
            console.log(`${name} -> ${normalized}`);
        });
        
        // 测试工具图标获取
        const toolNames = ['read', 'write', 'bash'];
        toolNames.forEach(name => {
            const icon = MessageRenderer._getToolIcon(name);
            console.log(`${name} 图标: ${icon}`);
        });
        
        console.log('✓ 工具功能测试通过');
    } catch (e) {
        console.error('✗ 工具功能测试失败:', e.message);
    }
}

// 运行所有测试
function runAllTests() {
    console.log('开始测试消息渲染器模块...\n');
    
    testModuleLoading();
    testCoreFunctionality();
    testToolFunctionality();
    
    console.log('\n=== 测试完成 ===');
}

// 如果在浏览器环境中，自动运行测试
if (typeof window !== 'undefined') {
    // 延迟执行确保所有模块加载完成
    setTimeout(runAllTests, 100);
}

// 导出测试函数（如果在 Node.js 环境中）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        runAllTests,
        testModuleLoading,
        testCoreFunctionality,
        testToolFunctionality
    };
}