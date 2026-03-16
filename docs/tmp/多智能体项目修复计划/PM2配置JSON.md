# PM2配置JSON

> 完整的PM2任务配置JSON，可直接复制到 `~/.claude/scheduler/scheduled-tasks.json`

---

## 配置说明

将这些任务添加到PM2配置文件中，然后启动PM2即可自动执行。

**配置文件位置**:
- Windows: `C:\Users\Administrator\.claude\scheduler\scheduled-tasks.json`
- Linux/Mac: `~/.claude/scheduler/scheduled-tasks.json`

---

## 完整配置JSON

```json
[
  {
    "id": "claude-runner-phase1-1",
    "name": "阶段1-产品经理执行需求梳理",
    "prompt": "/产品经理 执行阶段1需求梳理。任务：根据 docs/plan/功能规划/ 开发计划 和 docs/需求文档/ 的内容，梳理项目需求。要求：\n1. 阅读所有需求文档\n2. 识别已实现、未实现、部分实现的功能\n3. 整理成统一的需求清单\n4. 输出到 docs/tmp/需求梳理-执行日志.md\n5. 全程不与用户沟通，用户不在线",
    "workspace": "E:\\workspaces_2026_python\\claude-code-runner",
    "timeout": 1200000,
    "enabled": true,
    "autoApprove": true,
    "allowedTools": null,
    "cron": "0/20 0 * * *",
    "createdAt": "2026-03-04 00:00:00"
  },
  {
    "id": "claude-runner-phase1-2",
    "name": "阶段1-产品总监评审需求梳理",
    "prompt": "/产品总监 评审阶段1需求梳理。任务：\n1. 阅读 docs/tmp/需求梳理-执行日志.md\n2. 检查需求梳理的完整性和准确性\n3. 检查需求与设计文档的对应关系\n4. 给出评审意见（通过/需修改/拒绝）\n5. 输出到 docs/tmp/需求梳理-评审报告.md\n6. 全程不与用户沟通，用户不在线",
    "workspace": "E:\\workspaces_2026_python\\claude-code-runner",
    "timeout": 1200000,
    "enabled": true,
    "autoApprove": true,
    "allowedTools": null,
    "cron": "10/20 0 * * *",
    "createdAt": "2026-03-04 00:10:00"
  },
  {
    "id": "claude-runner-phase2-1",
    "name": "阶段2-技术经理执行代码设计",
    "prompt": "/技术经理 执行阶段2代码设计。任务：\n1. 根据阶段1输出的需求清单，检查 docs/技术设计/ 文档\n2. 识别缺失的技术设计文档\n3. 检查现有设计文档与需求的对应关系\n4. 补充缺失的设计内容\n5. 输出到 docs/tmp/代码设计-执行日志.md\n6. 全程不与用户沟通，用户不在线",
    "workspace": "E:\\workspaces_2026_python\\claude-code-runner",
    "timeout": 1200000,
    "enabled": true,
    "autoApprove": true,
    "allowedTools": null,
    "cron": "0/20 1 * * *",
    "createdAt": "2026-03-04 01:00:00"
  },
  {
    "id": "claude-runner-phase2-2",
    "name": "阶段2-高级架构师评审代码设计",
    "prompt": "/高级架构师 评审阶段2代码设计。任务：\n1. 阅读 docs/tmp/代码设计-执行日志.md\n2. 检查技术设计的完整性和合理性\n3. 检查设计方案的可实施性\n4. 检查API设计符合RESTful规范\n5. 给出评审意见（通过/需修改/拒绝）\n6. 输出到 docs/tmp/代码设计-评审报告.md\n7. 全程不与用户沟通，用户不在线",
    "workspace": "E:\\workspaces_2026_python\\claude-code-runner",
    "timeout": 1200000,
    "enabled": true,
    "autoApprove": true,
    "allowedTools": null,
    "cron": "10/20 1 * * *",
    "createdAt": "2026-03-04 01:10:00"
  },
  {
    "id": "claude-runner-phase3-1",
    "name": "阶段3-技术经理执行代码修复",
    "prompt": "/技术经理 执行阶段3代码修复。任务：\n1. 根据需求文档和技术设计，检查 app/ 目录下的代码\n2. 识别缺失的功能实现\n3. 修复SDK版本混乱导致的代码问题\n4. 补充缺失的业务逻辑\n5. 确保代码符合 .claude/rules/ 中的编码规范\n6. 输出到 docs/tmp/代码修复-执行日志.md\n7. 全程不与用户沟通，用户不在线",
    "workspace": "E:\\workspaces_2026_python\\claude-code-runner",
    "timeout": 1200000,
    "enabled": true,
    "autoApprove": true,
    "allowedTools": null,
    "cron": "0/20 2-4 * * *",
    "createdAt": "2026-03-04 02:00:00"
  },
  {
    "id": "claude-runner-phase3-2",
    "name": "阶段3-高级全栈工程师评审代码修复",
    "prompt": "/高级全栈工程师 评审阶段3代码修复。任务：\n1. 阅读 docs/tmp/代码修复-执行日志.md\n2. 检查代码修复的完整性\n3. 运行测试确保功能正常\n4. 检查代码质量和规范\n5. 给出评审意见（通过/需修改/拒绝）\n6. 输出到 docs/tmp/代码修复-评审报告.md\n7. 全程不与用户沟通，用户不在线",
    "workspace": "E:\\workspaces_2026_python\\claude-code-runner",
    "timeout": 1200000,
    "enabled": true,
    "autoApprove": true,
    "allowedTools": null,
    "cron": "10/20 2-4 * * *",
    "createdAt": "2026-03-04 02:10:00"
  }
]
```

