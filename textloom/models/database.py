import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_connection import get_db_session
from models.db_models import (
    MaterialAnalysisTable,
    MediaItemTable,
    PersonaTable,
    PromptTemplateTable,
    ScriptContentTable,
    TaskTable,
    VideoProjectTable,
)
from models.material_analysis import (
    AnalysisStats,
    AnalysisStatus,
    MaterialAnalysisInDB,
    QualityLevel,
)
from models.task import (
    MediaItem,
    MediaItemInDB,
    TaskDetail,
    TaskInDB,
    TaskStats,
    TaskStatus,
    TaskType,
)
from models.video_project import VideoProjectInDB, VideoProjectStatus

logger = logging.getLogger(__name__)


async def create_tables():
    """创建数据库表（已废弃，请使用 init_database.py）"""
    logger.warning(
        "create_tables() 函数已废弃，请使用 'uv run python init_database.py create' 创建表"
    )
    # 不再自动创建表，避免启动时的事务冲突
    pass


# 视频项目相关数据库操作
async def get_video_project_by_id(project_id: UUID) -> Optional[VideoProjectInDB]:
    """根据ID获取视频项目"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(VideoProjectTable).where(VideoProjectTable.id == project_id)
            )
            project_row = result.scalar_one_or_none()
            if project_row:
                return VideoProjectInDB(
                    id=project_row.id,
                    title=project_row.title,
                    status=VideoProjectStatus(project_row.status),
                    video_url=project_row.video_url,
                    created_at=project_row.created_at,
                    updated_at=project_row.updated_at,
                )
            return None
    except Exception as e:
        logger.error(f"获取视频项目失败: {str(e)}")
        return None


async def create_video_project(project_data: dict) -> VideoProjectInDB:
    """创建新视频项目"""
    try:
        async with get_db_session() as session:
            now = datetime.utcnow()
            project_row = VideoProjectTable(
                title=project_data["title"],
                status=project_data.get("status", VideoProjectStatus.PROCESSING),
                video_url=project_data.get("video_url"),
                created_at=now,
                updated_at=now,
            )
            session.add(project_row)
            await session.flush()

            return VideoProjectInDB(
                id=project_row.id,
                title=project_row.title,
                status=VideoProjectStatus(project_row.status),
                video_url=project_row.video_url,
                created_at=project_row.created_at,
                updated_at=project_row.updated_at,
            )
    except Exception as e:
        logger.error(f"创建视频项目失败: {str(e)}")
        raise


async def update_video_project(
    project_id: UUID, update_data: dict
) -> Optional[VideoProjectInDB]:
    """更新视频项目"""
    try:
        async with get_db_session() as session:
            # 更新项目
            stmt = (
                update(VideoProjectTable)
                .where(VideoProjectTable.id == project_id)
                .values(**update_data, updated_at=datetime.utcnow())
            )
            result = await session.execute(stmt)

            if result.rowcount == 0:
                return None

            # 获取更新后的项目
            return await get_video_project_by_id(project_id)
    except Exception as e:
        logger.error(f"更新视频项目失败: {str(e)}")
        return None


async def delete_video_project(project_id: UUID) -> bool:
    """删除视频项目"""
    try:
        async with get_db_session() as session:
            stmt = delete(VideoProjectTable).where(VideoProjectTable.id == project_id)
            result = await session.execute(stmt)
            return result.rowcount > 0
    except Exception as e:
        logger.error(f"删除视频项目失败: {str(e)}")
        return False


async def get_all_video_projects() -> List[VideoProjectInDB]:
    """获取所有视频项目"""
    try:
        async with get_db_session() as session:
            result = await session.execute(select(VideoProjectTable))
            projects = []
            for row in result.scalars():
                projects.append(
                    VideoProjectInDB(
                        id=row.id,
                        title=row.title,
                        status=VideoProjectStatus(row.status),
                        video_url=row.video_url,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                )
            return projects
    except Exception as e:
        logger.error(f"获取所有视频项目失败: {str(e)}")
        return []


async def get_video_projects_by_status(
    status: VideoProjectStatus,
) -> List[VideoProjectInDB]:
    """根据状态获取视频项目"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(VideoProjectTable).where(
                    VideoProjectTable.status == status.value
                )
            )
            projects = []
            for row in result.scalars():
                projects.append(
                    VideoProjectInDB(
                        id=row.id,
                        title=row.title,
                        status=VideoProjectStatus(row.status),
                        video_url=row.video_url,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                )
            return projects
    except Exception as e:
        logger.error(f"根据状态获取视频项目失败: {str(e)}")
        return []


# 任务相关数据库操作
async def get_task_by_id(task_id: UUID) -> Optional[TaskInDB]:
    """根据ID获取任务"""
    try:
        if not task_id:
            logger.warning("get_task_by_id: 任务ID为空")
            return None

        logger.debug(f"get_task_by_id: 查找任务ID {task_id}")

        async with get_db_session() as session:
            result = await session.execute(
                select(TaskTable).where(TaskTable.id == task_id)
            )
            task_row = result.scalar_one_or_none()

            if task_row:
                logger.debug(
                    f"get_task_by_id: 找到任务 {task_id}, 状态: {task_row.status}"
                )
                return _convert_task_row_to_model(task_row)
            else:
                logger.warning(f"get_task_by_id: 未找到任务 {task_id}")
                return None

    except Exception as e:
        logger.error(
            f"get_task_by_id: 查找任务时异常 - 任务ID: {task_id}, 错误: {str(e)}"
        )
        return None


async def get_task_detail(task_id: UUID) -> Optional[TaskDetail]:
    """获取任务详细信息"""
    try:
        task = await get_task_by_id(task_id)
        if not task:
            return None

        # 获取任务相关的媒体项目
        media_items = await get_media_items_by_task_id(task_id)

        # 获取任务相关的素材分析并转换为字典
        async with get_db_session() as session:
            result = await session.execute(
                select(MaterialAnalysisTable).where(
                    MaterialAnalysisTable.task_id == task_id
                )
            )
            material_analyses = []
            for row in result.scalars():
                material_analyses.append({
                    "id": str(row.id),
                    "task_id": str(row.task_id),
                    "media_item_id": str(row.media_item_id) if row.media_item_id else None,
                    "original_url": row.original_url,
                    "file_url": row.file_url,
                    "file_type": row.file_type,
                    "file_size": row.file_size,
                    "status": row.status,
                    "ai_description": row.ai_description,
                    "extracted_text": row.extracted_text,
                    "key_objects": row.key_objects or [],
                    "emotional_tone": row.emotional_tone,
                    "visual_style": row.visual_style,
                    "quality_score": row.quality_score,
                    "quality_level": row.quality_level,
                    "usage_suggestions": row.usage_suggestions or [],
                    "duration": row.duration,
                    "fps": row.fps,
                    "resolution": row.resolution,
                    "key_frames": row.key_frames or [],
                    "dimensions": row.dimensions,
                    "color_palette": row.color_palette or [],
                    "processing_time": row.processing_time,
                    "model_version": row.model_version,
                    "error_message": row.error_message,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                })

        return TaskDetail(
            id=task.id,
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            status=task.status,
            progress=task.progress,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
            media_items=media_items,
            material_analyses=material_analyses,
            script_content=None,
            sub_video_tasks=[],  # 子视频功能已移除
        )
    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}")
        return None


