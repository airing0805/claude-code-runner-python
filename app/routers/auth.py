"""认证相关 API"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from app.auth import (
    ACCESS_TOKEN_EXPIRE_HOURS,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    generate_api_key,
    get_rate_limiter,
    get_current_user,
    update_user_password,
    validate_password_strength,
    verify_token,
)
from app.models.token import LoginResult
from app.models.user import Token, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_client_ip(request: Request) -> str:
    """
    获取客户端 IP 地址
    支持代理头 X-Forwarded-For 和 X-Real-IP
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For 可能包含多个 IP，取第一个
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"


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


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")


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
    is_admin: bool = False


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
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
async def login(
    request: LoginRequest,
    http_request: Request,
):
    """
    用户登录

    - **username**: 用户名
    - **password**: 密码

    返回:
    - **access_token**: JWT 访问令牌
    - **refresh_token**: 刷新令牌
    - **token_type**: bearer
    - **expires_in**: 过期时间（秒）
    """
    from datetime import datetime, timezone

    # 获取客户端 IP
    client_ip = get_client_ip(http_request)
    rate_limiter = get_rate_limiter()

    # 检查限流
    await rate_limiter.check(client_ip)

    # 验证用户凭据
    user = authenticate_user(request.username, request.password)

    if user is None:
        # 记录失败尝试
        await rate_limiter.record(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 更新最后登录时间
    user.last_login = datetime.now(timezone.utc)

    # 创建访问令牌和刷新令牌
    access_token = create_access_token(user)
    refresh_token, _ = create_refresh_token(user.id)

    # 登录成功，重置限流
    rate_limiter.reset(client_ip)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
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


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="刷新令牌",
    description="使用刷新令牌获取新的访问令牌",
)
async def refresh_token(request: RefreshTokenRequest):
    """
    刷新访问令牌

    - **refresh_token**: 刷新令牌

    返回:
    - **access_token**: 新的 JWT 访问令牌
    - **refresh_token**: 新的刷新令牌
    - **token_type**: bearer
    - **expires_in**: 过期时间（秒）
    """
    from app.auth import get_user_by_id

    # 验证刷新令牌
    payload = verify_token(request.refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user = get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    # 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 创建新的访问令牌和刷新令牌
    access_token = create_access_token(user)
    new_refresh_token, _ = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
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
