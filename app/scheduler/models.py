"""任务调度数据模型

定义 Task、ScheduledTask、TaskStatus 等数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class Task:
    """任务数据结构"""

    id: str  # 任务唯一标识 (UUID)
    prompt: str  # 任务描述/提示词
    workspace: str = "."  # 工作目录
    timeout: int = 600000  # 超时时间（毫秒）
    auto_approve: bool = False  # 是否自动批准工具操作
    allowed_tools: Optional[list[str]] = None  # 允许使用的工具列表
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )  # 创建时间
    started_at: Optional[str] = None  # 开始执行时间
    finished_at: Optional[str] = None  # 结束时间
    retries: int = 0  # 当前重试次数
    status: TaskStatus = field(
        default_factory=lambda: TaskStatus.PENDING
    )  # 任务状态
    scheduled: bool = False  # 是否来自定时任务
    scheduled_id: Optional[str] = None  # 定时任务ID（如果来自定时任务）
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
            "scheduled": self.scheduled,
            "scheduled_id": self.scheduled_id,
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
        # 处理 status 字段转换
        if "status" in data and isinstance(data["status"], str):
            data = dict(data)
            data["status"] = TaskStatus(data["status"])
        return cls(**data)


@dataclass
class ScheduledTask:
    """定时任务数据结构"""

    id: str  # 任务唯一标识 (UUID)
    name: str  # 任务名称
    prompt: str  # 任务描述/提示词
    cron: str  # Cron 表达式
    workspace: str = "."  # 工作目录
    timeout: int = 600000  # 超时时间（毫秒）
    auto_approve: bool = False  # 是否自动批准工具操作
    allowed_tools: Optional[list[str]] = None  # 允许使用的工具列表
    enabled: bool = True  # 是否启用
    last_run: Optional[str] = None  # 上次执行时间
    next_run: Optional[str] = None  # 下次执行时间
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )  # 创建时间
    updated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )  # 更新时间
    run_count: int = 0  # 已执行次数

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
            "run_count": self.run_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduledTask":
        """从字典创建"""
        return cls(**data)


@dataclass
class PaginatedResponse:
    """分页响应结构"""

    items: list[dict[str, Any]]
    total: int
    page: int
    limit: int
    pages: int
