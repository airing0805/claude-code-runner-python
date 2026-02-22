/**
 * 消息渲染器主模块
 * 整合所有子模块，提供统一的接口
 *
 * v0.5.3.6: 完善工具渲染器集成
 * v0.5.4: 消息渲染增强 - 内容截断、动画、思考块、工具图标/预览系统
 */

// 确保所有依赖模块已加载
if (typeof MessageRendererCore === 'undefined') {
    throw new Error('MessageRendererCore module not loaded');
}

if (typeof MessageRendererContent === 'undefined') {
    throw new Error('MessageRendererContent module not loaded');
}

if (typeof MessageRendererThinking === 'undefined') {
    throw new Error('MessageRendererThinking module not loaded');
}

if (typeof MessageRendererTools === 'undefined') {
    throw new Error('MessageRendererTools module not loaded');
}

if (typeof MessageRendererToolResults === 'undefined') {
    throw new Error('MessageRendererToolResults module not loaded');
}

/**
 * 消息渲染器主类
 * 提供统一的接口访问所有渲染功能
 */
const MessageRenderer = {
    // 代理核心功能
    displayHistoryMessages: MessageRendererCore.displayHistoryMessages.bind(MessageRendererCore),
    addAssistantMessage: MessageRendererCore.addAssistantMessage.bind(MessageRendererCore),
    
    // 代理配置访问
    get truncationConfig() {
        return MessageRendererCore._truncationConfig;
    },
    
    set truncationConfig(config) {
        Object.assign(MessageRendererCore._truncationConfig, config);
    },
    
    get autoExpandTools() {
        return MessageRendererCore._autoExpandTools;
    },
    
    set autoExpandTools(tools) {
        MessageRendererCore._autoExpandTools = tools;
    },

    // 内容块渲染相关方法（内部使用）
    _renderUserContent: MessageRendererContent._renderUserContent.bind(MessageRendererContent),
    _renderAssistantMessages: MessageRendererContent._renderAssistantMessages.bind(MessageRendererContent),
    _renderContentBlock: MessageRendererContent._renderContentBlock.bind(MessageRendererContent),
    _renderTextBlock: MessageRendererContent._renderTextBlock.bind(MessageRendererContent),
    _renderTruncatedText: MessageRendererContent._renderTruncatedText.bind(MessageRendererContent),
    _toggleContentExpand: MessageRendererContent._toggleContentExpand.bind(MessageRendererContent),

    // 思考块渲染相关方法（内部使用）
    _renderThinkingBlock: MessageRendererThinking._renderThinkingBlock.bind(MessageRendererThinking),
    _toggleThinking: MessageRendererThinking._toggleThinking.bind(MessageRendererThinking),

    // 工具渲染相关方法（内部使用）
    _isToolRenderersAvailable: MessageRendererTools._isToolRenderersAvailable.bind(MessageRendererTools),
    _isToolIconsAvailable: MessageRendererTools._isToolIconsAvailable.bind(MessageRendererTools),
    _isToolPreviewAvailable: MessageRendererTools._isToolPreviewAvailable.bind(MessageRendererTools),
    _getToolIcon: MessageRendererTools._getToolIcon.bind(MessageRendererTools),
    _getToolPreview: MessageRendererTools._getToolPreview.bind(MessageRendererTools),
    _normalizeToolName: MessageRendererTools._normalizeToolName.bind(MessageRendererTools),
    _renderToolUseBlock: MessageRendererTools._renderToolUseBlock.bind(MessageRendererTools),
    _renderToolUseContent: MessageRendererTools._renderToolUseContent.bind(MessageRendererTools),
    _toggleToolUse: MessageRendererTools._toggleToolUse.bind(MessageRendererTools),
    _renderToolResultBlock: MessageRendererTools._renderToolResultBlock.bind(MessageRendererTools),
    _toggleToolResult: MessageRendererTools._toggleToolResult.bind(MessageRendererTools),

    // 工具结果渲染相关方法（内部使用）
    _getToolResultStyle: MessageRendererToolResults._getToolResultStyle.bind(MessageRendererToolResults),
    _renderToolResultByType: MessageRendererToolResults._renderToolResultByType.bind(MessageRendererToolResults),
    _renderReadResult: MessageRendererToolResults._renderReadResult.bind(MessageRendererToolResults),
    _renderBashResult: MessageRendererToolResults._renderBashResult.bind(MessageRendererToolResults),
    _renderGrepResult: MessageRendererToolResults._renderGrepResult.bind(MessageRendererToolResults),
    _renderGlobResult: MessageRendererToolResults._renderGlobResult.bind(MessageRendererToolResults),
    _getFileIcon: MessageRendererToolResults._getFileIcon.bind(MessageRendererToolResults)
};

// 导出到全局命名空间
window.MessageRenderer = MessageRenderer;