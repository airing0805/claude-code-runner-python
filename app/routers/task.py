"""任务执行相关 API"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional, Union

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.claude_runner import ClaudeCodeClient
from app.claude_runner.client import MessageType, PermissionMode
from app.routers.session_manager import session_manager, SessionInfo

router = APIRouter(prefix="/api/task", tags=["task"])

# Claude Code 数据目录
CLAUDE_DIR = Path.home() / ".claude"


def get_project_dir_name(project_path: str) -> str:
    """
    根据项目路径生成目录名（与 Claude Agent SDK 一致）

    SDK 使用的命名规则：
    - Windows: E:\\workspaces_2026\\project → E--workspaces-2026-project
    - Unix: /home/user/project → -home-user-project
    - 盘符后的冒号转换为 --
    - 路径分隔符和下划线都转换为 -
    """
    abs_path = Path(project_path).resolve()
    path_str = str(abs_path)

    # Windows 路径处理
    if len(path_str) >= 2 and path_str[1] == ":":
        # E:\path → E--path (从索引 3 跳过 "E:\")
        drive = path_str[0].upper()
        rest = path_str[3:].replace("\\", "-").replace("/", "-").replace("_", "-")
        return f"{drive}--{rest}"
    else:
        # Unix 路径: /home/user → -home-user
        return path_str.replace("\\", "-").replace("/", "-").replace("_", "-")


async def save_user_message_to_session(
    session_id: str,
    prompt: str,
    cwd: str,
    permission_mode: PermissionMode = "default",
) -> None:
    """
    保存用户消息到会话文件

    生成与 Claude Agent SDK 兼容的会话文件格式。
    注意：此函数仅在创建新会话时调用，恢复会话时不应该覆盖已有文件。
    """
    import subprocess

    try:
        # 获取项目目录
        project_hash = get_project_dir_name(cwd)
        project_dir = CLAUDE_DIR / "projects" / project_hash
        project_dir.mkdir(parents=True, exist_ok=True)

        # 会话文件路径
        session_file = project_dir / f"{session_id}.jsonl"

        # 如果文件已存在，不要覆盖（恢复会话的情况）
        if session_file.exists():
            logger.info(f"会话文件已存在，跳过创建: {session_file}")
            return

        # 获取 Git 分支（如果可用）
        git_branch = "master"
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                git_branch = result.stdout.strip() or "master"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # 构建符合 Claude Code 格式的用户消息
        message_uuid = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        message_data = {
            "parentUuid": None,  # 首条消息没有父消息
            "isSidechain": False,
            "userType": "external",
            "cwd": cwd.replace("/", "\\") if "\\" in cwd else cwd,
            "sessionId": session_id,
            "version": "2.1.47",  # Claude Code 版本
            "gitBranch": git_branch,
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            },
            "uuid": message_uuid,
            "timestamp": timestamp,
            "permissionMode": permission_mode,
        }

        # 写入会话文件
        with open(session_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(message_data, ensure_ascii=False) + "\n")

        logger.info(f"已创建会话文件: {session_file}")
    except Exception as e:
        # 记录错误但不影响主流程
        logger.warning(f"保存用户消息失败: {e}")


def check_session_file_valid(session_id: str, cwd: str) -> bool:
    """
    检查会话文件是否存在且格式有效

    跳过 queue-operation 等非消息类型的行，找到第一条真正的用户消息或助手消息来验证。
    兼容旧格式会话文件（第一行可能是 queue-operation）。

    Args:
        session_id: 会话 ID
        cwd: 工作目录

    Returns:
        bool: 会话文件是否有效
    """
    try:
        project_hash = get_project_dir_name(cwd)
        session_file = CLAUDE_DIR / "projects" / project_hash / f"{session_id}.jsonl"

        if not session_file.exists():
            logger.info(f"会话文件不存在: {session_file}")
            return False

        # 检查文件是否为空
        if session_file.stat().st_size == 0:
            logger.info(f"会话文件为空: {session_file}")
            return False

        # 检查文件格式：读取文件，跳过非消息类型的行
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                data = json.loads(line)
                msg_type = data.get("type")

                # 跳过非消息类型的行（如 queue-operation, progress 等）
                # 只验证 user 或 assistant 类型的消息
                if msg_type not in ("user", "assistant"):
                    logger.debug(f"跳过非消息行: type={msg_type}")
                    continue

                # 检查必要字段
                required_fields = ["type", "sessionId", "uuid", "message"]
                for field in required_fields:
                    if field not in data:
                        logger.info(f"会话文件消息缺少字段 {field}: {session_file}")
                        return False

                # 验证 sessionId 匹配
                if data.get("sessionId") != session_id:
                    logger.info(f"会话文件 sessionId 不匹配: 期望={session_id}, 实际={data.get('sessionId')}")
                    return False

                logger.info(f"会话文件有效: {session_file} (验证消息 type={msg_type})")
                return True

            # 遍历完所有行都没找到有效消息
            logger.info(f"会话文件未找到有效的用户/助手消息: {session_file}")
            return False

    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"检查会话文件失败: {e}")
        return False


class TaskRequest(BaseModel):
    """任务请求"""
    prompt: str
    working_dir: Optional[str] = None
    tools: Optional[list[str]] = None
    resume: Optional[str] = None
    new_session: bool = False  # 是否创建新会话（忽略 resume）
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
    # 原始问题数据，用于构建 toolUseResult
    raw_question_data: Optional[dict] = None


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


class NewSessionRequest(BaseModel):
    """新会话请求"""
    session_id: Optional[str] = None  # 如果指定，只结束该会话；否则结束所有会话


class NewSessionResponse(BaseModel):
    """新会话响应"""
    success: bool
    message: str
    ended_sessions: list[str] = []


@router.post("", response_model=TaskResponse)
async def run_task(task: TaskRequest, working_dir: str = "."):
    """
    执行任务 (同步等待结果)
    """
    client = ClaudeCodeClient(
        working_dir=task.working_dir or working_dir,
        allowed_tools=task.tools,
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
    # ========== 调试日志：入口 ==========
    import time
    request_start_time = time.time()
    logger.info(f"[SSE] ==================== 新请求开始 ====================")
    logger.info(f"[SSE] 请求详情: resume={task.resume}, new_session={task.new_session}, working_dir={task.working_dir}, prompt长度={len(task.prompt) if task.prompt else 0}")
    logger.info(f"[SSE] 当前所有会话数: {len(session_manager._sessions)}")
    logger.info(f"[SSE] 当前所有会话IDs: {list(session_manager._sessions.keys())}")

    # 确定工作目录
    cwd = task.working_dir or working_dir

    # 会话 ID 确定逻辑
    # 优先级：1. new_session=True → 创建新会话
    #         2. resume 参数有效 → 检查内存会话和文件有效性
    #         3. 创建新会话
    existing_session = None
    can_resume = False  # 是否可以真正恢复会话

    if task.new_session:
        # 用户明确请求新会话，忽略 resume 参数
        session_id = str(uuid.uuid4())
        logger.info(f"[SSE] new_session=True，创建新会话: session_id={session_id}")
    elif task.resume:
        # 尝试恢复已有会话
        existing_session = await session_manager.get_session(task.resume)

        # 检查会话文件是否有效
        session_file_valid = check_session_file_valid(task.resume, cwd)
        logger.info(f"[SSE] 会话文件有效性检查: session_id={task.resume}, valid={session_file_valid}")

        if existing_session and session_file_valid:
            # 内存会话存在且文件有效，可以恢复
            session_id = task.resume
            can_resume = True
            logger.info(f"[SSE] 恢复已有会话: session_id={session_id}, is_waiting={existing_session.is_waiting}")
        elif session_file_valid:
            # 文件有效但内存会话不存在（服务重启后的情况），也可以恢复
            session_id = task.resume
            can_resume = True
            logger.info(f"[SSE] 恢复文件中的会话: session_id={session_id}")
        else:
            # 会话文件无效，创建新会话
            session_id = str(uuid.uuid4())
            existing_session = None
            logger.info(f"[SSE] 会话文件无效，创建新会话: session_id={session_id}")
    else:
        # 生成新的会话 ID
        session_id = str(uuid.uuid4())
        logger.info(f"[SSE] 无 resume 参数，创建新会话: session_id={session_id}")

    # 创建客户端：只有 can_resume=True 时才传递 resume 参数
    client = ClaudeCodeClient(
        working_dir=cwd,
        allowed_tools=task.tools,
        resume=task.resume if can_resume else None,
        permission_mode=task.permission_mode,
    )

    logger.info(f"[SSE] 客户端配置: resume={task.resume if can_resume else None}, can_resume={can_resume}")

    # 设置客户端的会话 ID
    client.set_session_id(session_id)

    # 注册会话到管理器
    logger.info(f"[SSE] 创建会话: session_id={session_id}")
    await session_manager.create_session(session_id, client)

    # 注意：不再手动创建会话文件！
    # SDK 会自己创建和管理会话文件，手动创建可能导致格式不一致
    # 恢复会话时，SDK 会根据 resume 参数自动查找文件系统中的会话文件

    # 用于控制迭代器完成
    iteration_done = asyncio.Event()

    async def event_generator():
        """SSE 事件生成器"""
        # 用于跟踪 SDK 返回的真实 session_id
        sdk_session_id = None

        try:
            # 流式接收消息
            async for msg in client.run_stream(task.prompt):
                is_waiting = client.is_waiting_answer()
                session = await session_manager.get_session(session_id)
                session_is_waiting = session.is_waiting if session else False
                pending_qid = client.get_pending_question_id()

                # 检查是否有 SDK 返回的 session_id（在 complete 消息的 metadata 中）
                if msg.type == MessageType.COMPLETE and msg.metadata:
                    sdk_sid = msg.metadata.get("session_id")
                    if sdk_sid:
                        sdk_session_id = sdk_sid
                        logger.info(f"[SSE] SDK 返回的 session_id: {sdk_sid}")

                # 使用 SDK 的 session_id（如果有的话），否则使用后端生成的
                effective_session_id = sdk_session_id or session_id

                # ========== 调试日志：每次消息处理 ==========
                logger.info(
                    f"[SSE] ★★★ 消息处理: session_id={effective_session_id}, "
                    f"client.is_waiting_answer()={is_waiting}, "
                    f"session.is_waiting={session_is_waiting}, "
                    f"pending_question_id={pending_qid}, "
                    f"msg.type={msg.type.value}"
                )

                # 检查是否正在等待用户回答
                # 只在客户端真正在等待答案时设置等待状态，避免重复显示对话框
                if is_waiting:
                    # 只有当客户端真正在等待答案时才设置会话为等待状态
                    logger.info(f"[SSE] >>>>> 会话进入等待状态: session_id={effective_session_id}, reason=client_is_waiting={is_waiting}, msg_type={msg.type.value}")
                    await session_manager.set_waiting(session_id, True)
                    # 再次检查确认
                    session_after = await session_manager.get_session(session_id)
                    logger.info(f"[SSE] >>>>> set_waiting(True) 后的 session.is_waiting={session_after.is_waiting if session_after else 'N/A'}, client.is_waiting_answer={client.is_waiting_answer()}")
                # 注意：不再在其他消息时自动设置 is_waiting=False
                # 只有用户提交答案后才会清除等待状态

                data = {
                    "type": msg.type.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "tool_name": msg.tool_name,
                    "tool_input": msg.tool_input,
                    "session_id": effective_session_id,  # 使用 SDK 的 session_id
                    "metadata": msg.metadata,
                }

                # 添加 question 数据
                if msg.question:
                    # 检查会话状态
                    session_check = await session_manager.get_session(session_id)
                    session_waiting = session_check.is_waiting if session_check else "N/A"
                    logger.info(f"[SSE] 发送问答消息: session_id={session_id}, question_id={msg.question.question_id}, question_text={msg.question.question_text[:50]}..., session.is_waiting={session_waiting}")

                    # 获取原始问题数据（用于提交答案时构建 toolUseResult）
                    raw_question_data = getattr(msg.question, 'raw_tool_input', None)

                    data["question"] = {
                        "question_id": msg.question.question_id,
                        "question_text": msg.question.question_text,
                        "type": msg.question.type,
                        "header": msg.question.header,
                        "description": msg.question.description,
                        "required": msg.question.required,
                        "raw_question_data": raw_question_data,  # 原始问题数据
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

                # ========== 调试日志：发送的完整 SSE 消息 ==========
                logger.info(f"[SSE] >>>>> 发送消息: session_id={session_id}, type={msg.type.value}, content_length={len(msg.content or '')}")
                if msg.type.value == "ask_user_question" and msg.question:
                    logger.info(f"[SSE] >>>>> 完整 question 数据: {json.dumps(data.get('question', {}), ensure_ascii=False, indent=2)}")
                logger.info(f"[SSE] >>>>> 完整消息内容: {json.dumps(data, ensure_ascii=False, indent=2)[:2000]}")

                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            # 任务完成，保留会话以支持多轮对话
            # 不再自动删除会话，用户可以通过"新会话"按钮明确结束
            logger.info(f"[SSE] 任务完成，保留会话: session_id={session_id}")
            # 会话保留，支持用户继续对话
            # 将在用户点击"新会话"或超时时清理

        except Exception as e:
            # 发生错误时清理会话
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"[SSE] 发生错误，删除会话: session_id={session_id}, error={e}")
            logger.error(f"[SSE] 错误堆栈:\n{error_trace}")
            await session_manager.remove_session(session_id)
            error_data = {
                "type": "error",
                "content": f"执行错误: {str(e)}",
                "session_id": session_id,
                "error_detail": error_trace,  # 添加详细错误信息
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
    import time
    logger.info(f"[Answer] ★★★★★ 收到答案提交 ★★★★★")
    logger.info(f"[Answer] 提交的数据: session_id={answer.session_id}, question_id={answer.question_id}, answer={answer.answer}")
    logger.info(f"[Answer] 当前所有会话数: {len(session_manager._sessions)}")
    logger.info(f"[Answer] 当前所有会话IDs: {list(session_manager._sessions.keys())}")

    # 获取会话
    session = await session_manager.get_session(answer.session_id)

    # 打印完整的会话状态信息用于调试
    if session:
        session_age = time.time() - session.created_at
        logger.info(
            f"[Answer] ★ 会话状态详情: session_id={answer.session_id}, "
            f"is_waiting={session.is_waiting}, "
            f"created_at={session.created_at}, "
            f"age_seconds={session_age:.2f}"
        )
    else:
        logger.warning(f"[Answer] ★ 会话不存在: {answer.session_id}")

    if not session:
        logger.warning(f"[Answer] 会话不存在: {answer.session_id}")
        raise HTTPException(
            status_code=404,
            detail=f"会话不存在或已过期: {answer.session_id}"
        )

    if not session.is_waiting:
        logger.warning(f"[Answer] ★★★ 验证失败 - 会话不在等待状态 ★★★")
        logger.warning(f"[Answer] session_id={answer.session_id}, is_waiting={session.is_waiting}")
        # 打印所有会话状态供参考
        for sid, s in session_manager._sessions.items():
            logger.warning(f"[Answer] 参考 - 其他会话: session_id={sid}, is_waiting={s.is_waiting}")
        raise HTTPException(
            status_code=400,
            detail=f"当前会话不在等待回答状态 (session_id={answer.session_id})"
        )

    # 获取客户端
    client = session.client
    is_waiting = client.is_waiting_answer()
    pending_qid = client.get_pending_question_id()
    logger.info(f"[Answer] 客户端状态: is_waiting_answer={is_waiting}, pending_question_id={pending_qid}")

    # 验证客户端状态（如果客户端不在等待状态，但会话在等待，也允许继续）
    # 修复：放宽检查条件，允许在某些边界情况下提交答案
    client_waiting = client.is_waiting_answer()
    if not client_waiting and session.is_waiting:
        logger.warning(f"[Answer] ★ 会话在等待状态，但客户端不在等待（可能是边界情况），允许继续")
        # 仍然允许继续，因为会话状态可能是正确的

    # 验证 question_id 是否匹配
    pending_question_id = client.get_pending_question_id()
    if pending_question_id and pending_question_id != answer.question_id:
        logger.warning(f"[Answer] question_id 不匹配: 期望={pending_question_id}, 收到={answer.question_id}")
        raise HTTPException(
            status_code=400,
            detail=f"question_id 不匹配: 期望 {pending_question_id}, 收到 {answer.question_id}"
        )

    # 提交答案（带上原始问题数据，用于构建 toolUseResult）
    logger.info(f"[Answer] 提交答案: session_id={answer.session_id}")
    await client.submit_answer({
        "question_id": answer.question_id,
        "answer": answer.answer,
        "follow_up_answers": answer.follow_up_answers,
        "raw_question_data": answer.raw_question_data,  # 前端传来的原始问题数据
    })

    # 更新会话状态
    await session_manager.set_waiting(answer.session_id, False)
    logger.info(f"[Answer] 答案已提交，任务继续执行: session_id={answer.session_id}")

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

    返回当前所有活跃会话（包括等待回答和执行中的）
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


@router.post("/new-session", response_model=NewSessionResponse)
async def new_session(request: NewSessionRequest):
    """
    创建新会话（结束当前会话）

    用于用户点击"新会话"按钮，结束当前活跃会话
    """
    logger.info(f"[NewSession] 请求结束会话: {request.session_id}")

    ended_sessions = []

    if request.session_id:
        # 结束指定会话
        session = await session_manager.get_session(request.session_id)
        if session:
            await session_manager.remove_session(request.session_id)
            ended_sessions.append(request.session_id)
            logger.info(f"[NewSession] 已结束会话: {request.session_id}")
    else:
        # 结束所有会话
        all_sessions = await session_manager.list_sessions()
        for s in all_sessions:
            await session_manager.remove_session(s.session_id)
            ended_sessions.append(s.session_id)
        logger.info(f"[NewSession] 已结束所有会话: {ended_sessions}")

    return NewSessionResponse(
        success=True,
        message=f"已结束 {len(ended_sessions)} 个会话",
        ended_sessions=ended_sessions,
    )


@router.get("/session/{session_id}/exists")
async def session_exists(session_id: str):
    """
    检查会话是否存在

    用于前端判断会话是否仍然活跃
    """
    session = await session_manager.get_session(session_id)
    return {"exists": session is not None}
