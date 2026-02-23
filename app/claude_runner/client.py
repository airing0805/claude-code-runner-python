"""Claude Agent SDK 客户端封装 - 支持流式输出"""

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Literal, Optional

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    ResultMessage,
    UserMessage,
    ToolResultBlock,
)

# 权限模式类型
PermissionMode = Literal["default", "acceptEdits", "plan", "bypassPermissions"]

# 问答状态枚举
class QuestionStatus(Enum):
    """问答状态枚举"""
    PENDING = "pending"      # 等待显示
    SHOWING = "showing"      # 正在显示
    ANSWERED = "answered"    # 已回答
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"  # 已完成
    ERROR = "error"          # 错误
    TIMEOUT = "timeout"      # 超时

class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    ERROR = "error"
    COMPLETE = "complete"
    ASK_USER_QUESTION = "ask_user_question"

@dataclass
class QuestionOption:
    """问答选项"""
    id: str
    label: str
    description: Optional[str] = None
    default: bool = False

@dataclass
class FollowUpQuestion:
    """追问问题"""
    question_id: str
    question_text: str
    type: str  # multiple_choice, checkbox, text, boolean
    options: Optional[list[QuestionOption]] = None
    required: bool = True
    header: Optional[str] = None
    description: Optional[str] = None

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
    # 新增字段
    multi_select: bool = False  # 是否允许多选
    max_selections: Optional[int] = None  # 最大选择数量
    min_selections: int = 0     # 最小选择数量
    timeout_seconds: int = 300  # 超时时间（秒）
    created_at: float = field(default_factory=time.time)  # 创建时间戳
    # 保存原始 tool_input，用于构建 toolUseResult
    raw_tool_input: Optional[dict] = None  # SDK 返回的原始 input 数据

@dataclass
class StreamMessage:
    """流式消息"""
    type: MessageType
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    metadata: dict = field(default_factory=dict)
    question: Optional[AskUserQuestion] = None

@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    message: str
    session_id: Optional[str] = None
    cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    files_changed: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)

class InputValidator:
    """输入验证器"""
    def __init__(self):
        self.max_input_length = 1000
        # 允许 Unicode 字符（包括中文、日文、韩文等）
        self.allowed_chars = None  # None 表示允许所有字符
    
    def validate_question_options(self, options: list) -> bool:
        """验证问题选项"""
        if not isinstance(options, list):
            return False
        
        for option in options:
            if not isinstance(option, dict):
                return False
            
            if 'label' not in option or not option['label']:
                return False
            
            if len(option['label']) > 100:
                return False

            # 字符安全检查（如果 allowed_chars 为 None，则跳过检查）
            if self.allowed_chars is not None and not all(c in self.allowed_chars for c in option['label']):
                return False
        
        return True
    
    def sanitize_user_input(self, input_text: str) -> str:
        """清理用户输入"""
        # 移除潜在危险字符
        dangerous_chars = ['<', '>', '&', '"', "'", '`']
        sanitized = input_text
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # 限制长度
        return sanitized[:self.max_input_length]

class ConcurrencyManager:
    """并发管理器"""
    def __init__(self):
        self.max_concurrent_questions = 5
        self.active_questions = {}
        self.question_queue = asyncio.Queue()
        self.lock = asyncio.Lock()
    
    async def acquire_question_slot(self, session_id: str, question_id: str) -> bool:
        """获取问答执行槽位"""
        async with self.lock:
            if len(self.active_questions) >= self.max_concurrent_questions:
                # 加入队列等待
                await self.question_queue.put((session_id, question_id))
                return False
            
            self.active_questions[question_id] = {
                'session_id': session_id,
                'start_time': time.time(),
                'question_id': question_id
            }
            return True
    
    async def release_question_slot(self, question_id: str):
        """释放问答执行槽位"""
        async with self.lock:
            if question_id in self.active_questions:
                del self.active_questions[question_id]
                
            # 处理队列中的等待项
            if not self.question_queue.empty():
                try:
                    next_item = self.question_queue.get_nowait()
                    await self.acquire_question_slot(next_item[0], next_item[1])
                except asyncio.QueueEmpty:
                    pass

