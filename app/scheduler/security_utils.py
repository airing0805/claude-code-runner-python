"""安全验证模块工具函数"""

from pathlib import Path


def is_safe_path(base_dir: str, user_path: str) -> bool:
    """
    检查用户路径是否在基础目录内（防止目录遍历）

    Args:
        base_dir: 基础目录
        user_path: 用户提供的路径

    Returns:
        bool: 路径是否安全
    """
    try:
        base = Path(base_dir).resolve()
        target = Path(user_path).resolve()
        target.relative_to(base)
        return True
    except ValueError:
        return False
    except Exception:
        return False


def sanitize_file_path(file_path: str) -> str:
    """
    清理文件路径，移除危险字符

    Args:
        file_path: 文件路径

    Returns:
        str: 清理后的路径
    """
    # 移除控制字符
    cleaned = "".join(char for char in file_path if ord(char) >= 32 or char in "\n\r\t")

    # 移除路径遍历模式
    cleaned = cleaned.replace("..", "")
    cleaned = cleaned.replace("~", "")

    return cleaned


def sanitize_input(text: str) -> str:
    """
    清理输入文本，移除潜在的危险字符

    Args:
        text: 输入文本

    Returns:
        str: 清理后的文本
    """
    # 移除控制字符（保留换行符、制表符）
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

    # 移除潜在的脚本注入
    text = text.replace("<script", "&lt;script", 1)
    text = text.replace("</script>", "&lt;/script&gt;")

    return text