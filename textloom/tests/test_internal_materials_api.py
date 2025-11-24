import os

import pytest
from fastapi.testclient import TestClient

from main import app

pytestmark = [pytest.mark.integration]


def _with_token_env(token: str):
    os.environ["INTERNAL_TEST_TOKEN"] = token
    # 触发 settings 重新读取（如果项目使用了全局单例，这里仅用于测试环境）
    from importlib import reload

    import config as _cfg

    reload(_cfg)
    return _cfg.settings


def test_extract_media_requires_token(monkeypatch):
    client = TestClient(app)
    # 未设置 token 或 token 不匹配
    r = client.post(
        "/internal/materials/extract-media",
        json={"content_markdown": "![a](http://x/a.jpg)"},
    )
    assert r.status_code == 401


def test_extract_media_ok(monkeypatch):
    # 设置内置 token
    _with_token_env("test-token")
    client = TestClient(app)
    md = """
这是一个段落

![图1](https://example.com/a.jpg)

另一个段落包含视频链接 https://example.com/v.mp4
"""
    r = client.post(
        "/internal/materials/extract-media",
        json={"content_markdown": md},
        headers={"x-test-token": "test-token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["stats"]["image_count"] == 1
    assert data["stats"]["video_count"] == 1


def test_download_and_organize_requires_token():
    client = TestClient(app)
    r = client.post("/internal/materials/download-and-organize", json={"urls": []})
    assert r.status_code == 401


def test_download_and_organize_ok(monkeypatch, tmp_path):
    _with_token_env("test-token")
    client = TestClient(app)

    # mock HTTP 下载，返回最小 JPEG 头
    class _HTTP:
        def get(self, url):
            return b"\xff\xd8\xff\xdb" + b"0" * 1024

    monkeypatch.setattr(
        "processors.sync_material_processor.get_sync_http_client", lambda: _HTTP()
    )

    payload = {
        "urls": [
            {
                "url": "https://example.com/a.jpg",
                "type": "image",
                "context": "c1",
                "position": 10,
            },
        ]
    }
    r = client.post(
        "/internal/materials/download-and-organize",
        json=payload,
        headers={"x-test-token": "test-token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["count"] == 1
    assert data["results"][0]["file_type"] == "image"
