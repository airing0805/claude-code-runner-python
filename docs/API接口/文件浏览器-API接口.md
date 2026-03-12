# 文件浏览器 API 文档

本文档描述文件浏览器系统的 REST API 接口。

## 概述

文件浏览器系统提供以下核心功能：
- 目录树浏览：获取指定目录的文件树结构
- 文件读取：读取文件内容，支持分页
- 文件搜索：使用 Glob 模式搜索文件
- 文件信息：获取文件/目录的元数据信息

> **版本**: v1.0 (2026-03-10)
> **说明**: 文件浏览器是 v11.0.0 版本的新功能

## 基础信息

| 项目 | 值 |
|------|-----|
| 基础路径 | `/api/files` |
| 认证方式 | 与主 API 一致 |
| 响应格式 | JSON |

## 通用响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... }
}
```

### 错误响应

```json
{
  "success": false,
  "error": "错误信息",
  "code": "ERROR_CODE"
}
```

---

## 目录树接口

### 获取目录文件树

**GET** `/api/files/tree`

获取指定目录的树形结构。

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| path | string | "." | 目录路径 |
| depth | integer | 2 | 递归深度 (1-5) |
| include_hidden | boolean | false | 是否包含隐藏文件 |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "path": "/home/user/project",
    "name": "project",
    "type": "directory",
    "children": [
      {
        "name": "src",
        "path": "/home/user/project/src",
        "type": "directory",
        "size": null,
        "extension": null,
        "modified": null,
        "children": [
          {
            "name": "main.py",
            "path": "/home/user/project/src/main.py",
            "type": "file",
            "size": 1234,
            "extension": ".py",
            "modified": "2026-03-10T10:00:00"
          }
        ]
      },
      {
        "name": "README.md",
        "path": "/home/user/project/README.md",
        "type": "file",
        "size": 567,
        "extension": ".md",
        "modified": "2026-03-09T15:30:00"
      }
    ],
    "metadata": {
      "total_files": 25,
      "total_dirs": 8
    }
  }
}
```

---

## 文件读取接口

### 读取文件内容

**GET** `/api/files/read`

读取文件内容，支持分页读取。

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| path | string | - | 文件路径（必填） |
| start_line | integer | 1 | 起始行号 |
| limit | integer | 500 | 读取行数 (1-1000) |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "path": "/home/user/project/src/main.py",
    "name": "main.py",
    "size": 1234,
    "totalLines": 89,
    "content": "def main():\n    print('hello')",
    "truncated": false,
    "hasMore": false,
    "encoding": "utf-8"
  }
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| path | string | 文件完整路径 |
| name | string | 文件名 |
| size | integer | 文件大小（字节） |
| totalLines | integer | 文件总行数 |
| content | string | 文件内容 |
| truncated | boolean | 内容是否被截断（>50KB） |
| hasMore | boolean | 是否还有更多内容 |
| encoding | string | 文件编码 |

**错误响应**

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 403 | FORBIDDEN_PATH | 路径超出允许范围 |
| 403 | FORBIDDEN_FILE | 禁止访问敏感文件 |
| 404 | NOT_FOUND | 文件不存在 |
| 413 | FILE_TOO_LARGE | 文件过大 |

---

## 文件搜索接口

### 搜索文件

**GET** `/api/files/search`

使用 Glob 模式搜索文件。

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| pattern | string | - | Glob 模式（必填） |
| path | string | "." | 搜索目录 |
| limit | integer | 100 | 限制结果数量 (1-500) |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "pattern": "*.py",
    "matches": [
      {
        "path": "/home/user/project/src/main.py",
        "name": "main.py",
        "size": 1234
      },
      {
        "path": "/home/user/project/src/utils.py",
        "name": "utils.py",
        "size": 567
      }
    ],
    "total": 25,
    "truncated": false
  }
}
```

---

## 文件信息接口

### 获取文件信息

**GET** `/api/files/info`

获取文件或目录的元数据信息。

**查询参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| path | string | 文件或目录路径（必填） |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "path": "/home/user/project/src/main.py",
    "name": "main.py",
    "type": "file",
    "size": 1234,
    "sizeFormatted": "1.2 KB",
    "extension": ".py",
    "mimeType": "text/x-python",
    "modified": "2026-03-10T10:00:00",
    "created": "2026-03-01T08:00:00"
  }
}
```

