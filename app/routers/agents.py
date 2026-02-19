"""Agent 监控 API"""

import uuid

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.agents.manager import Agent, AgentManager, AgentStatus, agent_manager

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def get_agents(
    status: str | None = Query(None, description="按状态过滤"),
    parent_task_id: str | None = Query(None, description="按父任务ID过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
):
    """获取子代理列表"""
    # 转换状态字符串到枚举
    status_enum = None
    if status:
        try:
            status_enum = AgentStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")

    agents = agent_manager.get_all_agents(
        status=status_enum,
        parent_task_id=parent_task_id,
        limit=limit,
    )

    return {
        "agents": [agent.model_dump(mode="json") for agent in agents],
        "total": len(agents),
        "running_count": agent_manager.get_running_count(),
    }


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """获取子代理详情"""
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="代理不存在")
    return agent.model_dump(mode="json")


@router.post("/{agent_id}/terminate")
async def terminate_agent(agent_id: str):
    """终止子代理"""
    success = agent_manager.terminate(agent_id)
    if not success:
        # 检查代理是否存在
        agent = agent_manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="代理不存在")
        raise HTTPException(status_code=400, detail="只能终止运行中的代理")

    return {"success": True, "message": "代理已终止"}


@router.get("/{agent_id}/logs")
async def get_agent_logs(agent_id: str):
    """获取日志流 (SSE)"""
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="代理不存在")

    async def event_generator():
        for log in agent.logs:
            yield f"data: {log}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{agent_id}/files")
async def get_agent_files(agent_id: str):
    """获取文件变更列表"""
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="代理不存在")

    return {
        "files": agent.files_changed,
        "count": len(agent.files_changed),
    }


@router.get("/{agent_id}/tools")
async def get_agent_tools(agent_id: str):
    """获取工具使用列表"""
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="代理不存在")

    return {
        "tools": agent.tools_used,
        "count": len(agent.tools_used),
    }


# 用于测试的辅助端点 - 创建模拟代理
@router.post("/debug/create")
async def create_debug_agent(
    parent_task_id: str = Query("test-task"),
    prompt: str = Query("测试代理任务"),
):
    """创建测试用代理（仅调试用）"""
    agent_id = f"sub_{uuid.uuid4().hex[:8]}"
    agent = agent_manager.create_agent(agent_id, parent_task_id, prompt)

    # 添加一些模拟数据
    agent.tools_used = ["Read", "Glob", "Grep"]
    agent.files_changed = ["src/main.py", "src/utils.py"]
    agent.logs = [
        "[10:30:45] Agent started",
        "[10:30:46] Reading file: src/main.py",
        "[10:30:47] Searching for patterns",
    ]

    return {"success": True, "agent": agent.model_dump(mode="json")}
