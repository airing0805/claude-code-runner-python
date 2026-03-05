"""提问历史记录服务

提供从会话文件中提取提问文本的功能。
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class QuestionItem:
    """提问项数据模型"""

    id: str  # 提问唯一标识 (session_id)
    project_name: str  # 项目名称
    question_text: str  # 提问文本（完整内容）
    session_id: str  # 会话 ID
    timestamp: str  # 时间戳 (ISO格式)


@dataclass
class QuestionListResponse:
    """提问列表响应"""

    project_name: str
    project_path: str | None
    questions: list[QuestionItem]
    total: int
    page: int
    limit: int
    pages: int


# 敏感信息正则模式
SENSITIVE_PATTERNS = [
    # API Keys
    (r"sk-[a-zA-Z0-9]{20,}", "[API_KEY]"),
    (r"sk-ant-api03-[a-zA-Z0-9\-]{20,}", "[API_KEY]"),
    (r"anthropic[_-]?api[_-]?key['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", "[API_KEY]"),
    # Tokens
    (r"ghp_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN]"),
    (r"gho_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN]"),
    (r"ghu_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN]"),
    (r"ghs_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN]"),
    (r"ghr_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN]"),
    # Passwords
    (r"password['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", "[PASSWORD]"),
    (r"passwd['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", "[PASSWORD]"),
    # AWS
    (r"AKIA[0-9A-Z]{16}", "[AWS_ACCESS_KEY]"),
    (r"aws[_-]?secret[_-]?access[_-]?key['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", "[AWS_SECRET]"),
    # Generic secrets
    (r"secret['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", "[SECRET]"),
    (r"token['\"]?\s*[:=]\s*['\"][^'\"]+['\"]", "[TOKEN]"),
]


def mask_sensitive_info(text: str) -> str:
    """
    脱敏提问文本中的敏感信息

    Args:
        text: 原始文本

    Returns:
        脱敏后的文本
    """
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def _filter_ide_tags(text: str) -> str:
    """
    过滤 IDE 相关标签内容

    过滤以下标签:
    - <ide_selection>...</ide_selection>
    - <ide_opened_file>...</ide_opened_file>

    Args:
        text: 原始文本

    Returns:
        过滤后的文本
    """
    # 过滤 <ide_selection> 标签
    text = re.sub(
        r"<ide_selection>.*?</ide_selection>",
        "",
        text,
        flags=re.DOTALL,
    )
    # 过滤 <ide_opened_file> 标签
    text = re.sub(
        r"<ide_opened_file>.*?</ide_opened_file>",
        "",
        text,
        flags=re.DOTALL,
    )
    # 清理多余空白
    text = re.sub(r"\n\s*\n", "\n", text)
    return text.strip()


def extract_question(filepath: Path) -> dict[str, Any] | None:
    """
    从会话文件中提取首次用户提问

    Args:
        filepath: 会话文件路径 (.jsonl)

    Returns:
        包含提问信息的字典，如果没有找到提问则返回 None:
        {
            "id": str,              # session_id
            "question_text": str,   # 提问文本
            "timestamp": str,       # 时间戳
        }
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # 只处理用户消息
                if data.get("type") != "user":
                    continue

                message = data.get("message", {})
                if message.get("role") != "user":
                    continue

                content = message.get("content", [])
                if not isinstance(content, list):
                    continue

                # 提取文本内容
                text_parts: list[str] = []
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type")

                        # 跳过 tool_result 类型（这是工具返回结果，不是用户提问）
                        if item_type == "tool_result":
                            continue

                        if item_type == "text":
                            text_content = item.get("text", "")
                            if text_content:
                                text_parts.append(text_content)

                if not text_parts:
                    continue

                # 合并所有文本
                full_text = "\n".join(text_parts)

                # 过滤 IDE 标签
                filtered_text = _filter_ide_tags(full_text)

                if not filtered_text:
                    continue

                # 脱敏敏感信息
                masked_text = mask_sensitive_info(filtered_text)

                return {
                    "id": data.get("sessionId", filepath.stem),
                    "question_text": masked_text,
                    "timestamp": data.get("timestamp", ""),
                }

    except Exception:
        return None

    return None
