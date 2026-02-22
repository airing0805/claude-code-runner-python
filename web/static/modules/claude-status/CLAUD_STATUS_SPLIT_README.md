# Claude Status 模块拆分说明

## 拆分结构

原 `claudeStatus.js` 文件已被拆分为以下四个独立模块，存放在 `/static/modules/claude-status/` 目录下：

### 1. claudeStatusCore.js - 核心状态管理模块
- 负责基础的状态管理功能
- 处理数据加载和API调用
- 管理事件绑定和生命周期
- 包含版本信息、环境变量、配置信息等核心数据加载

### 2. claudeDocs.js - 文档展示模块
- 专门负责各种文档内容的加载和展示
- 包含工具文档、代理文档、命令文档、最佳实践等内容
- 管理文档的手风琴展开/收起交互

### 3. claudeUI.js - UI组件模块
- 负责UI相关的样式注入和组件管理
- 包含所有的CSS样式定义
- 管理UI交互组件如提示消息等

### 4. claudeStatusMain.js - 主整合模块
- 整合所有子模块功能
- 提供统一的对外接口
- 确保模块间的协调工作

## 使用方式

在HTML中按以下顺序引入模块：

```html
<script src="/static/modules/claude-status/claudeStatusCore.js"></script>
<script src="/static/modules/claude-status/claudeDocs.js"></script>
<script src="/static/modules/claude-status/claudeUI.js"></script>
<script src="/static/modules/claude-status/claudeStatusMain.js"></script>
```

## 优势

1. **职责分离**：每个模块职责明确，便于维护和扩展
2. **可复用性**：UI组件和文档展示可以独立复用
3. **易于测试**：可以单独测试每个模块的功能
4. **按需加载**：未来可以根据需要选择性加载特定模块
5. **代码组织**：提高了代码的可读性和结构性
6. **文件管理**：集中存放相关模块，便于项目结构管理

## 兼容性

新的模块结构保持了与原有 `ClaudeStatus` 对象相同的公共接口，
确保现有代码无需修改即可正常工作。

## 文件位置

所有拆分后的模块文件位于：
`/web/static/modules/claude-status/` 目录下