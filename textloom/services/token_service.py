"""
Token服务层
提供Token管理相关的业务逻辑操作
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.db_models import RefreshTokenTable, UserTable
from utils.jwt_auth import jwt_manager

logger = logging.getLogger(__name__)


class TokenService:
    """Token服务类"""

    def __init__(self):
        self.jwt_manager = jwt_manager

    async def create_refresh_token(
        self,
        user_id: UUID,
        jti: str,
        token: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        db_session: Session = None,
    ) -> RefreshTokenTable:
        """
        创建刷新Token记录

        Args:
            user_id: 用户ID
            jti: JWT ID
            token: 刷新Token字符串
            device_info: 设备信息
            ip_address: IP地址
            db_session: 数据库会话

        Returns:
            RefreshTokenTable: 创建的刷新Token记录
        """
        expires_at = datetime.utcnow() + timedelta(days=7)  # 7天过期
        token_hash = self.jwt_manager.get_token_hash(token)

        refresh_token_record = RefreshTokenTable(
            user_id=user_id,
            jti=jti,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
        )

        try:
            db_session.add(refresh_token_record)
            await db_session.commit()
            await db_session.refresh(refresh_token_record)

            logger.info(f"刷新Token创建成功: user_id={user_id}, jti={jti}")
            return refresh_token_record

        except IntegrityError as e:
            await db_session.rollback()
            logger.error(f"创建刷新Token失败: {e}")
            raise ValueError("刷新Token创建失败")

    async def verify_refresh_token(
        self, jti: str, user_id: UUID, db_session: Session
    ) -> bool:
        """
        验证刷新Token是否有效

        Args:
            jti: JWT ID
            user_id: 用户ID
            db_session: 数据库会话

        Returns:
            bool: Token是否有效
        """
        try:
            stmt = select(RefreshTokenTable).where(
                and_(
                    RefreshTokenTable.jti == jti,
                    RefreshTokenTable.user_id == user_id,
                    RefreshTokenTable.is_revoked == False,
                    RefreshTokenTable.expires_at > datetime.utcnow(),
                )
            )
            result = await db_session.execute(stmt)
            refresh_token = result.scalar_one_or_none()

            return refresh_token is not None

        except Exception as e:
            logger.error(f"验证刷新Token失败: {e}")
            return False

    async def get_refresh_token(
        self, jti: str, user_id: UUID, db_session: Session
    ) -> Optional[RefreshTokenTable]:
        """获取刷新Token记录"""
        stmt = select(RefreshTokenTable).where(
            and_(RefreshTokenTable.jti == jti, RefreshTokenTable.user_id == user_id)
        )
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(
        self, jti: str, user_id: UUID, db_session: Session
    ) -> bool:
        """
        撤销刷新Token

        Args:
            jti: JWT ID
            user_id: 用户ID
            db_session: 数据库会话

        Returns:
            bool: 撤销是否成功
        """
        stmt = (
            update(RefreshTokenTable)
            .where(
                and_(RefreshTokenTable.jti == jti, RefreshTokenTable.user_id == user_id)
            )
            .values(is_revoked=True)
        )

        result = await db_session.execute(stmt)
        await db_session.commit()

        success = result.rowcount > 0
        if success:
            logger.info(f"刷新Token撤销成功: user_id={user_id}, jti={jti}")

        return success

    async def revoke_all_user_tokens(self, user_id: UUID, db_session: Session) -> int:
        """
        撤销用户的所有刷新Token

        Args:
            user_id: 用户ID
            db_session: 数据库会话

        Returns:
            int: 撤销的Token数量
        """
        stmt = (
            update(RefreshTokenTable)
            .where(
                and_(
                    RefreshTokenTable.user_id == user_id,
                    RefreshTokenTable.is_revoked == False,
                )
            )
            .values(is_revoked=True)
        )

        result = await db_session.execute(stmt)
        await db_session.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"用户所有刷新Token撤销成功: user_id={user_id}, count={count}")

        return count

    async def get_user_active_sessions(
        self, user_id: UUID, db_session: Session
    ) -> List[RefreshTokenTable]:
        """
        获取用户的活跃会话列表

        Args:
            user_id: 用户ID
            db_session: 数据库会话

        Returns:
            List[RefreshTokenTable]: 活跃会话列表
        """
        stmt = (
            select(RefreshTokenTable)
            .where(
                and_(
                    RefreshTokenTable.user_id == user_id,
                    RefreshTokenTable.is_revoked == False,
                    RefreshTokenTable.expires_at > datetime.utcnow(),
                )
            )
            .order_by(RefreshTokenTable.created_at.desc())
        )

        result = await db_session.execute(stmt)
        return result.scalars().all()

    async def clean_expired_tokens(self, db_session: Session) -> int:
        """
        清理过期的刷新Token

        Args:
            db_session: 数据库会话

        Returns:
            int: 清理的Token数量
        """
        # 删除过期的Token记录（超过过期时间30天的）
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        stmt = delete(RefreshTokenTable).where(
            RefreshTokenTable.expires_at < cutoff_date
        )

        result = await db_session.execute(stmt)
        await db_session.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"清理过期刷新Token: count={count}")

        return count

    async def get_token_stats(self, db_session: Session) -> dict:
        """
        获取Token统计信息

        Args:
            db_session: 数据库会话

        Returns:
            dict: 统计信息
        """
        # 活跃Token数量
        stmt = select(RefreshTokenTable).where(
            and_(
                RefreshTokenTable.is_revoked == False,
                RefreshTokenTable.expires_at > datetime.utcnow(),
            )
        )
        result = await db_session.execute(stmt)
        active_tokens = len(result.scalars().all())

        # 已撤销Token数量
        stmt = select(RefreshTokenTable).where(RefreshTokenTable.is_revoked == True)
        result = await db_session.execute(stmt)
        revoked_tokens = len(result.scalars().all())

        # 过期Token数量
        stmt = select(RefreshTokenTable).where(
            and_(
                RefreshTokenTable.is_revoked == False,
                RefreshTokenTable.expires_at <= datetime.utcnow(),
            )
        )
        result = await db_session.execute(stmt)
        expired_tokens = len(result.scalars().all())

        return {
            "active_tokens": active_tokens,
            "revoked_tokens": revoked_tokens,
            "expired_tokens": expired_tokens,
            "total_tokens": active_tokens + revoked_tokens + expired_tokens,
        }

    async def revoke_tokens_by_device(
        self, user_id: UUID, device_info: str, db_session: Session
    ) -> int:
        """
        撤销指定设备的所有Token

        Args:
            user_id: 用户ID
            device_info: 设备信息
            db_session: 数据库会话

        Returns:
            int: 撤销的Token数量
        """
        stmt = (
            update(RefreshTokenTable)
            .where(
                and_(
                    RefreshTokenTable.user_id == user_id,
                    RefreshTokenTable.device_info == device_info,
                    RefreshTokenTable.is_revoked == False,
                )
            )
            .values(is_revoked=True)
        )

        result = await db_session.execute(stmt)
        await db_session.commit()

        count = result.rowcount
        if count > 0:
            logger.info(
                f"设备Token撤销成功: user_id={user_id}, device={device_info}, count={count}"
            )

        return count

    async def update_token_last_used(
        self, jti: str, user_id: UUID, db_session: Session
    ):
        """
        更新Token最后使用时间

        Args:
            jti: JWT ID
            user_id: 用户ID
            db_session: 数据库会话
        """
        # 这里可以添加last_used_at字段到RefreshTokenTable，暂时跳过
        pass

    async def get_user_login_history(
        self, user_id: UUID, limit: int = 50, db_session: Session = None
    ) -> List[dict]:
        """
        获取用户登录历史

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            db_session: 数据库会话

        Returns:
            List[dict]: 登录历史列表
        """
        stmt = (
            select(RefreshTokenTable)
            .where(RefreshTokenTable.user_id == user_id)
            .order_by(RefreshTokenTable.created_at.desc())
            .limit(limit)
        )

        result = await db_session.execute(stmt)
        tokens = result.scalars().all()

        return [
            {
                "created_at": token.created_at,
                "device_info": token.device_info,
                "ip_address": token.ip_address,
                "is_revoked": token.is_revoked,
                "expires_at": token.expires_at,
                "is_expired": token.expires_at <= datetime.utcnow(),
            }
            for token in tokens
        ]


# 全局Token服务实例
token_service = TokenService()
