# Claude Code 内置命令

Claude Code 提供内置的斜杠命令，方便用户快速执行常用操作。

## 1. CLI 启动命令（终端执行）

| 命令 | 说明 |
|------|------|
| `claude` | 启动交互式会话 |
| `claude "问题"` | 带初始问题直接启动 |
| `claude -c` | 继续上次对话 |
| `claude --version` | 查看版本号 |
| `claude update` | 更新客户端 |
| `claude doctor` | 诊断安装环境/检查依赖 |
| `claude mcp` | 启动 MCP 向导 |
| `claude login` | 登录 Anthropic 账户 |
| `claude logout` | 登出账户 |

---

## 2. 斜杠命令（交互会话中使用）

| 命令 | 说明 |
|------|------|
| `/help` | 查看帮助列表 |
| `/config` | 配置设置（语言、模型、主题等） |
| `/model` | 切换 AI 模型 |
| `/memory` | 管理全局记忆（CLAUDE.md） |
| `/init` | 初始化项目，生成 CLAUDE.md |
| `/clear` | 清除当前对话上下文（别名：`/reset`, `/new`） |
| `/compact` | 压缩会话内容，节省 tokens |
| `/exit` | 退出 Claude Code |
| `/bug` | 向 Anthropic 报告 Bug |
| `/doctor` | 诊断问题 |
| `/usage` | 查看用量统计 |
| `/stats` | 查看统计信息 |
| `/permissions` | 管理权限设置 |
| `/terminal-setup` | 终端设置优化 |
| `/add-dir` | 添加额外工作目录 |
| `/context` | 查看上下文信息 |
| `/cost` | 查看成本/Token 消耗 |
| `/agents` | 管理 Agent 任务 |
| `/bashes` | 管理 Bash 任务 |
| `/todos` | 管理待办事项 |
| `/resume` | 恢复之前的会话 |
| `/rewind` | 回退到之前的 checkpoint（别名：`/checkpoint`） |
| `/export` | 导出会话内容 |

---

## 3. 符号命令

| 符号 | 说明 |
|------|------|
| `!` | Bash 模式（执行 shell 命令） |
| `/` | 命令模式（调用斜杠命令） |
| `@` | 引用文件路径 |
| `&` | 后台运行 |

---

## 4. 常用快捷键

| 快捷键 | 说明 |
|--------|------|
| `Ctrl+C` | 中断当前操作 |
| `Ctrl+D` | 退出会话 |
| `Ctrl+L` | 清屏 |
| `Ctrl+R` | 搜索历史命令 |
| `Tab` | 自动补全 |
| `↑/↓` | 浏览历史命令 |
| `Esc` | 取消当前输入 |
| `Ctrl+Z` | 挂起会话 |

---

## 5. 项目文件

| 文件 | 说明 |
|------|------|
| `CLAUDE.md` | 项目记忆文件，存储项目上下文、约定和常用命令 |
| `.claude/settings.json` | 用户配置文件 |

---

## 6. 使用小贴士

1. **首次使用**：运行 `claude doctor` 检查环境，然后 `claude init` 初始化项目
2. **节省 Token**：定期使用 `/compact` 压缩上下文
3. **多目录支持**：用 `/add-dir` 添加多个工作目录
4. **会话恢复**：用 `/resume` 或 `claude -c` 继续之前的工作
5. **权限管理**：通过 `/permissions` 控制 Claude 的操作权限
