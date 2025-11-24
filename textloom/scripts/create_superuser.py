#!/usr/bin/env python3
"""
创建超级用户脚本
用于初始化系统管理员账户
"""

import asyncio
import os
import sys
from getpass import getpass

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from models.auth_models import UserCreate
from models.db_connection import get_db_session
from models.db_models import UserTable
from services.user_service import user_service
from utils.enhanced_logging import (
    log_critical,
    log_debug,
    log_error,
    log_info,
    log_warning,
)
from utils.jwt_auth import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_superuser():
    """创建超级用户"""
    log_info("=== TextLoom 超级用户创建工具 ===\n")

    # 获取用户输入
    username = input("请输入用户名: ").strip()
    if not username:
        log_error("错误: 用户名不能为空")
        return

    email = input("请输入邮箱: ").strip()
    if not email:
        log_error("错误: 邮箱不能为空")
        return

    full_name = input("请输入全名 (可选): ").strip() or None

    # 获取密码
    while True:
        password = getpass("请输入密码: ")
        if len(password) < 8:
            log_error("错误: 密码至少需要8个字符")
            continue

        confirm_password = getpass("请确认密码: ")
        if password != confirm_password:
            log_error("错误: 两次输入的密码不一致")
            continue

        break

    try:
        async with get_db_session() as db_session:
            # 检查用户是否已存在
            existing_user = await user_service.get_user_by_username(
                username, db_session
            )
            if existing_user:
                log_error(f"错误: 用户名 '{username}' 已存在")
                return

            existing_user = await user_service.get_user_by_email(email, db_session)
            if existing_user:
                log_error(f"错误: 邮箱 '{email}' 已存在")
                return

            # 直接创建超级用户（绕过UserCreate验证）
            hashed_password = get_password_hash(password)

            superuser = UserTable(
                username=username.lower(),
                email=email.lower(),
                full_name=full_name,
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=True,  # 设置为超级用户
                is_verified=True,  # 默认验证
                preferences={},
            )

            db_session.add(superuser)
            await db_session.commit()
            await db_session.refresh(superuser)

            log_info(f"\n✅ 超级用户创建成功!")
            log_info(f"用户名: {superuser.username}")
            log_info(f"邮箱: {superuser.email}")
            log_info(f"全名: {superuser.full_name or '未设置'}")
            log_info(f"用户ID: {superuser.id}")

    except Exception as e:
        logger.error(f"创建超级用户失败: {e}")
        log_error(f"❌ 创建失败: {e}")


async def list_superusers():
    """列出现有的超级用户"""
    try:
        async with get_db_session() as db_session:
            from sqlalchemy import select

            stmt = select(UserTable).where(UserTable.is_superuser == True)
            result = await db_session.execute(stmt)
            superusers = result.scalars().all()

            if not superusers:
                log_info("没有找到超级用户")
                return

            log_info(f"\n现有超级用户 ({len(superusers)} 个):")
            log_info("-" * 80)
            log_info(f"{'用户名':<20} {'邮箱':<30} {'全名':<20} {'状态':<10}")
            log_info("-" * 80)

            for user in superusers:
                status = "正常" if user.is_active else "禁用"
                log_info(
                    f"{user.username:<20} {user.email:<30} {user.full_name or '':<20} {status:<10}"
                )

    except Exception as e:
        logger.error(f"获取超级用户列表失败: {e}")
        log_error(f"❌ 获取失败: {e}")


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        asyncio.run(list_superusers())
    else:
        asyncio.run(create_superuser())


if __name__ == "__main__":
    main()
