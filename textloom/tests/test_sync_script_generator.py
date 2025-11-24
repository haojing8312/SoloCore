"""
测试同步脚本生成器（对齐异步版业务语义）
验证 services/sync_script_generator.py 的提示词构建、解析与多风格生成功能
"""

import json
from unittest.mock import Mock, patch

import pytest

from models.script_generation import ScriptStyle
from tests.conftest import TEST_CONTENT


class TestSyncScriptGenerator:
    """测试同步脚本生成器"""

    def test_generate_single_script_sync_success(self):
        """单风格生成成功，结构与字段对齐异步版"""
        from services.sync_script_generator import SyncScriptGenerator

        # 准备mock
        with (
            patch(
                "services.sync_script_generator.get_sync_gemini_client"
            ) as gemini_mock,
            patch(
                "services.sync_script_generator.sync_create_script_content"
            ) as create_mock,
            patch(
                "services.sync_script_generator.sync_get_persona_by_id"
            ) as persona_mock,
            patch(
                "services.sync_script_generator.sync_get_prompt_templates_by_type_and_style"
            ) as tmpl_mock,
            patch(
                "services.sync_script_generator.sync_update_script_content", create=True
            ) as update_mock,
        ):

            gemini_mock.return_value.generate_script.return_value = json.dumps(
                {
                    "titles": ["标题1", "标题2", "标题3"],
                    "narration": "这是测试旁白内容。",
                    "material_mapping": {
                        "m1": {
                            "type": "image",
                            "description": "图",
                            "timing": "0-5s",
                            "scene_usage": "开头",
                        }
                    },
                    "scenes": [
                        {
                            "scene_id": 1,
                            "timing": "0-5s",
                            "narration": "段1。",
                            "material_id": "m1",
                            "description": "场景",
                        }
                    ],
                    "description": "描述",
                    "tags": ["tag1"],
                    "estimated_duration": 60,
                }
            )
            create_mock.return_value = {"id": "script-1"}
            persona_mock.return_value = {"id": 1, "name": "测试人设"}
            tmpl_mock.return_value = []  # 无模板时回落到内置提示

            gen = SyncScriptGenerator()
            result = gen._generate_single_script_sync(
                task_id="t1",
                topic="测试主题",
                source_content=TEST_CONTENT,
                style=ScriptStyle.DEFAULT,
                creator_id="u1",
                persona={"id": 1, "name": "测试人设"},
                user_requirements="尽量简洁",
                material_context={},
            )

            assert result["script_id"] == "script-1"
            assert result["task_id"] == "t1"
            assert result["script_style"] == ScriptStyle.DEFAULT.value
            assert isinstance(result["titles"], list) and len(result["titles"]) == 3
            assert result["narration"]
            assert isinstance(result["material_mapping"], dict)
            assert isinstance(result["scenes"], list) and len(result["scenes"]) == 1
            assert result["generation_status"] == "completed"
            update_mock.assert_called_once()

    def test_generate_multi_scripts_sync_success(self):
        """多风格生成，计数与风格列表正确"""
        from services.sync_script_generator import SyncScriptGenerator

        with (
            patch(
                "services.sync_script_generator.get_sync_gemini_client"
            ) as gemini_mock,
            patch(
                "services.sync_script_generator.sync_create_script_content"
            ) as create_mock,
            patch(
                "services.sync_script_generator.sync_get_prompt_templates_by_type_and_style"
            ) as tmpl_mock,
        ):

            gemini_mock.return_value.generate_script.return_value = json.dumps(
                {
                    "titles": ["A", "B", "C"],
                    "narration": "内容。",
                    "material_mapping": {},
                    "scenes": [],
                    "description": "",
                    "tags": [],
                    "estimated_duration": 60,
                }
            )
            # 每次创建不同的id便于断言
            create_mock.side_effect = ({"id": "s-1"}, {"id": "s-2"})
            tmpl_mock.return_value = []

            gen = SyncScriptGenerator()
            batch = gen.generate_multi_scripts_sync(
                task_id="t2",
                topic="多风格",
                source_content=TEST_CONTENT,
                material_context={},
                persona_id=None,
                styles=[ScriptStyle.DEFAULT, ScriptStyle.PRODUCT_GEEK],
            )

            assert batch["task_id"] == "t2"
            assert batch["requested_styles"] == [
                ScriptStyle.DEFAULT.value,
                ScriptStyle.PRODUCT_GEEK.value,
            ]
            assert batch["total_count"] == 2
            assert batch["success_count"] == 2
            assert batch["failure_count"] == 0
            assert len(batch["successful_results"]) == 2
            ids = {r["script_id"] for r in batch["successful_results"]}
            assert ids == {"s-1", "s-2"}

    def test_generate_single_script_sync_failure_when_gemini_returns_none(self):
        """当Gemini返回None时，单脚本生成应抛出异常，外层批量结果计入失败"""
        from services.sync_script_generator import SyncScriptGenerator

        with (
            patch(
                "services.sync_script_generator.get_sync_gemini_client"
            ) as gemini_mock,
            patch(
                "services.sync_script_generator.sync_create_script_content"
            ) as create_mock,
            patch(
                "services.sync_script_generator.sync_get_prompt_templates_by_type_and_style"
            ) as tmpl_mock,
        ):

            # Gemini返回None
            gemini_mock.return_value.generate_script.return_value = None
            create_mock.return_value = {"id": "script-x"}
            tmpl_mock.return_value = []

            gen = SyncScriptGenerator()
            with pytest.raises(Exception):
                gen._generate_single_script_sync(
                    task_id="t-fail",
                    topic="主题",
                    source_content="内容",
                    style=ScriptStyle.DEFAULT,
                )

    def test_generate_multi_scripts_sync_collects_failures(self):
        """批量生成时，Gemini失败应计入failed_results且不影响其他风格统计逻辑"""
        from services.sync_script_generator import SyncScriptGenerator

        with (
            patch(
                "services.sync_script_generator.get_sync_gemini_client"
            ) as gemini_mock,
            patch(
                "services.sync_script_generator.sync_create_script_content"
            ) as create_mock,
            patch(
                "services.sync_script_generator.sync_get_prompt_templates_by_type_and_style"
            ) as tmpl_mock,
        ):

            # 统一返回None，制造失败
            gemini_mock.return_value.generate_script.return_value = None
            create_mock.side_effect = ({"id": "s1"}, {"id": "s2"})
            tmpl_mock.return_value = []

            gen = SyncScriptGenerator()
            batch = gen.generate_multi_scripts_sync(
                task_id="t3",
                topic="T",
                source_content="content",
                styles=[ScriptStyle.DEFAULT],
            )

            assert batch["total_count"] == 1
            assert batch["success_count"] == 0
            assert batch["failure_count"] == 1
            assert len(batch["failed_results"]) == 1

    def test_parse_generated_script_sync_variants(self):
        """解析器兼容markdown代码块与直文本JSON，并补全scenes字段"""
        from services.sync_script_generator import SyncScriptGenerator

        gen = SyncScriptGenerator()
        md_json = """
```json
{
  "titles": ["T1"],
  "narration": "N。",
  "material_mapping": {"m1": {"type": "image", "description": "d", "timing": "0-5s", "scene_usage": "开头"}},
  "scenes": [{"narration": "段。", "material_id": "m1"}],
  "description": "D", "tags": ["t"], "estimated_duration": 60
}
```
"""
        parsed = gen._parse_generated_script_sync(md_json, ScriptStyle.DEFAULT)
        assert parsed["titles"] == ["T1"]
        assert parsed["material_mapping"].get("m1") is not None
        assert isinstance(parsed["scenes"], list) and len(parsed["scenes"]) == 1
        assert "timing" in parsed["scenes"][0]

        invalid = gen._parse_generated_script_sync("不是JSON", ScriptStyle.DEFAULT)
        assert isinstance(invalid["titles"], list)
        assert isinstance(invalid["scenes"], list)

    def test_build_prompt_contains_sections(self):
        """提示词包含生成要求、原文内容和素材上下文"""
        from services.sync_script_generator import SyncScriptGenerator

        # 准备模拟模板为空，走内置风格
        with patch(
            "services.sync_script_generator.sync_get_prompt_templates_by_type_and_style"
        ) as tmpl_mock:
            tmpl_mock.return_value = []

            # 构造素材对象（具备analysis_status等属性）
            class Ana:
                def __init__(self):
                    self.analysis_status = type("S", (), {"value": "completed"})()
                    self.media_item_id = "m1"
                    self.file_format = "PNG"
                    self.description = "desc"
                    self.cloud_url = "http://x"

            material_context = {
                "material_count": 1,
                "material_types": ["image"],
                "description": "可用素材",
                "analysis_results": [Ana()],
            }

            gen = SyncScriptGenerator()
            prompt = gen._build_script_prompt_sync(
                topic="主题",
                source_content=TEST_CONTENT,
                style=ScriptStyle.DEFAULT,
                persona={
                    "name": "人设A",
                    "persona_type": "professional",
                    "style": "严谨",
                    "target_audience": "开发者",
                    "characteristics": "清晰",
                    "tone": "专业",
                    "keywords": ["AI"],
                },
                user_requirements="简洁",
                material_context=material_context,
            )

            assert "## 生成要求" in prompt
            assert "## 原文内容" in prompt
            assert "## 素材上下文" in prompt
            assert "素材ID: m1" in prompt

    def test_estimated_duration_bounds(self):
        """时长估算在设定上下限之间"""
        from services.sync_script_generator import SyncScriptGenerator

        gen = SyncScriptGenerator()
        short = gen._estimate_duration_sync("短内容。")
        long = gen._estimate_duration_sync("字" * 10000)

        assert 15.0 <= short <= 120.0
        assert long == 120.0
