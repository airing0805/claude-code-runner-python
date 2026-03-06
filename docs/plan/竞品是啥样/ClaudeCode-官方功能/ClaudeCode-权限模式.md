# Claude Code 权限模式

Claude Code 提供四种权限模式来控制工具执行行为。

## 权限模式概览

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **default** | 默认模式，每次工具调用需要用户确认 | 安全性要求高的场景 |
| **acceptEdits** | 自动接受编辑操作（Write/Edit），其他操作仍需确认 | 日常开发 |
| **plan** | 规划模式，先生成计划，用户批准后执行 | 复杂任务需要规划 |
| **bypassPermissions** | 跳过所有权限检查，完全自动化 | 无人值守自动化 |

---

## 1. default 模式

默认权限模式，每次工具调用都会请求用户确认。

```python
options = ClaudeCodeOptions(
    permission_mode="default",
    cwd="/path/to/project"
)
```

**行为**：
- 每次工具调用前暂停
- 等待用户 approve/deny
- 可设置允许的工具列表限制

---

## 2. acceptEdits 模式

自动接受文件编辑操作，其他操作仍需确认。

```python
options = ClaudeCodeOptions(
    permission_mode="acceptEdits",
    cwd="/path/to/project"
)
```

**行为**：
- Write/Edit 工具自动执行
- Bash/删除等敏感操作仍需确认
- 适合日常开发工作流

---

## 3. plan 模式

规划模式，先输出执行计划，用户批准后再执行。

```python
options = ClaudeCodeOptions(
    permission_mode="plan",
    cwd="/path/to/project"
)
```

**行为**：
- Claude 先分析任务并生成执行计划
- 显示将要执行的操作列表
- 用户批准后才开始执行
- 适合重要或不可逆的操作

---

## 4. bypassPermissions 模式

完全自动化，跳过所有权限检查。

```python
options = ClaudeCodeOptions(
    permission_mode="bypassPermissions",
    cwd="/path/to/project"
)
```

**行为**：
- 所有工具调用自动执行
- 无需任何用户交互
- 适合 CI/CD、无人值守任务
- **注意**：存在风险，请确保输入可信

---

## 权限模式选择指南

| 场景 | 推荐模式 |
|------|---------|
| 交互式开发 | `acceptEdits` |
| 审查/分析任务 | `default` |
| 复杂重构 | `plan` |
| CI/CD 自动化 | `bypassPermissions` |
