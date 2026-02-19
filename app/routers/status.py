"""状态和工具相关 API"""

import asyncio

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["status"])

# 全局任务存储
active_tasks: dict[str, asyncio.Task] = {}


@router.get("/status")
async def get_status(working_dir: str = "."):
    """获取服务状态"""
    return {
        "status": "running",
        "working_dir": working_dir,
        "active_tasks": len(active_tasks),
    }


@router.get("/tools")
async def get_available_tools():
    """获取可用工具列表"""
    return {
        "tools": [
            {"name": "Read", "description": "读取文件内容"},
            {"name": "Write", "description": "创建新文件"},
            {"name": "Edit", "description": "编辑现有文件"},
            {"name": "Bash", "description": "运行终端命令"},
            {"name": "Glob", "description": "按模式查找文件"},
            {"name": "Grep", "description": "搜索文件内容"},
            {"name": "WebSearch", "description": "搜索网络"},
            {"name": "WebFetch", "description": "获取网页内容"},
            {"name": "Task", "description": "启动子代理任务"},
        ]
    }
