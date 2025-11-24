"""
用户服务层
提供用户相关的业务逻辑操作
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.auth_models import UserCreate, UserResponse, UserUpdate
from models.db_models import RefreshTokenTable, TaskTable, UserTable
from utils.jwt_auth import get_password_hash, jwt_manager, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """用户服务类"""

    def __init__(self):
        self.jwt_manager = jwt_manager

    async def create_user(
        self, user_data: UserCreate, db_session: Session
    ) -> UserTable:
        """
        创建新用户

        Args:
            user_data: 用户创建数据
            db_session: 数据库会话

        Returns:
            UserTable: 创建的用户对象

        Raises:
            ValueError: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        stmt = select(UserTable).where(UserTable.username == user_data.username.lower())
        result = await db_session.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("用户名已存在")

        # 检查邮箱是否已存在
        stmt = select(UserTable).where(UserTable.email == user_data.email.lower())
        result = await db_session.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("邮箱已存在")

        # 创建新用户
        hashed_password = get_password_hash(user_data.password)
        db_user = UserTable(
            username=user_data.username.lower(),
            email=user_data.email.lower(),
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_active=user_data.is_active,
            timezone=user_data.timezone,
            language=user_data.language,
            preferences={},
        )

        try:
            db_session.add(db_user)
            await db_session.commit()
            await db_session.refresh(db_user)

            logger.info(f"新用户创建成功: {db_user.username} ({db_user.email})")
            return db_user

        except IntegrityError as e:
            await db_session.rollback()
            logger.error(f"创建用户失败: {e}")
            raise ValueError("用户创建失败，可能存在重复数据")

    async def get_user_by_id(
        self, user_id: UUID, db_session: Session
    ) -> Optional[UserTable]:
        """根据ID获取用户"""
        stmt = select(UserTable).where(UserTable.id == user_id)
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_username(
        self, username: str, db_session: Session
    ) -> Optional[UserTable]:
        """根据用户名获取用户"""
        stmt = select(UserTable).where(UserTable.username == username.lower())
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(
        self, email: str, db_session: Session
    ) -> Optional[UserTable]:
        """根据邮箱获取用户"""
        stmt = select(UserTable).where(UserTable.email == email.lower())
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_username_or_email(
        self, username_or_email: str, db_session: Session
    ) -> Optional[UserTable]:
        """根据用户名或邮箱获取用户"""
        # 先尝试按用户名查找
        user = await self.get_user_by_username(username_or_email, db_session)
        if not user:
            # 再尝试按邮箱查找
            user = await self.get_user_by_email(username_or_email, db_session)
        return user

    async def authenticate_user(
        self, username_or_email: str, password: str, db_session: Session
    ) -> Optional[UserTable]:
        """
        认证用户

        Args:
            username_or_email: 用户名或邮箱
            password: 密码
            db_session: 数据库会话

        Returns:
            UserTable: 认证成功的用户对象，失败返回None
        """
        user = await self.get_user_by_username_or_email(username_or_email, db_session)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    async def update_user(
        self, user_id: UUID, user_update: UserUpdate, db_session: Session
    ) -> Optional[UserTable]:
        """
        更新用户信息

        Args:
            user_id: 用户ID
            user_update: 更新数据
            db_session: 数据库会话

        Returns:
            UserTable: 更新后的用户对象
        """
        # 构建更新数据
        update_data = {}
        for field, value in user_update.dict(exclude_unset=True).items():
            if field == "email" and value:
                # 检查邮箱是否已被其他用户使用
                stmt = select(UserTable).where(
                    UserTable.email == value.lower(), UserTable.id != user_id
                )
                result = await db_session.execute(stmt)
                if result.scalar_one_or_none():
                    raise ValueError("邮箱已被其他用户使用")
                update_data["email"] = value.lower()
            elif value is not None:
                update_data[field] = value

        if update_data:
            update_data["updated_at"] = datetime.utcnow()

            stmt = (
                update(UserTable).where(UserTable.id == user_id).values(**update_data)
            )
            result = await db_session.execute(stmt)

            if result.rowcount == 0:
                return None

            await db_session.commit()

        # 获取更新后的用户信息
        return await self.get_user_by_id(user_id, db_session)

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        db_session: Session,
    ) -> bool:
        """
        修改用户密码

        Args:
            user_id: 用户ID
            current_password: 当前密码
            new_password: 新密码
            db_session: 数据库会话

        Returns:
            bool: 修改成功返回True
        """
        # 获取用户当前密码哈希
        stmt = select(UserTable.hashed_password).where(UserTable.id == user_id)
        result = await db_session.execute(stmt)
        current_hashed_password = result.scalar_one_or_none()

        if not current_hashed_password:
            return False

        # 验证当前密码
        if not verify_password(current_password, current_hashed_password):
            return False

        # 更新密码和token版本（使现有token失效）
        new_hashed_password = get_password_hash(new_password)

        stmt = (
            update(UserTable)
            .where(UserTable.id == user_id)
            .values(
                hashed_password=new_hashed_password,
                token_version=UserTable.token_version + 1,
                updated_at=datetime.utcnow(),
            )
        )

        await db_session.execute(stmt)

        # 撤销所有刷新Token
        stmt = (
            update(RefreshTokenTable)
            .where(
                RefreshTokenTable.user_id == user_id,
                RefreshTokenTable.is_revoked == False,
            )
            .values(is_revoked=True)
        )

        await db_session.execute(stmt)
        await db_session.commit()

        return True

    async def deactivate_user(self, user_id: UUID, db_session: Session) -> bool:
        """停用用户"""
        stmt = (
            update(UserTable)
            .where(UserTable.id == user_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )

        result = await db_session.execute(stmt)
        await db_session.commit()

        return result.rowcount > 0

    async def activate_user(self, user_id: UUID, db_session: Session) -> bool:
        """激活用户"""
        stmt = (
            update(UserTable)
            .where(UserTable.id == user_id)
            .values(is_active=True, updated_at=datetime.utcnow())
        )

        result = await db_session.execute(stmt)
        await db_session.commit()

        return result.rowcount > 0

    async def update_last_login(self, user_id: UUID, db_session: Session):
        """更新最后登录时间"""
        stmt = (
            update(UserTable)
            .where(UserTable.id == user_id)
            .values(last_login_at=datetime.utcnow())
        )

        await db_session.execute(stmt)
        await db_session.commit()

    async def get_user_list(
        self, skip: int = 0, limit: int = 100, db_session: Session = None
    ) -> List[UserTable]:
        """获取用户列表（管理员功能）"""
        stmt = (
            select(UserTable)
            .offset(skip)
            .limit(limit)
            .order_by(UserTable.created_at.desc())
        )
        result = await db_session.execute(stmt)
        return result.scalars().all()

    async def get_user_count(self, db_session: Session) -> int:
        """获取用户总数"""
        stmt = select(func.count(UserTable.id))
        result = await db_session.execute(stmt)
        return result.scalar()

    async def get_user_stats(self, user_id: UUID, db_session: Session) -> dict:
        """获取用户统计信息"""
        # 统计任务信息
        stmt = select(TaskTable).where(TaskTable.creator_id == user_id)
        result = await db_session.execute(stmt)
        tasks = result.scalars().all()

        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "completed"])
        failed_tasks = len([t for t in tasks if t.status == "failed"])

        # 统计生成的视频数量
        total_videos = 0
        for task in tasks:
            if task.is_multi_video_task:
                total_videos += task.sub_videos_completed
            elif task.video_url:
                total_videos += 1

        # TODO: 统计存储使用量
        total_storage_used = 0

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "total_videos_generated": total_videos,
            "total_storage_used": total_storage_used,
        }


# 全局用户服务实例
user_service = UserService()
