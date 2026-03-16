# OpenClaw 竞品分析

## 1. 项目定位与愿景

### 定位
OpenClaw 是一个多渠道个人 AI 助手网关（Multi-channel AI gateway），让你可以在已有的通讯工具上与 AI 助手对话。

### 愿景
打造一个本地化、快速、始终在线的个人 AI 助手，通过用户已经使用的渠道（WhatsApp、Telegram、Slack 等）提供服务。

### 目标用户
- 普通用户想要个人 AI 助手
- 需要通过多种消息渠道访问 AI
- 重视隐私和数据本地化
- 需要语音交互能力

---

## 2. 技术架构

### 编程语言与技术栈

| 组件 | 技术 |
|------|------|
| 编程语言 | TypeScript (ESM) |
| 运行时 | Node.js 22+ |
| 包管理 | pnpm |
| 构建工具 | tsup / tsdown |
| 测试框架 | vitest |
| 格式化/检查 | Oxlint + Oxfmt |
| Web 服务器 | 原生 Node.js |
| 认证 | OAuth + API Key |

### 系统架构

```
┌─────────────────────────────────────────────────┐
│              Gateway (控制平面)                  │
│  - 会话管理 (sessions)                          │
│  - 渠道路由 (routing)                          │
│  - 配置管理 (config)                            │
│  - 定时任务 (cron)                             │
│  - Webhooks                                    │
└──────────────┬──────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┬─────────────┐
    ▼          ▼          ▼          ▼             ▼
  Telegram   Discord   Slack    WhatsApp      [更多]
    │          │          │          │             │
    └──────────┴─────┬────┴──────────┴─────────────┘
                     ▼
            ┌─────────────────┐
            │  Agent 运行时    │
            │  (Pi agent)     │
            └────────┬────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
     Skills      Tools        Media
```

### 核心模块

| 模块 | 职责 |
|------|------|
| `src/agents/` | Agent 运行时、工具执行 |
| `src/gateway/` | Gateway 控制平面 |
| `src/sessions/` | 会话管理 |
| `src/routing/` | 消息路由 |
| `src/channels/` | 内置消息渠道 |
| `src/plugins/` | 插件系统 |
| `src/plugin-sdk/` | 插件 SDK |
| `src/media/` | 媒体处理管道 |
| `src/cli/` | CLI 接口 |
| `extensions/` | 第三方扩展 |

---

## 3. 核心功能

### 消息渠道（20+）

| 渠道 | 类型 | 状态 |
|------|------|------|
| WhatsApp | 官方 | 内置 |
| Telegram | 官方 | 内置 |
| Discord | 官方 | 内置 |
| Slack | 官方 | 内置 |
| Signal | 官方 | 内置 |
| iMessage (BlueBubbles) | 官方 | 内置 |
| IRC | 官方 | 内置 |
| Microsoft Teams | 官方 | 内置 |
| Matrix | 官方 | 内置 |
| Feishu (飞书) | 官方 | 内置 |
| LINE | 官方 | 内置 |
| Mattermost | 官方 | 内置 |
| Nextcloud Talk | 官方 | 内置 |
| Nostr | 官方 | 内置 |
| Synology Chat | 官方 | 内置 |
| Twitch | 官方 | 内置 |
| Zalo | 官方 | 内置 |
| WebChat | 官方 | 内置 |
| macOS | 官方 | 内置 |
| iOS/Android | 官方 | 内置 |

### 核心功能

| 功能 | 说明 | 状态 |
|------|------|------|
| 多渠道消息 | 20+ 消息渠道集成 | ✅ |
| 多代理路由 | 消息路由到隔离的 Agent | ✅ |
| Live Canvas | 代理驱动的可视化工作空间 | ✅ |
| Voice Wake | macOS/iOS 语音唤醒 | ✅ |
| Talk Mode | Android 持续语音对话 | ✅ |
| 设备配对 | 移动端配对机制 | ✅ |
| 插件系统 | Plugin SDK 完整支持 | ✅ |
| Skills | 预置技能系统 | ✅ |
| Cron 定时任务 | 定时执行任务 | ✅ |
| 媒体处理 | 图片/音频/视频处理 | ✅ |
| OAuth 认证 | 模型认证 | ✅ |
| API Key 轮换 | 密钥轮换 | ✅ |