def _convert_task_row_to_model(task_row: TaskTable) -> TaskInDB:
    """将数据库行转换为TaskInDB模型"""
    return TaskInDB(
        id=task_row.id,
        title=task_row.title,
        description=task_row.description,
        creator_id=str(task_row.creator_id) if task_row.creator_id else None,
        task_type=TaskType(task_row.task_type),
        status=TaskStatus(task_row.status),
        progress=task_row.progress,
        current_stage=getattr(task_row, "current_stage", None),
        created_at=task_row.created_at,
        updated_at=task_row.updated_at,
        started_at=task_row.started_at,
        completed_at=task_row.completed_at,
        error_message=task_row.error_message,
        # Celery集成字段
        celery_task_id=getattr(task_row, "celery_task_id", None),
        worker_name=getattr(task_row, "worker_name", None),
        retry_count=getattr(task_row, "retry_count", 0) or 0,
        max_retries=getattr(task_row, "max_retries", 3) or 3,
        error_traceback=getattr(task_row, "error_traceback", None),
        # 脚本相关字段
        script_title=getattr(task_row, "script_title", None),
        script_description=getattr(task_row, "script_description", None),
        script_narration=getattr(task_row, "script_narration", None),
        script_tags=getattr(task_row, "script_tags", None) or [],
        script_estimated_duration=getattr(task_row, "script_estimated_duration", None),
        script_word_count=getattr(task_row, "script_word_count", None),
        script_material_count=getattr(task_row, "script_material_count", None),
        # 视频相关字段
        video_url=getattr(task_row, "video_url", None),
        thumbnail_url=getattr(task_row, "thumbnail_url", None),
        video_duration=getattr(task_row, "video_duration", None),
        video_file_size=getattr(task_row, "video_file_size", None),
        video_quality=getattr(task_row, "video_quality", None),
        course_media_id=getattr(task_row, "course_media_id", None),
        # 多视频相关字段已移除 - 改为单视频架构
        is_multi_video_task=False,  # 硬编码为 False，保持兼容性
        multi_video_urls=[],
        multi_video_count=1,
        # 缺失的字段设置默认值
        source_file=getattr(task_row, "file_path", None),
        file_path=getattr(task_row, "file_path", None),
        workspace_dir=getattr(task_row, "workspace_dir", None),
        script_style_type=getattr(task_row, "script_style_type", None),
        sub_videos_completed=0,
        multi_video_results=[],
    )


async def create_task(task_data: dict) -> TaskInDB:
    """创建新任务"""
    try:
        logger.info(f"create_task: 创建任务，数据: {task_data}")

        async with get_db_session() as session:
            now = datetime.utcnow()
            task_row = TaskTable(
                title=task_data["title"],
                description=task_data.get("description"),
                creator_id=task_data.get("creator_id"),
                task_type=task_data["task_type"],
                status=task_data.get("status", TaskStatus.PENDING),
                progress=task_data.get("progress", 0),
                created_at=now,
                updated_at=now,
                # is_multi_video_task 和 multi_video_count 已移除 - 改为单视频架构
                file_path=task_data.get("file_path"),
                source_file=task_data.get("file_path"),  # 使用file_path作为source_file
                workspace_dir=task_data.get("workspace_dir"),
                script_style_type=task_data.get("script_style_type"),
                script_material_count=task_data.get("script_material_count"),
            )
            session.add(task_row)
            # 刷新以获取数据库生成的ID
            await session.flush()
            # 刷新对象以确保从数据库获取所有属性
            await session.refresh(task_row)

            logger.info(
                f"create_task: 任务行ID: {task_row.id}, 类型: {type(task_row.id)}"
            )

            # 确保ID不为None
            if task_row.id is None:
                logger.error("create_task: 数据库未生成ID，强制生成UUID")
                task_row.id = uuid4()
                await session.flush()
                await session.refresh(task_row)

            created_task = _convert_task_row_to_model(task_row)
            logger.info(f"create_task: 任务创建成功，ID: {created_task.id}")
            return created_task

    except Exception as e:
        logger.error(f"create_task: 创建任务失败 - 错误: {str(e)}")
        raise


