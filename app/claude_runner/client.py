"""Claude Code SDK 客户端封装 - 支持流式输出"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Literal, Optional

from claude_code_sdk import (
    ClaudeCodeOptions,
    ClaudeSDKClient,
    AssistantMessage,
    ResultMessage,
)

# 权限模式类型
PermissionMode = Literal["default", "acceptEdits", "plan", "bypassPermissions"]


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


class ClaudeCodeClient:
    """
    Claude Code 客户端封装

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

    def _create_options(self) -> ClaudeCodeOptions:
        """创建 SDK 配置"""
        return ClaudeCodeOptions(
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

    async def wait_for_answer(
        self,
        question_id: str,
        timeout: Optional[float] = None,
    ) -> Optional[dict]:
        """
        等待用户回答问题

        Args:
            question_id: 问题 ID，用于验证
            timeout: 超时时间（秒），None 表示无限等待

        Returns:
            用户答案 dict，包含 question_id 和 answer
        """
        self._answer_event = asyncio.Event()
        self._is_waiting_answer = True
        self._pending_answer = None
        self._pending_question_id = question_id

        try:
            # 等待答案或超时
            if timeout:
                await asyncio.wait_for(self._answer_event.wait(), timeout=timeout)
            else:
                await self._answer_event.wait()

            return self._pending_answer
        except asyncio.TimeoutError:
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

    async def submit_answer(self, answer: dict) -> None:
        """
        提交用户答案，唤醒等待

        Args:
            answer: 答案 dict，包含 question_id、answer 和 follow_up_answers
        """
        if self._answer_event and not self._answer_event.is_set():
            self._pending_answer = answer
            self._answer_event.set()

    async def _parse_question_data(self, tool_input: dict) -> Optional[AskUserQuestion]:
        """解析问答数据"""
        try:
            # 解析选项
            options = None
            if tool_input.get("options"):
                options = [
                    QuestionOption(
                        id=opt.get("id", ""),
                        label=opt.get("label", ""),
                        description=opt.get("description"),
                        default=opt.get("default", False),
                    )
                    for opt in tool_input["options"]
                ]

            # 解析追问问题
            follow_up_questions = {}
            if tool_input.get("follow_up_questions"):
                for parent_id, questions in tool_input["follow_up_questions"].items():
                    follow_up_questions[parent_id] = [
                        FollowUpQuestion(
                            question_id=q.get("question_id", ""),
                            question_text=q.get("question_text", ""),
                            type=q.get("type", "multiple_choice"),
                            options=[
                                QuestionOption(
                                    id=opt.get("id", ""),
                                    label=opt.get("label", ""),
                                    description=opt.get("description"),
                                    default=opt.get("default", False),
                                )
                                for opt in (q.get("options") or [])
                            ] if q.get("options") else None,
                            required=q.get("required", True),
                        )
                        for q in questions
                    ]

            return AskUserQuestion(
                question_id=tool_input.get("question_id", ""),
                question_text=tool_input.get("question_text", ""),
                type=tool_input.get("type", "multiple_choice"),
                header=tool_input.get("header"),
                description=tool_input.get("description"),
                options=options,
                required=tool_input.get("required", True),
                follow_up_questions=follow_up_questions,
            )
        except Exception:
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
                    stream_msg = None

                    if isinstance(message, AssistantMessage):
                        for block in message.content:
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

                                # 检查是否为 AskUserQuestion 工具调用
                                if tool_name == "ask_user_question":
                                    question_data = await self._parse_question_data(tool_input)
                                    stream_msg = StreamMessage(
                                        type=MessageType.ASK_USER_QUESTION,
                                        content=tool_input.get("question_text", "请回答问题"),
                                        question=question_data,
                                    )

                                    # yield 消息后等待用户回答
                                    if on_message:
                                        on_message(stream_msg)
                                    yield stream_msg

                                    # 等待用户回答（阻塞，等待 submit_answer 唤醒）
                                    # 设置超时为 1 小时
                                    answer = await self.wait_for_answer(
                                        question_id=question_data.question_id if question_data else "",
                                        timeout=3600,
                                    )

                                    if answer:
                                        # 用户回答了问题，需要发送响应给 SDK
                                        # 构建工具结果响应（包含追问答案）
                                        tool_result = {
                                            "answer": answer.get("answer"),
                                        }
                                        # 添加追问答案
                                        follow_up_answers = answer.get("follow_up_answers")
                                        if follow_up_answers:
                                            tool_result["follow_up_answers"] = follow_up_answers

                                        tool_result_content = json.dumps(tool_result)

                                        # 通过工具结果响应
                                        await client.send_tool_result(
                                            tool_id=block.id,
                                            content=tool_result_content,
                                        )
                                    else:
                                        # 超时或取消，发送空响应
                                        await client.send_tool_result(
                                            tool_id=block.id,
                                            content=json.dumps({"answer": None}),
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
