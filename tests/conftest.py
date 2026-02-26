"""测试配置和共享 fixtures"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import uuid

# 设置测试环境变量
os.environ["SCHEDULER_ALLOW_ANY_WORKSPACE"] = "true"


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # 清理
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_task_data():
    """示例任务数据"""
    return {
        "id": str(uuid.uuid4()),
        "prompt": "测试任务",
        "workspace": "/test/workspace",
        "timeout": 600000,
        "auto_approve": False,
        "allowed_tools": None,
    }


@pytest.fixture
def sample_scheduled_task_data():
    """示例定时任务数据"""
    return {
        "id": str(uuid.uuid4()),
        "name": "测试定时任务",
        "prompt": "测试任务描述",
        "cron": "0 * * * *",
        "workspace": "/test/workspace",
        "timeout": 600000,
        "auto_approve": False,
        "allowed_tools": None,
        "enabled": True,
    }


@pytest.fixture
def multiple_tasks_data():
    """多个任务数据用于分页测试"""
    tasks = []
    for i in range(25):
        tasks.append({
            "id": str(uuid.uuid4()),
            "prompt": f"测试任务 {i}",
            "workspace": "/test/workspace",
            "timeout": 600000,
            "auto_approve": False,
            "created_at": datetime.now().isoformat(),
            "status": "completed" if i % 2 == 0 else "failed",
        })
    return tasks
