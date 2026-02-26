"""任务调度 API 路由

提供任务队列管理、定时任务管理、任务状态查询、调度器控制等 API。
"""

import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer

from app.scheduler.config import MAX_TIMEOUT, MIN_TIMEOUT
from app.scheduler.cron import CronParser
from app.scheduler.models import PaginatedResponse, ScheduledTask, Task, TaskStatus
from app.scheduler.scheduler import get_scheduler, get_scheduler_status, start_scheduler, stop_scheduler
from app.scheduler.storage import get_storage

router = APIRouter(prefix="/api", tags=["任务调度"])

# 可选认证 - auto_error=False 使认证变为可选
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# 用户认证依赖（可选）
CurrentUser = Annotated[Optional[str], Depends(oauth2_scheme_optional)]

# 安全常量
MAX_PROMPT_LENGTH = 10000
MAX_NAME_LENGTH = 100
VALID_NAME_PATTERN = re.compile(r'^[\w\u4e00-\u9fff\- ]+$')  # 字母数字中文下划线空格

# 合法工具名称列表
VALID_TOOLS = {
    "Read", "Write", "Edit", "Glob", "Grep", "Bash", "Task",
    "TodoWrite", "WebFetch", "WebSearch", "NotebookEdit",
}


def validate_workspace(workspace: str | None) -> str:
    """
    验证 workspace 路径安全性

    防止路径遍历攻击，确保工作目录在允许的范围内。
    在测试环境中可设置 SCHEDULER_ALLOW_ANY_WORKSPACE=true 禁用验证。
    """
    if workspace is None or not workspace.strip():
        return "."

    workspace = workspace.strip()

    # 解析为绝对路径
    try:
        abs_workspace = Path(workspace).resolve()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=error_response("无效的工作目录路径", "INVALID_WORKSPACE"),
        )

    # 检查是否允许任意工作目录（用于测试环境）
    allow_any = os.getenv("SCHEDULER_ALLOW_ANY_WORKSPACE", "false").lower() == "true"
    if allow_any:
        return str(abs_workspace)

    # 获取基础工作目录
    base_dir = Path(os.getenv("WORKING_DIR", ".")).resolve()

    # 检查是否在基础目录内
    try:
        abs_workspace.relative_to(base_dir)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=error_response("工作目录必须在允许的目录内", "WORKSPACE_NOT_ALLOWED"),
        )

    return str(abs_workspace)


def validate_prompt(prompt: str | None) -> str:
    """验证 prompt 字段"""
    if not prompt or not prompt.strip():
        raise HTTPException(
            status_code=400,
            detail=error_response("prompt 不能为空", "VALIDATION_ERROR"),
        )
    prompt = prompt.strip()
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=error_response(f"prompt 长度不能超过 {MAX_PROMPT_LENGTH} 字符", "PROMPT_TOO_LONG"),
        )
    return prompt


def validate_name(name: str | None) -> str:
    """验证 name 字段"""
    if not name or not name.strip():
        raise HTTPException(
            status_code=400,
            detail=error_response("name 不能为空", "VALIDATION_ERROR"),
        )
    name = name.strip()
    if len(name) > MAX_NAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=error_response(f"name 长度不能超过 {MAX_NAME_LENGTH} 字符", "NAME_TOO_LONG"),
        )
    if not VALID_NAME_PATTERN.match(name):
        raise HTTPException(
            status_code=400,
            detail=error_response("任务名称包含非法字符", "INVALID_NAME"),
        )
    return name


def validate_timeout(timeout: int | None) -> int:
    """验证 timeout 字段"""
    if timeout is None:
        return 600000
    if not isinstance(timeout, int) or timeout < MIN_TIMEOUT or timeout > MAX_TIMEOUT:
        raise HTTPException(
            status_code=400,
            detail=error_response(f"timeout 必须在 {MIN_TIMEOUT} 到 {MAX_TIMEOUT} 之间", "INVALID_TIMEOUT"),
        )
    return timeout


def validate_allowed_tools(tools: list[str] | None) -> list[str] | None:
    """验证 allowed_tools 列表"""
    if tools is None:
        return None
    for tool in tools:
        if tool not in VALID_TOOLS:
            raise HTTPException(
                status_code=400,
                detail=error_response(f"无效的工具名称: {tool}", "INVALID_TOOL"),
            )
    return tools


