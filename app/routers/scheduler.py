"""任务调度 API 路由

提供任务队列管理、定时任务管理、任务状态查询、调度器控制等 API。
"""

import os
import re
import uuid
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as Status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.auth import get_current_user_optional
from app.scheduler.config import DEFAULT_TIMEOUT, MIN_TIMEOUT
from app.scheduler.cron import CronParser
from app.scheduler.models import PaginatedResponse, ScheduledTask, Task, TaskLog, TaskSource, TaskStatus
from app.scheduler.scheduler import get_scheduler, get_scheduler_status, start_scheduler, stop_scheduler
from app.scheduler.storage import get_storage
from app.scheduler.timezone_utils import now_iso, now_shanghai, format_datetime

router = APIRouter(prefix="/api/scheduler", tags=["任务调度"])
logger = logging.getLogger(__name__)

# ============= 认证依赖 =============

CurrentUser = Annotated[Optional[any], Depends(get_current_user_optional)]


# ============= 常量定义 =============

MAX_PROMPT_LENGTH = 10000
MAX_NAME_LENGTH = 100
VALID_NAME_PATTERN = re.compile(r'^[\w\u4e00-\u9fff\- ]+$')

# 工具白名单 - 仅允许这些工具被使用
VALID_TOOLS = {
    "Read", "Write", "Edit", "Glob", "Grep", "Bash", "Task",
    "TodoWrite", "WebFetch", "WebSearch", "NotebookEdit",
}

# 系统敏感目录黑名单 - 防止访问关键系统目录
# Windows 和 Unix/Linux 系统目录
FORBIDDEN_PATHS = {
    # Unix/Linux 系统目录
    "/etc", "/root", "/boot", "/dev", "/proc", "/sys", "/kernel",
    # Windows 系统目录
    "c:\\windows", "c:\\windows\\system32", "c:\\program files",
    # 其他敏感目录
    "/var/log", "/var/lib", "/usr/bin", "/usr/sbin",
}

# 路径遍历危险字符模式
PATH_TRAVERSAL_PATTERNS = [
    "..",           # 父目录引用
    "~",            # 用户主目录
    "\\\\",         # UNC 路径 (Windows)
]


# ============= Pydantic 请求模型 =============

class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH, description="任务描述")
    workspace: Optional[str] = Field(None, description="工作目录")
    timeout: Optional[int] = Field(None, ge=MIN_TIMEOUT, description="超时时间(秒)")
    auto_approve: bool = Field(False, description="是否自动批准工具操作")
    allowed_tools: Optional[list[str]] = Field(None, description="允许使用的工具列表")


