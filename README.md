# Claude Code Runner

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.129+-00.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.6.0-orange.svg)](https://github.com/your-repo/claude-code-runner/releases)

</div>

Claude Code Runner 是基于 [Claude Agent SDK](https://docs.anthropic.com/en/docs/agent-sdk/python) 的 Web 服务封装，通过 FastAPI 提供 REST API 和友好的 Web 界面来调用 Claude Agent 执行编程任务。

## 🌍 多平台代码同步

本项目代码同时托管在 GitHub 和 Gitee 平台，确保访问的便利性：

- **GitHub**: `https://github.com/airing0805/claude-code-runner-python.git`
- **Gitee**: `https://gitee.com/andy0805/claude-code-runner-python.git`

## 为什么使用 Claude Code Runner？

Claude Code 是一个强大的 AI 编程助手，但原生的 CLI 方式在使用上有一定门槛。Claude Code Runner 将 Claude Code 的能力以 Web API 和可视化界面的形式开放出来，让团队可以更灵活地集成和使用 AI 编程能力。

### 项目解决的问题

1. **API 化交付** - 将 Claude Code 从 CLI 工具转化为 REST API，便于与现有系统集成
2. **多用户支持** - 提供用户认证和会话管理，支持团队协作
3. **可视化交互** - 提供 Web 界面，降低使用门槛
4. **实时反馈** - SSE 流式输出，实时展示 AI 的思考和操作过程
5. **扩展能力** - MCP 服务器、技能系统、插件机制、钩子配置，满足定制化需求
6. **能力无限制** - 通过技能系统，几乎可以完成任何 AI 可以处理的任务

### 理论上可以做任何事情

Claude Code 本身就是一个强大的通用 AI 助手，配合技能系统可以完成各种任务：

- **内容创作**: 写文章、写小说、写剧本、拍短视频脚本、自媒体运营
- **学术研究**: 读论文、写论文、文献综述、实验设计、数据分析
- **日常生活**: 旅行规划、食谱推荐、健康咨询、购物决策
- **游戏娱乐**: 游戏攻略、MOD 开发、代码辅助
- **教育培训**: 课程设计、作业批改、在线辅导、知识讲解
- **工作自动化**: 邮件处理、日程安排、会议纪要、数据报表
- **软件开发**: 编程、调试、重构、测试、部署（这是基本能力）

简单来说，只要你能想到的，Claude Code 都可以帮你完成。Claude Code Runner 只是提供了一个更方便的方式来调用它。

### 适用场景

| 场景 | 说明 | 可用的技能/Agent |
|------|------|-----------------|
| **AI 编程助手服务** | 作为团队内部的 AI 编程助手服务，为多个开发者提供统一的 AI 编程入口 | skills: 代码开发、代码审查、重构 |
| **CI/CD 集成** | 将 AI 能力集成到构建流水线，自动完成代码审查、bug 修复等任务 | hooks: 拦截危险操作、记录执行日志 |
| **低代码平台** | 作为 AI 能力的后端，为低代码/无代码平台提供代码生成能力 | agents: 子任务管理 |
| **教学/实验环境** | 在编程教学场景中，为学生提供 AI 辅助编程环境 | skills: 代码审查、测试辅助 |
| **自动化运维** | 集成到运维系统，让 AI 帮助分析日志、生成脚本、执行运维任务 | skills: Bash/Docker/安全相关 |
| **企业内部 AI 助手** | 部署为内部服务，为企业提供可控的 AI 编程能力 | hooks: 权限控制、操作审计 |
| **文档自动生成** | 自动生成 API 文档、代码注释、技术文档 | skills: 文档处理、API 文档 |
| **数据库操作** | 辅助 SQL 编写、数据库迁移、数据模型设计 | skills: 数据库操作 |
| **安全审计** | 代码安全扫描、漏洞检测、合规检查 | skills: 安全扫描 |
| **测试自动化** | 自动生成单元测试、集成测试、E2E 测试 | skills: 测试框架 |
| **公众号运营** | 自动撰写文章、排版发布、回复评论、分析数据 | skills: 写作、文档处理、webhook |
| **短视频创作** | 生成脚本、剪辑视频、添加字幕、配音旁白 | skills: 视频处理、音频处理 |
| **论文写作** | 文献综述、实验设计、数据分析、格式排版 | skills: 文档处理、数据分析 |
| **游戏辅助** | 游戏攻略生成、代码辅助 MOD 开发、数据分析 | skills: 多种技能组合 |
| **个人助理** | 日程管理、邮件处理、信息汇总、创意头脑风暴 | skills: 多种技能组合 |
| **内容创作** | 小说写作、剧本创作、自媒体内容生成 | skills: 写作、创意相关 |
| **教育培训** | 课程设计、作业批改、知识点讲解、学习辅导 | skills: 教育相关 |
| **生活服务** | 旅行规划、食谱推荐、健康建议、购物决策 | skills: 搜索、文档处理 |

#### 技能系统具体能力

项目支持以下技能分类，可通过安装 Claude Code 官方技能或自定义技能来扩展：

| 分类 | 可执行的任务 |
|------|-------------|
| **文档处理** | PDF 读取/编辑、Word 文档处理、OCR 识别 |
| **代码开发** | 代码生成、重构、性能优化 |
| **版本控制** | Git 操作、PR 管理、代码审查 |
| **数据库** | SQL 编写、数据库设计、迁移脚本 |
| **测试** | 单元测试、集成测试、E2E 测试生成 |
| **部署** | Docker、K8s、CI/CD 流水线配置 |
| **安全** | 代码审计、漏洞扫描、密钥检测 |
| **前端** | React、Vue、组件开发 |
| **后端** | API 设计、微服务架构 |
| **AI/ML** | 模型训练、数据处理 |
| **写作创作** | 文章撰写、小说创作、公众号排版、剧本编写 |
| **视频音频** | 视频剪辑、字幕生成、配音合成、音频处理 |
| **数据分析** | 数据可视化、统计分析、报告生成 |
| **教育** | 课程设计、作业批改、知识点讲解 |
| **生活服务** | 旅行规划、食谱推荐、健康建议 |
| **游戏** | 游戏攻略、MOD 开发、数据分析 |
| **社交媒体** | 内容策划、发布管理、评论回复 |

#### 子代理 (Agent) 具体能力

项目支持创建子代理来并行执行多任务：

- **代码审查代理** - 并行审查多个文件
- **测试生成代理** - 为多个模块同时生成测试
- **重构代理** - 执行大规模代码重构
- **文档生成代理** - 并行生成多个文档
- **数据处理代理** - 并行处理多个数据任务

#### 钩子系统具体应用

| 钩子类型 | 应用场景 |
|----------|---------|
| **PreToolUse** | 阻止危险命令执行（如 rm -rf /）、要求确认敏感操作、限制可用工具 |
| **PostToolUse** | 记录所有操作日志、审计文件变更、自动提交代码 |
| **Stop** | 清理临时文件、生成执行报告、发送通知 |
| **SessionStart** | 加载项目配置、初始化环境、检查依赖 |
| **Notification** | 任务完成通知、错误告警、执行统计 |

### 目标用户

- **开发团队** - 需要为团队提供统一的 AI 编程入口
- **平台开发者** - 需要将 AI 编程能力集成到现有产品
- **DevOps 工程师** - 需要将 AI 能力融入自动化流程
- **教育机构** - 需要为学生提供 AI 辅助编程环境

## 特性

- **Web 界面** - 直观的 UI 用于提交任务、查看执行过程和管理会话
- **SSE 流式输出** - 实时显示 Claude Code 的思考和工具调用过程
- **同步/异步 API** - 支持同步等待和异步流式两种执行模式
- **会话管理** - 保存和管理多个会话上下文，支持会话历史回溯
- **MCP 服务器管理** - 配置和管理 MCP (Model Context Protocol) 服务器
- **技能系统** - 自定义技能配置，扩展 Claude Code 能力
- **Agent 监控** - 实时监控 Agent 运行状态和资源使用
- **插件系统** - 灵活的插件机制，支持功能扩展
- **钩子配置** - 支持 PreToolUse/PostToolUse/Stop 等钩子事件
- **用户认证** - 完整的用户注册和登录系统
- **API 密钥管理** - 支持多 API 密钥配置和轮换
- **执行统计** - 返回费用、耗时、文件变更等详细信息
- **权限模式** - 支持 default、acceptEdits、plan、bypassPermissions 模式

## 快速开始

### 环境要求

- Python 3.10+
- Anthropic API Key

### 1. 安装

```bash
# 克隆项目
git clone https://github.com/your-repo/claude-code-runner.git
cd claude-code-runner

# 使用 uv 安装依赖 (推荐)
uv sync

# 或使用 pip
pip install -e .
```

### 2. 配置

```bash
# 复制示例配置
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# Claude API Key (必需)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# 工作目录 - Claude Code 执行任务的目录 (必需)
WORKING_DIR=/path/to/your/project

# 服务器配置 (可选)
HOST=127.0.0.1
PORT=8000
SECRET_KEY=your-secret-key-change-in-production
```

### 3. 启动

```bash
# 方式1: 使用 uv (推荐)
uv run python -m app.main

# 方式2: 使用 uvicorn (支持热重载)
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 方式3: 使用启动脚本
python run_server.py
```

服务启动后，访问 http://127.0.0.1:8000

## 功能详解

### 任务执行

#### 同步执行

```bash
curl -X POST http://127.0.0.1:8000/api/task \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "阅读 main.py 并总结其功能",
    "working_dir": "/path/to/project",
    "tools": ["Read", "Glob", "Grep"]
  }'
```

响应示例：

```json
{
  "success": true,
  "message": "任务完成的响应文本",
  "cost_usd": 0.05,
  "duration_ms": 3000,
  "files_changed": ["/path/to/file.py"],
  "tools_used": ["Read", "Edit"]
}
```

#### 流式执行 (SSE)

```bash
curl -X POST http://127.0.0.1:8000/api/task/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "列出所有 Python 文件"}'
```

SSE 消息格式：

```json
{
  "type": "text|tool_use|tool_result|thinking|error|complete",
  "content": "消息内容",
  "timestamp": "2025-01-15T10:30:00.000000",
  "tool_name": "Read",
  "tool_input": {"file_path": "/test.py"}
}
```

### 用户认证

注册新用户：

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "your-username", "password": "your-password"}'
```

登录：

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your-username", "password": "your-password"}'
```

### API 密钥管理

```bash
# 创建 API 密钥
curl -X POST http://127.0.0.1:8000/api/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-api-key", "key": "sk-ant-xxx"}'
```

### MCP 服务器管理

```bash
# 列出 MCP 服务器
curl -X GET http://127.0.0.1:8000/api/mcp/servers

# 添加 MCP 服务器
curl -X POST http://127.0.0.1:8000/api/mcp/servers \
  -H "Content-Type: application/json" \
  -d '{"name": "filesystem", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]}'
```

### 技能管理

```bash
# 列出可用技能
curl -X GET http://127.0.0.1:8000/api/skills

# 添加自定义技能
curl -X POST http://127.0.0.1:8000/api/skills \
  -H "Content-Type: application/json" \
  -d '{"name": "code-review", "description": "代码审查技能", "instruction": "你是一个代码审查专家..."}'
```

### 钩子配置

```bash
# 配置 PreToolUse 钩子
curl -X POST http://127.0.0.1:8000/api/claude/hooks \
  -H "Content-Type: application/json" \
  -d '{
    "event": "PreToolUse",
    "action": "allow",
    "conditions": [{"field": "tool_name", "operator": "in", "value": ["Read", "Glob"]}]
  }'
```

## API 文档

启动服务后访问：
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### 主要 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/task | 同步执行任务 |
| POST | /api/task/stream | 流式执行任务 |
| GET | /api/sessions | 获取会话列表 |
| GET | /api/sessions/{id} | 获取会话详情 |
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |
| GET | /api/status | 服务状态 |
| GET | /api/tools | 获取可用工具 |
| GET | /api/mcp/servers | MCP 服务器列表 |
| GET | /api/skills | 技能列表 |
| GET | /api/agents | Agent 列表 |

## 项目结构

```
claude-code-runner/
├── app/
│   ├── main.py                 # FastAPI 应用入口
│   ├── auth/                   # 认证模块
│   │   ├── core.py             # 认证核心逻辑
│   │   └── dependencies.py     # 认证依赖
│   ├── claude/                 # Claude 相关
│   │   ├── hooks_manager.py    # 钩子管理
│   │   └── plugins_manager.py  # 插件管理
│   ├── claude_runner/          # SDK 封装
│   │   └── client.py           # 客户端封装
│   ├── models/                 # 数据模型
│   ├── mcp/                    # MCP 服务器管理
│   ├── routers/                # API 路由
│   │   ├── task.py             # 任务执行
│   │   ├── session.py          # 会话管理
│   │   ├── auth.py             # 认证
│   │   ├── api_keys.py        # API 密钥
│   │   ├── mcp.py             # MCP
│   │   ├── skills.py          # 技能
│   │   ├── agents.py          # Agent
│   │   └── claude.py          # Claude 配置
│   ├── skills/                 # 技能系统
│   └── agents/                 # Agent 管理
├── web/
│   ├── templates/              # Jinja2 模板
│   │   └── index.html         # 主页面
│   └── static/                # 静态资源
│       ├── style.css          # 样式
│       └── js/                # 前端脚本
├── tests/                      # 测试
├── docs/                       # 文档
├── .env.example               # 环境变量示例
├── pyproject.toml             # 项目配置
└── run_server.py              # 启动脚本
```

## 技术栈

- **Python 3.10+** - 核心语言
- **FastAPI** - Web 框架
- **Claude Code SDK** - Anthropic 官方 SDK
- **Uvicorn** - ASGI 服务器
- **Jinja2** - 模板引擎
- **Pydantic** - 数据验证
- **bcrypt + python-jose** - 用户认证
- **slowapi** - 请求限流
- **pytest** - 测试框架

## 配置说明

### 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| ANTHROPIC_API_KEY | 是 | - | Anthropic API Key |
| WORKING_DIR | 是 | "." | 工作目录 |
| HOST | 否 | "127.0.0.1" | 监听地址 |
| PORT | 否 | 8000 | 监听端口 |
| SECRET_KEY | 否 | - | JWT 密钥 (生产环境必设) |

### 权限模式

| 模式 | 说明 |
|------|------|
| default | 默认模式，需要用户确认 |
| acceptEdits | 自动接受编辑操作 |
| plan | 规划模式，先生成计划 |
| bypassPermissions | 跳过所有权限检查 |

### 可用工具

| 工具 | 说明 | 是否修改文件 |
|------|------|-------------|
| Read | 读取文件内容 | 否 |
| Write | 创建新文件 | 是 |
| Edit | 编辑现有文件 | 是 |
| Bash | 运行终端命令 | 可能 |
| Glob | 按模式查找文件 | 否 |
| Grep | 搜索文件内容 | 否 |
| WebSearch | 搜索网络 | 否 |
| WebFetch | 获取网页内容 | 否 |
| Task | 启动子代理任务 | 取决于子任务 |

## 开发

### 运行测试

```bash
# 安装测试依赖
uv sync --group dev

# 运行所有测试
uv run pytest tests/ -v

# 运行测试并显示覆盖率
uv run pytest tests/ -v --cov=app --cov-report=term-missing

# 运行特定测试
uv run pytest tests/test_runner.py::TestClaudeCodeClient -v
```

### 代码规范

项目遵循以下规范：
- PEP 8 Python 编码风格
- 类型注解 (Type Hints)
- 80% 以上测试覆盖率

## 常见问题

### Q: 如何在 Docker 中运行？

``dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -e .
ENV ANTHROPIC_API_KEY=your-key
ENV WORKING_DIR=/workspace
EXPOSE 8000
CMD ["python", "-m", "app.main"]
```

### Q: 如何配置反向代理？

Nginx 配置示例：

``nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE 支持
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
}
```

### Q: API Key 安全建议

- 使用环境变量，不要硬编码
- 生产环境使用密钥管理服务
- 定期轮换 API Key
- 限制 API Key 的使用额度

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

## 许可证

MIT License - see [LICENSE](LICENSE) for details.

## 致谢

- [Anthropic](https://www.anthropic.com/) - Claude Code SDK
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- 所有贡献者和用户