async def update_task(task_id: UUID, update_data: dict) -> Optional[TaskInDB]:
    """更新任务"""
    try:
        logger.debug(f"update_task: 更新任务 {task_id}，数据: {update_data}")

        async with get_db_session() as session:
            # 准备更新数据
            update_values = {**update_data, "updated_at": datetime.utcnow()}

            # 执行更新
            stmt = (
                update(TaskTable).where(TaskTable.id == task_id).values(**update_values)
            )
            result = await session.execute(stmt)

            if result.rowcount == 0:
                logger.warning(f"update_task: 任务 {task_id} 不存在")
                return None

            # 获取更新后的任务
            updated_task = await get_task_by_id(task_id)
            logger.debug(f"update_task: 任务 {task_id} 更新成功")
            return updated_task

    except Exception as e:
        logger.error(f"update_task: 更新任务失败 - 任务ID: {task_id}, 错误: {str(e)}")
        return None


async def delete_task(task_id: UUID) -> bool:
    """删除任务"""
    try:
        async with get_db_session() as session:
            # 先删除相关的媒体项目和分析
            await session.execute(
                delete(MediaItemTable).where(MediaItemTable.task_id == task_id)
            )
            await session.execute(
                delete(MaterialAnalysisTable).where(
                    MaterialAnalysisTable.task_id == task_id
                )
            )
            await session.execute(
                delete(ScriptContentTable).where(ScriptContentTable.task_id == task_id)
            )

            # 删除任务
            stmt = delete(TaskTable).where(TaskTable.id == task_id)
            result = await session.execute(stmt)
            return result.rowcount > 0
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        return False


async def get_all_tasks() -> List[TaskInDB]:
    """获取所有任务"""
    try:
        async with get_db_session() as session:
            result = await session.execute(select(TaskTable))
            tasks = []
            for row in result.scalars():
                tasks.append(_convert_task_row_to_model(row))
            return tasks
    except Exception as e:
        logger.error(f"获取所有任务失败: {str(e)}")
        return []


async def get_tasks_by_status(status: TaskStatus) -> List[TaskInDB]:
    """根据状态获取任务"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(TaskTable).where(TaskTable.status == status.value)
            )
            tasks = []
            for row in result.scalars():
                tasks.append(_convert_task_row_to_model(row))
            return tasks
    except Exception as e:
        logger.error(f"根据状态获取任务失败: {str(e)}")
        return []


async def get_tasks_by_creator(creator_id: str) -> List[TaskInDB]:
    """根据创建者获取任务"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(TaskTable).where(TaskTable.creator_id == creator_id)
            )
            tasks = []
            for row in result.scalars():
                tasks.append(_convert_task_row_to_model(row))
            return tasks
    except Exception as e:
        logger.error(f"根据创建者获取任务失败: {str(e)}")
        return []


# 其他函数保持兼容，先用简单实现
async def get_task_by_creator_and_type(
    creator_id: str, task_type: TaskType
) -> Optional[TaskInDB]:
    """根据创建者和任务类型获取任务"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(TaskTable)
                .where(
                    and_(
                        TaskTable.creator_id == creator_id,
                        TaskTable.task_type == task_type.value,
                    )
                )
                .order_by(TaskTable.created_at.desc())
            )
            task_row = result.first()
            return _convert_task_row_to_model(task_row[0]) if task_row else None
    except Exception as e:
        logger.error(f"根据创建者和类型获取任务失败: {str(e)}")
        return None


async def get_tasks_by_status_and_type(
    status: TaskStatus, task_type: TaskType
) -> List[TaskInDB]:
    """根据状态和类型获取任务"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(TaskTable).where(
                    and_(
                        TaskTable.status == status.value,
                        TaskTable.task_type == task_type.value,
                    )
                )
            )
            tasks = []
            for row in result.scalars():
                tasks.append(_convert_task_row_to_model(row))
            return tasks
    except Exception as e:
        logger.error(f"根据状态和类型获取任务失败: {str(e)}")
        return []


