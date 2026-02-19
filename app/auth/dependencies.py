"""认证依赖 - FastAPI 依赖注入"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

from app.auth.core import (
    ACCESS_TOKEN_EXPIRE_HOURS,
    decode_access_token,
    get_user_by_id,
    verify_api_key,
)
from app.models.user import User

# OAuth2 密码 bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    获取当前认证用户 (JWT)

    用于需要用户登录的端点
    """
    from datetime import datetime, timezone

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = decode_access_token(token)
    if token_data is None:
        raise credentials_exception

    # 检查 token 是否过期 (JWT 库自动验证，但双重检查)
    if token_data.exp < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(token_data.user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> Optional[User]:
    """
    获取当前用户 (可选)

    支持 JWT 或 API Key 认证
    """
    # 优先使用 JWT token
    if token is not None:
        token_data = decode_access_token(token)
        if token_data is not None:
            return get_user_by_id(token_data.user_id)

    # 其次使用 API Key
    if api_key is not None:
        return verify_api_key(api_key)

    return None


async def get_api_key_user(api_key: Optional[str] = Depends(api_key_header)) -> User:
    """
    获取 API Key 认证用户

    用于机器对机器通信
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key",
            headers={"X-API-Key": "Required"},
        )

    user = verify_api_key(api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key",
        )

    return user


# 导出
__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "get_api_key_user",
    "oauth2_scheme",
    "api_key_header",
]
