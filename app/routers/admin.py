"""管理员接口"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.auth import (
    authenticate_user,
    create_user,
    get_current_admin_user,
    get_user_by_id,
    get_user_by_username,
    update_user_password,
    validate_password_strength,
    verify_password,
    _users_db,
)
from app.models.user import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============== 请求模型 ==============


class UserListResponse(BaseModel):
    """用户列表响应"""
    users: list["UserInfo"]
    total: int


class UserInfo(BaseModel):
    """用户信息"""
    user_id: str
    username: str
    name: str
    is_active: bool
    is_admin: bool
    created_at: str
    last_login: str | None


class UpdateUserStatusRequest(BaseModel):
    """更新用户状态请求"""
    is_active: bool = Field(..., description="是否激活")


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class ResetPasswordResponse(BaseModel):
    """重置密码响应"""
    user_id: str
    username: str
    message: str


# ============== 路由 ==============


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="获取用户列表",
    description="获取所有用户列表（管理员权限）",
)
async def list_users(
    admin: User = Depends(get_current_admin_user),
):
    """
    获取用户列表

    需要管理员权限
    """
    users_info = []
    for user in _users_db.values():
        users_info.append(
            UserInfo(
                user_id=user.id,
                username=user.username,
                name=user.name,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at.isoformat(),
                last_login=user.last_login.isoformat() if user.last_login else None,
            )
        )

    return UserListResponse(users=users_info, total=len(users_info))


@router.patch(
    "/users/{user_id}/status",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="更新用户状态",
    description="启用或禁用用户（管理员权限）",
)
async def update_user_status(
    user_id: str,
    request: UpdateUserStatusRequest,
    admin: User = Depends(get_current_admin_user),
):
    """
    更新用户状态

    - **user_id**: 用户 ID
    - **is_active**: 是否激活

    需要管理员权限
    """
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 不能禁用自己
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己",
        )

    # 不能禁用其他管理员
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能禁用其他管理员",
        )

    user.is_active = request.is_active
    return None


@router.post(
    "/users/{user_id}/reset-password",
    response_model=ResetPasswordResponse,
    summary="重置用户密码",
    description="重置指定用户的密码（管理员权限）",
)
async def reset_user_password(
    user_id: str,
    request: ResetPasswordRequest,
    admin: User = Depends(get_current_admin_user),
):
    """
    重置用户密码

    - **user_id**: 用户 ID
    - **new_password**: 新密码

    需要管理员权限
    """
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 重置密码
    try:
        success = update_user_password(user_id, request.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置密码失败",
        )

    return ResetPasswordResponse(
        user_id=user.id,
        username=user.username,
        message="密码重置成功",
    )


@router.post(
    "/users/{user_id}/set-admin",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="设置管理员",
    description="设置或取消用户管理员权限（管理员权限）",
)
async def set_user_admin(
    user_id: str,
    is_admin: bool = True,
    admin: User = Depends(get_current_admin_user),
):
    """
    设置用户管理员权限

    - **user_id**: 用户 ID
    - **is_admin**: 是否为管理员（默认 true）

    需要管理员权限
    """
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 不能修改自己的管理员权限
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的管理员权限",
        )

    user.is_admin = is_admin
    return None


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除用户",
    description="删除指定用户（管理员权限）",
)
async def delete_user(
    user_id: str,
    admin: User = Depends(get_current_admin_user),
):
    """
    删除用户

    - **user_id**: 用户 ID

    需要管理员权限
    """
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 不能删除自己
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己",
        )

    # 不能删除其他管理员
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能删除其他管理员",
        )

    # 从存储中删除
    del _users_db[user.username]

    return None
