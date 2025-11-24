"""
动态字幕相关的Celery任务 - 基于PyCaps
"""

import traceback
from typing import Any, Dict

from celery import current_task

from celery_config import celery_app
from models.celery_db import (
    get_sync_db_connection,
    sync_update_sub_video_task,
    sync_update_task_multi_video_results_and_count,
    sync_update_task_status,
    sync_update_task_stage,
)
from services.pycaps_subtitle_service import PyCapsSubtitleService
from utils.sync_logging import get_logger
from utils.task_validation import validate_sub_task_exists

logger = get_logger("pycaps_subtitle_tasks")


def _fetch_sub_tasks_by_parent(parent_task_id: str) -> list[Dict[str, Any]]:
    """获取父任务下所有子任务的状态信息"""
    with get_sync_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT sub_task_id, status, video_url, thumbnail_url, duration, course_media_id, error_message
                FROM textloom_core.sub_video_tasks
                WHERE parent_task_id = %s
                ORDER BY created_at ASC
                """,
                (parent_task_id,),
            )
            rows = cursor.fetchall() or []
            result = []
            for r in rows:
                result.append(
                    {
                        "sub_task_id": r[0],
                        "status": r[1],
                        "video_url": r[2],
                        "thumbnail_url": r[3],
                        "duration": r[4],
                        "course_media_id": r[5],
                        "error": r[6],
                    }
                )
            return result


def _all_sub_tasks_terminal(sub_tasks: list[Dict[str, Any]]) -> bool:
    """检查所有子任务是否都到达终态"""
    return all(t.get("status") in ("completed", "failed", "error") for t in sub_tasks)


def _build_multi_video_results(sub_tasks: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """构建多视频结果数据"""
    from datetime import datetime
    
    results = []
    for idx, t in enumerate(sub_tasks):
        results.append(
            {
                "sub_task_id": t.get("sub_task_id"),
                "sub_task_index": idx + 1,
                "script_style": None,
                "success": t.get("status") == "completed",
                "video_url": t.get("video_url"),
                "thumbnail_url": t.get("thumbnail_url"),
                "duration": t.get("duration"),
                "course_media_id": t.get("course_media_id"),
                "error": t.get("error"),
                "generated_at": datetime.utcnow().isoformat(),
            }
        )
    return results


def _get_parent_task_id(sub_task_id: str) -> str:
    """通过子任务ID获取父任务ID"""
    with get_sync_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT parent_task_id FROM textloom_core.sub_video_tasks WHERE sub_task_id = %s",
                (sub_task_id,),
            )
            result = cursor.fetchone()
            return str(result[0]) if result else None


def _check_and_update_parent_task_status(sub_task_id: str):
    """检查并更新父任务状态"""
    try:
        # 获取父任务ID
        parent_task_id = _get_parent_task_id(sub_task_id)
        if not parent_task_id:
            logger.warning(f"无法获取子任务 {sub_task_id} 的父任务ID")
            return

        # 获取所有子任务状态
        sub_tasks = _fetch_sub_tasks_by_parent(parent_task_id)
        
        if not sub_tasks:
            logger.warning(f"父任务 {parent_task_id} 下没有子任务")
            return

        # 检查是否所有子任务都到达终态
        if _all_sub_tasks_terminal(sub_tasks):
            logger.info(f"父任务 {parent_task_id} 所有子任务已完成，开始收敛状态")
            
            # 构建多视频结果
            multi_video_results = _build_multi_video_results(sub_tasks)
            completed_count = sum(1 for t in sub_tasks if t.get("status") == "completed")
            
            # 更新父任务的多视频结果和完成数量
            sync_update_task_multi_video_results_and_count(
                parent_task_id, multi_video_results, completed_count
            )
            
            # 设置父任务最终状态
            total = len(sub_tasks)
            if completed_count == total and total > 0:
                # 所有子任务都成功
                sync_update_task_status(parent_task_id, "completed", "所有子视频任务已完成")
                sync_update_task_stage(parent_task_id, "completed")
                logger.info(f"父任务 {parent_task_id} 状态更新为 completed")
            elif completed_count > 0:
                # 部分成功
                sync_update_task_status(parent_task_id, "partial_success", "子任务部分成功，部分失败")
                sync_update_task_stage(parent_task_id, "completed")
                logger.info(f"父任务 {parent_task_id} 状态更新为 partial_success")
            else:
                # 全部失败
                sync_update_task_status(parent_task_id, "failed", "所有子视频任务失败")
                sync_update_task_stage(parent_task_id, "failed")
                logger.info(f"父任务 {parent_task_id} 状态更新为 failed")
        else:
            logger.debug(f"父任务 {parent_task_id} 仍有子任务未完成，状态: {[t.get('status') for t in sub_tasks]}")
            
    except Exception as e:
        logger.error(f"检查父任务状态时出错 - sub_task_id={sub_task_id}, error={e}", exc_info=True)


@celery_app.task(bind=True)
def process_pycaps_subtitles_task(
    self,
    sub_task_id: str,
    video_url: str,
    subtitles_url: str,
    template: str,
):
    """
    Celery任务：为视频添加PyCaps动态字幕

    Args:
        sub_task_id: 子任务ID
        video_url: 原视频URL
        subtitles_url: 字幕文件URL (.srt格式)
        template: PyCaps模板名称 (hype, minimalist, explosive等)
    """
    task_id = self.request.id
    logger.info(f"开始PyCaps字幕处理任务 - TaskID: {task_id}, SubTaskID: {sub_task_id}")
    logger.info(
        f"参数: video_url={video_url}, subtitles_url={subtitles_url}, template={template}"
    )

    try:
        # 更新子任务状态
        update_result = sync_update_sub_video_task(
            sub_task_id,
            {
                "status": "processing_subtitles",
                "progress": 85,  # 视频生成完成后的字幕处理阶段
            },
        )
        logger.info(
            f"子任务状态更新为 processing_subtitles - SubTaskID: {sub_task_id}, 更新结果: {update_result}"
        )

        # 初始化PyCaps字幕服务
        subtitle_service = PyCapsSubtitleService()

        # 处理动态字幕
        result = subtitle_service.process_video_subtitles(
            video_url=video_url,
            subtitles_url=subtitles_url,
            template=template,
            task_id=sub_task_id,
        )

        if result["success"]:
            if result.get("processed"):
                # 字幕处理成功，更新视频URL
                logger.info(f"PyCaps字幕处理成功 - SubTaskID: {sub_task_id}")
                update_result = sync_update_sub_video_task(
                    sub_task_id,
                    {
                        "status": "completed",
                        "progress": 100,
                        "video_url": result["video_url"],
                    },
                )
                logger.info(
                    f"子任务状态更新为 completed - SubTaskID: {sub_task_id}, 新视频URL: {result['video_url']}, 更新结果: {update_result}"
                )

                # 检查父任务是否可收敛
                _check_and_update_parent_task_status(sub_task_id)

                return {
                    "success": True,
                    "video_url": result["video_url"],
                    "original_video_url": result.get("original_video_url"),
                    "template": template,
                    "processed": True,
                    "message": "PyCaps字幕处理成功",
                }
            else:
                # 跳过处理（功能禁用或不可用）
                logger.info(
                    f"PyCaps字幕处理跳过 - SubTaskID: {sub_task_id}, 原因: {result.get('message')}"
                )
                update_result = sync_update_sub_video_task(
                    sub_task_id,
                    {
                        "status": "completed",
                        "progress": 100,
                        "video_url": video_url,  # Preserve original video URL when skipping
                    },
                )
                logger.info(
                    f"子任务状态更新为 completed (跳过处理) - SubTaskID: {sub_task_id}, 更新结果: {update_result}"
                )

                # 检查父任务是否可收敛
                _check_and_update_parent_task_status(sub_task_id)

                return {
                    "success": True,
                    "video_url": video_url,
                    "template": template,
                    "processed": False,
                    "message": result.get("message", "跳过PyCaps字幕处理"),
                }
        else:
            # 处理失败
            error_msg = result.get("error", "PyCaps字幕处理失败")
            logger.error(
                f"PyCaps字幕处理失败 - SubTaskID: {sub_task_id}, 错误: {error_msg}"
            )

            # 标记为失败，因为字幕生成失败就是任务失败
            sync_update_sub_video_task(
                sub_task_id,
                {
                    "status": "failed",
                    "progress": 100,
                    "video_url": video_url,  # Preserve original video URL when failing
                    "error_message": f"PyCaps字幕处理失败: {error_msg}",
                },
            )

            # 检查父任务是否可收敛
            _check_and_update_parent_task_status(sub_task_id)

            return {
                "success": False,  # 返回失败，因为字幕处理失败
                "video_url": video_url,
                "template": template,
                "processed": False,
                "error": error_msg,
                "message": "PyCaps字幕处理失败",
            }

    except Exception as e:
        error_msg = f"PyCaps字幕任务异常: {str(e)}"
        error_trace = traceback.format_exc()

        logger.error(f"{error_msg}\n{error_trace}")

        # 更新子任务错误状态
        sync_update_sub_video_task(
            sub_task_id,
            {
                "status": "failed",  # 标记失败，因为异常就是失败
                "progress": 100,
                "video_url": video_url,  # Preserve original video URL when exception occurs
                "error_message": error_msg,
            },
        )

        # 检查父任务是否可收敛
        _check_and_update_parent_task_status(sub_task_id)

        # 返回失败状态
        return {
            "success": False,
            "video_url": video_url,
            "template": template,
            "processed": False,
            "error": error_msg,
            "message": "PyCaps字幕任务异常",
        }


@celery_app.task(bind=True)
def batch_process_pycaps_subtitles_task(
    self,
    sub_task_results: list[Dict[str, Any]],
    template: str,
):
    """
    批量处理多个视频的PyCaps字幕

    Args:
        sub_task_results: 子任务结果列表，每个包含sub_task_id、video_url、subtitles_url等
        template: 统一的PyCaps模板名称
    """
    task_id = self.request.id
    logger.info(
        f"开始批量PyCaps字幕处理 - TaskID: {task_id}, 数量: {len(sub_task_results)}, 模板: {template}"
    )

    processed_results = []

    try:
        subtitle_service = PyCapsSubtitleService()

        for sub_result in sub_task_results:
            sub_task_id = sub_result.get("sub_task_id")
            video_url = sub_result.get("video_url")
            subtitles_url = sub_result.get("subtitles_url")

            if not sub_task_id or not video_url or not subtitles_url:
                logger.warning(f"跳过无效的子任务结果: {sub_result}")
                processed_results.append(
                    {
                        "sub_task_id": sub_task_id,
                        "success": False,
                        "error": "缺少必要参数 (video_url, subtitles_url)",
                    }
                )
                continue

            try:
                # 处理单个视频的PyCaps字幕
                result = subtitle_service.process_video_subtitles(
                    video_url=video_url,
                    subtitles_url=subtitles_url,
                    template=template,
                    task_id=sub_task_id,
                )

                # 更新子任务
                if result["success"] and result.get("processed"):
                    sync_update_sub_video_task(
                        sub_task_id,
                        {
                            "video_url": result["video_url"],
                        },
                    )
                elif result["success"] and not result.get("processed"):
                    # 如果处理被跳过但成功，确保保留原视频URL
                    sync_update_sub_video_task(
                        sub_task_id,
                        {
                            "status": "completed",
                            "progress": 100,
                            "video_url": video_url,  # Preserve original video URL
                        },
                    )
                else:
                    # 如果处理失败，标记为失败状态
                    sync_update_sub_video_task(
                        sub_task_id,
                        {
                            "status": "failed",
                            "progress": 100,
                            "video_url": video_url,  # Preserve original video URL
                            "error_message": result.get("error", "PyCaps字幕处理失败"),
                        },
                    )

                processed_results.append(
                    {
                        "sub_task_id": sub_task_id,
                        "success": result["success"],
                        "video_url": result.get("video_url", video_url),
                        "template": template,
                        "processed": result.get("processed", False),
                        "message": result.get("message", ""),
                        "error": result.get("error"),
                    }
                )

            except Exception as e:
                error_msg = f"子任务 {sub_task_id} PyCaps字幕处理异常: {str(e)}"
                logger.error(error_msg)

                # 确保即使异常也更新子任务状态并保留原视频URL
                try:
                    sync_update_sub_video_task(
                        sub_task_id,
                        {
                            "status": "failed",  # 异常就是失败
                            "progress": 100,
                            "video_url": video_url,  # Preserve original video URL
                            "error_message": error_msg,
                        },
                    )
                except Exception as update_e:
                    logger.error(f"批量处理中更新子任务状态失败: {update_e}")

                processed_results.append(
                    {
                        "sub_task_id": sub_task_id,
                        "success": False,
                        "video_url": video_url,
                        "template": template,
                        "processed": False,
                        "error": error_msg,
                    }
                )

        success_count = sum(1 for r in processed_results if r["success"])
        processed_count = sum(1 for r in processed_results if r.get("processed"))

        logger.info(
            f"批量PyCaps字幕处理完成 - 成功: {success_count}/{len(processed_results)}, 实际处理: {processed_count}"
        )

        return {
            "success": True,
            "total": len(processed_results),
            "success_count": success_count,
            "processed_count": processed_count,
            "template": template,
            "results": processed_results,
        }

    except Exception as e:
        error_msg = f"批量PyCaps字幕处理异常: {str(e)}"
        error_trace = traceback.format_exc()
        logger.error(f"{error_msg}\n{error_trace}")

        return {
            "success": False,
            "error": error_msg,
            "template": template,
            "results": processed_results,
        }
