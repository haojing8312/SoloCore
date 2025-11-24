from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import config
from services.sync_video_generator import SyncVideoGenerator

router = APIRouter(prefix="/internal/video", tags=["internal-video"])


class GenerateVideoRequest(BaseModel):
    # 简化的输入：脚本数据和媒体文件列表（与生成器所需结构一致）
    script_data: Dict[str, Any]
    media_files: List[Dict[str, Any]]
    task_id: Optional[str] = None
    mode: str = "multi_scene"  # 或 "single_scene"


def _require_internal_token(x_test_token: Optional[str]) -> None:
    expected = (config.settings.internal_test_token or "").strip()
    provided = (x_test_token or "").strip()
    if not expected or provided != expected:
        raise HTTPException(
            status_code=401, detail="Unauthorized: invalid or missing test token"
        )


@router.post("/generate-single")
def generate_single_video(
    req: GenerateVideoRequest, x_test_token: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    """使用 SyncVideoGenerator 生成单个视频（仅内部评估）。"""
    _require_internal_token(x_test_token)
    generator = SyncVideoGenerator()
    task_id = req.task_id or uuid4().hex
    try:
        # 使用新的单视频生成方法
        result = generator.generate_single_video_by_style(
            script_data=req.script_data,
            media_files=req.media_files,
            task_id=task_id,
            script_style=req.script_data.get("script_style"),
            mode=req.mode,
        )
        return {"ok": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"video generate failed: {e}")


@router.post("/generate-multiple")
def generate_multiple_videos(
    req: Dict[str, Any], x_test_token: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    """使用 SyncVideoGenerator 并发生成多个视频（仅内部评估）。"""
    _require_internal_token(x_test_token)
    generator = SyncVideoGenerator()
    scripts_data: List[Dict[str, Any]] = req.get("scripts_data") or []
    media_files: List[Dict[str, Any]] = req.get("media_files") or []
    task_id: str = req.get("task_id") or uuid4().hex
    mode: str = req.get("mode") or "multi_scene"
    try:
        results = generator.generate_multiple_videos_sync(
            scripts_data=scripts_data,
            media_files=media_files,
            task_id=task_id,
            mode=mode,
        )
        return {"ok": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"video generate failed: {e}")
