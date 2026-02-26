"""数据模型单元测试"""

import pytest
import uuid
from datetime import datetime

from app.scheduler.models import Task, ScheduledTask, TaskStatus, PaginatedResponse


class TestTaskStatus:
    """TaskStatus 枚举测试"""

    def test_task_status_values(self):
        """测试任务状态枚举值"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_from_string(self):
        """测试从字符串创建状态"""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("running") == TaskStatus.RUNNING
        assert TaskStatus("completed") == TaskStatus.COMPLETED
        assert TaskStatus("failed") == TaskStatus.FAILED
        assert TaskStatus("cancelled") == TaskStatus.CANCELLED


class TestTask:
    """Task 数据模型测试"""

    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试任务",
            workspace="/test",
            timeout=600000,
        )

        assert task.prompt == "测试任务"
        assert task.workspace == "/test"
        assert task.timeout == 600000
        assert task.status == TaskStatus.PENDING
        assert task.retries == 0
        assert task.scheduled is False

    def test_task_default_values(self):
        """测试任务默认值"""
        task = Task(
            id=str(uuid.uuid4()),
            prompt="测试任务",
        )

        assert task.workspace == "."
        assert task.timeout == 600000
        assert task.auto_approve is False
        assert task.allowed_tools is None
        assert task.created_at is not None
        assert task.files_changed == []
        assert task.tools_used == []

    def test_task_to_dict(self):
        """测试任务转字典"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            prompt="测试任务",
            workspace="/test",
            timeout=600000,
            auto_approve=True,
            allowed_tools=["Read", "Edit"],
            status=TaskStatus.RUNNING,
        )

        result = task.to_dict()

        assert result["id"] == task_id
        assert result["prompt"] == "测试任务"
        assert result["workspace"] == "/test"
        assert result["timeout"] == 600000
        assert result["auto_approve"] is True
        assert result["allowed_tools"] == ["Read", "Edit"]
        assert result["status"] == "running"
        assert result["files_changed"] == []
        assert result["tools_used"] == []

    def test_task_from_dict(self):
        """测试从字典创建任务"""
        data = {
            "id": str(uuid.uuid4()),
            "prompt": "测试任务",
            "workspace": "/test",
            "timeout": 600000,
            "auto_approve": False,
            "status": "running",
            "files_changed": ["/test/file1.py"],
            "tools_used": ["Read"],
        }

        task = Task.from_dict(data)

        assert task.id == data["id"]
        assert task.prompt == "测试任务"
        assert task.workspace == "/test"
        assert task.status == TaskStatus.RUNNING
        assert task.files_changed == ["/test/file1.py"]
        assert task.tools_used == ["Read"]

    def test_task_from_dict_with_string_status(self):
        """测试从字典创建任务（状态为字符串）"""
        data = {
            "id": str(uuid.uuid4()),
            "prompt": "测试任务",
            "status": "completed",
        }

        task = Task.from_dict(data)

        assert task.status == TaskStatus.COMPLETED

    def test_task_round_trip(self):
        """测试任务序列化往返"""
        original = Task(
            id=str(uuid.uuid4()),
            prompt="测试任务",
            workspace="/test",
            timeout=300000,
            auto_approve=True,
            allowed_tools=["Read", "Glob", "Edit"],
            status=TaskStatus.FAILED,
            error="执行失败",
            files_changed=["/test/a.py", "/test/b.py"],
            tools_used=["Read", "Edit"],
            cost_usd=0.05,
            duration_ms=5000,
        )

        # 转换为字典
        data = original.to_dict()
        # 从字典恢复
        restored = Task.from_dict(data)

        assert restored.id == original.id
        assert restored.prompt == original.prompt
        assert restored.workspace == original.workspace
        assert restored.timeout == original.timeout
        assert restored.auto_approve == original.auto_approve
        assert restored.allowed_tools == original.allowed_tools
        assert restored.status == original.status
        assert restored.error == original.error
        assert restored.files_changed == original.files_changed
        assert restored.tools_used == original.tools_used
        assert restored.cost_usd == original.cost_usd
        assert restored.duration_ms == original.duration_ms


