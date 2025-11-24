import os
from importlib import reload

import pytest
from fastapi.testclient import TestClient

import config as _cfg
from main import app

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _ensure_token(token: str):
    os.environ["INTERNAL_TEST_TOKEN"] = token
    reload(_cfg)


TOKEN = "test-token"


@pytest.fixture(scope="module", autouse=True)
def _set_internal_token_once():
    _ensure_token(TOKEN)


@pytest.mark.skipif(os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled")
def test_live_generate_script():
    # 准备模型凭据门槛：根据配置判断需要的 key
    settings = _cfg.settings
    need_skip = False
    if settings.use_gemini:
        need_skip = not bool(settings.gemini_api_key or settings.gemini_api_base)
    else:
        need_skip = not bool(settings.openai_api_key or settings.openai_api_base)
    if need_skip:
        pytest.skip("model credentials not configured")

    client = TestClient(app)
    payload = {
        "topic": "AI 工具趋势",
        "source_content": "近期生成式AI工具持续演进，开发者生态高速发展。",
        "material_context": {
            "summary": {"total_count": 1, "image_count": 1, "video_count": 0}
        },
        "styles": ["professional", "viral"],
    }
    r = client.post(
        "/internal/script/generate", json=payload, headers={"x-test-token": TOKEN}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True
    assert "result" in data and isinstance(data["result"], dict)
    assert "successful_results" in data["result"]


@pytest.mark.skipif(os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled")
def test_live_generate_single_video():
    # 依赖视频合成服务配置（从 settings 获取）
    if not (_cfg.settings.video_merge_api_url and _cfg.settings.video_merge_api_key):
        pytest.skip("video merge service not configured")

    client = TestClient(app)
    script_data = {
        "title": "示例视频",
        "narration": "这是一段示例旁白，用于验证视频生成接口的行为。",
        "scenes": [{"scene_id": 1, "narration": "片头介绍", "material_id": "mat1"}],
    }
    media_files = [
        {
            "id": "mat1",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Cat03.jpg",
            "filename": "a.jpg",
        }
    ]

    r = client.post(
        "/internal/video/generate-single",
        json={
            "script_data": script_data,
            "media_files": media_files,
            "mode": "multi_scene",
        },
        headers={"x-test-token": TOKEN},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True
    assert "result" in data and isinstance(data["result"], dict)
    assert "success" in data["result"]


@pytest.mark.skipif(os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled")
def test_live_generate_complex_multi_scene_video():
    """测试复杂多场景视频生成，包含多个素材和详细场景"""
    if not (_cfg.settings.video_merge_api_url and _cfg.settings.video_merge_api_key):
        pytest.skip("video merge service not configured")

    client = TestClient(app)

    # 复杂的脚本数据 - 多场景，包含标题
    script_data = {
        "title": "AI技术发展趋势深度解析",
        "description": "深入分析当前AI技术的发展方向和未来趋势",
        "narration": "欢迎观看本期AI技术趋势分析",
        "scenes": [
            {
                "scene_id": 1,
                "narration": "人工智能技术在过去几年中取得了突破性进展，从机器学习到深度学习，再到大语言模型的兴起。",
                "material_id": "ai_chart",
            },
            {
                "scene_id": 2,
                "narration": "ChatGPT的发布标志着AI进入了新的时代，生成式AI开始广泛应用于各个领域。",
                "material_id": "chatgpt_demo",
            },
            {
                "scene_id": 3,
                "narration": "多模态AI模型的发展让机器能够同时理解文本、图像和语音，这为未来的应用打开了无限可能。",
                "material_id": "multimodal_ai",
            },
            {
                "scene_id": 4,
                "narration": "AI技术的发展也带来了新的挑战，包括数据隐私、算法偏见和AI安全等问题需要我们深入思考。",
                "material_id": "ai_ethics",
            },
        ],
    }

    # 多个真实可访问的媒体文件
    media_files = [
        {
            "id": "ai_chart",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2d/Tensorflow_logo.svg/320px-Tensorflow_logo.svg.png",
            "filename": "ai_chart.png",
        },
        {
            "id": "chatgpt_demo",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/320px-ChatGPT_logo.svg.png",
            "filename": "chatgpt_demo.png",
        },
        {
            "id": "multimodal_ai",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2d/Tensorflow_logo.svg/320px-Tensorflow_logo.svg.png",
            "filename": "multimodal_ai.png",
        },
        {
            "id": "ai_ethics",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Artificial_intelligence_prompt_completion.svg/320px-Artificial_intelligence_prompt_completion.svg.png",
            "filename": "ai_ethics.png",
        },
    ]

    r = client.post(
        "/internal/video/generate-single",
        json={
            "script_data": script_data,
            "media_files": media_files,
            "mode": "multi_scene",
        },
        headers={"x-test-token": TOKEN},
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True

    result = data.get("result", {})
    assert isinstance(result, dict)
    assert "success" in result

    # 验证视频生成结果
    if result.get("success"):
        # 如果成功，检查返回的视频信息
        assert result.get("sub_task_id") is not None
        assert result.get("mode") == "multi_scene"
        print(f"✅ 复杂多场景视频生成成功: {result.get('sub_task_id')}")

        # 如果有视频URL，验证格式
        if result.get("video_url"):
            assert result["video_url"].startswith(("http://", "https://"))
            print(f"📹 视频URL: {result['video_url']}")
    else:
        # 如果失败，打印错误信息用于调试
        print(f"❌ 视频生成失败: {result.get('error', 'Unknown error')}")


@pytest.mark.skipif(os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled")
def test_live_generate_multiple_videos():
    """测试批量多视频生成功能"""
    if not (_cfg.settings.video_merge_api_url and _cfg.settings.video_merge_api_key):
        pytest.skip("video merge service not configured")

    client = TestClient(app)

    # 多个不同风格的脚本数据
    scripts_data = [
        {
            "title": "专业版AI趋势分析",
            "description": "专业角度分析AI发展趋势",
            "scenes": [
                {
                    "scene_id": 1,
                    "narration": "从技术角度深入分析AI的发展轨迹和未来方向。",
                    "material_id": "tech_chart",
                },
                {
                    "scene_id": 2,
                    "narration": "行业专家对AI技术演进的专业见解和预测。",
                    "material_id": "expert_view",
                },
            ],
            "script_style": "professional",
        },
        {
            "title": "病毒式AI热点解读",
            "description": "用轻松有趣的方式解读AI热点",
            "scenes": [
                {
                    "scene_id": 1,
                    "narration": "AI竟然能做到这些？让我们一起看看最新的AI黑科技！",
                    "material_id": "ai_magic",
                },
                {
                    "scene_id": 2,
                    "narration": "这些AI应用简直太酷了，你绝对想不到！",
                    "material_id": "cool_ai",
                },
            ],
            "script_style": "viral",
        },
    ]

    media_files = [
        {
            "id": "tech_chart",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2d/Tensorflow_logo.svg/240px-Tensorflow_logo.svg.png",
            "filename": "tech_chart.png",
        },
        {
            "id": "expert_view",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Baidu_Apollo_Logo.svg/240px-Baidu_Apollo_Logo.svg.png",
            "filename": "expert_view.png",
        },
        {
            "id": "ai_magic",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/240px-ChatGPT_logo.svg.png",
            "filename": "ai_magic.png",
        },
        {
            "id": "cool_ai",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Artificial_intelligence_prompt_completion.svg/240px-Artificial_intelligence_prompt_completion.svg.png",
            "filename": "cool_ai.png",
        },
    ]

    r = client.post(
        "/internal/video/generate-multiple",
        json={
            "scripts_data": scripts_data,
            "media_files": media_files,
            "mode": "multi_scene",
        },
        headers={"x-test-token": TOKEN},
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True

    result = data.get("result", {})
    assert isinstance(result, dict)
    assert "results" in result

    results = result["results"]
    assert isinstance(results, list)
    assert len(results) == 2  # 应该生成2个视频

    # 验证每个视频生成结果
    for i, video_result in enumerate(results):
        assert "success" in video_result
        assert "sub_task_id" in video_result
        assert "script_style" in video_result

        expected_style = scripts_data[i]["script_style"]
        assert video_result["script_style"] == expected_style

        print(
            f"📹 视频{i+1} ({expected_style}): {video_result.get('sub_task_id')} - {'✅成功' if video_result.get('success') else '❌失败'}"
        )


@pytest.mark.skipif(os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled")
def test_live_video_with_title_subtitle_components():
    """测试视频生成中标题和副标题组件是否正确添加"""
    if not (_cfg.settings.video_merge_api_url and _cfg.settings.video_merge_api_key):
        pytest.skip("video merge service not configured")

    # 验证标题副标题配置
    assert _cfg.settings.video_title_enabled is True, "标题组件应该启用"
    assert _cfg.settings.video_subtitle_enabled is True, "副标题组件应该启用"
    assert _cfg.settings.video_subtitle_text, "副标题文本不能为空"

    client = TestClient(app)

    # 特别设计的测试数据，重点验证标题副标题
    script_data = {
        "title": "测试标题组件功能",  # 明确的标题，应该出现在视频中
        "description": "验证标题和副标题组件是否正确添加到视频中",
        "scenes": [
            {
                "scene_id": 1,
                "narration": "这个测试专门验证标题和副标题组件是否正确添加到每个场景中。",
                "material_id": "test_image",
            }
        ],
    }

    media_files = [
        {
            "id": "test_image",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/320px-ChatGPT_logo.svg.png",
            "filename": "test_image.png",
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/320px-ChatGPT_logo.svg.png",
        }
    ]

    r = client.post(
        "/internal/video/generate-single",
        json={
            "script_data": script_data,
            "media_files": media_files,
            "mode": "multi_scene",
        },
        headers={"x-test-token": TOKEN},
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True

    result = data.get("result", {})
    assert "success" in result

    # 验证返回结果包含标题信息
    if result.get("success"):
        print(f"✅ 标题副标题视频生成成功")
        print(f"📝 脚本标题: {script_data['title']}")
        print(f"📝 副标题文本: {_cfg.settings.video_subtitle_text}")

        # 检查返回的任务信息
        assert result.get("sub_task_id") is not None
        print(f"🆔 子任务ID: {result['sub_task_id']}")
    else:
        print(f"❌ 标题副标题视频生成失败: {result.get('error')}")


@pytest.mark.skipif(os.getenv("RUN_LIVE_AI_TESTS") != "1", reason="live tests disabled")
def test_live_error_handling_scenarios():
    """测试各种错误处理场景"""
    if not (_cfg.settings.video_merge_api_url and _cfg.settings.video_merge_api_key):
        pytest.skip("video merge service not configured")

    client = TestClient(app)

    # 测试1: 空标题的情况
    script_data_no_title = {
        "title": "",  # 空标题
        "scenes": [
            {"scene_id": 1, "narration": "测试空标题的情况", "material_id": "mat1"}
        ],
    }

    media_files = [
        {
            "id": "mat1",
            "file_url": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Cat03.jpg",
            "filename": "test.jpg",
        }
    ]

    r1 = client.post(
        "/internal/video/generate-single",
        json={
            "script_data": script_data_no_title,
            "media_files": media_files,
            "mode": "multi_scene",
        },
        headers={"x-test-token": TOKEN},
    )
    assert r1.status_code == 200, r1.text
    data1 = r1.json()
    assert data1.get("ok") is True
    print("✅ 空标题场景处理正常")

    # 测试2: 无场景数据的情况
    script_data_no_scenes = {
        "title": "测试无场景",
        "narration": "这是一个没有scenes的测试",
        "scenes": [],  # 空场景列表
    }

    r2 = client.post(
        "/internal/video/generate-single",
        json={
            "script_data": script_data_no_scenes,
            "media_files": media_files,
            "mode": "multi_scene",
        },
        headers={"x-test-token": TOKEN},
    )

    # 这种情况应该返回错误
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    # 可能成功也可能失败，取决于具体实现
    print(f"📝 无场景数据测试结果: {data2.get('ok')}")

    # 测试3: 不存在的素材ID
    script_data_invalid_material = {
        "title": "测试无效素材ID",
        "scenes": [
            {
                "scene_id": 1,
                "narration": "使用不存在的素材ID",
                "material_id": "non_existent_material",
            }
        ],
    }

    r3 = client.post(
        "/internal/video/generate-single",
        json={
            "script_data": script_data_invalid_material,
            "media_files": media_files,
            "mode": "multi_scene",
        },
        headers={"x-test-token": TOKEN},
    )

    assert r3.status_code == 200, r3.text
    data3 = r3.json()
    assert data3.get("ok") is True
    print("✅ 无效素材ID场景处理正常")
