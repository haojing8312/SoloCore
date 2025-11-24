from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile

# 导入Celery相关模块
from celery_config import celery_app
from config import settings
from models import (
    MediaItem,
    Task,
    TaskCreate,
    TaskDetail,
    TaskStats,
    TaskStatus,
    TaskType,
    TaskUpdate,
)
from models.database import (
    create_task,
    delete_task,
    get_all_tasks,
    get_media_items_by_task_id,
    get_task_by_id,
    get_task_detail,
    get_task_stats,
    get_tasks_by_status,
    get_tasks_by_type,
    update_task,
)
from tasks.video_processing_tasks import process_text_to_video
from utils.enhanced_logging import (
    log_critical,
    log_debug,
    log_error,
    log_info,
    log_warning,
)
from utils.oss.storage_factory import StorageFactory
from utils.api_key_auth import require_api_key, optional_api_key

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create-video-task", response_model=Task)
async def create_video_task(
    current_user=Depends(require_api_key),
    media_urls: List[str] = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    mode: str = Form("multi_scene"),
    script_style: Optional[str] = Form("default"),
    persona_id: Optional[int] = Form(None),
    multi_video_count: int = Form(3),
    media_meta: Optional[str] = Form(None),
) -> Task:
    """
    创建文本转视频任务（多素材URL版） - 使用Celery异步处理
    步骤：
    1. 接收最多50个素材URL（支持 Markdown、图片、视频）。
    2. 生成合并清单文件（Markdown），用于后续统一提取媒体。
    3. 提交Celery任务处理。

    参数:
    - mode: 视频合成模式，"single_scene"（单场景模式）或"multi_scene"（多场景模式）
    - script_style: 脚本生成风格，"default"（默认风格）或"product_geek"（产品极客风格）
    - persona_id: 人设ID，用于个性化脚本生成
    - multi_video_count: 生成视频数量，支持多视频生成
    """

    # 校验基础参数
    if mode not in ["single_scene", "multi_scene"]:
        raise HTTPException(
            status_code=400, detail="模式参数必须是 'single_scene' 或 'multi_scene'"
        )
    if script_style not in ["default", "product_geek"]:
        raise HTTPException(
            status_code=400, detail="脚本风格必须是 'default' 或 'product_geek'"
        )
    if multi_video_count < 1 or multi_video_count > 5:
        raise HTTPException(status_code=400, detail="多视频数量必须在1-5之间")

    # 校验URL数量
    if not media_urls or len(media_urls) == 0:
        raise HTTPException(status_code=400, detail="必须提供至少1个素材URL")
    if len(media_urls) > 50:
        raise HTTPException(status_code=400, detail="素材URL数量不能超过50个")

    try:
        # 创建工作目录
        workspace_dir = Path.cwd() / "workspace" / f"task_{uuid4().hex}_{os.getpid()}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # 生成清单文件（Markdown），让下游解析图片/视频
        manifest_path = workspace_dir / "source_manifest.md"
        markdown_lines: List[str] = []

        def _is_markdown_url(u: str) -> bool:
            lower = u.lower()
            return lower.endswith((".md", ".markdown", ".txt"))

        def _is_image_url(u: str) -> bool:
            lower = u.lower()
            return lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"))

        def _is_video_url(u: str) -> bool:
            lower = u.lower()
            return lower.endswith(
                (".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm")
            )

        # 将Markdown远程内容内联（轻量级），其余直接按标签引用
        import requests
        import shutil

        for url in media_urls:
            try:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError("无效URL")
            except Exception:
                raise HTTPException(status_code=400, detail=f"无效URL: {url}")

        # 跟踪下载状态
        total_markdown_count = len([url for url in media_urls if _is_markdown_url(url)])
        successful_markdown_count = 0
        failed_urls = []

        for url in media_urls:
            if _is_markdown_url(url):
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200 and resp.text and resp.text.strip():
                        markdown_lines.append(f"\n\n<!-- Source: {url} -->\n")
                        markdown_lines.append(resp.text)
                        markdown_lines.append("\n\n")
                        successful_markdown_count += 1
                    else:
                        markdown_lines.append(
                            f"\n\n<!-- Unavailable markdown: {url} -->\n"
                        )
                        failed_urls.append(url)
                except Exception as e:
                    markdown_lines.append(
                        f"\n\n<!-- Fetch markdown failed: {url} -->\n"
                    )
                    failed_urls.append(url)
                    logger.warning(f"Markdown下载失败: {url}, 错误: {str(e)}")
            elif _is_image_url(url):
                markdown_lines.append(f"![]({url})")
            elif _is_video_url(url):
                markdown_lines.append(f'<video src="{url}"></video>')
            else:
                # 未知类型：作为链接保留，便于人工追踪
                markdown_lines.append(
                    f"[{os.path.basename(urlparse(url).path) or 'resource'}]({url})"
                )

        # 验证所有markdown都必须下载成功
        if total_markdown_count > 0 and successful_markdown_count < total_markdown_count:
            error_msg = f"Markdown文件下载失败: {len(failed_urls)}/{total_markdown_count} 个文件失败"
            logger.error(f"{error_msg}. 失败的URLs: {failed_urls}")
            # 清理已创建的工作目录
            shutil.rmtree(workspace_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail=f"{error_msg}，失败的URLs: {', '.join(failed_urls[:3])}{'...' if len(failed_urls) > 3 else ''}")
        
        # 验证是否有有效内容（排除注释行）
        if total_markdown_count > 0:
            effective_lines = [line for line in markdown_lines if line.strip() and not line.strip().startswith("<!--")]
            if not effective_lines:
                error_msg = "所有Markdown文件都下载失败，没有有效内容"
                logger.error(error_msg)
                shutil.rmtree(workspace_dir, ignore_errors=True)
                raise HTTPException(status_code=400, detail=error_msg)

        with open(manifest_path, "w", encoding="utf-8") as mf:
            mf.write("\n".join(markdown_lines) if markdown_lines else "")

        # 保存素材元数据（人工描述），用于后续阶段跳过AI分析
        try:
            if media_meta and media_meta.strip():
                meta_obj = json.loads(media_meta)
                meta_map = {}
                if isinstance(meta_obj, dict):
                    # 直接为 url->description 映射
                    meta_map = {str(k): str(v) for k, v in meta_obj.items() if v}
                elif isinstance(meta_obj, list):
                    # 数组项包含 {url, description}
                    for item in meta_obj:
                        try:
                            url = str(item.get("url") or "").strip()
                            desc = str(item.get("description") or "").strip()
                            if url and desc:
                                meta_map[url] = desc
                        except Exception:
                            continue
                if meta_map:
                    meta_path = workspace_dir / "materials_meta.json"
                    with open(meta_path, "w", encoding="utf-8") as mf2:
                        json.dump(meta_map, mf2, ensure_ascii=False, indent=2)
                    logger.info(f"保存素材元数据: {meta_path}，条目数: {len(meta_map)}")
        except Exception as meta_e:
            # 元数据不是强依赖，解析失败时仅记录告警
            logger.warning(f"素材元数据解析/保存失败（忽略）: {meta_e}")

        # 创建任务记录
        task_description = description or ""

        # 统计素材类型数量
        md_count = len([u for u in media_urls if _is_markdown_url(u)])
        img_count = len([u for u in media_urls if _is_image_url(u)])
        vid_count = len([u for u in media_urls if _is_video_url(u)])
        script_material_count = img_count + vid_count

        task_data = {
            "title": title,
            "description": task_description,
            "task_type": TaskType.TEXT_TO_VIDEO.value,
            "status": TaskStatus.PENDING.value,
            "file_path": str(manifest_path),
            "workspace_dir": str(workspace_dir),
            "creator_id": str(current_user.id),
            "script_style_type": script_style,
            "is_multi_video_task": multi_video_count > 1,
            "multi_video_count": multi_video_count,
            "script_material_count": script_material_count,
        }

        task = await create_task(task_data)
        if not task:
            raise HTTPException(status_code=500, detail="创建任务失败")

        # 提交到Celery队列
        celery_task = process_text_to_video.delay(
            task_id=str(task.id),
            source_file=str(manifest_path),
            workspace_dir=str(workspace_dir),
            mode=mode,
            persona_id=persona_id,
            multi_video_count=multi_video_count,
        )

        # 更新任务记录，保存Celery任务ID
        await update_task(
            task.id,
            {
                "celery_task_id": celery_task.id,
                "status": TaskStatus.PENDING.value,
                "updated_at": datetime.utcnow(),
            },
        )

        # 返回任务信息（附带素材计数，便于前端展示）
        task_response = Task(
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
            file_path=getattr(task, "file_path", None),
            workspace_dir=getattr(task, "workspace_dir", None),
            creator_id=task.creator_id,
            video_url=task.video_url,
            error_message=task.error_message,
            celery_task_id=celery_task.id,
            is_multi_video_task=task.is_multi_video_task,
            multi_video_count=getattr(task, "multi_video_count", multi_video_count),
            multi_video_urls=getattr(task, "multi_video_urls", []),
            script_style_type=getattr(task, "script_style_type", script_style),
            source_file=getattr(task, "source_file", str(manifest_path)),
            markdown_count=md_count,
            image_count=img_count,
            video_count=vid_count,
        )

        logger.info(f"视频任务创建成功: {task.id}, Celery任务ID: {celery_task.id}, Markdown成功: {successful_markdown_count}/{total_markdown_count}")
        return task_response

    except HTTPException:
        # HTTPException 直接抛出，不需要额外处理
        raise
    except Exception as e:
        logger.error(f"创建视频任务失败: {str(e)}", exc_info=True)
        # 确保清理工作目录
        try:
            if 'workspace_dir' in locals() and workspace_dir.exists():
                shutil.rmtree(workspace_dir, ignore_errors=True)
        except Exception:
            pass
        # 清理工作目录（仅在任务未成功创建时）
        if (
            "workspace_dir" in locals()
            and isinstance(workspace_dir, Path)
            and workspace_dir.exists()
        ):
            try:
                import shutil

                shutil.rmtree(workspace_dir, ignore_errors=True)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.post("/attachments/upload")
