"""
动态字幕相关API接口 - 基于PyCaps
"""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from config import settings
from services.pycaps_subtitle_service import PyCapsSubtitleService
from utils.auth import verify_internal_token

router = APIRouter(prefix="/dynamic-subtitles", tags=["动态字幕"])


class ProcessPyCapsSubtitleRequest(BaseModel):
    """PyCaps动态字幕处理请求"""

    video_url: str = Field(..., description="视频URL")
    subtitles_url: str = Field(..., description="字幕文件URL (.srt格式)")
    template: str = Field(..., description="PyCaps模板名称 (hype, minimalist, explosive等)")


@router.get("/templates")
async def get_pycaps_templates():
    """获取PyCaps模板列表"""
    service = PyCapsSubtitleService()
    result = service.get_available_templates()
    return result


@router.post("/process")
async def process_pycaps_subtitles(
    request: ProcessPyCapsSubtitleRequest, x_test_token: Optional[str] = Header(None)
):
    """处理PyCaps动态字幕"""

    # 验证内部测试token
    if not verify_internal_token(x_test_token):
        raise HTTPException(status_code=403, detail="需要有效的测试token")

    try:
        # 使用PyCaps服务处理
        service = PyCapsSubtitleService()
        result = service.process_video_subtitles(
            video_url=request.video_url,
            subtitles_url=request.subtitles_url,
            template=request.template,
            task_id="manual_test",
        )

        if result["success"]:
            return {
                "success": True,
                "message": "PyCaps动态字幕处理成功",
                "video_url": result["video_url"],
                "original_video_url": result.get("original_video_url"),
                "template": request.template,
                "processed": result["processed"],
            }
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "PyCaps处理失败")
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PyCaps处理失败: {str(e)}")


@router.get("/config")
async def get_pycaps_config():
    """获取PyCaps配置"""
    return {
        "success": True,
        "config": {
            "enabled": settings.dynamic_subtitle_enabled,
            "engine": "PyCaps",
            "storage_type": settings.storage_type,
        },
    }


@router.get("/test/pycaps-status")
async def check_pycaps_status(
    x_test_token: Optional[str] = Header(None, alias="x-test-token")
):
    """检查PyCaps库状态（内部测试接口）"""
    if not verify_internal_token(x_test_token):
        raise HTTPException(status_code=403, detail="需要有效的内部测试Token")

    try:
        service = PyCapsSubtitleService()
        
        # 检查FFmpeg
        ffmpeg_available = False
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            ffmpeg_available = result.returncode == 0
        except Exception:
            ffmpeg_available = False

        # 检查Playwright
        playwright_available = False
        try:
            from playwright.sync_api import sync_playwright
            playwright_available = True
        except ImportError:
            playwright_available = False

        # 获取模板列表
        templates_result = service.get_available_templates()

        return {
            "success": True,
            "pycaps_available": True,
            "pycaps_info": {
                "version": "pycaps_integrated_1.0",
                "module_path": "services/pycaps_subtitle_service.py",
            },
            "dependencies": {
                "ffmpeg": ffmpeg_available,
                "playwright": playwright_available,
            },
            "config": {
                "enabled": settings.dynamic_subtitle_enabled,
                "temp_dir": service.temp_dir,
            },
            "templates": templates_result.get("templates", []),
        }

    except Exception as e:
        return {"success": False, "error": str(e), "pycaps_available": False}