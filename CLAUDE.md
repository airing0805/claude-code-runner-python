# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Claude Code Runner 是 Claude Code SDK 的 Web 服务封装，通过 FastAPI 提供 REST API 和 Web 界面来调用 Claude Code 执行编程任务。支持同步响应和 SSE 流式输出两种模式。

## 常用命令

```bash
# 安装依赖
uv sync

# 安装开发依赖（用于测试）
uv sync --group dev

# 启动服务
uv run python -m app.main

# 使用 uvicorn 直接启动（支持热重载）
uv run uvicorn app.main:app --reload

# 运行测试
uv run pytest tests/ -v

# 运行测试并显示覆盖率
uv run pytest tests/ -v --cov=app --cov-report=term-missing

# 运行特定测试类
uv run pytest tests/test_runner.py::TestClaudeCodeClient -v
```

## 环境配置

复制 `.env.example` 到 `.env` 并配置：
- `ANTHROPIC_API_KEY` - Claude Code SDK 所需的 API 密钥
- `WORKING_DIR` - Claude Code 执行任务的工作目录
- `HOST` / `PORT` - 服务器配置（默认：127.0.0.1:8000）

## 架构

```
app/
├── main.py                 # FastAPI 应用入口
├── claude_runner/
│   └── client.py           # SDK 封装核心
├── routers/                # API 路由模块
│   ├── task.py             # 任务执行 API
│   ├── session.py          # 会话管理 API
│   ├── status.py           # 状态查询 API
│   ├── auth.py             # 认证 API
│   └── api_keys.py         # API 密钥管理
├── auth/                   # 认证模块
└── models/                 # 数据模型

web/                        # 前端文件
├── templates/              # Jinja2 模板
└── static/                # 静态资源
```

### 核心组件

**ClaudeCodeClient** (`app/claude_runner/client.py`)：
- 封装 claude-code-sdk 的 `ClaudeSDKClient`
- 两种执行模式：`run()`（同步）和 `run_stream()`（异步迭代器）
- 跟踪执行过程中的工具使用和文件变更
- 支持权限模式：`default`、`acceptEdits`、`plan`、`bypassPermissions`

**API 路由** (`app/routers/`)：
- `POST /api/task` - 同步任务执行
- `POST /api/task/stream` - SSE 流式输出
- `GET /api/status` - 服务状态
- `GET /` - Web 界面

### 关键数据结构

```python
# SSE 流式消息类型
MessageType: TEXT | TOOL_USE | TOOL_RESULT | THINKING | ERROR | COMPLETE

# 最终结果
TaskResult:
  - success: bool
  - message: str
  - cost_usd: float
  - duration_ms: int
  - files_changed: list[str]
  - tools_used: list[str]
```

## 项目规则

项目规则位于 `.claude/rules/` 目录：
- `coding-style.md` - Python 编码风格、类型注解
- `testing.md` - 测试策略、80% 覆盖率要求
- `api-design.md` - REST API 设计规范
- `security.md` - 安全要求、密钥管理
- `patterns.md` - 设计模式、架构约定
- `git-workflow.md` - Git 提交规范

## 依赖

- `claude-code-sdk>=0.0.25` - Anthropic 官方 SDK
- `fastapi>=0.129.0` + `uvicorn>=0.41.0` - Web 框架
- `jinja2>=3.1.6` - 模板引擎
- `python-dotenv>=1.2.1` - 环境变量管理
- `pydantic>=2.10.0` - 数据验证
- `slowapi>=0.1.9` - 限流
- `bcrypt>=4.2.0` + `python-jose>=3.3.0` - 认证
