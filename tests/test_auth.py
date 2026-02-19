"""认证系统测试"""

import pytest
from fastapi.testclient import TestClient


class TestPasswordValidation:
    """密码验证测试"""

    def test_password_too_short(self):
        """测试密码太短"""
        from app.auth.core import validate_password_strength

        is_valid, error = validate_password_strength("1234567")
        assert is_valid is False
        assert "8 位" in error

    def test_password_no_letter(self):
        """测试密码没有字母"""
        from app.auth.core import validate_password_strength

        is_valid, error = validate_password_strength("12345678")
        assert is_valid is False
        assert "字母" in error

    def test_password_no_number(self):
        """测试密码没有数字"""
        from app.auth.core import validate_password_strength

        is_valid, error = validate_password_strength("abcdefgh")
        assert is_valid is False
        assert "数字" in error

    def test_valid_password(self):
        """测试有效密码"""
        from app.auth.core import validate_password_strength

        is_valid, error = validate_password_strength("Password123")
        assert is_valid is True
        assert error == ""


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        from app.auth.core import hash_password, verify_password

        password = "Password123"
        hashed = hash_password(password)

        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """测试验证错误密码"""
        from app.auth.core import hash_password, verify_password

        password = "Password123"
        hashed = hash_password(password)

        assert verify_password("WrongPassword", hashed) is False


class TestJWTToken:
    """JWT Token 测试"""

    def test_create_and_decode_token(self):
        """测试创建和解码 Token"""
        from app.auth.core import create_access_token, decode_access_token
        from app.models.user import User

        user = User(id="test-id", username="test@example.com")
        token = create_access_token(user)

        assert token is not None
        assert len(token) > 0

        token_data = decode_access_token(token)
        assert token_data is not None
        assert token_data.user_id == "test-id"
        assert token_data.username == "test@example.com"

    def test_decode_invalid_token(self):
        """测试解码无效 Token"""
        from app.auth.core import decode_access_token

        token_data = decode_access_token("invalid-token")
        assert token_data is None


class TestUserManagement:
    """用户管理测试"""

    @pytest.fixture(autouse=True)
    def clear_users(self):
        """清空用户数据库"""
        import app.auth.core as auth_core

        auth_core._users_db.clear()
        yield
        auth_core._users_db.clear()

    def test_create_user(self):
        """测试创建用户"""
        from app.auth.core import create_user, get_user_by_username

        user = create_user(
            username="test@example.com",
            password="Password123",
            name="Test User",
        )

        assert user is not None
        assert user.username == "test@example.com"
        assert user.name == "Test User"

        # 验证用户已存储
        stored_user = get_user_by_username("test@example.com")
        assert stored_user is not None
        assert stored_user.id == user.id

    def test_create_duplicate_user(self):
        """测试创建重复用户"""
        from app.auth.core import create_user

        create_user(
            username="test@example.com",
            password="Password123",
            name="Test User",
        )

        # 尝试创建同名用户
        user = create_user(
            username="test@example.com",
            password="Password456",
            name="Another User",
        )

        assert user is None

    def test_authenticate_user(self):
        """测试用户认证"""
        from app.auth.core import authenticate_user, create_user

        create_user(
            username="test@example.com",
            password="Password123",
            name="Test User",
        )

        # 正确的密码
        user = authenticate_user("test@example.com", "Password123")
        assert user is not None
        assert user.username == "test@example.com"

        # 错误的密码
        user = authenticate_user("test@example.com", "WrongPassword")
        assert user is None

    def test_authenticate_nonexistent_user(self):
        """测试认证不存在的用户"""
        from app.auth.core import authenticate_user

        user = authenticate_user("nonexistent@example.com", "Password123")
        assert user is None


