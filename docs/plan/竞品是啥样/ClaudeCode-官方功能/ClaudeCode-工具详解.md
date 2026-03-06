# Claude Code 工具详解

Claude Code 内置 9 个核心工具，用于读取、修改和执行代码。

## 工具概览

| 工具名称 | 功能描述 | 是否修改文件 | 说明 |
|---------|---------|-------------|------|
| **Read** | 读取文件内容 | 否 | 查看文件内容，支持指定行号范围 |
| **Write** | 创建新文件 | 是 | 创建全新的文件 |
| **Edit** | 编辑现有文件 | 是 | 对现有文件进行精确修改 |
| **Bash** | 运行终端命令 | 可能 | 执行 shell 命令 |
| **Glob** | 按模式查找文件 | 否 | 使用 glob 模式搜索文件 |
| **Grep** | 搜索文件内容 | 否 | 在文件中搜索文本内容 |
| **WebSearch** | 搜索网络 | 否 | 搜索互联网获取信息 |
| **WebFetch** | 获取网页内容 | 否 | 抓取网页内容 |
| **Task** | 启动子代理任务 | 取决于子任务 | 创建子代理执行独立任务 |

---

## 1. Read 工具

读取文件内容的工具。

```python
# 调用示例
{
    "name": "Read",
    "input": {
        "file_path": "/path/to/file.py",
        "limit": 100,        # 可选，限制行数
        "offset": 0           # 可选，起始行号
    }
}
```

**参数说明**：
- `file_path`（必需）：要读取的文件路径
- `limit`（可选）：限制返回的行数
- `offset`（可选）：从指定行号开始读取

---

## 2. Write 工具

创建新文件或覆盖现有文件。

```python
{
    "name": "Write",
    "input": {
        "file_path": "/path/to/new_file.py",
        "content": "# 文件内容..."
    }
}
```

**参数说明**：
- `file_path`（必需）：目标文件路径
- `content`（必需）：文件内容

**注意**：如果文件已存在，会覆盖原文件。

---

## 3. Edit 工具

对现有文件进行精确编辑。

```python
{
    "name": "Edit",
    "input": {
        "file_path": "/path/to/file.py",
        "old_string": "旧代码块",
        "new_string": "新代码块"
    }
}
```

**参数说明**：
- `file_path`（必需）：要编辑的文件路径
- `old_string`（必需）：要替换的代码（必须精确匹配）
- `new_string`（必需）：替换后的新代码

---

## 4. Bash 工具

执行终端命令。

```python
{
    "name": "Bash",
    "input": {
        "command": "npm install",
        "description": "安装项目依赖"
    }
}
```

**参数说明**：
- `command`（必需）：要执行的命令
- `description`（可选）：命令描述

---

## 5. Glob 工具

使用 glob 模式查找文件。

```python
{
    "name": "Glob",
    "input": {
        "pattern": "**/*.py",
        "path": "/path/to/search"
    }
}
```

**参数说明**：
- `pattern`（必需）：glob 模式（如 `**/*.py`）
- `path`（可选）：搜索路径，默认为当前工作目录

---

## 6. Grep 工具

在文件中搜索文本内容。

```python
{
    "name": "Grep",
    "input": {
        "pattern": "def.*function",
        "path": "/path/to/search",
        "glob": "*.py",
        "-n": true,
        "output_mode": "content"
    }
}
```

**参数说明**：
- `pattern`（必需）：正则表达式搜索模式
- `path`（可选）：搜索路径
- `glob`（可选）：文件过滤模式
- `-n`（可选）：是否显示行号
- `output_mode`（可选）：输出模式（content/files_with_matches/count）

---

## 7. WebSearch 工具

搜索互联网获取信息。

```python
{
    "name": "WebSearch",
    "input": {
        "query": "Python async best practices 2025",
        "num_results": 5
    }
}
```

**参数说明**：
- `query`（必需）：搜索关键词
- `num_results`（可选）：返回结果数量

---

## 8. WebFetch 工具

获取网页内容。

```python
{
    "name": "WebFetch",
    "input": {
        "url": "https://example.com/docs",
        "prompt": "提取文档中的 API 接口说明"
    }
}
```

**参数说明**：
- `url`（必需）：目标 URL
- `prompt`（可选）：从页面中提取信息的提示

---

## 9. Task 工具

启动子代理任务。

```python
{
    "name": "Task",
    "input": {
        "prompt": "分析这个代码库的错误处理模式",
        "agent": "general-purpose",
        "model": "sonnet"
    }
}
```

**参数说明**：
- `prompt`（必需）：子任务描述
- `agent`（可选）：代理类型（general-purpose/explore）
- `model`（可选）：使用的模型（sonnet/haiku）