class CreateScheduledTaskRequest(BaseModel):
    """创建定时任务请求"""
    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH, description="任务名称")
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH, description="任务描述")
    cron: str = Field(..., description="Cron 表达式")
    workspace: Optional[str] = Field(None, description="工作目录")
    timeout: Optional[int] = Field(None, ge=MIN_TIMEOUT, description="超时时间(秒)")
    auto_approve: bool = Field(False, description="是否自动批准")
    allowed_tools: Optional[list[str]] = Field(None, description="允许使用的工具列表")
    enabled: bool = Field(True, description="是否启用")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not VALID_NAME_PATTERN.match(v):
            raise ValueError("任务名称包含非法字符")
        return v

    @field_validator('allowed_tools')
    @classmethod
    def validate_tools(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None:
            invalid = [tool for tool in v if tool not in VALID_TOOLS]
            if invalid:
                raise ValueError(f"无效的工具名称: {', '.join(invalid)}")
        return v


class UpdateScheduledTaskRequest(BaseModel):
    """更新定时任务请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=MAX_NAME_LENGTH)
    prompt: Optional[str] = Field(None, min_length=1, max_length=MAX_PROMPT_LENGTH)
    cron: Optional[str] = Field(None)
    workspace: Optional[str] = Field(None)
    timeout: Optional[int] = Field(None, ge=MIN_TIMEOUT)
    auto_approve: Optional[bool] = None
    allowed_tools: Optional[list[str]] = Field(None)
    enabled: Optional[bool] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not VALID_NAME_PATTERN.match(v):
            raise ValueError("任务名称包含非法字符")
        return v

    @field_validator('allowed_tools')
    @classmethod
    def validate_tools(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None:
            invalid = [tool for tool in v if tool not in VALID_TOOLS]
            if invalid:
                raise ValueError(f"无效的工具名称: {', '.join(invalid)}")
        return v


class ValidateCronRequest(BaseModel):
    """验证 Cron 表达式请求"""
    cron: str = Field(..., min_length=1, description="Cron 表达式")


# ============= 响应模型 =============

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    data: Any = None
    message: str = "操作成功"


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    code: str


# ============= 验证函数 =============

def _check_path_traversal(workspace: str) -> None:
    """检查路径遍历攻击模式

    检测常见的路径遍历攻击字符和模式。
    """
    # 转换为小写进行不区分大小写的检查
    workspace_lower = workspace.lower()

    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern in workspace_lower:
            raise HTTPException(
                status_code=Status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error=f"工作目录包含非法路径模式: {pattern}",
                    code="PATH_TRAVERSAL_DETECTED"
                ).model_dump(),
            )


def _check_forbidden_path(abs_workspace: Path) -> None:
    """检查是否为系统敏感目录

    防止访问系统关键目录，如 /etc, /root, c:\\windows 等。
    """
    # 获取规范化的小写路径字符串
    workspace_str = str(abs_workspace).lower().replace("/", "\\")

    for forbidden in FORBIDDEN_PATHS:
        forbidden_normalized = forbidden.lower().replace("/", "\\")
        # 检查路径是否以禁用目录开头
        if workspace_str.startswith(forbidden_normalized):
            raise HTTPException(
                status_code=Status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error="工作目录不允许访问系统敏感目录",
                    code="FORBIDDEN_WORKSPACE"
                ).model_dump(),
            )


def validate_workspace(workspace: str | None) -> str:
    """验证 workspace 路径安全性

    多层安全验证策略：
    1. 检查路径遍历攻击模式（..、~ 等）
    2. 检查系统敏感目录黑名单
    3. 白名单机制：确保工作目录在允许的范围内

    在测试环境中可设置 SCHEDULER_ALLOW_ANY_WORKSPACE=true 禁用白名单验证。
    """
    if workspace is None or not workspace.strip():
        return ""

    workspace = workspace.strip()

    # 1. 检查路径遍历攻击模式
    _check_path_traversal(workspace)

    # 处理默认工作空间标识符
    default_indicators = ['默认工作空间', '默认', '.']
    if workspace in default_indicators:
        # 获取实际的工作目录路径
        actual_workspace = os.getenv("WORKING_DIR", ".").strip()
        if not actual_workspace:
            return ""
        workspace = actual_workspace

    try:
        abs_workspace = Path(workspace).resolve()
    except Exception:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="无效的工作目录路径", code="INVALID_WORKSPACE").model_dump(),
        )

    # 2. 检查系统敏感目录黑名单
    _check_forbidden_path(abs_workspace)

    # 3. 白名单机制验证
    allow_any = os.getenv("SCHEDULER_ALLOW_ANY_WORKSPACE", "false").lower() == "true"
    if allow_any:
        # 测试环境跳过白名单检查，但仍保留敏感目录检查
        return str(abs_workspace)

    base_dir = Path(os.getenv("WORKING_DIR", "")).resolve()

    try:
        abs_workspace.relative_to(base_dir)
    except ValueError:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="工作目录必须在允许的目录内", code="WORKSPACE_NOT_ALLOWED").model_dump(),
        )

    return str(abs_workspace)


def validate_prompt(prompt: str | None) -> str:
    """验证 prompt 字段"""
    if not prompt or not prompt.strip():
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="prompt 不能为空", code="VALIDATION_ERROR").model_dump(),
        )
    prompt = prompt.strip()
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error=f"prompt 长度不能超过 {MAX_PROMPT_LENGTH} 字符", code="PROMPT_TOO_LONG").model_dump(),
        )
    return prompt


def validate_timeout(timeout: int | None) -> int:
    """验证 timeout 字段

    如果 timeout 为 None，返回 None（保留原值，不覆盖）
    调用方应处理 None 情况
    """
    if timeout is None:
        return None  # 返回 None，保留原值
    if not isinstance(timeout, int) or timeout < MIN_TIMEOUT:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error=f"timeout 必须大于等于 {MIN_TIMEOUT}", code="INVALID_TIMEOUT").model_dump(),
        )
    return timeout


def validate_allowed_tools(tools: list[str] | None) -> list[str] | None:
    """验证 allowed_tools 列表"""
    if tools is None:
        return None
    for tool in tools:
        if tool not in VALID_TOOLS:
            raise HTTPException(
                status_code=Status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(error=f"无效的工具名称: {tool}", code="INVALID_TOOL").model_dump(),
            )
    return tools


def validate_task_id(task_id: str) -> str:
    """验证 task_id 是否为有效的 UUID 或字符串格式

    对于队列任务，必须是 UUID 格式
    对于定时任务，可以是任何非空字符串（允许自定义 ID）
    """
    if not task_id or not task_id.strip():
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="任务 ID 不能为空", code="INVALID_TASK_ID").model_dump(),
        )
    return task_id


# Cron 解析器实例
_cron_parser = CronParser()


# ============= 任务队列管理 API =============

@router.post("/tasks", status_code=Status.HTTP_201_CREATED)
async def create_task(request: CreateTaskRequest, current_user: CurrentUser = None) -> dict:
    """添加任务到队列

    支持可选认证：
    - 已认证用户：任务将关联到用户（未来扩展）
    - 匿名用户：任务正常执行
    """
    # 记录用户信息
    if current_user:
        logger.info(f"创建队列任务 - 用户: {current_user.username} (ID: {current_user.id})")

    # 验证字段
    prompt = validate_prompt(request.prompt)
    workspace = validate_workspace(request.workspace)
    timeout = validate_timeout(request.timeout) or DEFAULT_TIMEOUT
    allowed_tools = validate_allowed_tools(request.allowed_tools)
    auto_approve = request.auto_approve

    # 创建任务（手动添加）
    task = Task(
        id=str(uuid.uuid4()),
        prompt=prompt,
        workspace=workspace,
        timeout=timeout,
        auto_approve=auto_approve,
        allowed_tools=allowed_tools,
        source=TaskSource.MANUAL,
    )

    # 添加到队列
    storage = get_storage()
    storage.queue.add(task)

    return SuccessResponse(data=task.to_dict(), message="任务已添加到队列").model_dump()


@router.get("/tasks")
async def list_tasks() -> dict:
    """获取队列列表"""
    storage = get_storage()
    tasks = storage.queue.get_all()
    return SuccessResponse(data=[t.to_dict() for t in tasks]).model_dump()


@router.delete("/tasks/clear")
async def clear_tasks() -> dict:
    """清空队列"""
    storage = get_storage()
    storage.queue.clear()
    return SuccessResponse(message="队列已清空").model_dump()


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: CurrentUser = None) -> dict:
    """
    删除队列中的任务

    支持可选认证：
    - 已认证用户：可记录用户操作（未来扩展）
    - 匿名用户：任务正常删除
    """
    task_id = validate_task_id(task_id)
    storage = get_storage()
    if not storage.queue.remove(task_id):
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="任务不存在", code="TASK_NOT_FOUND").model_dump(),
        )
    return SuccessResponse(message="任务已从队列中删除").model_dump()


# ============= 定时任务管理 API =============

@router.post("/scheduled-tasks", status_code=Status.HTTP_201_CREATED)
async def create_scheduled_task(request: CreateScheduledTaskRequest, current_user: CurrentUser = None) -> dict:
    """
    创建定时任务

    支持可选认证：
    - 已认证用户：任务将关联到用户（未来扩展）
    - 匿名用户：任务正常创建
    """
    # 记录用户信息
    if current_user:
        logger.info(f"创建定时任务 - 用户: {current_user.username} (ID: {current_user.id}), 名称: {request.name}")
    # 验证 cron 表达式
    is_valid, error_msg = _cron_parser.validate(request.cron)
    if not is_valid:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error=f"无效的 Cron 表达式: {error_msg}", code="INVALID_CRON").model_dump(),
        )

    # 验证可选字段
    workspace = validate_workspace(request.workspace)
    timeout = validate_timeout(request.timeout) or DEFAULT_TIMEOUT
    allowed_tools = validate_allowed_tools(request.allowed_tools)

    # 计算下次执行时间
    next_run = _cron_parser.calculate_next_run(request.cron)

    # 创建定时任务
    task = ScheduledTask(
        id=str(uuid.uuid4()),
        name=request.name,
        prompt=request.prompt,
        cron=request.cron,
        workspace=workspace,
        timeout=timeout,
        auto_approve=request.auto_approve,
        allowed_tools=allowed_tools,
        enabled=request.enabled,
        next_run=format_datetime(next_run) if next_run else None,
    )

    # 使用 scheduler 添加任务（会同步到 APScheduler）
    scheduler = get_scheduler()
    success = scheduler.add_scheduled_task(task)
    if not success:
        raise HTTPException(
            status_code=Status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(error="定时任务添加失败", code="SCHEDULED_TASK_ADD_FAILED").model_dump(),
        )

    return SuccessResponse(data=task.to_dict(), message="定时任务已创建").model_dump()


@router.get("/scheduled-tasks")
async def list_scheduled_tasks() -> dict:
    """获取定时任务列表"""
    storage = get_storage()
    tasks = storage.scheduled.get_all()
    return SuccessResponse(data=[t.to_dict() for t in tasks]).model_dump()


@router.patch("/scheduled-tasks/{task_id}")
async def update_scheduled_task(task_id: str, request: UpdateScheduledTaskRequest, current_user: CurrentUser = None) -> dict:
    """
    更新定时任务

    支持可选认证：
    - 已认证用户：可记录用户操作（未来扩展）
    - 匿名用户：任务正常更新
    """
    task_id = validate_task_id(task_id)
    storage = get_storage()
    task = storage.scheduled.get(task_id)

    if not task:
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="定时任务不存在", code="SCHEDULED_TASK_NOT_FOUND").model_dump(),
        )

    # 更新字段（Pydantic 已验证）
    if request.name is not None:
        task.name = request.name

    if request.prompt is not None:
        task.prompt = request.prompt

    if request.cron is not None:
        is_valid, error_msg = _cron_parser.validate(request.cron)
        if not is_valid:
            raise HTTPException(
                status_code=Status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(error="无效的 Cron 表达式", code="INVALID_CRON").model_dump(),
            )
        task.cron = request.cron
        # 重新计算下次执行时间
        next_run = _cron_parser.calculate_next_run(request.cron)
        task.next_run = format_datetime(next_run) if next_run else None

    if request.workspace is not None:
        task.workspace = validate_workspace(request.workspace)

    if request.timeout is not None:
        task.timeout = request.timeout

    if request.auto_approve is not None:
        task.auto_approve = request.auto_approve

    if request.allowed_tools is not None:
        task.allowed_tools = request.allowed_tools

    if request.enabled is not None:
        task.enabled = request.enabled
        if not task.enabled:
            task.next_run = None
        else:
            # 重新启用时计算下次执行时间
            next_run = _cron_parser.calculate_next_run(task.cron)
            task.next_run = format_datetime(next_run) if next_run else None

    task.updated_at = now_iso()

    # 使用 scheduler 更新任务（会同步到 APScheduler）
    scheduler = get_scheduler()
    success = scheduler.update_scheduled_task(task)
    if not success:
        raise HTTPException(
            status_code=Status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(error="定时任务更新失败", code="SCHEDULED_TASK_UPDATE_FAILED").model_dump(),
        )

    return SuccessResponse(data=task.to_dict(), message="定时任务已更新").model_dump()


@router.delete("/scheduled-tasks/{task_id}")
async def delete_scheduled_task(task_id: str, current_user: CurrentUser = None) -> dict:
    """
    删除定时任务

    支持可选认证：
    - 已认证用户：可记录用户操作（未来扩展）
    - 匿名用户：任务正常删除
    """
    task_id = validate_task_id(task_id)
    scheduler = get_scheduler()
    success = scheduler.remove_scheduled_task(task_id)
    if not success:
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="定时任务不存在", code="SCHEDULED_TASK_NOT_FOUND").model_dump(),
        )
    return SuccessResponse(message="定时任务已删除").model_dump()


@router.post("/scheduled-tasks/{task_id}/toggle")
async def toggle_scheduled_task(task_id: str, current_user: CurrentUser = None) -> dict:
    """
    启用/禁用定时任务

    支持可选认证：
    - 已认证用户：可记录用户操作（未来扩展）
    - 匿名用户：任务正常切换
    """
    task_id = validate_task_id(task_id)
    storage = get_storage()
    task = storage.scheduled.get(task_id)

    if not task:
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="定时任务不存在", code="SCHEDULED_TASK_NOT_FOUND").model_dump(),
        )

    # 切换状态
    task.enabled = not task.enabled

    if task.enabled:
        # 重新启用时计算下次执行时间
        next_run = _cron_parser.calculate_next_run(task.cron)
        task.next_run = format_datetime(next_run) if next_run else None
    else:
        task.next_run = None

    task.updated_at = now_iso()

    # 使用 scheduler 更新任务（会同步到 APScheduler）
    scheduler = get_scheduler()
    success = scheduler.update_scheduled_task(task)
    if not success:
        raise HTTPException(
            status_code=Status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(error="定时任务状态更新失败", code="SCHEDULED_TASK_TOGGLE_FAILED").model_dump(),
        )

    message = "定时任务已启用" if task.enabled else "定时任务已禁用"
    return SuccessResponse(
        data={"id": task.id, "enabled": task.enabled, "next_run": task.next_run},
        message=message,
    ).model_dump()


@router.post("/scheduled-tasks/{task_id}/run")
async def run_scheduled_task_now(task_id: str, current_user: CurrentUser = None) -> dict:
    """
    立即执行定时任务

    支持可选认证：
    - 已认证用户：可记录用户操作（未来扩展）
    - 匿名用户：任务正常执行
    """
    task_id = validate_task_id(task_id)
    scheduler = get_scheduler()
    task = scheduler.run_scheduled_now(task_id)

    if not task:
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="定时任务不存在", code="SCHEDULED_TASK_NOT_FOUND").model_dump(),
        )

    return SuccessResponse(data={"task_id": task.id}, message="任务已添加到队列").model_dump()


# ============= 任务状态查询 API =============

@router.get("/tasks/running")
async def list_running_tasks() -> dict:
    """获取运行中任务"""
    storage = get_storage()
    tasks = storage.running.get_all()
    return SuccessResponse(data=[t.to_dict() for t in tasks]).model_dump()


@router.get("/tasks/completed")
async def list_completed_tasks(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
) -> dict:
    """获取已完成任务（支持分页）"""
    storage = get_storage()
    result: PaginatedResponse = storage.history.get_completed(page, limit)
    return SuccessResponse(data={
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "limit": result.limit,
        "pages": result.pages,
    }).model_dump()


@router.get("/tasks/failed")
async def list_failed_tasks(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
) -> dict:
    """获取失败任务（支持分页）"""
    storage = get_storage()
    result: PaginatedResponse = storage.history.get_failed(page, limit)
    return SuccessResponse(data={
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "limit": result.limit,
        "pages": result.pages,
    }).model_dump()


@router.get("/tasks/cancelled")
async def list_cancelled_tasks(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
) -> dict:
    """获取已取消任务（支持分页）"""
    storage = get_storage()
    result: PaginatedResponse = storage.cancelled.get_paginated(page, limit)
    return SuccessResponse(data={
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "limit": result.limit,
        "pages": result.pages,
    }).model_dump()


@router.get("/tasks/{task_id}")
async def get_task_detail(task_id: str, current_user: CurrentUser = None) -> dict:
    """
    获取任务详情

    支持可选认证：
    - 已认证用户：可返回用户相关任务（未来扩展）
    - 匿名用户：返回所有任务详情
    """
    task_id = validate_task_id(task_id)
    storage = get_storage()

    # 从各个存储位置查找
    task = storage.queue.get(task_id)
    if task:
        return SuccessResponse(data=task.to_dict()).model_dump()

    task = storage.running.get(task_id)
    if task:
        return SuccessResponse(data=task.to_dict()).model_dump()

    # 从已取消任务中查找
    task = storage.cancelled.get(task_id)
    if task:
        return SuccessResponse(data=task.to_dict()).model_dump()

    # 从历史记录中查找（使用索引优化搜索）
    task = storage.history.find_by_id(task_id)
    if task:
        return SuccessResponse(data=task.to_dict()).model_dump()

    raise HTTPException(
        status_code=Status.HTTP_404_NOT_FOUND,
        detail=ErrorResponse(error="任务不存在", code="TASK_NOT_FOUND").model_dump(),
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, current_user: CurrentUser = None) -> dict:
    """
    取消任务

    支持可选认证：
    - 已认证用户：可记录用户操作（未来扩展）
    - 匿名用户：任务正常取消

    可以取消队列中等待的任务。
    运行中的任务无法通过此接口取消。
    """
    task_id = validate_task_id(task_id)
    storage = get_storage()

    # 1. 检查是否在队列中
    task = storage.queue.get(task_id)
    if task:
        # 从队列中移除
        storage.queue.remove(task_id)
        # 更新状态
        task.status = TaskStatus.CANCELLED
        task.finished_at = now_iso()
        task.error = "用户取消"
        # 保存到已取消列表
        storage.cancelled.add(task)
        return SuccessResponse(data=task.to_dict(), message="任务已取消").model_dump()

    # 2. 检查是否正在运行
    running_task = storage.running.get(task_id)
    if running_task:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="无法取消正在运行的任务", code="TASK_ALREADY_RUNNING").model_dump(),
        )

    # 3. 任务不存在
    raise HTTPException(
        status_code=Status.HTTP_404_NOT_FOUND,
        detail=ErrorResponse(error="任务不存在或已完成", code="TASK_NOT_FOUND").model_dump(),
    )


# ============= 调度器控制 API =============

@router.get("/status")
async def get_status() -> dict:
    """获取调度器状态"""
    status = get_scheduler_status()
    return SuccessResponse(data=status).model_dump()


@router.post("/start")
async def start() -> dict:
    """启动调度器"""
    success = await start_scheduler()
    if not success:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="调度器已在运行中", code="SCHEDULER_ALREADY_RUNNING").model_dump(),
        )
    return SuccessResponse(message="调度器已启动").model_dump()


@router.post("/stop")
async def stop() -> dict:
    """停止调度器"""
    success = await stop_scheduler()
    if not success:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="调度器未运行", code="SCHEDULER_NOT_RUNNING").model_dump(),
        )
    return SuccessResponse(message="调度器已停止").model_dump()


# ============= Cron 表达式验证 API =============

@router.post("/validate-cron")
async def validate_cron(request: ValidateCronRequest, current_user: CurrentUser = None) -> dict:
    """
    验证 Cron 表达式

    支持可选认证：
    - 已认证用户：可记录使用情况（未来扩展）
    - 匿名用户：正常验证
    """
    is_valid, error_msg = _cron_parser.validate(request.cron)

    if not is_valid:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="无效的 Cron 表达式", code="INVALID_CRON").model_dump(),
        )

    # 获取下 5 次执行时间
    next_runs = _cron_parser.get_next_runs(request.cron, 5)

    # 下次运行时间（第一个）
    next_run = format_datetime(next_runs[0]) if next_runs else None

    return SuccessResponse(data={
        "valid": True,
        "next_run": next_run,
        "next_runs": [format_datetime(dt) for dt in next_runs],
    }).model_dump()


@router.get("/cron-examples")
async def get_cron_examples() -> dict:
    """获取常用 Cron 表达式示例"""
    examples = [
        {"expression": "*/5 * * * *", "description": "每 5 分钟执行"},
        {"expression": "0 * * * *", "description": "每小时执行"},
        {"expression": "0 */2 * * *", "description": "每 2 小时执行"},
        {"expression": "0 9 * * *", "description": "每天 9:00 执行"},
        {"expression": "0 9 * * 1-5", "description": "工作日 9:00 执行"},
        {"expression": "0 9 * * 0,6", "description": "周末 9:00 执行"},
        {"expression": "0 0 * * *", "description": "每天零点执行"},
        {"expression": "0 0 1 * *", "description": "每月 1 日零点执行"},
        {"expression": "@hourly", "description": "每小时整点（别名）"},
        {"expression": "@daily", "description": "每天零点（别名）"},
    ]

    # 添加示例执行时间
    now = now_shanghai()
    for example in examples:
        next_run = _cron_parser.calculate_next_run(example["expression"], now)
        example["next_run_example"] = format_datetime(next_run) if next_run else None

    return SuccessResponse(data=examples).model_dump()


# ============= 任务日志查询 API =============

@router.get("/logs")
async def list_logs(
    task_id: Optional[str] = Query(None, description="按任务 ID 筛选"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
) -> dict:
    """获取任务执行日志"""
    storage = get_storage()

    if task_id:
        # 获取指定任务的日志
        logs = storage.logs.get_by_task_id(task_id, limit)
    else:
        # 获取所有日志
        logs = storage.logs.get_all(limit)

    return SuccessResponse(
        data=logs,
        message=f"共找到 {len(logs)} 条日志",
    ).model_dump()


@router.get("/logs/{task_id}")
async def get_task_logs(
    task_id: str,
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
) -> dict:
    """获取指定任务的执行日志"""
    task_id = validate_task_id(task_id)
    storage = get_storage()
    logs = storage.logs.get_by_task_id(task_id, limit)

    return SuccessResponse(
        data=logs,
        message=f"任务 {task_id} 共有 {len(logs)} 条日志",
    ).model_dump()


@router.delete("/logs")
async def clear_logs() -> dict:
    """清空所有日志"""
    storage = get_storage()
    storage.logs.clear()
    return SuccessResponse(message="日志已清空").model_dump()


# ============= 日志增强 API =============

@router.get("/tasks/{task_id}/logs/normal")
async def get_normal_logs(
    task_id: str,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(100, ge=1, le=500, description="每页数量"),
    start_time: Optional[str] = Query(None, description="开始时间 (ISO 格式)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO 格式)"),
) -> dict:
    """获取任务的正常日志 (stdout)"""
    task_id = validate_task_id(task_id)
    storage = get_storage()

    # 检查任务是否存在
    task = storage.history.find_by_id(task_id)
    if not task:
        task = storage.running.get(task_id)
    if not task:
        task = storage.queue.get(task_id)
    if not task:
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="任务不存在", code="TASK_NOT_FOUND").model_dump(),
        )

    result = storage.logs.get_paginated(
        task_id=task_id,
        page=page,
        limit=limit,
        log_type="stdout",
        start_time=start_time,
        end_time=end_time,
    )

    return SuccessResponse(data={
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "limit": result.limit,
        "pages": result.pages,
    }).model_dump()


@router.get("/tasks/{task_id}/logs/error")
async def get_error_logs(
    task_id: str,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(100, ge=1, le=500, description="每页数量"),
    start_time: Optional[str] = Query(None, description="开始时间 (ISO 格式)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO 格式)"),
) -> dict:
    """获取任务的错误日志 (stderr)"""
    task_id = validate_task_id(task_id)
    storage = get_storage()

    # 检查任务是否存在
    task = storage.history.find_by_id(task_id)
    if not task:
        task = storage.running.get(task_id)
    if not task:
        task = storage.queue.get(task_id)
    if not task:
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="任务不存在", code="TASK_NOT_FOUND").model_dump(),
        )

    result = storage.logs.get_paginated(
        task_id=task_id,
        page=page,
        limit=limit,
        log_type="stderr",
        start_time=start_time,
        end_time=end_time,
    )

    return SuccessResponse(data={
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "limit": result.limit,
        "pages": result.pages,
    }).model_dump()


@router.get("/tasks/{task_id}/logs/search")
async def search_logs(
    task_id: str,
    keyword: str = Query(..., min_length=1, description="搜索关键字"),
    regex: bool = Query(False, description="是否使用正则表达式"),
    log_type: Optional[str] = Query(None, description="日志类型过滤 (stdout/stderr/all)"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(100, ge=1, le=500, description="每页数量"),
) -> dict:
    """搜索任务日志"""
    task_id = validate_task_id(task_id)

    if not keyword or not keyword.strip():
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="搜索关键字不能为空", code="EMPTY_KEYWORD").model_dump(),
        )

    # 验证日志类型
    if log_type and log_type not in ("stdout", "stderr", "all"):
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="无效的日志类型", code="INVALID_LOG_TYPE").model_dump(),
        )

    # 转换为存储层使用的类型过滤
    type_filter = None
    if log_type == "all":
        type_filter = None
    elif log_type:
        type_filter = log_type

    storage = get_storage()

    # 检查任务是否存在
    task = storage.history.find_by_id(task_id)
    if not task:
        task = storage.running.get(task_id)
    if not task:
        task = storage.queue.get(task_id)
    if not task:
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="任务不存在", code="TASK_NOT_FOUND").model_dump(),
        )

    result = storage.logs.search(
        task_id=task_id,
        keyword=keyword.strip(),
        regex=regex,
        log_type=type_filter,
        page=page,
        limit=limit,
    )

    return SuccessResponse(data={
        "items": result.items,
        "total": result.total,
        "keyword": keyword,
        "page": result.page,
        "limit": result.limit,
        "pages": result.pages,
    }).model_dump()


@router.get("/tasks/{task_id}/logs/count")
async def get_log_counts(
    task_id: str,
) -> dict:
    """获取任务的日志数量统计"""
    task_id = validate_task_id(task_id)
    storage = get_storage()

    # 检查任务是否存在
    task = storage.history.find_by_id(task_id)
    if not task:
        task = storage.running.get(task_id)
    if not task:
        task = storage.queue.get(task_id)
    if not task:
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="任务不存在", code="TASK_NOT_FOUND").model_dump(),
        )

    counts = storage.logs.get_count_by_type(task_id)

    return SuccessResponse(data=counts).model_dump()


@router.get("/tasks/{task_id}/logs/stream")
async def stream_task_logs(
    task_id: str,
    log_type: str = Query("all", description="日志类型过滤 (stdout/stderr/all)"),
):
    """SSE 实时日志流

    建立 SSE 连接以接收任务的实时日志。
    支持日志类型过滤（stdout/stderr/all）。
    """
    import asyncio

    task_id = validate_task_id(task_id)

    # 验证日志类型
    if log_type not in ("stdout", "stderr", "all"):
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(error="无效的日志类型", code="INVALID_LOG_TYPE").model_dump(),
        )

    storage = get_storage()
    scheduler = get_scheduler()

    # 检查任务是否存在
    task = storage.history.find_by_id(task_id)
    if not task:
        task = storage.running.get(task_id)
    if not task:
        task = storage.queue.get(task_id)
    if not task:
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(error="任务不存在", code="TASK_NOT_FOUND").model_dump(),
        )

    async def event_generator():
        # 订阅日志事件
        queue = scheduler.subscribe_logs(task_id)

        try:
            # 首先发送连接成功消息
            yield f"event: connected\ndata: {json.dumps({'message': '已连接到日志流'})}\n\n"

            # 持续监听日志事件
            while True:
                try:
                    # 使用超时等待日志事件
                    log_entry = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # 根据类型过滤
                    if log_type != "all" and log_entry.get("type") != log_type:
                        continue

                    # 发送日志事件
                    yield f"event: log\ndata: {json.dumps(log_entry, ensure_ascii=False)}\n\n"

                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield f": heartbeat\n\n"
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
                    break

                # 检查任务状态
                running_task = storage.running.get(task_id)
                if not running_task:
                    # 任务已结束
                    completed_task = storage.history.find_by_id(task_id)
                    if completed_task:
                        if completed_task.status == TaskStatus.COMPLETED:
                            yield f"event: complete\ndata: {json.dumps({'message': '任务已完成'})}\n\n"
                        else:
                            yield f"event: error\ndata: {json.dumps({'message': '任务执行失败', 'error': completed_task.error})}\n\n"
                    yield f"event: close\ndata: {json.dumps({'message': '连接关闭'})}\n\n"
                    break

        finally:
            # 取消订阅
            scheduler.unsubscribe_logs(task_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
