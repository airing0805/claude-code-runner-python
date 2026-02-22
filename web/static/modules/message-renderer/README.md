# Message Renderer 消息渲染器模块

## 概述

消息渲染器模块负责处理 Claude Code Runner 中所有类型消息的渲染，包括历史消息显示、实时消息更新、工具调用渲染等功能。该模块采用模块化设计，将不同功能拆分为独立的子模块。

## 模块结构

```
message-renderer/
├── index.js          # 主模块入口，整合所有子模块
├── core.js           # 核心渲染器，处理基础消息渲染和轮次管理
├── content.js        # 内容块渲染器，处理各种内容类型的渲染
├── thinking.js       # 思考块渲染器，专门处理 AI 思考内容
├── tools.js          # 工具渲染器，处理工具调用的渲染逻辑
├── tool-results.js   # 工具结果渲染器，专门处理各种工具结果类型
└── README.md         # 本说明文档
```

## 功能特性

### 核心功能 (core.js)
- 历史消息显示和分组
- 对话轮次管理
- 基础消息添加功能
- 内容截断配置管理

### 内容渲染 (content.js)
- 文本块渲染（支持截断和展开）
- 用户消息渲染
- AI 响应消息渲染
- 内容块类型分发

### 思考渲染 (thinking.js)
- AI 思考内容的可折叠渲染
- 思考块展开/收起交互

### 工具渲染 (tools.js)
- 工具调用块渲染
- 工具图标和预览系统集成
- 工具结果块渲染
- 专用工具渲染器集成

### 结果渲染 (tool-results.js)
- 各种工具结果类型的专门渲染
- Read 工具的代码行号显示
- Bash 工具的终端样式渲染
- Grep 工具的搜索结果高亮
- Glob 工具的文件列表显示

## 使用方法

### 基本使用

```javascript
// 显示历史消息
MessageRenderer.displayHistoryMessages(runner, messages);

// 添加助手消息
MessageRenderer.addAssistantMessage(runner, 'text', 'Hello World', timestamp);
```

### 配置选项

```javascript
// 修改内容截断配置
MessageRenderer.truncationConfig = {
    maxLines: 50,
    maxChars: 10000,
    previewLines: 5
};

// 修改自动展开的工具类型
MessageRenderer.autoExpandTools = ['todowrite', 'task'];
```

## 依赖关系

- `Utils` - 工具函数库
- `Task` - 任务管理模块
- `ToolRenderers` - 工具渲染器（可选）
- `ToolIcons` - 工具图标系统（可选）
- `ToolPreview` - 工具预览系统（可选）

## 版本历史

### v0.5.4
- 消息渲染增强：内容截断、动画、思考块、工具图标/预览系统
- 模块化重构，拆分为多个独立子模块

### v0.5.3.6
- 完善工具渲染器集成

## 注意事项

1. 所有子模块必须在主模块之前加载
2. 某些高级功能需要相应的依赖模块支持
3. 渲染过程中会自动生成唯一 ID 用于交互控制
4. 支持实时滚动到底部功能

## 扩展开发

要添加新的工具结果类型渲染：

1. 在 `tool-results.js` 中添加样式配置
2. 实现对应的渲染方法
3. 在 `_renderToolResultByType` 方法中添加类型判断

要添加新的内容块类型：

1. 在 `content.js` 中添加渲染方法
2. 在 `_renderContentBlock` 方法中添加类型分支