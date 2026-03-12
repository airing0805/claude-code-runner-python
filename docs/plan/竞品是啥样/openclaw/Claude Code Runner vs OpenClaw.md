# 项目比较：Claude Code Runner vs OpenClaw

## 项目概述

| 特性 | Claude Code Runner | OpenClaw |
|------|-------------------|----------|
| **定位** | Claude Code 的 Web API 封装 | 多渠道个人 AI 助手网关 |
| **语言** | Python | TypeScript/Node.js |
| **版本** | 0.6.0 | 2026.3.3 |
| **许可证** | 未指定 | MIT |

---

## 核心功能差异

### Claude Code Runner
- **REST API + Web 界面**：通过 FastAPI 提供任务执行 API
- **任务执行**：同步/流式执行 Claude Code 任务
- **会话管理**：历史会话记录和恢复
- **定时任务**：基于 APScheduler 的定时任务
- **MCP 协议支持**：Model Context Protocol 集成
- **认证系统**：JWT + bcrypt 用户认证
- **Rate Limiting**：请求限流

### OpenClaw
- **多渠道消息**：支持 WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Line 等 20+ 渠道
- **多平台终端**：macOS/iOS/Android 语音交互
- **Live Canvas**：代理驱动的可视化工作空间
- **Voice Wake + Talk Mode**：语音唤醒和持续对话
- **插件系统**：完整的 Plugin SDK
- **设备配对**：移动端配对机制
- **多代理路由**：将消息路由到隔离的代理

---

## 技术栈对比

| 层面 | Claude Code Runner | OpenClaw |
|------|-------------------|----------|
| **后端框架** | FastAPI | 原生 Node.js |
| **SDK** | Claude Agent SDK | 自研 |
| **认证** | JWT + bcrypt | OAuth + API Key |
| **数据库** | 未指定 | 未指定 |
| **任务调度** | APScheduler | 内置 Cron |
| **包管理** | uv | pnpm |
| **测试** | pytest | vitest |

---

## 项目规模对比

| 指标 | Claude Code Runner | OpenClaw |
|------|-------------------|----------|
| **源码目录** | `app/`, `src/` | `src/` (50+ 模块) |
| **packages** | 无 | `packages/` (clawdbot, moltbot) |
| **apps** | 无 | `apps/` (iOS, Android, macOS) |
| **配置文件** | pyproject.toml | package.json, pnpm-workspace.yaml |
| **Docker** | 单 Dockerfile | docker-compose, 多 Dockerfile |

---

## 架构设计差异

### Claude Code Runner
```
┌─────────────────────────────────────┐
│         FastAPI Web 服务            │
│  (REST API + Web 界面 + SSE)        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│       ClaudeCodeClient               │
│    (Claude Agent SDK 封装)           │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Claude Code CLI              │
└─────────────────────────────────────┘
```

### OpenClaw
```
┌─────────────────────────────────────┐
│         Gateway (控制平面)          │
│  (会话、渠道、工具、事件管理)       │
└──────────────┬──────────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
 Telegram   Discord   Slack    WhatsApp
    │          │          │          │
    └──────────┴─────┬────┴──────────┘
                     ▼
            ┌──────────────┐
            │  Agent 运行时 │
            │  (工具流)     │
            └──────────────┘
```

---

## 总结

| 维度 | Claude Code Runner | OpenClaw |
|------|-------------------|----------|
| **复杂度** | 较低 | 极高 |
| **功能范围** | 单一（API 封装） | 全面（AI 助手平台） |
| **目标用户** | 开发者需要编程任务 API | 普通用户需要个人 AI 助手 |
| **可扩展性** | 有限 | 通过 Plugin SDK 高度可扩展 |
| **部署** | 简单（单服务） | 复杂（Docker/多服务） |

---

## 关键区别

1. **定位不同**：Claude Code Runner 是工具类（让 Claude Code 可编程访问），OpenClaw 是产品类（完整 AI 助手）

2. **渠道支持**：OpenClaw 支持 20+ 消息渠道，Claude Code Runner 只提供 Web API

3. **用户体验**：OpenClaw 有完整的 UI（Web, CLI, 移动端），Claude Code Runner 主要是 API

4. **开发模式**：Claude Code Runner 通过 MCP 协议扩展，OpenClaw 通过 Plugin SDK 和 Skills 扩展

5. **架构复杂度**：OpenClaw 是分布式多服务架构，Claude Code Runner 是单体服务