---

## 4. 用户交互方式

| 方式 | 支持 | 说明 |
|------|------|------|
| WhatsApp | ✅ | 官方集成 |
| Telegram | ✅ | 官方集成 |
| Discord | ✅ | 官方集成 |
| Slack | ✅ | 官方集成 |
| Signal | ✅ | 官方集成 |
| iMessage | ✅ | 通过 BlueBubbles |
| LINE | ✅ | 官方集成 |
| Web | ✅ | Web UI |
| CLI | ✅ | 完整 CLI |
| 语音 (macOS) | ✅ | Voice Wake |
| 语音 (iOS) | ✅ | Voice Wake |
| 语音 (Android) | ✅ | Talk Mode |

### CLI 命令

```bash
openclaw onboard              # 向导安装
openclaw gateway run         # 运行 Gateway
openclaw agent               # 与 Agent 对话
openclaw message send        # 发送消息
openclaw pairing approve     # 配对审批
openclaw config set          # 配置管理
openclaw doctor              # 诊断检查
openclaw update              # 更新
```

### Web API

```
WebSocket: ws://gateway:18789/gateway
REST API: http://gateway:18789/
```

---

## 5. 扩展性

### 插件系统

| 扩展类型 | 示例 |
|----------|------|
| 消息渠道 | `extensions/msteams`, `extensions/matrix` |
| AI 提供商 | `extensions/gemini`, `extensions/llm-task` |
| 技能 | `extensions/github`, `extensions/coding-agent` |
| 记忆 | `extensions/memory-core`, `extensions/memory-lancedb` |
| 工具 | `extensions/diffs`, `extensions/blucli` |

### Plugin SDK

```typescript
// 插件结构
extensions/
└── my-extension/
    ├── package.json
    ├── src/
    │   └── channel.ts    # 渠道实现
    └── dist/
```

### Skills

预置 Skills（20+）：
- `coding-agent` - 编程代理
- `github` - GitHub 集成
- `canvas` - Canvas 集成
- `discord` - Discord 工具
- `1password` - 密码管理
- 等等...

---

## 6. 部署与运维

### 部署方式

| 方式 | 支持 | 说明 |
|------|------|------|
| 本地运行 | ✅ | 推荐方式 |
| Docker | ✅ | docker-compose |
| Podman | ✅ | podman-compose |
| systemd | ✅ | 用户服务 |
| macOS LaunchD | ✅ | 桌面端 |

### 依赖要求

- Node.js ≥ 22
- pnpm / npm / bun
- 消息渠道对应的机器人账号

### 运维复杂度

- **高**：多服务架构
- 需要配置多个消息渠道
- 需要管理 OAuth 认证
- 需要管理代理运行

### Docker 支持

```bash
docker-compose up -d
```

提供多个 Dockerfile：
- `Dockerfile` - 主服务
- `Dockerfile.sandbox` - 沙箱环境
- `Dockerfile.sandbox-browser` - 浏览器沙箱
- `Dockerfile.sandbox-common` - 共享依赖

---

## 7. 安全模型

### 认证机制

| 机制 | 说明 |
|------|------|
| OAuth | 模型认证（OpenAI 等） |
| API Key | 直接 API 密钥认证 |
| Auth Profiles | 认证配置轮换 |
| 密钥轮换 | 自动过期和刷新 |

### 安全策略

| 策略 | 说明 |
|------|------|
| DM Pairing | 未知发送者需要配对码 |
| Allowlist | 白名单机制 |
| DM Policy | 可配置 DM 策略（open/pairing） |
| 敏感数据 | 本地存储，不上传 |

### DM 安全策略

```yaml
# 配对模式（默认）
channels.discord.dmPolicy: "pairing"

# 开放模式
channels.discord.dmPolicy: "open"
channels.discord.allowFrom:
  - "*"  # 允许所有人
```

---

## 8. 社区与生态

### 开源信息

| 项目 | 信息 |
|------|------|
| 许可证 | MIT |
| GitHub | openclaw/openclaw |
| Star | 18k+ |
| Forks | 1k+ |
| 贡献者 | 100+ |

### 文档

- 完整的 Mintlify 文档站点
- API 参考
- 渠道配置指南
- 安全指南
- 开发指南

### 社区

- Discord 社区
- GitHub Issues
- Release Channels: stable/beta/dev

