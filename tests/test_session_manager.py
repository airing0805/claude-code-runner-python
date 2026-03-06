"""
后端单元测试 - SessionManager 测试

测试 SessionManager 类的所有方法，包括：
- 会话创建 (create_session)
- 会话查询 (get_session, get_session_info)
- 会话列表 (list_sessions)
- 会话移除 (remove_session)
- 等待状态设置 (set_waiting)
- 过期会话清理 (cleanup_old_sessions)
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.routers.session_manager import (
    SessionManager,
    SessionState,
    SessionInfo,
)


class TestSessionManagerCreation:
    """会话创建测试"""

    @pytest.mark.asyncio
    async def test_create_session(self):
        """测试创建新会话"""
        manager = SessionManager()

        # 创建 mock 客户端
        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value=None)

        # 创建会话
        session_id = "test-session-001"
        state = await manager.create_session(session_id, mock_client)

        # 验证会话创建成功
        assert state is not None
        assert state.session_id == session_id
        assert state.client == mock_client
        assert state.is_waiting is False

    @pytest.mark.asyncio
    async def test_create_multiple_sessions(self):
        """测试创建多个会话"""
        manager = SessionManager()

        # 创建多个会话
        for i in range(3):
            mock_client = MagicMock()
            mock_client.get_pending_question_id = MagicMock(return_value=None)

            session_id = f"test-session-{i:03d}"
            state = await manager.create_session(session_id, mock_client)

            assert state.session_id == session_id

        # 验证所有会话都被创建
        sessions = await manager.list_sessions()
        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_create_duplicate_session(self):
        """测试创建重复会话 ID"""
        manager = SessionManager()

        mock_client1 = MagicMock()
        mock_client1.get_pending_question_id = MagicMock(return_value=None)
        mock_client2 = MagicMock()
        mock_client2.get_pending_question_id = MagicMock(return_value=None)

        session_id = "duplicate-session"

        # 创建第一个会话
        state1 = await manager.create_session(session_id, mock_client1)
        assert state1.session_id == session_id

        # 创建第二个会话（覆盖）
        state2 = await manager.create_session(session_id, mock_client2)
        assert state2.session_id == session_id


class TestSessionManagerQuery:
    """会话查询测试"""

    @pytest.mark.asyncio
    async def test_get_existing_session(self):
        """测试获取已存在的会话"""
        manager = SessionManager()

        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value=None)

        session_id = "test-session-query"
        await manager.create_session(session_id, mock_client)

        # 获取会话
        state = await manager.get_session(session_id)

        assert state is not None
        assert state.session_id == session_id

    @pytest.mark.asyncio
    async def test_get_non_existing_session(self):
        """测试获取不存在的会话"""
        manager = SessionManager()

        # 获取不存在的会话
        state = await manager.get_session("non-existent-session")

        assert state is None

    @pytest.mark.asyncio
    async def test_get_session_info(self):
        """测试获取会话信息（不含客户端）"""
        manager = SessionManager()

        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value="pending-q1")

        session_id = "test-session-info"
        await manager.create_session(session_id, mock_client)

        # 获取会话信息
        info = await manager.get_session_info(session_id)

        assert info is not None
        assert isinstance(info, SessionInfo)
        assert info.session_id == session_id
        assert info.is_waiting is False
        assert info.pending_question_id == "pending-q1"

    @pytest.mark.asyncio
    async def test_get_session_info_non_existing(self):
        """测试获取不存在会话的信息"""
        manager = SessionManager()

        info = await manager.get_session_info("non-existent")

        assert info is None


class TestSessionManagerList:
    """会话列表测试"""

    @pytest.mark.asyncio
    async def test_list_empty_sessions(self):
        """测试列出空会话列表"""
        manager = SessionManager()

        sessions = await manager.list_sessions()

        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_all_sessions(self):
        """测试列出所有会话"""
        manager = SessionManager()

        # 创建多个会话
        for i in range(5):
            mock_client = MagicMock()
            mock_client.get_pending_question_id = MagicMock(return_value=None)

            session_id = f"test-session-{i:03d}"
            await manager.create_session(session_id, mock_client)

        # 列出所有会话
        sessions = await manager.list_sessions()

        assert len(sessions) == 5
        # 验证返回的是 SessionInfo 而不是 SessionState
        for session in sessions:
            assert isinstance(session, SessionInfo)


class TestSessionManagerRemove:
    """会话移除测试"""

    @pytest.mark.asyncio
    async def test_remove_existing_session(self):
        """测试移除已存在的会话"""
        manager = SessionManager()

        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value=None)

        session_id = "test-session-remove"
        await manager.create_session(session_id, mock_client)

        # 验证会话存在
        state = await manager.get_session(session_id)
        assert state is not None

        # 移除会话
        await manager.remove_session(session_id)

        # 验证会话已移除
        state = await manager.get_session(session_id)
        assert state is None

    @pytest.mark.asyncio
    async def test_remove_non_existing_session(self):
        """测试移除不存在的会话"""
        manager = SessionManager()

        # 尝试移除不存在的会话（不应该抛出异常）
        await manager.remove_session("non-existent-session")

        # 验证空列表
        sessions = await manager.list_sessions()
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_remove_all_sessions(self):
        """测试移除所有会话"""
        manager = SessionManager()

        # 创建多个会话
        for i in range(3):
            mock_client = MagicMock()
            mock_client.get_pending_question_id = MagicMock(return_value=None)

            session_id = f"test-session-{i}"
            await manager.create_session(session_id, mock_client)

        # 移除所有会话
        sessions = await manager.list_sessions()
        for session in sessions:
            await manager.remove_session(session.session_id)

        # 验证空列表
        sessions = await manager.list_sessions()
        assert len(sessions) == 0


class TestSessionManagerWaiting:
    """等待状态测试"""

    @pytest.mark.asyncio
    async def test_set_waiting_true(self):
        """测试设置等待状态为 True"""
        manager = SessionManager()

        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value=None)

        session_id = "test-session-waiting"
        await manager.create_session(session_id, mock_client)

        # 设置等待状态
        await manager.set_waiting(session_id, True)

        # 验证状态已更新
        state = await manager.get_session(session_id)
        assert state.is_waiting is True

    @pytest.mark.asyncio
    async def test_set_waiting_false(self):
        """测试设置等待状态为 False"""
        manager = SessionManager()

        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value=None)

        session_id = "test-session-waiting"
        await manager.create_session(session_id, mock_client)

        # 先设置为 True
        await manager.set_waiting(session_id, True)
        state = await manager.get_session(session_id)
        assert state.is_waiting is True

        # 再设置为 False
        await manager.set_waiting(session_id, False)

        # 验证状态已更新
        state = await manager.get_session(session_id)
        assert state.is_waiting is False

    @pytest.mark.asyncio
    async def test_set_waiting_non_existing_session(self):
        """测试设置不存在会话的等待状态"""
        manager = SessionManager()

        # 尝试设置不存在会话的等待状态（应该记录警告但不抛出异常）
        await manager.set_waiting("non-existent-session", True)

    @pytest.mark.asyncio
    async def test_set_waiting_no_change(self):
        """测试设置相同等待状态（无变化）"""
        manager = SessionManager()

        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value=None)

        session_id = "test-session-no-change"
        await manager.create_session(session_id, mock_client)

        # 初始状态为 False
        state = await manager.get_session(session_id)
        assert state.is_waiting is False

        # 再次设置为 False（无变化）
        await manager.set_waiting(session_id, False)

        # 验证状态未变
        state = await manager.get_session(session_id)
        assert state.is_waiting is False


class TestSessionManagerCleanup:
    """会话清理测试"""

    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(self):
        """测试清理过期会话"""
        manager = SessionManager()

        # 创建一个会话并将创建时间设置为过去
        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value=None)

        session_id = "old-session"
        state = await manager.create_session(session_id, mock_client)

        # 手动修改创建时间为 5 小时前（超过默认的 4 小时）
        state.created_at = time.time() - (5 * 3600)

        # 执行清理
        removed_count = await manager.cleanup_old_sessions(max_age_seconds=14400)  # 4 小时

        # 验证清理结果
        assert removed_count == 1

        # 验证会话已移除
        state = await manager.get_session(session_id)
        assert state is None

    @pytest.mark.asyncio
    async def test_cleanup_recent_sessions(self):
        """测试不清理最近的会话"""
        manager = SessionManager()

        # 创建一个新会话
        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value=None)

        session_id = "recent-session"
        await manager.create_session(session_id, mock_client)

        # 执行清理（1 秒超时）
        removed_count = await manager.cleanup_old_sessions(max_age_seconds=1)

        # 验证没有清理任何会话
        assert removed_count == 0

        # 验证会话仍然存在
        state = await manager.get_session(session_id)
        assert state is not None

    @pytest.mark.asyncio
    async def test_cleanup_mixed_sessions(self):
        """测试混合清理（有过期的也有新的）"""
        manager = SessionManager()

        # 创建 3 个会话，2 个旧的，1 个新的
        for i in range(3):
            mock_client = MagicMock()
            mock_client.get_pending_question_id = MagicMock(return_value=None)

            session_id = f"mixed-session-{i}"
            state = await manager.create_session(session_id, mock_client)

            # 前 2 个设置为旧的
            if i < 2:
                state.created_at = time.time() - (5 * 3600)

        # 执行清理
        removed_count = await manager.cleanup_old_sessions(max_age_seconds=14400)

        # 验证清理了 2 个
        assert removed_count == 2

        # 验证剩余 1 个
        sessions = await manager.list_sessions()
        assert len(sessions) == 1


class TestSessionManagerConcurrency:
    """并发测试"""

    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self):
        """测试并发创建会话"""
        manager = SessionManager()

        async def create_session_task(i):
            mock_client = MagicMock()
            mock_client.get_pending_question_id = MagicMock(return_value=None)
            session_id = f"concurrent-session-{i}"
            return await manager.create_session(session_id, mock_client)

        # 并发创建 10 个会话
        results = await asyncio.gather(*[create_session_task(i) for i in range(10)])

        # 验证所有会话都创建成功
        assert len(results) == 10

        # 验证所有会话都在列表中
        sessions = await manager.list_sessions()
        assert len(sessions) == 10

    @pytest.mark.asyncio
    async def test_concurrent_session_access(self):
        """测试并发访问会话"""
        manager = SessionManager()

        mock_client = MagicMock()
        mock_client.get_pending_question_id = MagicMock(return_value=None)

        session_id = "concurrent-access-session"
        await manager.create_session(session_id, mock_client)

        async def access_session():
            for _ in range(100):
                await manager.get_session(session_id)
                await asyncio.sleep(0.001)

        # 并发访问同一个会话
        await asyncio.gather(*[access_session() for _ in range(5)])

        # 验证会话仍然存在
        state = await manager.get_session(session_id)
        assert state is not None


class TestSessionInfo:
    """SessionInfo 数据类测试"""

    def test_session_info_creation(self):
        """测试创建 SessionInfo"""
        info = SessionInfo(
            session_id="test-001",
            is_waiting=True,
            pending_question_id="q1",
            created_at=time.time(),
        )

        assert info.session_id == "test-001"
        assert info.is_waiting is True
        assert info.pending_question_id == "q1"

    def test_session_info_with_none_question(self):
        """测试无待处理问题时的 SessionInfo"""
        info = SessionInfo(
            session_id="test-002",
            is_waiting=False,
            pending_question_id=None,
            created_at=time.time(),
        )

        assert info.session_id == "test-002"
        assert info.is_waiting is False
        assert info.pending_question_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
