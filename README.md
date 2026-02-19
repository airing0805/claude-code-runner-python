# Claude Code Runner

基于 Claude Code SDK 的 Web 服务封装，通过 FastAPI 提供 REST API 和 Web 界面来调用 Claude Code 执行编程任务。

## 功能特点

- **Web 界面** - 直观的 UI 用于提交任务和查看执行过程
- **SSE 流式输出** - 实时显示 Claude Code 的思考和工具调用过程
- **同步 API** - 支持等待任务完成后返回结果
- **可配置工具** - 自定义允许使用的工具集
- **执行统计** - 返回费用、耗时、文件变更等详细信息
- **权限模式** - 支持 default、acceptEdits、plan、bypassPermissions 模式

## 技术栈

- **Python 3.14+**
- **FastAPI** - Web 框架
- **Claude Code SDK** - Anthropic 官方 SDK
- **Uvicorn** - ASGI 服务器
- **Jinja2** - 模板引擎

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -e .
```

### 2. 配置环境变量

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
```

### 3. 启动服务

```bash
# 方式1: 使用 uv (推荐)
uv run python -m app.main

# 方式2: 使用启动脚本
python run_server.py

# 方式3: 直接运行模块
uv run uvicorn app.main:app --reload
```

访问 http://127.0.0.1:8000

## API 接口

### POST /api/task

同步执行任务，等待完成后返回结果。

**请求体：**

```json
{
  "prompt": "阅读 main.py 并总结其功能",
  "working_dir": "/path/to/project",
  "tools": ["Read", "Glob", "Grep"]
}
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| prompt | string | 是 | 任务描述 |
| working_dir | string | 否 | 工作目录，默认使用环境变量配置 |
| tools | string[] | 否 | 允许使用的工具列表 |

**响应：**

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

### POST /api/task/stream

SSE 流式执行任务，实时返回执行过程。

**请求体：** 同 `/api/task`

**SSE 消息格式：**

```json
{
  "type": "text|tool_use|tool_result|thinking|error|complete",
  "content": "消息内容",
  "timestamp": "2025-01-15T10:30:00.000000",
  "tool_name": "Read",
  "tool_input": {"file_path": "/test.py"},
  "metadata": {}
}
```

**前端调用示例：**

```javascript
const response = await fetch('/api/task/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ prompt: '你的任务' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  // 解析 SSE 格式: "data: {...}\n\n"
  const data = JSON.parse(text.replace('data: ', ''));
  console.log(data.type, data.content);
}
```

### GET /api/status

获取服务状态。

**响应：**

```json
{
  "status": "running",
  "working_dir": "/path/to/project",
  "active_tasks": 0
}
```

### GET /api/tools

获取可用工具列表。

**响应：**

```json
{
  "tools": [
    {"name": "Read", "description": "读取文件内容"},
    {"name": "Write", "description": "创建新文件"},
    {"name": "Edit", "description": "编辑现有文件"},
    {"name": "Bash", "description": "运行终端命令"},
    {"name": "Glob", "description": "按模式查找文件"},
    {"name": "Grep", "description": "搜索文件内容"},
    {"name": "WebSearch", "description": "搜索网络"},
    {"name": "WebFetch", "description": "获取网页内容"},
    {"name": "Task", "description": "启动子代理任务"}
  ]
}
```

## 项目结构

```
claude-code-runner/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── templates/
│   │   └── index.html       # Web 界面模板
│   └── static/
│       ├── style.css        # 样式文件
│       └── app.js           # 前端交互逻辑
├── src/
│   └── claude_runner/
│       ├── __init__.py      # 模块导出
│       └── client.py        # Claude Code 客户端封装
├── tests/
│   ├── __init__.py
│   └── test_runner.py       # 测试用例
├── .env.example             # 环境变量示例
├── pyproject.toml           # 项目配置
├── run_server.py            # 启动脚本
└── README.md
```

## 使用示例

### Python 客户端调用

```python
import httpx
import asyncio

async def run_task():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/task",
            json={
                "prompt": "分析项目结构并生成 README",
                "tools": ["Read", "Glob", "Write"]
            }
        )
        result = response.json()
        print(f"成功: {result['success']}")
        print(f"费用: ${result['cost_usd']:.4f}")
        print(f"修改文件: {result['files_changed']}")

asyncio.run(run_task())
```

### 流式调用示例

```python
import httpx
import asyncio
import json

async def stream_task():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://127.0.0.1:8000/api/task/stream",
            json={"prompt": "列出所有 Python 文件"},
            timeout=None
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    print(f"[{data['type']}] {data['content']}")

asyncio.run(stream_task())
```

## 测试

```bash
# 安装测试依赖
uv sync --group dev

# 运行所有测试
uv run pytest tests/ -v

# 运行测试并显示覆盖率
uv run pytest tests/ -v --cov=src --cov=app

# 只运行特定测试类
uv run pytest tests/test_runner.py::TestClaudeCodeClient -v
```

## 可用工具

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

## 权限模式

| 模式 | 说明 |
|------|------|
| default | 默认模式，需要用户确认 |
| acceptEdits | 自动接受编辑操作 |
| plan | 规划模式，先生成计划 |
| bypassPermissions | 跳过所有权限检查 |

## 常见问题

### Q: 如何在 Docker 中运行？

```dockerfile
FROM python:3.14-slim
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

```nginx
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

## 许可证

MIT
