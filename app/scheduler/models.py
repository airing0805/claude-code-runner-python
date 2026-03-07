"""任务调度数据模型

定义 Task、ScheduledTask、TaskStatus 等数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from app.scheduler.timezone_utils import now_iso


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class TaskSource(str, Enum):
    """任务来源枚举"""

    MANUAL = "manual"  # 手动添加
    SCHEDULED = "scheduled"  # 定时任务自动触发
    IMMEDIATE = "immediate"  # 立即执行定时任务


@dataclass
class Task:
    """任务数据结构"""

    id: str  # 任务唯一标识 (UUID)
    prompt: str  # 任务描述/提示词
    workspace: str = "."  # 工作目录
    timeout: int = 600  # 超时时间（秒）
    auto_approve: bool = False  # 是否自动批准工具操作
    allowed_tools: Optional[list[str]] = None  # 允许使用的工具列表
    created_at: str = field(
        default_factory=lambda: now_iso()
    )  # 创建时间
    started_at: Optional[str] = None  # 开始执行时间
    finished_at: Optional[str] = None  # 结束时间
    retries: int = 0  # 当前重试次数
    status: TaskStatus = field(
        default_factory=lambda: TaskStatus.PENDING
    )  # 任务状态
    source: TaskSource = field(
        default_factory=lambda: TaskSource.MANUAL
    )  # 任务来源
    scheduled_id: Optional[str] = None  # 定时任务ID（如果来自定时任务）
    scheduled_name: Optional[str] = None  # 定时任务名称（如果来自定时任务）
    result: Optional[dict[str, Any]] = None  # 执行结果
    error: Optional[str] = None  # 错误信息（失败时）
    files_changed: list[str] = field(default_factory=list)  # 变更的文件列表
    tools_used: list[str] = field(default_factory=list)  # 使用过的工具列表
    cost_usd: Optional[float] = None  # 消耗费用（美元）
    duration_ms: Optional[int] = None  # 执行耗时（毫秒）

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "prompt": self.prompt,
            "workspace": self.workspace,
            "timeout": self.timeout,
            "auto_approve": self.auto_approve,
            "allowed_tools": self.allowed_tools,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "retries": self.retries,
            "status": self.status.value,
            "source": self.source.value,
            "scheduled_id": self.scheduled_id,
            "scheduled_name": self.scheduled_name,
            "result": self.result,
            "error": self.error,
            "files_changed": self.files_changed,
            "tools_used": self.tools_used,
            "cost_usd": self.cost_usd,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """从字典创建"""
        data = dict(data)  # 复制以避免修改原始数据

        # 定义 Task 类接受的字段（用于过滤未知字段）
        valid_fields = {
            "id", "prompt", "workspace", "timeout", "auto_approve",
            "allowed_tools", "created_at", "started_at", "finished_at",
            "retries", "status", "source", "scheduled_id", "scheduled_name",
            "result", "error", "files_changed", "tools_used", "cost_usd",
            "duration_ms",
        }

        # 过滤未知字段（防止因旧数据或混合数据导致错误）
        data = {k: v for k, v in data.items() if k in valid_fields}

        # 处理 status 字段转换
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus(data["status"])

        # 处理 source 字段转换
        if "source" in data and isinstance(data["source"], str):
            data["source"] = TaskSource(data["source"])

        # 兼容旧数据：将 scheduled 字段转换为 source
        if "source" not in data and "scheduled" in data:
            if data.get("scheduled"):
                data["source"] = TaskSource.SCHEDULED
            else:
                data["source"] = TaskSource.MANUAL
            # 移除旧字段避免传递给构造函数
            data.pop("scheduled", None)

        # 字段名映射：驼峰式 -> 蛇形式（前端可能使用驼峰式）
        field_mapping = {
            "autoApprove": "auto_approve",
            "allowedTools": "allowed_tools",
            "createdAt": "created_at",
            "startedAt": "started_at",
            "finishedAt": "finished_at",
            "scheduledId": "scheduled_id",
            "scheduledName": "scheduled_name",
        }

        for camel_key, snake_key in field_mapping.items():
            if camel_key in data:
                data[snake_key] = data.pop(camel_key)

        return cls(**data)


@dataclass
class ScheduledTask:
    """定时任务数据结构"""

    id: str  # 任务唯一标识 (UUID)
    name: str  # 任务名称
    prompt: str  # 任务描述/提示词
    cron: str  # Cron 表达式
    workspace: str = "."  # 工作目录
    timeout: int = 600  # 超时时间（秒）
    auto_approve: bool = False  # 是否自动批准工具操作
    allowed_tools: Optional[list[str]] = None  # 允许使用的工具列表
    enabled: bool = True  # 是否启用
    last_run: Optional[str] = None  # 上次执行时间（ISO 8601 格式）
    next_run: Optional[str] = None  # 下次执行时间（ISO 8601 格式）
                                      # - 可以为 null，表示未计算下次执行时间
                                      # - 当为 null 时，调度器不会触发该任务
                                      # - 首次创建时可为 null，启用时应计算并设置该值
    created_at: str = field(
        default_factory=lambda: now_iso()
    )  # 创建时间
    updated_at: str = field(
        default_factory=lambda: now_iso()
    )  # 更新时间

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "workspace": self.workspace,
            "cron": self.cron,
            "timeout": self.timeout,
            "auto_approve": self.auto_approve,
            "allowed_tools": self.allowed_tools,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduledTask":
        """从字典创建
        
        处理驼峰式命名到蛇形命名的转换（前端可能使用驼峰式）
        """
        data = dict(data)
        
        # 字段名映射：驼峰式 -> 蛇形式
        field_mapping = {
            "autoApprove": "auto_approve",
            "allowedTools": "allowed_tools",
            "cron": "cron",
            "createdAt": "created_at",
            "updatedAt": "updated_at",
            "nextRun": "next_run",
            "lastRun": "last_run",
        }

        for camel_key, snake_key in field_mapping.items():
            if camel_key in data:
                data[snake_key] = data.pop(camel_key)

        # 处理缺失的 name 字段（可能是旧数据导致）
        if "name" not in data:
            # 尝试从 id 生成默认 name
            data["name"] = data.get("id", "未命名任务")
        
        for camel_key, snake_key in field_mapping.items():
            if camel_key in data:
                data[snake_key] = data.pop(camel_key)
        
        return cls(**data)


@dataclass
class PaginatedResponse:
    """分页响应结构"""

    items: list[dict[str, Any]]
    total: int
    page: int
    limit: int
    pages: int


@dataclass
class TaskLog:
    """任务执行日志"""

    id: str  # 日志唯一标识 (UUID)
    task_id: str  # 关联的任务 ID
    timestamp: str  # 日志时间
    level: str  # 日志级别: INFO, WARNING, ERROR
    message: str  # 日志消息
    context: dict = field(default_factory=dict)  # 上下文信息

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskLog":
        """从字典创建"""
        return cls(**data)