async def get_tasks_by_type(task_type: TaskType) -> List[TaskInDB]:
    """根据任务类型获取任务"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(TaskTable).where(TaskTable.task_type == task_type.value)
            )
            tasks = []
            for row in result.scalars():
                tasks.append(_convert_task_row_to_model(row))
            return tasks
    except Exception as e:
        logger.error(f"根据类型获取任务失败: {str(e)}")
        return []


async def get_tasks_in_status_list(status_list: List[TaskStatus]) -> List[TaskInDB]:
    """根据状态列表获取任务"""
    try:
        async with get_db_session() as session:
            status_values = [status.value for status in status_list]
            result = await session.execute(
                select(TaskTable).where(TaskTable.status.in_(status_values))
            )
            tasks = []
            for row in result.scalars():
                tasks.append(_convert_task_row_to_model(row))
            return tasks
    except Exception as e:
        logger.error(f"根据状态列表获取任务失败: {str(e)}")
        return []


# 媒体项目相关数据库操作
async def create_media_item(media_data: dict) -> MediaItemInDB:
    """创建媒体项目"""
    try:
        async with get_db_session() as session:
            media_row = MediaItemTable(
                task_id=media_data["task_id"],
                filename=media_data["filename"],
                original_url=media_data["original_url"],
                file_url=media_data.get("file_url"),
                file_size=media_data.get("file_size"),
                media_type=media_data["media_type"],
                mime_type=media_data.get("mime_type"),
                resolution=media_data.get("resolution"),
                duration=media_data.get("duration"),
                context_before=media_data.get("context_before"),
                context_after=media_data.get("context_after"),
                surrounding_paragraph=media_data.get("surrounding_paragraph"),
                caption=media_data.get("caption"),
                position_in_content=media_data.get("position_in_content"),
                created_at=datetime.utcnow(),
            )
            session.add(media_row)
            await session.flush()

            return MediaItemInDB(
                id=media_row.id,
                task_id=media_row.task_id,
                original_url=media_row.original_url,
                filename=media_row.filename,
                file_url=media_row.file_url,
                file_size=media_row.file_size,
                media_type=media_row.media_type,
                mime_type=media_row.mime_type,
                resolution=media_row.resolution,
                duration=media_row.duration,
                created_at=media_row.created_at,
            )
    except Exception as e:
        logger.error(f"创建媒体项目失败: {str(e)}")
        raise


async def get_media_item_by_id(media_id: UUID) -> Optional[MediaItemInDB]:
    """根据ID获取媒体项目"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(MediaItemTable).where(MediaItemTable.id == media_id)
            )
            row = result.scalar_one_or_none()
            if row:
                return MediaItemInDB(
                    id=row.id,
                    task_id=row.task_id,
                    original_url=row.original_url,
                    filename=row.filename,
                    file_url=row.file_url,
                    file_size=row.file_size,
                    media_type=row.media_type,
                    mime_type=row.mime_type,
                    duration=row.duration,
                    created_at=row.created_at,
                )
            return None
    except Exception as e:
        logger.error(f"根据ID获取媒体项目失败: {str(e)}")
        return None


async def get_media_items_by_task_id(task_id: UUID) -> List[MediaItemInDB]:
    """根据任务ID获取媒体项目"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(MediaItemTable).where(MediaItemTable.task_id == task_id)
            )
            media_items = []
            for row in result.scalars():
                media_items.append(
                    MediaItemInDB(
                        id=row.id,
                        task_id=row.task_id,
                        original_url=row.original_url,
                        filename=row.filename,
                        file_url=row.file_url,
                        local_path=row.local_path,
                        cloud_url=row.cloud_url,
                        file_size=row.file_size,
                        media_type=row.media_type,
                        mime_type=row.mime_type,
                        resolution=row.resolution,
                        duration=row.duration,
                        download_status=row.download_status,
                        upload_status=row.upload_status,
                        downloaded_at=row.downloaded_at,
                        uploaded_at=row.uploaded_at,
                        error_message=row.error_message,
                        context_before=row.context_before,
                        context_after=row.context_after,
                        surrounding_paragraph=row.surrounding_paragraph,
                        caption=row.caption,
                        position_in_content=row.position_in_content,
                        created_at=row.created_at,
                    )
                )
            return media_items
    except Exception as e:
        logger.error(f"根据任务获取媒体项目失败: {str(e)}")
        return []


async def update_media_item(
    media_id: UUID, update_data: dict
) -> Optional[MediaItemInDB]:
    """更新媒体项目"""
    try:
        async with get_db_session() as session:
            stmt = (
                update(MediaItemTable)
                .where(MediaItemTable.id == media_id)
                .values(**update_data)
            )
            result = await session.execute(stmt)

            if result.rowcount == 0:
                return None

            return await get_media_item_by_id(media_id)
    except Exception as e:
        logger.error(f"更新媒体项目失败: {str(e)}")
        return None


async def delete_media_item(media_id: UUID) -> bool:
    """删除媒体项目"""
    try:
        async with get_db_session() as session:
            stmt = delete(MediaItemTable).where(MediaItemTable.id == media_id)
            result = await session.execute(stmt)
            return result.rowcount > 0
    except Exception as e:
        logger.error(f"删除媒体项目失败: {str(e)}")
        return False


# 素材分析相关数据库操作
async def create_material_analysis(analysis_data: dict) -> MaterialAnalysisInDB:
    """创建素材分析"""
    try:
        async with get_db_session() as session:
            analysis_row = MaterialAnalysisTable(
                task_id=analysis_data["task_id"],
                original_url=analysis_data["original_url"],
                file_url=analysis_data.get("file_url"),
                file_type=analysis_data["file_type"],
                file_size=analysis_data.get("file_size"),
                status=analysis_data.get("status", AnalysisStatus.PENDING),
                created_at=datetime.utcnow(),
            )
            session.add(analysis_row)
            await session.flush()

            return _convert_analysis_row_to_model(analysis_row)
    except Exception as e:
        logger.error(f"创建素材分析失败: {str(e)}")
        raise


def _convert_analysis_row_to_model(
    analysis_row: MaterialAnalysisTable,
) -> MaterialAnalysisInDB:
    """将数据库行转换为MaterialAnalysisInDB模型"""
    return MaterialAnalysisInDB(
        id=analysis_row.id,
        task_id=analysis_row.task_id,
        media_item_id=getattr(analysis_row, "media_item_id", None),
        original_url=analysis_row.original_url,
        file_url=analysis_row.file_url,
        file_type=analysis_row.file_type,
        file_size=analysis_row.file_size,
        status=AnalysisStatus(analysis_row.status),
        ai_description=analysis_row.ai_description,
        extracted_text=analysis_row.extracted_text,
        key_objects=analysis_row.key_objects or [],
        emotional_tone=analysis_row.emotional_tone,
        visual_style=analysis_row.visual_style,
        quality_score=analysis_row.quality_score,
        quality_level=(
            QualityLevel(analysis_row.quality_level)
            if analysis_row.quality_level
            else None
        ),
        usage_suggestions=analysis_row.usage_suggestions or [],
        duration=analysis_row.duration,
        fps=analysis_row.fps,
        resolution=analysis_row.resolution,
        key_frames=analysis_row.key_frames or [],
        dimensions=analysis_row.dimensions,
        color_palette=analysis_row.color_palette or [],
        processing_time=analysis_row.processing_time,
        model_version=analysis_row.model_version,
        error_message=analysis_row.error_message,
        created_at=analysis_row.created_at,
        updated_at=analysis_row.updated_at,
    )


async def get_material_analysis_by_id(
    analysis_id: UUID,
) -> Optional[MaterialAnalysisInDB]:
    """根据ID获取素材分析"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(MaterialAnalysisTable).where(
                    MaterialAnalysisTable.id == analysis_id
                )
            )
            row = result.scalar_one_or_none()
            return _convert_analysis_row_to_model(row) if row else None
    except Exception as e:
        logger.error(f"获取素材分析失败: {str(e)}")
        return None


