# Git 工作流

> 本文件定义项目的 Git 使用规范。

## 提交消息格式

### 结构

```
<type>: <description>

[optional body]
```

### 类型

| 类型 | 用途 | 示例 |
|------|------|------|
| feat | 新功能 | feat: 添加会话历史 API |
| fix | Bug 修复 | fix: 修复 SSE 流式输出断开问题 |
| refactor | 重构 | refactor: 提取客户端配置到独立类 |
| docs | 文档 | docs: 更新 API 文档 |
| test | 测试 | test: 添加 ClaudeCodeClient 单元测试 |
| chore | 杂项 | chore: 更新依赖版本 |
| perf | 性能 | perf: 优化会话列表查询性能 |

### 示例

```bash
# 好的提交消息
feat: 添加项目列表 API 端点

- 新增 GET /api/projects 接口
- 支持按会话数量排序
- 返回解码后的原始路径

# 简洁的提交消息
fix: 修复环境变量恢复逻辑
refactor: 使用 dataclass 替代普通类
test: 添加工具跟踪测试用例
```

## 分支策略

### 分支命名

```
main              # 主分支（生产）
master            # 主分支（当前）
feature/xxx       # 功能分支
fix/xxx           # 修复分支
refactor/xxx      # 重构分支
```

### 工作流程

```bash
# 1. 从 main 创建功能分支
git checkout -b feature/session-history

# 2. 开发并提交
git add src/claude_runner/client.py
git commit -m "feat: 添加会话历史功能"

# 3. 推送到远程
git push -u origin feature/session-history

# 4. 创建 Pull Request
gh pr create --title "feat: 添加会话历史功能" --body "..."

# 5. 合并后删除分支
git branch -d feature/session-history
```

## Pull Request 规范

### PR 标题格式

```
<type>: <description>

# 示例
feat: 添加 SSE 流式输出支持
fix: 修复文件路径解码错误
refactor: 重构客户端配置管理
```

### PR 描述模板

```markdown
## Summary
- 添加了 xxx 功能
- 修复了 xxx 问题
- 重构了 xxx 模块

## Changes
- `src/claude_runner/client.py`: 新增 run_stream 方法
- `app/main.py`: 添加 /api/task/stream 端点

## Test Plan
- [ ] 单元测试通过
- [ ] API 测试通过
- [ ] 手动测试流式输出
```

## 提交前检查

### 必须完成

```bash
# 1. 运行测试
uv run pytest tests/ -v

# 2. 检查覆盖率
uv run pytest tests/ --cov=src --cov=app

# 3. 检查代码风格
uv run ruff check src/ app/
```

### 检查清单

- [ ] 测试全部通过
- [ ] 覆盖率 ≥ 80%
- [ ] 无硬编码密钥
- [ ] 提交消息格式正确
- [ ] 无无关文件（.env、__pycache__ 等）

## 常用命令

```bash
# 查看状态
git status

# 查看差异
git diff
git diff main...HEAD

# 查看历史
git log --oneline -10

# 撤销未提交的更改
git restore <file>

# 撤销最近一次提交（保留更改）
git reset --soft HEAD~1

# 更新分支
git fetch origin
git rebase origin/main
```

## .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
.venv/
venv/

# 环境变量
.env
.env.local

# IDE
.vscode/
.idea/

# 构建产物
dist/
*.egg-info/

# 测试
.pytest_cache/
.coverage
htmlcov/
```