class TestScheduledTask:
    """ScheduledTask 数据模型测试"""

    def test_scheduled_task_creation(self):
        """测试定时任务创建"""
        task = ScheduledTask(
            id=str(uuid.uuid4()),
            name="定时任务测试",
            prompt="每天执行的任务",
            cron="0 * * * *",
            workspace="/test",
        )

        assert task.name == "定时任务测试"
        assert task.prompt == "每天执行的任务"
        assert task.cron == "0 * * * *"
        assert task.workspace == "/test"
        assert task.enabled is True
        assert task.run_count == 0

    def test_scheduled_task_default_values(self):
        """测试定时任务默认值"""
        task = ScheduledTask(
            id=str(uuid.uuid4()),
            name="测试",
            prompt="测试",
            cron="0 * * * *",
        )

        assert task.workspace == "."
        assert task.timeout == 600000
        assert task.auto_approve is False
        assert task.allowed_tools is None
        assert task.enabled is True
        assert task.last_run is None
        assert task.next_run is None
        assert task.created_at is not None
        assert task.updated_at is not None
        assert task.run_count == 0

    def test_scheduled_task_to_dict(self):
        """测试定时任务转字典"""
        task_id = str(uuid.uuid4())
        task = ScheduledTask(
            id=task_id,
            name="定时任务",
            prompt="任务描述",
            cron="0 0 * * *",
            workspace="/test",
            timeout=300000,
            enabled=False,
            last_run="2024-01-01T00:00:00",
            next_run="2024-01-02T00:00:00",
            run_count=5,
        )

        result = task.to_dict()

        assert result["id"] == task_id
        assert result["name"] == "定时任务"
        assert result["cron"] == "0 0 * * *"
        assert result["enabled"] is False
        assert result["last_run"] == "2024-01-01T00:00:00"
        assert result["next_run"] == "2024-01-02T00:00:00"
        assert result["run_count"] == 5

    def test_scheduled_task_from_dict(self):
        """测试从字典创建定时任务"""
        data = {
            "id": str(uuid.uuid4()),
            "name": "测试定时任务",
            "prompt": "任务描述",
            "cron": "*/5 * * * *",
            "workspace": "/workspace",
            "timeout": 300000,
            "auto_approve": True,
            "allowed_tools": ["Read", "Edit"],
            "enabled": True,
            "run_count": 10,
        }

        task = ScheduledTask.from_dict(data)

        assert task.id == data["id"]
        assert task.name == "测试定时任务"
        assert task.cron == "*/5 * * * *"
        assert task.workspace == "/workspace"
        assert task.timeout == 300000
        assert task.auto_approve is True
        assert task.enabled is True
        assert task.run_count == 10

    def test_scheduled_task_round_trip(self):
        """测试定时任务序列化往返"""
        original = ScheduledTask(
            id=str(uuid.uuid4()),
            name="测试定时任务",
            prompt="任务描述",
            cron="0 8 * * *",
            workspace="/project",
            timeout=1800000,
            auto_approve=True,
            allowed_tools=["Read", "Edit", "Glob", "Bash"],
            enabled=True,
            last_run="2024-01-01T08:00:00",
            next_run="2024-01-02T08:00:00",
            run_count=100,
        )

        data = original.to_dict()
        restored = ScheduledTask.from_dict(data)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.prompt == original.prompt
        assert restored.cron == original.cron
        assert restored.workspace == original.workspace
        assert restored.timeout == original.timeout
        assert restored.auto_approve == original.auto_approve
        assert restored.allowed_tools == original.allowed_tools
        assert restored.enabled == original.enabled
        assert restored.last_run == original.last_run
        assert restored.next_run == original.next_run
        assert restored.run_count == original.run_count


class TestPaginatedResponse:
    """PaginatedResponse 测试"""

    def test_paginated_response_creation(self):
        """测试分页响应创建"""
        response = PaginatedResponse(
            items=[{"id": "1"}, {"id": "2"}],
            total=100,
            page=1,
            limit=20,
            pages=5,
        )

        assert len(response.items) == 2
        assert response.total == 100
        assert response.page == 1
        assert response.limit == 20
        assert response.pages == 5

    def test_paginated_response_first_page(self):
        """测试第一页分页"""
        response = PaginatedResponse(
            items=[{"id": str(i)} for i in range(20)],
            total=100,
            page=1,
            limit=20,
            pages=5,
        )

        assert response.page == 1
        assert response.pages == 5

    def test_paginated_response_last_page(self):
        """测试最后一页分页"""
        response = PaginatedResponse(
            items=[{"id": str(i)} for i in range(20)],
            total=100,
            page=5,
            limit=20,
            pages=5,
        )

        assert response.page == 5
        assert response.pages == 5

    def test_paginated_response_empty(self):
        """测试空结果分页"""
        response = PaginatedResponse(
            items=[],
            total=0,
            page=1,
            limit=20,
            pages=1,
        )

        assert len(response.items) == 0
        assert response.total == 0
        assert response.pages == 1
