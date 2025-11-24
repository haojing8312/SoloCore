"""
安全的任务处理路由 - 集成安全验证组件

这个模块展示了如何在现有的任务处理路由中集成安全验证，
提供了完整的安全防护示例。
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from celery_config import celery_app
from config import settings

# 导入现有模型和数据库操作
from models import Task, TaskCreate, TaskStatus, TaskType
from models.database import create_task, get_task_by_id, update_task
from tasks.video_processing_tasks import process_text_to_video
from utils.security.file_validator import SecurityThreatLevel
from utils.security.input_validator import ValidationLevel, secure_input_validator

# 导入安全组件
from utils.security.secure_file_handler import secure_file_handler, secure_url_validator
from utils.security.security_middleware import require_api_key, require_https

router = APIRouter(prefix="/secure", tags=["安全任务处理"])
logger = logging.getLogger(__name__)

# 安全配置
SECURITY_CONFIG = {
    "max_urls_per_request": 50,
    "max_file_size": settings.max_file_size,
    "allowed_domains": [],  # 可配置的域名白名单
    "enable_strict_validation": True,
}


@router.post(
    "/upload-files",
    summary="安全文件上传",
    description="提供多层安全验证的文件上传接口",
)
async def secure_upload_files(
    files: List[UploadFile] = File(..., description="上传的文件列表"),
    enable_virus_scan: bool = Form(False, description="是否启用病毒扫描"),
    max_file_size_override: Optional[int] = Form(None, description="覆盖文件大小限制"),
):
    """
    安全的文件上传接口

    实施的安全措施：
    1. 文件类型白名单验证
    2. MIME类型验证
    3. 文件头魔数检查
    4. 恶意内容扫描
    5. 文件名安全化
    6. 病毒扫描（可选）
    7. 安全存储
    """

    try:
        # 1. 基础验证
        if not files:
            raise HTTPException(status_code=400, detail="必须提供至少一个文件")

        if len(files) > 50:
            raise HTTPException(status_code=400, detail="单次上传文件数量不能超过50个")

        # 2. 配置安全处理器
        if (
            max_file_size_override
            and max_file_size_override <= SECURITY_CONFIG["max_file_size"]
        ):
            # 只允许降低限制，不允许提高
            secure_file_handler.config.max_file_size = max_file_size_override

        secure_file_handler.config.enable_virus_scan = enable_virus_scan

        # 3. 处理文件上传
        logger.info(f"开始处理{len(files)}个文件的安全上传")

        file_results = await secure_file_handler.handle_multiple_uploads(files)

        # 4. 构建响应
        uploaded_files = []
        security_warnings = []

        for file_info in file_results:
            file_result = {
                "original_filename": file_info.original_filename,
                "sanitized_filename": file_info.sanitized_filename,
                "file_size": file_info.file_size,
                "mime_type": file_info.mime_type,
                "file_hash": file_info.file_hash,
                "file_type": file_info.validation_result.file_type.value,
                "threat_level": file_info.validation_result.threat_level.value,
                "upload_path": file_info.final_path,
                "success": True,
            }

            # 添加安全警告信息
            if file_info.validation_result.warnings:
                file_result["security_warnings"] = file_info.validation_result.warnings
                security_warnings.extend(file_info.validation_result.warnings)

            # 添加扫描结果
            if file_info.scan_results:
                file_result["scan_results"] = file_info.scan_results

            uploaded_files.append(file_result)

        # 5. 安全审计日志
        logger.info(f"文件上传完成: {len(uploaded_files)}个文件成功上传")
        if security_warnings:
            logger.warning(f"安全警告: {security_warnings}")

        response = {
            "uploaded_files": uploaded_files,
            "total_files": len(uploaded_files),
            "security_warnings": list(set(security_warnings)),  # 去重
            "upload_timestamp": datetime.utcnow().isoformat(),
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"安全文件上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件上传处理失败: {str(e)}")


@router.post(
    "/create-video-task",
    summary="安全视频任务创建",
    description="使用安全验证的视频任务创建接口",
)
async def secure_create_video_task(
    media_urls: List[str] = Form(..., description="媒体文件URL列表"),
    title: str = Form(..., description="任务标题"),
    description: Optional[str] = Form(None, description="任务描述"),
    mode: str = Form("multi_scene", description="视频合成模式"),
    script_style: Optional[str] = Form("default", description="脚本生成风格"),
    persona_id: Optional[int] = Form(None, description="人设ID"),
    multi_video_count: int = Form(3, description="生成视频数量"),
    enable_strict_validation: bool = Form(True, description="是否启用严格验证"),
):
    """
    安全的视频任务创建接口

    实施的安全措施：
    1. URL安全验证
    2. 输入参数验证和清理
    3. SSRF防护
    4. 注入攻击防护
    5. 参数范围检查
    """

    try:
        # 1. 输入参数验证
        validation_level = (
            ValidationLevel.STRICT
            if enable_strict_validation
            else ValidationLevel.STANDARD
        )
        input_validator = secure_input_validator
        input_validator.validation_level = validation_level

        # 验证标题
        title_result = input_validator.validate_text_input(title, max_length=200)
        if not title_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"标题验证失败: {', '.join(title_result.issues)}",
            )
        title = title_result.cleaned_value

        # 验证描述
        if description:
            desc_result = input_validator.validate_text_input(
                description, max_length=1000
            )
            if not desc_result.is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"描述验证失败: {', '.join(desc_result.issues)}",
                )
            description = desc_result.cleaned_value

        # 验证模式参数
        if mode not in ["single_scene", "multi_scene"]:
            raise HTTPException(status_code=400, detail="无效的视频模式参数")

        # 验证脚本风格
        if script_style not in ["default", "product_geek"]:
            raise HTTPException(status_code=400, detail="无效的脚本风格参数")

        # 验证视频数量
        if not (1 <= multi_video_count <= 5):
            raise HTTPException(status_code=400, detail="视频数量必须在1-5之间")

        # 2. URL安全验证
        if not media_urls:
            raise HTTPException(status_code=400, detail="必须提供至少一个媒体URL")

        if len(media_urls) > SECURITY_CONFIG["max_urls_per_request"]:
            raise HTTPException(
                status_code=400,
                detail=f"URL数量超限: {len(media_urls)} > {SECURITY_CONFIG['max_urls_per_request']}",
            )

        logger.info(f"开始验证{len(media_urls)}个媒体URL")

        # 使用安全URL验证器
        validated_urls, url_errors = secure_url_validator.validate_media_urls(
            media_urls
        )

        if url_errors:
            logger.warning(f"URL验证失败: {url_errors}")
            if enable_strict_validation:
                # 严格模式下任何URL错误都拒绝
                raise HTTPException(
                    status_code=400,
                    detail=f"URL验证失败: {'; '.join(url_errors[:3])}{'...' if len(url_errors) > 3 else ''}",
                )

        # 使用验证后的URL
        clean_urls = validated_urls

        # 3. 创建安全的工作目录
        from uuid import uuid4

        workspace_dir = (
            Path.cwd() / "workspace" / f"secure_task_{uuid4().hex}_{os.getpid()}"
        )
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # 设置目录权限
        try:
            os.chmod(workspace_dir, 0o700)
        except Exception as e:
            logger.warning(f"无法设置目录权限: {e}")

        # 4. 创建安全的清单文件
        manifest_path = workspace_dir / "secure_source_manifest.md"

        # 安全地构建Markdown内容
        markdown_lines = []

        def _categorize_url(url: str) -> str:
            """安全地分类URL"""
            lower_url = url.lower()
            if any(ext in lower_url for ext in [".md", ".markdown", ".txt"]):
                return "markdown"
            elif any(
                ext in lower_url
                for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]
            ):
                return "image"
            elif any(
                ext in lower_url
                for ext in [".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm"]
            ):
                return "video"
            else:
                return "unknown"

        # 安全地处理URL内容
        for url in clean_urls:
            url_type = _categorize_url(url)

            if url_type == "markdown":
                # 对于Markdown类型，添加安全的引用
                markdown_lines.append(f"\n\n<!-- Source: {url} -->\n")
                markdown_lines.append(f"[Markdown Content]({url})")
            elif url_type == "image":
                # 使用安全的图片引用
                safe_url = input_validator.sanitize_for_html(url)
                markdown_lines.append(f"![]({safe_url})")
            elif url_type == "video":
                # 使用安全的视频引用
                safe_url = input_validator.sanitize_for_html(url)
                markdown_lines.append(f'<video src="{safe_url}"></video>')
            else:
                # 未知类型作为安全链接
                safe_url = input_validator.sanitize_for_html(url)
                safe_filename = input_validator.sanitize_for_html(os.path.basename(url))
                markdown_lines.append(f"[{safe_filename or 'resource'}]({safe_url})")

        # 写入清单文件
        with open(manifest_path, "w", encoding="utf-8") as mf:
            content = "\n".join(markdown_lines) if markdown_lines else ""
            # 确保内容安全
            safe_content = input_validator.sanitize_for_html(content)
            mf.write(safe_content)

        # 5. 创建任务记录
        task_data = {
            "title": title,
            "description": description or "",
            "task_type": TaskType.TEXT_TO_VIDEO.value,
            "status": TaskStatus.PENDING.value,
            "file_path": str(manifest_path),
            "workspace_dir": str(workspace_dir),
            "creator_id": None,
            "script_style_type": script_style,
            "is_multi_video_task": multi_video_count > 1,
            "multi_video_count": multi_video_count,
            "script_material_count": len(
                [u for u in clean_urls if _categorize_url(u) in ["image", "video"]]
            ),
        }

        task = await create_task(task_data)
        if not task:
            raise HTTPException(status_code=500, detail="创建任务失败")

        # 6. 提交到Celery队列
        celery_task = process_text_to_video.delay(
            task_id=str(task.id),
            source_file=str(manifest_path),
            workspace_dir=str(workspace_dir),
            mode=mode,
            persona_id=persona_id,
            multi_video_count=multi_video_count,
        )

        # 更新任务记录
        await update_task(
            task.id,
            {
                "celery_task_id": celery_task.id,
                "status": TaskStatus.PENDING.value,
                "updated_at": datetime.utcnow(),
            },
        )

        # 7. 构建安全响应
        response = {
            "task_id": str(task.id),
            "celery_task_id": celery_task.id,
            "title": title,
            "description": description,
            "status": task.status,
            "workspace_dir": str(workspace_dir),
            "validated_urls": len(clean_urls),
            "total_urls": len(media_urls),
            "security_info": {
                "validation_level": validation_level.value,
                "url_errors": len(url_errors),
                "strict_mode": enable_strict_validation,
            },
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }

        # 8. 安全审计日志
        logger.info(
            f"安全视频任务创建成功: 任务ID={task.id}, Celery任务ID={celery_task.id}"
        )
        logger.info(f"URL验证结果: {len(clean_urls)}/{len(media_urls)} 个URL通过验证")

        if url_errors:
            logger.warning(f"URL验证警告: {url_errors}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"安全视频任务创建失败: {e}", exc_info=True)
        # 清理工作目录
        if "workspace_dir" in locals() and workspace_dir.exists():
            try:
                import shutil

                shutil.rmtree(workspace_dir, ignore_errors=True)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"任务创建失败: {str(e)}")


@router.get(
    "/task/{task_id}/security-status",
    summary="获取任务安全状态",
    description="获取任务的安全验证状态和威胁等级",
)
async def get_task_security_status(task_id: UUID):
    """
    获取任务的安全状态信息
    """
    try:
        task = await get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 获取工作空间的安全信息
        security_info = {
            "task_id": str(task_id),
            "workspace_secure": False,
            "files_validated": 0,
            "security_warnings": [],
            "threat_level": "unknown",
        }

        if task.workspace_dir and os.path.exists(task.workspace_dir):
            workspace_path = Path(task.workspace_dir)

            # 检查工作空间安全性
            try:
                stat_info = workspace_path.stat()
                # 检查权限
                security_info["workspace_secure"] = (stat_info.st_mode & 0o777) <= 0o700
            except Exception:
                pass

            # 统计已验证文件
            validated_dir = workspace_path / "validated"
            if validated_dir.exists():
                security_info["files_validated"] = len(list(validated_dir.rglob("*")))

            # 检查隔离文件
            quarantine_dir = workspace_path / "quarantine"
            if quarantine_dir.exists():
                quarantined_files = list(quarantine_dir.glob("*.info"))
                if quarantined_files:
                    security_info["security_warnings"].append(
                        f"发现{len(quarantined_files)}个隔离文件"
                    )
                    security_info["threat_level"] = "high"

        return security_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取安全状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取安全状态失败")


@router.post(
    "/validate-input", summary="输入验证测试", description="用于测试各种输入的安全验证"
)
async def validate_input_test(
    test_input: str = Form(..., description="待验证的输入"),
    validation_type: str = Form("text", description="验证类型: text, url, filename"),
    validation_level: str = Form(
        "standard", description="验证级别: strict, standard, lenient"
    ),
):
    """
    输入验证测试接口（仅用于开发和测试）

    注意：生产环境应该移除此接口
    """
    try:
        # 验证级别映射
        level_map = {
            "strict": ValidationLevel.STRICT,
            "standard": ValidationLevel.STANDARD,
            "lenient": ValidationLevel.LENIENT,
        }

        validation_level_enum = level_map.get(
            validation_level, ValidationLevel.STANDARD
        )
        validator = secure_input_validator
        validator.validation_level = validation_level_enum

        # 根据类型进行验证
        if validation_type == "url":
            result = validator.validate_url(test_input)
        elif validation_type == "filename":
            result = validator.validate_filename(test_input)
        else:  # text
            result = validator.validate_text_input(test_input)

        # 返回详细的验证结果
        response = {
            "original_input": test_input,
            "validation_type": validation_type,
            "validation_level": validation_level,
            "is_valid": result.is_valid,
            "cleaned_value": result.cleaned_value,
            "issues": result.issues,
            "warnings": result.warnings,
            "risk_score": result.risk_score,
            "sanitized_html": validator.sanitize_for_html(test_input),
            "sanitized_sql": validator.sanitize_for_sql(test_input),
        }

        return response

    except Exception as e:
        logger.error(f"输入验证测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"验证测试失败: {str(e)}")


# 安全装饰器使用示例
@router.get("/secure-endpoint", dependencies=[Depends(require_https)])
async def secure_endpoint_example():
    """
    安全端点示例 - 需要HTTPS
    """
    return {"message": "这是一个需要HTTPS的安全端点"}


@router.get("/admin/security-status", dependencies=[Depends(require_api_key())])
async def admin_security_status():
    """
    管理员安全状态 - 需要API密钥
    """
    # 获取系统安全状态
    security_status = {
        "file_handler_status": "active",
        "input_validator_status": "active",
        "middleware_status": "active",
        "quarantine_files": 0,
        "blocked_requests": 0,
        "security_warnings": [],
    }

    try:
        # 检查隔离目录
        quarantine_dir = Path("./quarantine")
        if quarantine_dir.exists():
            security_status["quarantine_files"] = len(
                list(quarantine_dir.glob("*.info"))
            )

        # 可以添加更多状态检查

    except Exception as e:
        logger.error(f"获取安全状态失败: {e}")
        security_status["security_warnings"].append(f"状态检查异常: {e}")

    return security_status
