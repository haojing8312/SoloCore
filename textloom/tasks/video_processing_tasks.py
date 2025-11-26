"""
Celery任务模块 - 视频处理相关任务
将原有的APScheduler后台任务重构为Celery分布式任务
使用同步数据库连接，完全独立于FastAPI的异步数据库
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from celery import Task
from celery.exceptions import Retry

from celery_config import celery_app
from models.celery_db import (
    close_sync_connection_pool,
    sync_check_database_health,
    sync_get_task_by_id,
    sync_update_task_status,
    sync_update_task_with_results,
)
from models.task import TaskStatus
from utils.task_validation import validate_task_exists, log_task_consistency_info

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """带回调和状态更新的任务基类"""

    def on_success(self, retval, task_id, args, kwargs):
        """任务成功完成回调"""
        # 检查是否是跳过的任务
        if isinstance(retval, dict) and retval.get('status') == 'skipped':
            logger.info(f"Task {task_id} was skipped: {retval.get('reason', 'unknown')}")
        else:
            logger.info(f"Task {task_id} completed successfully: {retval}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败回调"""
        try:
            # 检查是否是Ignore异常（任务被跳过）
            from celery.exceptions import Ignore
            if isinstance(exc, Ignore):
                logger.info(f"Task {task_id} was ignored (skipped)")
                return
            
            logger.error(f"Task {task_id} failed with error: {exc}")
            logger.error(f"Traceback: {einfo}")
            # 尝试更新数据库中的任务状态为失败
            if args and len(args) > 0:
                task_db_id = args[0]
                sync_update_task_status(
                    task_db_id,
                    TaskStatus.FAILED,
                    {
                        "error_message": str(exc),
                        "error_traceback": str(einfo),
                        "completed_at": datetime.utcnow(),
                    },
                )
        except Exception as callback_exc:
            logger.error(f"Error in on_failure callback: {callback_exc}")
            # 确保不会因为回调错误而导致更严重的问题

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """任务重试回调"""
        try:
            logger.warning(f"Task {task_id} is being retried due to: {exc}")
            # 更新重试次数
            if args and len(args) > 0:
                task_db_id = args[0]
                task_info = sync_get_task_by_id(task_db_id)
                if task_info:
                    retry_count = task_info.get("retry_count", 0) + 1
                    sync_update_task_status(
                        task_db_id, TaskStatus.PROCESSING, {"retry_count": retry_count}
                    )
        except Exception as callback_exc:
            logger.error(f"Error in on_retry callback: {callback_exc}")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    queue="video_processing",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    time_limit=3600,  # 1小时超时
    soft_time_limit=3300,  # 55分钟软超时
)
@validate_task_exists
def process_text_to_video(
    self,
    task_id: str,
    source_file: str,
    workspace_dir: str,
    mode: str = "multi_scene",
    persona_id: Optional[int] = None,
    multi_video_count: int = 1,
):
    """
    处理文本转视频的完整流程

    Args:
        task_id: 数据库中的任务ID
        source_file: 源文件路径
        workspace_dir: 工作目录
        mode: 处理模式 (multi_scene/single_scene)
        persona_id: 人设ID
        multi_video_count: 多视频生成数量
    """
    try:
        task_start_time = datetime.utcnow()
        logger.info(f"🚀 开始文本转视频任务 - 任务ID: {task_id}")
        logger.info(
            f"任务参数:\n"
            f"  • 源文件: {source_file}\n"
            f"  • 工作目录: {workspace_dir}\n"
            f"  • 模式: {mode}\n"
            f"  • 人设id: {persona_id}\n"
            f"  • 多视频数: {multi_video_count}\n"
            f"  • Worker: {self.request.hostname}\n"
            f"  • Celery任务ID: {self.request.id}"
        )

        # 更新任务状态为处理中
        self.update_state(
            state="PROCESSING",
            meta={
                "progress": 0,
                "stage": "initialization",
                "message": "Starting task processing...",
                "worker_name": self.request.hostname,
            },
        )

        # 更新数据库中的任务状态（使用同步方法）
        sync_update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            {
                "celery_task_id": self.request.id,
                "worker_name": self.request.hostname,
                "started_at": datetime.utcnow(),
            },
        )

        # 设置进度回调函数
        def progress_callback(progress: int, stage: str, message: str):
            callback_start = datetime.utcnow()
            self.update_state(
                state="PROCESSING",
                meta={
                    "progress": progress,
                    "stage": stage,
                    "message": message,
                    "worker_name": self.request.hostname,
                },
            )
            # 同时更新数据库中的进度
            sync_update_task_status(
                task_id, TaskStatus.PROCESSING, {"progress": progress}
            )
            callback_duration = (datetime.utcnow() - callback_start).total_seconds()
            logger.debug(
                f"进度更新 - {progress}% | {stage} | {message} (耗时: {callback_duration:.3f}s)"
            )

        # 直接使用同步方式处理任务
        # 注意：这里需要使用同步版本的任务处理器
        logger.info(f"初始化同步任务处理器 - workspace: {workspace_dir}")
        processor_start_time = datetime.utcnow()

        from services.sync_task_processor import SyncTaskProcessor

        processor = SyncTaskProcessor(workspace_dir)
        processor_init_duration = (
            datetime.utcnow() - processor_start_time
        ).total_seconds()
        logger.debug(f"任务处理器初始化完成 - 耗时: {processor_init_duration:.3f}s")

        # 执行任务处理
        logger.info(f"开始执行任务处理 - 任务ID: {task_id}")
        processing_start_time = datetime.utcnow()

        result = processor.process_text_to_video_task(
            task_id=task_id,
            source_file=source_file,
            workspace_dir=workspace_dir,
            mode=mode,
            persona_id=persona_id,
            multi_video_count=multi_video_count,
            progress_callback=progress_callback,
        )

        processing_duration = (
            datetime.utcnow() - processing_start_time
        ).total_seconds()
        logger.info(f"任务处理完成 - 耗时: {processing_duration:.2f}s")

        # 根据处理器返回结果的状态更新数据库中的任务状态
        db_update_start = datetime.utcnow()
        final_status = result.get("status") if isinstance(result, dict) else None
        if final_status in (TaskStatus.COMPLETED, "completed"):
            sync_update_task_status(
                task_id, TaskStatus.COMPLETED, {"completed_at": datetime.utcnow()}
            )
        elif final_status in (TaskStatus.PARTIAL_SUCCESS, "partial_success"):
            sync_update_task_status(
                task_id, TaskStatus.PARTIAL_SUCCESS, {"completed_at": datetime.utcnow()}
            )
        elif final_status in (TaskStatus.PROCESSING, "processing"):
            # 仍在进行中：保持processing，由轮询任务收敛到最终态
            sync_update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                "子视频任务进行中，等待合成结果轮询收敛",  # description参数
            )
        elif final_status in (TaskStatus.FAILED, "failed"):
            sync_update_task_status(
                task_id, TaskStatus.FAILED, {"completed_at": datetime.utcnow()}
            )
        else:
            # 不明状态，保持当前状态，仅写入结果
            logger.warning(f"未知的最终状态: {final_status}, 保持当前数据库状态")

        # 写入详细结果
        if result:
            sync_update_task_with_results(task_id, result)

        db_update_duration = (datetime.utcnow() - db_update_start).total_seconds()
        total_task_duration = (datetime.utcnow() - task_start_time).total_seconds()

        logger.info(
            f"✅ Celery任务完成 - 任务ID: {task_id}\n"
            f"  • 总耗时: {total_task_duration:.2f}s\n"
            f"  • 处理器耗时: {processing_duration:.2f}s\n"
            f"  • 数据库更新耗时: {db_update_duration:.3f}s\n"
            f"  • 结果数据: {len(str(result)) if result else 0} bytes\n"
            f"  • Worker: {self.request.hostname}\n"
            f"  • Celery任务ID: {self.request.id}"
        )
        return result

    except Exception as exc:
        task_duration = (datetime.utcnow() - task_start_time).total_seconds()
        error_msg = str(exc)
        error_traceback = traceback.format_exc()

        logger.error(
            f"❌ Celery任务失败 - 任务ID: {task_id}\n"
            f"  • 总耗时: {task_duration:.2f}s\n"
            f"  • 错误信息: {error_msg}\n"
            f"  • 错误类型: {type(exc).__name__}\n"
            f"  • Worker: {self.request.hostname}\n"
            f"  • Celery任务ID: {self.request.id}"
        )
        logger.debug(f"详细错误堆栈: {error_traceback}")

        # 更新任务状态为失败
        self.update_state(
            state="FAILURE",
            meta={
                "error": error_msg,
                "traceback": error_traceback,
                "worker_name": self.request.hostname,
            },
        )

        # 更新任务状态为失败
        try:
            db_update_start = datetime.utcnow()
            sync_update_task_status(
                task_id,
                TaskStatus.FAILED,
                {
                    "error_message": error_msg,
                    "error_traceback": error_traceback,
                    "error_type": type(exc).__name__,
                    "failed_duration": f"{task_duration:.2f}s",
                    "completed_at": datetime.utcnow(),
                },
            )
            db_update_duration = (datetime.utcnow() - db_update_start).total_seconds()
            logger.debug(f"数据库错误状态更新完成 - 耗时: {db_update_duration:.3f}s")
        except Exception as db_error:
            logger.error(f"更新任务失败状态时出错: {db_error}")

        raise exc


