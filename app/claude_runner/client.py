"""Claude Agent SDK 客户端封装 - 支持流式输出"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Literal, Optional

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    ResultMessage,
)

# 配置日志
logger = logging.getLogger(__name__)

# 权限模式类型
PermissionMode = Literal["default", "acceptEdits", "plan", "bypassPermissions"]

# ============================================================================
# 会话完整性配置
# ============================================================================
# SDK 的 ResultMessage 发出时间早于 Claude Code 会话记录的完整写入时间。
# 当 async with ClaudeSDKClient 上下文退出时，会话记录可能还在写入中，
# 导致会话停留在 Assistant 的 "thinking" 阶段。
# 此延迟确保会话记录有足够时间完成写入。
SESSION_WRITE_DELAY_SECONDS = 20


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    ERROR = "error"
    COMPLETE = "complete"


class QuestionStatus(Enum):
    """问题状态枚举"""
    PENDING = "pending"      # 问题待处理
    SHOWING = "showing"      # 问题正在显示
    SHOWING_UPPER = "showing_upper"  # 兼容旧代码（showing 的别名）
    ANSWERED = "answered"    # 已回答
    TIMEOUT = "timeout"      # 超时未回答
    CANCELLED = "cancelled"  # 已取消


@dataclass
class QuestionOption:
    """问答选项"""
    id: str = ""
    label: str = ""
    description: str = ""
    default: Any = None


@dataclass
class AskUserQuestion:
    """用户问答数据（占位 - SDK 当前不支持）"""
    question_id: str = ""
    question_text: str = ""
    type: str = ""
    header: str = ""
    description: str = ""
    required: bool = False
    options: Optional[list[QuestionOption]] = None
    follow_up_questions: Optional[dict[str, list]] = None
    raw_tool_input: Optional[dict] = None


@dataclass
class QuestionData:
    """问答数据（占位 - SDK 当前不支持）"""
    question_id: str = ""
    question_text: str = ""
    type: str = ""
    header: str = ""
    description: str = ""
    required: bool = False
    raw_tool_input: Optional[dict] = None


@dataclass
class FollowUpQuestion:
    """追问数据"""
    question_id: str = ""
    question_text: str = ""
    type: str = ""
    required: bool = False
    options: Optional[list[QuestionOption]] = None


@dataclass
class StreamMessage:
    """流式消息"""
    type: MessageType
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    metadata: dict = field(default_factory=dict)
    question: Optional[QuestionData] = None  # 问答数据（SDK 当前不支持）


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
    """

    def __init__(
        self,
        working_dir: str = ".",
        allowed_tools: Optional[list[str]] = None,
        permission_mode: PermissionMode = "acceptEdits",
        resume: Optional[str] = None,
    ):
        self.working_dir = working_dir
        self.allowed_tools = allowed_tools or [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]
        self.permission_mode = permission_mode
        self.resume = resume
        self._session_id: Optional[str] = None  # 会话 ID
        self._files_changed: list[str] = []
        self._tools_used: list[str] = []
        # 问答相关状态（SDK 当前不支持问答功能）
        self._is_waiting_for_answer: bool = False
        self._pending_question_id: Optional[str] = None
        # 添加 _is_waiting_answer 作为 _is_waiting_for_answer 的别名
        self._is_waiting_answer = self._is_waiting_for_answer
        self._question_states: dict[str, dict] = {}  # 问题状态映射
        self._answer_event_value = asyncio.Event()  # 答案事件
        self._pending_answer_value: Optional[dict] = None  # 待处理答案

    def _create_options(self) -> ClaudeAgentOptions:
        """创建 SDK 配置"""
        # 传递环境变量，确保不包含 CLAUDECODE（防止嵌套调用检测）
        env_override = {}
        if "CLAUDECODE" in os.environ:
            # 已经在外部清除了，但额外确保子进程也不会继承
            pass
        # 显式设置 CLAUDECODE 为空，覆盖可能的继承
        env_override["CLAUDECODE"] = ""

        return ClaudeAgentOptions(
            permission_mode=self.permission_mode,
            cwd=self.working_dir,
            resume=self.resume,
            env=env_override,
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

        # 保存并清除 CLAUDECODE 环境变量，允许嵌套调用
        # 必须在创建 options 之前清除，否则 SDK 会继承这个环境变量
        old_claudedecode = os.environ.pop("CLAUDECODE", None)
        logger.info(f"[Client] 清除 CLAUDECODE 环境变量, 原值={old_claudedecode}")

        options = self._create_options()
        logger.info(f"[Client] 开始执行任务, prompt长度={len(prompt)}")

        # 使用标志来跟踪是否需要清理
        cleanup_needed = True
        sdk_client = None

        try:
            logger.info("[Client] 创建 ClaudeSDKClient，options.env=%s", options.env if hasattr(options, 'env') else 'N/A')
            logger.info("[Client] 当前工作目录: %s", self.working_dir)

            # 手动调用 __aenter__ 和 __aexit__，避免使用 async with
            # 这样可以更好地控制清理时机，避免跨任务的 cancel scope 问题
            sdk_client = ClaudeSDKClient(options=options)
            await sdk_client.__aenter__()
            client = sdk_client

            logger.info("[Client] SDK 客户端初始化成功")
            # 发送任务
            logger.info(f"[Client] 发送 query: {prompt[:50]}...")
            await client.query(prompt)
            logger.info("[Client] query 发送成功，开始接收响应...")

            # 流式接收响应
            message_count = 0
            async for message in client.receive_response():
                message_count += 1
                logger.info(f"[Client] 收到消息 #{message_count}: type={type(message).__name__}")
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

                            stream_msg = StreamMessage(
                                type=MessageType.TOOL_USE,
                                content=f"调用工具: {tool_name}",
                                tool_name=tool_name,
                                tool_input=tool_input,
                            )

                elif isinstance(message, ResultMessage):
                    # 任务完成 - 更新 session_id
                    if message.session_id:
                        self._session_id = message.session_id
                    stream_msg = StreamMessage(
                        type=MessageType.COMPLETE,
                        content="任务完成" if not message.is_error else "任务失败",
                        metadata={
                            "session_id": message.session_id,
                            "cost_usd": message.total_cost_usd,
                            "duration_ms": message.duration_ms,
                            "is_error": message.is_error,
                            "files_changed": self._files_changed.copy(),
                            "tools_used": self._tools_used.copy(),
                        },
                    )

                if stream_msg:
                    if on_message:
                        on_message(stream_msg)
                    yield stream_msg

            logger.info(f"[Client] 响应流结束，共收到 {message_count} 条消息")

            # 会话完整性延迟：
            # SDK 的 ResultMessage 发出时间早于 Claude Code 会话记录的完整写入时间。
            # 当 async with ClaudeSDKClient 上下文退出时，会话记录可能还在写入中，
            # 导致会话停留在 Assistant 的 "thinking" 阶段。
            # 此延迟确保会话记录有足够时间完成写入（在退出上下文之前执行，避免 cancel scope 冲突）。
            if self._session_id:
                logger.info(
                    f"[Client] 响应流结束，等待 {SESSION_WRITE_DELAY_SECONDS} 秒 "
                    f"确保会话记录完整写入 (session_id={self._session_id})"
                )
                await asyncio.sleep(SESSION_WRITE_DELAY_SECONDS)
                logger.info(
                    f"[Client] 会话完整性等待完成 (session_id={self._session_id})"
                )

            # 正常完成，标记不需要清理
            cleanup_needed = False

        except (GeneratorExit, asyncio.CancelledError):
            # 外部取消迭代（如 SSE 连接断开、调度器取消任务）
            logger.warning("[Client] run_stream 被外部取消")
            # 不再 yield，避免再次触发异常处理
            cleanup_needed = False  # 取消时不再清理，避免跨任务问题
            raise  # 重新抛出，让调用方处理

        except Exception as e:
            import traceback
            logger.error(f"[Client] run_stream 发生错误: {e}")
            logger.error(f"[Client] 错误堆栈:\n{traceback.format_exc()}")
            error_msg = StreamMessage(
                type=MessageType.ERROR,
                content=f"执行错误: {str(e)}",
            )
            if on_message:
                on_message(error_msg)
            yield error_msg
            cleanup_needed = False  # 错误已处理

        finally:
            # 只在需要时清理
            if cleanup_needed and sdk_client is not None:
                try:
                    await sdk_client.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"[Client] SDK 清理失败: {e}")

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
                # 注意：会话完整性延迟已在 run_stream 内部处理
                break
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

    # ========== 会话管理相关方法 ==========

    def set_session_id(self, session_id: str) -> None:
        """设置会话 ID"""
        self._session_id = session_id

    def get_session_id(self) -> Optional[str]:
        """获取当前会话 ID"""
        return self._session_id

    # ========== 问答功能相关方法（占位实现）=========
    # 注意: claude-agent-sdk v0.0.25 不支持问答功能
    # 以下方法为占位实现，等待 SDK 支持后完善

    def is_waiting_answer(self) -> bool:
        """
        检查是否正在等待用户回答

        当前 SDK 版本不支持问答功能，始终返回 False
        """
        return self._is_waiting_answer or self._is_waiting_for_answer

    def get_pending_question_id(self) -> Optional[str]:
        """
        获取待处理的问题 ID

        当前 SDK 版本不支持问答功能，始终返回 None
        """
        return self._pending_question_id

    async def submit_answer(self, answer_data: dict) -> bool:
        """
        提交用户答案

        当前 SDK 版本不支持问答功能，此方法为占位实现

        Args:
            answer_data: 答案数据，包含:
                - question_id: 问题 ID
                - answer: 用户答案
                - follow_up_answers: 追问答案（可选）
                - raw_question_data: 原始问题数据（可选）

        Returns:
            bool: 提交是否成功
        """
        question_id = answer_data.get("question_id")
        answer = answer_data.get("answer")

        # 检查是否有会话 ID
        if not self._session_id:
            logger.warning("submit_answer: 没有设置 session_id")
            return False

        # 检查答案是否为空
        if not answer:
            logger.warning(f"submit_answer: 答案为空, question_id={question_id}")
            return False

        # 检查问题状态
        if question_id in self._question_states:
            state = self._question_states[question_id]
            if state.get("status") != QuestionStatus.SHOWING_UPPER.value:
                logger.warning(
                    f"submit_answer: 问题状态不正确, question_id={question_id}, status={state.get('status')}"
                )
                return False

        # 存储答案
        self._pending_answer_value = answer_data
        self._is_waiting_for_answer = False
        self._is_waiting_answer = False  # 同步更新
        self._pending_question_id = None

        # 触发答案事件
        self._answer_event_value.set()

        logger.info(f"submit_answer: 答案已提交, question_id={question_id}")
        return True

    # 以下方法为测试兼容性占位实现

    async def _update_question_state(self, question_id: str, status: QuestionStatus) -> None:
        """更新问题状态（占位）"""
        if not hasattr(self, "_question_states"):
            self._question_states: dict[str, dict] = {}
        self._question_states[question_id] = {
            "status": status.value,
            "updated_at": 0,
            "metadata": {}
        }

    async def wait_for_answer(self, question_id: str, timeout: float = 30.0) -> Optional[dict]:
        """
        等待用户答案（占位，返回 None 表示超时）

        Args:
            question_id: 问题 ID
            timeout: 超时时间（秒）

        Returns:
            Optional[dict]: 答案数据，超时返回 None
        """
        try:
            await asyncio.wait_for(self._answer_event_value.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            # 超时，更新问题状态
            self._question_states[question_id] = {
                "status": QuestionStatus.TIMEOUT.value,
                "updated_at": 0,
                "metadata": {}
            }
            return None
        return self._pending_answer

    @property
    def _pending_answer(self) -> Optional[dict]:
        """待处理答案（占位）"""
        return self._pending_answer_value

    @_pending_answer.setter
    def _pending_answer(self, value: Optional[dict]) -> None:
        """设置待处理答案"""
        self._pending_answer_value = value

    @property
    def _answer_event(self) -> asyncio.Event:
        """答案事件（占位）"""
        return self._answer_event_value

    @_answer_event.setter
    def _answer_event(self, value: asyncio.Event) -> None:
        """设置答案事件"""
        self._answer_event_value = value


class ConcurrencyManager:
    """并发管理器（占位实现）"""

    def __init__(self, max_concurrent_questions: int = 10):
        self.max_concurrent_questions = max_concurrent_questions
        self.active_questions: dict[str, Any] = {}
        self._queue: list[tuple[str, str]] = []

    async def acquire_question_slot(self, session_id: str, question_id: str) -> bool:
        """获取问题槽位"""
        if len(self.active_questions) >= self.max_concurrent_questions:
            self._queue.append((session_id, question_id))
            return False
        self.active_questions[question_id] = {"session_id": session_id}
        return True

    async def release_question_slot(self, question_id: str) -> None:
        """释放问题槽位"""
        self.active_questions.pop(question_id, None)
        # 处理队列中的请求
        if self._queue:
            next_sid, next_qid = self._queue.pop(0)
            self.active_questions[next_qid] = {"session_id": next_sid}
