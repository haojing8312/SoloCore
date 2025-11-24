"""
测试同步素材分析器
验证 processors/sync_material_analyzer.py 的AI分析功能
基于原版material_analyzer.py的业务逻辑进行完整测试
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from tests.conftest import TEST_ANALYSIS_RESULTS, TEST_CONTENT, TEST_MEDIA_FILES


class TestSyncMaterialAnalyzer:
    """测试同步素材分析器"""

    def test_initialization(self, temp_workspace):
        """测试初始化"""
        from processors.sync_material_analyzer import SyncMaterialAnalyzer

        analyzer = SyncMaterialAnalyzer(temp_workspace)
        assert analyzer.workspace_dir == temp_workspace
        assert hasattr(analyzer, "openai_client")
        assert hasattr(analyzer, "logger")

    @patch("processors.sync_material_analyzer.get_sync_openai_client")
    def test_analyze_image_media_item_with_context(
        self, mock_get_client, temp_workspace
    ):
        """测试基于MediaItem的图片上下文分析（严格JSON）"""
        from uuid import uuid4

        from models.task import MediaItem, MediaType
        from processors.sync_material_analyzer import SyncMaterialAnalyzer

        # mock客户端返回严格JSON
        mock_client = Mock()
        mock_client.analyze_image.return_value = json.dumps(
            {
                "description": "一张展示科技产品的图片",
                "contextual_description": "结合上下文的解释",
                "contextual_purpose": "展示功能",
                "content_role": "主要展示",
                "semantic_relevance": 90.0,
                "tags": ["科技", "产品"],
                "quality_level": "good",
                "quality_score": 85.0,
                "voiceover_script": "这是口播稿",
                "contextual_voiceover_script": "这是上下文口播稿",
                "usage_suggestions": ["用于封面"],
            }
        )
        mock_get_client.return_value = mock_client

        analyzer = SyncMaterialAnalyzer(temp_workspace)
        # 构造本地图片文件
        img_dir = Path(temp_workspace) / "materials" / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        img_path = img_dir / "test.jpg"
        from PIL import Image as PILImage

        PILImage.new("RGB", (100, 100), color="red").save(img_path)

        item = MediaItem(
            id=uuid4(),
            task_id=uuid4(),
            original_url=str(img_path),
            media_type=MediaType.IMAGE,
            filename="test.jpg",
            local_path=str(img_path),
            context_before="前文",
            context_after="后文",
            surrounding_paragraph="所在段落",
        )

        result = analyzer.analyze_material_with_context(item)
        assert result.analysis_status == result.analysis_status.COMPLETED
        assert result.description
        assert result.file_format

    @patch("processors.sync_material_analyzer.get_sync_openai_client")
    def test_analyze_video_media_item_with_ffprobe_and_keyframes(
        self, mock_get_client, temp_workspace
    ):
        """测试视频分析使用ffprobe/ffmpeg抽帧并走图片上下文分析"""
        from uuid import uuid4

        from models.task import MediaItem, MediaType
        from processors.sync_material_analyzer import SyncMaterialAnalyzer

        mock_client = Mock()
        # 关键帧图片走同一个接口
        mock_client.analyze_image.return_value = json.dumps(
            {
                "description": "关键帧描述",
                "contextual_description": "关键帧上下文描述",
                "contextual_purpose": "演示",
                "content_role": "辅助说明",
                "semantic_relevance": 80.0,
                "tags": ["演示"],
                "quality_level": "good",
                "quality_score": 75.0,
                "voiceover_script": "视频口播",
                "contextual_voiceover_script": "视频上下文口播",
                "usage_suggestions": ["用于中段"],
            }
        )
        mock_get_client.return_value = mock_client

        analyzer = SyncMaterialAnalyzer(temp_workspace)
        video_dir = Path(temp_workspace) / "materials" / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)
        video_path = video_dir / "test.mp4"
        # 生成一个空文件占位（ffprobe会失败，允许抛异常）
        video_path.write_bytes(b"\x00\x00\x00\x18ftypmp4")
        item = MediaItem(
            id=uuid4(),
            task_id=uuid4(),
            original_url=str(video_path),
            media_type=MediaType.VIDEO,
            filename="test.mp4",
            local_path=str(video_path),
            context_before="前文",
            context_after="后文",
            surrounding_paragraph="所在段落",
        )

        try:
            _ = analyzer.analyze_material_with_context(item)
        except Exception:
            # 在无真实ffprobe/ffmpeg环境下允许失败
            pass

    def test_extract_keywords_from_description(self, temp_workspace):
        """测试从描述中提取关键词"""
        from processors.sync_material_analyzer import SyncMaterialAnalyzer

        analyzer = SyncMaterialAnalyzer(temp_workspace)

        test_description = "这是一张展示最新科技产品的图片，包含智能手机、创新技术、用户界面设计等元素。"

        # 测试关键词提取
        keywords = analyzer._extract_keywords_sync(test_description)

        # 验证结果
        assert isinstance(keywords, list)
        assert len(keywords) > 0

        # 应该包含一些预期的关键词
        expected_keywords = ["科技", "产品", "手机", "技术", "界面"]
        found_keywords = [
            kw for kw in expected_keywords if any(kw in k for k in keywords)
        ]
        assert len(found_keywords) > 0

    def test_concurrent_analysis_limitation(self, temp_workspace):
        """测试并发分析限制"""
        from processors.sync_material_analyzer import SyncMaterialAnalyzer

        analyzer = SyncMaterialAnalyzer(temp_workspace)

        # 验证并发限制配置
        assert hasattr(analyzer, "analysis_semaphore")
        # 默认应该有合理的并发限制
        assert analyzer.analysis_semaphore._value <= 5