async def update_material_analysis(
    analysis_id: UUID, update_data: dict
) -> Optional[MaterialAnalysisInDB]:
    """更新素材分析"""
    try:
        async with get_db_session() as session:
            update_values = {**update_data, "updated_at": datetime.utcnow()}
            stmt = (
                update(MaterialAnalysisTable)
                .where(MaterialAnalysisTable.id == analysis_id)
                .values(**update_values)
            )
            result = await session.execute(stmt)

            if result.rowcount == 0:
                return None

            return await get_material_analysis_by_id(analysis_id)
    except Exception as e:
        logger.error(f"更新素材分析失败: {str(e)}")
        return None


async def get_material_analyses_by_task(task_id: UUID) -> List[MaterialAnalysisInDB]:
    """根据任务ID获取素材分析"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(MaterialAnalysisTable).where(
                    MaterialAnalysisTable.task_id == task_id
                )
            )
            analyses = []
            for row in result.scalars():
                analyses.append(_convert_analysis_row_to_model(row))
            return analyses
    except Exception as e:
        logger.error(f"根据任务获取素材分析失败: {str(e)}")
        return []


async def get_analysis_stats() -> AnalysisStats:
    """获取分析统计信息"""
    try:
        async with get_db_session() as session:
            # 获取总数
            total_result = await session.execute(
                select(func.count(MaterialAnalysisTable.id))
            )
            total = total_result.scalar()

            # 获取各状态数量
            status_result = await session.execute(
                select(
                    MaterialAnalysisTable.status, func.count(MaterialAnalysisTable.id)
                ).group_by(MaterialAnalysisTable.status)
            )
            status_counts = dict(status_result.all())

            return AnalysisStats(
                total_analyses=total,
                pending_analyses=status_counts.get(AnalysisStatus.PENDING.value, 0),
                processing_analyses=status_counts.get(
                    AnalysisStatus.PROCESSING.value, 0
                ),
                completed_analyses=status_counts.get(AnalysisStatus.COMPLETED.value, 0),
                failed_analyses=status_counts.get(AnalysisStatus.FAILED.value, 0),
            )
    except Exception as e:
        logger.error(f"获取分析统计失败: {str(e)}")
        return AnalysisStats()


async def cleanup_old_analyses(days: int = 30) -> int:
    """清理旧的分析记录"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        async with get_db_session() as session:
            stmt = delete(MaterialAnalysisTable).where(
                MaterialAnalysisTable.created_at < cutoff_date
            )
            result = await session.execute(stmt)
            return result.rowcount
    except Exception as e:
        logger.error(f"清理旧分析记录失败: {str(e)}")
        return 0


