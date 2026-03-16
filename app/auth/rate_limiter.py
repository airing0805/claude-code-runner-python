"""登录限流器模块"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException

from app.models.token import RateLimitRecord

logger = logging.getLogger(__name__)

# 限流配置
MAX_ATTEMPTS = 10  # 同一 IP 5 分钟内最多 10 次
WINDOW_MINUTES = 5  # 时间窗口（分钟）


class RateLimiter:
    """
    登录限流器

    规则：同一 IP 5 分钟内最多 10 次登录尝试
    """

    def __init__(
        self,
        max_attempts: int = MAX_ATTEMPTS,
        window_minutes: int = WINDOW_MINUTES,
    ):
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self._records: dict[str, RateLimitRecord] = defaultdict(
            lambda: RateLimitRecord(
                ip_address="",
                reset_at=datetime.now(timezone.utc) + timedelta(minutes=window_minutes),
            )
        )

    async def check(self, ip: str) -> None:
        """
        检查是否允许登录

        Raises:
            HTTPException: 如果超过限制则抛出 429 错误
        """
        record = self._records.get(ip)
        now = datetime.now(timezone.utc)

        if record is None:
            # 首次尝试，创建新记录
            self._records[ip] = RateLimitRecord(
                ip_address=ip,
                attempt_count=0,
                first_attempt=now,
                reset_at=now + timedelta(minutes=self.window_minutes),
            )
            return

        # 检查是否在限制期内
        if now < record.reset_at:
            if record.attempt_count >= self.max_attempts:
                retry_after = int((record.reset_at - now).total_seconds())
                raise HTTPException(
                    status_code=429,
                    detail="登录尝试过于频繁，请 5 分钟后再试",
                    headers={"Retry-After": str(retry_after)},
                )
        else:
            # 超过限制期，重置记录
            record.attempt_count = 0
            record.first_attempt = now
            record.reset_at = now + timedelta(minutes=self.window_minutes)

    async def record(self, ip: str) -> None:
        """
        记录失败登录

        Args:
            ip: 客户端 IP 地址
        """
        record = self._records.get(ip)

        if record is None:
            # 首次尝试
            now = datetime.now(timezone.utc)
            self._records[ip] = RateLimitRecord(
                ip_address=ip,
                attempt_count=1,
                first_attempt=now,
                reset_at=now + timedelta(minutes=self.window_minutes),
            )
        else:
            # 增加计数
            record.attempt_count += 1

    def get_remaining_attempts(self, ip: str) -> int:
        """
        获取剩余尝试次数

        Args:
            ip: 客户端 IP 地址

        Returns:
            剩余尝试次数
        """
        record = self._records.get(ip)
        if record is None:
            return self.max_attempts

        now = datetime.now(timezone.utc)
        if now >= record.reset_at:
            return self.max_attempts

        return max(0, self.max_attempts - record.attempt_count)

    def reset(self, ip: str) -> None:
        """
        重置限流记录

        Args:
            ip: 客户端 IP 地址
        """
        if ip in self._records:
            del self._records[ip]


# 全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取全局限流器实例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
