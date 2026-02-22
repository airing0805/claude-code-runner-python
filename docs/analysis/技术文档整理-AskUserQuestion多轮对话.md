# AskUserQuestion多轮对话技术文档整理

## 1. 概述

AskUserQuestion是Claude Code中的核心交互工具，用于在任务执行过程中与用户进行多轮对话交互。本文档整理了与AskUserQuestion多轮对话相关的所有技术文档、实现代码和设计规范。

## 2. 核心文档清单

### 2.1 需求文档
- **`当前会话-AskUserQuestion多轮对话业务规则.md`**
  - 位置：`docs/需求文档/`
  - 内容：完整的多轮对话业务规则、交互规范、状态管理机制
  - 关键章节：递进式选择模式、条件分支模式、最终执行模式

### 2.2 分析文档
- **`当前会话-AskUserQuestion多轮对话需求分析.md`**
  - 位置：`docs/analysis/`
  - 内容：基于实际会话记录的分析总结、关键洞察、改进建议

### 2.3 示例文档
- **`AskUserQuestion对话框介绍.md`**
  - 位置：`docs/samples/`
  - 内容：AskUserQuestion工具的核心概念、数据结构、使用场景
- **`AskUserQuestion对话框数据格式.md`**
  - 位置：`docs/samples/`
  - 内容：前后端数据交互格式、完整交互流程
- **`多轮对话AskUserQuestion会话记录格式.jsonl`**
  - 位置：`docs/samples/`
  - 内容：实际的多轮对话会话记录样本

## 3. 技术实现架构

### 3.1 后端实现
**文件**: `app/claude_runner/client.py`

#### 3.1.1 核心数据结构
```python
@dataclass
class AskUserQuestion:
    """用户问答数据"""
    question_id: str
    question_text: str
    type: str  # multiple_choice, checkbox, text, boolean
    header: Optional[str] = None
    description: Optional[str] = None
    options: Optional[list[QuestionOption]] = None
    required: bool = True
    follow_up_questions: dict[str, list[FollowUpQuestion]] = field(default_factory=dict)
```

#### 3.1.2 关键方法
- `_parse_question_data()`: 解析问答数据
- 工具调用识别逻辑：支持多种名称格式的AskUserQuestion工具检测

### 3.2 前端实现
**文件**: `web/static/components/askUserQuestionDialog.js`

#### 3.2.1 核心组件
```javascript
const AskUserQuestionDialog = {
    _currentQuestion: null,
    _sessionId: null,
    
    show(runner, questionData, sessionId) {
        // 显示问答对话框
    },
    
    _createDialogElement(questionData) {
        // 创建对话框DOM元素
    },
    
    _renderOptions(questionData) {
        // 渲染选项
    }
}
```

#### 3.2.2 交互流程
1. 接收SSE推送的问答消息
2. 解析问题数据并渲染对话框
3. 处理用户选择并提交答案
4. 等待后端确认后继续任务执行

## 4. 多轮对话机制

### 4.1 对话模式分类
1. **递进式选择模式**
   - 用户通过重复选择来体验多轮对话
   - 支持无限递归（受资源限制）
   - 典型选项："再给一个多选框还是这些选项"

2. **条件分支模式**
   - 基于用户答案触发后续问题
   - follow_up_questions机制实现分支逻辑
   - 保持对话上下文连贯性

3. **最终执行模式**
   - 完成选择后执行具体操作
   - 从问答状态平滑过渡到执行状态
   - 提供完整的操作反馈

### 4.2 状态管理
```
状态流转：pending → answered → [继续下一轮或执行]
并发控制：支持同一会话内多个pending状态的问答
消息链：通过parentUuid维护对话顺序关系
```

## 5. 数据格式规范

### 5.1 工具调用格式
```json
{
  "type": "tool_use",
  "id": "call_function_xxx",
  "name": "ask_user_question",
  "input": {
    "question_id": "功能选择",
    "header": "选择功能",
    "question_text": "请选择一个功能",
    "type": "multiple_choice",
    "options": [
      {
        "label": "背唐诗",
        "description": "背诵一首经典唐诗"
      }
    ],
    "multiSelect": true
  }
}
```

### 5.2 工具结果格式
```json
{
  "type": "tool_result",
  "tool_use_id": "call_function_xxx",
  "content": "User has answered your questions: \"请选择一个功能\"=\"背唐诗\""
}
```

### 5.3 前端交互格式
```json
{
  "type": "ask_user_question",
  "question": {
    "question_id": "选择操作",
    "header": "选择操作",
    "question_text": "你想让我做什么？",
    "type": "multiple_choice",
    "options": [...],
    "required": true
  }
}
```



## 8. 相关技术组件

### 8.1 依赖模块
- **消息渲染器**: `web/static/modules/message-renderer/tools.js`
- **任务管理器**: `web/static/modules/task.js`
- **工具预览处理器**: `web/static/constants/toolPreviewHandlers.js`

### 8.2 CSS样式
- **响应式样式**: `web/static/css/responsive.css` (AskUserQuestion对话框样式)
- **工具渲染器**: `web/static/components/tool-renderers/index.js`

