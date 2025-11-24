"""
Celery专用同步数据库连接模块
完全独立于FastAPI的异步数据库连接，避免事件循环冲突
"""

import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional
from uuid import UUID

import psycopg2
from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from sqlalchemy import case, create_engine, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import sessionmaker

from config import settings
from models.db_models import (
    MaterialAnalysisTable,
    MediaItemTable,
    PersonaTable,
    PromptTemplateTable,
    ScriptContentTable,
    TaskTable,
)
from models.material_analysis import AnalysisStatus, QualityLevel
from models.task import TaskStatus
from utils.sync_logging import log_database_operation

logger = logging.getLogger(__name__)

# 全局连接池和锁
_connection_pool: Optional[ThreadedConnectionPool] = None
_pool_lock = threading.Lock()
_indexes_ensured = False
_material_analyses_has_media_item_id: Optional[bool] = None
_sa_engine = None
_SessionLocal = None


def _get_sync_sa_session():
    """获取同步 SQLAlchemy Session（psycopg2）。"""
    global _sa_engine, _SessionLocal
    if _sa_engine is None:
        sync_url = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )
        _sa_engine = create_engine(
            sync_url,
            pool_size=settings.celery_database_pool_size,
            max_overflow=settings.celery_database_max_overflow,
            pool_pre_ping=True,
            pool_recycle=settings.database_pool_recycle,
        )
        _SessionLocal = sessionmaker(bind=_sa_engine, autoflush=False, autocommit=False)
    return _SessionLocal()


def get_sync_connection_pool() -> ThreadedConnectionPool:
    """获取或创建同步数据库连接池"""
    global _connection_pool

    with _pool_lock:
        if _connection_pool is None:
            # 解析异步URL为同步URL
            sync_url = settings.database_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            )

            logger.info("创建Celery专用同步数据库连接池...")

            # 创建连接池 - 使用配置文件中的参数
            _connection_pool = ThreadedConnectionPool(
                minconn=settings.celery_database_min_connections,  # 从配置获取最小连接数
                maxconn=settings.celery_database_pool_size,  # 从配置获取最大连接数
                dsn=sync_url,
                # 禁用预处理语句，兼容pgbouncer（移除不支持的statement_cache_size参数）
                options="-c statement_timeout=60s -c search_path=textloom_core,public",
            )

            # 测试连接
            conn = _connection_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    if result[0] != 1:
                        raise Exception("连接测试失败")
                logger.info("✅ Celery数据库连接池创建成功")
                # 创建幂等性相关索引（若不存在）
                _ensure_idempotency_indexes(conn)
            finally:
                _connection_pool.putconn(conn)

        return _connection_pool


@contextmanager
def get_sync_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """获取同步数据库连接的上下文管理器"""
    pool = get_sync_connection_pool()
    conn = pool.getconn()

    try:
        # 设置自动提交为False，手动控制事务
        conn.autocommit = False
        yield conn
        # 成功时提交事务
        conn.commit()
    except Exception as e:
        # 出错时回滚
        conn.rollback()
        logger.error(f"数据库操作错误: {e}")
        raise
    finally:
        # 归还连接到池
        pool.putconn(conn)


def close_sync_connection_pool():
    """关闭同步数据库连接池"""
    global _connection_pool

    with _pool_lock:
        if _connection_pool:
            _connection_pool.closeall()
            _connection_pool = None
            logger.info("Celery数据库连接池已关闭")


def _ensure_idempotency_indexes(conn):
    """确保关键唯一索引存在（用于幂等保护）。

    - material_analyses (task_id, original_url) 唯一（避免重复分析同一文件）
    """
    global _indexes_ensured
    if _indexes_ensured:
        return
    try:
        with conn.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_material_analyses_task_original_url
                    ON textloom_core.material_analyses (task_id, original_url)
                    """
                )
            except Exception:
                pass
        conn.commit()
        _indexes_ensured = True
    except Exception as e:
        logger.warning(f"创建幂等性索引失败（忽略不阻断业务）: {e}")


def _check_column_exists(conn, schema: str, table: str, column: str) -> bool:
    """检查指定列是否存在。"""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s AND column_name = %s
            )
            """,
            (schema, table, column),
        )
        return bool(cursor.fetchone()[0])


