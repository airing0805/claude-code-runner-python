#!/usr/bin/env python3
"""
测试任务超时检查功能
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# 创建测试数据
def create_test_running_task():
    """创建一个模拟的运行中任务，设置为19小时前开始"""
    running_file = Path("data/running.json")
    
    # 确保目录存在
    running_file.parent.mkdir(exist_ok=True)
    
    # 创建19小时前的时间戳
    now = datetime.now()
    started_time = now - timedelta(hours=19)
    
    test_task = {
        "id": "test-timeout-task-123",
        "prompt": "测试超时任务",
        "workspace": ".",
        "timeout": 600000,  # 10分钟超时
        "auto_approve": False,
        "allowed_tools": ["Read", "Write"],
        "created_at": (started_time - timedelta(minutes=1)).isoformat(),
        "started_at": started_time.isoformat(),
        "finished_at": None,
        "retries": 0,
        "status": "running",
        "source": "manual",
        "scheduled_id": None,
        "scheduled_name": None,
        "result": None,
        "error": None,
        "files_changed": [],
        "tools_used": [],
        "cost_usd": None,
        "duration_ms": None
    }
    
    # 写入运行中任务文件
    if running_file.exists():
        with open(running_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {"tasks": []}
    
    # 添加测试任务
    data["tasks"].append(test_task)
    
    with open(running_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"创建了测试任务，开始时间: {started_time}")
    print(f"当前时间: {now}")
    print(f"已运行时间: {19} 小时")
    print(f"超时限制: 10 分钟")

if __name__ == "__main__":
    create_test_running_task()
    print("测试任务创建完成！")
    print("现在可以启动调度器来测试超时检查功能。")