---

## 9. 优缺点分析

### 优势

1. **功能全面**：20+ 消息渠道、语音、Canvas、插件系统
2. **多平台支持**：macOS/iOS/Android 客户端
3. **本地化**：数据存储在本地，隐私保护
4. **开源免费**：MIT 许可证
5. **活跃社区**：18k+ stars，活跃开发
6. **完整文档**：Mintlify 托管文档
7. **插件生态**：Plugin SDK + 20+ 官方扩展

### 劣势

1. **复杂度高**：架构复杂，学习曲线陡峭
2. **部署困难**：需要配置多个渠道
3. **资源消耗**：需要运行多个服务
4. **维护成本**：需要管理多个机器人账号
5. **非官方**：非 Anthropic 官方产品

### 改进机会

1. 简化部署流程
2. 增加云托管选项
3. 一键安装脚本
4. 更完善的监控

---

## 10. 商业模式

### 当前状态
- 开源免费（MIT 许可证）
- 接受赞助

### 可能的商业方向
- 云托管服务
- 企业版（SSO、审计）
- 技术支持服务
- 优先支持某些渠道

---

## 11. 调度系统

### 定时任务机制

OpenClaw 有内置的 Cron 调度系统，位于 `src/cron/`：

| 模块 | 职责 |
|------|------|
| `schedule.ts` | 调度定义 |
| `delivery.ts` | 投递逻辑 |
| `normalize.ts` | 消息标准化 |
| `run-log.ts` | 运行日志 |
| `service/` | 调度服务 |
| `isolated-agent/` | 隔离代理 |
| `session-reaper.ts` | 会话清理 |

### 功能特性

| 功能 | 说明 | 状态 |
|------|------|------|
| Cron 表达式 | 标准 Cron | ✅ |
| Every 语法 | `every 5 minutes` | ✅ |
| 心跳机制 | 任务心跳检测 | ✅ |
| 失败告警 | 任务失败通知 | ✅ |
| 消息投递 | 支持多渠道投递 | ✅ |
| 隔离代理 | 隔离的代理环境 | ✅ |
| 会话清理 | 自动清理会话 | ✅ |
| 重试机制 | 失败自动重试 | ✅ |
| 时区支持 | 时区感知 | ✅ |

### 调度配置示例

```yaml
# 在配置文件中定义
cron:
  - name: "daily-report"
    schedule: "0 9 * * *"  # 每天 9 点
    message: "生成每日报告"
    channels:
      - telegram
```

### 与 Claude Code Runner 对比

| 维度 | Claude Code Runner | OpenClaw |
|------|-------------------|----------|
| 实现方式 | APScheduler | 内置 Cron 服务 |
| 功能完整性 | 更完善 | 基础 |
| 安全验证 | 完整安全验证 | 依赖配置 |
| 持久化 | JSON 文件 | 本地存储 |
| 重试机制 | 完善 | 基础 |

---

## 12. 多项目/多工作区操作

### Agent 架构

OpenClaw 有明确的 **Gateway 主代理** 概念：

| 概念 | 说明 |
|------|------|
| **Gateway 主代理** | 处理所有入站消息的中央代理 |
| **Agent** | 独立的 AI 代理实例，可配置多个 |
| **Workspace** | 代理的工作目录 |
| **Session** | 对话会话 |
| **Scope** | 代理的作用域隔离 |
| **Subagent** | 主代理创建的子代理 |

### Gateway 主代理

OpenClaw 的 Gateway 是整个系统的控制平面，所有消息首先到达 Gateway 主代理：

```
用户消息 → Gateway → 路由到对应 Agent → 处理
```

### Workspace 内多 Agent 支持

**是的，OpenClaw 的 Workspace 内支持多 Agent！**

通过 `sessions_spawn` 工具，主代理可以创建子代理（subagent）：

```typescript
// sessions_spawn 工具参数
{
  task: "任务描述",
  runtime: "subagent" | "acp",  // 子代理运行时
  agentId: "指定代理ID",
  model: "模型覆盖",
  cwd: "工作目录",
  mode: "run" | "session",  // 一次性或持续
  cleanup: "delete" | "keep"  // 完成后是否删除
}
```

### 子代理架构

