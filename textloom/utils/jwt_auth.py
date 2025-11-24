"""
JWT认证工具类
提供JWT Token的生成、验证、刷新等核心功能
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token数据模型"""

    user_id: UUID
    username: str
    email: str
    is_superuser: bool = False
    token_type: str = "access"  # access 或 refresh
    jti: Optional[str] = None  # JWT ID，用于refresh token
    token_version: int = 1


class JWTTokens(BaseModel):
    """JWT Token对"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class JWTManager:
    """JWT管理器"""

    def __init__(self):
        # 允许在测试环境中使用默认密钥
        if not settings.secret_key:
            import os

            if os.getenv("PYTEST_CURRENT_TEST"):
                # 测试环境使用默认密钥
                self.secret_key = (
                    "test_secret_key_for_jwt_testing_only_do_not_use_in_production"
                )
            else:
                raise ValueError("JWT secret_key 未配置，请设置 SECRET_KEY 环境变量")
        else:
            self.secret_key = settings.secret_key

        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = 7  # 7天

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """获取密码哈希值"""
        return pwd_context.hash(password)

    def create_access_token(
        self,
        user_id: UUID,
        username: str,
        email: str,
        is_superuser: bool = False,
        token_version: int = 1,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """创建访问Token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode = {
            "sub": str(user_id),
            "username": username,
            "email": email,
            "is_superuser": is_superuser,
            "token_type": "access",
            "token_version": token_version,
            "exp": expire.timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "iss": "textloom-api",
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self,
        user_id: UUID,
        username: str,
        email: str,
        token_version: int = 1,
        jti: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        创建刷新Token
        返回: (token_string, jti)
        """
        if not jti:
            jti = str(uuid4())

        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode = {
            "sub": str(user_id),
            "username": username,
            "email": email,
            "token_type": "refresh",
            "token_version": token_version,
            "jti": jti,
            "exp": expire.timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "iss": "textloom-api",
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt, jti

    def create_token_pair(
        self,
        user_id: UUID,
        username: str,
        email: str,
        is_superuser: bool = False,
        token_version: int = 1,
    ) -> JWTTokens:
        """创建Token对（访问+刷新）"""
        access_token = self.create_access_token(
            user_id=user_id,
            username=username,
            email=email,
            is_superuser=is_superuser,
            token_version=token_version,
        )

        refresh_token, jti = self.create_refresh_token(
            user_id=user_id, username=username, email=email, token_version=token_version
        )

        return JWTTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
        )

    def verify_token(self, token: str, token_type: str = "access") -> TokenData:
        """
        验证Token

        Args:
            token: JWT token字符串
            token_type: token类型 ("access" 或 "refresh")

        Returns:
            TokenData: 解析的token数据

        Raises:
            HTTPException: token无效时抛出
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 验证token类型
            if payload.get("token_type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"无效的token类型，期望: {token_type}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # 验证必要字段
            user_id_str = payload.get("sub")
            username = payload.get("username")
            email = payload.get("email")

            if not user_id_str or not username or not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token缺少必要字段",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            try:
                user_id = UUID(user_id_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的用户ID格式",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return TokenData(
                user_id=user_id,
                username=username,
                email=email,
                is_superuser=payload.get("is_superuser", False),
                token_type=token_type,
                jti=payload.get("jti"),
                token_version=payload.get("token_version", 1),
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token已过期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def get_token_hash(self, token: str) -> str:
        """获取token的哈希值，用于安全存储"""
        return hashlib.sha256(token.encode()).hexdigest()

    def extract_jti_from_token(self, token: str) -> Optional[str]:
        """从token中提取JTI，不验证有效性"""
        try:
            # 不验证签名，只提取payload
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("jti")
        except Exception:
            return None

    def is_token_expired(self, token: str) -> bool:
        """检查token是否过期"""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            exp = payload.get("exp")
            if not exp:
                return True
            # 比较当前时间戳和过期时间戳
            current_timestamp = datetime.utcnow().timestamp()
            return current_timestamp > exp
        except Exception:
            return True


# 全局JWT管理器实例
jwt_manager = JWTManager()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return jwt_manager.verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希值"""
    return jwt_manager.get_password_hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问Token（向后兼容）"""
    user_id = data.get("sub")
    username = data.get("username", "")
    email = data.get("email", "")
    is_superuser = data.get("is_superuser", False)
    token_version = data.get("token_version", 1)

    return jwt_manager.create_access_token(
        user_id=UUID(user_id),
        username=username,
        email=email,
        is_superuser=is_superuser,
        token_version=token_version,
        expires_delta=expires_delta,
    )


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """验证Token（向后兼容）"""
    return jwt_manager.verify_token(token, token_type)
