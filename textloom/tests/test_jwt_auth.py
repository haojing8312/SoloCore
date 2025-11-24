"""
JWT认证功能测试
"""

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from models.auth_models import UserCreate
from services.token_service import token_service
from services.user_service import user_service
from utils.jwt_auth import get_password_hash, jwt_manager, verify_password


class TestJWTAuth:
    """JWT认证测试类"""

    def setup_method(self):
        """测试前设置"""
        # 设置测试用的JWT密钥
        jwt_manager.secret_key = "test_secret_key_for_jwt_testing_only"
        jwt_manager.algorithm = "HS256"
        jwt_manager.access_token_expire_minutes = 1440  # 24小时，避免测试中过期

    def test_password_hashing(self):
        """测试密码哈希"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_create_access_token(self):
        """测试访问Token创建"""
        user_id = uuid4()
        username = "testuser"
        email = "test@example.com"

        token = jwt_manager.create_access_token(
            user_id=user_id, username=username, email=email, is_superuser=False
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # 验证Token
        token_data = jwt_manager.verify_token(token, "access")
        assert token_data.user_id == user_id
        assert token_data.username == username
        assert token_data.email == email
        assert token_data.is_superuser is False
        assert token_data.token_type == "access"

    def test_create_refresh_token(self):
        """测试刷新Token创建"""
        user_id = uuid4()
        username = "testuser"
        email = "test@example.com"

        token, jti = jwt_manager.create_refresh_token(
            user_id=user_id, username=username, email=email
        )

        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert len(token) > 0
        assert len(jti) > 0

        # 验证Token
        token_data = jwt_manager.verify_token(token, "refresh")
        assert token_data.user_id == user_id
        assert token_data.username == username
        assert token_data.email == email
        assert token_data.token_type == "refresh"
        assert token_data.jti == jti

    def test_create_token_pair(self):
        """测试Token对创建"""
        user_id = uuid4()
        username = "testuser"
        email = "test@example.com"

        tokens = jwt_manager.create_token_pair(
            user_id=user_id, username=username, email=email, is_superuser=True
        )

        assert hasattr(tokens, "access_token")
        assert hasattr(tokens, "refresh_token")
        assert hasattr(tokens, "token_type")
        assert hasattr(tokens, "expires_in")

        # 验证访问Token
        access_data = jwt_manager.verify_token(tokens.access_token, "access")
        assert access_data.user_id == user_id
        assert access_data.is_superuser is True

        # 验证刷新Token
        refresh_data = jwt_manager.verify_token(tokens.refresh_token, "refresh")
        assert refresh_data.user_id == user_id

    def test_token_expiration(self):
        """测试Token过期"""
        user_id = uuid4()
        username = "testuser"
        email = "test@example.com"

        # 创建一个立即过期的Token
        expired_token = jwt_manager.create_access_token(
            user_id=user_id,
            username=username,
            email=email,
            expires_delta=timedelta(seconds=-1),  # 已过期
        )

        # 验证过期Token应该抛出异常
        with pytest.raises(Exception):  # 应该是HTTPException，但这里简化测试
            jwt_manager.verify_token(expired_token, "access")

    def test_invalid_token_type(self):
        """测试错误的Token类型"""
        user_id = uuid4()
        username = "testuser"
        email = "test@example.com"

        access_token = jwt_manager.create_access_token(
            user_id=user_id, username=username, email=email
        )

        # 尝试用访问Token验证刷新Token应该失败
        with pytest.raises(Exception):  # 应该是HTTPException
            jwt_manager.verify_token(access_token, "refresh")

    def test_token_hash(self):
        """测试Token哈希"""
        token = "test_token_string"
        hash1 = jwt_manager.get_token_hash(token)
        hash2 = jwt_manager.get_token_hash(token)

        # 相同输入应该产生相同哈希
        assert hash1 == hash2

        # 不同输入应该产生不同哈希
        different_hash = jwt_manager.get_token_hash("different_token")
        assert hash1 != different_hash

    def test_extract_jti(self):
        """测试JTI提取"""
        user_id = uuid4()
        username = "testuser"
        email = "test@example.com"

        token, expected_jti = jwt_manager.create_refresh_token(
            user_id=user_id, username=username, email=email
        )

        extracted_jti = jwt_manager.extract_jti_from_token(token)
        assert extracted_jti == expected_jti

        # 测试无效Token
        invalid_jti = jwt_manager.extract_jti_from_token("invalid_token")
        assert invalid_jti is None

    def test_is_token_expired(self):
        """测试Token过期检查"""
        user_id = uuid4()
        username = "testuser"
        email = "test@example.com"

        # 创建有效Token
        valid_token = jwt_manager.create_access_token(
            user_id=user_id, username=username, email=email
        )
        assert jwt_manager.is_token_expired(valid_token) is False

        # 创建过期Token
        expired_token = jwt_manager.create_access_token(
            user_id=user_id,
            username=username,
            email=email,
            expires_delta=timedelta(seconds=-10),  # 使用更明显的过期时间
        )
        assert jwt_manager.is_token_expired(expired_token) is True

        # 测试无效Token
        assert jwt_manager.is_token_expired("invalid_token") is True


class TestUserCreate:
    """用户创建模型测试"""

    def test_valid_user_create(self):
        """测试有效的用户创建数据"""
        user_data = UserCreate(
            username="testuser123",
            email="test@example.com",
            full_name="Test User",
            password="TestPassword123!",
            confirm_password="TestPassword123!",
        )

        assert user_data.username == "testuser123"
        assert user_data.email == "test@example.com"
        assert user_data.full_name == "Test User"

    def test_password_mismatch(self):
        """测试密码不匹配"""
        with pytest.raises(ValueError):
            UserCreate(
                username="testuser123",
                email="test@example.com",
                password="TestPassword123!",
                confirm_password="DifferentPassword123!",
            )

    def test_weak_password(self):
        """测试弱密码"""
        with pytest.raises(ValueError):
            UserCreate(
                username="testuser123",
                email="test@example.com",
                password="weak",
                confirm_password="weak",
            )

    def test_invalid_username(self):
        """测试无效用户名"""
        with pytest.raises(ValueError):
            UserCreate(
                username="test@user",  # 包含无效字符
                email="test@example.com",
                password="TestPassword123!",
                confirm_password="TestPassword123!",
            )


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v"])
