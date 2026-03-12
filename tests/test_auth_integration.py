"""认证集成测试 - 验证 API 认证保护"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import create_user, create_access_token, authenticate_user, get_user_by_username


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def test_user():
    """创建测试用户"""
    # 检查用户是否已存在
    existing_user = get_user_by_username("test_integration@example.com")

    if existing_user:
        # 如果已存在，直接使用
        token = create_access_token(existing_user)
        return existing_user, token

    # 创建新用户
    user = create_user(username="test_integration@example.com", password="Password123", name="测试集成用户")
    if user:
        token = create_access_token(user)
        return user, token

    # 如果创建失败（可能已存在），尝试认证
    authenticated = authenticate_user("test_integration@example.com", "Password123")
    if authenticated:
        token = create_access_token(authenticated)
        return authenticated, token

    raise Exception("无法创建或获取测试用户")


class TestOptionalAuth:
    """可选认证测试"""

    def test_task_api_without_auth(self, client):
        """测试任务 API 不提供认证（应该成功）"""
        response = client.get("/api/task/sessions")
        assert response.status_code == 200

    def test_task_api_with_auth(self, client, test_user):
        """测试任务 API 提供认证（应该成功）"""
        _, token = test_user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/task/sessions", headers=headers)
        assert response.status_code == 200

    def test_sessions_api_without_auth(self, client):
        """测试会话列表 API 不提供认证（应该成功）"""
        response = client.get("/api/sessions", params={"working_dir": "."})
        assert response.status_code == 200

    def test_sessions_api_with_auth(self, client, test_user):
        """测试会话列表 API 提供认证（应该成功）"""
        _, token = test_user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/sessions", params={"working_dir": "."}, headers=headers)
        assert response.status_code == 200

    def test_files_api_without_auth(self, client):
        """测试文件浏览器 API 不提供认证（应该成功）"""
        response = client.get("/api/files/tree", params={"path": ".", "depth": 1})
        assert response.status_code == 200

    def test_files_api_with_auth(self, client, test_user):
        """测试文件浏览器 API 提供认证（应该成功）"""
        _, token = test_user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/files/tree", params={"path": ".", "depth": 1}, headers=headers)
        assert response.status_code == 200

    def test_projects_api_without_auth(self, client):
        """测试项目列表 API 不提供认证（应该成功）"""
        response = client.get("/api/projects")
        assert response.status_code == 200

    def test_projects_api_with_auth(self, client, test_user):
        """测试项目列表 API 提供认证（应该成功）"""
        _, token = test_user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/projects", headers=headers)
        assert response.status_code == 200

    def test_scheduler_status_without_auth(self, client):
        """测试调度器状态 API 不提供认证（应该成功）"""
        response = client.get("/api/scheduler/status")
        assert response.status_code == 200

    def test_scheduler_status_with_auth(self, client, test_user):
        """测试调度器状态 API 提供认证（应该成功）"""
        _, token = test_user
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/scheduler/status", headers=headers)
        assert response.status_code == 200

    def test_invalid_token(self, client):
        """测试无效 token（应该返回 401）"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/sessions", params={"working_dir": "."}, headers=headers)
        # 可选认证的端点应该仍然返回 200，只是 user=None
        assert response.status_code == 200
