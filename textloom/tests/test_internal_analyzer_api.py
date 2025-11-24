import json
import os
import types

import pytest
from fastapi.testclient import TestClient

from main import app

pytestmark = [pytest.mark.integration]


def _with_token_env(token: str):
    os.environ["INTERNAL_TEST_TOKEN"] = token
    from importlib import reload

    import config as _cfg

    reload(_cfg)
    return _cfg.settings


def test_analyze_image_requires_token():
    client = TestClient(app)
    r = client.post(
        "/internal/analyzer/analyze-image", json={"image_url": "http://x.jpg"}
    )
    assert r.status_code == 401


def test_analyze_image_ok(monkeypatch):
    _with_token_env("test-token")
    client = TestClient(app)

    # mock openai 客户端，返回严格 JSON 字符串
    from utils import sync_clients as S

    class _Client:
        def analyze_image(self, image_url: str, context: str, model: str):
            payload = {
                "description": "一张手机产品图，桌面拍摄",
                "contextual_description": "结合上下文，该图用于展示产品外观细节",
                "contextual_purpose": "产品外观展示",
                "content_role": "主要展示",
                "semantic_relevance": 92.5,
                "tags": ["手机", "产品", "科技"],
                "quality_level": "good",
                "quality_score": 86.0,
                "voiceover_script": "外观精致，细节到位。",
                "contextual_voiceover_script": "这张图强调了新机的设计语言与材质质感。",
                "usage_suggestions": ["做封面", "做细节说明"],
            }
            return json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr(S.SyncClientFactory, "_openai_client", None)
    monkeypatch.setattr(
        S.SyncClientFactory, "get_openai_client", lambda logger=None: _Client()
    )

    body = {
        "image_url": "https://example.com/a.jpg",
        "context_before": "这是前文",
        "context_after": "这是后文",
        "surrounding_paragraph": "整段上下文",
        "resolution": "800x600",
    }
    r = client.post(
        "/internal/analyzer/analyze-image",
        json=body,
        headers={"x-test-token": "test-token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["result"]["description"]
    assert data["result"]["tags"]
