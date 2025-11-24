import os

import pytest
from fastapi.testclient import TestClient

from main import app

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _ensure_token(token: str):
    os.environ["INTERNAL_TEST_TOKEN"] = token
    # 强制重载 settings，使运行时读取到新 token
    from importlib import reload

    import config as _cfg

    reload(_cfg)


# 统一在本模块内设置测试专用 Token，避免外部 export
TOKEN = "test-token"


@pytest.fixture(scope="module", autouse=True)
def _set_internal_token_once():
    _ensure_token(TOKEN)


@pytest.mark.skipif(os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled")
def test_live_analyze_image_with_context():
    """
    受控真连网测试：使用真实图片与上下文，验证内部评估接口的端到端行为。
    需设置：
      - INTERNAL_TEST_TOKEN=test-token
      - OpenAI/Gemini 等必要环境变量
      - RUN_LIVE_AI_TESTS=1 才会执行
    """
    client = TestClient(app)

    payload = {
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Cat03.jpg",
        "context_before": "本文介绍一款全新的智能手机，其摄像头具有出色的低光表现。",
        "context_after": "下面将进一步展示它的拍照样张和细节表现。",
        "surrounding_paragraph": "评测章节：外观与影像系统",
        "resolution": "unknown",
    }
    r = client.post(
        "/internal/analyzer/analyze-image",
        json=payload,
        headers={"x-test-token": TOKEN},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert isinstance(data.get("result", {}).get("description"), str)
    assert len(data["result"]["description"]) > 10


@pytest.mark.skipif(os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled")
def test_live_extract_and_download_materials():
    """
    受控真连网测试：调用内部素材接口进行提取与下载（对下载接口可按需保留/跳过）。
    """
    client = TestClient(app)

    md = (
        "# 测试文档\n\n"
        "这里有一张图片：![图1](https://upload.wikimedia.org/wikipedia/commons/3/3a/Cat03.jpg)\n\n"
        "以及一个演示视频链接：https://file-examples.com/storage/fe1e0f2fe/sample_960x540.mp4\n"
    )

    r = client.post(
        "/internal/materials/extract-media",
        json={"content_markdown": md},
        headers={"x-test-token": TOKEN},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["stats"]["image_count"] >= 1

    # 可选：实际下载测试（可能较慢/不稳定，可按需启用）
    urls = []
    for img in data.get("images", [])[:1]:
        urls.append(
            {
                "url": img["url"],
                "type": "image",
                "context": img.get("surrounding_paragraph", ""),
                "position": img.get("position", 0),
            }
        )

    if urls:
        r2 = client.post(
            "/internal/materials/download-and-organize",
            json={"urls": urls},
            headers={"x-test-token": TOKEN},
        )
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        assert d2["ok"] is True
        assert d2["count"] >= 1
