# Webhook 通知

## 概述

任务完成时发送 HTTP 回调通知，方便集成外部系统。

## 需求

### 4.1 Webhook 配置

```json
POST /api/webhooks
{
  "url": "https://example.com/webhook",
  "events": ["task.completed", "task.failed"],
  "secret": "whsec_xxx"  // 用于签名验证
}
```

### 4.2 事件类型

| 事件 | 说明 | 载荷 |
|------|------|------|
| task.completed | 任务成功完成 | TaskResponse |
| task.failed | 任务执行失败 | TaskResponse + error |
| task.started | 任务开始执行 | TaskRequest |

### 4.3 回调载荷

```json
{
  "event": "task.completed",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "session_id": "abc123",
    "success": true,
    "message": "任务完成",
    "cost_usd": 0.01,
    "duration_ms": 5000,
    "files_changed": ["file1.py"],
    "tools_used": ["Read", "Edit"]
  },
  "signature": "sha256=xxx"  // 验证请求来源
}
```

## 实现

- 使用 httpx 异步发送 Webhook
- 支持重试机制（指数退避）
- 签名验证确保安全性
- Webhook 记录日志便于调试