| 模块 | 职责 |
|------|------|
| `subagent-registry.ts` | 子代理注册表 |
| `subagent-spawn.ts` | 子代理创建逻辑 |
| `subagent-registry-state.ts` | 子代理状态管理 |
| `subagent-announce.ts` | 子代理公告/通知 |
| `subagent-depth.ts` | 子代理深度限制 |

### 功能特性

| 功能 | 说明 | 状态 |
|------|------|------|
| Gateway 主代理 | 中央消息处理代理 | ✅ |
| 多代理 | 支持多个独立代理（配置多个） | ✅ |
| 子代理 | 主代理创建的子代理 | ✅ |
| 工作区隔离 | 每个代理独立工作区 | ✅ |
| 会话管理 | 完整会话管理 | ✅ |
| 消息路由 | 消息路由到代理 | ✅ |
| 配置覆盖 | 每个代理独立配置 | ✅ |
| 资源配额 | 可配置资源限制 | ✅ |
| 模型覆盖 | 每个代理可指定模型 | ✅ |

### 路由配置

```yaml
# 消息路由到不同代理
gateway:
  agents:
    - id: "coding-agent"
      workspace: "/workspace/coding"
      model: "claude-sonnet"
    - id: "general-agent"
      workspace: "/workspace/general"
      model: "claude-haiku"

# 渠道路由
channels:
  telegram:
    agent: "coding-agent"  # 编程问题路由到 coding-agent
  discord:
    agent: "general-agent"
```

### 多 Agent 协同机制

#### 每个 Agent 有独立 Workspace

- 通过配置文件定义，每个 agent 有自己的 workspace 目录
- `resolveAgentWorkspaceDir(cfg, agentId)` 根据 agentId 解析对应的 workspace

#### Subagent 协同模式

```
Gateway
    │
    ├── Agent A (workspace: /workspace/a)
    │    └── Subagent (默认) → /workspace/a
    │    └── Subagent (agentId: "agent-b") → /workspace/b (跨workspace!)
    │
    └── Agent B (workspace: /workspace/b)
```

#### 跨 Workspace 机制

通过 `sessions_spawn` 工具的 `agentId` 参数，subagent 可以使用不同 agent 的 workspace：

```typescript
// 跨 workspace 创建子代理
{
  task: "任务描述",
  agentId: "coding-agent",  // 指定不同的 agent，使用其 workspace
}
```

#### Workspace 隔离

- **同一 Workspace 内**：主代理和子代理共享同一个 workspace
- **跨 Workspace**：通过指定不同的 `agentId`，subagent 可以使用另一个 agent 的 workspace

### 与 Claude Code Runner 对比

| 维度 | Claude Code Runner | OpenClaw |
|------|-------------------|----------|
| 主代理概念 | ❌ 无 | ✅ Gateway 主代理 |
| 子代理创建 | 通过 prompt 指令 | 通过 sessions_spawn 工具 |
| 子代理管理 | AgentManager | subagent-registry |
| Workspace | Task 级 | Agent 级 |
| 多代理配置 | 通过 Task 每次指定 | 配置文件预定义 |
| 子代理深度 | prompt 指令控制 | subagent-depth 限制 |
| 跨 Workspace | ❌ | ✅ 通过 agentId 参数 |

### 架构差异总结

**Claude Code Runner**:
```
Task → 主执行 Agent → 子代理 (通过 prompt 创建)
       ↑
   无主代理概念，Task 即是入口
```

**OpenClaw**:
```
Gateway (主代理) → Agent → Subagent (通过 sessions_spawn 创建)
     ↑
  所有消息的中央入口
```

### OpenClaw 优势

1. **Gateway 主代理**：统一的入口，处理所有消息
2. **完整的多代理架构**：配置文件预定义多个代理
3. **Workspace 内多 Agent**：通过 sessions_spawn 支持
4. **跨 Workspace 协同**：通过 agentId 参数指定不同 workspace
5. **工作区隔离**：完整的作用域隔离
6. **消息路由**：根据渠道/用户自动路由

---

## 13. 系统级 vs 项目级：多Agent协同的定位差异

### 核心认知