# 人设相关操作 - 兼容原有接口
async def create_persona(persona_data: dict):
    """创建人设"""
    try:
        async with get_db_session() as session:
            persona_row = PersonaTable(
                name=persona_data["name"],
                persona_type=persona_data["persona_type"],
                style=persona_data.get("style"),
                target_audience=persona_data.get("target_audience"),
                characteristics=persona_data.get("characteristics"),
                tone=persona_data.get("tone"),
                keywords=persona_data.get("keywords"),
                custom_prompts=persona_data.get("custom_prompts", {}),
                is_preset=persona_data.get("is_preset", False),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(persona_row)
            await session.flush()

            return {
                "id": str(persona_row.id),
                "name": persona_row.name,
                "persona_type": persona_row.persona_type,
                "style": persona_row.style,
                "target_audience": persona_row.target_audience,
                "characteristics": persona_row.characteristics,
                "tone": persona_row.tone,
                "keywords": persona_row.keywords,
                "custom_prompts": persona_row.custom_prompts,
                "is_preset": persona_row.is_preset,
                "created_at": persona_row.created_at,
                "updated_at": persona_row.updated_at,
            }
    except Exception as e:
        logger.error(f"创建人设失败: {str(e)}")
        raise


async def get_persona_by_id(persona_id: str) -> Optional[dict]:
    """根据ID获取人设"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(PersonaTable).where(PersonaTable.id == persona_id)
            )
            row = result.scalar_one_or_none()
            if row:
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
            return None
    except Exception as e:
        logger.error(f"获取人设失败: {str(e)}")
        return None


async def get_all_personas() -> List[dict]:
    """获取所有人设"""
    try:
        async with get_db_session() as session:
            result = await session.execute(select(PersonaTable))
            personas = []
            for row in result.scalars():
                personas.append(
                    {
                        "id": str(row.id),
                        "name": row.name,
                        "persona_type": row.persona_type,
                        "style": row.style,
                        "target_audience": row.target_audience,
                        "characteristics": row.characteristics,
                        "tone": row.tone,
                        "keywords": row.keywords.split(",") if row.keywords else [],
                        "custom_prompts": row.custom_prompts,
                        "is_preset": row.is_preset,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                )
            return personas
    except Exception as e:
        logger.error(f"获取所有人设失败: {str(e)}")
        return []


async def get_preset_personas() -> List[dict]:
    """获取预设人设"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(PersonaTable).where(PersonaTable.is_preset == True)
            )
            personas = []
            for row in result.scalars():
                personas.append(
                    {
                        "id": str(row.id),
                        "name": row.name,
                        "persona_type": row.persona_type,
                        "style": row.style,
                        "target_audience": row.target_audience,
                        "characteristics": row.characteristics,
                        "tone": row.tone,
                        "keywords": row.keywords.split(",") if row.keywords else [],
                        "custom_prompts": row.custom_prompts,
                        "is_preset": row.is_preset,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                )
            return personas
    except Exception as e:
        logger.error(f"获取预设人设失败: {str(e)}")
        return []


async def update_persona(persona_id: str, update_data: dict) -> Optional[dict]:
    """更新人设"""
    try:
        async with get_db_session() as session:
            update_values = {**update_data, "updated_at": datetime.utcnow()}
            stmt = (
                update(PersonaTable)
                .where(PersonaTable.id == persona_id)
                .values(**update_values)
            )
            result = await session.execute(stmt)

            if result.rowcount == 0:
                return None

            return await get_persona_by_id(persona_id)
    except Exception as e:
        logger.error(f"更新人设失败: {str(e)}")
        return None


async def delete_persona(persona_id: str) -> bool:
    """删除人设"""
    try:
        async with get_db_session() as session:
            stmt = delete(PersonaTable).where(PersonaTable.id == persona_id)
            result = await session.execute(stmt)
            return result.rowcount > 0
    except Exception as e:
        logger.error(f"删除人设失败: {str(e)}")
        return False


# 其他原有函数的简化实现，保持兼容性
async def get_task_stats() -> TaskStats:
    """获取任务统计信息"""
    try:
        async with get_db_session() as session:
            total_result = await session.execute(select(func.count(TaskTable.id)))
            total = total_result.scalar()

            status_result = await session.execute(
                select(TaskTable.status, func.count(TaskTable.id)).group_by(
                    TaskTable.status
                )
            )
            status_counts = dict(status_result.all())

            return TaskStats(
                total_tasks=total,
                pending_tasks=status_counts.get(TaskStatus.PENDING.value, 0),
                processing_tasks=status_counts.get(TaskStatus.PROCESSING.value, 0),
                completed_tasks=status_counts.get(TaskStatus.COMPLETED.value, 0),
                failed_tasks=status_counts.get(TaskStatus.FAILED.value, 0),
            )
    except Exception as e:
        logger.error(f"获取任务统计失败: {str(e)}")
        return TaskStats()


async def get_recent_tasks(limit: int = 10) -> List[TaskInDB]:
    """获取最近的任务"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(TaskTable).order_by(TaskTable.created_at.desc()).limit(limit)
            )
            tasks = []
            for row in result.scalars():
                tasks.append(_convert_task_row_to_model(row))
            return tasks
    except Exception as e:
        logger.error(f"获取最近任务失败: {str(e)}")
        return []


# 其他必需的函数实现
async def get_prompt_template_by_key(template_key: str) -> Optional[dict]:
    """根据键获取提示词模板"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(PromptTemplateTable).where(
                    PromptTemplateTable.template_key == template_key
                )
            )
            row = result.scalar_one_or_none()
            if row:
                return {
                    "id": str(row.id),
                    "template_key": row.template_key,
                    "template_content": row.template_content,
                    "description": row.description,
                    "category": row.category,
                    "created_at": row.created_at,
                }
            return None
    except Exception as e:
        logger.error(f"获取提示词模板失败: {str(e)}")
        return None


async def create_prompt_template(template_data: dict) -> dict:
    """创建提示词模板"""
    try:
        async with get_db_session() as session:
            template_row = PromptTemplateTable(
                template_key=template_data["template_key"],
                template_content=template_data["template_content"],
                description=template_data.get("description"),
                category=template_data.get("category"),
                template_type=template_data.get("template_type"),
                template_style=template_data.get("template_style"),
                created_at=datetime.utcnow(),
            )
            session.add(template_row)
            await session.flush()

            return {
                "id": str(template_row.id),
                "template_key": template_row.template_key,
                "template_content": template_row.template_content,
                "description": template_row.description,
                "category": template_row.category,
                "template_type": template_row.template_type,
                "template_style": template_row.template_style,
                "created_at": template_row.created_at,
            }
    except Exception as e:
        logger.error(f"创建提示词模板失败: {str(e)}")
        raise


