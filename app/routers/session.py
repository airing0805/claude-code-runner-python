"""会话历史相关 API"""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user_optional
from app.routers.session_manager import session_manager
from app.services import extract_question
from app.services.path_utils import decode_project_name, get_project_dir_name

router = APIRouter(prefix="/api", tags=["session"])
logger = logging.getLogger(__name__)

# 路径配置
CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
METADATA_FILE = ".metadata.json"


class MetadataCache:
    """会话元数据缓存"""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.cache_file = project_dir / METADATA_FILE
        self._cache: dict[str, Any] = {}
        self._loaded = False

    def _load(self) -> None:
        """加载缓存文件"""
        if self._loaded:
            return
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._cache = {}
        self._loaded = True

    def _save(self) -> None:
        """保存缓存文件"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def get(self, session_file: Path) -> dict[str, Any] | None:
        """获取缓存的元数据（如果文件未修改）"""
        self._load()
        cache_key = session_file.name

        if cache_key not in self._cache:
            return None

        cached = self._cache[cache_key]
        cached_mtime = cached.get("mtime")

        # 检查文件修改时间
        if not session_file.exists():
            return None

        file_mtime = session_file.stat().st_mtime
        if cached_mtime != file_mtime:
            return None

        # 返回缓存的元数据（不包含 mtime 字段）
        metadata = cached.copy()
        metadata.pop("mtime", None)
        return metadata

    def set(self, session_file: Path, metadata: dict[str, Any]) -> None:
        """设置缓存"""
        self._load()
        cache_key = session_file.name

        # 获取文件修改时间
        mtime = 0.0
        if session_file.exists():
            mtime = session_file.stat().st_mtime

        self._cache[cache_key] = {
            "mtime": mtime,
            **metadata,
        }
        self._save()

    def invalidate(self, session_file: Path) -> None:
        """使缓存失效"""
        self._load()
        cache_key = session_file.name
        if cache_key in self._cache:
            del self._cache[cache_key]
            self._save()


def get_sessions_dir(working_dir: str) -> Path:
    """获取当前项目的会话目录"""
    project_dir_name = get_project_dir_name(working_dir)
    return CLAUDE_DIR / "projects" / project_dir_name


def parse_session_metadata(
    filepath: Path,
    cache: MetadataCache | None = None,
    extract_full_question: bool = False,
) -> dict[str, Any]:
    """
    解析会话文件获取元数据

    Args:
        filepath: 会话文件路径
        cache: 可选的元数据缓存实例
        extract_full_question: 是否提取完整提问文本（用于提问历史记录功能）
    """
    # 尝试从缓存获取
    if cache:
        cached = cache.get(filepath)
        if cached is not None:
            # 如果需要提取完整提问文本，但缓存中没有，则需要重新提取
            if extract_full_question and cached.get("has_question"):
                question_result = extract_question(filepath)
                if question_result:
                    cached["question_text"] = question_result.get("question_text", "")
            return cached

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            first_user_msg = None
            timestamp = None
            session_id = None
            message_count = 0
            tools_used: set[str] = set()
            cwd = None  # 工作目录
            has_question = False  # 是否存在有效用户提问
            question_timestamp = None  # 提问时间戳
            question_text = None  # 完整提问文本

            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    msg_type = data.get("type")

                    if msg_type == "user":
                        # 提取 cwd（工作目录）
                        if cwd is None:
                            cwd = data.get("cwd")

                        if not first_user_msg:
                            content = data.get("message", {}).get("content", [])
                            # 处理 content 为字符串的情况（简单文本消息）
                            if isinstance(content, str):
                                text = content
                                # 跳过包含 ide_selection 或 ide_opened_file 的块
                                if "<ide_selection>" not in text and "<ide_opened_file>" not in text:
                                    first_user_msg = text  # 保存完整文本，后续再截断
                            # 处理 content 为数组的情况（复杂消息）
                            elif content and isinstance(content, list):
                                for item in content:
                                    if item.get("type") == "text":
                                        text = item.get("text", "")
                                        # 跳过包含 ide_selection 或 ide_opened_file 的块
                                        if "<ide_selection>" in text or "<ide_opened_file>" in text:
                                            continue
                                        first_user_msg = text  # 保存完整文本，后续再截断
                                        break
                            timestamp = data.get("timestamp")
                            session_id = data.get("sessionId")

                            # 检查是否存在有效提问（用于缓存）
                            # 只有当 first_user_msg 不为空时才认为有有效提问
                            has_question = first_user_msg is not None
                            question_timestamp = timestamp
                        message_count += 1
                    elif msg_type == "assistant":
                        message_count += 1

                        # 提取工具使用信息
                        content = data.get("message", {}).get("content", [])
                        if content and isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "tool_use":
                                    tool_name = item.get("name", "")
                                    if tool_name:
                                        tools_used.add(tool_name)
                except json.JSONDecodeError:
                    continue

        # 如果需要提取完整提问文本
        if extract_full_question:
            question_result = extract_question(filepath)
            if question_result:
                question_text = question_result.get("question_text", "")
                has_question = bool(question_text)
                question_timestamp = question_result.get("timestamp") or question_timestamp

        # 生成标题和摘要
        # 标题：最大 100 字符
        title_text = first_user_msg or "无标题"
        if len(title_text) > 100:
            title_text = title_text[:100] + "..."
        # 摘要：最大 30 字符，用于下拉选择等空间受限场景
        summary_text = first_user_msg or "无摘要"
        if len(summary_text) > 30:
            summary_text = summary_text[:30] + "..."

        metadata = {
            "id": session_id or filepath.stem,
            "title": title_text,
            "summary": summary_text,  # 新增：会话摘要，用于下拉选择
            "timestamp": timestamp,
            "message_count": message_count,
            "size_bytes": filepath.stat().st_size if filepath.exists() else 0,
            "tools": sorted(list(tools_used)),
            "cwd": cwd,  # 返回工作目录
            # 提问缓存字段（用于提问历史记录功能）
            "has_question": has_question,
            "question_timestamp": question_timestamp,
        }

        # 如果提取了完整提问文本，也添加到元数据中
        if question_text:
            metadata["question_text"] = question_text

        # 更新缓存
        if cache:
            cache.set(filepath, metadata)

        return metadata
    except Exception as e:
        error_msg = f"解析错误: {str(e)[:30]}"
        error_metadata = {
            "id": filepath.stem,
            "title": error_msg,
            "summary": error_msg,  # 错误情况下摘要与标题相同
            "timestamp": None,
            "message_count": 0,
            "size_bytes": 0,
            "tools": [],
            "cwd": None,
            "has_question": False,
            "question_timestamp": None,
        }
        return error_metadata


def find_session_file(session_id: str) -> Optional[Path]:
    """在所有项目中查找会话文件"""
    if not PROJECTS_DIR.exists():
        return None

    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        # 尝试直接匹配文件名
        session_file = project_dir / f"{session_id}.jsonl"
        if session_file.exists():
            return session_file
        # 尝试匹配以 session_id 开头的文件
        for filepath in project_dir.glob("*.jsonl"):
            if filepath.stem.startswith(session_id[:8]):
                return filepath
    return None


@router.get("/sessions")
async def list_sessions(
    working_dir: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100, description="返回数量上限"),
    offset: int = Query(0, ge=0, description="偏移量"),
    sort_by: str = Query("timestamp", description="排序字段 (timestamp/title)"),
    order: str = Query("desc", description="排序方向 (asc/desc)"),
    current_user: Optional[any] = Depends(get_current_user_optional),
):
    """
    获取历史会话列表（支持分页和排序）

    支持可选认证：
    - 已认证用户：可以添加用户筛选（未来扩展）
    - 匿名用户：返回所有会话
    """
    # 记录用户信息
    if current_user:
        logger.info(f"会话列表查询 - 用户: {current_user.username} (ID: {current_user.id})")

    # 如果没有指定 working_dir，返回空列表（前端应该使用 /projects 接口获取项目列表）
    if not working_dir:
        return {"sessions": [], "total": 0, "limit": limit, "offset": offset}

    sessions_dir = get_sessions_dir(working_dir)

    if not sessions_dir.exists():
        return {"sessions": [], "total": 0, "limit": limit, "offset": offset}

    # 创建缓存实例
    cache = MetadataCache(sessions_dir)

    sessions = []
    for filepath in sessions_dir.glob("*.jsonl"):
        # 使用缓存解析元数据
        metadata = parse_session_metadata(filepath, cache=cache)
        sessions.append(metadata)

    # 排序
    if sort_by == "title":
        # 按标题排序，空标题（"无标题"）始终排在最后
        # 分离空标题和非空标题，分别排序后合并
        empty_title_sessions = [s for s in sessions if s.get("title") in ("无标题", "")]
        non_empty_sessions = [s for s in sessions if s.get("title") not in ("无标题", "")]

        # 对非空标题排序
        non_empty_sessions.sort(
            key=lambda x: (x.get("title") or "").lower(),
            reverse=(order == "desc")
        )

        # 合并：非空标题在前，空标题在后
        sessions = non_empty_sessions + empty_title_sessions
    else:
        # 默认按时间戳排序，None 值排在最后
        # 分离有时间戳和无时间戳的会话
        no_timestamp_sessions = [s for s in sessions if s.get("timestamp") is None]
        with_timestamp_sessions = [s for s in sessions if s.get("timestamp") is not None]

        # 对有时间戳的会话排序
        with_timestamp_sessions.sort(
            key=lambda x: x.get("timestamp") or "",
            reverse=(order == "desc")
        )

        # 合并：有时间戳的会话在前，无时间戳的在后
        sessions = with_timestamp_sessions + no_timestamp_sessions

    # 计算总会话数
    total = len(sessions)

    # 分页
    paginated_sessions = sessions[offset:offset + limit]

    # 计算总页数
    pages = (total + limit - 1) // limit if limit > 0 else 0

    return {
        "sessions": paginated_sessions,
        "total": total,
        "limit": limit,
        "offset": offset,
        "pages": pages,
    }


@router.get("/projects")
async def list_projects(
    page: int = 1,
    limit: int = 20,
    current_user: Optional[any] = Depends(get_current_user_optional),
):
    """
    获取所有项目列表（分页，使用缓存）

    支持可选认证：
    - 已认证用户：可以添加用户筛选（未来扩展）
    - 匿名用户：返回所有项目
    """
    # 记录用户信息
    if current_user:
        logger.info(f"项目列表查询 - 用户: {current_user.username} (ID: {current_user.id})")

    if not PROJECTS_DIR.exists():
        return {
            "projects": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "pages": 0
        }

    projects = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        # 创建缓存实例
        cache = MetadataCache(project_dir)

        # 统计会话数量和工具使用情况
        session_files = list(project_dir.glob("*.jsonl"))
        session_count = len(session_files)

        # 汇总所有会话中使用的工具，并获取真实路径
        all_tools: set[str] = set()
        real_path: str | None = None

        for session_file in session_files:
            # 使用缓存解析元数据
            metadata = parse_session_metadata(session_file, cache=cache)
            tools = metadata.get("tools", [])
            all_tools.update(tools)

            # 从会话文件中获取真实工作目录
            if real_path is None and metadata.get("cwd"):
                real_path = metadata.get("cwd")

        # 使用真实路径，如果无法获取则使用解码后的目录名
        project_path = real_path if real_path else decode_project_name(project_dir.name)

        projects.append({
            "encoded_name": project_dir.name,
            "path": project_path,
            "session_count": session_count,
            "tools": sorted(list(all_tools)),
        })

    # 按会话数量降序排序
    projects.sort(key=lambda x: x["session_count"], reverse=True)

    # 分页
    total = len(projects)
    pages = (total + limit - 1) // limit if limit > 0 else 0
    start = (page - 1) * limit
    end = start + limit
    paginated_projects = projects[start:end]

    return {
        "projects": paginated_projects,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }


@router.get("/projects/{project_name}/sessions")
async def list_project_sessions(project_name: str, page: int = 1, limit: int = 20):
    """获取指定项目的会话列表（分页，使用缓存）"""
    project_dir = PROJECTS_DIR / project_name

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")

    # 创建缓存实例
    cache = MetadataCache(project_dir)

    sessions = []
    project_path: str | None = None

    for filepath in project_dir.glob("*.jsonl"):
        # 使用缓存解析元数据
        metadata = parse_session_metadata(filepath, cache=cache)
        sessions.append(metadata)

        # 从会话文件中获取真实工作目录
        if project_path is None and metadata.get("cwd"):
            project_path = metadata.get("cwd")

    # 按时间戳降序排序，None 值排在最后
    no_timestamp_sessions = [s for s in sessions if s.get("timestamp") is None]
    with_timestamp_sessions = [s for s in sessions if s.get("timestamp") is not None]
    with_timestamp_sessions.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    sessions = with_timestamp_sessions + no_timestamp_sessions

    # 使用真实路径，如果无法获取则使用解码后的目录名
    if project_path is None:
        project_path = decode_project_name(project_name)

    # 分页
    total = len(sessions)
    pages = (total + limit - 1) // limit if limit > 0 else 0
    start = (page - 1) * limit
    end = start + limit
    paginated_sessions = sessions[start:end]

    return {
        "project_name": project_name,
        "project_path": project_path,
        "sessions": paginated_sessions,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }


def parse_content_blocks(message_content: list | str) -> list[dict[str, Any]]:
    """
    解析消息内容为内容块列表

    支持的内容类型：
    - text: 文本内容
    - thinking: 思考过程
    - tool_use: 工具调用
    - tool_result: 工具返回结果

    message_content 可以是：
    - 数组: 复杂消息格式
    - 字符串: 简单文本消息（如第一条用户消息）
    """
    blocks = []

    # 处理字符串类型的 content（简单的文本消息）
    if isinstance(message_content, str):
        # v9.0.2: 即使内容为空字符串，也保留消息结构
        # 用于保持消息链完整（空消息可能是 tool_use/tool_result 链的一部分）
        blocks.append({
            "type": "text",
            "text": message_content,
        })
        return blocks

    if not isinstance(message_content, list):
        # v9.0.2: 保留空内容块，用于消息链完整性
        blocks.append({
            "type": "text",
            "text": "",
        })
        return blocks

    # 第一遍：收集 tool_use 的 ID 到名称的映射（包括空名称的情况）
    tool_use_map: dict[str, str] = {}
    for item in message_content:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "tool_use":
            tool_use_id = item.get("id", "")
            tool_name = item.get("name", "")
            # v9.0.2: 即使 tool_name 为空也保存映射，用于关联 tool_result
            if tool_use_id:
                tool_use_map[tool_use_id] = tool_name

    # 第二遍：解析所有块
    for item in message_content:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")

        if item_type == "text":
            # v9.0.2: 即使 text 为空也保留，用于消息链完整性
            text = item.get("text", "")
            blocks.append({
                "type": "text",
                "text": text,
            })

        elif item_type == "thinking":
            thinking = item.get("thinking", "")
            # v9.0.2: 即使 thinking 为空也保留
            blocks.append({
                "type": "thinking",
                "thinking": thinking,
            })

        elif item_type == "tool_use":
            # v9.0.2: 即使 tool_input 为空也保留 tool_use，用于消息链完整
            blocks.append({
                "type": "tool_use",
                "tool_name": item.get("name", ""),
                "tool_input": item.get("input", {}),
                "tool_use_id": item.get("id", ""),
            })

        elif item_type == "tool_result":
            tool_use_id = item.get("tool_use_id", "")
            tool_name = tool_use_map.get(tool_use_id, "")
            # v9.0.2: 即使 content 为空也保留，用于消息链完整
            blocks.append({
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "tool_name": tool_name,
                "content": item.get("content", ""),
                "is_error": item.get("is_error", False),
            })

    # v9.0.2: 如果所有块都被过滤掉了，添加一个空文本块以保持消息结构
    if not blocks:
        blocks.append({
            "type": "text",
            "text": "",
        })

    return blocks


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(100, ge=1, le=500, description="每页数量"),
):
    """
    获取会话的消息历史（支持分页）

    v9.0.2: 添加分页支持，用于优化大文件会话加载性能
    """
    session_file = find_session_file(session_id)

    if not session_file:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 获取项目路径（备用：解码目录名）
    project_dir = session_file.parent
    encoded_name = project_dir.name
    fallback_path = decode_project_name(encoded_name)

    # v9.0.2: 第一遍扫描获取总消息数和项目路径
    all_messages = []
    project_path: str | None = None

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    msg_type = data.get("type")

                    if msg_type == "user":
                        # 获取真实工作目录
                        if project_path is None and data.get("cwd"):
                            project_path = data.get("cwd")

                        message = data.get("message", {})
                        content_blocks = parse_content_blocks(
                            message.get("content", [])
                        )

                        # v9.0.2: 始终添加消息，即使内容为空（用于保持消息链完整）
                        all_messages.append({
                            "role": "user",
                            "content": content_blocks,
                            "timestamp": data.get("timestamp"),
                            "uuid": data.get("uuid"),
                            # 添加 permissionMode 用于前端识别新会话轮次
                            "permissionMode": data.get("permissionMode"),
                        })

                    elif msg_type == "assistant":
                        message = data.get("message", {})
                        content_blocks = parse_content_blocks(
                            message.get("content", [])
                        )

                        # v9.0.2: 始终添加消息，即使内容为空（用于保持消息链完整）
                        all_messages.append({
                            "role": "assistant",
                            "content": content_blocks,
                            "timestamp": data.get("timestamp"),
                            "uuid": data.get("uuid"),
                            "stop_reason": message.get("stop_reason"),
                            "usage": message.get("usage"),
                        })
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取会话文件失败: {str(e)}")

    # 使用真实路径，如果无法获取则使用解码后的目录名
    final_path = project_path if project_path else fallback_path

    # v9.0.2: 计算分页
    total = len(all_messages)
    pages = (total + limit - 1) // limit if limit > 0 else 0
    start = (page - 1) * limit
    end = start + limit
    paginated_messages = all_messages[start:end]

    # v9.0.2: 返回分页信息和完整数据
    return {
        "session_id": session_id,
        "project_path": final_path,
        "messages": paginated_messages,
        # v9.0.2: 分页元数据
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": pages,
            "has_more": page < pages,
        }
    }


class AddMessageRequest(BaseModel):
    """添加消息请求"""
    session_id: str
    role: str  # "user" or "assistant"
    content: list[dict[str, Any]]
    working_dir: Optional[str] = None


@router.post("/sessions/{session_id}/messages")
async def add_session_message(session_id: str, request: AddMessageRequest):
    """添加消息到会话历史"""
    # 验证会话存在
    session_file = find_session_file(session_id)
    if not session_file:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 如果提供了 working_dir，使用它；否则从会话文件中获取
    working_dir = request.working_dir
    if not working_dir:
        # 从会话文件中读取工作目录
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("cwd"):
                            working_dir = data.get("cwd")
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

    # 构建消息格式（与 Claude Code 会话格式一致）
    message_data = {
        "type": request.role,
        "uuid": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "message": {
            "role": request.role,
            "content": request.content,
        },
    }

    if working_dir:
        message_data["cwd"] = working_dir

    # 追加到会话文件
    try:
        with open(session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(message_data, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存消息失败: {str(e)}")

    return {"success": True, "message": "消息已保存"}


# ============= 提问历史记录 API =============

from datetime import datetime, timedelta


def format_time_display(timestamp: str | None) -> str:
    """
    格式化时间显示

    Args:
        timestamp: ISO 格式时间戳

    Returns:
        格式化后的时间字符串
    """
    if not timestamp:
        return "未知时间"

    try:
        date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        now = datetime.now(date.tzinfo)

        # 计算时间差
        diff = (now - date).total_seconds()

        # 小于 1 分钟
        if diff < 60:
            return "刚刚"

        # 小于 1 小时
        if diff < 3600:
            return f"{int(diff // 60)} 分钟前"

        # 小于 24 小时
        if diff < 86400:
            return f"{int(diff // 3600)} 小时前"

        # 昨天
        yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        if date.replace(hour=0, minute=0, second=0, microsecond=0) == yesterday:
            return f"昨天 {date.strftime('%H:%M')}"

        # 小于 7 天
        if diff < 604800:
            return f"{int(diff // 86400)} 天前"

        # >= 7 天
        return date.strftime("%Y-%m-%d %H:%M")

    except Exception:
        return "未知时间"


@router.get("/projects/{project_name}/questions")
async def get_project_questions(
    project_name: str,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: Optional[any] = Depends(get_current_user_optional),
):
    """
    获取指定项目的提问列表（分页）

    支持可选认证：
    - 已认证用户：可以添加用户筛选（未来扩展）
    - 匿名用户：返回所有提问

    从项目的所有会话文件中提取首次用户提问，并按时间倒序排列。

    Args:
        project_name: 项目编码名称
        page: 页码，从 1 开始
        limit: 每页数量，最大 100

    Returns:
        {
            "success": true,
            "data": {
                "items": [
                    {
                        "id": "session_uuid",
                        "session_id": "session_uuid",
                        "project_name": "E--test-project",
                        "question_text": "完整提问内容",
                        "timestamp": "2026-03-05T10:30:00.000Z",
                        "time_display": "2 小时前"
                    }
                ],
                "total": 50,
                "page": 1,
                "limit": 20,
                "pages": 3
            },
            "project_path": "E:\\test\\project"
        }
    """
    # 验证项目目录
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取真实项目路径
    project_path = decode_project_name(project_name)

    # 创建缓存实例
    cache = MetadataCache(project_dir)

    # 提取所有提问
    questions = []

    for filepath in project_dir.glob("*.jsonl"):
        try:
            # 使用缓存解析元数据，同时提取完整提问文本
            metadata = parse_session_metadata(filepath, cache=cache, extract_full_question=True)

            # 检查是否有有效提问
            has_question = metadata.get("has_question", False)
            question_timestamp = metadata.get("question_timestamp") or metadata.get("timestamp")

            if has_question and question_timestamp:
                # 获取完整提问文本
                question_text = metadata.get("question_text", "")

                # 如果缓存中没有完整提问文本（可能是旧缓存），则从文件提取
                if not question_text:
                    result = extract_question(filepath)
                    if result:
                        question_text = result.get("question_text", "")

                if question_text:
                    questions.append({
                        "id": metadata.get("id", filepath.stem),
                        "session_id": metadata.get("id", filepath.stem),
                        "project_name": project_name,
                        "question_text": question_text,
                        "timestamp": question_timestamp,
                    })
        except Exception:
            # 跳过无法处理的文件
            continue

    # 按时间倒序排序
    questions.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    # 分页
    total = len(questions)
    pages = (total + limit - 1) // limit if total > 0 else 0
    start = (page - 1) * limit
    end = start + limit
    paginated_questions = questions[start:end]

    # 添加时间显示
    for question in paginated_questions:
        question["time_display"] = format_time_display(question.get("timestamp"))

    # 返回响应
    return {
        "success": True,
        "data": {
            "items": paginated_questions,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        },
        "project_path": project_path,
    }


class DeleteSessionResponse(BaseModel):
    """删除会话响应"""
    success: bool
    message: str
    session_id: str


@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    session_id: str,
    current_user: Optional[any] = Depends(get_current_user_optional),
):
    """
    删除会话文件及其元数据缓存

    支持可选认证：
    - 已认证用户：可以删除会话（未来扩展用户级权限）
    - 匿名用户：可以删除会话
    """
    # 记录用户信息
    if current_user:
        logger.info(f"删除会话 - 用户: {current_user.username} (ID: {current_user.id}), session_id: {session_id}")

    # 查找会话文件
    session_file = find_session_file(session_id)

    if not session_file:
        raise HTTPException(status_code=404, detail="会话不存在")

    try:
        # 获取项目目录并使缓存失效
        project_dir = session_file.parent
        cache = MetadataCache(project_dir)
        cache.invalidate(session_file)

        # 删除会话文件
        session_file.unlink()

        # 同步清理内存中的活跃会话（如果存在）
        await session_manager.remove_session(session_id)

        logger.info(f"已删除会话文件: {session_file}")
        return DeleteSessionResponse(
            success=True,
            message="会话已删除",
            session_id=session_id,
        )
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")