---

## Glob 模式接口

### Glob 模式查询（POST）

**POST** `/api/files/glob`

使用 Glob 模式搜索文件（POST 版本）。

**请求体**

```json
{
  "pattern": "src/**/*.py",
  "path": "/home/user/project",
  "limit": 50
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pattern | string | 是 | Glob 模式 |
| path | string | 否 | 搜索目录，默认 "." |
| limit | integer | 否 | 限制结果数量，默认 100 |

**响应** `200 OK`

```json
{
  "success": true,
  "data": {
    "pattern": "src/**/*.py",
    "matches": [
      "src/main.py",
      "src/utils.py",
      "src/models/user.py"
    ],
    "count": 3
  }
}
```

---

## 错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|-------------|------|
| FORBIDDEN_PATH | 403 | 路径超出允许范围 |
| FORBIDDEN_FILE | 403 | 禁止访问敏感文件 |
| NOT_FOUND | 404 | 文件或目录不存在 |
| FILE_TOO_LARGE | 413 | 文件过大 |
| INVALID_PATH | 400 | 无效的路径格式 |

---

## 安全控制

### 路径验证

系统会验证所有请求的路径，确保：
1. 路径必须在允许的基础目录内
2. 不允许使用 `..` 进行路径遍历
3. 禁止访问敏感文件（.env, .pem, .key 等）
4. 禁止访问系统目录

### 敏感文件模式

以下文件模式被禁止访问：
- `.env` - 环境变量文件
- `.pem` - 私钥文件
- `.key` - 密钥文件
- `.secret` - 密钥文件
- `.password` - 密码文件
- `.git/config` - Git 配置文件

### 限制参数

| 参数 | 最大值 | 说明 |
|------|--------|------|
| depth | 5 | 目录树最大深度 |
| limit | 500 | 搜索结果最大数量 |
| limit | 1000 | 文件读取最大行数 |
| file_size | 10 MB | 文件大小限制 |

---

## 使用示例

### cURL 示例

```bash
# 获取目录树
curl "http://localhost:8000/api/files/tree?path=.&depth=2"

# 读取文件
curl "http://localhost:8000/api/files/read?path=src/main.py"

# 搜索文件
curl "http://localhost:8000/api/files/search?pattern=*.py&path=src"

# 获取文件信息
curl "http://localhost:8000/api/files/info?path=src/main.py"

# Glob 搜索
curl -X POST "http://localhost:8000/api/files/glob" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "**/*.py", "path": ".", "limit": 50}'
```

### JavaScript 示例

```javascript
// 获取目录树
async function getTree(path = '.', depth = 2) {
  const response = await fetch(`/api/files/tree?path=${path}&depth=${depth}`);
  return response.json();
}

// 读取文件
async function readFile(path, startLine = 1, limit = 500) {
  const response = await fetch(
    `/api/files/read?path=${encodeURIComponent(path)}&start_line=${startLine}&limit=${limit}`
  );
  return response.json();
}

// 搜索文件
async function searchFiles(pattern, path = '.', limit = 100) {
  const response = await fetch(
    `/api/files/search?pattern=${pattern}&path=${path}&limit=${limit}`
  );
  return response.json();
}
```

---

## Glob 模式指南

### 常用模式

| 模式 | 说明 | 示例 |
|------|------|------|
| `*` | 匹配任意字符 | `*.py` 匹配所有 .py 文件 |
| `**` | 递归匹配目录 | `**/*.py` 递归匹配所有 .py 文件 |
| `?` | 匹配单个字符 | `file?.txt` 匹配 file1.txt |
| `[abc]` | 匹配括号内任意字符 | `[abc].py` 匹配 a.py, b.py, c.py |
| `{a,b}` | 匹配多个模式之一 | `*.{py,js}` 匹配 .py 或 .js 文件 |

### 示例

```
src/**/*.py          # src 目录下所有 .py 文件
**/node_modules/    # 任意目录下的 node_modules
docs/*.md           # docs 目录下的 .md 文件
src/**/index.*      # src 任意子目录下的 index 文件
```

---

*文档版本：1.0*
*创建日期：2026-03-10*
