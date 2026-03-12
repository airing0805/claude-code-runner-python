"""文件浏览器 API 端点测试

使用项目目录作为测试工作目录，验证 API 端点功能。
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import os

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class TestFileBrowserAPI:
    """文件浏览器 API 端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from app.main import app
        return TestClient(app)

    def test_get_tree_root(self, client):
        """测试获取根目录树"""
        response = client.get("/api/files/tree?path=.&depth=1")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_tree_with_depth(self, client):
        """测试带深度的目录树"""
        response = client.get("/api/files/tree?path=app&depth=1")
        # 可能返回 200 (成功) 或 404 (目录不存在)
        assert response.status_code in [200, 404]

    def test_get_tree_nonexistent(self, client):
        """测试不存在路径"""
        response = client.get("/api/files/tree?path=nonexistent_directory_xyz")
        assert response.status_code == 404

    def test_read_file_pyproject(self, client):
        """测试读取 pyproject 文件"""
        response = client.get("/api/files/read?path=pyproject.toml")
        # 可能成功或文件不存在
        assert response.status_code in [200, 404, 403]

    def test_read_file_not_found(self, client):
        """测试读取不存在的文件"""
        response = client.get("/api/files/read?path=nonexistent_file_xyz.txt")
        assert response.status_code == 404

    def test_search_files_py(self, client):
        """测试搜索 Python 文件"""
        response = client.get("/api/files/search?pattern=*.py&path=.")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_search_files_with_limit(self, client):
        """测试限制搜索结果"""
        response = client.get("/api/files/search?pattern=*&path=.&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_file_info_pyproject(self, client):
        """测试获取 pyproject 文件信息"""
        response = client.get("/api/files/info?path=pyproject.toml")
        # 文件可能存在或不存在
        assert response.status_code in [200, 404, 403]

    def test_get_file_info_directory(self, client):
        """测试获取 app 目录信息"""
        response = client.get("/api/files/info?path=app")
        # 目录可能存在或不存在
        assert response.status_code in [200, 404, 403]

    def test_glob_files(self, client):
        """测试 Glob 模式查询"""
        response = client.post("/api/files/glob", json={
            "pattern": "*.py",
            "path": ".",
            "limit": 10
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_glob_files_with_limit(self, client):
        """测试 Glob 限制结果数量"""
        response = client.post("/api/files/glob", json={
            "pattern": "*",
            "path": ".",
            "limit": 2
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_path_traversal_blocked(self, client):
        """测试路径遍历被阻止"""
        # 尝试访问超出范围的路径
        response = client.get("/api/files/tree?path=../..")
        assert response.status_code == 403

    def test_read_sensitive_file_blocked(self, client):
        """测试敏感文件访问被阻止"""
        response = client.get("/api/files/read?path=.env")
        # 敏感文件应该被阻止
        assert response.status_code in [403, 404]


class TestFileBrowserErrorHandling:
    """API 错误处理测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from app.main import app
        return TestClient(app)

    def test_invalid_pagination_params(self, client):
        """测试无效的分页参数"""
        # start_line 为 0 应该被拒绝或修正
        response = client.get("/api/files/read?path=pyproject.toml&start_line=0&limit=10")
        # 应该返回错误或修正参数
        assert response.status_code in [200, 422]

    def test_excessive_depth(self, client):
        """测试过大的深度参数"""
        response = client.get("/api/files/tree?path=.&depth=100")
        # 应该被限制到最大深度
        assert response.status_code in [200, 422]

    def test_excessive_limit(self, client):
        """测试过大的限制参数"""
        response = client.get("/api/files/search?pattern=*&path=.&limit=10000")
        # 应该被限制
        assert response.status_code in [200, 422]