def validate_task_id(task_id: str) -> str:
    """验证 task_id 是否为有效的 UUID 格式"""
    try:
        uuid.UUID(task_id)
        return task_id
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=error_response("无效的任务 ID 格式", "INVALID_TASK_ID"),
        )

# Cron 解析器实例
_cron_parser = CronParser()


# ============== 通用响应模型 ==============

def success_response(data: Any = None, message: str = "操作成功") -> dict:
    """成功响应"""
    return {"success": True, "data": data, "message": message}


def error_response(error: str, code: str = "ERROR") -> dict:
    """错误响应"""
    return {"success": False, "error": error, "code": code}


# ============== 任务队列管理 API ==============

@router.post("/tasks", status_code=201)
async def create_task(request: dict, current_user: CurrentUser = None) -> dict:
    """
    添加任务到队列

    请求体:
    - prompt: 任务描述（必填，最大 10000 字符）
    - workspace: 工作目录（可选，必须在允许的目录内）
    - timeout: 超时时间毫秒（可选，1000-3600000）
    - auto_approve: 是否自动批准工具操作（可选，默认 false）
    - allowed_tools: 允许使用的工具列表（可选，需为有效工具名）
    """
    # 验证所有字段
    prompt = validate_prompt(request.get("prompt"))
    workspace = validate_workspace(request.get("workspace"))
    timeout = validate_timeout(request.get("timeout"))
    allowed_tools = validate_allowed_tools(request.get("allowed_tools"))
    auto_approve = bool(request.get("auto_approve", False))

    # 创建任务
    task = Task(
        id=str(uuid.uuid4()),
        prompt=prompt,
        workspace=workspace,
        timeout=timeout,
        auto_approve=auto_approve,
        allowed_tools=allowed_tools,
    )

    # 添加到队列
    storage = get_storage()
    storage.queue.add(task)

    return success_response(task.to_dict(), "任务已添加到队列")


@router.get("/tasks")
async def list_tasks() -> dict:
    """获取队列列表"""
    storage = get_storage()
    tasks = storage.queue.get_all()
    return success_response([t.to_dict() for t in tasks])


@router.delete("/tasks/clear")
async def clear_tasks() -> dict:
    """清空队列"""
    storage = get_storage()
    storage.queue.clear()
    return success_response(message="队列已清空")


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: CurrentUser = None) -> dict:
    """删除队列中的任务"""
    task_id = validate_task_id(task_id)
    storage = get_storage()
    if not storage.queue.remove(task_id):
        raise HTTPException(
            status_code=404,
            detail=error_response("任务不存在", "TASK_NOT_FOUND"),
        )
    return success_response(message="任务已从队列中删除")


# ============== 定时任务管理 API ==============

@router.post("/scheduled-tasks", status_code=201)
async def create_scheduled_task(request: dict, current_user: CurrentUser = None) -> dict:
    """
    创建定时任务

    请求体:
    - name: 任务名称（必填，最大 100 字符）
    - prompt: 任务描述（必填，最大 10000 字符）
    - cron: Cron 表达式（必填）
    - workspace: 工作目录（可选，必须在允许的目录内）
    - timeout: 超时时间（可选，1000-3600000 毫秒）
    - auto_approve: 是否自动批准（可选，默认 false）
    - allowed_tools: 允许的工具列表（可选）
    - enabled: 是否启用（可选，默认 true）
    """
    # 验证必填字段
    name = validate_name(request.get("name"))
    prompt = validate_prompt(request.get("prompt"))
    cron = request.get("cron")

    if not cron or not cron.strip():
        raise HTTPException(
            status_code=400,
            detail=error_response("cron 不能为空", "VALIDATION_ERROR"),
        )
    cron = cron.strip()

    # 验证 Cron 表达式
    is_valid, error_msg = _cron_parser.validate(cron)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_response("无效的 Cron 表达式", "INVALID_CRON"),
        )

    # 验证可选字段
    workspace = validate_workspace(request.get("workspace"))
    timeout = validate_timeout(request.get("timeout"))
    allowed_tools = validate_allowed_tools(request.get("allowed_tools"))
    auto_approve = bool(request.get("auto_approve", False))
    enabled = bool(request.get("enabled", True))

    # 计算下次执行时间
    next_run = _cron_parser.calculate_next_run(cron)

    # 创建定时任务
    task = ScheduledTask(
        id=str(uuid.uuid4()),
        name=name,
        prompt=prompt,
        cron=cron,
        workspace=workspace,
        timeout=timeout,
        auto_approve=auto_approve,
        allowed_tools=allowed_tools,
        enabled=enabled,
        next_run=next_run.isoformat() if next_run else None,
    )

    # 保存
    storage = get_storage()
    storage.scheduled.save(task)

    return success_response(task.to_dict(), "定时任务已创建")


