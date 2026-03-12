"""认证存储层 - JSONL 文件存储"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.models.api_key import APIKey
from app.models.token import RateLimitRecord, TokenBlacklistEntry
from app.models.user import User

logger = logging.getLogger(__name__)

# 存储目录
DATA_DIR = Path("data/auth")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 文件路径
USERS_FILE = DATA_DIR / "users.jsonl"
KEYS_FILE = DATA_DIR / "keys.jsonl"
TOKEN_BLACKLIST_FILE = DATA_DIR / "token_blacklist.jsonl"
RATE_LIMIT_FILE = DATA_DIR / "rate_limit.jsonl"


class UserStorage:
    """用户存储"""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.users_file = data_dir / "users.jsonl"
        self.users_file.touch(exist_ok=True)

    async def create(self, user: User) -> None:
        """创建用户"""
        with open(self.users_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(user.to_dict()) + "\n")

    async def get_by_username(self, username: str) -> Optional[User]:
        """按用户名查询"""
        with open(self.users_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                user_data = json.loads(line)
                if user_data.get("username") == username:
                    return User(**user_data)
        return None

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """按 ID 查询"""
        with open(self.users_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                user_data = json.loads(line)
                if user_data.get("user_id") == user_id:
                    return User(**user_data)
        return None

    async def update(self, user: User) -> None:
        """更新用户"""
        users = []
        with open(self.users_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                user_data = json.loads(line)
                if user_data.get("user_id") == user.id:
                    users.append(user.to_dict())
                else:
                    users.append(user_data)

        with open(self.users_file, "w", encoding="utf-8") as f:
            for user_data in users:
                f.write(json.dumps(user_data) + "\n")

    async def list_paginated(self, page: int = 1, limit: int = 20) -> tuple[list[User], int]:
        """
        分页获取用户列表

        Returns:
            (用户列表, 总数)
        """
        users = []
        total = 0

        with open(self.users_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                total += 1
                # 跳过不需要的页
                skip = (page - 1) * limit
                if skip > 0:
                    skip -= 1
                    continue
                # 达到限制数量后停止
                if len(users) >= limit:
                    break

                user_data = json.loads(line)
                users.append(User(**user_data))

        return users, total


class APIKeyStorage:
    """API 密钥存储"""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.keys_file = data_dir / "keys.jsonl"
        self.keys_file.touch(exist_ok=True)

    async def create(self, api_key: APIKey) -> None:
        """创建密钥"""
        with open(self.keys_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(api_key.to_dict()) + "\n")

    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """按密钥哈希查询"""
        with open(self.keys_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                key_data = json.loads(line)
                if key_data.get("key_hash") == key_hash and key_data.get("is_active"):
                    return APIKey(**key_data)
        return None

    async def get_by_id(self, key_id: str) -> Optional[APIKey]:
        """按密钥 ID 查询"""
        with open(self.keys_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                key_data = json.loads(line)
                if key_data.get("key_id") == key_id:
                    return APIKey(**key_data)
        return None

    async def list_by_user(self, user_id: str) -> list[APIKey]:
        """列出用户的所有密钥"""
        keys = []
        with open(self.keys_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                key_data = json.loads(line)
                if key_data.get("user_id") == user_id:
                    keys.append(APIKey(**key_data))
        return keys

    async def update(self, api_key: APIKey) -> None:
        """更新密钥"""
        keys = []
        with open(self.keys_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                key_data = json.loads(line)
                if key_data.get("key_id") == api_key.id:
                    keys.append(api_key.to_dict())
                else:
                    keys.append(key_data)

        with open(self.keys_file, "w", encoding="utf-8") as f:
            for key_data in keys:
                f.write(json.dumps(key_data) + "\n")


class TokenBlacklistStorage:
    """Token 黑名单存储"""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.blacklist_file = data_dir / "token_blacklist.jsonl"
        self.blacklist_file.touch(exist_ok=True)

    async def add(self, jti: str, user_id: str, expires_at: datetime) -> None:
        """添加黑名单"""
        entry = TokenBlacklistEntry(
            jti=jti,
            user_id=user_id,
            expires_at=expires_at,
        )
        with open(self.blacklist_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    async def is_blacklisted(self, jti: str) -> bool:
        """检查是否在黑名单中"""
        now = datetime.now(timezone.utc)
        with open(self.blacklist_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry.get("jti") == jti:
                    # 检查是否过期
                    expires_at_str = entry.get("expires_at")
                    if expires_at_str:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if expires_at > now:
                            return True
        return False

    async def cleanup(self) -> None:
        """清理过期条目"""
        now = datetime.now(timezone.utc)
        valid_entries = []

        with open(self.blacklist_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                expires_at_str = entry.get("expires_at")
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if expires_at > now:
                        valid_entries.append(entry)

        with open(self.blacklist_file, "w", encoding="utf-8") as f:
            for entry in valid_entries:
                f.write(json.dumps(entry) + "\n")


class RateLimitStorage:
    """限流记录存储"""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.rate_limit_file = data_dir / "rate_limit.jsonl"
        self.rate_limit_file.touch(exist_ok=True)

    async def get(self, ip_address: str) -> Optional[RateLimitRecord]:
        """获取限流记录"""
        with open(self.rate_limit_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("ip_address") == ip_address:
                    return RateLimitRecord.from_dict(record)
        return None

    async def save(self, record: RateLimitRecord) -> None:
        """保存限流记录"""
        records = []
        found = False

        with open(self.rate_limit_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("ip_address") == record.ip_address:
                    records.append(record.to_dict())
                    found = True
                else:
                    records.append(r)

        if not found:
            records.append(record.to_dict())

        with open(self.rate_limit_file, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    async def cleanup(self) -> None:
        """清理过期记录"""
        now = datetime.now(timezone.utc)
        valid_records = []

        with open(self.rate_limit_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                reset_at_str = record.get("reset_at")
                if reset_at_str:
                    reset_at = datetime.fromisoformat(reset_at_str)
                    if reset_at > now:
                        valid_records.append(record)

        with open(self.rate_limit_file, "w", encoding="utf-8") as f:
            for record in valid_records:
                f.write(json.dumps(record) + "\n")
