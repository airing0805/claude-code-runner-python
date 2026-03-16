# API 密钥管理

## 概述

支持用户创建和管理多个 API 密钥，用于程序化访问。

## 需求

### 2.1 密钥 CRUD

| 操作 | 方法 | 路径 |
|------|------|------|
| 创建密钥 | POST | /api/keys |
| 列表密钥 | GET | /api/keys |
| 撤销密钥 | DELETE | /api/keys/{key_id} |

### 2.2 密钥属性

```json
{
  "key_id": "uuid",
  "name": "My API Key",
  "prefix": "sk-ccr-xxx...",  // 只显示前4位
  "created_at": "2024-01-01T00:00:00Z",
  "last_used": "2024-01-02T00:00:00Z",
  "expires_at": null,  // 可选过期时间
  "is_active": true
}
```

### 2.3 使用方式

```bash
# 使用 API Key 访问
curl -H "X-API-Key: sk-ccr-xxxxx" http://localhost:8000/api/task
```

## 权限控制

- 密钥只能由创建者查看和管理
- 密钥可以设置过期时间
- 支持按用户配额限制密钥数量

## 安全要求

- 密钥创建时只显示一次，之后不再显示
- 密钥存储使用哈希值
- 支持设置密钥权限范围（只读/读写）
