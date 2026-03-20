"""Claude Agent SDK 客户端封装 - 支持流式输出"""

import asyncio
import json
import logging
import os
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
    ASK_USER_QUESTION = "ask_user_question"  # 用户问答类型


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
    tool_use_id: Optional[str] = None  # 工具调用 ID，用于 tool_use 和 tool_result 配对
    metadata: dict = field(default_factory=dict)
    question: Optional[QuestionData] = None  # 问答数据（SDK 当前不支持）


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None  # 使用的模型
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
        self._model: Optional[str] = None  # 使用的模型
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
            max_buffer_size=1024 * 1024,  # 限制缓冲区为 1MB，防止 Windows 崩溃
        )

    async def _track_tool_use(self, tool_name: str, tool_input: dict) -> None:
        """跟踪工具使用和文件变更"""
        if tool_name not in self._tools_used:
            self._tools_used.append(tool_name)

        # 跟踪文件变更 - Write 和 Edit
        if tool_name in ("Write", "Edit"):
            file_path = tool_input.get("file_path", "")
            if file_path and file_path not in self._files_changed:
                self._files_changed.append(file_path)

        # 跟踪文件变更 - Bash 命令
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            if command:
                # 提取 Bash 命令中的文件路径
                file_paths = self._extract_bash_file_paths(command)
                for file_path in file_paths:
                    if file_path and file_path not in self._files_changed:
                        self._files_changed.append(file_path)

    def _extract_bash_file_paths(self, command: str) -> list[str]:
        """
        从 Bash 命令中提取文件路径

        支持的命令模式:
        - rm <file>
        - mv <src> <dst>
        - cp <src> <dst>
        - echo "..." > <file>
        - cat ... > <file>
        - tee <file>
        - touch <file>
        - mkdir -p <dir> (不跟踪目录)
        - install <src> <dst>

        Args:
            command: Bash 命令字符串

        Returns:
            文件路径列表
        """
        import re

        file_paths: list[str] = []
        command = command.strip()

        # 重定向模式: > file 或 >> file
        # 匹配 "anything > file" 或 "anything >> file"
        redirect_pattern = r'>\s*([^\s>]+)'
        matches = re.findall(redirect_pattern, command)
        for match in matches:
            # 清理引号
            file_path = match.strip('"\'')
            if file_path and file_path not in file_paths:
                file_paths.append(file_path)

        # tee 命令: tee [options] file
        if command.startswith('tee '):
            # 匹配 tee 后的文件参数（不是以 - 开头的）
            parts = command[4:].split()
            for part in parts:
                if not part.startswith('-') and part not in ('>', '>>'):
                    if part not in file_paths:
                        file_paths.append(part)

        # touch 命令: touch file1 file2 ...
        if command.startswith('touch '):
            parts = command[6:].split()
            for part in parts:
                if not part.startswith('-'):
                    if part not in file_paths:
                        file_paths.append(part)

        # rm 命令: rm [options] file1 file2 ...
        # 但排除 rf/r 之类的选项
        if command.startswith('rm '):
            parts = command[3:].split()
            for part in parts:
                if part.startswith('-'):
                    continue  # 跳过选项
                if part not in file_paths:
                    file_paths.append(part)

        # mv 命令: mv src dst
        if command.startswith('mv '):
            parts = command[3:].split()
            # 跳过前两个参数（src），第三个开始可能是 dst 或选项
            if len(parts) >= 2:
                # 最后一个非选项参数通常是目标
                for part in reversed(parts):
                    if not part.startswith('-'):
                        if part not in file_paths:
                            file_paths.append(part)
                        break

        # cp 命令: cp src dst
        if command.startswith('cp '):
            parts = command[3:].split()
            # 跳过前两个参数（src），第三个开始可能是 dst 或选项
            if len(parts) >= 2:
                for part in reversed(parts):
                    if not part.startswith('-'):
                        if part not in file_paths:
                            file_paths.append(part)
                        break

        return file_paths

    def _parse_question_from_tool(
        self, tool_name: str, tool_input: dict, tool_use_id: Optional[str]
    ) -> "QuestionData":
        """
        从工具调用中解析问答数据

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数
            tool_use_id: 工具调用 ID

        Returns:
            QuestionData: 解析后的问答数据
        """
        question_id = tool_use_id or str(uuid.uuid4())

        # 尝试从工具输入中提取问题文本
        question_text = (
            tool_input.get("prompt")
            or tool_input.get("question")
            or tool_input.get("message")
            or tool_input.get("reason")
            or str(tool_input)
        )

        # 尝试提取问题类型
        question_type = tool_input.get("type", "single_choice")

        # 尝试提取标题
        header = tool_input.get("header", "需要您的确认")

        # 尝试提取描述
        description = tool_input.get("description", "")

        # 尝试提取选项
        options = None
        if "options" in tool_input:
            raw_options = tool_input["options"]
            if isinstance(raw_options, list):
                options = [
                    QuestionOption(
                        id=opt.get("id", str(idx)),
                        label=opt.get("label", str(opt)),
                        description=opt.get("description", ""),
                        default=opt.get("default"),
                    )
                    for idx, opt in enumerate(raw_options)
                ]

        return QuestionData(
            question_id=question_id,
            question_text=question_text,
            type=question_type,
            header=header,
            description=description,
            required=True,
            raw_tool_input=tool_input,
        )

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
        old_claudecode = os.environ.pop("CLAUDECODE", None)
        logger.info(f"[Client] 清除 CLAUDECODE 环境变量, 原值={old_claudecode}")

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
                    # 记录使用的模型（首次捕获）
                    if not self._model and hasattr(message, 'model'):
                        self._model = message.model
                        logger.info(f"[Client] 使用模型: {self._model}")

                    for block in message.content:
                        # 文本内容
                        if hasattr(block, "text") and block.text:
                            stream_msg = StreamMessage(
                                type=MessageType.TEXT,
                                content=block.text,
                            )
                        # 思考过程
                        elif hasattr(block, "thinking") and block.thinking:
                            stream_msg = StreamMessage(
                                type=MessageType.THINKING,
                                content=block.thinking,
                            )
                        # 工具调用
                        elif hasattr(block, "name"):
                            tool_name = block.name
                            tool_input = getattr(block, "input", {})
                            tool_use_id = getattr(block, "id", None)  # 获取工具调用 ID

                            await self._track_tool_use(tool_name, tool_input)

                            # 检测权限请求/问答工具调用
                            # 这些工具名称表示 SDK 正在等待用户回答
                            is_permission_tool = tool_name in (
                                "AskUserQuestion",
                                "ask_user_question",
                                "AskPermission",
                                "ask_permission",
                                "PermissionAsk",
                                "permission_ask",
                            ) or tool_name.lower().startswith(("ask", "permission"))

                            if is_permission_tool:
                                # 设置等待状态
                                self._is_waiting_for_answer = True
                                self._is_waiting_answer = True
                                self._pending_question_id = tool_use_id or str(uuid.uuid4())

                                logger.info(
                                    f"[Client] 检测到权限请求工具: tool_name={tool_name}, "
                                    f"question_id={self._pending_question_id}"
                                )

                                # 生成问答消息
                                question_data = self._parse_question_from_tool(tool_name, tool_input, tool_use_id)
                                stream_msg = StreamMessage(
                                    type=MessageType.ASK_USER_QUESTION,
                                    content=tool_input.get("prompt", "") or tool_input.get("question", "") or f"需要确认: {tool_name}",
                                    tool_name=tool_name,
                                    tool_input=tool_input,
                                    tool_use_id=tool_use_id,
                                    question=question_data,
                                )
                            else:
                                stream_msg = StreamMessage(
                                    type=MessageType.TOOL_USE,
                                    content=f"调用工具: {tool_name}",
                                    tool_name=tool_name,
                                    tool_input=tool_input,
                                    tool_use_id=tool_use_id,  # 传递工具调用 ID
                                )
                        # 工具结果
                        elif hasattr(block, "tool_use_id"):
                            tool_result_content = getattr(block, "content", None)
                            if isinstance(tool_result_content, str):
                                content_str = tool_result_content
                            elif isinstance(tool_result_content, list):
                                content_str = json.dumps(tool_result_content, ensure_ascii=False)
                            else:
                                content_str = str(tool_result_content) if tool_result_content else ""

                            is_error = getattr(block, "is_error", False)
                            tool_use_id = block.tool_use_id  # 获取关联的工具调用 ID

                            stream_msg = StreamMessage(
                                type=MessageType.TOOL_RESULT,
                                content=content_str,
                                tool_use_id=tool_use_id,  # 传递工具调用 ID，用于与 tool_use 配对
                                metadata={"is_error": is_error, "tool_use_id": tool_use_id} if is_error else {"tool_use_id": tool_use_id},
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
                            "model": self._model,
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

        except asyncio.CancelledError:
            # 外部取消迭代（如 SSE 连接断开、调度器取消任务）
            logger.warning("[Client] run_stream 被外部取消 (CancelledError)")
            # 重新抛出，让 finally 块处理清理
            # Python 的 CancelledError 会在 finally 执行后继续传播
            raise

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

        finally:
            # 始终尝试清理 SDK 客户端
            # 注意：如果在已取消的任务中调用 __aexit__，可能会抛出 cancel scope 错误
            # 这是 asyncio 的限制，我们需要捕获并记录，但不应影响环境变量恢复
            if sdk_client is not None:
                try:
                    await sdk_client.__aexit__(None, None, None)
                    logger.info("[Client] SDK 客户端已清理")
                except Exception as e:
                    # 记录错误但不传播
                    # 常见错误："Attempted to exit cancel scope in a different task"
                    # 这通常发生在任务被取消后的清理过程中
                    logger.warning(f"[Client] SDK 清理失败（可能因任务取消）: {e}")

            # 恢复环境变量（无论清理是否成功）
            if old_claudecode is not None:
                os.environ["CLAUDECODE"] = old_claudecode
                logger.debug("[Client] CLAUDECODE 环境变量已恢复")

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
        model = None
        cost_usd = 0.0
        duration_ms = 0
        is_error = False

        async for msg in self.run_stream(prompt):
            if msg.type == MessageType.TEXT:
                texts.append(msg.content)
            elif msg.type == MessageType.COMPLETE:
                session_id = msg.metadata.get("session_id")
                model = msg.metadata.get("model")
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
            model=model,
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

    # ========== 问答功能相关方法 ==========

    def is_waiting_answer(self) -> bool:
        """
        检查是否正在等待用户回答

        Returns:
            bool: 如果正在等待用户回答返回 True，否则返回 False
        """
        return self._is_waiting_answer or self._is_waiting_for_answer

    def get_pending_question_id(self) -> Optional[str]:
        """
        获取待处理的问题 ID

        Returns:
            Optional[str]: 待处理的问题 ID，如果没有则返回 None
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

    async def wait_for_answer(self, question_id: str, timeout: float = 300.0) -> Optional[dict]:
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
