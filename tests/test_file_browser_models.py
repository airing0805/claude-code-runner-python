"""文件浏览器数据模型测试

测试 FileTreeNode、FileContent、FileInfo、SearchResult 等数据模型。
"""

import pytest
from dataclasses import asdict
from pathlib import Path
import tempfile
import os
import shutil


class TestFileTreeNode:
    """FileTreeNode 数据模型测试"""

    def test_creation(self):
        """测试创建节点"""
        from app.services.file_service import FileTreeNode

        node = FileTreeNode(
            name="test",
            path="/test/path",
            type="file",
            size=100,
            extension=".txt"
        )

        assert node.name == "test"
        assert node.path == "/test/path"
        assert node.type == "file"
        assert node.size == 100
        assert node.extension == ".txt"

    def test_directory_type(self):
        """测试目录类型"""
        from app.services.file_service import FileTreeNode

        node = FileTreeNode(
            name="mydir",
            path="/test/mydir",
            type="directory"
        )

        assert node.type == "directory"
        assert node.extension is None

    def test_children(self):
        """测试子节点"""
        from app.services.file_service import FileTreeNode

        child = FileTreeNode(
            name="child.txt",
            path="/test/child.txt",
            type="file",
            size=50
        )

        parent = FileTreeNode(
            name="parent",
            path="/test/parent",
            type="directory",
            children=[child]
        )

        assert len(parent.children) == 1
        assert parent.children[0].name == "child.txt"

    def test_serialization(self):
        """测试序列化"""
        from app.services.file_service import FileTreeNode

        node = FileTreeNode(
            name="test",
            path="/test/path",
            type="file",
            size=100,
            extension=".txt"
        )

        data = asdict(node)
        assert data["name"] == "test"
        assert data["size"] == 100


class TestFileContent:
    """FileContent 数据模型测试"""

    def test_creation(self):
        """测试创建文件内容对象"""
        from app.services.file_service import FileContent

        content = FileContent(
            path="/test/file.txt",
            name="file.txt",
            size=100,
            total_lines=10,
            content="line1\nline2\n",
            truncated=False,
            has_more=False,
            encoding="utf-8"
        )

        assert content.path == "/test/file.txt"
        assert content.name == "file.txt"
        assert content.total_lines == 10
        assert content.truncated is False
        assert content.has_more is False
        assert content.encoding == "utf-8"

    def test_has_more_flag(self):
        """测试 has_more 标志"""
        from app.services.file_service import FileContent

        content = FileContent(
            path="/test/file.txt",
            name="file.txt",
            size=1000,
            total_lines=100,
            content="x" * 500,
            truncated=False,
            has_more=True
        )

        assert content.has_more is True


class TestFileInfo:
    """FileInfo 数据模型测试"""

    def test_creation(self):
        """测试创建文件信息对象"""
        from app.services.file_service import FileInfo

        info = FileInfo(
            path="/test/file.txt",
            name="file.txt",
            type="file",
            size=1024,
            size_formatted="1.0 KB",
            extension=".txt",
            mime_type="text/plain"
        )

        assert info.path == "/test/file.txt"
        assert info.name == "file.txt"
        assert info.type == "file"
        assert info.size == 1024
        assert info.size_formatted == "1.0 KB"
        assert info.extension == ".txt"
        assert info.mime_type == "text/plain"

    def test_directory_info(self):
        """测试目录信息"""
        from app.services.file_service import FileInfo

        info = FileInfo(
            path="/test/mydir",
            name="mydir",
            type="directory",
            size=4096,
            size_formatted="4.0 KB"
        )

        assert info.type == "directory"
        assert info.extension is None
        assert info.mime_type is None


class TestSearchResult:
    """SearchResult 数据模型测试"""

    def test_creation(self):
        """测试创建搜索结果对象"""
        from app.services.file_service import SearchResult

        result = SearchResult(
            pattern="*.py",
            matches=[
                {"path": "/test/a.py", "name": "a.py", "size": 100},
                {"path": "/test/b.py", "name": "b.py", "size": 200},
            ],
            total=2,
            truncated=False
        )

        assert result.pattern == "*.py"
        assert len(result.matches) == 2
        assert result.total == 2
        assert result.truncated is False

    def test_truncated_result(self):
        """测试截断的搜索结果"""
        from app.services.file_service import SearchResult

        result = SearchResult(
            pattern="*",
            matches=[{"path": f"/test/{i}.txt", "name": f"{i}.txt", "size": 100} for i in range(100)],
            total=100,
            truncated=True
        )

        assert result.truncated is True
        assert len(result.matches) == 100


