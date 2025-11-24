#!/usr/bin/env python3
"""
数据库初始化脚本
直接使用 SQLAlchemy 创建所有表
"""
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from models.db_models import Base


async def init_database():
    """初始化数据库表结构"""
    print("开始初始化数据库...")
    print(f"数据库 URL: {settings.database_url}")

    # 创建异步引擎
    engine = create_async_engine(
        settings.database_url,
        echo=True,  # 打印 SQL 语句
    )

    try:
        # 创建所有表
        async with engine.begin() as conn:
            print("\n创建所有表...")
            await conn.run_sync(Base.metadata.create_all)

        print("\n✅ 数据库表创建成功！")

        # 列出所有创建的表
        print("\n创建的表：")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")

    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        raise

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
