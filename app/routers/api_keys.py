"""API 密钥管理 API"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import (
    create_api_key,
    delete_api_key,
    get_api_key_by_id,
    get_current_user,
    get_user_api_keys,
    revoke_api_key,
)
from app.models.api_key import APIKeyWithMeta
from app.models.user import User

router = APIRouter(prefix="/api/keys", tags=["api-keys"])

# 每用户最大密钥数量限制
MAX_KEYS_PER_USER = 10


# ============== 请求模型 ==============


class APIKeyCreateRequest(BaseModel):
    """API 密钥创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="密钥名称")
    permissions: str = Field("read_write", description="权限: read_only | read_write")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="过期天数（可选）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "My API Key",
                "permissions": "read_write",
                "expires_in_days": 30,
            }
        }
    }


class APIKeyResponse(BaseModel):
    """API 密钥响应（不含明文）"""
    key_id: str
    name: str
    prefix: str
    permissions: str
    is_active: bool
    created_at: str
    last_used_at: Optional[str]
    expires_at: Optional[str]


class APIKeyCreatedResponse(BaseModel):
    """API 密钥创建响应（含明文，只显示一次）"""
    key_id: str
    name: str
    key: str  # 明文密钥，只在创建时返回
    prefix: str
    permissions: str
    created_at: str


# ============== 路由 ==============


@router.post(
    "",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建 API 密钥",
    description="创建新的 API 密钥，密钥只在创建时显示一次",
)
async def create_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    创建新的 API 密钥

    - **name**: 密钥名称
    - **permissions**: 权限（read_only 或 read_write）
    - **expires_in_days**: 过期天数（可选，不设置则永不过期）

    返回的 **key** 字段只在此刻显示一次，请妥善保存！

    需要 JWT 认证
    """
    # 验证权限
    if request.permissions not in ("read_only", "read_write"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="权限必须是 read_only 或 read_write",
        )

    # 检查密钥数量限制
    existing_keys = get_user_api_keys(current_user.id)
    if len(existing_keys) >= MAX_KEYS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"已达到最大密钥数量限制 ({MAX_KEYS_PER_USER} 个)",
        )

    # 计算过期时间
    expires_at = None
    if request.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    # 创建密钥
    api_key_obj, raw_key = create_api_key(
        user_id=current_user.id,
        name=request.name,
        permissions=request.permissions,
        expires_at=expires_at,
    )

    return APIKeyCreatedResponse(
        key_id=api_key_obj.id,
        name=api_key_obj.name,
        key=raw_key,  # 只在创建时返回明文
        prefix=api_key_obj.prefix,
        permissions=api_key_obj.permissions,
        created_at=api_key_obj.created_at.isoformat(),
    )


@router.get(
    "",
    response_model=list[APIKeyResponse],
    summary="获取 API 密钥列表",
    description="获取当前用户的所有 API 密钥",
)
async def list_keys(current_user: User = Depends(get_current_user)):
    """
    获取当前用户的所有 API 密钥

    注意：不会返回密钥明文

    需要 JWT 认证
    """
    keys = get_user_api_keys(current_user.id)
    return [
        APIKeyResponse(
            key_id=k.id,
            name=k.name,
            prefix=k.prefix,
            permissions=k.permissions,
            is_active=k.is_active,
            created_at=k.created_at.isoformat(),
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
        )
        for k in keys
    ]


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="撤销 API 密钥",
    description="撤销指定的 API 密钥",
)
async def revoke_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    撤销指定的 API 密钥

    撤销后密钥将立即失效，无法再用于认证

    需要 JWT 认证
    """
    # 检查密钥是否存在
    api_key = get_api_key_by_id(key_id)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="密钥不存在",
        )

    # 撤销密钥
    success = revoke_api_key(key_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无法撤销其他用户的密钥",
        )

    return None


@router.delete(
    "/{key_id}/permanent",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除 API 密钥",
    description="永久删除指定的 API 密钥",
)
async def delete_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    永久删除指定的 API 密钥

    密钥将被完全删除，无法恢复

    需要 JWT 认证
    """
    # 检查密钥是否存在
    api_key = get_api_key_by_id(key_id)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="密钥不存在",
        )

    # 删除密钥
    success = delete_api_key(key_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无法删除其他用户的密钥",
        )

    return None
