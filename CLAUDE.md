# CLAUDE.md

Claude Code Runner - Claude Code CLI 的 Web 服务封装，通过 FastAPI 提供 REST API 和 Web 界面。

## 常用命令

## 环境变量

当前版本混乱，需要调整。在对历史功能代码进行修改时，先看看是否已有相关内容的实现。

## 文档操作
有hook会阻止edit 和 write 操作文档。使用 MCP 对文档进行修改，使用 MCP 读取文档，使用 MCP 进行处理。


## 文档规范
编辑修改文档时触发规范，当文档超过500行时，将按照"功能-子功能"的命名规范自动拆分为多个独立文档，确保每个文档保持良好的可读性和可维护性。

## Skills

项目级 skills 路径: `.claude/skills`

### 使用 Skill 工具调用

使用 Skill 工具可以调用已配置的 skills：

```
/skill-name

任务描述
```

### 可用角色 Skills

| Skill | 用途 | 调用方式 |
|-------|------|----------|
| `senior-product-manager` | 高级产品经理 - 需求分析、产品设计 | `/senior-product-manager` |
| `director-product-management` | 产品总监 - 战略规划、任务分配、产出评审 | `/director-product-management` |
| `senior-architect` | 高级架构师 - 系统架构设计、技术方案评审 | `/senior-architect` |
| `senior-fullstack` | 全栈开发工程师 - 代码质量评审、功能实现 | `/senior-fullstack` |
| `tech-manager` | 技术经理 - 技术任务规划、代码实现与修复 | `/tech-manager` |



