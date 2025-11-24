import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入Celery相关模块
from celery_config import celery_app
from config import settings
from models.celery_db import sync_check_database_health
from models.db_connection import check_connection_pool_health, init_database
from routers import (
    auth,
    dynamic_subtitles,
    internal_analyzer,
    internal_materials,
    internal_script,
    internal_video,
    personas,
    tasks,
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(settings.log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="智能文本转视频系统 - 支持Markdown文本自动转换为视频内容",
    version=settings.app_version,
)

# CORS中间件配置 - 安全配置
# 限制域名、方法和头部为必要范围，防止CSRF和其他安全风险
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),  # 环境配置的可信域名列表
    allow_credentials=settings.cors_allow_credentials,  # 根据环境控制是否允许凭据
    allow_methods=settings.cors_allowed_methods,  # 仅允许业务必需的HTTP方法
    allow_headers=settings.cors_allowed_headers,  # 仅允许必要的请求头
    expose_headers=settings.cors_expose_headers,  # 限制暴露的响应头
    max_age=settings.cors_max_age,  # 预检请求缓存时间
)

# 包含路由器
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(personas.router, prefix="/personas", tags=["personas"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(internal_materials.router)
app.include_router(internal_analyzer.router)
app.include_router(internal_script.router)
app.include_router(internal_video.router)
app.include_router(dynamic_subtitles.router)



@app.on_event("startup")
async def startup_event() -> None:
    """应用启动时初始化连接和服务"""
    logger.info("应用启动中...")

    # 测试数据库连接（不创建表）
    await init_database()

    # 初始化Celery应用（无需启动Worker，Worker独立运行）
    logger.info("Celery配置已加载，Worker进程需要独立启动")


    logger.info("应用启动完成")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """应用关闭时清理资源"""
    logger.info("应用关闭中...")

    # 关闭数据库连接
    try:
        from models.db_connection import close_database

        await close_database()
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")

    logger.info("应用关闭完成")


@app.get("/")
async def root() -> Dict[str, Any]:
    """根端点"""
    # 获取Celery状态
    celery_status = {"available": False, "workers": 0}
    try:
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        celery_status = {
            "available": True,
            "workers": len(active_workers) if active_workers else 0,
            "broker": "redis",
        }
    except Exception:
        pass

    return {
        "message": "TextLoom API - Celery架构",
        "version": settings.app_version,
        "docs": "/docs",
        "celery_status": celery_status,
        "architecture": "Celery + Redis",
    }


@app.get("/health")
async def health_check():
    """健康检查端点 - 增强版本，包含数据库连接池状态"""
    # 检查Celery连接
    celery_health = {"status": "disconnected", "workers": 0}
    try:
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        celery_health = {
            "status": "connected",
            "workers": len(active_workers) if active_workers else 0,
            "broker": "redis",
        }
    except Exception as e:
        celery_health["error"] = str(e)

    # 检查异步数据库连接池健康状态
    async_db_health = {"status": "unknown"}
    try:
        pool_status = await check_connection_pool_health()
        async_db_health = {
            "status": "healthy" if pool_status.get("is_healthy") else "unhealthy",
            "pool_size": pool_status.get("pool_size", 0),
            "connections_in_use": pool_status.get("checked_out", 0),
            "available_connections": pool_status.get("checked_in", 0),
            "overflow_connections": pool_status.get("overflow", 0),
            "utilization_rate": round(
                (
                    pool_status.get("checked_out", 0)
                    / max(pool_status.get("pool_size", 1), 1)
                )
                * 100,
                1,
            ),
        }
    except Exception as e:
        async_db_health = {"status": "error", "error": str(e)}

    # 检查同步数据库连接池健康状态
    sync_db_health = {"status": "unknown"}
    try:
        sync_status = sync_check_database_health()
        sync_db_health = {
            "status": sync_status.get("status", "unhealthy"),
            "connection_test": sync_status.get("connection", "unknown"),
            "timestamp": sync_status.get("timestamp"),
        }
    except Exception as e:
        sync_db_health = {"status": "error", "error": str(e)}

    # 计算整体健康状态
    overall_status = "healthy"
    if (
        celery_health.get("status") != "connected"
        or async_db_health.get("status") != "healthy"
        or sync_db_health.get("status") != "healthy"
    ):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
        "celery": celery_health,
        "database": {"async_pool": async_db_health, "sync_pool": sync_db_health},
        "connection_pool_config": {
            "async_pool_size": settings.database_pool_size,
            "async_max_overflow": settings.database_max_overflow,
            "celery_pool_size": settings.celery_database_pool_size,
            "celery_max_overflow": settings.celery_database_max_overflow,
            "pool_recycle_seconds": settings.database_pool_recycle,
        },
        "system_config": {
            "max_file_size_mb": settings.max_file_size / 1024 / 1024,
            "celery_worker_concurrency": settings.celery_worker_concurrency,
            "max_concurrent_tasks": settings.max_concurrent_tasks,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app", host=settings.host, port=settings.port, reload=settings.debug
    )