async def get_prompt_templates_by_type_and_style(
    template_type: str, template_style: str
) -> List[dict]:
    """根据类型和风格获取提示词模板"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(PromptTemplateTable).where(
                    and_(
                        PromptTemplateTable.template_type == template_type,
                        PromptTemplateTable.template_style == template_style,
                    )
                )
            )
            templates = []
            for row in result.scalars():
                templates.append(
                    {
                        "id": str(row.id),
                        "template_key": row.template_key,
                        "template_content": row.template_content,
                        "description": row.description,
                        "category": row.category,
                        "template_type": row.template_type,
                        "template_style": row.template_style,
                        "created_at": row.created_at,
                    }
                )
            return templates
    except Exception as e:
        logger.error(f"根据类型和风格获取提示词模板失败: {str(e)}")
        return []


# 脚本内容相关函数
async def create_script_content(script_data: dict) -> dict:
    """创建脚本内容"""
    try:
        async with get_db_session() as session:
            script_row = ScriptContentTable(
                task_id=script_data["task_id"],
                persona_id=script_data.get("persona_id"),
                script_style=script_data.get("script_style"),
                generation_status=script_data.get("generation_status", "pending"),
                titles=script_data.get("titles", []),
                narration=script_data.get("narration"),
                material_mapping=script_data.get("material_mapping", {}),
                description=script_data.get("description"),
                tags=script_data.get("tags", []),
                estimated_duration=script_data.get("estimated_duration"),
                word_count=script_data.get("word_count"),
                material_count=script_data.get("material_count"),
                generation_prompt=script_data.get("generation_prompt"),
                ai_response=script_data.get("ai_response"),
                error_message=script_data.get("error_message"),
                created_at=datetime.utcnow(),
            )
            session.add(script_row)
            await session.flush()

            return {
                "id": str(script_row.id),
                "task_id": str(script_row.task_id),
                "persona_id": (
                    str(script_row.persona_id) if script_row.persona_id else None
                ),
                "script_style": script_row.script_style,
                "generation_status": script_row.generation_status,
                "titles": script_row.titles,
                "narration": script_row.narration,
                "material_mapping": script_row.material_mapping,
                "description": script_row.description,
                "tags": script_row.tags,
                "estimated_duration": script_row.estimated_duration,
                "word_count": script_row.word_count,
                "material_count": script_row.material_count,
                "generation_prompt": script_row.generation_prompt,
                "ai_response": script_row.ai_response,
                "error_message": script_row.error_message,
                "created_at": script_row.created_at,
                "updated_at": script_row.updated_at,
                "generated_at": script_row.generated_at,
            }
    except Exception as e:
        logger.error(f"创建脚本内容失败: {str(e)}")
        raise


async def get_script_content_by_task_id(task_id: UUID) -> Optional[dict]:
    """根据任务ID获取脚本内容（返回最新的一个脚本）"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(ScriptContentTable)
                .where(ScriptContentTable.task_id == task_id)
                .order_by(ScriptContentTable.created_at.desc())
            )
            row = result.first()
            if row:
                row = row[0]  # 从tuple中提取实际的row对象
                return {
                    "id": str(row.id),
                    "task_id": str(row.task_id),
                    "persona_id": str(row.persona_id) if row.persona_id else None,
                    "script_style": row.script_style,
                    "generation_status": row.generation_status,
                    "titles": row.titles,
                    "narration": row.narration,
                    "material_mapping": row.material_mapping,
                    "description": row.description,
                    "tags": row.tags,
                    "estimated_duration": row.estimated_duration,
                    "word_count": row.word_count,
                    "material_count": row.material_count,
                    "generation_prompt": row.generation_prompt,
                    "ai_response": row.ai_response,
                    "error_message": row.error_message,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "generated_at": row.generated_at,
                }
            return None
    except Exception as e:
        logger.error(f"根据任务ID获取脚本内容失败: {str(e)}")
        return None


