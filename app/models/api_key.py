"""API 密钥数据模型"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class APIKey:
    """API 密钥模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str = ""
    key_hash: str = ""  # 存储哈希值，不存储明文
    prefix: str = ""  # sk-ccr-xxx... (只显示前8位)
    permissions: str = "read_write"  # read_only | read_write
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """转换为字典（不包含敏感信息）"""
        return {
            "key_id": self.id,
            "name": self.name,
            "prefix": self.prefix,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def to_response(self) -> dict:
        """转换为 API 响应（不含敏感信息）"""
        return self.to_dict()


@dataclass
class APIKeyCreateResponse:
    """API 密钥创建响应（包含明文密钥，只显示一次）"""
    key_id: str
    name: str
    key: str  # 明文密钥，只在创建时返回一次
    prefix: str
    permissions: str
    created_at: str


@dataclass
class APIKeyWithMeta:
    """API 密钥列表项"""
    key_id: str
    name: str
    prefix: str
    permissions: str
    is_active: bool
    created_at: str
    last_used_at: Optional[str]
    expires_at: Optional[str]
