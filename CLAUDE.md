# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

Claude Code Runner 是 Claude Code SDK 的 Web 服务封装，通过 FastAPI 提供 REST API 和 Web 界面来调用 Claude Code 执行编程任务。支持同步响应和 SSE 流式输出两种模式。

## 常用命令

```bash
# 安装依赖
uv sync

# 安装开发依赖（用于测试）
uv sync --group dev

# 启动服务（推荐）
uv run python -m app.main

# 使用 uvicorn 直接启动（支持热重载）
uv run uvicorn app.main:app --reload

# 运行测试
uv run pytest tests/ -v

# 运行测试并显示覆盖率
uv run pytest tests/ -v --cov=src --cov=app

# 运行特定测试类
uv run pytest tests/test_runner.py::TestClaudeCodeClient -v

# 运行特定测试
uv run pytest tests/test_runner.py::TestClaudeCodeClient::test_client_initialization -v
```

## 环境配置

复制 `.env.example` 到 `.env` 并配置：
- `ANTHROPIC_API_KEY` - Claude Code SDK 所需的 API 密钥
- `WORKING_DIR` - Claude Code 执行任务的工作目录
- `HOST` / `PORT` - 服务器配置（默认：127.0.0.1:8000）

## 架构

```
app/main.py                 # FastAPI 应用 - 路由、模型、SSE 流式输出
src/claude_runner/client.py # SDK 封装核心，包含 ClaudeCodeClient 类
tests/test_runner.py        # 单元测试和 API 测试
```

### 核心组件

**ClaudeCodeClient** (`src/claude_runner/client.py`)：
- 封装 claude-code-sdk 的 `ClaudeSDKClient`
- 两种执行模式：`run()`（同步）和 `run_stream()`（异步迭代器）
- 跟踪执行过程中的工具使用和文件变更
- 支持权限模式：`default`、`acceptEdits`、`plan`、`bypassPermissions`
- 通过管理 `CLAUDECODE` 环境变量处理嵌套的 Claude Code 调用

**FastAPI 应用** (`app/main.py`)：
- `POST /api/task` - 同步任务执行，返回 `TaskResponse`
- `POST /api/task/stream` - SSE 流式输出，返回 `StreamMessage` 事件
- `GET /api/status` - 服务状态
- `GET /api/tools` - 可用工具列表
- `GET /` - Web 界面（Jinja2 模板）

### 关键数据结构

```python
# SSE 流式消息类型
MessageType: TEXT | TOOL_USE | TOOL_RESULT | THINKING | ERROR | COMPLETE

# 最终结果
TaskResult:
  - success: bool        # 是否成功
  - message: str         # 响应消息
  - cost_usd: float      # 费用（美元）
  - duration_ms: int     # 耗时（毫秒）
  - files_changed: list[str]  # 变更的文件列表
  - tools_used: list[str]     # 使用的工具列表
```

## 依赖

- `claude-code-sdk` - Anthropic 官方 Claude Code SDK
- `fastapi` + `uvicorn` - Web 框架和 ASGI 服务器
- `jinja2` - Web 界面模板引擎
- `python-dotenv` - 环境变量管理

开发依赖：`pytest`、`pytest-asyncio`、`httpx`
