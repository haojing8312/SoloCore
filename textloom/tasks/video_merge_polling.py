"""
视频合成结果轮询任务（Celery Beat）
- 周期性查询 sub_video_tasks 中 status=processing 的记录
- 调用与异步版一致的查询接口，更新子任务状态/结果
- 当同一 parent_task_id 的子任务全部到达终态，汇总并更新主任务
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from celery_config import celery_app
from config import settings
from models.celery_db import (
    get_sync_db_connection,
    sync_mark_sub_video_task_failed,
    sync_update_sub_video_task,
    sync_update_task_multi_video_results,
    sync_update_task_multi_video_results_and_count,
    sync_update_task_status,
)
from services.sync_video_generator import SyncVideoGenerator

logger = logging.getLogger(__name__)


def _get_sub_task_status(sub_task_id: str) -> str:
    """获取子任务当前状态"""
    with get_sync_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT status FROM textloom_core.sub_video_tasks WHERE sub_task_id = %s",
                (sub_task_id,),
            )
            result = cursor.fetchone()
            return result[0] if result else "unknown"


def _fetch_processing_sub_tasks(limit: int = 50) -> List[Dict[str, Any]]:
    """读取进行中的子视频任务。"""
    with get_sync_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT sub_task_id, parent_task_id, course_media_id, created_at, updated_at
                FROM textloom_core.sub_video_tasks
                WHERE status IN ('processing', 'processing_subtitles')
                ORDER BY updated_at ASC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall() or []
            result = [
                {
                    "sub_task_id": row[0],
                    "parent_task_id": str(row[1]),
                    "course_media_id": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                }
                for row in rows
            ]
            logger.info(
                "polling.fetch_processing_sub_tasks: fetched=%d limit=%d",
                len(result),
                limit,
            )
            return result


def _fetch_sub_tasks_by_parent(parent_task_id: str) -> List[Dict[str, Any]]:
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
            logger.debug(
                "polling.fetch_sub_tasks_by_parent: parent_task_id=%s count=%d statuses=%s",
                parent_task_id,
                len(result),
                [t.get("status") for t in result],
            )
            return result


def _all_sub_tasks_terminal(sub_tasks: List[Dict[str, Any]]) -> bool:
    terminal = all(
        t.get("status") in ("completed", "failed", "error") for t in sub_tasks
    )
    if not terminal:
        logger.debug(
            "polling.check_terminal: non_terminal_statuses=%s",
            [t.get("status") for t in sub_tasks],
        )
    return terminal


def _build_multi_video_results(sub_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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


@celery_app.task(
    name="tasks.video_merge_polling.poll_video_merge_results", queue="maintenance"
)
def poll_video_merge_results():
    generator = SyncVideoGenerator()
    limit = max(10, settings.max_concurrent_tasks)
    tasks = _fetch_processing_sub_tasks(limit=limit)
    logger.info(
        "polling.start: now=%s processing_tasks=%d limit=%d",
        datetime.utcnow().isoformat(),
        len(tasks),
        limit,
    )
    if not tasks:
        logger.info("polling.no_tasks: nothing_to_do")
        return {"polled": 0, "updated": 0}

    updated = 0
    parent_updates = 0
    errors = 0
    for item in tasks:
        sub_task_id = item["sub_task_id"]
        parent_task_id = item["parent_task_id"]
        cmid = item.get("course_media_id")
        logger.debug(
            "polling.task.loaded: sub_task_id=%s parent_task_id=%s course_media_id=%s created_at=%s updated_at=%s",
            sub_task_id,
            parent_task_id,
            cmid,
            item.get("created_at"),
            item.get("updated_at"),
        )

        # 检查任务状态
        current_status = _get_sub_task_status(sub_task_id)

        # 如果是字幕处理状态，检查是否超时
        if current_status == "processing_subtitles":
            # 检查字幕处理超时（默认10分钟）
            started_at = item.get("updated_at") or item.get("created_at")
            elapsed = (
                (datetime.utcnow() - started_at).total_seconds() if started_at else 0
            )
            subtitle_timeout = getattr(settings, 'dynamic_subtitle_timeout', 600)  # 10分钟
            
            if elapsed > subtitle_timeout:
                logger.info(
                    "polling.subtitle.timeout: sub_task_id=%s parent_task_id=%s elapsed=%.1fs threshold=%ss",
                    sub_task_id,
                    parent_task_id,
                    elapsed,
                    subtitle_timeout,
                )
                # 字幕处理超时，标记为完成但记录错误
                timeout_update = {
                    "status": "completed", 
                    "progress": 100,
                    "error_message": f"动态字幕处理超时 ({elapsed:.1f}s > {subtitle_timeout}s)"
                }
                try:
                    if sync_update_sub_video_task(sub_task_id, timeout_update):
                        logger.info(
                            "polling.subtitle.timeout_updated: sub_task_id=%s update=%s",
                            sub_task_id,
                            timeout_update,
                        )
                        updated += 1
                    else:
                        logger.warning(
                            "polling.subtitle.timeout_update_failed: sub_task_id=%s update=%s",
                            sub_task_id,
                            timeout_update,
                        )
                except Exception as e:
                    logger.error(
                        "字幕超时状态更新异常 - sub_task_id=%s, error=%s",
                        sub_task_id,
                        e,
                    )
                continue
            else:
                logger.debug(
                    "polling.task.skip_subtitles: sub_task_id=%s parent_task_id=%s elapsed=%.1fs",
                    sub_task_id,
                    parent_task_id,
                    elapsed,
                )
                continue

        if not cmid:
            logger.warning(
                "polling.task.skip_no_cmid: sub_task_id=%s parent_task_id=%s",
                sub_task_id,
                parent_task_id,
            )
            continue

        # 超时判断（默认30分钟，可通过 settings.multi_video_generation_timeout 配置）
        try:
            started_at = item.get("updated_at") or item.get("created_at")
            elapsed = (
                (datetime.utcnow() - started_at).total_seconds() if started_at else 0
            )
            if elapsed > settings.multi_video_generation_timeout:
                logger.info(
                    "polling.task.timeout: sub_task_id=%s parent_task_id=%s elapsed=%.1fs threshold=%ss",
                    sub_task_id,
                    parent_task_id,
                    elapsed,
                    settings.multi_video_generation_timeout,
                )
                timeout_update = {"status": "failed", "error_message": "生成超时"}
                try:
                    if sync_update_sub_video_task(sub_task_id, timeout_update):
                        logger.info(
                            "polling.sub_task.updated: sub_task_id=%s update=%s",
                            sub_task_id,
                            timeout_update,
                        )
                        updated += 1
                    else:
                        logger.warning(
                            "polling.sub_task.update_failed: sub_task_id=%s update=%s",
                            sub_task_id,
                            timeout_update,
                        )
                except Exception as e:
                    logger.error(
                        "超时失败状态写入异常 - sub_task_id=%s, error=%s. 将回写为失败状态。",
                        sub_task_id,
                        e,
                    )
                    try:
                        sync_mark_sub_video_task_failed(
                            sub_task_id, "生成超时且写入异常"
                        )
                        updated += 1
                    except Exception:
                        logger.exception(
                            "超时失败状态回退写仍出错 - sub_task_id=%s",
                            sub_task_id,
                        )
                # 超时后也尝试父任务收敛
                sub_tasks = _fetch_sub_tasks_by_parent(parent_task_id)
                if _all_sub_tasks_terminal(sub_tasks):
                    multi_video_results = _build_multi_video_results(sub_tasks)
                    completed_count = sum(
                        1 for t in sub_tasks if t.get("status") == "completed"
                    )
                    ok_results = sync_update_task_multi_video_results_and_count(
                        parent_task_id, multi_video_results, completed_count
                    )
                    logger.info(
                        "polling.parent.multi_video_results: parent_task_id=%s count=%d completed=%d ok=%s",
                        parent_task_id,
                        len(multi_video_results),
                        completed_count,
                        ok_results,
                    )
                    total = len(sub_tasks)
                    if completed_count == total and total > 0:
                        ok = sync_update_task_status(
                            parent_task_id, "completed", "所有子视频任务已完成"
                        )
                        logger.info(
                            "polling.parent.status: parent_task_id=%s status=%s ok=%s",
                            parent_task_id,
                            "completed",
                            ok,
                        )
                    elif completed_count > 0:
                        ok = sync_update_task_status(
                            parent_task_id,
                            "partial_success",
                            "子任务部分成功，部分超时/失败",
                        )
                        logger.info(
                            "polling.parent.status: parent_task_id=%s status=%s ok=%s reason=%s",
                            parent_task_id,
                            "partial_success",
                            ok,
                            "部分成功",
                        )
                    else:
                        ok = sync_update_task_status(
                            parent_task_id, "failed", "所有子视频任务失败"
                        )
                        logger.info(
                            "polling.parent.status: parent_task_id=%s status=%s ok=%s",
                            parent_task_id,
                            "failed",
                            ok,
                        )
                    parent_updates += 1
                continue
        except Exception as e:
            errors += 1
            logger.exception(
                "polling.task.timeout_check_error: sub_task_id=%s parent_task_id=%s error=%s",
                sub_task_id,
                parent_task_id,
                e,
            )

        try:
            result = generator._check_merge_result_sync(cmid)
        except Exception as e:
            errors += 1
            logger.exception(
                "polling.task.query_error: sub_task_id=%s parent_task_id=%s cmid=%s error=%s",
                sub_task_id,
                parent_task_id,
                cmid,
                e,
            )
            continue
        if not result:
            logger.debug(
                "polling.task.query_empty: sub_task_id=%s parent_task_id=%s cmid=%s",
                sub_task_id,
                parent_task_id,
                cmid,
            )
            continue

        # status: 2=success, 3=failed（按异步版约定）
        if result.status in [2, 3]:
            update = {"updated_at": datetime.utcnow()}
            if result.status == 2 and result.merge_video:
                # 检查是否启用动态字幕处理
                if settings.dynamic_subtitle_enabled:
                    # 先更新为字幕处理中状态
                    update.update(
                        {
                            "status": "processing_subtitles",
                            "video_url": result.merge_video,
                            "thumbnail_url": result.snapshot_url,
                            "duration": result.duration,
                        }
                    )
                else:
                    # 直接完成
                    update.update(
                        {
                            "status": "completed",
                            "video_url": result.merge_video,
                            "thumbnail_url": result.snapshot_url,
                            "duration": result.duration,
                        }
                    )
            else:
                update.update(
                    {
                        "status": "failed",
                        "error_message": result.failure_reasons or "视频合成失败",
                    }
                )
            logger.info(
                "polling.task.query_result: sub_task_id=%s parent_task_id=%s cmid=%s status=%s has_video=%s duration=%s",
                sub_task_id,
                parent_task_id,
                cmid,
                getattr(result, "status", None),
                bool(getattr(result, "merge_video", None)),
                getattr(result, "duration", None),
            )
            try:
                if sync_update_sub_video_task(sub_task_id, update):
                    logger.info(
                        "polling.sub_task.updated: sub_task_id=%s update=%s",
                        sub_task_id,
                        update,
                    )
                    updated += 1

                    # 如果启用了动态字幕且视频生成成功，触发动态字幕处理任务
                    if (
                        settings.dynamic_subtitle_enabled
                        and result.status == 2
                        and result.merge_video
                        and update.get("status") == "processing_subtitles"
                    ):
                        try:
                            from tasks.dynamic_subtitle_tasks import (
                                process_pycaps_subtitles_task,
                            )

                            # 异步触发动态字幕处理任务
                            task_result = process_pycaps_subtitles_task.delay(
                                sub_task_id=sub_task_id,
                                video_url=result.merge_video,
                                subtitles_url=getattr(result, "subtitles_url", None),
                                template="hype",  # 使用默认PyCaps模板
                            )

                            logger.info(
                                "polling.subtitle.triggered: sub_task_id=%s video_url=%s celery_task_id=%s",
                                sub_task_id,
                                result.merge_video,
                                task_result.id,
                            )
                        except Exception as e:
                            logger.error(
                                "polling.subtitle.trigger_failed: sub_task_id=%s error=%s",
                                sub_task_id,
                                str(e),
                            )
                            # 如果动态字幕任务触发失败，直接标记为已完成
                            fallback_update = {
                                "status": "completed",
                                "error_message": f"动态字幕任务触发失败: {str(e)}",
                            }
                            sync_update_sub_video_task(sub_task_id, fallback_update)
                else:
                    logger.warning(
                        "polling.sub_task.update_failed: sub_task_id=%s update=%s",
                        sub_task_id,
                        update,
                    )
            except Exception as e:
                # 任何 ORM 编译/执行异常，回退为失败并记录错误
                logger.error(
                    "更新子视频任务失败 - sub_task_id=%s, error=%s. 将回写为失败状态。",
                    sub_task_id,
                    e,
                )
                fallback_ok = False
                try:
                    # 拼接更友好的错误提示
                    err_msg = f"数据库更新异常: {str(e)[:200]}"
                    fallback_ok = sync_mark_sub_video_task_failed(sub_task_id, err_msg)
                except Exception as e2:
                    logger.exception(
                        "回退写失败状态时再次出错 - sub_task_id=%s error=%s",
                        sub_task_id,
                        e2,
                    )
                if fallback_ok:
                    updated += 1

            # 检查父任务是否可收敛
            sub_tasks = _fetch_sub_tasks_by_parent(parent_task_id)
            if _all_sub_tasks_terminal(sub_tasks):
                # 汇总并写入主任务（包含成功数量）
                multi_video_results = _build_multi_video_results(sub_tasks)
                completed_count = sum(
                    1 for t in sub_tasks if t.get("status") == "completed"
                )
                ok_results = sync_update_task_multi_video_results_and_count(
                    parent_task_id, multi_video_results, completed_count
                )
                logger.info(
                    "polling.parent.multi_video_results: parent_task_id=%s count=%d completed=%d ok=%s",
                    parent_task_id,
                    len(multi_video_results),
                    completed_count,
                    ok_results,
                )
                # 设置主任务最终状态
                total = len(sub_tasks)
                completed_count = sum(
                    1 for t in sub_tasks if t.get("status") == "completed"
                )
                if completed_count == total and total > 0:
                    ok = sync_update_task_status(
                        parent_task_id, "completed", "所有子视频任务已完成"
                    )
                    # 更新阶段为完成
                    from models.celery_db import sync_update_task_stage
                    sync_update_task_stage(parent_task_id, "completed")
                    logger.info(
                        "polling.parent.status: parent_task_id=%s status=%s ok=%s",
                        parent_task_id,
                        "completed",
                        ok,
                    )
                elif completed_count > 0:
                    ok = sync_update_task_status(
                        parent_task_id, "partial_success", "子任务部分成功，部分失败"
                    )
                    # 更新阶段为完成（部分成功也算完成）
                    from models.celery_db import sync_update_task_stage
                    sync_update_task_stage(parent_task_id, "completed")
                    logger.info(
                        "polling.parent.status: parent_task_id=%s status=%s ok=%s",
                        parent_task_id,
                        "partial_success",
                        ok,
                    )
                else:
                    ok = sync_update_task_status(
                        parent_task_id, "failed", "所有子视频任务失败"
                    )
                    # 更新阶段为失败
                    from models.celery_db import sync_update_task_stage
                    sync_update_task_stage(parent_task_id, "failed")
                    logger.info(
                        "polling.parent.status: parent_task_id=%s status=%s ok=%s",
                        parent_task_id,
                        "failed",
                        ok,
                    )
                parent_updates += 1

    logger.info(
        "polling.finish: polled=%d sub_updated=%d parent_updates=%d errors=%d",
        len(tasks),
        updated,
        parent_updates,
        errors,
    )
    return {"polled": len(tasks), "updated": updated}