@router.get("/scheduled-tasks")
async def list_scheduled_tasks() -> dict:
    """获取定时任务列表"""
    storage = get_storage()
    tasks = storage.scheduled.get_all()
    return success_response([t.to_dict() for t in tasks])


@router.patch("/scheduled-tasks/{task_id}")
async def update_scheduled_task(task_id: str, request: dict, current_user: CurrentUser = None) -> dict:
    """更新定时任务"""
    task_id = validate_task_id(task_id)
    storage = get_storage()
    task = storage.scheduled.get(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail=error_response("定时任务不存在", "SCHEDULED_TASK_NOT_FOUND"),
        )

    # 更新字段（使用验证函数）
    if "name" in request and request["name"]:
        task.name = validate_name(request["name"])

    if "prompt" in request and request["prompt"]:
        task.prompt = validate_prompt(request["prompt"])

    if "cron" in request:
        cron = request["cron"]
        is_valid, error_msg = _cron_parser.validate(cron)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_response("无效的 Cron 表达式", "INVALID_CRON"),
            )
        task.cron = cron.strip()
        # 重新计算下次执行时间
        next_run = _cron_parser.calculate_next_run(cron)
        task.next_run = next_run.isoformat() if next_run else None

    if "workspace" in request:
        task.workspace = validate_workspace(request["workspace"])

    if "timeout" in request:
        task.timeout = validate_timeout(request["timeout"])

    if "auto_approve" in request:
        task.auto_approve = bool(request["auto_approve"])

    if "allowed_tools" in request:
        task.allowed_tools = validate_allowed_tools(request["allowed_tools"])

    if "enabled" in request:
        task.enabled = bool(request["enabled"])
        if not task.enabled:
            task.next_run = None
        else:
            # 重新启用时计算下次执行时间
            next_run = _cron_parser.calculate_next_run(task.cron)
            task.next_run = next_run.isoformat() if next_run else None

    task.updated_at = datetime.now().isoformat()
    storage.scheduled.save(task)

    return success_response(task.to_dict(), "定时任务已更新")


@router.delete("/scheduled-tasks/{task_id}")
async def delete_scheduled_task(task_id: str, current_user: CurrentUser = None) -> dict:
    """删除定时任务"""
    task_id = validate_task_id(task_id)
    storage = get_storage()
    if not storage.scheduled.delete(task_id):
        raise HTTPException(
            status_code=404,
            detail=error_response("定时任务不存在", "SCHEDULED_TASK_NOT_FOUND"),
        )
    return success_response(message="定时任务已删除")


@router.post("/scheduled-tasks/{task_id}/toggle")
async def toggle_scheduled_task(task_id: str, current_user: CurrentUser = None) -> dict:
    """启用/禁用定时任务"""
    task_id = validate_task_id(task_id)
    storage = get_storage()
    task = storage.scheduled.get(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail=error_response("定时任务不存在", "SCHEDULED_TASK_NOT_FOUND"),
        )

    # 切换状态
    task.enabled = not task.enabled

    if task.enabled:
        # 重新启用时计算下次执行时间
        next_run = _cron_parser.calculate_next_run(task.cron)
        task.next_run = next_run.isoformat() if next_run else None
    else:
        task.next_run = None

    task.updated_at = datetime.now().isoformat()
    storage.scheduled.save(task)

    message = "定时任务已启用" if task.enabled else "定时任务已禁用"
    return success_response(
        {"id": task.id, "enabled": task.enabled, "next_run": task.next_run},
        message,
    )


