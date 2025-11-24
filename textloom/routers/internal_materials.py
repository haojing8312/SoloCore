from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import config
from processors.sync_material_processor import SyncMaterialProcessor

router = APIRouter(prefix="/internal/materials", tags=["internal-materials"])


class AnalyzeImageRequest(BaseModel):
    image_url: str
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    surrounding_paragraph: Optional[str] = None


class ProcessArticleRequest(BaseModel):
    content_markdown: str
    max_images: int = 10
    max_videos: int = 3


def _require_internal_token(x_test_token: Optional[str]) -> None:
    expected = (config.settings.internal_test_token or "").strip()
    provided = (x_test_token or "").strip()
    if not expected or provided != expected:
        # 当未配置 expected 时，认为禁用内部接口
        raise HTTPException(
            status_code=401, detail="Unauthorized: invalid or missing test token"
        )


@router.post("/extract-media")
def extract_media(
    request: ProcessArticleRequest, x_test_token: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    """提取 Markdown/HTML 文本中的媒体 URL 与上下文（仅内部评估使用）。"""
    _require_internal_token(x_test_token)
    # 使用临时工作目录（内存/容器文件系统），只做提取不落库
    proc = SyncMaterialProcessor(workspace_dir="workspace/internal-playground")
    # 写入临时文件
    article_path = f"workspace/internal-playground/article-{uuid4().hex[:8]}.md"
    try:
        import os

        os.makedirs("workspace/internal-playground", exist_ok=True)
        with open(article_path, "w", encoding="utf-8") as f:
            f.write(request.content_markdown or "")
        # 走与对外一致的提取逻辑，但不下载
        images, videos, _ = proc._extract_media_urls_with_context(
            request.content_markdown or ""
        )
        return {
            "ok": True,
            "images": images,
            "videos": videos,
            "stats": {"image_count": len(images), "video_count": len(videos)},
        }
    finally:
        try:
            import os

            if os.path.exists(article_path):
                os.remove(article_path)
        except Exception:
            pass


@router.post("/download-and-organize")
def download_and_organize(
    payload: Dict[str, Any], x_test_token: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    """给定媒体 URL 列表（含类型与上下文），执行下载与本地组织（内部评估）。"""
    _require_internal_token(x_test_token)
    urls: List[Dict[str, Any]] = payload.get("urls") or []
    task_id: str = payload.get("task_id") or uuid4().hex
    proc = SyncMaterialProcessor(workspace_dir="workspace/internal-playground")
    results = proc._download_and_organize_files_sync(urls, task_id)
    return {
        "ok": True,
        "task_id": task_id,
        "count": len(results),
        "results": results,
    }
