# Claude Code 安装与政策

本文档介绍 Claude Code 的安装方式和数据收集政策。

## 1. 安装方式

### 1.1 Mac/Linux

```bash
# 官方安装脚本（推荐）
curl -fsSL https://claude.ai/install.sh | bash

# Homebrew
brew install --cask claude-code
```

### 1.2 Windows

```powershell
# PowerShell（推荐）
irm https://claude.ai/install.ps1 | iex

# WinGet
winget install Anthropic.ClaudeCode
```

### 1.3 npm（已废弃）

```bash
# 不推荐，已废弃
npm install -g @anthropic-ai/claude-code
```

### 1.4 安装后使用

```bash
# 进入项目目录
cd your-project

# 启动 Claude Code
claude

# 或在 IDE 中使用
# VSCode: 安装 Claude Code 扩展
```

---

## 2. 数据收集和使用政策

Claude Code 会收集以下数据：

### 2.1 收集的数据类型

- **使用数据**：代码接受或拒绝情况
- **对话数据**：相关会话信息
- **用户反馈**：通过 `/bug` 命令提交的内容

### 2.2 数据使用政策

- 用于改进 Claude Code 产品
- **不会**将用户反馈用于模型训练
- 限制敏感信息保留期限
- 限制用户会话数据访问权限

### 2.3 隐私保护

- 实施数据保留限制
- 限制敏感信息访问
- 明确政策：不用于模型训练

---

## 3. 相关政策链接

- [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms)
- [Privacy Policy](https://www.anthropic.com/legal/privacy)
- [Data Usage Policies](https://code.claude.com/docs/en/data-usage)
