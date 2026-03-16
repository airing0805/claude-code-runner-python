/**
 * Claude 状态模块（整合版）
 * 整合核心状态管理、文档展示和UI组件功能
 */

// 确保依赖模块已加载
if (typeof ClaudeStatusCore === 'undefined') {
    throw new Error('ClaudeStatusCore 模块未加载');
}

if (typeof ClaudeDocs === 'undefined') {
    throw new Error('ClaudeDocs 模块未加载');
}

if (typeof ClaudeUI === 'undefined') {
    throw new Error('ClaudeUI 模块未加载');
}

// 整合模块
const ClaudeStatus = {
    // 继承核心功能
    ...ClaudeStatusCore,
    
    // 继承文档功能
    ...ClaudeDocs,
    
    // 继承UI功能
    ...ClaudeUI,

    /**
     * 初始化整个 Claude 状态模块
     */
    init() {
        // 初始化各个子模块
        ClaudeStatusCore.init();
        ClaudeUI.init();
        
        // 绑定文档相关事件
        this.bindDocsEvents();
    },

    /**
     * 绑定文档相关事件
     */
    bindDocsEvents() {
        // 文档 tab 切换已在核心模块中处理
        // 这里可以添加其他文档相关的事件绑定
    },

    /**
     * 重写 onShow 方法，确保所有子模块都被调用
     */
    onShow() {
        // 调用核心模块的 onShow
        ClaudeStatusCore.onShow.call(this);
        
        // 如果需要特殊的文档加载逻辑，可以在这里添加
    },

    /**
     * 重写 onDocsShow 方法
     */
    onDocsShow() {
        // 调用核心模块的 onDocsShow
        ClaudeStatusCore.onDocsShow.call(this);
    }
};

// 导出模块
window.ClaudeStatus = ClaudeStatus;