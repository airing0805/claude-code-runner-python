"""认证相关 API"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.auth import (
    ACCESS_TOKEN_EXPIRE_HOURS,
    authenticate_user,
    create_access_token,
    create_user,
    generate_api_key,
    get_current_user,
    update_user_password,
    validate_password_strength,
)
from app.models.user import Token, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============== 请求模型 ==============


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=1, max_length=255, description="用户名（邮箱格式）")
    password: str = Field(..., min_length=8, max_length=100, description="密码")
    name: str = Field(..., min_length=1, max_length=100, description="显示名称")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("用户名不能为空")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class PasswordUpdateRequest(BaseModel):
    """密码更新请求"""
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class RegisterResponse(BaseModel):
    """注册响应"""
    user_id: str
    username: str
    name: str


class UserResponse(BaseModel):
    """用户信息响应"""
    user_id: str
    username: str
    name: str
    api_key: str | None = None


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_HOURS * 3600


# ============== 路由 ==============


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="创建新用户账号",
)
async def register(request: RegisterRequest):
    """
    用户注册

    - **username**: 用户名（邮箱格式）
    - **password**: 密码（至少8位，包含字母和数字）
    - **name**: 显示名称
    """
    try:
        user = create_user(
            username=request.username,
            password=request.password,
            name=request.name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    return RegisterResponse(
        user_id=user.id,
        username=user.username,
        name=user.name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录",
    description="登录并获取访问令牌",
)
async def login(request: LoginRequest):
    """
    用户登录

    - **username**: 用户名
    - **password**: 密码

    返回:
    - **access_token**: JWT 访问令牌
    - **token_type**: bearer
    - **expires_in**: 过期时间（秒）
    """
    user = authenticate_user(request.username, request.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户",
    description="获取已认证用户的个人信息",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息

    需要 JWT 认证
    """
    # 生成 API Key
    api_key = generate_api_key(current_user)

    return UserResponse(
        user_id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        api_key=api_key,
    )


@router.put(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="修改密码",
    description="修改当前用户的密码",
)
async def update_password(
    request: PasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    修改密码

    - **old_password**: 当前密码
    - **new_password**: 新密码（至少8位，包含字母和数字）

    需要 JWT 认证
    """
    # 验证当前密码
    from app.auth import verify_password

    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误",
        )

    # 更新密码
    try:
        success = update_user_password(current_user.id, request.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新密码失败",
        )

    return None
