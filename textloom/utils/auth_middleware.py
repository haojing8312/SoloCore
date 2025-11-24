"""
JWT认证中间件
提供认证依赖项和权限检查
"""

import logging
from typing import Optional, Union
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.auth_models import UserResponse
from models.db_connection import get_db_session
from models.db_models import RefreshTokenTable, UserTable
from utils.auth import verify_internal_token
from utils.jwt_auth import TokenData, jwt_manager

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_from_db(
    user_id: UUID, db_session: Session
) -> Optional[UserTable]:
    """从数据库获取用户信息"""
    try:
        stmt = select(UserTable).where(UserTable.id == user_id)
        result = await db_session.execute(stmt)
        user = result.scalar_one_or_none()
        return user
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return None


async def verify_refresh_token_in_db(
    jti: str, user_id: UUID, db_session: Session
) -> bool:
    """验证刷新Token是否在数据库中且未被撤销"""
    try:
        stmt = select(RefreshTokenTable).where(
            RefreshTokenTable.jti == jti,
            RefreshTokenTable.user_id == user_id,
            RefreshTokenTable.is_revoked == False,
        )
        result = await db_session.execute(stmt)
        refresh_token = result.scalar_one_or_none()
        return refresh_token is not None
    except Exception as e:
        logger.error(f"验证刷新Token失败: {e}")
        return False


class AuthenticationManager:
    """认证管理器，处理JWT和内部测试Token"""

    def __init__(self):
        self.jwt_manager = jwt_manager

    async def get_current_user_optional(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> Optional[UserResponse]:
        """
        获取当前用户（可选）
        支持JWT Token和内部测试Token
        """
        # 首先检查内部测试Token（优先级更高）
        internal_token = request.headers.get("x-test-token")
        if internal_token and verify_internal_token(internal_token):
            # 内部测试Token验证通过，返回虚拟超级用户
            from datetime import datetime
            from uuid import uuid4

            return UserResponse(
                id=uuid4(),
                username="internal_test_user",
                email="test@internal.com",
                full_name="内部测试用户",
                is_active=True,
                is_superuser=True,
                is_verified=True,
                avatar_url=None,
                preferences={},
                timezone="UTC",
                language="zh-CN",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_login_at=None,
            )

        # 检查JWT Token
        if not credentials or not credentials.credentials:
            return None

        try:
            # 验证JWT Token
            token_data = self.jwt_manager.verify_token(
                credentials.credentials, "access"
            )

            # 从数据库获取用户信息
            async with get_db_session() as db_session:
                user = await get_current_user_from_db(token_data.user_id, db_session)
                if not user:
                    return None

                # 检查用户状态
                if not user.is_active:
                    return None

                # 检查token版本（防止旧token使用）
                if user.token_version != token_data.token_version:
                    return None

                return UserResponse.from_orm(user)

        except HTTPException:
            return None
        except Exception as e:
            logger.warning(f"Token验证异常: {e}")
            return None

    async def get_current_user(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> UserResponse:
        """
        获取当前用户（必需）
        如果认证失败则抛出异常
        """
        user = await self.get_current_user_optional(request, credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未认证或认证已过期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    async def get_current_active_user(
        self,
        current_user: UserResponse = Depends(
            lambda request, credentials: AuthenticationManager().get_current_user(
                request, credentials
            )
        ),
    ) -> UserResponse:
        """获取当前活跃用户"""
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="用户账户已被禁用"
            )
        return current_user

    async def get_current_superuser(
        self,
        current_user: UserResponse = Depends(
            lambda request, credentials: AuthenticationManager().get_current_user(
                request, credentials
            )
        ),
    ) -> UserResponse:
        """获取当前超级用户"""
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足，需要超级用户权限",
            )
        return current_user

    async def verify_refresh_token(self, refresh_token: str) -> TokenData:
        """
        验证刷新Token
        """
        try:
            # 验证JWT格式和签名
            token_data = self.jwt_manager.verify_token(refresh_token, "refresh")

            # 从数据库验证Token是否有效
            async with get_db_session() as db_session:
                if not token_data.jti:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="无效的刷新Token",
                    )

                is_valid = await verify_refresh_token_in_db(
                    token_data.jti, token_data.user_id, db_session
                )

                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="刷新Token已被撤销或不存在",
                    )

                # 验证用户状态
                user = await get_current_user_from_db(token_data.user_id, db_session)
                if not user or not user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="用户不存在或已被禁用",
                    )

                # 检查token版本
                if user.token_version != token_data.token_version:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token版本已过期，请重新登录",
                    )

                return token_data

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"验证刷新Token失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新Token验证失败"
            )


# 全局认证管理器实例
auth_manager = AuthenticationManager()


# 认证依赖项（向外暴露的接口）
async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[UserResponse]:
    """获取当前用户（可选，兼容内部测试Token）"""
    return await auth_manager.get_current_user_optional(request, credentials)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserResponse:
    """获取当前用户（必需，兼容内部测试Token）"""
    return await auth_manager.get_current_user(request, credentials)


async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用户账户已被禁用"
        )
    return current_user


async def get_current_superuser(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """获取当前超级用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="权限不足，需要超级用户权限"
        )
    return current_user


async def verify_refresh_token(refresh_token: str) -> TokenData:
    """验证刷新Token"""
    return await auth_manager.verify_refresh_token(refresh_token)


# 兼容性函数：与现有内部测试Token系统集成
def check_internal_or_jwt_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> bool:
    """
    检查内部测试Token或JWT认证
    主要用于内部API端点的快速认证检查
    """
    # 检查内部测试Token
    internal_token = request.headers.get("x-test-token")
    if internal_token and verify_internal_token(internal_token):
        return True

    # 检查JWT Token
    if credentials and credentials.credentials:
        try:
            jwt_manager.verify_token(credentials.credentials, "access")
            return True
        except Exception:
            pass

    return False
