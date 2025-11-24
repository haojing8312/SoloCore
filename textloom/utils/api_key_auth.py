"""
API Key认证工具模块
提供第三方系统API Key认证功能
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_connection import get_db_session
from models.db_models import UserTable

logger = logging.getLogger(__name__)


class APIKeyAuth:
    """API Key认证管理器"""

    @staticmethod
    def generate_api_key() -> str:
        """生成安全的API Key"""
        # 生成32字节随机数据，转换为64字符的十六进制字符串
        return secrets.token_hex(32)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """对API Key进行哈希处理（用于存储）"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    async def create_api_user(
        username: str,
        email: str,
        full_name: str = None,
        quota_limit: Optional[int] = None,
    ) -> tuple[UserTable, str]:
        """
        创建API用户
        
        Args:
            username: 用户名
            email: 邮箱
            full_name: 全名
            quota_limit: API调用配额限制（每月）
            
        Returns:
            tuple: (用户对象, 明文API Key)
        """
        async with get_db_session() as db_session:
            # 检查用户名和邮箱是否已存在
            stmt = select(UserTable).where(
                (UserTable.username == username.lower()) |
                (UserTable.email == email.lower())
            )
            result = await db_session.execute(stmt)
            if result.scalar_one_or_none():
                raise ValueError("用户名或邮箱已存在")

            # 生成API Key
            api_key = APIKeyAuth.generate_api_key()
            
            # 创建用户
            db_user = UserTable(
                username=username.lower(),
                email=email.lower(),
                full_name=full_name or username,
                hashed_password="",  # API用户不需要密码
                is_active=True,
                user_type="api_user",
                api_key=api_key,  # 直接存储明文（考虑到查询性能）
                api_key_enabled=True,
                api_quota_limit=quota_limit,
                api_quota_used=0,
                quota_reset_at=APIKeyAuth._get_next_month_start(),
            )

            db_session.add(db_user)
            await db_session.commit()
            await db_session.refresh(db_user)

            logger.info(f"API用户创建成功: {username} ({email})")
            return db_user, api_key

    @staticmethod
    async def verify_api_key(api_key: str) -> Optional[UserTable]:
        """
        验证API Key并返回用户信息
        
        Args:
            api_key: API密钥
            
        Returns:
            UserTable或None: 验证成功返回用户对象，失败返回None
        """
        if not api_key:
            return None

        async with get_db_session() as db_session:
            # 查找API用户
            stmt = select(UserTable).where(
                UserTable.api_key == api_key,
                UserTable.api_key_enabled == True,
                UserTable.is_active == True,
                UserTable.user_type == "api_user"
            )
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"无效的API Key: {api_key[:10]}...")
                return None

            # 检查配额限制
            if user.api_quota_limit and user.api_quota_used >= user.api_quota_limit:
                logger.warning(f"API配额已耗尽: {user.username}")
                return None

            # 检查是否需要重置配额
            if user.quota_reset_at and datetime.utcnow() >= user.quota_reset_at:
                # 重置配额
                await db_session.execute(
                    update(UserTable)
                    .where(UserTable.id == user.id)
                    .values(
                        api_quota_used=0,
                        quota_reset_at=APIKeyAuth._get_next_month_start()
                    )
                )
                await db_session.commit()
                user.api_quota_used = 0

            return user

    @staticmethod
    async def increment_api_usage(user_id) -> None:
        """增加API使用次数"""
        async with get_db_session() as db_session:
            await db_session.execute(
                update(UserTable)
                .where(UserTable.id == user_id)
                .values(api_quota_used=UserTable.api_quota_used + 1)
            )
            await db_session.commit()

    @staticmethod
    async def disable_api_key(user_id) -> bool:
        """禁用API Key"""
        async with get_db_session() as db_session:
            result = await db_session.execute(
                update(UserTable)
                .where(UserTable.id == user_id, UserTable.user_type == "api_user")
                .values(api_key_enabled=False)
            )
            await db_session.commit()
            return result.rowcount > 0

    @staticmethod
    async def regenerate_api_key(user_id) -> Optional[str]:
        """重新生成API Key"""
        new_api_key = APIKeyAuth.generate_api_key()
        
        async with get_db_session() as db_session:
            result = await db_session.execute(
                update(UserTable)
                .where(UserTable.id == user_id, UserTable.user_type == "api_user")
                .values(api_key=new_api_key)
            )
            await db_session.commit()
            
            if result.rowcount > 0:
                logger.info(f"API Key已重新生成，用户ID: {user_id}")
                return new_api_key
            return None

    @staticmethod
    def _get_next_month_start() -> datetime:
        """获取下个月第一天"""
        now = datetime.utcnow()
        if now.month == 12:
            return datetime(now.year + 1, 1, 1)
        else:
            return datetime(now.year, now.month + 1, 1)


# FastAPI依赖项
async def require_api_key(
    x_api_key: Optional[str] = Header(None, description="API密钥")
) -> UserTable:
    """
    API Key认证依赖项
    
    Args:
        x_api_key: HTTP头中的API Key
        
    Returns:
        UserTable: 认证成功的用户对象
        
    Raises:
        HTTPException: 认证失败时抛出401错误
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少API Key，请在请求头中包含 X-API-Key",
            headers={"WWW-Authenticate": "API-Key"},
        )

    user = await APIKeyAuth.verify_api_key(x_api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API Key或配额已耗尽",
            headers={"WWW-Authenticate": "API-Key"},
        )

    # 增加使用计数
    await APIKeyAuth.increment_api_usage(user.id)
    
    return user


# 可选的API Key认证（用于某些不强制要求认证的接口）
async def optional_api_key(
    x_api_key: Optional[str] = Header(None, description="可选的API密钥")
) -> Optional[UserTable]:
    """
    可选的API Key认证依赖项
    
    Args:
        x_api_key: HTTP头中的API Key
        
    Returns:
        Optional[UserTable]: 认证成功的用户对象，或None
    """
    if not x_api_key:
        return None

    return await APIKeyAuth.verify_api_key(x_api_key)