class TestFileService:
    """FileService 功能测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())

        # 创建测试文件结构
        (temp_path / "test.py").write_text("print('hello')")
        (temp_path / "readme.md").write_text("# Test")
        (temp_path / "data.json").write_text('{"key": "value"}')
        (temp_path / "subdir").mkdir()
        (temp_path / "subdir" / "nested.py").write_text("def test(): pass")

        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_get_tree(self, temp_dir):
        """测试获取目录树"""
        from app.services.file_service import FileService

        service = FileService(str(temp_dir))
        result = service.get_tree(".", depth=2)

        assert result.name == str(temp_dir.name) or result.name == str(temp_dir).split(os.sep)[-1]
        assert result.type == "directory"

    def test_get_tree_with_depth(self, temp_dir):
        """测试带深度的目录树"""
        from app.services.file_service import FileService

        service = FileService(str(temp_dir))

        # 深度为 1
        result = service.get_tree(".", depth=1)
        assert result.type == "directory"

        # 深度为 2，应该包含子目录内容
        result = service.get_tree(".", depth=2)
        # 子目录应该存在
        has_subdir = any(child.name == "subdir" for child in result.children)
        assert has_subdir

    def test_read_file(self, temp_dir):
        """测试读取文件"""
        from app.services.file_service import FileService

        service = FileService(str(temp_dir))
        result = service.read_file("test.py")

        assert result.name == "test.py"
        assert "print('hello')" in result.content
        assert result.total_lines == 1

    def test_read_file_pagination(self, temp_dir):
        """测试分页读取"""
        from app.services.file_service import FileService

        # 创建多行文件
        content = "\n".join([f"line {i}" for i in range(100)])
        (temp_dir / "multiline.txt").write_text(content)

        service = FileService(str(temp_dir))

        # 读取前 10 行
        result = service.read_file("multiline.txt", start_line=1, limit=10)
        assert result.has_more is True
        assert result.total_lines == 100

        # 读取后续内容
        result = service.read_file("multiline.txt", start_line=11, limit=10)
        assert "line 11" in result.content

    def test_search_files(self, temp_dir):
        """测试搜索文件"""
        from app.services.file_service import FileService

        service = FileService(str(temp_dir))
        # 使用 **/*.py 搜索所有子目录中的 py 文件
        result = service.search_files("**/*.py", ".", 10)

        assert result.pattern == "**/*.py"
        assert result.total >= 2  # test.py 和 subdir/nested.py
        # 应该有 .py 文件
        assert any(".py" in m["name"] for m in result.matches)

    def test_search_with_limit(self, temp_dir):
        """测试搜索结果限制"""
        from app.services.file_service import FileService

        service = FileService(str(temp_dir))
        result = service.search_files("*", ".", limit=2)

        # 验证结果数量不超过限制
        assert len(result.matches) <= 2
        # 当达到限制时，truncated 应该为 True
        # 注意：实现可能在达到限制数时返回 truncated=True

    def test_get_file_info(self, temp_dir):
        """测试获取文件信息"""
        from app.services.file_service import FileService

        service = FileService(str(temp_dir))
        result = service.get_file_info("test.py")

        assert result.name == "test.py"
        assert result.type == "file"
        assert result.extension == ".py"
        assert result.size > 0
        assert result.mime_type == "text/x-python"

    def test_get_directory_info(self, temp_dir):
        """测试获取目录信息"""
        from app.services.file_service import FileService

        service = FileService(str(temp_dir))
        result = service.get_file_info("subdir")

        assert result.name == "subdir"
        assert result.type == "directory"


class TestUtilityFunctions:
    """工具函数测试"""

    def test_format_file_size(self):
        """测试文件大小格式化"""
        from app.services.file_service import format_file_size

        assert format_file_size(0) == "0.0 B"
        assert format_file_size(512) == "512.0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_get_mime_type(self):
        """测试获取 MIME 类型"""
        from app.services.file_service import get_mime_type

        assert get_mime_type(".py") == "text/x-python"
        assert get_mime_type(".js") == "text/javascript"
        assert get_mime_type(".json") == "application/json"
        assert get_mime_type(".md") == "text/markdown"
        assert get_mime_type(".unknown") is None
        assert get_mime_type("") is None
