# 项目管理 API 技术设计

## 概述

项目管理 API 提供项目信息查询功能，用于管理多个工作目录下的 Claude Code 项目。

> **注意**: 项目列表 API 与会话管理 API 完全共享，详细说明请参阅 [会话管理API-技术设计.md](./会话管理API-技术设计.md)。

---

## 项目资源结构

```
api/
├── /api/projects                    # 项目列表（与会话管理共享）
├── /api/projects/{project_name}     # 单个项目操作
└── /api/projects/{project_name}/sessions  # 项目会话
```

---

## 基础信息

- **Base URL**: `http://127.0.0.1:8000`
- **Content-Type**: `application/json`

---

## 项目列表

> 此 API 与会话管理 API 完全相同，详见 [会话管理API-技术设计.md](./会话管理API-技术设计.md)。

---

## 错误响应

所有 API 在出错时返回统一格式：

```json
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