# Celery任务专用的数据库操作函数
def sync_update_task_status(
    task_id: str,
    status: TaskStatus | str,
    update_data: Optional[Dict[str, Any]] | str | None = None,
) -> bool:
    """同步更新任务状态（ORM版）。

    - progress 只增不减
    - 已完成状态不回退，除非本次也设置为 completed
    - 兼容第三个参数为描述字符串或扩展字典
    """
    start_time = datetime.utcnow()
    try:
        log_database_operation(
            logger,
            "UPDATE",
            "tasks",
            True,
            {
                "task_id": task_id,
                "status": str(status),
                "operation": "sync_update_task_status",
            },
        )

        session = _get_sync_sa_session()
        status_value = status.value if isinstance(status, TaskStatus) else str(status)

        # 读取当前状态/进度（锁行以避免竞态）
        current_row = session.execute(
            select(TaskTable.status, TaskTable.progress)
            .where(TaskTable.id == task_id)
            .with_for_update()
        ).first()
        if not current_row:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_database_operation(
                logger,
                "UPDATE",
                "tasks",
                False,
                {
                    "task_id": task_id,
                    "error": "task_not_found",
                    "duration": f"{duration:.3f}s",
                },
            )
            logger.warning(f"任务 {task_id} 不存在或未更新")
            return False
        current_status, current_progress = current_row[0], int(current_row[1] or 0)

        logger.debug(
            f"任务 {task_id} 当前状态: {current_status}, 进度: {current_progress}%"
        )

        # 构建更新值
        set_values: Dict[str, Any] = {
            "status": status_value,
            "updated_at": datetime.utcnow(),
        }

        if isinstance(update_data, str) and update_data:
            set_values["description"] = update_data
        elif isinstance(update_data, dict) and update_data:
            set_values.update(update_data)

        # 终态保护
        if current_status == "completed" and status_value != "completed":
            logger.debug(f"任务 {task_id} 已完成，忽略非completed更新")
            return True

        # progress 只增不减
        if "progress" in set_values and set_values["progress"] is not None:
            set_values["progress"] = max(current_progress, int(set_values["progress"]))

        stmt = update(TaskTable).where(TaskTable.id == task_id).values(**set_values)
        result = session.execute(stmt)
        session.commit()

        if result.rowcount == 0:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_database_operation(
                logger,
                "UPDATE",
                "tasks",
                False,
                {
                    "task_id": task_id,
                    "error": "no_rows_affected",
                    "duration": f"{duration:.3f}s",
                },
            )
            logger.warning(f"任务 {task_id} 不存在或未更新")
            return False

        duration = (datetime.utcnow() - start_time).total_seconds()
        log_database_operation(
            logger,
            "UPDATE",
            "tasks",
            True,
            {
                "task_id": task_id,
                "status": status_value,
                "rows_affected": result.rowcount,
                "duration": f"{duration:.3f}s",
            },
        )
        logger.info(
            f"任务 {task_id} 状态更新成功: {status_value} - 耗时: {duration:.3f}s"
        )
        return True
    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        log_database_operation(
            logger,
            "UPDATE",
            "tasks",
            False,
            {"task_id": task_id, "error": str(e)[:200], "duration": f"{duration:.3f}s"},
        )
        logger.error(
            f"更新任务状态失败 - 任务ID: {task_id}, 错误: {e} - 耗时: {duration:.3f}s"
        )
        try:
            session.rollback()
        except Exception:
            pass
        return False