class TestAPIKey:
    """API Key 测试"""

    def test_generate_api_key(self):
        """测试生成 API Key"""
        from app.auth.core import generate_api_key
        from app.models.user import User

        user = User(id="test-id", username="test@example.com")
        api_key = generate_api_key(user)

        # 现在使用 sk-ccr- 前缀
        assert api_key.startswith("sk-ccr-")
        assert len(api_key) > 10

    def test_verify_valid_api_key(self):
        """测试验证有效的 API Key"""
        from app.auth.core import create_user, create_api_key, verify_api_key

        user = create_user(
            username="test@example.com",
            password="Password123",
            name="Test User",
        )

        # 使用 create_api_key 来创建并存储密钥
        api_key_obj, api_key = create_api_key(
            user_id=user.id,
            name="Test Key",
            permissions="read_write",
        )
        verified_user = verify_api_key(api_key)

        assert verified_user is not None
        assert verified_user.id == user.id

    def test_verify_invalid_api_key(self):
        """测试验证无效的 API Key"""
        from app.auth.core import verify_api_key

        # 无效格式
        assert verify_api_key("invalid-key") is None

        # 空的
        assert verify_api_key("") is None


class TestAuthAPI:
    """认证 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from app.main import app

        # 清空用户数据库
        import app.auth.core as auth_core

        auth_core._users_db.clear()

        return TestClient(app)

    @pytest.fixture(autouse=True)
    def clear_users_after(self):
        """测试后清空用户"""
        yield
        import app.auth.core as auth_core

        auth_core._users_db.clear()

    def test_register(self, client):
        """测试注册接口"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "test@example.com",
                "password": "Password123",
                "name": "Test User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["username"] == "test@example.com"
        assert data["name"] == "Test User"

    def test_register_duplicate_username(self, client):
        """测试注册重复用户名"""
        # 先注册
        client.post(
            "/api/auth/register",
            json={
                "username": "test@example.com",
                "password": "Password123",
                "name": "Test User",
            },
        )

        # 尝试重复注册
        response = client.post(
            "/api/auth/register",
            json={
                "username": "test@example.com",
                "password": "Password456",
                "name": "Another User",
            },
        )

        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]

    def test_register_weak_password(self, client):
        """测试注册时弱密码"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "test@example.com",
                "password": "weak",
                "name": "Test User",
            },
        )

        assert response.status_code == 422

    def test_login(self, client):
        """测试登录接口"""
        # 先注册
        client.post(
            "/api/auth/register",
            json={
                "username": "test@example.com",
                "password": "Password123",
                "name": "Test User",
            },
        )

        # 登录
        response = client.post(
            "/api/auth/login",
            json={
                "username": "test@example.com",
                "password": "Password123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_invalid_credentials(self, client):
        """测试登录无效凭据"""
        # 先注册
        client.post(
            "/api/auth/register",
            json={
                "username": "test@example.com",
                "password": "Password123",
                "name": "Test User",
            },
        )

        # 错误密码登录
        response = client.post(
            "/api/auth/login",
            json={
                "username": "test@example.com",
                "password": "WrongPassword",
            },
        )

        assert response.status_code == 401

    def test_get_me_unauthorized(self, client):
        """测试未授权获取用户信息"""
        response = client.get("/api/auth/me")

        assert response.status_code == 401

    def test_get_me(self, client):
        """测试获取当前用户"""
        # 先注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "test@example.com",
                "password": "Password123",
                "name": "Test User",
            },
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "test@example.com",
                "password": "Password123",
            },
        )

        token = login_response.json()["access_token"]

        # 获取用户信息
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "test@example.com"
        assert "api_key" in data

    def test_update_password(self, client):
        """测试修改密码"""
        # 先注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "test@example.com",
                "password": "Password123",
                "name": "Test User",
            },
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "test@example.com",
                "password": "Password123",
            },
        )

        token = login_response.json()["access_token"]

        # 修改密码
        response = client.put(
            "/api/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "Password123",
                "new_password": "NewPassword456",
            },
        )

        assert response.status_code == 204

        # 使用新密码登录
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "test@example.com",
                "password": "NewPassword456",
            },
        )

        assert login_response.status_code == 200

    def test_update_password_wrong_old(self, client):
        """测试修改密码时旧密码错误"""
        # 先注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "test@example.com",
                "password": "Password123",
                "name": "Test User",
            },
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "test@example.com",
                "password": "Password123",
            },
        )

        token = login_response.json()["access_token"]

        # 使用错误旧密码修改密码
        response = client.put(
            "/api/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "WrongPassword",
                "new_password": "NewPassword456",
            },
        )

        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
