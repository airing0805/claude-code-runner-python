"""会话状态管理模块

管理活跃的 Claude Code 会话状态，支持问答暂停和恢复
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.claude_runner.client import ClaudeCodeClient

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """会话状态"""
    session_id: str
    client: ClaudeCodeClient
    is_waiting: bool = False
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    pending_question_id: Optional[str] = None


@dataclass
class SessionInfo:
    """会话信息（不含客户端）"""
    session_id: str
    is_waiting: bool
    pending_question_id: Optional[str]
    created_at: float


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, session_id: str, client: ClaudeCodeClient) -> SessionState:
        """创建新会话"""
        async with self._lock:
            state = SessionState(session_id=session_id, client=client)
            self._sessions[session_id] = state
            return state

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """获取会话状态"""
        return self._sessions.get(session_id)

    async def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息（不含客户端）"""
        state = self._sessions.get(session_id)
        if not state:
            return None

        return SessionInfo(
            session_id=state.session_id,
            is_waiting=state.is_waiting,
            pending_question_id=state.client.get_pending_question_id(),
            created_at=state.created_at,
        )

    async def list_sessions(self) -> list[SessionInfo]:
        """列出所有会话信息"""
        return [
            SessionInfo(
                session_id=state.session_id,
                is_waiting=state.is_waiting,
                pending_question_id=state.client.get_pending_question_id(),
                created_at=state.created_at,
            )
            for state in self._sessions.values()
        ]

    async def remove_session(self, session_id: str) -> None:
        """移除会话"""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def set_waiting(self, session_id: str, waiting: bool) -> None:
        """设置等待状态"""
        async with self._lock:
            if session_id in self._sessions:
                old_value = self._sessions[session_id].is_waiting
                self._sessions[session_id].is_waiting = waiting
                if old_value != waiting:
                    logger.info(
                        f"[SessionManager] set_waiting: session_id={session_id}, "
                        f"is_waiting: {old_value} -> {waiting}"
                    )
            else:
                logger.warning(
                    f"[SessionManager] set_waiting: session_id={session_id} not found"
                )

    async def cleanup_old_sessions(self, max_age_seconds: float = 14400) -> int:
        """清理过期会话"""
        current_time = asyncio.get_event_loop().time()
        to_remove = []

        async with self._lock:
            for session_id, state in self._sessions.items():
                if current_time - state.created_at > max_age_seconds:
                    to_remove.append(session_id)

            for session_id in to_remove:
                del self._sessions[session_id]

        return len(to_remove)


# 全局会话管理器实例
session_manager = SessionManager()
