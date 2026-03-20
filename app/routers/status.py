"""状态和工具相关 API"""

import asyncio
import os
from pathlib import Path

from fastapi import APIRouter
from dotenv import load_dotenv

router = APIRouter(prefix="/api", tags=["status"])

# 全局任务存储
active_tasks: dict[str, asyncio.Task] = {}


@router.get("/status")
async def get_status(working_dir: str = "."):
    """
    获取服务状态

    v12.0.0.7: 返回实际的工作目录，而不是传入的参数
    """
    # 加载环境变量
    load_dotenv()

    # 获取实际的工作目录
    # 优先使用环境变量 WORKING_DIR
    actual_working_dir = os.getenv("WORKING_DIR")

    # 如果环境变量未设置，使用传入的 working_dir 并解析为绝对路径
    if not actual_working_dir:
        if working_dir and working_dir != ".":
            actual_working_dir = working_dir
        else:
            # 使用当前工作目录
            actual_working_dir = str(Path.cwd())

    return {
        "status": "running",
        "working_dir": actual_working_dir,
        "active_tasks": len(active_tasks),
    }


@router.get("/tools")
async def get_available_tools():
    """获取可用工具列表（扩展版，包含分类和文件修改标记）"""
    return {
        "tools": [
            {
                "name": "Read",
                "description": "读取文件内容",
                "category": "文件操作",
                "modifies_files": False,
            },
            {
                "name": "Write",
                "description": "创建新文件",
                "category": "文件操作",
                "modifies_files": True,
            },
            {
                "name": "Edit",
                "description": "编辑现有文件",
                "category": "文件操作",
                "modifies_files": True,
            },
            {
                "name": "Bash",
                "description": "运行终端命令",
                "category": "系统操作",
                "modifies_files": False,
            },
            {
                "name": "Glob",
                "description": "按模式查找文件",
                "category": "文件操作",
                "modifies_files": False,
            },
            {
                "name": "Grep",
                "description": "搜索文件内容",
                "category": "搜索",
                "modifies_files": False,
            },
            {
                "name": "WebSearch",
                "description": "搜索网络",
                "category": "网络",
                "modifies_files": False,
            },
            {
                "name": "WebFetch",
                "description": "获取网页内容",
                "category": "网络",
                "modifies_files": False,
            },
            {
                "name": "Task",
                "description": "启动子代理任务",
                "category": "代理",
                "modifies_files": False,
            },
        ]
    }