async def get_all_script_contents_by_task_id(task_id: UUID) -> List[dict]:
    """根据任务ID获取所有脚本内容"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(ScriptContentTable)
                .where(ScriptContentTable.task_id == task_id)
                .order_by(ScriptContentTable.created_at.desc())
            )
            scripts = []
            for row in result.scalars():
                scripts.append({
                    "id": str(row.id),
                    "task_id": str(row.task_id),
                    "persona_id": str(row.persona_id) if row.persona_id else None,
                    "script_style": row.script_style,
                    "generation_status": row.generation_status,
                    "titles": row.titles,
                    "narration": row.narration,
                    "material_mapping": row.material_mapping,
                    "description": row.description,
                    "tags": row.tags,
                    "estimated_duration": row.estimated_duration,
                    "word_count": row.word_count,
                    "material_count": row.material_count,
                    "generation_prompt": row.generation_prompt,
                    "ai_response": row.ai_response,
                    "error_message": row.error_message,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "generated_at": row.generated_at,
                })
            return scripts
    except Exception as e:
        logger.error(f"根据任务ID获取所有脚本内容失败: {str(e)}")
        return []


async def get_script_content_by_id(script_id: str) -> Optional[dict]:
    """根据脚本ID获取脚本内容"""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(ScriptContentTable).where(ScriptContentTable.id == script_id)
            )
            row = result.scalar_one_or_none()
            if row:
                return {
                    "id": str(row.id),
                    "task_id": str(row.task_id),
                    "persona_id": str(row.persona_id) if row.persona_id else None,
                    "script_style": row.script_style,
                    "generation_status": row.generation_status,
                    "titles": row.titles,
                    "narration": row.narration,
                    "material_mapping": row.material_mapping,
                    "description": row.description,
                    "tags": row.tags,
                    "estimated_duration": row.estimated_duration,
                    "word_count": row.word_count,
                    "material_count": row.material_count,
                    "generation_prompt": row.generation_prompt,
                    "ai_response": row.ai_response,
                    "error_message": row.error_message,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "generated_at": row.generated_at,
                }
            return None
    except Exception as e:
        logger.error(f"根据脚本ID获取脚本内容失败: {str(e)}")
        return None


async def update_script_content(script_id: str, update_data: dict) -> Optional[dict]:
    """更新脚本内容"""
    try:
        async with get_db_session() as session:
            update_values = {**update_data, "updated_at": datetime.utcnow()}
            if (
                "generation_status" in update_data
                and update_data["generation_status"] == "completed"
            ):
                update_values["generated_at"] = datetime.utcnow()

            stmt = (
                update(ScriptContentTable)
                .where(ScriptContentTable.id == script_id)
                .values(**update_values)
            )
            result = await session.execute(stmt)

            if result.rowcount == 0:
                return None

            # 返回更新后的脚本内容
            updated_result = await session.execute(
                select(ScriptContentTable).where(ScriptContentTable.id == script_id)
            )
            row = updated_result.scalar_one_or_none()
            if row:
                return {
                    "id": str(row.id),
                    "task_id": str(row.task_id),
                    "persona_id": str(row.persona_id) if row.persona_id else None,
                    "script_style": row.script_style,
                    "generation_status": row.generation_status,
                    "titles": row.titles,
                    "narration": row.narration,
                    "material_mapping": row.material_mapping,
                    "description": row.description,
                    "tags": row.tags,
                    "estimated_duration": row.estimated_duration,
                    "word_count": row.word_count,
                    "material_count": row.material_count,
                    "generation_prompt": row.generation_prompt,
                    "ai_response": row.ai_response,
                    "error_message": row.error_message,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "generated_at": row.generated_at,
                }
            return None
    except Exception as e:
        logger.error(f"更新脚本内容失败: {str(e)}")
        return None


# 子视频任务相关操作 - 已移除
# 注意：SubVideoTask 功能已完全移除,主任务直接管理视频生成


# 数据初始化
async def init_preset_data():
    """初始化预设数据"""
    try:
        logger.info("开始初始化预设数据...")

        # 检查是否已有预设人设
        existing_personas = await get_preset_personas()
        if len(existing_personas) > 0:
            logger.info("预设数据已存在，跳过初始化")
            return

        # 创建预设人设
        preset_personas = [
            {
                "name": "知识科普博主",
                "persona_type": "educator",
                "style": "专业严谨",
                "target_audience": "求知者",
                "characteristics": "逻辑清晰，表达准确，善于将复杂概念简化",
                "tone": "专业而亲和",
                "keywords": "知识,科普,学习,教育",
                "custom_prompts": {
                    "intro": "作为一名知识科普博主，我致力于将复杂的知识用简单易懂的方式传达给大家...",
                    "style": "请用专业但通俗易懂的语言，确保内容准确性...",
                },
                "is_preset": True,
            },
            {
                "name": "生活方式达人",
                "persona_type": "lifestyle",
                "style": "轻松愉快",
                "target_audience": "生活爱好者",
                "characteristics": "热爱生活，善于分享实用技巧和美好体验",
                "tone": "亲切友好",
                "keywords": "生活,技巧,分享,体验",
                "custom_prompts": {
                    "intro": "大家好！我是你们的生活方式达人，今天要和大家分享...",
                    "style": "用轻松愉快的语调，分享实用的生活技巧...",
                },
                "is_preset": True,
            },
            {
                "name": "商业分析师",
                "persona_type": "business",
                "style": "数据驱动",
                "target_audience": "商业人士",
                "characteristics": "善于数据分析，洞察商业趋势，提供专业见解",
                "tone": "专业权威",
                "keywords": "商业,分析,数据,趋势",
                "custom_prompts": {
                    "intro": "从商业分析的角度来看...",
                    "style": "请用数据和事实支撑观点，提供专业的商业分析...",
                },
                "is_preset": True,
            },
        ]

        for persona_data in preset_personas:
            await create_persona(persona_data)

        # 创建预设提示词模板
        preset_templates = [
            {
                "template_key": "script_generation_base",
                "template_content": """基于提供的素材，创建一个引人入胜的视频脚本。

素材信息：
{material_info}

要求：
1. 创建吸引人的标题（3-5个选择）
2. 编写流畅的旁白内容
3. 合理安排素材使用顺序
4. 估算视频时长
5. 添加相关标签

请确保内容：
- 符合目标受众需求
- 逻辑清晰，结构完整
- 语言生动，富有吸引力
- 适合视频媒体特点""",
                "description": "基础脚本生成模板",
                "category": "script",
            },
            {
                "template_key": "material_analysis_base",
                "template_content": """请分析这个素材文件：

文件类型：{file_type}
文件信息：{file_info}

请提供：
1. 详细的内容描述
2. 识别的关键对象/元素
3. 情感基调分析
4. 视觉风格评估
5. 质量评分（1-10分）
6. 使用建议

分析要准确、客观，为后续脚本生成提供有价值的信息。""",
                "description": "基础素材分析模板",
                "category": "analysis",
            },
        ]

        for template_data in preset_templates:
            await create_prompt_template(template_data)

        logger.info("预设数据初始化完成")

    except Exception as e:
        logger.error(f"初始化预设数据失败: {e}")