async def upload_attachments(
    current_user=Depends(require_api_key),
    files: List[UploadFile] = File(...)
) -> Dict[str, Any]:
    """附件上传接口：将文件上传到对象存储并返回URL（单次≤50个）。"""
    try:
        if not files:
            raise HTTPException(status_code=400, detail="必须提供至少1个文件")
        if len(files) > 50:
            raise HTTPException(status_code=400, detail="单次上传文件数量不能超过50个")

        storage = StorageFactory.get_storage()
        uploaded = []
        warnings: List[str] = []

        # 允许的扩展名分类
        image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        video_exts = {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm"}
        markdown_exts = {".md", ".markdown", ".txt"}

        # 临时保存与上传
        temp_dir = (
            Path.cwd() / "workspace" / "uploads" / datetime.utcnow().strftime("%Y%m%d")
        )
        temp_dir.mkdir(parents=True, exist_ok=True)

        total_size = 0
        stats = {"markdown_count": 0, "image_count": 0, "video_count": 0}

        for uf in files:
            content = await uf.read()
            if not content or len(content) == 0:
                uploaded.append(
                    {"filename": uf.filename, "success": False, "error": "空文件"}
                )
                continue

            if len(content) > settings.max_file_size:
                uploaded.append(
                    {
                        "filename": uf.filename,
                        "success": False,
                        "error": f"文件超过大小限制: {settings.max_file_size}",
                    }
                )
                continue

            # 写入临时文件
            safe_name = os.path.basename(uf.filename or "file")
            object_key = f"uploads/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid4().hex}_{safe_name}"
            tmp_path = temp_dir / f"{uuid4().hex}_{safe_name}"
            with open(tmp_path, "wb") as f:
                f.write(content)

            # 类型推断与校验
            ext_lower = (
                "".join(Path(safe_name).suffixes).lower()
                or Path(safe_name).suffix.lower()
            )
            media_type = None
            if any(ext_lower.endswith(e) for e in markdown_exts):
                media_type = "markdown"
                stats["markdown_count"] += 1
            elif any(ext_lower.endswith(e) for e in image_exts):
                media_type = "image"
                stats["image_count"] += 1
            elif any(ext_lower.endswith(e) for e in video_exts):
                media_type = "video"
                stats["video_count"] += 1
            else:
                warnings.append(f"不支持的文件类型: {safe_name}")
                media_type = "unknown"

            total_size += len(content)

            # 上传到对象存储
            try:
                url = storage.upload_file(str(tmp_path), object_key)
                uploaded.append(
                    {
                        "filename": uf.filename,
                        "url": url,
                        "object_key": object_key,
                        "media_type": media_type,
                        "size": len(content),
                        "success": True,
                    }
                )
            except Exception as up_e:
                uploaded.append(
                    {"filename": uf.filename, "success": False, "error": str(up_e)}
                )
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        return {
            "items": uploaded,
            "stats": {**stats, "total_size": total_size},
            "warnings": warnings,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"附件上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"附件上传失败: {str(e)}")


@router.get("/", response_model=List[Task])
async def get_all_tasks_endpoint() -> List[Task]:
    """获取所有任务列表"""
    try:
        tasks = await get_all_tasks()
        return [
            Task(
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
                file_path=task.file_path,
                workspace_dir=task.workspace_dir,
                creator_id=task.creator_id,
                video_url=task.video_url,
                error_message=task.error_message,
            )
            for task in tasks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/stats", response_model=TaskStats)
async def get_task_stats_endpoint() -> TaskStats:
    """获取任务统计信息"""
    try:
        stats = await get_task_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/{task_id}")
async def get_task_unified(
    task_id: UUID,
    include_stages: Optional[str] = Query(None, description="要包含的阶段数据，用逗号分隔: subtasks,media,analysis,scripts,videos"),
    detail_level: str = Query("basic", description="详情级别: basic,full"),
    current_user=Depends(optional_api_key)
) -> Dict[str, Any]:
    """统一任务查询接口 - 可按需返回不同阶段的数据"""
    try:
        # 解析要包含的阶段
        stages = []
        if include_stages:
            stages = [s.strip() for s in include_stages.split(",") if s.strip()]
        
        # 获取任务基础信息（必返回）
        task = await get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 构建基础响应（必返回字段）
        response = {
            "task_id": str(task.id),
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "workspace_dir": task.workspace_dir,
            "is_multi_video_task": True,
        }
        
        # 获取子任务信息并构建多视频摘要（必返回）- SubVideoTask 已移除
        # from models.database import get_sub_video_tasks_by_parent_id
        # sub_video_tasks = await get_sub_video_tasks_by_parent_id(task_id)
        sub_video_tasks = []  # SubVideoTask 已移除，返回空列表

        # 计算多视频任务统计 - 简化为单视频模式
        total_videos = 1 if task.video_url else 0
        completed_count = 1 if task.status == "completed" and task.video_url else 0
        failed_count = 1 if task.status in ["failed", "error"] else 0
        processing_count = 1 if task.status in ["processing", "video_generating", "script_generating", "script_generated"] else 0
        pending_count = 1 if task.status == "pending" else 0

        response["multi_video_summary"] = {
            "total_videos": total_videos,
            "completed_count": completed_count,
            "failed_count": failed_count,
            "processing_count": processing_count,
            "pending_count": pending_count,
        }
        
        # 设置当前阶段信息（从数据库读取实际阶段）
        response["current_stage"] = task.current_stage or "unknown"
        
        # 准备阶段数据容器
        stages_data = {}
        
        # 并行查询阶段数据
        async_queries = []
        
        if "media" in stages:
            from models.database import get_media_items_by_task_id
            async_queries.append(("media", get_media_items_by_task_id(task_id)))
        
        if "analysis" in stages:
            async_queries.append(("analysis", get_material_analyses(task_id)))
        
        if "subtasks" in stages:
            # 子任务信息 - SubVideoTask 已移除，返回空列表
            stages_data["subtasks"] = {
                "count": 0,
                "items": []
            }
        
        if "scripts" in stages:
            # 脚本信息 - SubVideoTask 已移除，返回空列表
            stages_data["scripts"] = {
                "count": 0,
                "items": []
            }
        
        # 初始化视频相关变量
        completed_videos = []
        processing_videos = []
        failed_videos = []
        
        if "videos" in stages:
            # 视频信息 - SubVideoTask 已移除，直接从主任务读取
            if task.status == "completed" and task.video_url:
                completed_videos.append({
                    "video_url": task.video_url,
                    "thumbnail_url": task.thumbnail_url or "",
                    "duration": task.duration or 0,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                })
            elif task.status in ["failed", "error"]:
                failed_videos.append({
                    "status": task.status,
                    "error_message": task.error_message,
                })
            elif task.status in ["processing", "video_generating", "script_generating", "script_generated"]:
                processing_videos.append({
                    "status": task.status,
                    "progress": task.progress,
                })

            stages_data["videos"] = {
                "count": total_videos,
                "completed": completed_videos,
                "processing": processing_videos,
                "failed": failed_videos,
            }
        
        # 执行并行查询
        if async_queries:
            results = await asyncio.gather(*[query[1] for query in async_queries], return_exceptions=True)
            for i, (stage_name, _) in enumerate(async_queries):
                if isinstance(results[i], Exception):
                    logger.error(f"查询阶段数据失败 - {stage_name}: {results[i]}")
                    continue
                
                if stage_name == "media":
                    media_items = results[i]
                    stages_data["media"] = {
                        "count": len(media_items) if media_items else 0,
                        "items": [
                            {
                                "id": str(item.id),
                                "filename": item.filename,
                                "media_type": item.media_type,
                                "original_url": item.original_url,
                                "file_size": item.file_size,
                                "mime_type": item.mime_type,
                                "resolution": item.resolution,
                                "created_at": item.created_at.isoformat() if item.created_at else None,
                            }
                            for item in media_items
                        ] if media_items else []
                    }
                elif stage_name == "analysis":
                    analyses = results[i]
                    stages_data["analysis"] = {
                        "count": len(analyses) if analyses else 0,
                        "items": analyses if analyses else []
                    }
        
        # 添加阶段数据到响应
        if stages_data:
            response["stages"] = stages_data
        
        # 向后兼容：添加主视频信息
        if completed_videos:
            response["video_url"] = completed_videos[0].get("video_url")
            response["thumbnail_url"] = completed_videos[0].get("thumbnail_url")
            response["video_duration"] = completed_videos[0].get("duration")
        else:
            response["video_url"] = task.video_url
            response["thumbnail_url"] = getattr(task, "thumbnail_url", None)
            response["video_duration"] = getattr(task, "video_duration", None)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"统一任务查询失败 - 任务ID: {task_id}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询任务失败: {str(e)}")


async def get_material_analyses(task_id: UUID) -> List[Dict[str, Any]]:
    """获取素材分析结果"""
    try:
        from models.database import get_db_session
        from models.tables import MaterialAnalysisTable
        from sqlalchemy import select
        
        async with get_db_session() as session:
            result = await session.execute(
                select(MaterialAnalysisTable).where(
                    MaterialAnalysisTable.task_id == task_id
                )
            )
            analyses = []
            for row in result.scalars():
                analyses.append({
                    "id": str(row.id),
                    "media_item_id": str(row.media_item_id) if row.media_item_id else None,
                    "original_url": row.original_url,
                    "ai_description": row.ai_description,
                    "quality_score": row.quality_score,
                    "quality_level": row.quality_level,
                    "key_objects": row.key_objects or [],
                    "emotional_tone": row.emotional_tone,
                    "visual_style": row.visual_style,
                    "usage_suggestions": row.usage_suggestions or [],
                    "color_palette": row.color_palette or [],
                    "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })
            return analyses
    except Exception as e:
        logger.error(f"获取素材分析失败: {str(e)}")
        return []


@router.put("/{task_id}", response_model=Task)
async def update_task_endpoint(
    task_id: UUID, 
    task_update: TaskUpdate,
    current_user=Depends(require_api_key)
):
    """更新任务信息"""
    try:
        task = await get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 构建更新数据
        update_data = {
            k: v for k, v in task_update.model_dump().items() if v is not None
        }
        if update_data:
            update_data["updated_at"] = datetime.now()

        updated_task = await update_task(task_id, update_data)
        if not updated_task:
            raise HTTPException(status_code=500, detail="更新任务失败")

        return Task(
            id=updated_task.id,
            title=updated_task.title,
            description=updated_task.description,
            task_type=updated_task.task_type,
            status=updated_task.status,
            progress=updated_task.progress,
            created_at=updated_task.created_at,
            updated_at=updated_task.updated_at,
            started_at=updated_task.started_at,
            completed_at=updated_task.completed_at,
            file_path=updated_task.file_path,
            workspace_dir=updated_task.workspace_dir,
            creator_id=updated_task.creator_id,
            video_url=updated_task.video_url,
            error_message=updated_task.error_message,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")


# 保持向后兼容：提供单独的 status 接口
@router.get("/{task_id}/status")
async def get_task_status_compat(task_id: UUID):
    """获取任务状态（向后兼容接口）"""
    # 直接调用统一接口
    return await get_task_detail(task_id)


@router.post("/{task_id}/retry")
async def retry_task(task_id: UUID):
    """重试失败的任务"""
    try:
        task = await get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 只有失败的任务才能重试
        if task.status != TaskStatus.FAILED.value:
            raise HTTPException(status_code=400, detail="只有失败的任务才能重试")

        # 重置任务状态，重新提交到Celery
        celery_task = process_text_to_video.delay(
            task_id=str(task_id),
            source_file=task.file_path,
            workspace_dir=task.workspace_dir,
            mode="multi_scene",  # 默认模式
            persona_id=None,
            multi_video_count=getattr(task, "multi_video_count", 1),
        )

        update_data = {
            "status": TaskStatus.PENDING.value,
            "progress": 0,
            "error_message": None,
            "error_traceback": None,
            "started_at": None,
            "completed_at": None,
            "celery_task_id": celery_task.id,
            "retry_count": getattr(task, "retry_count", 0) + 1,
            "updated_at": datetime.utcnow(),
        }

        updated_task = await update_task(task_id, update_data)
        if not updated_task:
            raise HTTPException(status_code=500, detail="重试任务失败")

        return {"message": "任务已重新加入处理队列", "task_id": str(task_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重试任务失败: {str(e)}")


@router.delete("/{task_id}")
async def delete_task_endpoint(task_id: UUID, current_user=Depends(require_api_key)):
    """删除任务"""
    try:
        task = await get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 不能删除正在处理的任务
        if task.status == TaskStatus.PROCESSING.value:
            raise HTTPException(status_code=400, detail="不能删除正在处理的任务")

        success = await delete_task(task_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除任务失败")

        # 清理工作目录
        if task.workspace_dir and os.path.exists(task.workspace_dir):
            import shutil

            shutil.rmtree(task.workspace_dir, ignore_errors=True)

        return {"message": "任务删除成功", "task_id": str(task_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.get("/{task_id}/media-items", response_model=List[MediaItem])
@router.get(
    "/{task_id}/media", response_model=List[MediaItem]
)  # 路由别名，兼容测试脚本
async def get_task_media_items(task_id: UUID):
    """获取任务的媒体项目列表"""
    try:
        task = await get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        media_items = await get_media_items_by_task_id(task_id)

        return [
            MediaItem(
                id=item.id,
                task_id=item.task_id,
                original_url=item.original_url,
                media_type=item.media_type,
                filename=item.filename,
                file_size=item.file_size,
                mime_type=item.mime_type,
                local_path=item.local_path,
                cloud_url=item.cloud_url,
                upload_status=item.upload_status,
                download_status=item.download_status,
                created_at=item.created_at,
                downloaded_at=item.downloaded_at,
                uploaded_at=item.uploaded_at,
                error_message=item.error_message,
                context_before=item.context_before,
                context_after=item.context_after,
                position_in_content=item.position_in_content,
                surrounding_paragraph=item.surrounding_paragraph,
            )
            for item in media_items
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取媒体项目失败: {str(e)}")


@router.get("/celery/status")
async def get_celery_status():
    """获取Celery集群状态"""
    try:
        # 获取活跃的Worker
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        stats = inspect.stats()

        worker_info = []
        if active_workers:
            for worker_name, tasks in active_workers.items():
                worker_stats = stats.get(worker_name, {}) if stats else {}
                worker_info.append(
                    {
                        "worker_name": worker_name,
                        "active_tasks": len(tasks),
                        "processed_tasks": worker_stats.get("total", {}).get(
                            "celery.control.inspect", 0
                        ),
                        "status": "online",
                    }
                )

        # 获取队列状态
        pending_tasks = await get_tasks_by_status(TaskStatus.PENDING)
        processing_tasks = await get_tasks_by_status(TaskStatus.PROCESSING)

        return {
            "celery_status": "running" if worker_info else "no_workers",
            "workers": worker_info,
            "total_workers": len(worker_info),
            "queue_status": {
                "pending_tasks": len(pending_tasks),
                "processing_tasks": len(processing_tasks),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Celery状态失败: {str(e)}")


@router.post("/celery/purge")
async def purge_celery_queue():
    """清空Celery队列（谨慎使用）"""
    try:
        celery_app.control.purge()
        return {"message": "Celery队列已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空队列失败: {str(e)}")


@router.get("/queue/status")
async def get_queue_status():
    """获取任务队列状态 - 基于数据库和Celery状态"""
    try:
        # 获取各状态的任务
        pending_tasks = await get_tasks_by_status(TaskStatus.PENDING)
        processing_tasks = await get_tasks_by_status(TaskStatus.PROCESSING)
        completed_tasks = await get_tasks_by_status(TaskStatus.COMPLETED)
        failed_tasks = await get_tasks_by_status(TaskStatus.FAILED)

        # 计算总体统计
        total_pending = len(pending_tasks)
        total_processing = len(processing_tasks)
        total_completed = len(completed_tasks)
        total_failed = len(failed_tasks)

        # 计算最近完成任务的平均处理时间
        avg_processing_time = 0
        if completed_tasks:
            processing_times = []
            for task in completed_tasks[-10:]:  # 只看最近10个完成的任务
                if task.started_at and task.completed_at:
                    duration = (task.completed_at - task.started_at).total_seconds()
                    processing_times.append(duration)

            if processing_times:
                avg_processing_time = sum(processing_times) / len(processing_times)

        # 获取Celery状态
        celery_status = {"available": False}
        try:
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            celery_status = {
                "available": True,
                "active_workers": len(active_workers) if active_workers else 0,
                "total_active_tasks": (
                    sum(len(tasks) for tasks in active_workers.values())
                    if active_workers
                    else 0
                ),
            }
        except Exception:
            pass

        return {
            "queue_status": {
                "pending": total_pending,
                "processing": total_processing,
                "completed": total_completed,
                "failed": total_failed,
            },
            "average_processing_time": round(avg_processing_time, 2),
            "celery_info": celery_status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取队列状态失败: {str(e)}")