@router.post("/scheduled-tasks/{task_id}/run")
async def run_scheduled_task_now(task_id: str, current_user: CurrentUser = None) -> dict:
    """立即执行定时任务"""
    task_id = validate_task_id(task_id)
    scheduler = get_scheduler()
    task = scheduler.run_scheduled_now(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail=error_response("定时任务不存在", "SCHEDULED_TASK_NOT_FOUND"),
        )

    return success_response({"task_id": task.id}, "任务已添加到队列")


# ============== 任务状态查询 API ==============

@router.get("/tasks/running")
async def list_running_tasks() -> dict:
    """获取运行中任务"""
    storage = get_storage()
    tasks = storage.running.get_all()
    return success_response([t.to_dict() for t in tasks])


@router.get("/tasks/completed")
async def list_completed_tasks(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
) -> dict:
    """获取已完成任务（支持分页）"""
    storage = get_storage()
    result: PaginatedResponse = storage.history.get_completed(page, limit)
    return success_response({
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "limit": result.limit,
        "pages": result.pages,
    })


@router.get("/tasks/failed")
async def list_failed_tasks(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
) -> dict:
    """获取失败任务（支持分页）"""
    storage = get_storage()
    result: PaginatedResponse = storage.history.get_failed(page, limit)
    return success_response({
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "limit": result.limit,
        "pages": result.pages,
    })


@router.get("/tasks/{task_id}")
async def get_task_detail(task_id: str, current_user: CurrentUser = None) -> dict:
    """获取任务详情"""
    task_id = validate_task_id(task_id)
    storage = get_storage()

    # 从各个存储位置查找
    task = storage.queue.get(task_id)
    if task:
        return success_response(task.to_dict())

    task = storage.running.get(task_id)
    if task:
        return success_response(task.to_dict())

    # 从历史记录中查找
    for page in range(1, 100):  # 最多搜索 100 页
        result = storage.history.get_completed(page, 100)
        for item in result.items:
            if item.get("id") == task_id:
                return success_response(item)

        result = storage.history.get_failed(page, 100)
        for item in result.items:
            if item.get("id") == task_id:
                return success_response(item)

        # 如果当前页数据不足 100 条，说明已到末尾
        if len(result.items) < 100:
            break

    raise HTTPException(
        status_code=404,
        detail=error_response("任务不存在", "TASK_NOT_FOUND"),
    )


# ============== 调度器控制 API ==============

@router.get("/scheduler/status")
async def get_status() -> dict:
    """获取调度器状态"""
    status = get_scheduler_status()
    return success_response(status)


@router.post("/scheduler/start")
async def start() -> dict:
    """启动调度器"""
    success = await start_scheduler()
    if not success:
        raise HTTPException(
            status_code=400,
            detail=error_response("调度器已在运行中", "SCHEDULER_ALREADY_RUNNING"),
        )
    return success_response(message="调度器已启动")


@router.post("/scheduler/stop")
async def stop() -> dict:
    """停止调度器"""
    success = await stop_scheduler()
    if not success:
        raise HTTPException(
            status_code=400,
            detail=error_response("调度器未运行", "SCHEDULER_NOT_RUNNING"),
        )
    return success_response(message="调度器已停止")


# ============== Cron 表达式验证 API ==============

@router.post("/scheduler/validate-cron")
async def validate_cron(request: dict, current_user: CurrentUser = None) -> dict:
    """验证 Cron 表达式"""
    cron = request.get("cron")
    if not cron:
        raise HTTPException(
            status_code=400,
            detail=error_response("cron 不能为空", "VALIDATION_ERROR"),
        )

    is_valid, error_msg = _cron_parser.validate(cron)

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_response("无效的 Cron 表达式", "INVALID_CRON"),
        )

    # 获取下 5 次执行时间
    next_runs = _cron_parser.get_next_runs(cron, 5)

    return success_response({
        "valid": True,
        "next_runs": [dt.isoformat() for dt in next_runs],
    })


@router.get("/scheduler/cron-examples")
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
    now = datetime.now()
    for example in examples:
        next_run = _cron_parser.calculate_next_run(example["expression"], now)
        example["next_run_example"] = next_run.isoformat() if next_run else None

    return success_response(examples)
