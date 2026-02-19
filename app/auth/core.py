"""认证核心模块 - JWT 令牌和密码哈希"""

import hashlib
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.models.api_key import APIKey
from app.models.user import TokenData, User

# JWT 配置
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "1"))
SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())

# 用户存储（内存）- 生产环境应使用数据库
_users_db: dict[str, User] = {}

# API Key 存储（内存）- 生产环境应使用数据库
_api_keys_db: dict[str, APIKey] = {}  # key_id -> APIKey
_api_keys_by_hash: dict[str, str] = {}  # key_hash -> key_id


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    """哈希密码"""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度

    要求:
    - 最小长度 8 位
    - 必须包含字母和数字

    Returns:
        (是否有效, 错误消息)
    """
    if len(password) < 8:
        return False, "密码长度至少为 8 位"

    if not re.search(r"[a-zA-Z]", password):
        return False, "密码必须包含字母"

    if not re.search(r"[0-9]", password):
        return False, "密码必须包含数字"

    return True, ""


def create_access_token(user: User) -> str:
    """创建访问令牌"""
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "user_id": user.id,
        "username": user.username,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """解码访问令牌"""
    from datetime import timezone

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        username: str = payload.get("username")
        exp: int = payload.get("exp")  # JWT 返回的是 Unix 时间戳（秒）

        if user_id is None or username is None:
            return None

        # 转换 Unix 时间戳为 datetime
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)

        return TokenData(
            user_id=user_id,
            username=username,
            exp=exp_datetime,
        )
    except JWTError:
        return None


def get_user_by_username(username: str) -> Optional[User]:
    """根据用户名获取用户"""
    return _users_db.get(username)


def get_user_by_id(user_id: str) -> Optional[User]:
    """根据用户 ID 获取用户"""
    for user in _users_db.values():
        if user.id == user_id:
            return user
    return None


def create_user(username: str, password: str, name: str) -> Optional[User]:
    """创建新用户"""
    # 检查用户名是否已存在
    if username in _users_db:
        return None

    # 验证密码强度
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise ValueError(error_msg)

    # 创建用户
    user = User(
        username=username,
        hashed_password=hash_password(password),
        name=name,
    )
    _users_db[username] = user
    return user


def authenticate_user(username: str, password: str) -> Optional[User]:
    """验证用户凭据"""
    user = get_user_by_username(username)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def update_user_password(user_id: str, new_password: str) -> bool:
    """更新用户密码"""
    user = get_user_by_id(user_id)
    if user is None:
        return False

    # 验证新密码强度
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        raise ValueError(error_msg)

    user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    return True


def generate_api_key(user: User) -> str:
    """生成 API Key (与 create_api_key 格式一致)"""
    import uuid

    # 使用 sk-ccr- 前缀以与 create_api_key 一致
    return f"sk-ccr-{uuid.uuid4().hex}"


def verify_api_key(api_key: str) -> Optional[User]:
    """验证 API Key"""
    # 检查前缀 (只接受 sk-ccr- 开头的密钥)
    if not api_key.startswith("sk-ccr-"):
        return None

    # 计算哈希值
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # 查找密钥
    key_id = _api_keys_by_hash.get(key_hash)
    if key_id is None:
        return None

    api_key_obj = _api_keys_db.get(key_id)
    if api_key_obj is None:
        return None

    # 检查是否激活
    if not api_key_obj.is_active:
        return None

    # 检查是否过期
    if api_key_obj.expires_at is not None and api_key_obj.expires_at < datetime.now(timezone.utc):
        return None

    # 更新最后使用时间
    api_key_obj.last_used_at = datetime.now(timezone.utc)

    # 返回用户
    return get_user_by_id(api_key_obj.user_id)


def _hash_api_key(api_key: str) -> str:
    """计算 API Key 的哈希值"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def create_api_key(
    user_id: str,
    name: str,
    permissions: str = "read_write",
    expires_at: Optional[datetime] = None,
) -> tuple[APIKey, str]:
    """
    创建 API Key

    Args:
        user_id: 用户 ID
        name: 密钥名称
        permissions: 权限 (read_only | read_write)
        expires_at: 过期时间

    Returns:
        (APIKey 对象, 明文密钥) - 明文密钥只在创建时返回一次
    """
    # 生成密钥: sk-ccr-{uuid}
    key_id = str(uuid.uuid4())
    raw_key = f"sk-ccr-{uuid.uuid4().hex}"

    # 计算哈希并存储
    key_hash = _hash_api_key(raw_key)
    prefix = f"sk-ccr-{raw_key[7:11]}..."  # 只显示前4位

    api_key = APIKey(
        id=key_id,
        user_id=user_id,
        name=name,
        key_hash=key_hash,
        prefix=prefix,
        permissions=permissions,
        is_active=True,
        expires_at=expires_at,
    )

    _api_keys_db[key_id] = api_key
    _api_keys_by_hash[key_hash] = key_id

    return api_key, raw_key


def get_user_api_keys(user_id: str) -> list[APIKey]:
    """获取用户的所有 API Key"""
    return [k for k in _api_keys_db.values() if k.user_id == user_id]


def get_api_key_by_id(key_id: str) -> Optional[APIKey]:
    """根据 ID 获取 API Key"""
    return _api_keys_db.get(key_id)


def revoke_api_key(key_id: str, user_id: str) -> bool:
    """
    撤销 API Key

    Args:
        key_id: 密钥 ID
        user_id: 用户 ID（用于验证权限）

    Returns:
        是否成功
    """
    api_key = _api_keys_db.get(key_id)
    if api_key is None:
        return False

    # 验证权限（只能撤销自己的密钥）
    if api_key.user_id != user_id:
        return False

    api_key.is_active = False
    return True


def delete_api_key(key_id: str, user_id: str) -> bool:
    """
    删除 API Key

    Args:
        key_id: 密钥 ID
        user_id: 用户 ID（用于验证权限）

    Returns:
        是否成功
    """
    api_key = _api_keys_db.get(key_id)
    if api_key is None:
        return False

    # 验证权限（只能删除自己的密钥）
    if api_key.user_id != user_id:
        return False

    # 从存储中移除
    del _api_keys_db[key_id]
    del _api_keys_by_hash[api_key.key_hash]

    return True
