# Claude Code Runner 竞品分析

## 1. 项目定位与愿景

### 定位
Claude Code Runner 是 Claude Code（Anthropic 官方 CLI）的 Web 服务封装，通过 REST API 和 Web 界面提供对 Claude Code 的编程访问能力。

### 愿景
让开发者能够通过 HTTP API 调用 Claude Code 执行编程任务，实现自动化、集成到现有系统、工作流编排等场景。

### 目标用户
- 开发者需要自动化编程任务
- 需要将 AI 编程能力集成到现有系统
- 需要定时执行代码任务
- 需要通过 Web 界面使用 Claude Code（非 CLI 用户）

---

## 2. 技术架构

### 编程语言与技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 服务器 | uvicorn |
| SDK | claude-agent-sdk |
| 数据验证 | Pydantic |
| 认证 | JWT + bcrypt |
| 限流 | slowapi |
| 任务调度 | APScheduler |
| 数据库 | 未持久化（运行时数据 JSON 文件） |
| 测试 | pytest + pytest-asyncio |
| 包管理 | uv |

### 系统架构

```
┌─────────────────────────────────────────────────┐
│                   FastAPI App                   │
│  app/main.py - 路由、请求处理、SSE 流式输出    │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│               ClaudeCodeClient                  │
│  app/claude_runner/client.py - SDK 封装核心     │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│               Claude Code CLI                    │
│  claude-code - Anthropic 官方工具               │
└─────────────────────────────────────────────────┘
```

### 核心模块

| 模块 | 职责 |
|------|------|
| `app/routers/task.py` | 任务执行（同步/流式） |
| `app/routers/session.py` | 会话管理 |
| `app/routers/auth.py` | 用户认证 |
| `app/routers/scheduler.py` | 定时任务 |
| `app/routers/mcp.py` | MCP 协议支持 |
| `app/routers/claude.py` | Claude 集成 |
| `app/routers/agents.py` | Agent 管理 |
| `app/routers/skills.py` | Skills 调用 |
| `app/claude_runner/client.py` | Claude Code SDK 封装 |
| `app/scheduler/` | 定时任务调度系统 |

---

## 3. 核心功能

### 主要功能

| 功能 | 说明 | 状态 |
|------|------|------|
| 任务执行 | 同步/流式执行 Claude Code 任务 | ✅ |
| 会话管理 | 历史会话记录、恢复、重命名 | ✅ |
| 定时任务 | Cron 表达式定时执行任务 | ✅ |
| MCP 协议 | Model Context Protocol 支持 | ✅ |
| 用户认证 | JWT + bcrypt 认证 | ✅ |
| Rate Limiting | 请求限流 | ✅ |
| Skills | 技能系统调用 | ✅ |
| Agent 管理 | 多 Agent 管理 | ✅ |
| API Keys | API 密钥管理 | ✅ |

### 差异化功能

1. **SSE 流式输出**：Server-Sent Events 实现实时任务进度
2. **嵌套环境变量管理**：处理 Claude Code 嵌套调用时的环境变量
3. **工具使用跟踪**：跟踪文件变更和工具使用
4. **定时任务安全验证**：完整的安全验证机制

---

## 4. 用户交互方式

| 方式 | 支持 | 说明 |
|------|------|------|
| REST API | ✅ | 主要交互方式 |
| Web 界面 | ✅ | 基础 Web UI |
| SSE 流式 | ✅ | 实时任务输出 |
| CLI | ❌ | 无 CLI |

### API 端点

```
POST   /api/task              # 执行任务（同步）
POST   /api/task/stream       # 执行任务（流式）
GET    /api/sessions         # 获取会话列表
POST   /api/sessions         # 创建会话
DELETE /api/sessions/{id}    # 删除会话
POST   /api/scheduler/tasks  # 创建定时任务
GET    /api/scheduler/tasks  # 获取定时任务列表
POST   /api/auth/login       # 用户登录
POST   /api/auth/register    # 用户注册
```

---

## 5. 扩展性

### 扩展机制

| 机制 | 说明 |
|------|------|
| MCP 协议 | 通过 MCP 协议扩展工具能力 |
| Skills | 技能系统，支持自定义技能 |
| Hooks | 钩子系统，扩展生命周期 |
| Plugins | 插件系统 |

### Skills 系统
- 位置：`app/skills/`
- 支持自定义技能
- 生命周期管理

---

## 6. 部署与运维

### 部署方式

| 方式 | 支持 |
|------|------|
| 直接运行 | ✅ `python -m app.main` |
| Docker | ✅ |
| systemd | 需自行配置 |

### 依赖要求

- Python ≥ 3.10
- claude-code CLI 已安装
- ANTHROPIC_API_KEY

### 运维复杂度

- **低**：单体服务，依赖少
- 无数据库依赖
- 运行时数据 JSON 文件存储

---

## 7. 安全模型

### 认证机制

| 机制 | 说明 |
|------|------|
| JWT Token | 用户认证 |
| bcrypt | 密码加密 |
| Rate Limiting | 请求限流 |

### 权限控制

- 用户级别权限
- API Key 管理
- 任务执行权限验证

### 安全验证

- 定时任务安全验证
- 输入验证
- 路径安全检查

---

## 8. 社区与生态

### 开源信息

| 项目 | 信息 |
|------|------|
| 许可证 | 未指定 |
| GitHub | claude-code-runner |
| 社区规模 | 较小 |

### 文档

- 基础 README
- 代码内文档
- API 设计规范

---

## 9. 优缺点分析

### 优势

