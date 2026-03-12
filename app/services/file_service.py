"""文件服务模块

提供目录遍历、文件读取、文件搜索等功能的业务逻辑层。
"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

# 配置常量
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_READ_LINES = 1000  # 最多读取行数
MAX_TREE_DEPTH = 5  # 目录树最大深度
MAX_SEARCH_RESULTS = 500  # 搜索结果最大数量

# 支持的编码
SUPPORTED_ENCODINGS = ["utf-8", "gbk", "gb2312", "latin-1"]

# MIME 类型映射
MIME_TYPES = {
    ".py": "text/x-python",
    ".js": "text/javascript",
    ".ts": "text/typescript",
    ".jsx": "text/jsx",
    ".tsx": "text/tsx",
    ".html": "text/html",
    ".css": "text/css",
    ".json": "application/json",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".xml": "application/xml",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".sh": "application/x-sh",
    ".bat": "application/x-bat",
    ".ps1": "application/x-powershell",
    ".sql": "application/sql",
    ".go": "text/x-go",
    ".rs": "text/x-rust",
    ".java": "text/x-java",
    ".c": "text/x-c",
    ".cpp": "text/x-c++",
    ".h": "text/x-c-header",
    ".hpp": "text/x-c++-header",
}


# ============= 数据模型 =============

@dataclass
class FileTreeNode:
    """目录树节点"""
    name: str
    path: str
    type: Literal["file", "directory"]
    size: Optional[int] = None
    extension: Optional[str] = None
    modified: Optional[str] = None
    children: list["FileTreeNode"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class FileContent:
    """文件内容"""
    path: str
    name: str
    size: int
    total_lines: int
    content: str
    truncated: bool
    has_more: bool
    encoding: str = "utf-8"


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    name: str
    type: Literal["file", "directory"]
    size: int
    size_formatted: str
    extension: Optional[str] = None
    mime_type: Optional[str] = None
    modified: Optional[str] = None
    created: Optional[str] = None


@dataclass
class SearchResult:
    """搜索结果"""
    pattern: str
    matches: list[dict]
    total: int
    truncated: bool


# ============= 异常定义 =============

class FileServiceError(Exception):
    """文件服务异常基类"""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class PathValidationError(FileServiceError):
    """路径验证错误"""

    def __init__(self, message: str, code: str):
        super().__init__(message, code)


class FileTooLargeError(FileServiceError):
    """文件过大错误"""

    def __init__(self, message: str):
        super().__init__(message, "FILE_TOO_LARGE")


class FileNotFoundError(FileServiceError):
    """文件不存在错误"""

    def __init__(self, message: str):
        super().__init__(message, "FILE_NOT_FOUND")


class DirectoryNotFoundError(FileServiceError):
    """目录不存在错误"""

    def __init__(self, message: str):
        super().__init__(message, "NOT_FOUND")


# ============= 路径验证器 =============

class PathValidator:
    """路径安全验证器"""

    # 敏感文件/目录模式
    SENSITIVE_PATTERNS = [
        r"\.env$",
        r"\.pem$",
        r"\.key$",
        r"\.secret$",
        r"\.password$",
        r"\.git/config$",
    ]

    # 禁止访问的系统目录
    FORBIDDEN_DIRS = {
        # Unix/Linux
        "/etc", "/root", "/boot", "/dev", "/proc", "/sys",
        "/var/log", "/var/lib", "/usr/bin", "/usr/sbin",
        # Windows
        "c:\\windows", "c:\\windows\\system32", "c:\\program files",
    }

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir.resolve()

    def validate(self, path: str) -> Path:
        """验证路径安全性"""
        # 1. 处理空路径
        if not path:
            return self._base_dir

        # 2. 解析绝对路径
        try:
            if os.path.isabs(path):
                abs_path = Path(path).resolve()
            else:
                abs_path = (self._base_dir / path).resolve()
        except Exception:
            raise PathValidationError("无效的路径格式", "INVALID_PATH")

        # 3. 检查是否在基础目录内
        try:
            abs_path.relative_to(self._base_dir)
        except ValueError:
            raise PathValidationError("路径超出允许范围", "FORBIDDEN_PATH")

        # 4. 检查路径遍历攻击
        if ".." in Path(path).parts:
            raise PathValidationError("不允许路径遍历", "INVALID_PATH")

        # 5. 检查敏感文件
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, str(abs_path), re.IGNORECASE):
                raise PathValidationError("禁止访问敏感文件", "FORBIDDEN_FILE")

        # 6. 检查系统目录
        path_str = str(abs_path).lower()
        for forbidden in self.FORBIDDEN_DIRS:
            if path_str.startswith(forbidden.lower()):
                raise PathValidationError("禁止访问系统目录", "FORBIDDEN_PATH")

        return abs_path


# ============= 文件大小格式化 =============

def format_file_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_mime_type(extension: str) -> Optional[str]:
    """获取 MIME 类型"""
    return MIME_TYPES.get(extension.lower())


# ============= 目录树构建器 =============

class TreeBuilder:
    """目录树构建器"""

    def build(
        self,
        root_path: Path,
        depth: int = 2,
        include_hidden: bool = False,
    ) -> FileTreeNode:
        """构建目录树"""
        if not root_path.exists():
            raise DirectoryNotFoundError(f"目录不存在: {root_path}")

        if not root_path.is_dir():
            raise FileServiceError("路径不是目录", "NOT_DIRECTORY")

        node = FileTreeNode(
            name=root_path.name or str(root_path),
            path=str(root_path),
            type="directory",
        )

        if depth > 0:
            node.children = self._build_children(
                root_path,
                depth - 1,
                include_hidden,
            )

        # 统计
        node.metadata["total_files"] = self._count_files(node)
        node.metadata["total_dirs"] = self._count_dirs(node)

        return node

    def _build_children(
        self,
        parent: Path,
        depth: int,
        include_hidden: bool,
    ) -> list[FileTreeNode]:
        """递归构建子节点"""
        children = []

        try:
            entries = sorted(
                parent.iterdir(),
                key=lambda e: (not e.is_dir(), e.name.lower()),
            )
        except PermissionError:
            return []

        for entry in entries:
            # 跳过隐藏文件
            if not include_hidden and entry.name.startswith("."):
                continue

            try:
                if entry.is_dir():
                    node = FileTreeNode(
                        name=entry.name,
                        path=str(entry),
                        type="directory",
                    )
                    if depth > 0:
                        node.children = self._build_children(
                            entry,
                            depth - 1,
                            include_hidden,
                        )
                    children.append(node)
                elif entry.is_file():
                    stat = entry.stat()
                    children.append(FileTreeNode(
                        name=entry.name,
                        path=str(entry),
                        type="file",
                        size=stat.st_size,
                        extension=entry.suffix,
                        modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    ))
            except PermissionError:
                continue

        return children

    def _count_files(self, node: FileTreeNode) -> int:
        """统计文件数量"""
        count = 0
        for child in node.children:
            if child.type == "file":
                count += 1
            elif child.type == "directory":
                count += self._count_files(child)
        return count

    def _count_dirs(self, node: FileTreeNode) -> int:
        """统计目录数量"""
        count = 0
        for child in node.children:
            if child.type == "directory":
                count += 1
                count += self._count_dirs(child)
        return count


# ============= 文件读取器 =============

class FileReader:
    """文件读取器"""

    def read(
        self,
        file_path: Path,
        start_line: int = 1,
        limit: int = 500,
    ) -> FileContent:
        """读取文件内容（分页）"""
        # 验证文件存在
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if not file_path.is_file():
            raise FileServiceError("路径不是文件", "NOT_FILE")

        # 验证文件大小
        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE:
            raise FileTooLargeError(f"文件过大: {format_file_size(size)}")

        # 读取内容
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise FileServiceError(f"文件读取失败: {e}", "READ_ERROR")

        lines = content.splitlines()

        # 计算分页
        total_lines = len(lines)
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, start_idx + limit)

        page_content = "\n".join(lines[start_idx:end_idx])

        return FileContent(
            path=str(file_path),
            name=file_path.name,
            size=size,
            total_lines=total_lines,
            content=page_content,
            truncated=len(content) > 50000,  # 超过50KB标记
            has_more=end_idx < total_lines,
        )


# ============= 文件搜索器 =============

class FileSearcher:
    """文件搜索器"""

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir

    def search(
        self,
        pattern: str,
        search_path: Optional[Path] = None,
        limit: int = 100,
    ) -> SearchResult:
        """搜索文件"""
        if search_path is None:
            search_path = self._base_dir

        matches: list[dict] = []
        truncated = False

        # 转换 Glob 模式
        glob_pattern = pattern
        if not pattern.startswith("*") and not pattern.startswith("**"):
            glob_pattern = f"**/{pattern}"

        try:
            for i, path in enumerate(search_path.glob(glob_pattern)):
                if i >= limit:
                    truncated = True
                    break

                if path.is_file():
                    try:
                        stat = path.stat()
                        matches.append({
                            "path": str(path),
                            "name": path.name,
                            "size": stat.st_size,
                        })
                    except PermissionError:
                        continue
        except Exception:
            pass

        return SearchResult(
            pattern=pattern,
            matches=matches,
            total=len(matches),
            truncated=truncated,
        )


# ============= 文件信息获取器 =============

class FileInfoGetter:
    """文件信息获取器"""

    def get_info(self, file_path: Path) -> FileInfo:
        """获取文件信息"""
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        stat = file_path.stat()
        is_dir = file_path.is_dir()

        return FileInfo(
            path=str(file_path),
            name=file_path.name,
            type="directory" if is_dir else "file",
            size=stat.st_size,
            size_formatted=format_file_size(stat.st_size),
            extension=file_path.suffix if not is_dir else None,
            mime_type=get_mime_type(file_path.suffix) if not is_dir else None,
            modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            created=datetime.fromtimestamp(stat.st_ctime).isoformat() if hasattr(stat, 'st_ctime') else None,
        )


# ============= 文件服务主类 =============

class FileService:
    """文件服务"""

    def __init__(self, working_dir: str = "."):
        self._working_dir = Path(working_dir).resolve()
        self._validator = PathValidator(self._working_dir)
        self._tree_builder = TreeBuilder()
        self._file_reader = FileReader()
        self._file_searcher = FileSearcher(self._working_dir)
        self._file_info_getter = FileInfoGetter()

    @property
    def working_dir(self) -> Path:
        return self._working_dir

    def get_tree(
        self,
        path: str = ".",
        depth: int = 2,
        include_hidden: bool = False,
    ) -> FileTreeNode:
        """获取目录树"""
        # 验证并获取安全路径
        safe_path = self._validator.validate(path)

        # 限制深度
        depth = min(max(1, depth), MAX_TREE_DEPTH)

        return self._tree_builder.build(safe_path, depth, include_hidden)

    def read_file(
        self,
        path: str,
        start_line: int = 1,
        limit: int = 500,
    ) -> FileContent:
        """读取文件内容"""
        # 验证并获取安全路径
        safe_path = self._validator.validate(path)

        # 限制参数
        start_line = max(1, start_line)
        limit = min(max(1, limit), MAX_READ_LINES)

        return self._file_reader.read(safe_path, start_line, limit)

    def search_files(
        self,
        pattern: str,
        path: str = ".",
        limit: int = 100,
    ) -> SearchResult:
        """搜索文件"""
        # 验证并获取安全路径
        safe_path = self._validator.validate(path)

        # 限制参数
        limit = min(max(1, limit), MAX_SEARCH_RESULTS)

        return self._file_searcher.search(pattern, safe_path, limit)

    def get_file_info(self, path: str) -> FileInfo:
        """获取文件信息"""
        # 验证并获取安全路径
        safe_path = self._validator.validate(path)

        return self._file_info_getter.get_info(safe_path)


# ============= 服务工厂 =============

_file_service_instance: Optional[FileService] = None


def get_file_service(working_dir: str = ".") -> FileService:
    """获取文件服务实例"""
    global _file_service_instance
    if _file_service_instance is None:
        _file_service_instance = FileService(working_dir)
    return _file_service_instance