| 维度 | OpenClaw (系统级) | Claude Code Runner (项目级) |
|------|-------------------|---------------------------|
| **定位** | 多渠道消息网关 | 项目开发任务执行引擎 |
| **Agent 作用** | 处理用户对话、执行后台任务 | 需求分析、技术设计、代码实现、评审 |
| **工作区** | 每个 Agent 独立 Workspace | Task 级，每个任务可指定不同目录 |
| **触发方式** | 消息对话、Slash 命令、Cron | API 调用、Web 界面、定时任务 |
| **典型场景** | "帮我查天气"、"每天提醒" | "实现用户登录"、"重构订单模块" |
| **持续性** | ❌ 任务式，一次性 | ✅ 项目持续迭代 |

### OpenClaw - 系统级多Agent协同

**特点**：
- 面向**离散任务**，每次交互独立完成
- 无状态或短状态
- 输出为对话/响应
- 不维护项目文件结构
- 适合个人助手、自动化场景

**典型流程**：
```
用户消息 → Gateway → Agent → 响应
         → sessions_spawn → Subagent → 响应
```

**不擅长的场景**：
- 持续迭代的项目开发
- 多阶段评审流程
- 长期维护的代码库
- 文档+代码的完整产出

### Claude Code Runner - 项目级Agent协同

**特点**：
- 面向**持续项目**，长期维护
- 完整的任务状态管理
- 输出为文档+代码
- 完整的项目目录结构
- 支持多阶段评审流转

**核心能力**：

| 能力 | 说明 |
|------|------|
| **任务调度** | APScheduler 定时任务，持续触发 |
| **会话管理** | 完整会话历史，跨任务保持上下文 |
| **项目目录** | 每个项目独立目录，长期维护代码 |
| **Workflow** | 任务状态管理，支持评审修订循环 |
| **多角色协同** | 产品总监→产品经理→技术经理→开发 |

**典型流程**：
```
用户 → 任务管理器 → 产品规划阶段
                       ↓
                   技术设计阶段
                       ↓
                   开发执行阶段
                       ↓
                   质量审核阶段
                       ↓
                   完成（持续迭代）
```

### 评审机制对比

| 机制 | OpenClaw | Claude Code Runner |
|------|----------|-------------------|
| **评审定义** | 需要自己实现 | 内置通过/需修改/拒绝 |
| **修订循环** | 手动处理 | 自动触发修订 |
| **状态追踪** | 无专门管理 | 任务状态管理 |
| **Skill 调用** | 通过 prompt | 专门的 /产品总监 /产品经理 |

### Workspace 目录结构对比

**OpenClaw 多Agent项目结构**：
```
~/.openclaw/
├── workspace-product-director/     # 产品总监
│   └── docs/
├── workspace-product-manager/     # 产品经理
│   └── docs/
├── workspace-tech-manager/        # 技术经理
│   └── docs/
└── workspace-developer/           # 开发
    └── project/
```

**Claude Code Runner 项目结构**：
```
项目目录/
├── docs/
│   ├── 产品/
│   │   ├── 产品方案.md
│   │   └── 需求文档.md
│   ├── 技术/
│   │   └── 技术设计.md
│   └── 评审/
│       └── 评审报告.md
├── src/                          # 代码实现
└── tests/                        # 测试用例
```

### 结论：适用场景

| 场景 | 推荐选择 |
|------|----------|
| 个人 AI 助手 | OpenClaw |
| 消息驱动的自动化 | OpenClaw |
| 持续迭代的项目开发 | Claude Code Runner |
| 多阶段评审流程 | Claude Code Runner |
| 长期维护的代码库 | Claude Code Runner |
| 文档+代码完整产出 | Claude Code Runner |

### 互补关系

两者并非完全替代，而是**互补**：

```
┌─────────────────────────────────────────────────────────────┐
│                        用户交互层                           │
│         (Telegram/Discord/Web/API 等消息渠道)               │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        ↓                                         ↓
   OpenClaw                                   Claude Code Runner
   (系统级)                                    (项目级)
        │                                         │
   消息处理                                  任务执行
   对话交互                                  评审流转
   短任务                                   持续项目
        │                                         │
        └────────────────────┬────────────────────┘
                             │
                      可以整合使用
                      (OpenClaw 触发
                       Claude Code Runner)
```

**整合场景**：
- OpenClaw 接收用户消息
- 通过 Cron 或命令触发 Claude Code Runner 任务
- Claude Code Runner 执行项目级任务
- 结果返回给 OpenClaw 通过消息渠道通知用户
