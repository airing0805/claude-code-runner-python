# 项目管理 API 技术设计

## 概述

项目管理 API 提供项目列表、创建、删除等操作，用于管理多个工作目录下的 Claude Code 项目。

---

## 项目资源结构

```
api/
├── /api/projects                    # 项目列表
├── /api/projects/{project_name}     # 单个项目操作
└── /api/projects/{project_name}/sessions  # 项目会话
```

---

## 基础信息

- **Base URL**: `http://127.0.0.1:8000`
- **Content-Type**: `application/json`

---

## 项目列表

### GET /api/projects

获取所有项目列表（含工具汇总）。

**响应**:

```json
{
  "projects": [
    {
      "encoded_name": "E--workspaces-2026-python",
      "path": "E:\\workspaces_2026_python\\project",
      "session_count": 5,
      "tools": ["Read", "Write", "Edit", "Bash"]
    }
  ]
}
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| encoded_name | string | URL 编码的项目名称 |
| path | string | 项目完整路径 |
| session_count | int | 会话数量 |
| tools | string[] | 该项目使用的工具列表 |

---

## 错误响应

所有返回统一格式：

 API 在出错时```json
{
  "detail": "错误描述信息"
}
```

常见错误码：

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 项目编码规则

项目名称使用 URL 编码规则，将路径中的特殊字符转换：

- `\` 转换为 `-`
- `/` 转换为 `-`
- `:` 保留（Windows 盘符）
- 空格转换为 `-`

示例：
- `E:\workspaces\2026_python\project` → `E--workspaces-2026_python-project`
