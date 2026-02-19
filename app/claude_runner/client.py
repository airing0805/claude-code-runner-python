"""Claude Code SDK 客户端封装 - 支持流式输出"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Optional

from claude_code_sdk import (
    ClaudeCodeOptions,
    ClaudeSDKClient,
    AssistantMessage,
    ResultMessage,
)
from typing import Literal

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


@dataclass
class StreamMessage:
    """流式消息"""
    type: MessageType
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    metadata: dict = field(default_factory=dict)


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

                                stream_msg = StreamMessage(
                                    type=MessageType.TOOL_USE,
                                    content=f"调用工具: {tool_name}",
                                    tool_name=tool_name,
                                    tool_input=tool_input,
                                )

                    elif isinstance(message, ResultMessage):
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
