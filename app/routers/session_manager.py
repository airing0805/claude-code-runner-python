"""会话状态管理模块

管理活跃的 Claude Code 会话状态，支持问答暂停和恢复
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.claude_runner.client import ClaudeCodeClient

logger = logging.getLogger(__name__)


class SessionStateEnum(Enum):
    """会话状态枚举

    与技术设计档中的状态定义保持一致：
    - pending: 任务已提交，等待执行（注：当前实现中任务提交后直接开始执行，pending 状态为预留）
    - idle: 会话空闲，无活动
    - running: 任务执行中
    - waiting: 等待用户答案
    - completed: 任务已完成
    - failed: 会话错误
    """
    PENDING = "pending"
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def from_string(cls, state_str: str) -> "SessionStateEnum":
        """从字符串转换为枚举值"""
        try:
            return cls(state_str)
        except ValueError:
            # 兼容旧代码中的布尔值
            if state_str == "true" or state_str == "waiting":
                return cls.WAITING
            return cls.IDLE


# 状态优先级：running > waiting > pending > completed > failed > idle
STATE_PRIORITY = {
    SessionStateEnum.RUNNING: 5,
    SessionStateEnum.WAITING: 4,
    SessionStateEnum.PENDING: 3,
    SessionStateEnum.COMPLETED: 2,
    SessionStateEnum.FAILED: 1,
    SessionStateEnum.IDLE: 0,
}


class SessionStateMachine:
    """会话状态机

    管理会话状态转换，确保状态转换的合法性。
    """

    # 合法的状态转换表：(当前状态, 事件) -> 下一状态
    TRANSITIONS = {
        # 会话创建
        (None, "create"): SessionStateEnum.PENDING,
        # 任务开始执行
        (SessionStateEnum.PENDING, "task_start"): SessionStateEnum.RUNNING,
        # idle 状态启动任务
        (SessionStateEnum.IDLE, "task_start"): SessionStateEnum.RUNNING,
        # 收到 ask_user_question，进入等待状态
        (SessionStateEnum.RUNNING, "ask_question"): SessionStateEnum.WAITING,
        # 用户提交答案，继续执行
        (SessionStateEnum.WAITING, "answer_submitted"): SessionStateEnum.RUNNING,
        # 任务正常完成
        (SessionStateEnum.RUNNING, "task_complete"): SessionStateEnum.COMPLETED,
        # 任务执行出错
        (SessionStateEnum.RUNNING, "task_error"): SessionStateEnum.FAILED,
        # 等待状态出错（如超时）
        (SessionStateEnum.WAITING, "task_error"): SessionStateEnum.FAILED,
        # 等待状态超时
        (SessionStateEnum.WAITING, "timeout"): SessionStateEnum.FAILED,
        # 清理后进入 idle 状态
        (SessionStateEnum.COMPLETED, "cleanup"): SessionStateEnum.IDLE,
        (SessionStateEnum.FAILED, "cleanup"): SessionStateEnum.IDLE,
    }

    @classmethod
    def can_transition(cls, current_state: Optional[SessionStateEnum], event: str) -> bool:
        """检查是否可以进行状态转换"""
        return (current_state, event) in cls.TRANSITIONS

    @classmethod
    def get_next_state(cls, current_state: Optional[SessionStateEnum], event: str) -> Optional[SessionStateEnum]:
        """获取下一状态"""
        return cls.TRANSITIONS.get((current_state, event))

    @classmethod
    def transition(cls, current_state: Optional[SessionStateEnum], event: str) -> tuple[bool, Optional[SessionStateEnum]]:
        """执行状态转换

        Returns:
            (成功标志, 下一状态)
        """
        if cls.can_transition(current_state, event):
            next_state = cls.get_next_state(current_state, event)
            return True, next_state
        return False, None


@dataclass
class SessionStateData:
    """会话状态数据"""
    session_id: str
    client: ClaudeCodeClient  # 客户端引用
    state: SessionStateEnum = SessionStateEnum.IDLE
    # 使用系统时间而不是事件循环时间，确保会话过期判断准确
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)  # 最后活动时间
    cwd: Optional[str] = None  # 工作目录
    pending_question_id: Optional[str] = None

    @property
    def is_waiting(self) -> bool:
        """兼容旧代码：返回是否在等待状态"""
        return self.state == SessionStateEnum.WAITING

    @property
    def is_running(self) -> bool:
        """返回是否在运行状态"""
        return self.state == SessionStateEnum.RUNNING

    @property
    def is_completed(self) -> bool:
        """返回是否已完成"""
        return self.state == SessionStateEnum.COMPLETED

    @property
    def is_failed(self) -> bool:
        """返回是否失败"""
        return self.state == SessionStateEnum.FAILED


@dataclass
class SessionState:
    """会话状态（兼容旧接口）"""
    session_id: str
    client: ClaudeCodeClient
    is_waiting: bool = False
    # 使用系统时间而不是事件循环时间，确保会话过期判断准确
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)  # 最后活动时间
    cwd: Optional[str] = None  # 工作目录
    pending_question_id: Optional[str] = None


@dataclass
class SessionInfo:
    """会话信息（不含客户端）"""
    session_id: str
    is_waiting: bool
    pending_question_id: Optional[str]
    created_at: float
    last_activity: float  # 最后活动时间
    cwd: Optional[str] = None  # 工作目录


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self._sessions: dict[str, SessionStateData] = {}  # 使用新的状态数据结构
        self._legacy_sessions: dict[str, SessionState] = {}  # 兼容旧接口
        self._lock = asyncio.Lock()

    async def create_session(self, session_id: str, client: ClaudeCodeClient) -> SessionStateData:
        """创建新会话"""
        async with self._lock:
            state = SessionStateData(session_id=session_id, client=client, state=SessionStateEnum.PENDING)
            self._sessions[session_id] = state

            # 兼容旧接口：创建 SessionState 对象
            legacy_state = SessionState(session_id=session_id, client=client, is_waiting=False)
            self._legacy_sessions[session_id] = legacy_state

            logger.info(f"[SessionManager] 创建会话: session_id={session_id}, 初始状态={state.state.value}")
            return state

    async def get_session(self, session_id: str) -> Optional[SessionStateData]:
        """获取会话状态（带锁保护）"""
        async with self._lock:
            return self._sessions.get(session_id)

    async def get_legacy_session(self, session_id: str) -> Optional[SessionState]:
        """获取旧版会话状态（兼容旧接口）"""
        async with self._lock:
            return self._legacy_sessions.get(session_id)

    async def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息（不含客户端，带锁保护）"""
        async with self._lock:
            state = self._sessions.get(session_id)
            if not state:
                return None

            return SessionInfo(
                session_id=state.session_id,
                is_waiting=state.is_waiting,
                pending_question_id=state.pending_question_id or state.client.get_pending_question_id(),
                created_at=state.created_at,
                last_activity=state.last_activity,
                cwd=state.cwd,
            )

    async def list_sessions(self) -> list[SessionInfo]:
        """列出所有会话信息"""
        return [
            SessionInfo(
                session_id=state.session_id,
                is_waiting=state.is_waiting,
                pending_question_id=state.pending_question_id or state.client.get_pending_question_id(),
                created_at=state.created_at,
                last_activity=state.last_activity,
                cwd=state.cwd,
            )
            for state in self._sessions.values()
        ]

    async def remove_session(self, session_id: str) -> None:
        """移除会话"""
        async with self._lock:
            self._sessions.pop(session_id, None)
            self._legacy_sessions.pop(session_id, None)
            logger.info(f"[SessionManager] 移除会话: session_id={session_id}")

    async def transition_state(self, session_id: str, event: str) -> bool:
        """根据事件触发状态转换

        Args:
            session_id: 会话 ID
            event: 事件名称 (task_start, ask_question, answer_submitted, task_complete, task_error, cleanup)

        Returns:
            bool: 转换是否成功
        """
        async with self._lock:
            state = self._sessions.get(session_id)
            if not state:
                logger.warning(f"[SessionManager] transition_state: session_id={session_id} not found")
                return False

            current_state = state.state
            success, next_state = SessionStateMachine.transition(current_state, event)

            if success:
                old_state = state.state
                state.state = next_state
                state.last_activity = time.time()

                # 同步更新 legacy session 的 is_waiting
                legacy = self._legacy_sessions.get(session_id)
                if legacy:
                    legacy.is_waiting = state.is_waiting

                logger.info(
                    f"[SessionManager] 状态转换: session_id={session_id}, "
                    f"事件={event}, {old_state.value} -> {next_state.value}"
                )
                return True
            else:
                logger.warning(
                    f"[SessionManager] 非法状态转换: session_id={session_id}, "
                    f"当前状态={current_state.value if current_state else 'None'}, 事件={event}"
                )
                return False

    async def set_waiting(self, session_id: str, waiting: bool) -> None:
        """设置等待状态（兼容旧接口）

        内部使用状态机进行状态转换：
        - waiting=True 相当于 transition_state(session_id, 'ask_question')
        - waiting=False 相当于 transition_state(session_id, 'answer_submitted')
        """
        async with self._lock:
            state = self._sessions.get(session_id)
            if not state:
                logger.warning(f"[SessionManager] set_waiting: session_id={session_id} not found")
                return

            event = "ask_question" if waiting else "answer_submitted"
            success, next_state = SessionStateMachine.transition(state.state, event)

            if success:
                old_state = state.state
                old_waiting = state.is_waiting
                state.state = next_state
                state.last_activity = time.time()

                # 同步更新 legacy session
                legacy = self._legacy_sessions.get(session_id)
                if legacy:
                    legacy.is_waiting = state.is_waiting

                if old_waiting != waiting:
                    logger.info(
                        f"[SessionManager] set_waiting: session_id={session_id}, "
                        f"is_waiting: {old_waiting} -> {waiting} "
                        f"({old_state.value} -> {next_state.value})"
                    )
            else:
                # 兼容旧逻辑：强制设置 is_waiting
                old_waiting = state.is_waiting
                state.last_activity = time.time()

                legacy = self._legacy_sessions.get(session_id)
                if legacy:
                    legacy.is_waiting = waiting

                logger.warning(
                    f"[SessionManager] set_waiting: 状态转换失败，强制设置: "
                    f"session_id={session_id}, is_waiting: {old_waiting} -> {waiting}"
                )

    async def update_activity(self, session_id: str) -> None:
        """更新会话最后活动时间"""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].last_activity = time.time()
            else:
                logger.warning(
                    f"[SessionManager] update_activity: session_id={session_id} not found"
                )

    async def set_cwd(self, session_id: str, cwd: str) -> None:
        """设置会话工作目录"""
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].cwd = cwd
            else:
                logger.warning(
                    f"[SessionManager] set_cwd: session_id={session_id} not found"
                )

    async def get_session_state(self, session_id: str) -> Optional[SessionStateEnum]:
        """获取会话状态枚举"""
        async with self._lock:
            state = self._sessions.get(session_id)
            return state.state if state else None

    async def cleanup_old_sessions(
        self,
        max_age_seconds: float = 3600,
        activity_timeout: float = 1800,
        answer_timeout: float = 300,
    ) -> list[dict]:
        """清理过期会话

        根据需求文档 `当前会话-会话状态.md` 定义的三种超时类型：
        - 单次答案超时: 300 秒 (5 分钟) - 等待用户回答超时
        - 会话总超时: 3600 秒 (1 小时) - 会话创建后的最大生命周期
        - 活动超时: 1800 秒 (30 分钟) - 无活动后的超时

        Args:
            max_age_seconds: 会话总超时时间，默认 3600 秒（1 小时）
            activity_timeout: 活动超时时间，默认 1800 秒（30 分钟）
            answer_timeout: 答案等待超时时间，默认 300 秒（5 分钟）

        Returns:
            list[dict]: 被清理的会话列表，包含 session_id 和 timeout_reason
        """
        # 使用系统时间进行准确的过期判断
        current_time = time.time()
        to_remove = []
        removed_info = []

        async with self._lock:
            for session_id, state in self._sessions.items():
                session_age = current_time - state.created_at
                activity_age = current_time - state.last_activity

                # 确定超时原因
                timeout_reason = None

                # 1. 检查答案等待超时（仅对等待状态的会话）
                if state.is_waiting and activity_age > answer_timeout:
                    timeout_reason = "answer_timeout"
                    logger.info(
                        f"[SessionManager] 答案等待超时: session_id={session_id}, "
                        f"activity_age={activity_age:.0f}s, answer_timeout={answer_timeout}s"
                    )
                # 2. 检查会话总超时
                elif session_age > max_age_seconds:
                    timeout_reason = "session_timeout"
                    logger.info(
                        f"[SessionManager] 会话总超时: session_id={session_id}, "
                        f"session_age={session_age:.0f}s, max_age={max_age_seconds}s"
                    )
                # 3. 检查活动超时
                elif activity_age > activity_timeout:
                    timeout_reason = "activity_timeout"
                    logger.info(
                        f"[SessionManager] 活动超时: session_id={session_id}, "
                        f"activity_age={activity_age:.0f}s, activity_timeout={activity_timeout}s"
                    )

                if timeout_reason:
                    to_remove.append(session_id)
                    removed_info.append({
                        "session_id": session_id,
                        "timeout_reason": timeout_reason,
                        "session_age": session_age,
                        "activity_age": activity_age,
                        "is_waiting": state.is_waiting,
                    })

            for session_id in to_remove:
                # 触发 cleanup 事件转换状态
                state = self._sessions.get(session_id)
                if state:
                    # 尝试状态转换（允许失败，因为会话可能已在终态）
                    success, _ = SessionStateMachine.transition(state.state, "cleanup")
                    if success:
                        logger.info(f"[SessionManager] 状态转换 cleanup: session_id={session_id}")

                del self._sessions[session_id]
                self._legacy_sessions.pop(session_id, None)

        if to_remove:
            logger.info(f"[SessionManager] 清理过期会话: {len(to_remove)} 个")

        return removed_info


# 全局会话管理器实例
session_manager = SessionManager()
