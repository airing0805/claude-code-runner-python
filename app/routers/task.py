"""任务执行相关 API"""

import json
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.claude_runner import ClaudeCodeClient

router = APIRouter(prefix="/api/task", tags=["task"])


class TaskRequest(BaseModel):
    """任务请求"""
    prompt: str
    working_dir: Optional[str] = None
    tools: Optional[list[str]] = None
    continue_conversation: bool = False
    resume: Optional[str] = None


class TaskResponse(BaseModel):
    """任务响应"""
    success: bool
    message: str
    session_id: Optional[str] = None
    cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    files_changed: list[str] = []
    tools_used: list[str] = []


@router.post("", response_model=TaskResponse)
async def run_task(task: TaskRequest, working_dir: str = "."):
    """
    执行任务 (同步等待结果)
    """
    client = ClaudeCodeClient(
        working_dir=task.working_dir or working_dir,
        allowed_tools=task.tools,
        continue_conversation=task.continue_conversation,
        resume=task.resume,
    )

    result = await client.run(task.prompt)

    return TaskResponse(
        success=result.success,
        message=result.message,
        session_id=result.session_id,
        cost_usd=result.cost_usd,
        duration_ms=result.duration_ms,
        files_changed=result.files_changed,
        tools_used=result.tools_used,
    )


@router.post("/stream")
async def run_task_stream(task: TaskRequest, working_dir: str = "."):
    """
    执行任务 (SSE 流式输出)
    """

    async def event_generator():
        client = ClaudeCodeClient(
            working_dir=task.working_dir or working_dir,
            allowed_tools=task.tools,
            continue_conversation=task.continue_conversation,
            resume=task.resume,
        )

        async for msg in client.run_stream(task.prompt):
            data = {
                "type": msg.type.value,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "tool_name": msg.tool_name,
                "tool_input": msg.tool_input,
                "metadata": msg.metadata,
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