def sync_get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """同步获取任务信息（ORM版）"""
    start_time = datetime.utcnow()
    try:
        log_database_operation(
            logger,
            "SELECT",
            "tasks",
            True,
            {"task_id": task_id, "operation": "sync_get_task_by_id"},
        )

        session = _get_sync_sa_session()
        result = (
            session.execute(select(TaskTable).where(TaskTable.id == task_id))
            .scalars()
            .first()
        )

        duration = (datetime.utcnow() - start_time).total_seconds()

        if not result:
            log_database_operation(
                logger,
                "SELECT",
                "tasks",
                False,
                {
                    "task_id": task_id,
                    "error": "not_found",
                    "duration": f"{duration:.3f}s",
                },
            )
            logger.debug(f"任务 {task_id} 不存在 - 耗时: {duration:.3f}s")
            return None

        log_database_operation(
            logger,
            "SELECT",
            "tasks",
            True,
            {"task_id": task_id, "found": True, "duration": f"{duration:.3f}s"},
        )
        logger.debug(f"任务 {task_id} 获取成功 - 耗时: {duration:.3f}s")

        row = result
        return {
            "id": str(row.id),
            "title": row.title,
            "description": row.description,
            "creator_id": row.creator_id,
            "task_type": row.task_type,
            "status": row.status,
            "progress": row.progress,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "started_at": row.started_at,
            "completed_at": row.completed_at,
        }
    except Exception as e:
        logger.error(f"获取任务失败 - 任务ID: {task_id}, 错误: {e}")
        return None


def sync_create_task(task_data: Dict[str, Any]) -> Optional[str]:
    """同步创建任务（ORM版）"""
    try:
        session = _get_sync_sa_session()
        now = datetime.utcnow()
        new_row = TaskTable(
            title=task_data["title"],
            description=task_data.get("description"),
            creator_id=task_data.get("creator_id"),
            task_type=task_data["task_type"],
            status=task_data.get("status", TaskStatus.PENDING.value),
            progress=task_data.get("progress", 0),
            created_at=now,
            updated_at=now,
            # is_multi_video_task 和 multi_video_count 已移除 - 改为单视频架构
            celery_task_id=task_data.get("celery_task_id"),
            worker_name=task_data.get("worker_name"),
            started_at=task_data.get("started_at"),
        )
        session.add(new_row)
        session.flush()
        session.commit()
        task_id = str(new_row.id)
        logger.debug(f"任务创建成功: {task_id}")
        return task_id
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        try:
            session.rollback()
        except Exception:
            pass
        return None


def sync_update_task_with_results(task_id: str, results: Dict[str, Any]) -> bool:
    """同步更新任务结果（ORM版）。避免覆盖已有结果字段。"""
    try:
        session = _get_sync_sa_session()
        update_values: Dict[str, Any] = {
            "updated_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
        }
        if "video_url" in results:
            # 避免覆盖已有：使用 COALESCE 逻辑交由数据库
            pass
        if "multi_video_urls" in results:
            pass
        if "script_title" in results:
            pass
        if "script_description" in results:
            pass
        if "script_narration" in results:
            pass
        if "video_duration" in results:
            pass

        # 基础 SET
        stmt = update(TaskTable).where(TaskTable.id == task_id).values(**update_values)
        # 条件 COALESCE 字段
        if "video_url" in results:
            stmt = stmt.values(
                video_url=func.coalesce(TaskTable.video_url, results["video_url"])
            )
        if "multi_video_urls" in results:
            stmt = stmt.values(
                multi_video_urls=func.coalesce(
                    TaskTable.multi_video_urls, results["multi_video_urls"]
                )
            )
        if "script_title" in results:
            stmt = stmt.values(
                script_title=func.coalesce(
                    TaskTable.script_title, results["script_title"]
                )
            )
        if "script_description" in results:
            stmt = stmt.values(
                script_description=func.coalesce(
                    TaskTable.script_description, results["script_description"]
                )
            )
        if "script_narration" in results:
            stmt = stmt.values(
                script_narration=func.coalesce(
                    TaskTable.script_narration, results["script_narration"]
                )
            )
        if "video_duration" in results:
            stmt = stmt.values(
                video_duration=func.coalesce(
                    TaskTable.video_duration, results["video_duration"]
                )
            )

        result = session.execute(stmt)
        session.commit()
        return result.rowcount > 0
    except Exception as e:
        logger.error(f"更新任务结果失败 - 任务ID: {task_id}, 错误: {e}")
        try:
            session.rollback()
        except Exception:
            pass
        return False


def sync_check_database_health() -> Dict[str, Any]:
    """同步检查数据库健康状态"""
    try:
        with get_sync_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as health_check")
                result = cursor.fetchone()

                if result and result[0] == 1:
                    return {
                        "status": "healthy",
                        "connection": "ok",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "connection": "failed",
                        "timestamp": datetime.utcnow().isoformat(),
                    }

    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