class ClaudeCodeClient:
    """
    Claude Agent 客户端封装

    支持流式输出，可用于 Web SSE 或 WebSocket
    支持用户问答的暂停和恢复
    """

    def __init__(
        self,
        working_dir: str = ".",
        allowed_tools: Optional[list[str]] = None,
        permission_mode: PermissionMode = "acceptEdits",
        continue_conversation: bool = False,
        resume: Optional[str] = None,
    ):
        self.working_dir = working_dir
        self.allowed_tools = allowed_tools or [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]
        self.permission_mode = permission_mode
        self.continue_conversation = continue_conversation
        self.resume = resume
        self._files_changed: list[str] = []
        self._tools_used: list[str] = []
        self._session_id: Optional[str] = None

        # 用于问答暂停/恢复
        self._client: Optional[ClaudeSDKClient] = None
        self._answer_event: Optional[asyncio.Event] = None
        self._pending_answer: Optional[dict] = None
        self._pending_question_id: Optional[str] = None
        self._is_waiting_answer: bool = False
        
        # 状态和安全管理
        self._question_states: dict = {}  # 问题状态管理
        self._input_validator = InputValidator()
        self._concurrency_manager = ConcurrencyManager()
        self._session_timeout = 3600  # 会话超时时间（秒）

    def _create_options(self) -> ClaudeAgentOptions:
        """创建 SDK 配置"""
        return ClaudeAgentOptions(
            permission_mode=self.permission_mode,
            cwd=self.working_dir,
            continue_conversation=self.continue_conversation,
            resume=self.resume,
        )

    async def _track_tool_use(self, tool_name: str, tool_input: dict) -> None:
        """跟踪工具使用"""
        if tool_name not in self._tools_used:
            self._tools_used.append(tool_name)

        # 跟踪文件变更
        if tool_name in ("Write", "Edit"):
            file_path = tool_input.get("file_path", "")
            if file_path and file_path not in self._files_changed:
                self._files_changed.append(file_path)

    async def _send_tool_result_via_query(
        self,
        client: "ClaudeSDKClient",
        tool_id: str,
        content: str,
        question_data: Optional[Any] = None,
        answer: Optional[dict] = None,
    ) -> None:
        """
        通过 query 方法发送工具结果响应

        Claude SDK 没有 send_tool_result 方法，需要通过 query 发送
        包含工具结果字典的用户消息来响应工具调用

        Args:
            client: ClaudeSDKClient 实例
            tool_id: 工具调用 ID
            content: 工具结果内容
            question_data: 问题数据（包含 question_text、options 等）
            answer: 用户答案 dict
        """
        # 构建工具结果字典（参考 JSONL 文件格式）
        # 注意：不包含 is_error 字段，SDK 不识别此字段
        # 字段顺序也保持与 JSONL 一致: type -> content -> tool_use_id
        tool_result_dict = {
            "type": "tool_result",
            "content": content,
            "tool_use_id": tool_id,
        }

        # SDK 的 query 方法期望 AsyncIterable 或字符串，将消息包装为异步迭代器
        # 使用 SDK 内部格式：parent_tool_use_id 字段

        # 构建 toolUseResult（参考 JSONL 格式）
        # 优先使用前端传来的 raw_question_data，其次使用 question_data 中的 raw_tool_input
        tool_use_result = None
        if answer:
            # 优先：从前端传来的 raw_question_data
            raw_question_data = answer.get("raw_question_data")

            # 获取 question_text（用于 answers）
            question_text = None
            if raw_question_data:
                # 从 raw_question_data 获取 questions
                questions_list = raw_question_data.get("questions", [])
                if questions_list and len(questions_list) > 0:
                    question_text = questions_list[0].get("question")
            elif question_data:
                # 备用：从 question_data 获取
                question_text = getattr(question_data, 'question_text', None)
                raw_input = getattr(question_data, 'raw_tool_input', None)
                if raw_input:
                    questions_list = raw_input.get("questions", [])
                else:
                    questions_list = []

            # 构建 answers
            answers_dict = {}
            user_answer = answer.get("answer")
            if question_text and user_answer:
                answers_dict[question_text] = user_answer

            tool_use_result = {
                "questions": questions_list if raw_question_data else [],
                "answers": answers_dict,
            }

        # 使用 SDK 内部格式（使用 parent_tool_use_id 字段）
        # 参考 SDK 的 query 方法实现
        message = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [tool_result_dict],
            },
            "parent_tool_use_id": tool_id,  # 使用 SDK 内部字段名
        }

        # 添加 toolUseResult（如果有的话）
        if tool_use_result:
            message["toolUseResult"] = tool_use_result

        # ========== 调试日志：打印完整的消息结构 ==========
        print(f"[SDK Debug] ★★★ 完整消息结构: {json.dumps(message, ensure_ascii=False)}")
        print(f"[SDK Debug] ★★★ SDK 格式: {{'type': 'user', 'message': {{'role': 'user', 'content': [{{'type': 'tool_result', 'content': '...', 'tool_use_id': 'xxx'}}]}}, 'parent_tool_use_id': 'xxx'}}")

        async def message_generator():
            yield message

        # 通过 query 发送包含工具结果的用户消息
        print(f"[Client] ★★★ 发送工具结果: tool_id={tool_id}, content={content}")
        try:
            await client.query(message_generator())
            print(f"[Client] ★★★ 工具结果发送成功")
        except Exception as e:
            print(f"[Client] ★★★ 工具结果发送失败: {e}")

    async def _update_question_state(self, question_id: str, status: QuestionStatus, metadata: dict = None):
        """更新问题状态"""
        self._question_states[question_id] = {
            'status': status.value,
            'updated_at': time.time(),
            'metadata': metadata or {}
        }
        
        # 记录状态变更日志
        print(f"[Question State] {question_id} -> {status.value}")

    async def wait_for_answer(
        self,
        question_id: str,
        timeout: Optional[float] = None,
    ) -> Optional[dict]:
        """
        等待用户回答问题

        注意：等待状态已在调用此方法前设置，此处只需等待事件触发

        Args:
            question_id: 问题 ID，用于验证
            timeout: 超时时间（秒），None 表示无限等待

        Returns:
            用户答案 dict，包含 question_id 和 answer
        """
        # 更新状态为SHOWING
        await self._update_question_state(question_id, QuestionStatus.SHOWING)
        
        try:
            # 等待答案或超时
            if timeout:
                await asyncio.wait_for(self._answer_event.wait(), timeout=timeout)
            else:
                await self._answer_event.wait()

            # 更新状态为ANSWERED
            await self._update_question_state(question_id, QuestionStatus.ANSWERED)
            return self._pending_answer
        except asyncio.TimeoutError:
            # 超时处理
            await self._update_question_state(question_id, QuestionStatus.TIMEOUT)
            return None
        finally:
            self._is_waiting_answer = False
            self._answer_event = None
            self._pending_question_id = None

    def is_waiting_answer(self) -> bool:
        """检查是否正在等待用户回答"""
        return self._is_waiting_answer

    def get_pending_question_id(self) -> Optional[str]:
        """获取正在等待的问题 ID"""
        return self._pending_question_id

    def get_session_id(self) -> Optional[str]:
        """获取当前会话 ID"""
        return self._session_id

    def set_session_id(self, session_id: str) -> None:
        """设置会话 ID"""
        self._session_id = session_id

    async def submit_answer(self, answer: dict) -> bool:
        """
        提交用户答案，唤醒等待

        Args:
            answer: 答案 dict，包含 question_id、answer 和 follow_up_answers

        Returns:
            bool: 提交是否成功
        """
        question_id = answer.get('question_id')
        user_answer = answer.get('answer')
        
        # 输入验证
        if not self._input_validator.sanitize_user_input(str(user_answer)):
            print(f"[Validation Error] Invalid answer for question {question_id}")
            return False
            
        # 检查会话有效性
        if not self._session_id:
            print("[Session Error] No active session")
            return False
            
        # 检查问题状态
        if question_id not in self._question_states:
            print(f"[State Error] Question {question_id} not found")
            return False
            
        current_state = self._question_states[question_id]['status']
        if current_state != QuestionStatus.SHOWING.value:
            print(f"[State Error] Question {question_id} is in wrong state: {current_state}")
            return False

        if self._answer_event and not self._answer_event.is_set():
            # 更新状态为PROCESSING
            await self._update_question_state(question_id, QuestionStatus.PROCESSING, {
                'answer_received': True,
                'answer_length': len(str(user_answer))
            })

            # ========== 调试日志：提交答案内容 ==========
            print(f"[Answer Debug] ★★★ submit_answer 收到的答案: {answer}")

            self._pending_answer = answer
            self._answer_event.set()
            return True
        return False

    async def _parse_question_data(self, tool_input: dict) -> Optional[AskUserQuestion]:
        """解析问答数据"""
        try:
            # 添加调试日志，查看 SDK 原始数据
            print(f"[Debug] _parse_question_data called with tool_input keys: {tool_input.keys()}")
            print(f"[Debug] tool_input: {tool_input}")

            # 检查是否有 questions 字段（某些版本 SDK 可能是这个字段名）
            questions = tool_input.get("questions")
            if questions:
                # 如果是 questions 字段，尝试提取第一个问题
                if isinstance(questions, list) and len(questions) > 0:
                    q = questions[0]
                    options = None
                    if q.get("options"):
                        if self._input_validator.validate_question_options(q["options"]):
                            options = [
                                QuestionOption(
                                    id=opt.get("id", str(uuid.uuid4())),
                                    label=opt.get("label", ""),
                                    description=opt.get("description"),
                                    default=opt.get("default", False),
                                )
                                for opt in q["options"]
                            ]

                    # 如果没有选项，提供默认选项
                    if not options:
                        print(f"[Warning] No options in questions field for question '{q.get('question_text', '')}', adding default options")
                        options = [
                            QuestionOption(id="option_1", label="选项1", description="默认选项1"),
                            QuestionOption(id="option_2", label="选项2", description="默认选项2"),
                            QuestionOption(id="option_3", label="选项3", description="默认选项3"),
                        ]

                    return AskUserQuestion(
                        question_id=q.get("question_id", str(uuid.uuid4())),
                        question_text=q.get("question_text", q.get("question", "")),
                        type=q.get("type", "multiple_choice"),
                        header=q.get("header"),
                        description=q.get("description"),
                        options=options,
                        required=q.get("required", True),
                        follow_up_questions={},
                        multi_select=q.get("multiSelect", False),
                        max_selections=q.get("maxSelections"),
                        min_selections=q.get("minSelections", 0),
                        timeout_seconds=q.get("timeoutSeconds", 300),
                        raw_tool_input=tool_input,  # 保存原始 tool_input
                    )

            # 解析选项
            options = None
            if tool_input.get("options"):
                if self._input_validator.validate_question_options(tool_input["options"]):
                    options = [
                        QuestionOption(
                            id=opt.get("id", str(uuid.uuid4())),
                            label=opt.get("label", ""),
                            description=opt.get("description"),
                            default=opt.get("default", False),
                        )
                        for opt in tool_input["options"]
                    ]
            else:
                # ⚠️ 临时修复：当没有选项时，提供默认选项
                print(f"[Warning] No options provided for question '{tool_input.get('question_text', '')}', adding default options")
                options = [
                    QuestionOption(id="option_1", label="选项1", description="默认选项1"),
                    QuestionOption(id="option_2", label="选项2", description="默认选项2"),
                    QuestionOption(id="option_3", label="选项3", description="默认选项3"),
                ]

            # 解析追问问题
            follow_up_questions = {}
            if tool_input.get("follow_up_questions"):
                for parent_id, questions in tool_input["follow_up_questions"].items():
                    follow_up_questions[parent_id] = [
                        FollowUpQuestion(
                            question_id=q.get("question_id", str(uuid.uuid4())),
                            question_text=q.get("question_text", ""),
                            type=q.get("type", "multiple_choice"),
                            options=[
                                QuestionOption(
                                    id=opt.get("id", str(uuid.uuid4())),
                                    label=opt.get("label", ""),
                                    description=opt.get("description"),
                                    default=opt.get("default", False),
                                )
                                for opt in (q.get("options") or [])
                            ] if q.get("options") else None,
                            required=q.get("required", True),
                            header=q.get("header"),
                            description=q.get("description"),
                        )
                        for q in questions
                    ]

            return AskUserQuestion(
                question_id=tool_input.get("question_id", str(uuid.uuid4())),
                question_text=tool_input.get("question_text", ""),
                type=tool_input.get("type", "multiple_choice"),
                header=tool_input.get("header"),
                description=tool_input.get("description"),
                options=options,
                required=tool_input.get("required", True),
                follow_up_questions=follow_up_questions,
                multi_select=tool_input.get("multiSelect", False),
                max_selections=tool_input.get("maxSelections"),
                min_selections=tool_input.get("minSelections", 0),
                timeout_seconds=tool_input.get("timeoutSeconds", 300),
                raw_tool_input=tool_input,  # 保存原始 tool_input
            )
        except Exception as e:
            print(f"[Parse Error] Failed to parse question data: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def run_stream(
        self,
        prompt: str,
        on_message: Optional[Callable[[StreamMessage], None]] = None,
    ) -> AsyncIterator[StreamMessage]:
        """
        执行任务并流式返回消息

        Args:
            prompt: 任务提示
            on_message: 消息回调函数

        Yields:
            StreamMessage: 流式消息
        """
        self._files_changed = []
        self._tools_used = []

        options = self._create_options()

        # 保存并清除 CLAUDECODE 环境变量，允许嵌套调用
        old_claudedecode = os.environ.pop("CLAUDECODE", None)

        try:
            async with ClaudeSDKClient(options=options) as client:
                # 保存 client 实例以便后续使用
                self._client = client

                # 发送任务
                await client.query(prompt)

                # 流式接收响应
                async for message in client.receive_response():
                    # ========== 调试日志：打印 SDK 返回的原始消息 ==========
                    print(f"[SDK Raw] ★★★ 收到 SDK 消息类型: {type(message)}")
                    if hasattr(message, 'content'):
                        print(f"[SDK Raw] ★★★ 消息内容: {message.content}")

                    stream_msg = None

                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            print(f"[SDK Raw] ★★★ Block 类型: {type(block)}, 内容: {block}")
                            # 文本内容
                            if hasattr(block, "text") and block.text:
                                stream_msg = StreamMessage(
                                    type=MessageType.TEXT,
                                    content=block.text,
                                )
                            # 工具调用
                            elif hasattr(block, "name"):
                                tool_name = block.name
                                tool_input = getattr(block, "input", {})

                                await self._track_tool_use(tool_name, tool_input)

                                # 检查是否为 AskUserQuestion 工具调用（支持多种名称格式）
                                tool_name_lower = tool_name.lower() if tool_name else ""
                                if tool_name_lower in ("ask_user_question", "askuserquestion", "askuser"):
                                    question_data = await self._parse_question_data(tool_input)

                                    if not question_data:
                                        # 解析失败，跳过此问题
                                        continue

                                    # 检查并发限制
                                    can_acquire = await self._concurrency_manager.acquire_question_slot(
                                        self._session_id or "unknown",
                                        question_data.question_id
                                    )

                                    if not can_acquire:
                                        # 并发限制，等待队列处理
                                        stream_msg = StreamMessage(
                                            type=MessageType.TEXT,
                                            content="系统繁忙，请稍候...",
                                        )
                                        if on_message:
                                            on_message(stream_msg)
                                        yield stream_msg
                                        continue

                                    # 更新状态为PENDING
                                    await self._update_question_state(
                                        question_data.question_id,
                                        QuestionStatus.PENDING
                                    )

                                    # 设置等待状态
                                    self._answer_event = asyncio.Event()
                                    self._is_waiting_answer = True
                                    self._pending_answer = None
                                    self._pending_question_id = question_data.question_id

                                    # 添加调试日志，确认状态设置正确
                                    print(f"[Client] ★ 设置等待状态: _is_waiting_answer={self._is_waiting_answer}, _pending_question_id={self._pending_question_id}")

                                    # 先 yield 消息，让前端显示对话框
                                    stream_msg = StreamMessage(
                                        type=MessageType.ASK_USER_QUESTION,
                                        content=tool_input.get("question_text", "请回答问题"),
                                        question=question_data,
                                    )

                                    if on_message:
                                        on_message(stream_msg)
                                    yield stream_msg

                                    # 等待用户回答（阻塞，等待 submit_answer 唤醒）
                                    answer = await self.wait_for_answer(
                                        question_id=question_data.question_id,
                                        timeout=question_data.timeout_seconds,
                                    )

                                    # 释放并发槽位
                                    await self._concurrency_manager.release_question_slot(question_data.question_id)

                                    if answer:
                                        # 用户回答了问题，需要发送响应给 SDK
                                        # 参考 JSONL 格式：
                                        # "User has answered your questions: \"{question}\"=\"{answer}\". You can now continue with the user's answers in mind."
                                        question_text = question_data.question_text or "问题"
                                        user_answer = answer.get("answer", "")

                                        # 使用 JSONL 中的格式
                                        tool_result_text = f'User has answered your questions: "{question_text}"="{user_answer}". You can now continue with the user\'s answers in mind.'

                                        # 使用描述性文本作为 content
                                        tool_result_content = tool_result_text

                                        # ========== 调试日志：打印发送给 SDK 的内容 ==========
                                        print(f"[SDK Debug] ★★★ 发送给 SDK 的 tool_result: {tool_result_content}")
                                        print(f"[SDK Debug] ★★★ answer 对象完整内容: {answer}")

                                        # 更新状态为COMPLETED
                                        await self._update_question_state(
                                            question_data.question_id,
                                            QuestionStatus.COMPLETED,
                                            {'result_sent': True}
                                        )

                                        # 通过 query 方法发送工具结果响应
                                        # 传递 question_data 和 answer 用于构建 toolUseResult
                                        await self._send_tool_result_via_query(
                                            client=client,
                                            tool_id=block.id,
                                            content=tool_result_content,
                                            question_data=question_data,
                                            answer=answer,
                                        )
                                    else:
                                        # 超时或取消，发送空响应
                                        await self._update_question_state(
                                            question_data.question_id,
                                            QuestionStatus.TIMEOUT,
                                            {'timed_out': True}
                                        )

                                        await self._send_tool_result_via_query(
                                            client=client,
                                            tool_id=block.id,
                                            content="User did not answer the question.",
                                        )

                                    # 继续处理下一条消息
                                    continue
                                else:
                                    stream_msg = StreamMessage(
                                        type=MessageType.TOOL_USE,
                                        content=f"调用工具: {tool_name}",
                                        tool_name=tool_name,
                                        tool_input=tool_input,
                                    )

                    elif isinstance(message, UserMessage):
                        # 处理 SDK 返回的用户消息（通常是 tool_result 响应）
                        # 例如：SDK 返回 "Answer questions?" 表示在等待确认
                        for block in getattr(message, 'content', []):
                            if isinstance(block, ToolResultBlock):
                                print(f"[SDK Raw] ★★★ UserMessage 中的 ToolResultBlock: tool_use_id={block.tool_use_id}, content={block.content}, is_error={block.is_error}")
                                # 如果 SDK 返回 is_error=True，这可能是询问确认
                                # 我们不需要主动发送响应，等待后续处理

                    elif isinstance(message, ResultMessage):
                        # 任务完成，更新 session_id
                        if message.session_id:
                            self._session_id = message.session_id

                        # 任务完成
                        stream_msg = StreamMessage(
                            type=MessageType.COMPLETE,
                            content="任务完成" if not message.is_error else "任务失败",
                            metadata={
                                "session_id": message.session_id,
                                "cost_usd": message.total_cost_usd,
                                "duration_ms": message.duration_ms,
                                "is_error": message.is_error,
                            },
                        )

                    if stream_msg:
                        if on_message:
                            on_message(stream_msg)
                        yield stream_msg

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[ClaudeCodeClient] run_stream 发生错误: {e}")
            print(f"[ClaudeCodeClient] 错误堆栈:\n{error_trace}")
            error_msg = StreamMessage(
                type=MessageType.ERROR,
                content=f"执行错误: {str(e)}",
            )
            if on_message:
                on_message(error_msg)
            yield error_msg
        finally:
            # 恢复环境变量
            if old_claudedecode is not None:
                os.environ["CLAUDECODE"] = old_claudedecode

    async def run(self, prompt: str) -> TaskResult:
        """
        执行任务并返回完整结果

        Args:
            prompt: 任务提示

        Returns:
            TaskResult: 任务结果
        """
        texts: list[str] = []
        session_id = None
        cost_usd = 0.0
        duration_ms = 0
        is_error = False

        async for msg in self.run_stream(prompt):
            if msg.type == MessageType.TEXT:
                texts.append(msg.content)
            elif msg.type == MessageType.COMPLETE:
                session_id = msg.metadata.get("session_id")
                cost_usd = msg.metadata.get("cost_usd", 0.0)
                duration_ms = msg.metadata.get("duration_ms", 0)
                is_error = msg.metadata.get("is_error", False)
            elif msg.type == MessageType.ERROR:
                is_error = True
                texts.append(msg.content)

        return TaskResult(
            success=not is_error,
            message="".join(texts),
            session_id=session_id,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            files_changed=self._files_changed.copy(),
            tools_used=self._tools_used.copy(),
        )
