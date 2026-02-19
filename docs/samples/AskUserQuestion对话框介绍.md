

`AskUserQuestion` 是 Anthropic 在 **Claude Code** 中引入的一种交互式工具，用于在任务执行过程中向用户收集明确的规格信息。当 Claude Code 需要用户确认、选择或输入信息时，会暂停执行并通过工具调用（`tool_use`）向用户提问，用户回答后通过工具结果（`tool_result`）返回答案，任务继续执行。

---

### 一、核心数据结构

`AskUserQuestion` 在会话中作为**工具调用**（`tool_use`）执行，完整的会话消息结构如下：

#### 1. 工具调用（Claude → 用户）

```json
{
  “type”: “message”,
  “role”: “assistant”,
  “content”: [
    {
      “type”: “tool_use”,
      “id”: “toolu_xxx”,
      “name”: “ask_user_question”,
      “input”: {
        “question_id”: “auth_strategy_01”,
        “question_text”: “您希望采用哪种身份验证策略？”,
        “description”: “请选择最适合当前项目安全要求和用户体验的方案。”,
        “type”: “multiple_choice”,
        “options”: [
          {
            “id”: “oauth2”,
            “label”: “OAuth 2.0 (推荐用于生产环境)”,
            “description”: “支持第三方登录（Google/GitHub），符合现代安全标准。”,
            “default”: true
          },
          {
            “id”: “jwt_local”,
            “label”: “JWT + 本地账号”,
            “description”: “用户注册/登录使用邮箱密码，Token 存储在客户端。”
          },
          {
            “id”: “session_cookie”,
            “label”: “Session + Cookie”,
            “description”: “服务端维护会话状态，适合传统 Web 应用。”
          }
        ],
        “required”: true,
        “follow_up_questions”: {
          “oauth2”: [
            {
              “question_id”: “oauth_providers”,
              “question_text”: “请选择要集成的 OAuth 提供商：”,
              “type”: “checkbox”,
              “options”: [
                { “id”: “google”, “label”: “Google” },
                { “id”: “github”, “label”: “GitHub” },
                { “id”: “microsoft”, “label”: “Microsoft” }
              ]
            }
          ]
        }
      }
    }
  ]
}
```

#### 2. 工具结果（用户 → Claude）

```json
{
  “type”: “message”,
  “role”: “user”,
  “content”: [
    {
      “type”: “tool_result”,
      “tool_use_id”: “toolu_xxx”,
      “content”: “{\”question_id\”: \”auth_strategy_01\”, \”answer\”: \”oauth2\”}”
    }
  ]
}
```

#### 3. 完整会话消息链（JSONL 格式）

```jsonl
{“type”: “user”, “message”: {“role”: “user”, “content”: [{“type”: “text”, “text”: “帮我实现登录功能”}]}, “uuid”: “msg_001”, “parentUuid”: null, “cwd”: “e:\\project”, “sessionId”: “xxx”, ...}
{“type”: “assistant”, “message”: {“role”: “assistant”, “content”: [{“type”: “tool_use”, “id”: “toolu_001”, “name”: “ask_user_question”, “input”: {...}}]}, “uuid”: “msg_002”, “parentUuid”: “msg_001”, ...}
{“type”: “user”, “message”: {“role”: “user”, “content”: [{“type”: “tool_result”, “tool_use_id”: “toolu_001”, “content”: “{\”answer\”: \”oauth2\”}”}]}, “uuid”: “msg_003”, “parentUuid”: “msg_002”, ...}
{“type”: “assistant”, “message”: {“role”: “assistant”, “content”: [{“type”: “text”, “text”: “好的，我来实现 OAuth 2.0 登录...”}]}, “uuid”: “msg_004”, “parentUuid”: “msg_003”, ...}
```

---

### 二、字段详解

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `input.question_id` | string | 是 | 唯一标识符，用于跟踪和条件分支 |
| `input.question_text` | string | 是 | 向用户显示的核心问题 |
| `input.description` | string | 否 | 问题上下文或选项解释（可选但推荐） |
| `input.type` | enum | 是 | 问题类型：• `”multiple_choice”`（单选）• `”checkbox”`（多选）• `”text”`（自由文本）• `”boolean”`（是/否） |
| `input.options` | array | 条件 | 当 `type` 为选择类时必填。每个选项包含：• `id`: 机器可读值• `label`: 用户可见文本• `description`: 选项详细说明• `default`: 是否默认选中 |
| `input.required` | boolean | 否 | 默认 `true`，是否必须回答 |
| `input.follow_up_questions` | object | 否 | **条件追问**：键为父选项 `id`，值为子问题数组 |
| `tool_use.id` | string | 是 | 工具调用唯一标识，用于关联 tool_result |
| `tool_result.tool_use_id` | string | 是 | 对应 tool_use 的 id |
| `tool_result.content` | string | 是 | 用户答案的 JSON 字符串 |

---

### 三、输出结构（用户响应）

当用户作答后，系统通过 `tool_result` 返回结构化结果供 Claude 后续使用：

#### 单选示例：
```json
{
  “question_id”: “auth_strategy_01”,
  “answer”: “oauth2”
}
```

#### 多选示例：
```json
{
  “question_id”: “oauth_providers”,
  “answer”: [“google”, “github”]
}
```

#### 文本输入示例：
```json
{
  “question_id”: “custom_port”,
  “answer”: “8080”
}
```

> 此输出会被自动注入到 Claude 的上下文中，作为后续代码生成的约束条件。

---

### 四、在不同环境中的体现

#### 1. **CLI 界面**
- 渲染为带编号的选项列表；
- 支持箭头键导航和回车确认；
- 自动处理 `follow_up_questions` 的级联显示。

#### 2. **Web 界面**
- 作为独立组件 `UserQuestionPanel` 存在；
- 展示交互式问答卡片，等待用户选择；
- 用户选择后调用 `/api/task/answer` 继续执行。

#### 3. **MCP（Model Context Protocol）**
- 通过标准工具调用格式传输：
  ```json
  {
    “name”: “ask_user_question”,
    “input”: { /* 上述 input 字段 */ }
  }
  ```
- MCP 服务器负责渲染 UI 并返回用户输入。

---

### 五、设计原则

1. **结构化优于自由文本**：强制使用 `id` 而非自然语言答案，便于程序解析；
2. **渐进式披露**：通过 `follow_up_questions` 避免一次性抛出过多问题；
3. **上下文感知**：问题内容可引用当前项目文件（如”基于 `auth.py` 的现有结构…”）；
4. **可追溯性**：每个 `question_id` 对应一个决策点，便于审计和回滚；
5. **会话关联**：通过 `tool_use_id` 关联问答与答案，保持会话消息链完整。

---

### 六、开发者自定义

用户可通过以下方式扩展：
- 在 `.claude/skills/` 中定义包含 `ask_user_question` 的 Skill；
- 通过 MCP 实现自定义 UI（如 Web 表单、移动端弹窗）；
- 在 Web 界面中通过 `/api/task/answer` 接口提交用户答案。

---

### 总结

`AskUserQuestion` 的数据结构体现了 **”人机协作规格化”** 的设计哲学：通过工具调用协议实现结构化的提问-回答对，确保 AI 在获得明确指令后再行动。其核心是**会话消息链**，通过 `tool_use` → `tool_result` 的配对实现阻塞式交互，从根本上提升开发可靠性。