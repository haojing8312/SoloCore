"""
PyCaps动态字幕功能集成测试
测试基于PyCaps的动态字幕生成系统的端到端流程
"""

import os
from importlib import reload

import pytest
from fastapi.testclient import TestClient

import config as _cfg
from main import app

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _ensure_token(token: str):
    """确保测试token设置正确"""
    os.environ["INTERNAL_TEST_TOKEN"] = token
    reload(_cfg)


TOKEN = "test-token"


@pytest.fixture(scope="module", autouse=True)
def _set_internal_token_once():
    """设置测试token"""
    _ensure_token(TOKEN)


class TestDynamicSubtitlesIntegration:
    """PyCaps动态字幕集成测试类"""

    # 测试用的真实视频和字幕URL
    TEST_VIDEO_URL = "https://res.bifrostv.com/easegen-core/video/20250819/1755614329910949574_1755614683357432_scenes_only.mp4"
    TEST_SUBTITLE_URL = "https://res.bifrostv.com/easegen-core/subtitle/20250819/1755614329910949574_1755614683357432.srt"

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_get_pycaps_templates(self, client):
        """测试获取PyCaps模板列表"""
        response = client.get("/dynamic-subtitles/templates")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "templates" in data
        assert "total" in data

        templates = data["templates"]
        assert len(templates) > 0
        
        # 验证常用模板存在
        template_names = [t for t in templates]
        assert "hype" in template_names or "minimalist" in template_names or "explosive" in template_names

    def test_get_pycaps_config(self, client):
        """测试获取PyCaps配置"""
        response = client.get("/dynamic-subtitles/config")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "config" in data

        config = data["config"]
        assert "enabled" in config
        assert "engine" in config
        assert config["engine"] == "PyCaps"

    @pytest.mark.skipif(
        os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled"
    )
    def test_process_pycaps_subtitles_hype_style(self, client):
        """测试PyCaps hype模板字幕处理"""
        payload = {
            "video_url": self.TEST_VIDEO_URL,
            "subtitles_url": self.TEST_SUBTITLE_URL,
            "template": "hype"
        }

        response = client.post(
            "/dynamic-subtitles/process",
            json=payload,
            headers={"x-test-token": TOKEN},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "video_url" in data
        assert "template" in data
        assert data["template"] == "hype"
        assert data["processed"] is True
        
        # 验证返回的视频URL
        assert data["video_url"].startswith("http")
        assert "original_video_url" in data

    @pytest.mark.skipif(
        os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled"
    )
    def test_process_pycaps_subtitles_minimalist_style(self, client):
        """测试PyCaps minimalist模板字幕处理"""
        payload = {
            "video_url": self.TEST_VIDEO_URL,
            "subtitles_url": self.TEST_SUBTITLE_URL,
            "template": "minimalist"
        }

        response = client.post(
            "/dynamic-subtitles/process",
            json=payload,
            headers={"x-test-token": TOKEN},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["template"] == "minimalist"
        assert data["processed"] is True

    @pytest.mark.skipif(
        os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled"
    )
    def test_process_pycaps_subtitles_explosive_style(self, client):
        """测试PyCaps explosive模板字幕处理"""
        payload = {
            "video_url": self.TEST_VIDEO_URL,
            "subtitles_url": self.TEST_SUBTITLE_URL,
            "template": "explosive"
        }

        response = client.post(
            "/dynamic-subtitles/process",
            json=payload,
            headers={"x-test-token": TOKEN},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["template"] == "explosive"
        assert data["processed"] is True

    def test_process_pycaps_subtitles_invalid_token(self, client):
        """测试无效token的错误处理"""
        payload = {
            "video_url": self.TEST_VIDEO_URL,
            "subtitles_url": self.TEST_SUBTITLE_URL,
            "template": "hype"
        }

        response = client.post(
            "/dynamic-subtitles/process",
            json=payload,
            headers={"x-test-token": "invalid-token"},
        )

        assert response.status_code == 403
        assert "需要有效的测试token" in response.json()["detail"]

    def test_process_pycaps_subtitles_missing_token(self, client):
        """测试缺少token的错误处理"""
        payload = {
            "video_url": self.TEST_VIDEO_URL,
            "subtitles_url": self.TEST_SUBTITLE_URL,
            "template": "hype"
        }

        response = client.post("/dynamic-subtitles/process", json=payload)

        assert response.status_code == 403

    @pytest.mark.skipif(
        os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled"
    )
    def test_process_pycaps_subtitles_invalid_urls(self, client):
        """测试无效URL的错误处理"""
        payload = {
            "video_url": "https://invalid-url.com/nonexistent.mp4",
            "subtitles_url": "https://invalid-url.com/nonexistent.srt",
            "template": "hype"
        }

        response = client.post(
            "/dynamic-subtitles/process",
            json=payload,
            headers={"x-test-token": TOKEN},
        )

        assert response.status_code == 500
        assert "PyCaps处理失败" in response.json()["detail"]

    def test_check_pycaps_status(self, client):
        """测试PyCaps状态检查端点"""
        response = client.get(
            "/dynamic-subtitles/test/pycaps-status",
            headers={"x-test-token": TOKEN}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "pycaps_available" in data
        assert "dependencies" in data
        assert "config" in data
        assert "templates" in data


@pytest.mark.skipif(os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled")
def test_end_to_end_pycaps_processing():
    """PyCaps端到端字幕处理流程测试"""
    client = TestClient(app)

    # 1. 获取模板列表
    templates_response = client.get("/dynamic-subtitles/templates")
    assert templates_response.status_code == 200

    templates_data = templates_response.json()
    templates = templates_data["templates"]
    assert len(templates) > 0

    # 选择第一个可用模板
    template_name = templates[0]

    # 2. 使用模板处理字幕
    payload = {
        "video_url": "https://res.bifrostv.com/easegen-core/video/20250819/1755614329910949574_1755614683357432_scenes_only.mp4",
        "subtitles_url": "https://res.bifrostv.com/easegen-core/subtitle/20250819/1755614329910949574_1755614683357432.srt",
        "template": template_name
    }

    process_response = client.post(
        "/dynamic-subtitles/process",
        json=payload,
        headers={"x-test-token": TOKEN},
    )

    assert process_response.status_code == 200
    result = process_response.json()

    # 3. 验证处理结果
    assert result["success"] is True
    assert "video_url" in result
    assert "template" in result
    assert result["template"] == template_name
    assert result["processed"] is True

    # 4. 验证输出视频URL
    assert result["video_url"].startswith("http")
    assert "original_video_url" in result

    print(f"✅ PyCaps端到端测试成功，使用模板: {template_name}，生成视频: {result['video_url']}")


if __name__ == "__main__":
    # 允许直接运行测试脚本进行快速验证
    import sys

    # 设置测试环境变量
    os.environ["RUN_LIVE_AI_TESTS"] = "1"
    os.environ["INTERNAL_TEST_TOKEN"] = "test-token"

    # 运行单个测试
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        print("运行PyCaps快速测试...")
        _ensure_token("test-token")
        client = TestClient(app)

        # 快速模板列表测试
        response = client.get("/dynamic-subtitles/templates")
        if response.status_code == 200:
            print("✅ PyCaps模板列表测试通过")
            templates = response.json()["templates"]
            print(f"   可用模板: {templates}")
        else:
            print(f"❌ 模板列表测试失败: {response.status_code}")
            sys.exit(1)

        # 快速配置测试
        response = client.get("/dynamic-subtitles/config")
        if response.status_code == 200:
            print("✅ PyCaps配置测试通过")
        else:
            print(f"❌ 配置测试失败: {response.status_code}")
            sys.exit(1)

        print("快速测试完成！使用 pytest 运行完整集成测试。")
    else:
        print("使用 pytest 命令运行完整测试:")
        print(
            "RUN_LIVE_AI_TESTS=1 pytest tests/integration/test_dynamic_subtitles_live.py -v"
        )
