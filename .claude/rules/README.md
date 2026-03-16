# Claude Code Runner - 项目规则

本目录包含项目专用的 Claude Code 规则，用于指导 AI 助手在此项目中工作。

## 规则文件

| 文件 | 用途 |
|------|------|
| `coding-style.md` | Python 编码风格、类型注解、命名约定 |
| `testing.md` | 测试策略、覆盖率要求、pytest 最佳实践 |
| `api-design.md` | REST API 设计规范、FastAPI 约定 |
| `security.md` | 安全要求、密钥管理、输入验证 |
| `patterns.md` | 设计模式、架构约定、项目结构 |
| `git-workflow.md` | Git 提交规范、分支策略、PR 流程 |
| `frontend-coding-style.md` | 前端编码风格（React 18 + TypeScript + Vite） |
| `frontend-testing.md` | 前端测试规范（Vitest + React Testing Library） |

## 前端项目

前端项目位于 `web2/` 目录，使用 CoPaw 技术栈：

- React 18.3.x + TypeScript 5.6.x
- Vite 6.x 构建工具
- React Router 7.x 路由管理
- Motion 动画库
- Lucide React 图标库

### 前端常用命令

```bash
# 进入前端目录
cd web2

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 代码格式检查
npm run format:check

# 代码格式化
npm run format
```

## 使用方式

这些规则会被 Claude Code 自动加载，在项目中工作时提供上下文指导。

### 规则优先级

1. 项目规则 (`.claude/rules/`) - 最高优先级
2. 用户全局规则 (`~/.claude/rules/`) - 补充规则
3. 默认行为 - 最低优先级

## 快速参考

### 常用命令

```bash
# 启动服务
uv run python -m app.main

# 运行测试
uv run pytest tests/ -v

# 测试覆盖率
uv run pytest tests/ --cov=src --cov=app
```

### 代码检查清单

- [ ] 类型注解完整
- [ ] 函数 < 50 行
- [ ] 文件 < 400 行
- [ ] 测试覆盖率 ≥ 80%
- [ ] 无硬编码密钥

### 提交消息格式

```
<type>: <description>

# 示例
feat: 添加会话历史 API
fix: 修复 SSE 断开问题
test: 添加客户端测试
```