def sync_get_tasks_by_status(status: TaskStatus, limit: int = 10) -> list:
    """同步获取指定状态的任务（ORM版）"""
    try:
        session = _get_sync_sa_session()
        rows = (
            session.execute(
                select(TaskTable)
                .where(TaskTable.status == status.value)
                .order_by(TaskTable.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": str(r.id),
                "title": r.title,
                "description": r.description,
                "creator_id": r.creator_id,
                "task_type": r.task_type,
                "status": r.status,
                "progress": r.progress,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"获取任务列表失败 - 状态: {status.value}, 错误: {e}")
        return []


def sync_get_all_active_tasks() -> List[Dict[str, Any]]:
    """同步获取所有活跃状态的任务（用于Redis清理检查）"""
    try:
        session = _get_sync_sa_session()
        
        # 定义活跃状态
        active_statuses = [TaskStatus.PENDING.value, TaskStatus.PROCESSING.value]
        
        rows = (
            session.execute(
                select(TaskTable)
                .where(TaskTable.status.in_(active_statuses))
                .order_by(TaskTable.updated_at.desc())
            )
            .scalars()
            .all()
        )
        
        result = []
        for r in rows:
            result.append({
                "id": str(r.id),
                "title": r.title,
                "task_type": r.task_type,
                "status": r.status,
                "progress": r.progress,
                "celery_task_id": r.celery_task_id,
                "worker_name": r.worker_name,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "started_at": r.started_at,
            })
        
        session.close()
        logger.info(f"获取活跃任务成功 - 数量: {len(result)}")
        return result
        
    except Exception as e:
        logger.error(f"获取活跃任务失败: {e}")
        return []


# ==================== 进度与结果更新（缺失方法补充） ====================


def sync_update_task_progress(
    task_id: str, progress: int, stage: str, description: Optional[str] = None
) -> bool:
    """同步更新任务进度（ORM版）。

    - progress 取最大值，避免回退
    - 写入描述
    - 根据 stage 写入状态，completed 时写 completed_at
    """
    try:
        session = _get_sync_sa_session()
        # 读取当前状态与进度并加锁
        row = session.execute(
            select(TaskTable.status, TaskTable.progress)
            .where(TaskTable.id == task_id)
            .with_for_update()
        ).first()
        if not row:
            return False
        current_status, current_progress = row[0], int(row[1] or 0)

        new_progress = max(current_progress, progress or 0)
        update_fields: Dict[str, Any] = {
            "progress": new_progress,
            "updated_at": datetime.utcnow(),
        }
        if description:
            update_fields["description"] = description

        target_status: Optional[str] = None
        if stage in ("completed", "failed"):
            target_status = stage
        if current_status == "completed" and target_status != "completed":
            target_status = None
        if target_status:
            update_fields["status"] = target_status
            if target_status == "completed":
                update_fields["completed_at"] = datetime.utcnow()

        result = session.execute(
            update(TaskTable).where(TaskTable.id == task_id).values(**update_fields)
        )
        session.commit()
        return result.rowcount > 0
    except Exception as e:
        logger.error(f"更新任务进度失败 - 任务ID: {task_id}, 错误: {e}")
        try:
            session.rollback()
        except Exception:
            pass
        return False


def sync_update_task_stage(task_id: str, stage: str) -> bool:
    """同步更新任务的当前阶段"""
    try:
        session = _get_sync_sa_session()
        result = session.execute(
            update(TaskTable)
            .where(TaskTable.id == task_id)
            .values(current_stage=stage, updated_at=datetime.utcnow())
        )
        session.commit()
        return result.rowcount > 0
    except Exception as e:
        logger.error(f"更新任务阶段失败 - 任务ID: {task_id}, 阶段: {stage}, 错误: {e}")
        try:
            session.rollback()
        except Exception:
            pass
        return False


def sync_update_task_multi_video_results(
    task_id: str, multi_video_results: List[Dict[str, Any]]
) -> bool:
    """同步更新多视频生成结果到任务记录。

    约定写入 tasks.multi_video_results JSON 字段，并更新 updated_at。
    若目标字段不存在，请在数据库中添加相应列。
    （不吞异常，交由调用方处理）
    """
    with get_sync_db_connection() as conn:
        with conn.cursor() as cursor:
            sql = """
            UPDATE textloom_core.tasks
            SET multi_video_results = %s, updated_at = %s
            WHERE id = %s
            """
            cursor.execute(
                sql, (Json(multi_video_results or []), datetime.utcnow(), task_id)
            )
            return cursor.rowcount > 0


def sync_update_task_multi_video_results_and_count(
    task_id: str, multi_video_results: List[Dict[str, Any]], sub_videos_completed: int
) -> bool:
    """同步更新多视频结果与成功数量（不吞异常）。"""
    with get_sync_db_connection() as conn:
        with conn.cursor() as cursor:
            sql = """
            UPDATE textloom_core.tasks
            SET multi_video_results = %s,
                sub_videos_completed = %s,
                updated_at = %s
            WHERE id = %s
            """
            cursor.execute(
                sql,
                (
                    Json(multi_video_results or []),
                    int(sub_videos_completed or 0),
                    datetime.utcnow(),
                    task_id,
                ),
            )
            return cursor.rowcount > 0


# ==================== 媒体项目相关数据库操作 ====================


def sync_create_media_item(media_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """同步创建媒体项目

    约定与其他表保持一致：不显式插入 id，由数据库默认值生成。
    """
    try:
        session = _get_sync_sa_session()
        now = datetime.utcnow()
        original_url = media_data.get("original_url") or media_data.get("file_url")
        file_url = media_data.get("file_url")
        new_row = MediaItemTable(
            task_id=media_data["task_id"],
            filename=media_data.get("filename"),
            original_url=original_url,
            file_url=file_url,
            local_path=media_data.get("local_path"),
            cloud_url=media_data.get("cloud_url"),
            file_size=media_data.get("file_size"),
            media_type=media_data["media_type"],
            mime_type=media_data.get("mime_type"),
            resolution=media_data.get("resolution"),
            duration=media_data.get("duration"),
            download_status=media_data.get("download_status", "pending"),
            upload_status=media_data.get("upload_status", "pending"),
            downloaded_at=media_data.get("downloaded_at"),
            uploaded_at=media_data.get("uploaded_at"),
            error_message=media_data.get("error_message"),
            context_before=media_data.get("context_before"),
            context_after=media_data.get("context_after"),
            surrounding_paragraph=media_data.get("surrounding_paragraph")
            or media_data.get("context"),
            caption=media_data.get("caption"),
            position_in_content=media_data.get("position")
            or media_data.get("position_in_content"),
            created_at=now,
        )
        session.add(new_row)
        session.flush()
        result = {
            "id": str(new_row.id),
            "task_id": str(new_row.task_id),
            "filename": new_row.filename,
            "original_url": new_row.original_url,
            "file_url": new_row.file_url,
            "local_path": new_row.local_path,
            "cloud_url": new_row.cloud_url,
            "file_size": new_row.file_size,
            "media_type": new_row.media_type,
            "mime_type": new_row.mime_type,
            "resolution": new_row.resolution,
            "duration": new_row.duration,
            "download_status": new_row.download_status,
            "upload_status": new_row.upload_status,
            "downloaded_at": new_row.downloaded_at,
            "uploaded_at": new_row.uploaded_at,
            "error_message": new_row.error_message,
            "context_before": new_row.context_before,
            "context_after": new_row.context_after,
            "surrounding_paragraph": new_row.surrounding_paragraph,
            "caption": new_row.caption,
            "position_in_content": new_row.position_in_content,
            "created_at": new_row.created_at,
        }
        session.commit()
        logger.debug(f"媒体项目创建成功: {result['id']}")
        return result
    except Exception as e:
        logger.error(f"创建媒体项目失败: {e}")
        try:
            session.rollback()
        except Exception:
            pass
        raise


def sync_get_media_items_by_task_id(task_id: str) -> List[Dict[str, Any]]:
    """同步获取任务的媒体项目列表（ORM版）"""
    try:
        session = _get_sync_sa_session()
        rows = (
            session.execute(
                select(MediaItemTable)
                .where(MediaItemTable.task_id == task_id)
                .order_by(MediaItemTable.created_at.asc())
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": str(r.id),
                "task_id": str(r.task_id),
                "filename": r.filename,
                "original_url": r.original_url,
                "file_url": r.file_url,
                "local_path": r.local_path,
                "file_size": r.file_size,
                "media_type": r.media_type,
                "mime_type": r.mime_type,
                "resolution": r.resolution,
                "duration": r.duration,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"获取媒体项目失败 - 任务ID: {task_id}, 错误: {e}")
        return []


# ==================== 素材分析相关数据库操作 ====================


def sync_create_material_analysis(
    analysis_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """同步创建素材分析"""
    try:
        session = _get_sync_sa_session()
        now = datetime.utcnow()
        values = {
            "task_id": analysis_data["task_id"],
            "media_item_id": analysis_data.get("media_item_id"),
            "original_url": analysis_data["original_url"],
            "file_url": analysis_data.get("file_url"),
            "file_type": analysis_data["file_type"],
            "file_size": analysis_data.get("file_size"),
            "status": analysis_data.get("status", AnalysisStatus.PENDING.value),
            "ai_description": analysis_data.get("ai_description"),
            "extracted_text": analysis_data.get("extracted_text"),
            "key_objects": analysis_data.get("key_objects", []),
            "emotional_tone": analysis_data.get("emotional_tone"),
            "visual_style": analysis_data.get("visual_style"),
            "quality_score": analysis_data.get("quality_score"),
            "quality_level": analysis_data.get("quality_level"),
            "usage_suggestions": analysis_data.get("usage_suggestions", []),
            "duration": analysis_data.get("duration"),
            "fps": analysis_data.get("fps"),
            "resolution": analysis_data.get("resolution"),
            "key_frames": analysis_data.get("key_frames", []),
            "dimensions": analysis_data.get("dimensions"),
            "color_palette": analysis_data.get("color_palette", []),
            "created_at": now,
            "updated_at": now,
        }
        insert_stmt = pg_insert(MaterialAnalysisTable).values(values)
        excluded = insert_stmt.excluded
        status_keep_completed = case(
            (MaterialAnalysisTable.status == "completed", MaterialAnalysisTable.status),
            else_=excluded.status,
        )
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                MaterialAnalysisTable.task_id,
                MaterialAnalysisTable.original_url,
            ],
            set_={
                "updated_at": excluded.updated_at,
                "status": status_keep_completed,
            },
        ).returning(
            MaterialAnalysisTable.id,
            MaterialAnalysisTable.task_id,
            MaterialAnalysisTable.original_url,
            MaterialAnalysisTable.file_url,
            MaterialAnalysisTable.status,
        )

        row_mapping = session.execute(upsert_stmt).mappings().first()
        session.commit()

        if not row_mapping:
            logger.error("素材分析创建失败：RETURNING 无结果")
            return None

        result_dict = dict(row_mapping)
        material_analysis_id = result_dict.get("id")

        # 若 RETURNING 未包含 id，做一次回查，避免掩盖潜在问题
        if not material_analysis_id:
            try:
                fetch_id_stmt = (
                    MaterialAnalysisTable.__table__.select()
                    .with_only_columns(MaterialAnalysisTable.id)
                    .where(
                        (MaterialAnalysisTable.task_id == values["task_id"])
                        & (MaterialAnalysisTable.original_url == values["original_url"])
                    )
                )
                fetched = session.execute(fetch_id_stmt).scalar_one_or_none()
                if fetched:
                    material_analysis_id = str(fetched)
                    result_dict["id"] = material_analysis_id
                else:
                    # 记录详细上下文并抛出异常，提示上层介入
                    logger.error(
                        "素材分析创建异常：RETURNING 无 id 且回查失败 — values=%s, returned_keys=%s",
                        values,
                        list(result_dict.keys()),
                    )
                    raise RuntimeError("素材分析创建未返回 id，且回查无记录")
            except Exception as fetch_e:
                logger.error(f"素材分析创建回查异常: {fetch_e}")
                raise

        logger.debug(f"素材分析创建成功: {material_analysis_id}")
        return result_dict
    except Exception as e:
        logger.error(f"创建素材分析失败: {e}")
        try:
            session.rollback()
        except Exception:
            pass
        return None


# ==================== 人设和脚本相关数据库操作 ====================


def sync_get_persona_by_id(persona_id: int) -> Optional[Dict[str, Any]]:
    """同步获取人设信息（ORM版）"""
    try:
        session = _get_sync_sa_session()
        row = (
            session.execute(select(PersonaTable).where(PersonaTable.id == persona_id))
            .scalars()
            .first()
        )
        if not row:
            return None
        return {
            "id": str(row.id),
            "name": row.name,
            "persona_type": row.persona_type,
            "style": row.style,
            "target_audience": row.target_audience,
            "characteristics": row.characteristics,
            "tone": row.tone,
            "keywords": row.keywords,
            "custom_prompts": row.custom_prompts,
            "is_preset": row.is_preset,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    except Exception as e:
        logger.error(f"获取人设失败 - ID: {persona_id}, 错误: {e}")
        return None


def sync_get_prompt_templates_by_type_and_style(
    template_type: str, style: str
) -> List[Dict[str, Any]]:
    """同步获取提示词模板（ORM版）"""
    try:
        session = _get_sync_sa_session()
        rows = (
            session.execute(
                select(PromptTemplateTable)
                .where(
                    (PromptTemplateTable.template_type == template_type)
                    & (PromptTemplateTable.template_style == style)
                )
                .order_by(PromptTemplateTable.created_at.desc())
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": str(r.id),
                "template_key": r.template_key,
                "template_type": r.template_type,
                "style": r.template_style,
                "content": r.template_content,
                "description": r.description,
                "category": r.category,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(
            f"获取提示词模板失败 - 类型: {template_type}, 风格: {style}, 错误: {e}"
        )
        return []


def sync_create_script_content(script_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """同步创建脚本内容（ORM版）"""
    try:
        session = _get_sync_sa_session()
        now = datetime.utcnow()
        row = ScriptContentTable(
            task_id=script_data["task_id"],
            persona_id=script_data.get("persona_id"),
            script_style=script_data.get("script_style", "default"),
            generation_status=script_data.get("generation_status", "processing"),
            titles=script_data.get("titles", []),
            narration=script_data.get("narration"),
            material_mapping=script_data.get("material_mapping", {}),
            description=script_data.get("description"),
            scenes=script_data.get("scenes", []),
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        result = {
            "id": str(row.id),
            "task_id": str(row.task_id),
            "persona_id": str(row.persona_id) if row.persona_id else None,
            "script_style": row.script_style,
            "generation_status": row.generation_status,
            "titles": row.titles,
            "narration": row.narration,
            "material_mapping": row.material_mapping,
            "description": row.description,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        session.commit()
        logger.debug(f"脚本内容创建成功: {result['id']}")
        return result
    except Exception as e:
        logger.error(f"创建脚本内容失败: {e}")
        try:
            session.rollback()
        except Exception:
            pass
        return None


def sync_update_script_content(script_id: str, update_data: Dict[str, Any]) -> bool:
    """同步更新脚本内容（ORM版），仅更新允许字段，并规范 status → generation_status。"""
    try:
        session = _get_sync_sa_session()
        json_fields = {"titles", "material_mapping", "tags", "scenes"}
        allowed_fields = {
            "titles",
            "narration",
            "material_mapping",
            "description",
            "tags",
            "estimated_duration",
            "word_count",
            "material_count",
            "generation_prompt",
            "ai_response",
            "error_message",
            "generation_status",
            "generated_at",
            "script_style",
            "scenes",
        }

        values: Dict[str, Any] = {"updated_at": datetime.utcnow()}
        for key, value in update_data.items():
            target_key = "generation_status" if key == "status" else key
            if target_key not in allowed_fields:
                continue
            values[target_key] = value

        if not values:
            return True

        result = session.execute(
            update(ScriptContentTable)
            .where(ScriptContentTable.id == script_id)
            .values(**values)
        )
        session.commit()
        return result.rowcount > 0
    except Exception as e:
        logger.error(f"更新脚本内容失败 - 脚本ID: {script_id}, 错误: {e}")
        try:
            session.rollback()
        except Exception:
            pass
        return False


# ==================== 子视频任务相关数据库操作 ====================
# 注意：SubVideoTask 相关功能已移除，主任务直接管理视频生成


