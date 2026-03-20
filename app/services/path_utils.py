"""路径编解码工具函数

提供项目路径与 Claude Code SDK 目录名之间的编解码转换功能。
使用简单编码规则：只转换盘符冒号和路径分隔符。
"""

import re
from pathlib import Path


def get_project_dir_name(project_path: str) -> str:
    """
    根据项目路径生成目录名（与 Claude Code SDK 一致）

    SDK 使用的命名规则（简单版本）：
    - Windows: E:\\workspaces_2026\\project → E--workspaces-2026-project
    - Unix: /home/user/project → -home-user-project
    - 盘符后的冒号转换为 --
    - 路径分隔符转换为 -
    - 其他字符（包括 _ 和 -）保持不变

    Args:
        project_path: 项目路径（可以是相对路径或绝对路径）

    Returns:
        编码后的目录名
    """
    abs_path = Path(project_path).resolve()
    path_str = str(abs_path)

    # Windows 路径处理
    if len(path_str) >= 2 and path_str[1] == ":":
        # E:\path → E--path
        drive = path_str[0].upper()
        rest = path_str[3:]  # 跳过 "X:\"
        # 先统一路径分隔符：前端可能传递 "/" 分隔符的路径
        rest = rest.replace("/", "\\")
        # 只转换路径分隔符
        rest = rest.replace("\\", "-")
        return f"{drive}--{rest}"
    else:
        # Unix 路径: /home/user → -home-user
        # 只转换路径分隔符
        encoded = path_str.replace("\\", "-").replace("/", "-")
        # 必须添加前缀 "-" 以符合设计规范
        if not encoded.startswith("-"):
            encoded = "-" + encoded
        return encoded


def decode_project_name(encoded_name: str) -> str:
    """
    解码项目目录名为原始路径（简单版本）

    解码规则（与编码对应）：
    - Windows: E--path → E:\\path
    - Unix: -home-user → /home/user

    Args:
        encoded_name: 编码后的目录名

    Returns:
        解码后的原始路径
    """
    # 匹配 Windows 路径格式：盘符--路径
    match = re.match(r'^([A-Za-z])--(.+)$', encoded_name)
    if match:
        drive = match.group(1).upper()
        rest = match.group(2)
        # 转换路径分隔符：- → \\
        path = rest.replace('-', '\\')
        return rf"{drive}:\{path}"
    else:
        # Unix 路径：移除前导的 -
        if encoded_name.startswith("-"):
            encoded_name = encoded_name[1:]
        # 转换路径分隔符
        path = encoded_name.replace('-', '/')
        return path


def encode_project_path(project_path: str) -> str:
    """
    编码项目路径（get_project_dir_name 的别名）

    为了 API 一致性提供的别名函数

    Args:
        project_path: 原始项目路径

    Returns:
        编码后的目录名
    """
    return get_project_dir_name(project_path)


def decode_project_dir(encoded_dir: str) -> str:
    """
    解码项目目录（decode_project_name 的别名）

    为了 API 一致性提供的别名函数

    Args:
        encoded_dir: 编码后的目录名

    Returns:
        原始项目路径
    """
    return decode_project_name(encoded_dir)


# 用于兼容旧版本的函数别名
get_project_hash = get_project_dir_name
