"""任务执行相关 API"""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional, Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.claude_runner import ClaudeCodeClient
from app.claude_runner.client import PermissionMode
from app.routers.session_manager import session_manager, SessionInfo

router = APIRouter(prefix="/api/task", tags=["task"])

# Claude Code 数据目录
CLAUDE_DIR = Path.home() / ".claude"


def get_project_hash(project_path: str) -> str:
    """根据项目路径生成哈希值（与 Claude Code 一致）"""
    abs_path = Path(project_path).resolve()
    path_str = str(abs_path).replace("\\", "/")
    return hashlib.md5(path_str.encode()).hexdigest()[:16]


async def save_user_message_to_session(session_id: str, prompt: str, cwd: str) -> None:
    """保存用户消息到会话文件"""
    try:
        # 获取项目目录
        project_hash = get_project_hash(cwd)
        project_dir = CLAUDE_DIR / "projects" / project_hash
        project_dir.mkdir(parents=True, exist_ok=True)

        # 创建会话文件
        session_file = project_dir / f"{session_id}.jsonl"

        # 构建用户消息格式
        message_data = {
            "type": "user",
            "uuid": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            },
            "cwd": cwd,
        }

        # 写入会话文件
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(message_data, ensure_ascii=False) + "\n")
    except Exception as e:
        # 记录错误但不影响主流程
        print(f"保存用户消息失败: {e}")


class TaskRequest(BaseModel):
    """任务请求"""
    prompt: str
    working_dir: Optional[str] = None
    tools: Optional[list[str]] = None
    continue_conversation: bool = False
    resume: Optional[str] = None
    permission_mode: PermissionMode = "default"


class TaskResponse(BaseModel):
    """任务响应"""
    success: bool
    message: str
    session_id: Optional[str] = None
    cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    files_changed: list[str] = []
    tools_used: list[str] = []


class QuestionAnswerRequest(BaseModel):
    """用户回答请求"""
    session_id: str
    question_id: str
    answer: Union[str, list[str], bool, None]
    follow_up_answers: Optional[dict[str, Union[str, list[str], bool, None]]] = None


class QuestionAnswerResponse(BaseModel):
    """用户回答响应"""
    success: bool
    message: str


class SessionStatusResponse(BaseModel):
    """会话状态响应"""
    session_id: str
    is_waiting: bool
    pending_question_id: Optional[str] = None
    created_at: float


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
        permission_mode=task.permission_mode,
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

    当遇到需要用户回答的问题时，会暂停并等待用户通过 /answer 接口提交答案
    """
    # 生成唯一会话 ID
    session_id = str(uuid.uuid4())

    # 确定工作目录
    cwd = task.working_dir or working_dir

    # 创建客户端
    client = ClaudeCodeClient(
        working_dir=cwd,
        allowed_tools=task.tools,
        continue_conversation=task.continue_conversation,
        resume=task.resume,
        permission_mode=task.permission_mode,
    )

    # 设置客户端的会话 ID
    client.set_session_id(session_id)

    # 注册会话到管理器
    await session_manager.create_session(session_id, client)

    # 保存用户消息到会话文件
    await save_user_message_to_session(session_id, task.prompt, cwd)

    # 用于控制迭代器完成
    iteration_done = asyncio.Event()

    async def event_generator():
        """SSE 事件生成器"""
        try:
            # 流式接收消息
            async for msg in client.run_stream(task.prompt):
                # 检查是否正在等待用户回答
                if client.is_waiting_answer():
                    # 设置会话为等待状态
                    await session_manager.set_waiting(session_id, True)

                data = {
                    "type": msg.type.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "tool_name": msg.tool_name,
                    "tool_input": msg.tool_input,
                    "session_id": session_id,
                    "metadata": msg.metadata,
                }

                # 添加 question 数据
                if msg.question:
                    data["question"] = {
                        "question_id": msg.question.question_id,
                        "question_text": msg.question.question_text,
                        "type": msg.question.type,
                        "header": msg.question.header,
                        "description": msg.question.description,
                        "required": msg.question.required,
                        "options": [
                            {
                                "id": opt.id,
                                "label": opt.label,
                                "description": opt.description,
                                "default": opt.default,
                            }
                            for opt in (msg.question.options or [])
                        ] if msg.question.options else None,
                        "follow_up_questions": {
                            parent_id: [
                                {
                                    "question_id": q.question_id,
                                    "question_text": q.question_text,
                                    "type": q.type,
                                    "required": q.required,
                                    "options": [
                                        {
                                            "id": opt.id,
                                            "label": opt.label,
                                            "description": opt.description,
                                            "default": opt.default,
                                        }
                                        for opt in (q.options or [])
                                    ] if q.options else None,
                                }
                                for q in questions
                            ]
                            for parent_id, questions in msg.question.follow_up_questions.items()
                        } if msg.question.follow_up_questions else None,
                    }

                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                # 当不再等待答案时，更新会话状态
                if not client.is_waiting_answer():
                    await session_manager.set_waiting(session_id, False)

            # 任务完成，清理会话
            await session_manager.remove_session(session_id)

        except Exception as e:
            # 发生错误时清理会话
            await session_manager.remove_session(session_id)
            error_data = {
                "type": "error",
                "content": f"执行错误: {str(e)}",
                "session_id": session_id,
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        finally:
            iteration_done.set()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/answer", response_model=QuestionAnswerResponse)
async def submit_answer(answer: QuestionAnswerRequest):
    """
    提交用户回答

    用户回答问答问题后调用此接口继续任务执行
    """
    # 获取会话
    session = await session_manager.get_session(answer.session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"会话不存在或已过期: {answer.session_id}"
        )

    if not session.is_waiting:
        raise HTTPException(
            status_code=400,
            detail="当前会话不在等待回答状态"
        )

    # 获取客户端
    client = session.client

    # 验证 question_id 匹配
    if not client.is_waiting_answer():
        raise HTTPException(
            status_code=400,
            detail="客户端不在等待回答状态"
        )

    # 验证 question_id 是否匹配
    pending_question_id = client.get_pending_question_id()
    if pending_question_id and pending_question_id != answer.question_id:
        raise HTTPException(
            status_code=400,
            detail=f"question_id 不匹配: 期望 {pending_question_id}, 收到 {answer.question_id}"
        )

    # 提交答案
    await client.submit_answer({
        "question_id": answer.question_id,
        "answer": answer.answer,
        "follow_up_answers": answer.follow_up_answers,
    })

    # 更新会话状态
    await session_manager.set_waiting(answer.session_id, False)

    return QuestionAnswerResponse(
        success=True,
        message="答案已提交，任务继续执行"
    )


@router.get("/session/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    获取会话状态

    用于查询会话是否正在等待用户回答
    """
    session_info = await session_manager.get_session_info(session_id)

    if not session_info:
        raise HTTPException(
            status_code=404,
            detail=f"会话不存在或已过期: {session_id}"
        )

    return SessionStatusResponse(
        session_id=session_info.session_id,
        is_waiting=session_info.is_waiting,
        pending_question_id=session_info.pending_question_id,
        created_at=session_info.created_at,
    )


@router.get("/sessions", response_model=list[SessionStatusResponse])
async def list_sessions():
    """
    列出所有活跃会话

    返回当前所有等待用户回答的会话
    """
    sessions = await session_manager.list_sessions()
    return [
        SessionStatusResponse(
            session_id=s.session_id,
            is_waiting=s.is_waiting,
            pending_question_id=s.pending_question_id,
            created_at=s.created_at,
        )
        for s in sessions
    ]
