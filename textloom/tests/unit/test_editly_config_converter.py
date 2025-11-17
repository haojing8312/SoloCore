"""
单元测试 - EditlyConfigConverter

测试目标：
- 数据转换功能
- 场景 → Clip 映射
- 组件 → Layer 映射
- 配置验证

作者: Claude
创建: 2025-11-17
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.editly_config_converter import EditlyConfigConverter


class TestEditlyConfigConverter:
    """EditlyConfigConverter 单元测试"""

    def setup_method(self):
        """每个测试前执行"""
        self.converter = EditlyConfigConverter()

    def test_base_config_structure(self):
        """测试基础配置结构"""
        config = self.converter._build_base_config("./output.mp4")

        assert config["outPath"] == "./output.mp4"
        assert config["width"] == 1080
        assert config["height"] == 1920
        assert config["fps"] == 30
        assert "defaults" in config
        assert "clips" in config
        assert config["clips"] == []

        print("✅ 基础配置结构正确")

    def test_scene_to_clip_conversion(self):
        """测试场景到 Clip 的转换"""
        scene = {
            "scene_id": 1,
            "narration": "测试旁白",
            "duration": 5,
        }

        media_map = {}
        clip = self.converter._convert_scene_to_clip(scene, media_map, 0)

        assert clip["duration"] == 5
        assert isinstance(clip["layers"], list)
        assert len(clip["layers"]) >= 1  # 至少有背景层

        print("✅ Scene → Clip 转换正确")

    def test_background_layer_creation(self):
        """测试背景层创建"""
        scene = {}
        layer = self.converter._create_background_layer(scene)

        assert layer is not None
        assert layer["type"] == "fill-color"
        assert "color" in layer

        print("✅ 背景层创建正确")

    def test_subtitle_text_extraction(self):
        """测试字幕文本提取"""
        # 从 textDriver 提取
        scene1 = {
            "textDriver": {"textJson": "来自 textDriver 的字幕"}
        }
        text1 = self.converter._extract_subtitle_text(scene1)
        assert text1 == "来自 textDriver 的字幕"

        # 从 narration 提取
        scene2 = {
            "narration": "来自 narration 的字幕"
        }
        text2 = self.converter._extract_subtitle_text(scene2)
        assert text2 == "来自 narration 的字幕"

        # 优先级：textDriver > narration
        scene3 = {
            "textDriver": {"textJson": "优先文本"},
            "narration": "次要文本"
        }
        text3 = self.converter._extract_subtitle_text(scene3)
        assert text3 == "优先文本"

        print("✅ 字幕文本提取正确")

    def test_config_validation(self):
        """测试配置验证"""
        # 有效配置
        valid = {
            "outPath": "./out.mp4",
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "clips": [{}]
        }
        assert self.converter.validate_config(valid) is True

        # 缺少必需字段
        invalid1 = {"width": 1080}
        assert self.converter.validate_config(invalid1) is False

        # clips 为空
        invalid2 = {
            "outPath": "./out.mp4",
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "clips": []
        }
        assert self.converter.validate_config(invalid2) is False

        print("✅ 配置验证逻辑正确")

    def test_supported_transitions(self):
        """测试支持的转场列表"""
        transitions = self.converter.get_supported_transitions()

        assert len(transitions) > 0
        assert "fade" in transitions
        assert "crosswarp" in transitions
        assert "directionalwipe" in transitions

        print(f"✅ 支持 {len(transitions)} 种转场")

    def test_full_conversion(self):
        """测试完整转换流程"""
        script_data = {
            "scenes": [
                {
                    "scene_id": 1,
                    "narration": "第一个场景",
                    "duration": 3,
                },
                {
                    "scene_id": 2,
                    "narration": "第二个场景",
                    "duration": 4,
                },
            ]
        }

        media_files = []
        output_path = "./test.mp4"

        config = self.converter.convert(script_data, media_files, output_path)

        assert config["outPath"] == output_path
        assert len(config["clips"]) == 2
        assert config["clips"][0]["duration"] == 3
        assert config["clips"][1]["duration"] == 4

        print("✅ 完整转换流程正确")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
