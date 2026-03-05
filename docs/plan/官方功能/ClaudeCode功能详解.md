# Claude Code 功能详解

本文档是 Claude Code 功能文档的索引页面，详细内容已拆分为多个子文档。

## 文档索引

| 章节 | 文档 | 内容概述 |
|------|------|---------|
| 核心概念 | [ClaudeCode-核心概念.md](./ClaudeCode-核心概念.md) | 工具调用、权限控制、流式响应、会话管理 |
| 工具详解 | [ClaudeCode-工具详解.md](./ClaudeCode-工具详解.md) | Read、Write、Edit、Bash、Glob、Grep、WebSearch、WebFetch、Task |
| 权限模式 | [ClaudeCode-权限模式.md](./ClaudeCode-权限模式.md) | default、acceptEdits、plan、bypassPermissions |
| 消息与执行 | [ClaudeCode-消息与执行.md](./ClaudeCode-消息与执行.md) | 消息类型、同步/流式执行 |
| 会话管理 | [ClaudeCode-会话管理.md](./ClaudeCode-会话管理.md) | 继续对话、恢复会话、配置选项 |
| 响应与实践 | [ClaudeCode-响应与最佳实践.md](./ClaudeCode-响应与最佳实践.md) | 任务统计、费用计算、最佳实践 |
| 内置命令 | [ClaudeCode-内置命令.md](./ClaudeCode-内置命令.md) | CLI 命令、斜杠命令、快捷键 |
| 代理类型 | [ClaudeCode-代理类型.md](./ClaudeCode-代理类型.md) | general-purpose、explore、code-explorer 等 |
| 插件系统 | [ClaudeCode-插件系统.md](./ClaudeCode-插件系统.md) | 官方插件、插件架构、钩子类型 |
| 安装与政策 | [ClaudeCode-安装与政策.md](./ClaudeCode-安装与政策.md) | 安装方式、数据收集政策 |

## 快速导航

### 按使用场景

| 场景 | 推荐阅读 |
|------|---------|
| 首次使用 | [安装与政策](./ClaudeCode-安装与政策.md) → [核心概念](./ClaudeCode-核心概念.md) |
| 日常开发 | [工具详解](./ClaudeCode-工具详解.md) → [内置命令](./ClaudeCode-内置命令.md) |
| 集成开发 | [消息与执行](./ClaudeCode-消息与执行.md) → [会话管理](./ClaudeCode-会话管理.md) |
| 扩展功能 | [代理类型](./ClaudeCode-代理类型.md) → [插件系统](./ClaudeCode-插件系统.md) |

### 按功能类型

| 功能 | 文档 |
|------|------|
| 文件操作 | [ClaudeCode-工具详解.md](./ClaudeCode-工具详解.md) § 1-3 |
| 代码搜索 | [ClaudeCode-工具详解.md](./ClaudeCode-工具详解.md) § 5-6 |
| 网络访问 | [ClaudeCode-工具详解.md](./ClaudeCode-工具详解.md) § 7-8 |
| 权限控制 | [ClaudeCode-权限模式.md](./ClaudeCode-权限模式.md) |
| 自动化 | [ClaudeCode-权限模式.md](./ClaudeCode-权限模式.md) § 4 |

## 相关链接

- [官方文档](https://code.claude.com/docs/en/overview)
- [官方 GitHub 仓库](https://github.com/anthropics/claude-code)
- [插件系统文档](https://docs.claude.com/en/docs/claude-code/plugins)
- [Agent SDK 文档](https://docs.claude.com/en/api/agent-sdk/overview)
