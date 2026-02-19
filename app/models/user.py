"""用户数据模型"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class User:
    """用户模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    hashed_password: str = ""
    name: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """转换为字典（不包含敏感信息）"""
        return {
            "user_id": self.id,
            "username": self.username,
            "name": self.name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class TokenData:
    """Token 数据"""
    user_id: str
    username: str
    exp: datetime


@dataclass
class Token:
    """Token 响应"""
    access_token: str
    token_type: str
    expires_in: int
