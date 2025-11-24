import asyncio
import logging
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from urllib.parse import unquote

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from config import settings
from models.db_models import Base

logger = logging.getLogger(__name__)

# 全局引擎实例和锁
_engine: Optional[object] = None
_session_factory: Optional[async_sessionmaker] = None
_lock = asyncio.Lock()
_connection_test_query = "SELECT 1 as health_check"


async def get_engine():
    """获取或创建异步数据库引擎"""
    global _engine
    async with _lock:
        if _engine is None:
            logger.info("创建新的数据库引擎...")
            _engine = create_async_engine(
                settings.database_url,
                # 使用统一的连接池配置，从settings获取
                pool_size=settings.database_pool_size,  # 使用配置文件中的连接池大小
                max_overflow=settings.database_max_overflow,  # 使用配置文件中的溢出连接数
                pool_timeout=settings.database_pool_timeout,
                pool_recycle=settings.database_pool_recycle,  # 使用配置文件中的回收时间
                pool_pre_ping=settings.database_pool_pre_ping,  # 使用配置文件中的ping设置
                pool_reset_on_return="rollback",  # 回滚重置，清理预处理语句
                echo=settings.debug,  # 在调试模式下打印SQL语句
                # 彻底禁用预处理语句支持，完全兼容Supabase supavisor事务代理
                connect_args={
                    # 完全禁用asyncpg预处理语句，兼容Supabase supavisor
                    "statement_cache_size": 0,
                    "server_settings": {
                        "search_path": "textloom_core, public",
                        "statement_timeout": "60s",
                    },
                    "command_timeout": 60,
                },
                # SQLAlchemy层面完全禁用语句编译和缓存
                execution_options={
                    "compiled_cache": None,  # 彻底禁用编译缓存
                    "isolation_level": "READ_COMMITTED",
                },
            )
            logger.info(
                f"数据库引擎创建成功 - 连接池大小: {settings.database_pool_size}, 最大溢出: {settings.database_max_overflow}"
            )
        return _engine


# 初始化引擎（保持向下兼容）
engine = None


async def init_engine():
    """初始化引擎"""
    global engine
    engine = await get_engine()


# 会话工厂（延迟创建）
AsyncSessionLocal = None


async def get_session_factory():
    """获取会话工厂"""
    global _session_factory
    if _session_factory is None:
        # 避免嵌套锁，因为get_engine()已经有锁了
        engine = await get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,  # 自动刷新
            autocommit=False,  # 使用手动提交，但在数据库操作后立即提交
        )
        logger.info("数据库会话工厂创建成功")
    return _session_factory


async def test_database_connection():
    """测试数据库连接可用性"""
    try:
        # 解析数据库URL
        pattern = r"postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/([^?]+)"
        match = re.match(pattern, settings.database_url)
        if not match:
            raise ValueError(f"无法解析数据库URL: {settings.database_url}")

        # 创建直接连接测试（密码需要 URL 解码）
        conn = await asyncpg.connect(
            user=match.group(1),
            password=unquote(match.group(2)),  # URL 解码密码
            host=match.group(3),
            port=int(match.group(4)),
            database=match.group(5),
            # 兼容Supabase supavisor的asyncpg参数
            statement_cache_size=0,
            command_timeout=30,
            server_settings={"search_path": "textloom_core, public"},
        )

        # 简单查询测试
        result = await conn.fetchval(_connection_test_query)
        await conn.close()

        if result == 1:
            return True
        else:
            raise Exception("连接测试查询失败")

    except Exception as e:
        logger.error(f"数据库连接测试失败: {str(e)}")
        raise


async def init_database():
    """初始化数据库连接"""
    try:
        logger.info("初始化数据库连接...")

        # 先测试基础连接
        await test_database_connection()
        logger.info("✅ 数据库连接测试通过")

        # 初始化引擎和会话工厂
        await get_engine()
        logger.info("✅ 数据库引擎初始化成功")

        await get_session_factory()
        logger.info("✅ 数据库会话工厂初始化成功")

        logger.info("✅ 数据库连接池初始化完成")

    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {str(e)}")
        raise


async def close_database():
    """优雅关闭数据库连接"""
    global _engine, _session_factory
    try:
        logger.info("关闭数据库连接...")

        # 清理会话工厂
        _session_factory = None

        # 关闭引擎连接池
        if _engine:
            await _engine.dispose()
            _engine = None

        logger.info("数据库连接已优雅关闭")

    except Exception as e:
        logger.error(f"关闭数据库连接失败: {str(e)}")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的上下文管理器 - 每个操作后立即提交"""
    session_factory = await get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            # 自动提交任何更改
            await session.commit()
        except Exception as e:
            # 出错时回滚
            await session.rollback()
            logger.error(f"数据库会话错误: {str(e)}")
            raise


@asynccontextmanager
async def get_db_session_no_commit() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的上下文管理器 - 不自动提交（用于只读操作）"""
    session_factory = await get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话错误: {str(e)}")
            raise
        finally:
            # 会话会自动关闭
            pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依赖项：获取数据库会话"""
    async with get_db_session() as session:
        yield session


async def check_connection_pool_health() -> dict:
    """检查连接池健康状态"""
    try:
        engine = await get_engine()
        pool = engine.pool

        # 获取连接池状态
        pool_status = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "is_healthy": True,
        }

        # 执行健康检查查询
        async with get_db_session_no_commit() as session:
            result = await session.execute(text(_connection_test_query))
            health_check = result.scalar()
            pool_status["query_test"] = health_check == 1

        return pool_status

    except Exception as e:
        logger.error(f"连接池健康检查失败: {str(e)}")
        return {
            "is_healthy": False,
            "error": str(e),
            "pool_size": 0,
            "checked_in": 0,
            "checked_out": 0,
            "overflow": 0,
            "query_test": False,
        }
