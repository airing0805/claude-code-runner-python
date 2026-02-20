# v0.3.3 - 文档展示

## 1. 功能概述

以文档形式展示 Claude Code 功能说明，包括工具详解、代理类型、内置命令和最佳实践。

## 2. 用户场景

| 场景 | 描述 |
|------|------|
| 了解工具详情 | 用户想深入了解每个工具的用途、参数和使用方法 |
| 了解代理类型 | 用户想了解不同代理类型的适用场景 |
| 了解内置命令 | 用户想了解斜杠命令的使用方法 |
| 学习最佳实践 | 用户想了解工具选择和错误处理的最佳实践 |

## 3. 功能列表

### 3.1 工具详解文档

- 9个工具的详细说明：Read、Write、Edit、Bash、Glob、Grep、WebSearch、WebFetch、Task
- 每个工具包含：功能描述、参数说明、使用示例

### 3.2 代理类型说明

- 9种代理类型：general-purpose、explore、code-explorer、code-architect、code-reviewer、agent-creator、plugin-validator、skill-reviewer、conversation-analyzer
- 每个代理包含：用途说明、适用场景

### 3.3 内置命令说明

- CLI 启动命令（9个）：claude、claude "问题"、claude -c、claude --version、claude update、claude doctor、claude mcp、claude login、claude logout
- 斜杠命令（24个）：/help、/config、/model、/memory、/init、/clear、/compact、/exit、/bug、/doctor、/usage、/stats、/permissions、/terminal-setup、/add-dir、/context、/cost、/agents、/bashes、/todos、/resume、/rewind、/export
- 符号命令（4个）：!、/、@、&
- 快捷键（8个）：Ctrl+C、Ctrl+D、Ctrl+L、Ctrl+R、Tab、↑/↓、Esc、Ctrl+Z
- 项目文件（2个）：CLAUDE.md、.claude/settings.json
- 每个命令包含：功能描述、使用方法

### 3.4 最佳实践指南

- 工具选择建议
- 权限模式选择建议
- 错误处理模式

## 4. 验收标准

- [x] 工具详解文档完整展示9个工具
- [x] 代理类型说明包含9种代理
- [x] 内置命令说明包含 CLI 启动命令(9个)、斜杠命令(24个)、符号命令(4个)、快捷键(8个)、项目文件(2个)
- [x] 最佳实践指南内容完整
- [x] 文档内容准确无误
- [x] 页面布局美观易读