---

## 配置参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `id` | 任务唯一标识 | `claude-runner-phase1-1` |
| `name` | 任务名称 | `阶段1-产品经理执行需求梳理` |
| `prompt` | 角色调用提示词 | `/产品经理 执行...` |
| `workspace` | 工作目录路径 | `E:\\workspaces_2026_python\\claude-code-runner` |
| `timeout` | 超时时间（毫秒） | `1200000` (20分钟) |
| `enabled` | 是否启用 | `true` |
| `autoApprove` | 是否自动批准 | `true` |
| `allowedTools` | 允许的工具 | `null` (全部允许) |
| `cron` | Cron表达式 | `0/20 0 * * *` |
| `createdAt` | 创建时间 | `2026-03-04 00:00:00` |

---

## Cron表达式说明

| Cron表达式 | 含义 |
|-----------|------|
| `0/20 0 * * *` | 第0小时，每20分钟执行一次（00:00, 00:20, 00:40） |
| `10/20 0 * * *` | 第0小时，从第10分钟开始每20分钟执行一次（00:10, 00:30, 00:50） |
| `0/20 1 * * *` | 第1小时，每20分钟执行一次（01:00, 01:20, 01:40） |
| `10/20 1 * * *` | 第1小时，从第10分钟开始每20分钟执行一次（01:10, 01:30, 01:50） |
| `0/20 2-4 * * *` | 第2-4小时，每20分钟执行一次 |
| `10/20 2-4 * * *` | 第2-4小时，从第10分钟开始每20分钟执行一次 |

---

## 安装步骤

### 步骤1：备份现有配置

```bash
# 备份当前配置
cp ~/.claude/scheduler/scheduled-tasks.json ~/.claude/scheduler/scheduled-tasks.json.backup
```

### 步骤2：编辑配置文件

```bash
# 使用文本编辑器打开配置文件
notepad ~/.claude/scheduler/scheduled-tasks.json

# 或使用vim/nano
vim ~/.claude/scheduler/scheduled-tasks.json
```

### 步骤3：粘贴配置

将上面的JSON数组粘贴到文件中，确保JSON格式正确。

### 步骤4：验证配置

```bash
# 查看配置列表
/scheduler:schedule-list
```

### 步骤5：启动执行

```bash
# PM2会自动根据cron表达式执行任务
# 可以查看执行状态
/scheduler:schedule-status

# 查看执行日志
/scheduler:schedule-logs
```

---

## 执行监控

### 查看任务列表

```bash
/scheduler:schedule-list
```

输出示例：
```
ID  | 名称                     | 状态    | 下次执行
----|--------------------------|----------|----------
... | ...                     | ...      | ...
```

### 查看执行日志

```bash
/scheduler:schedule-logs
```

输出示例：
```
任务ID: claude-runner-phase1-1
执行时间: 2026-03-04 00:00:00
执行状态: 成功
输出内容: ...
```

### 手动触发执行

```bash
# 手动触发特定任务
/scheduler:schedule-run claude-runner-phase1-1
```

---

## 调整时间

如果需要调整执行时间，修改 `cron` 表达式和 `createdAt` 字段。

**示例：推迟到明天早上8点开始**

```json
{
  "cron": "0/20 8 * * *",
  "createdAt": "2026-03-05 08:00:00"
}
```

---

## 停止执行

如需停止执行，将 `enabled` 字段设置为 `false`：

```json
{
  "enabled": false
}
```

---

## 故障排查

### 任务未执行

1. 检查 `enabled` 是否为 `true`
2. 检查 `cron` 表达式是否正确
3. 检查 `workspace` 路径是否存在
4. 查看 `/scheduler:schedule-logs` 了解错误

### 执行时间不对

1. 检查系统时区设置
2. 检查 `cron` 表达式的小时数

---

*文档版本：1.0*
*创建时间：2026-03-04*
