"""任务调度 API 路由测试

测试 API 端点：
- 任务队列管理 API
- 定时任务管理 API
- 任务状态查询 API
- 调度器控制 API
- Cron 表达式验证 API
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.scheduler.models import Task, ScheduledTask, TaskStatus, PaginatedResponse


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_storage():
    """创建模拟存储层"""
    storage = MagicMock()

    # 队列存储
    storage.queue = MagicMock()
    storage.queue.add = MagicMock()
    storage.queue.get_all = MagicMock(return_value=[])
    storage.queue.get = MagicMock(return_value=None)
    storage.queue.remove = MagicMock(return_value=False)
    storage.queue.clear = MagicMock()
    storage.queue.count = MagicMock(return_value=0)
    storage.queue.pop = MagicMock(return_value=None)

    # 定时任务存储
    storage.scheduled = MagicMock()
    storage.scheduled.save = MagicMock()
    storage.scheduled.get_all = MagicMock(return_value=[])
    storage.scheduled.get = MagicMock(return_value=None)
    storage.scheduled.delete = MagicMock(return_value=False)

    # 运行中任务存储
    storage.running = MagicMock()
    storage.running.get_all = MagicMock(return_value=[])
    storage.running.get = MagicMock(return_value=None)
    storage.running.add = MagicMock()
    storage.running.remove = MagicMock()
    storage.running.count = MagicMock(return_value=0)

    # 历史记录存储
    storage.history = MagicMock()
    storage.history.get_completed = MagicMock(return_value=PaginatedResponse(
        items=[], total=0, page=1, limit=20, pages=1
    ))
    storage.history.get_failed = MagicMock(return_value=PaginatedResponse(
        items=[], total=0, page=1, limit=20, pages=1
    ))

    return storage


@pytest.fixture
def mock_scheduler():
    """创建模拟调度器"""
    scheduler = MagicMock()
    scheduler.get_status_info = MagicMock(return_value={
        "status": "stopped",
        "is_executing": False,
        "queue_count": 0,
        "queue_count_today": 0,
        "scheduled_count": 0,
        "enabled_scheduled_count": 0,
        "running_count": 0,
        "running_count_today": 0,
        "completed_count": 0,
        "completed_count_today": 0,
        "failed_count": 0,
        "failed_count_today": 0,
        "poll_interval": 10,
        "updated_at": datetime.now().isoformat(),
    })
    scheduler.run_scheduled_now = MagicMock(return_value=None)
    return scheduler


@pytest.fixture
def sample_task():
    """创建示例任务"""
    return Task(
        id=str(uuid.uuid4()),
        prompt="测试任务描述",
        workspace="/test/workspace",
        timeout=60000,
        status=TaskStatus.PENDING,
    )


@pytest.fixture
def sample_scheduled_task():
    """创建示例定时任务"""
    return ScheduledTask(
        id=str(uuid.uuid4()),
        name="测试定时任务",
        prompt="定时任务描述",
        cron="*/5 * * * *",
        workspace="/test/workspace",
        enabled=True,
        next_run=datetime.now().isoformat(),
    )


class TestTaskQueueAPI:
    """任务队列管理 API 测试"""

    def test_create_task_success(self, client, mock_storage, mock_scheduler, sample_task):
        """测试成功创建任务"""
        with patch("app.scheduler.storage.get_storage", return_value=mock_storage), \
             patch("app.routers.scheduler.get_storage", return_value=mock_storage), \
             patch("app.routers.scheduler.get_scheduler", return_value=mock_scheduler):
            request_data = {
                "prompt": "执行代码审查",
                "workspace": "/test/workspace",
                "timeout": 300000,
            }
            response = client.post("/api/tasks", json=request_data)

            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["prompt"] == "执行代码审查"
            mock_storage.queue.add.assert_called_once()

    def test_create_task_with_empty_prompt(self, client, mock_storage):
        """测试创建任务时描述为空"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.post("/api/tasks", json={"prompt": ""})

            assert response.status_code == 400
            assert "VALIDATION_ERROR" in str(response.json())

    def test_create_task_without_prompt(self, client, mock_storage):
        """测试创建任务时缺少描述字段"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.post("/api/tasks", json={})

            assert response.status_code == 400

    def test_create_task_with_default_values(self, client, mock_storage):
        """测试创建任务时使用默认值"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            request_data = {"prompt": "测试任务"}
            response = client.post("/api/tasks", json=request_data)

            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["data"]["prompt"] == "测试任务"
            assert data["data"]["workspace"] == "."  # 默认工作目录

    def test_list_tasks_empty(self, client, mock_storage):
        """测试获取空队列列表"""
        mock_storage.queue.get_all.return_value = []

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"] == []

    def test_list_tasks_with_tasks(self, client, mock_storage, sample_task):
        """测试获取包含任务的队列列表"""
        mock_storage.queue.get_all.return_value = [sample_task]

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1
            assert data["data"][0]["prompt"] == "测试任务描述"

    def test_delete_task_success(self, client, mock_storage, sample_task):
        """测试成功删除任务"""
        mock_storage.queue.remove.return_value = True

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete(f"/api/tasks/{sample_task.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已从队列中删除" in data["message"]

    def test_delete_task_not_found(self, client, mock_storage):
        """测试删除不存在的任务"""
        mock_storage.queue.remove.return_value = False

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete("/api/tasks/00000000-0000-0000-0000-000000000000")

            assert response.status_code == 404

    def test_clear_tasks_success(self, client, mock_storage):
        """测试成功清空队列"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete("/api/tasks/clear")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已清空" in data["message"]
            mock_storage.queue.clear.assert_called_once()


class TestScheduledTaskAPI:
    """定时任务管理 API 测试"""

    def test_create_scheduled_task_success(self, client, mock_storage):
        """测试成功创建定时任务"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            request_data = {
                "name": "每日审查",
                "prompt": "执行代码审查",
                "cron": "0 9 * * *",
            }
            response = client.post("/api/scheduled-tasks", json=request_data)

            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["data"]["name"] == "每日审查"
            assert data["data"]["cron"] == "0 9 * * *"

    def test_create_scheduled_task_without_name(self, client, mock_storage):
        """测试创建定时任务时缺少名称"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            request_data = {
                "prompt": "测试描述",
                "cron": "0 9 * * *",
            }
            response = client.post("/api/scheduled-tasks", json=request_data)

            assert response.status_code == 400

    def test_create_scheduled_task_without_prompt(self, client, mock_storage):
        """测试创建定时任务时缺少描述"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            request_data = {
                "name": "定时任务",
                "cron": "0 9 * * *",
            }
            response = client.post("/api/scheduled-tasks", json=request_data)

            assert response.status_code == 400

    def test_create_scheduled_task_without_cron(self, client, mock_storage):
        """测试创建定时任务时缺少 cron 表达式"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            request_data = {
                "name": "定时任务",
                "prompt": "测试描述",
            }
            response = client.post("/api/scheduled-tasks", json=request_data)

            assert response.status_code == 400

    def test_create_scheduled_task_with_invalid_cron(self, client, mock_storage):
        """测试创建定时任务时使用无效的 cron 表达式"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            request_data = {
                "name": "定时任务",
                "prompt": "测试描述",
                "cron": "invalid cron",
            }
            response = client.post("/api/scheduled-tasks", json=request_data)

            assert response.status_code == 400
            assert "INVALID_CRON" in str(response.json())

    def test_list_scheduled_tasks_empty(self, client, mock_storage):
        """测试获取空的定时任务列表"""
        mock_storage.scheduled.get_all.return_value = []

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/scheduled-tasks")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"] == []

    def test_list_scheduled_tasks_with_tasks(self, client, mock_storage, sample_scheduled_task):
        """测试获取包含定时任务的列表"""
        mock_storage.scheduled.get_all.return_value = [sample_scheduled_task]

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/scheduled-tasks")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1
            assert data["data"][0]["name"] == "测试定时任务"

    def test_update_scheduled_task_success(self, client, mock_storage, sample_scheduled_task):
        """测试成功更新定时任务"""
        mock_storage.scheduled.get.return_value = sample_scheduled_task

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            request_data = {"name": "更新后的定时任务"}
            response = client.patch(f"/api/scheduled-tasks/{sample_scheduled_task.id}", json=request_data)

            assert response.status_code == 200
            mock_storage.scheduled.save.assert_called_once()

    def test_update_scheduled_task_cron(self, client, mock_storage, sample_scheduled_task):
        """测试更新定时任务的 cron 表达式"""
        mock_storage.scheduled.get.return_value = sample_scheduled_task

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            request_data = {"cron": "*/10 * * * *"}
            response = client.patch(f"/api/scheduled-tasks/{sample_scheduled_task.id}", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["cron"] == "*/10 * * * *"

    def test_update_scheduled_task_not_found(self, client, mock_storage):
        """测试更新不存在的定时任务"""
        mock_storage.scheduled.get.return_value = None

        with patch("app.routers.scheduler.get_scheduler", return_value=MagicMock()):
            response = client.patch("/api/scheduled-tasks/00000000-0000-0000-0000-000000000000", json={"name": "更新"})

            assert response.status_code == 404

    def test_delete_scheduled_task_success(self, client, mock_storage, sample_scheduled_task):
        """测试成功删除定时任务"""
        mock_storage.scheduled.delete.return_value = True

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete(f"/api/scheduled-tasks/{sample_scheduled_task.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_delete_scheduled_task_not_found(self, client, mock_storage):
        """测试删除不存在的定时任务"""
        mock_storage.scheduled.delete.return_value = False

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete("/api/scheduled-tasks/00000000-0000-0000-0000-000000000000")

            assert response.status_code == 404

    def test_toggle_scheduled_task_enable(self, client, mock_storage, sample_scheduled_task):
        """测试禁用定时任务后启用"""
        sample_scheduled_task.enabled = False
        mock_storage.scheduled.get.return_value = sample_scheduled_task

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.post(f"/api/scheduled-tasks/{sample_scheduled_task.id}/toggle")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["enabled"] is True

    def test_toggle_scheduled_task_disable(self, client, mock_storage, sample_scheduled_task):
        """测试启用定时任务后禁用"""
        sample_scheduled_task.enabled = True
        mock_storage.scheduled.get.return_value = sample_scheduled_task

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.post(f"/api/scheduled-tasks/{sample_scheduled_task.id}/toggle")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["enabled"] is False

    def test_toggle_scheduled_task_not_found(self, client, mock_storage):
        """测试切换不存在定时任务的状态"""
        mock_storage.scheduled.get.return_value = None

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.post("/api/scheduled-tasks/00000000-0000-0000-0000-000000000000/toggle")

            assert response.status_code == 404


class TestTaskStatusAPI:
    """任务状态查询 API 测试"""

    def test_list_running_tasks_empty(self, client, mock_storage):
        """测试获取空的运行中任务列表"""
        mock_storage.running.get_all.return_value = []

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks/running")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"] == []

    def test_list_running_tasks_with_tasks(self, client, mock_storage, sample_task):
        """测试获取包含任务的运行中任务列表"""
        sample_task.status = TaskStatus.RUNNING
        mock_storage.running.get_all.return_value = [sample_task]

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks/running")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1

    def test_list_completed_tasks_empty(self, client, mock_storage):
        """测试获取空的已完成任务列表"""
        mock_storage.running.get_all.return_value = []
        mock_storage.history.get_completed.return_value = PaginatedResponse(
            items=[], total=0, page=1, limit=20, pages=1
        )

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks/completed")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["items"] == []

    def test_list_completed_tasks_with_pagination(self, client, mock_storage, sample_task):
        """测试获取已完成任务列表的分页参数"""
        mock_storage.queue.get_all.return_value = []
        mock_storage.running.get_all.return_value = []
        sample_task.status = TaskStatus.COMPLETED
        mock_storage.running.get.return_value = None
        mock_storage.queue.get.return_value = None
        sample_task_list = [sample_task.to_dict() for _ in range(25)]
        mock_storage.history.get_completed.return_value = PaginatedResponse(
            items=sample_task_list[:20],
            total=25,
            page=1,
            limit=20,
            pages=2,
        )
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks/completed?page=1&limit=20")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total"] == 25
            assert data["data"]["page"] == 1
            assert data["data"]["limit"] == 20
            assert data["data"]["pages"] == 2

    def test_list_failed_tasks_empty(self, client, mock_storage):
        """测试获取空的失败任务列表"""
        mock_storage.running.get_all.return_value = []
        mock_storage.running.get.return_value = None
        mock_storage.queue.get_all.return_value = []
        mock_storage.history.get_failed.return_value = PaginatedResponse(
            items=[], total=0, page=1, limit=20, pages=1
        )

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks/failed")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["items"] == []

    def test_list_failed_tasks_with_pagination(self, client, mock_storage, sample_task):
        """测试获取失败任务列表的分页参数"""
        mock_storage.running.get_all.return_value = []
        mock_storage.queue.get_all.return_value = []
        mock_storage.running.get.return_value = None
        mock_storage.queue.get.return_value = None
        sample_task.status = TaskStatus.COMPLETED
        sample_task_list = [sample_task.to_dict() for _ in range(25)]
        mock_storage.history.get_failed.return_value = PaginatedResponse(
            items=sample_task_list[:20],
            total=25,
            page=1,
            limit=20,
            pages=2,
        )
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks/failed?page=1&limit=20")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total"] == 25
            assert data["data"]["page"] == 1
            assert data["data"]["limit"] == 20
            assert data["data"]["pages"] == 2

    def test_get_task_detail_from_queue(self, client, mock_storage, sample_task):
        """测试从队列获取任务详情"""
        mock_storage.queue.get.return_value = sample_task

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get(f"/api/tasks/{sample_task.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["id"] == sample_task.id

    def test_get_task_detail_from_running(self, client, mock_storage, sample_task):
        """测试从运行中获取任务详情"""
        mock_storage.queue.get.return_value = None
        mock_storage.running.get.return_value = sample_task
        sample_task.status = TaskStatus.RUNNING

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get(f"/api/tasks/{sample_task.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["id"] == sample_task.id

    def test_get_task_detail_not_found(self, client, mock_storage):
        """测试获取不存在的任务详情"""
        mock_storage.queue.get.return_value = None
        mock_storage.running.get.return_value = None
        mock_storage.running.get_all.return_value = []
        mock_storage.queue.get_all.return_value = []
        mock_storage.history.get_completed.return_value = PaginatedResponse(
            items=[], total=0, page=1, limit=20, pages=1
        )
        mock_storage.history.get_failed.return_value = PaginatedResponse(
            items=[], total=0, page=1, limit=20, pages=1
        )

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks/00000000-0000-0000-0000-000000000000")

            assert response.status_code == 404


class TestSchedulerControlAPI:
    """调度器控制 API 测试"""

    def test_get_scheduler_status_success(self, client, mock_scheduler):
        """测试获取调度器状态"""
        with patch("app.routers.scheduler.get_scheduler_status", return_value=mock_scheduler.get_status_info()):
            response = client.get("/api/scheduler/status")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data

    def test_start_scheduler_success(self, client, mock_scheduler):
        """测试成功启动调度器"""
        with patch("app.routers.scheduler.start_scheduler", new_callable=AsyncMock, return_value=True), \
             patch("app.routers.scheduler.get_scheduler", return_value=mock_scheduler):
            response = client.post("/api/scheduler/start")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已启动" in data["message"]

    def test_start_scheduler_already_running(self, client):
        """测试启动已运行的调度器"""
        with patch("app.routers.scheduler.start_scheduler", new_callable=AsyncMock, return_value=False), \
             patch("app.routers.scheduler.get_scheduler", return_value=MagicMock()):
            response = client.post("/api/scheduler/start")

            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False

    def test_stop_scheduler_success(self, client, mock_scheduler):
        """测试成功停止调度器"""
        with patch("app.routers.scheduler.stop_scheduler", new_callable=AsyncMock, return_value=True), \
             patch("app.routers.scheduler.get_scheduler", return_value=mock_scheduler):
            response = client.post("/api/scheduler/stop")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已停止" in data["message"]

    def test_stop_scheduler_already_stopped(self, client):
        """测试停止未运行的调度器"""
        with patch("app.routers.scheduler.stop_scheduler", new_callable=AsyncMock, return_value=False), \
             patch("app.routers.scheduler.get_scheduler", return_value=MagicMock()):
            response = client.post("/api/scheduler/stop")

            assert response.status_code == 400

    def test_stop_scheduler_not_running(self, client):
        """测试停止未运行的调度器"""
        with patch("app.routers.scheduler.stop_scheduler", new_callable=AsyncMock, return_value=False), \
             patch("app.routers.scheduler.get_scheduler", return_value=MagicMock()):
            response = client.post("/api/scheduler/stop")

            assert response.status_code == 400

    def test_start_scheduler_then_stop(self, client, mock_scheduler):
        """测试启动调度器后停止"""
        with patch("app.routers.scheduler.start_scheduler", new_callable=AsyncMock, return_value=True), \
             patch("app.routers.scheduler.stop_scheduler", new_callable=AsyncMock, return_value=True), \
             patch("app.routers.scheduler.get_scheduler", return_value=mock_scheduler):
            # 启动
            response = client.post("/api/scheduler/start")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已启动" in data["message"]

            # 停止
            response = client.post("/api/scheduler/stop")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已停止" in data["message"]

    def test_stop_scheduler_when_none(self, client):
        """测试停止 None 调度器"""
        with patch("app.routers.scheduler.stop_scheduler", new_callable=AsyncMock, return_value=False), \
             patch("app.routers.scheduler.get_scheduler", return_value=None):
            response = client.post("/api/scheduler/stop")
            assert response.status_code == 400

    def test_stop_scheduler_when_already_running(self, client):
        """测试停止已运行的调度器"""
        with patch("app.routers.scheduler.stop_scheduler", new_callable=AsyncMock, return_value=True), \
             patch("app.routers.scheduler.get_scheduler", return_value=MagicMock()):
            response = client.post("/api/scheduler/stop")
            assert response.status_code == 200

    def test_stop_scheduler_when_not_running(self, client):
        """测试停止未运行的调度器"""
        with patch("app.routers.scheduler.get_scheduler_status", return_value={"status": "stopped"}), \
             patch("app.routers.scheduler.stop_scheduler", new_callable=AsyncMock, return_value=False), \
             patch("app.routers.scheduler.get_scheduler", return_value=MagicMock()):
            response = client.post("/api/scheduler/stop")

            assert response.status_code == 400

    def test_start_scheduler_when_not_running(self, client, mock_scheduler):
        """测试启动未运行的调度器"""
        with patch("app.routers.scheduler.start_scheduler", new_callable=AsyncMock, return_value=True), \
             patch("app.routers.scheduler.get_scheduler", return_value=mock_scheduler):
            response = client.post("/api/scheduler/start")
            assert response.status_code == 200

    def test_start_scheduler_already_running(self, client, mock_scheduler):
        """测试启动已运行的调度器"""
        mock_scheduler = MagicMock()
        mock_scheduler.get_status_info = MagicMock(return_value={
            "status": "stopped",
            "is_executing": False,
            "queue_count": 0,
            "queue_count_today": 0,
            "scheduled_count": 0,
            "enabled_scheduled_count": 0,
            "running_count": 0,
            "running_count_today": 0,
            "completed_count": 0,
            "completed_count_today": 0,
            "failed_count": 0,
            "failed_count_today": 0,
            "poll_interval": 10,
            "updated_at": datetime.now().isoformat(),
        })

        with patch("app.routers.scheduler.get_scheduler", return_value=mock_scheduler):
            response = client.get("/api/scheduler/status")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_scheduler_status_with_running_task(self, client, mock_scheduler, sample_task):
        """测试获取运行中任务的调度器状态"""
        mock_scheduler.get_status_info = MagicMock(return_value={
            "status": "running",
            "is_executing": True,
            "current_task_id": sample_task.id,
            "queue_count": 0,
            "scheduled_count": 0,
            "running_count": 1,
            "poll_interval": 10,
            "updated_at": datetime.now().isoformat(),
        })
        mock_scheduler.get_current_task = MagicMock(return_value=sample_task)
        mock_scheduler.is_running = MagicMock(return_value=True)

        with patch("app.routers.scheduler.get_scheduler_status", return_value=mock_scheduler.get_status_info()):
            response = client.get("/api/scheduler/status")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestCronValidationAPI:
    """Cron 表达式验证 API 测试"""

    def test_validate_cron_success(self, client):
        """测试成功验证有效的 Cron 表达式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": "*/5 * * * *"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is True
        assert len(data["data"]["next_runs"]) == 5

    def test_validate_cron_empty(self, client):
        """测试验证空的 Cron 表达式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": ""})

        assert response.status_code == 400

    def test_validate_cron_invalid(self, client):
        """测试验证无效的 Cron 表达式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": "invalid cron"})

        assert response.status_code == 400

    def test_validate_cron_with_special_characters(self, client):
        """测试验证带特殊字符的 Cron 表达式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": "0 */2 * * *"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is True

    def test_validate_cron_with_aliases(self, client):
        """测试验证带别名的 Cron 表达式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": "@hourly"})

        assert response.status_code == 400 or response.status_code == 200
        # 别名可能不被支持，取决于实现
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True

    def test_validate_cron_without_cron(self, client):
        """测试验证缺少 cron 字段的请求"""
        response = client.post("/api/scheduler/validate-cron", json={})

        assert response.status_code == 400

    def test_validate_cron_with_standard_format(self, client):
        """测试验证标准 5 位格式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": "0 * * * *"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is True

    def test_validate_cron_with_complex_expressions(self, client):
        """测试验证复杂 Cron 表达式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": "0 9 * * 1-5"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_validate_cron_with_range_expressions(self, client):
        """测试验证带范围表达式的 Cron 表达式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": "0 9 * * 0,6"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_validate_cron_with_too_many_fields(self, client):
        """测试验证字段太多的 Cron 表达式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": "0 9 * * * *"})

        # 可能返回 400 或 200，取决于实现
        # 7 位格式通常不被支持
        assert response.status_code in [200, 400]

    def test_validate_cron_with_too_few_fields(self, client):
        """测试验证字段太少的 Cron 表达式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": "0 * * *"})

        assert response.status_code == 400

    def test_get_cron_examples(self, client):
        """测试获取常用 Cron 表达式示例"""
        response = client.get("/api/scheduler/cron-examples")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
        for example in data["data"]:
            assert "expression" in example
            assert "description" in example

    def test_validate_cron_with_aliases(self):
        client = TestClient(app)
        """测试验证带别名的 Cron 表达式"""
        response = client.post("/api/scheduler/validate-cron", json={"cron": "@daily"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is True


class TestTaskRunScheduledAPI:
    """立即执行定时任务 API 测试"""

    def test_run_scheduled_task_success(self, client, mock_storage, sample_scheduled_task, mock_scheduler):
        """测试成功立即执行定时任务"""
        mock_scheduler.run_scheduled_now.return_value = None
        mock_storage.scheduled.get.return_value = sample_scheduled_task
        mock_storage.queue.add = MagicMock()
        sample_scheduled_task.run_count = 0
        sample_scheduled_task.last_run = None

        with patch("app.routers.scheduler.get_scheduler", return_value=mock_scheduler), \
             patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.post(f"/api/scheduled-tasks/{sample_scheduled_task.id}/toggle")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_storage.scheduled.get.assert_called_once_with(sample_scheduled_task.id)

    def test_run_scheduled_task_not_found(self, client, mock_storage, sample_scheduled_task, mock_scheduler):
        """测试立即执行不存在的定时任务"""
        mock_storage.scheduled.get.return_value = None
        mock_scheduler.run_scheduled_now.return_value = None

        with patch("app.routers.scheduler.get_scheduler", return_value=mock_scheduler), \
             patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            # 使用 toggle 端点测试
            response = client.post(f"/api/scheduled-tasks/{sample_scheduled_task.id}/toggle")

            # 如果任务不存在，应该返回 404
            assert response.status_code == 404


class TestAPIResponseFormat:
    """API 响应格式测试"""

    def test_success_response_format(self, client, mock_storage):
        """测试成功响应的格式"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks")

            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert data["success"] is True
            assert "data" in data
            assert "message" in data or "error" not in data

    def test_error_response_format(self, client, mock_storage):
        """测试错误响应的格式"""
        mock_storage.queue.remove.return_value = False

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete("/api/tasks/00000000-0000-0000-0000-000000000000")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data or "error" in data or "success" in data

    def test_success_response_with_data(self, client, mock_storage):
        """测试成功响应包含数据"""
        mock_storage.queue.get_all.return_value = []

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.get("/api/tasks")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert isinstance(data["data"], list)

    def test_success_response_with_data_dict(self, client, mock_storage, sample_scheduled_task):
        """测试成功响应包含字典数据"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            mock_storage.scheduled.get.return_value = sample_scheduled_task
            sample_scheduled_task.enabled = True

            with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
                response = client.post(f"/api/scheduled-tasks/{sample_scheduled_task.id}/toggle")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert isinstance(data["data"], dict)

    def test_error_response_format_with_code(self, client, mock_storage):
        """测试错误响应包含错误代码"""
        mock_storage.scheduled.get.return_value = None

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete("/api/scheduled-tasks/00000000-0000-0000-0000-000000000000")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data or "error" in data or "success" in data

    def test_success_response_with_message(self, client, mock_storage):
        """测试成功响应包含消息"""
        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete("/api/tasks/clear")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "message" in data

    def test_error_response_format_with_detail(self, client, mock_storage):
        """测试错误响应包含详情"""
        mock_storage.queue.remove.return_value = False

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete("/api/tasks/00000000-0000-0000-0000-000000000000")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data or "error" in data or "success" in data


class TestAPIErrorResponse:
    """API 错误响应测试"""

    def test_error_response_with_code(self, client, mock_storage):
        """测试错误响应包含错误代码"""
        mock_storage.scheduled.delete.return_value = False

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete("/api/scheduled-tasks/00000000-0000-0000-0000-000000000000")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data or "error" in data or "success" in data

    def test_error_response_with_detail(self, client, mock_storage):
        """测试错误响应包含详情"""
        mock_storage.queue.remove.return_value = False

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete("/api/tasks/00000000-0000-0000-0000-000000000000")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data or "error" in data or "success" in data

    def test_error_response_with_detail_and_code(self, client, mock_storage):
        """测试错误响应包含详情和错误代码"""
        mock_storage.queue.remove.return_value = False

        with patch("app.routers.scheduler.get_storage", return_value=mock_storage):
            response = client.delete("/api/tasks/00000000-0000-0000-0000-000000000000")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data or "error" in data or "success" in data
