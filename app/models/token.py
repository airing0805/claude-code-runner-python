"""Token 和限流数据模型"""

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class TokenPayload:
    """JWT Token 载荷"""
    sub: str  # user_id
    exp: int  # 过期时间戳
    iat: int  # 签发时间戳
    type: str  # token 类型: access / refresh
    jti: Optional[str] = None  # JWT ID，用于黑名单追踪


@dataclass
class LoginResult:
    """登录结果"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


@dataclass
class TokenBlacklistEntry:
    """Token 黑名单条目"""
    jti: str = ""  # JWT ID
    user_id: str = ""
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1))

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "jti": self.jti,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TokenBlacklistEntry":
        """从字典创建"""
        expires_at = data.get("expires_at")
        if expires_at and isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        return cls(
            jti=data.get("jti", ""),
            user_id=data.get("user_id", ""),
            expires_at=expires_at,
        )


@dataclass
class RateLimitRecord:
    """限流记录"""
    ip_address: str = ""
    attempt_count: int = 0
    first_attempt: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reset_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=5))

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "ip_address": self.ip_address,
            "attempt_count": self.attempt_count,
            "first_attempt": self.first_attempt.isoformat() if self.first_attempt else None,
            "reset_at": self.reset_at.isoformat() if self.reset_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RateLimitRecord":
        """从字典创建"""
        first_attempt = data.get("first_attempt")
        if first_attempt and isinstance(first_attempt, str):
            first_attempt = datetime.fromisoformat(first_attempt)

        reset_at = data.get("reset_at")
        if reset_at and isinstance(reset_at, str):
            reset_at = datetime.fromisoformat(reset_at)

        return cls(
            ip_address=data.get("ip_address", ""),
            attempt_count=data.get("attempt_count", 0),
            first_attempt=first_attempt,
            reset_at=reset_at,
        )
