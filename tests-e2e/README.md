# Claude Code Runner - E2E Tests

使用 Playwright 进行端到端测试的测试套件。

## 前置条件

- Node.js 18+
- 后端服务运行在 http://127.0.0.1:8000

## 安装

```bash
cd tests-e2e
npm install
node node_modules/@playwright/test/cli.js install chromium
```

> 注意：如果 npm install 出现问题，可以手动下载包：
> ```bash
> npm pack @playwright/test typescript playwright playwright-core
> # 然后解压到 node_modules 目录
> ```

## 运行测试

```bash
# 运行所有测试
node node_modules/@playwright/test/cli.js test

# 运行特定测试文件
node node_modules/@playwright/test/cli.js test e2e/scheduler-tab-switching.spec.ts

# 运行测试并查看浏览器
node node_modules/@playwright/test/cli.js test --headed

# 调试模式
node node_modules/@playwright/test/cli.js test --debug

# 查看测试报告
node node_modules/@playwright/test/cli.js show-report
```

## 测试文件

| 文件 | 描述 |
|------|------|
| `scheduler-tab-switching.spec.ts` | 标签页切换测试 |
| `scheduler-dialog.spec.ts` | 对话框交互测试 |
| `scheduler-form-validation.spec.ts` | 表单验证测试 |
| `scheduler-api-integration.spec.ts` | API 集成测试 |
| `scheduler-error-handling.spec.ts` | 错误处理测试 |
| `scheduler-tools-selection.spec.ts` | 工具选择测试 |
| `scheduler-task-actions.spec.ts` | 任务操作测试 |
| `scheduler-task-detail.spec.ts` | 任务详情测试 |

## 测试覆盖

- 标签页切换（queue, scheduled, running, completed, failed）
- 对话框交互（添加任务、添加定时任务、Cron 帮助）
- 表单验证（必填字段、Cron 表达式验证）
- API 集成（获取调度器状态、任务列表）
- 错误处理（网络错误、验证错误提示）
- 工具选择（多选组件）
- 任务操作（删除、清空、启用/禁用、立即执行、重试）
- 任务详情（查看详情、折叠日志、复制日志）
