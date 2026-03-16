# Claude Code 插件系统

Claude Code 支持插件扩展，可以添加自定义命令、代理、技能和钩子。

## 1. 官方插件

Claude Code 仓库内置以下官方插件：

| 插件名称 | 功能描述 |
|----------|---------|
| **agent-sdk-dev** | Agent SDK 开发套件，包含 `/new-sdk-app` 命令和 SDK 验证代理 |
| **code-review** | 自动代码审查，使用 5 个并行 Sonnet 代理进行多维度审查 |
| **commit-commands** | Git 工作流自动化：`/commit`、`/commit-push-pr`、`/clean_gone` |
| **feature-dev** | 功能开发工作流，7 阶段结构化开发流程 |
| **frontend-design** | 前端设计指南，提供生产级界面设计建议 |
| **hookify** | 创建自定义钩子，防止不良行为 |
| **plugin-dev** | 插件开发工具包，8 阶段插件创建工作流 |
| **pr-review-toolkit** | PR 审查工具集，专注于注释、测试、错误处理等 |
| **ralph-wiggum** | 交互式自引用 AI 循环，持续迭代直到完成 |
| **security-guidance** | 安全提醒钩子，监控 9 种安全模式 |
| **learning-output-style** | 交互式学习模式，在决策点请求代码贡献 |

---

## 2. 插件结构

每个插件遵循标准结构：

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json          # 插件元数据
├── commands/               # 斜杠命令（可选）
├── agents/                 # 专业代理（可选）
├── skills/                # 技能定义（可选）
├── hooks/                 # 事件钩子（可选）
├── .mcp.json              # MCP 服务器配置（可选）
└── README.md              # 插件文档
```

---

## 3. 插件类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **commands** | 斜杠命令 | `/commit`, `/code-review` |
| **agents** | 专业代理 | 代码审查代理、安全代理 |
| **skills** | 技能定义 | 前端设计技能、插件开发技能 |
| **hooks** | 事件钩子 | PreToolUse、SessionStart、Stop |
| **MCP** | 外部工具 | 数据库连接、API 集成 |

---

## 4. 钩子类型

Claude Code 支持以下钩子：

| 钩子名称 | 触发时机 |
|----------|---------|
| **PreToolUse** | 工具执行前 |
| **PostToolUse** | 工具执行后 |
| **Stop** | 会话结束时 |
| **SessionStart** | 会话开始时 |
| **Notification** | 通知事件 |
