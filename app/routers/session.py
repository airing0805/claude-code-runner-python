"""会话历史相关 API"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["session"])

# 路径配置
CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"


def decode_project_name(encoded_name: str) -> str:
    """解码项目目录名为原始路径"""
    import re
    match = re.match(r'^([A-Za-z])--(.+)$', encoded_name)
    if match:
        drive = match.group(1).upper()
        rest = match.group(2)
        path = rest.replace('-', '\\')
        return f"{drive}:\\{path}"
    return encoded_name.replace('-', '/')


def get_project_hash(project_path: str) -> str:
    """根据项目路径生成哈希值（与 Claude Code 一致）"""
    abs_path = Path(project_path).resolve()
    path_str = str(abs_path).replace("\\", "/")
    return hashlib.md5(path_str.encode()).hexdigest()[:16]


def get_sessions_dir(working_dir: str) -> Path:
    """获取当前项目的会话目录"""
    project_hash = get_project_hash(working_dir)
    return CLAUDE_DIR / "projects" / project_hash


def parse_session_metadata(filepath: Path) -> dict[str, Any]:
    """解析会话文件获取元数据"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            first_user_msg = None
            timestamp = None
            session_id = None
            message_count = 0
            tools_used: set[str] = set()
            cwd = None  # 工作目录

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
                                    first_user_msg = text[:80] + ("..." if len(text) > 80 else "")
                            # 处理 content 为数组的情况（复杂消息）
                            elif content and isinstance(content, list):
                                for item in content:
                                    if item.get("type") == "text":
                                        text = item.get("text", "")
                                        # 跳过包含 ide_selection 或 ide_opened_file 的块
                                        if "<ide_selection>" in text or "<ide_opened_file>" in text:
                                            continue
                                        first_user_msg = text[:80] + ("..." if len(text) > 80 else "")
                                        break
                            timestamp = data.get("timestamp")
                            session_id = data.get("sessionId")
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

        return {
            "id": session_id or filepath.stem,
            "title": first_user_msg or "无标题",
            "timestamp": timestamp,
            "message_count": message_count,
            "size": filepath.stat().st_size if filepath.exists() else 0,
            "tools": sorted(list(tools_used)),
            "cwd": cwd,  # 返回工作目录
        }
    except Exception as e:
        return {
            "id": filepath.stem,
            "title": f"解析错误: {str(e)[:30]}",
            "timestamp": None,
            "message_count": 0,
            "size": 0,
            "tools": [],
            "cwd": None,
        }


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
async def list_sessions(working_dir: str = "."):
    """获取历史会话列表（使用当前项目）"""
    sessions_dir = get_sessions_dir(working_dir)

    if not sessions_dir.exists():
        return {"sessions": []}

    sessions = []
    for filepath in sessions_dir.glob("*.jsonl"):
        metadata = parse_session_metadata(filepath)
        sessions.append(metadata)

    # 按时间戳降序排序
    sessions.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    return {"sessions": sessions}


@router.get("/projects")
async def list_projects():
    """获取所有项目列表"""
    if not PROJECTS_DIR.exists():
        return {"projects": []}

    projects = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        # 统计会话数量和工具使用情况
        session_files = list(project_dir.glob("*.jsonl"))
        session_count = len(session_files)

        # 汇总所有会话中使用的工具，并获取真实路径
        all_tools: set[str] = set()
        real_path: str | None = None

        for session_file in session_files:
            metadata = parse_session_metadata(session_file)
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

    return {"projects": projects}


@router.get("/projects/{project_name}/sessions")
async def list_project_sessions(project_name: str):
    """获取指定项目的会话列表"""
    project_dir = PROJECTS_DIR / project_name

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")

    sessions = []
    project_path: str | None = None

    for filepath in project_dir.glob("*.jsonl"):
        metadata = parse_session_metadata(filepath)
        sessions.append(metadata)

        # 从会话文件中获取真实工作目录
        if project_path is None and metadata.get("cwd"):
            project_path = metadata.get("cwd")

    # 按时间戳降序排序
    sessions.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    # 使用真实路径，如果无法获取则使用解码后的目录名
    if project_path is None:
        project_path = decode_project_name(project_name)

    return {
        "project_name": project_name,
        "project_path": project_path,
        "sessions": sessions
    }


def parse_content_blocks(message_content: list) -> list[dict[str, Any]]:
    """
    解析消息内容为内容块列表

    支持的内容类型：
    - text: 文本内容
    - thinking: 思考过程
    - tool_use: 工具调用
    - tool_result: 工具返回结果
    """
    blocks = []
    if not isinstance(message_content, list):
        return blocks

    # 第一遍：收集 tool_use 的 ID 到名称的映射
    tool_use_map: dict[str, str] = {}
    for item in message_content:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "tool_use":
            tool_use_id = item.get("id", "")
            tool_name = item.get("name", "")
            if tool_use_id and tool_name:
                tool_use_map[tool_use_id] = tool_name

    # 第二遍：解析所有块
    for item in message_content:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")

        if item_type == "text":
            text = item.get("text", "")
            if text:
                blocks.append({
                    "type": "text",
                    "text": text,
                })

        elif item_type == "thinking":
            thinking = item.get("thinking", "")
            if thinking:
                blocks.append({
                    "type": "thinking",
                    "thinking": thinking,
                })

        elif item_type == "tool_use":
            blocks.append({
                "type": "tool_use",
                "tool_name": item.get("name", ""),
                "tool_input": item.get("input", {}),
                "tool_use_id": item.get("id", ""),
            })

        elif item_type == "tool_result":
            tool_use_id = item.get("tool_use_id", "")
            tool_name = tool_use_map.get(tool_use_id, "")
            blocks.append({
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "tool_name": tool_name,
                "content": item.get("content", ""),
                "is_error": item.get("is_error", False),
            })

    return blocks


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """获取会话的消息历史"""
    session_file = find_session_file(session_id)

    if not session_file:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 获取项目路径（备用：解码目录名）
    project_dir = session_file.parent
    encoded_name = project_dir.name
    fallback_path = decode_project_name(encoded_name)

    messages = []
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

                        # 只有当有内容块时才添加消息
                        if content_blocks:
                            messages.append({
                                "role": "user",
                                "content": content_blocks,
                                "timestamp": data.get("timestamp"),
                                "uuid": data.get("uuid"),
                            })

                    elif msg_type == "assistant":
                        message = data.get("message", {})
                        content_blocks = parse_content_blocks(
                            message.get("content", [])
                        )

                        # 只有当有内容块时才添加消息
                        if content_blocks:
                            messages.append({
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

    return {
        "session_id": session_id,
        "project_path": final_path,
        "messages": messages,
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
