from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import config
from processors.sync_material_analyzer import SyncMaterialAnalyzer

router = APIRouter(prefix="/internal/analyzer", tags=["internal-analyzer"])


class AnalyzeImageWithContextRequest(BaseModel):
    image_url: str
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    surrounding_paragraph: Optional[str] = None
    caption: Optional[str] = None
    resolution: Optional[str] = None  # 可选，默认 unknown


def _require_internal_token(x_test_token: Optional[str]) -> None:
    expected = (config.settings.internal_test_token or "").strip()
    provided = (x_test_token or "").strip()
    if not expected or provided != expected:
        raise HTTPException(
            status_code=401, detail="Unauthorized: invalid or missing test token"
        )


@router.post("/analyze-image")
def analyze_image_with_context(
    req: AnalyzeImageWithContextRequest,
    x_test_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """使用 SyncMaterialAnalyzer 的内部能力对图片+上下文进行分析（仅内部评估）。"""
    _require_internal_token(x_test_token)

    analyzer = SyncMaterialAnalyzer(workspace_dir="workspace/internal-playground")
    started = datetime.utcnow()
    try:
        parsed = analyzer._analyze_image_with_ai_context(
            image_path=req.image_url,
            resolution=req.resolution or "unknown",
            context_before=req.context_before,
            context_after=req.context_after,
            surrounding_paragraph=req.surrounding_paragraph,
            caption=req.caption,
        )
        duration = (datetime.utcnow() - started).total_seconds()
        return {
            "ok": True,
            "duration_sec": duration,
            "model": analyzer.analysis_model,
            "result": parsed,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"analyze failed: {e}")
