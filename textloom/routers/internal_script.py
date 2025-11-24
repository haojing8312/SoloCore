from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import config
from models.script_generation import ScriptStyle
from services.sync_script_generator import SyncScriptGenerator

router = APIRouter(prefix="/internal/script", tags=["internal-script"])


class GenerateScriptRequest(BaseModel):
    topic: str
    source_content: str
    material_context: Optional[Dict[str, Any]] = None
    persona_id: Optional[int] = None
    styles: Optional[List[str]] = None  # 例如 ["professional", "viral", "balanced"]
    creator_id: Optional[str] = None
    user_requirements: Optional[str] = None
    task_id: Optional[str] = None


def _require_internal_token(x_test_token: Optional[str]) -> None:
    expected = (config.settings.internal_test_token or "").strip()
    provided = (x_test_token or "").strip()
    if not expected or provided != expected:
        raise HTTPException(
            status_code=401, detail="Unauthorized: invalid or missing test token"
        )


@router.post("/generate")
def generate_script(
    req: GenerateScriptRequest, x_test_token: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    """使用 SyncScriptGenerator 生成脚本（仅内部评估）。"""
    _require_internal_token(x_test_token)

    generator = SyncScriptGenerator()
    task_id = req.task_id or uuid4().hex

    # 将字符串风格映射到枚举
    styles: Optional[List[ScriptStyle]] = None
    if req.styles:
        mapped: List[ScriptStyle] = []
        for s in req.styles:
            try:
                mapped.append(ScriptStyle(s))
            except Exception:
                # 忽略非法风格
                pass
        styles = mapped or None

    try:
        result = generator.generate_multi_scripts_sync(
            task_id=task_id,
            topic=req.topic,
            source_content=req.source_content,
            material_context=req.material_context,
            persona_id=req.persona_id,
            styles=styles,
            creator_id=req.creator_id,
            user_requirements=req.user_requirements,
        )
        return {
            "ok": True,
            "generated_at": datetime.utcnow(),
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generate failed: {e}")