@celery_app.task(
    bind=True,
    base=CallbackTask,
    queue="video_generation",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
    time_limit=1800,  # 30分钟超时
    soft_time_limit=1500,  # 25分钟软超时
)
@validate_task_exists
def process_video_generation(
    self,
    task_id: str,
    script_data: Dict[str, Any],
    workspace_dir: str,
    video_index: int = 0,
):
    """
    处理视频生成任务

    Args:
        task_id: 任务ID
        script_data: 脚本数据
        workspace_dir: 工作目录
        video_index: 视频索引（用于多视频生成）
    """
    try:
        logger.info(
            f"Starting video generation for task {task_id}, video index {video_index}"
        )

        # 更新任务状态
        self.update_state(
            state="PROCESSING",
            meta={
                "progress": 75,
                "stage": "video_generation",
                "message": f"Generating video {video_index + 1}...",
                "worker_name": self.request.hostname,
            },
        )

        # 使用同步版本的视频生成器
        from services.sync_video_generator import SyncVideoGenerator

        generator = SyncVideoGenerator()

        # 执行视频生成
        result = generator.generate_video(
            task_id=task_id,
            script_data=script_data,
            workspace_dir=workspace_dir,
            video_index=video_index,
        )

        logger.info(
            f"Video generation completed for task {task_id}, video {video_index}"
        )
        return result

    except Exception as exc:
        error_msg = str(exc)
        error_traceback = traceback.format_exc()

        logger.error(f"Video generation task {task_id} failed: {error_msg}")
        logger.error(f"Traceback: {error_traceback}")

        self.update_state(
            state="FAILURE",
            meta={
                "error": error_msg,
                "traceback": error_traceback,
                "worker_name": self.request.hostname,
            },
        )

        raise exc


@celery_app.task(bind=True, queue="maintenance")
def cleanup_expired_tasks(self):
    """清理过期任务的定期维护任务"""
    try:
        logger.info("Starting cleanup of expired tasks")

        from utils.redis_cleanup import cleanup_redis_tasks

        # 执行Redis任务清理
        cleanup_result = cleanup_redis_tasks(force=False, max_age_hours=24)
        
        logger.info(f"Redis清理完成: {cleanup_result}")

        # 清理数据库连接池（可选）
        # close_sync_connection_pool()

        return {
            "status": "completed", 
            "message": "Cleanup tasks completed",
            "redis_cleanup": cleanup_result
        }

    except Exception as exc:
        logger.error(f"Cleanup task failed: {exc}")
        raise


@celery_app.task(bind=True, queue="monitoring")
def health_check(self):
    """健康检查任务"""
    try:
        # 检查数据库连接（使用同步方法）
        db_health = sync_check_database_health()
        db_status = db_health.get("status", "unhealthy")

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_status,
            "worker": self.request.hostname,
        }

    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        return {
            "status": "unhealthy",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        }