1. **轻量级**：代码量适中，易于理解和维护
2. **专注**：聚焦于 API 封装，目标明确
3. **技术栈简洁**：FastAPI + Python，易于上手
4. **功能完整**：认证、限流、定时任务、MCP 等功能齐全

### 劣势

1. **非官方**：非 Anthropic 官方产品
2. **功能有限**：主要功能是任务执行，缺少高级特性
3. **无 UI**：Web 界面基础，功能有限
4. **无消息渠道**：不支持消息渠道集成
5. **扩展性有限**：相比 OpenClaw，扩展能力较弱

### 改进机会

1. 增加更多 API 端点（项目列表、文件管理等）
2. 完善 Web 界面
3. 支持更多消息渠道
4. 添加插件市场
5. 企业级功能（多租户、审计日志）

---

## 10. 商业模式

### 当前状态
- 开源免费
- 无明确商业模式

### 可能的商业方向
- 云服务托管
- 企业版（多租户、SSO）
- 技术支持服务

---

## 11. 调度系统

### 定时任务机制

基于 APScheduler 的完整调度系统：

| 模块 | 职责 |
|------|------|
| `scheduler.py` | 调度器主类 |
| `executor.py` | 任务执行器 |
| `executor_core.py` | 执行核心逻辑 |
| `executor_retry.py` | 重试机制 |
| `executor_errors.py` | 错误处理 |
| `cron.py` | Cron 表达式解析 |
| `cron_parser.py` | Cron 解析器 |
| `cron_validator.py` | Cron 验证器 |
| `cron_calculator.py` | Cron 计算工具 |
| `storage.py` | 存储抽象 |
| `storage_scheduled.py` | 定时任务存储 |
| `storage_queue.py` | 队列任务存储 |
| `storage_running.py` | 运行中任务存储 |
| `storage_history.py` | 历史记录存储 |
| `storage_cancelled.py` | 已取消任务存储 |
| `storage_logs.py` | 日志存储 |

### 功能特性

| 功能 | 说明 | 状态 |
|------|------|------|
| Cron 表达式 | 标准 5 字段 Cron | ✅ |
| 时区支持 | 时区感知调度 | ✅ |
| 持久化 | JSON 文件存储 | ✅ |
| 重试机制 | 失败自动重试 | ✅ |
| 任务队列 | 队列模式执行 | ✅ |
| 并发控制 | 防止任务冲突 | ✅ |
| 安全验证 | 输入安全检查 | ✅ |
| 执行日志 | 完整日志记录 | ✅ |
| 取消任务 | 支持取消 | ✅ |
| 手动触发 | 立即执行 | ✅ |

### 任务状态

- `scheduled` - 已调度
- `queued` - 队列中
- `running` - 运行中
- `completed` - 已完成
- `failed` - 失败
- `cancelled` - 已取消

### 安全机制

| 机制 | 说明 |
|------|------|
| `security_validators.py` | 输入验证器 |
| `security_utils.py` | 安全工具 |
| `security_constants.py` | 安全常量 |
| `security_exceptions.py` | 安全异常 |

---

## 12. 多项目/多工作区操作

### Agent 架构

Claude Code Runner **没有"主代理"的概念**，而是通过 prompt 配置灵活使用各种 agent：

| 概念 | 说明 |
|------|------|
| **Task** | 任务单元，可指定 workspace |
| **Agent** | 子代理，由 Task 创建和管理 |
| **AgentManager** | 管理子代理的生命周期 |

### 调度系统中的 Agent

```
Task (指定 workspace + prompt)
    │
    ├── 主执行 Agent (Task 创建)
    │
    └── 子代理 (通过 prompt 配置创建)
         │
         └── 每个子代理有独立的工作空间
```

### 项目级多 Agent 支持

| 功能 | 说明 | 状态 |
|------|------|------|
| 工作目录 | 每个任务可指定工作目录 | ✅ |
| 会话隔离 | 每个会话独立工作目录 | ✅ |
| 子代理 | 每个 Task 可创建多个子代理 | ✅ |
| 多 Agent 管理 | AgentManager 统一管理 | ✅ |
| 项目列表 | API 获取项目列表 | ❌ |
| 项目切换 | 动态切换工作目录 | ✅ |
| 项目配置 | 每个项目独立配置 | ✅ |

### 子代理功能 (AgentManager)

- 创建/获取/更新/终止代理
- 跟踪工具使用和文件变更
- 流式日志输出
- 状态管理（running/completed/terminated/failed）

### 当前实现

```
API 请求指定 working_dir:
{
  "prompt": "分析项目结构",
  "working_dir": "/path/to/project"
}

子代理在 Task 执行过程中通过 prompt 指令创建：
- "创建一个子代理来处理 X"
- 子代理有独立的状态跟踪
```

### 与 OpenClaw 对比

| 维度 | Claude Code Runner | OpenClaw |
|------|-------------------|----------|
| 主代理概念 | ❌ 无 | ✅ Gateway 主代理 |
| 子代理创建 | 通过 prompt 指令 | 通过 sessions_spawn 工具 |
| 子代理管理 | AgentManager | subagent-registry |
| Workspace | Task 级 | Agent 级 |

### 局限性

1. **无项目列表 API**：无法列出可用项目
2. **无项目切换命令**：需手动指定路径
3. **无资源配额**：不限制单个项目资源
4. **无项目隔离**：依赖文件系统隔离
5. **无项目元数据**：无项目配置存储

### 改进机会

1. 添加项目列表/创建/删除 API
2. 项目配置文件支持
3. 资源配额管理
4. 项目间数据隔离
5. 项目模板功能
