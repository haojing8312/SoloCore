"""
同步脚本生成器 - 用于Celery任务
完全同步版本的ScriptGenerator，避免事件循环冲突
"""

import json
import re
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from config import settings
from models.celery_db import (
    sync_create_script_content,
    sync_get_persona_by_id,
    sync_get_prompt_templates_by_type_and_style,
    sync_update_script_content,
)
from models.prompt_template import TemplateStyle, TemplateType
from models.script_generation import (
    GenerationStatus,
    PersonaBase,
    PersonaType,
    ScriptContentBase,
    ScriptGenerationBatch,
    ScriptGenerationResult,
    ScriptStyle,
)
from utils.sync_clients import get_sync_script_client
from utils.sync_logging import get_script_generator_logger, log_performance

logger = get_script_generator_logger()


class PromptStyleType(Enum):
    """提示词风格类型"""

    DEFAULT = "default"
    PRODUCT_GEEK = "product_geek"


class ScriptPromptConfig:
    """脚本提示词配置类"""

    # 默认选中的风格
    DEFAULT_STYLE = PromptStyleType.DEFAULT

    # 风格配置
    STYLES = {
        PromptStyleType.DEFAULT: {
            "code": "default",
            "name": "默认风格",
            "role_description": """# 角色：你是一名顶级的短视频内容策略师和编剧。你专精于将复杂的科技和商业趋势，转化为普通观众能理解、有共鸣、并觉得有价值的深度故事。

## 你的核心能力与风格：
- **学术背景，通俗表达**：你能将复杂的前沿AI技术（如世界模型、生成式AI）用普通人能听懂的语言清晰地表达出来。
- **趋势洞察，价值提炼**：你不仅仅是复述新闻，而是能迅速抓住一个事件背后的核心趋势，并提炼出对目标用户（大学生、职场人、科技爱好者）的"实用价值"和"信息差"。
- **情绪共鸣，未来感塑造**：你擅长使用充满"未来感"的预测和判断，并结合"黄金三秒"爆款开头，迅速抓住用户注意力，激发他们的期待与讨论。""",
            "core_task": """# 核心任务：
根据我提供的【原文内容】和【素材信息】，创作一个具有鲜明风格的短视频脚本。""",
            "methodology": """# 创作方法论（请严格遵循以下思维链进行创作）：

1.  **立意与视角挖掘 (Finding the Angle)**
    -   不要直接总结【原文内容】。首先思考：这篇内容背后揭示了什么重大的"AI趋势"？
    -   这个趋势对我的目标用户意味着什么？是"生存指南"（如高考选专业、职业危机）、"未来愿景"（如医疗突破、生命延长），还是"格局之争"（如中美AI竞争）？
    -   从这个角度出发，确立视频的核心"价值主张"。

2.  **打造"黄金三秒"开头 (The Hook)**
    -   基于你的立意，用一句极具冲击力、悬念感或颠覆性的话作为开场白。
    -   你可以选择以下方式之一：抛出一个惊人的数字、提出一个直击灵魂的问题、或使用一个巧妙的类比。

3.  **构建逻辑清晰的主体 (The Body)**
    -   故事主体必须逻辑清晰、层层递进。推荐使用"背景介绍 -> 深入分析 -> 揭示规律/影响"的结构。
    -   在"深入分析"部分，使用"第一、第二、第三..."这样的结构化方式来呈现你的发现，让观众感觉条理分明。
    -   在叙述中，智能地、恰当地引用【原文内容】中的关键信息或数据作为论据，增强专业性。

4.  价值升华 (Value Climax):
    -   在所有数据分析之后，必须有一个超越数据本身的、更深层次的"洞见"或"精神内核"作为高潮。这通常是关于机遇、挑战、热爱、长期主义等更宏大的主题。

5.  **结尾与行动号召 (Ending & CTA)**:
    -   视频结尾必须将视角从分析"事件"本身，拉回到"我们"（普通观众）的应对策略上。
    -   给观众提供一个积极、可行的思考方向或解决方案。
    -   最后，以一个开放性问题或一个引导性指令结束，以促进互动。

6.  **语言风格 (Language Style)**:
    -   权威自信：使用肯定、果断的语气。
    -   通俗易懂：用简单的词汇解释复杂的概念。
    -   富有节奏：多用短句，穿插设问和感叹，让语言适合口播。

7.  **素材与场景的智能映射 (Material Mapping)**
    -   在生成场景`scenes`时，深度理解每个场景旁白的情绪和内容。
    -   从【素材信息】中，选择"标签"或"描述"与当前场景旁白最匹配的图片或视频素材。
    -   如果不需要关联素材，则`material_id`为`null`。
    -   思考素材的象征意义，例如，讲述"突破"时，可以使用"火箭发射"或"打开一扇门"的素材（如果素材库中有的话）。""",
        },
        PromptStyleType.PRODUCT_GEEK: {
            "code": "product_geek",
            "name": "产品极客风格",
            "role_description": """# 角色：
你是一名顶级的AI工具发烧友和产品测评博主。你的个人品牌是"AI工具玩家"和"极客分享者"。你专精于第一时间发现市面上最新、最酷、最具潜力的AI工具，并通过"眼见为实"的硬核演示，将它们的核心价值清晰、直观地传递给你的观众（主要是开发者和AI爱好者）。

## 你的核心能力与风格：
- **价值嗅探，直击痛点**：你能迅速从一个产品或项目中，嗅探出它最核心的"杀手级功能"，并将其与用户的核心痛点场景紧密结合。
- **场景化演示，眼见为实**：你的内容核心永远是"Show, Don't Tell"。你擅长通过实际操作的屏幕录制，展示一个工具如何一步步解决一个具体、真实的问题，提供强大的信任感。
- **制造热度，引导行动**：你懂得如何利用社交认同（如GitHub Stars、下载量）来制造FOMO（错失恐惧症）氛围，并在视频结尾通过消除用户疑虑（价格、安装难度），给出"临门一脚"，促使观众立即行动。""",
            "core_task": """# 核心任务：
根据我提供的【原文内容】和【素材信息】，创作一个具有鲜明"产品极客"风格的短视频脚本。""",
            "methodology": """# 创作方法论（请严格遵循以下"H-D-A"模型进行创作）：

## H - The Hook (打造"FOMO"式开头)
**指令**：视频开头必须立刻用最有力、最量化的"社交证据"或"惊人效果"抓住观众。""",
        },
    }


class SyncScriptGenerator:
    """同步脚本生成器"""

    def __init__(self):
        """初始化同步脚本生成器"""
        # 根据配置选择脚本生成客户端（Gemini 或 OpenAI）
        self.script_client = get_sync_script_client()
        self.logger = get_script_generator_logger()

        self.logger.info("SyncScriptGenerator初始化完成")

    @log_performance(get_script_generator_logger(), "生成多脚本")
    def generate_multi_scripts_sync(
        self,
        task_id: str,
        topic: str,
        source_content: str,
        material_context: Optional[Dict] = None,
        persona_id: Optional[int] = None,
        styles: Optional[List[ScriptStyle]] = None,
        creator_id: Optional[str] = None,
        user_requirements: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        同步生成多种风格的脚本

        Args:
            task_id: 任务ID
            topic: 主题
            source_content: 源内容
            material_context: 素材上下文
            persona_id: 人设ID
            styles: 脚本风格列表
            creator_id: 创建者ID
            user_requirements: 用户需求

        Returns:
            生成结果
        """
        try:
            self.logger.info(f"开始生成多脚本 - 任务ID: {task_id}, 主题: {topic}")

            # 只生成单个风格的脚本（不再支持多风格）
            if not styles:
                # 默认使用 DEFAULT 风格
                styles = [ScriptStyle.DEFAULT]

            # 如果传入了多个风格，只使用第一个
            if len(styles) > 1:
                self.logger.warning(
                    f"传入了多个风格 {[s.value for s in styles]}，只使用第一个: {styles[0].value}"
                )
                styles = [styles[0]]

            self.logger.info(f"将生成脚本，风格: {styles[0].value}")

            # 获取人设信息
            persona = None
            if persona_id:
                persona = sync_get_persona_by_id(persona_id)
                if not persona:
                    self.logger.warning(f"未找到人设ID: {persona_id}")
                else:
                    self.logger.info(
                        f"成功获取人设信息: {persona.get('name', 'unknown')}"
                    )

            # 串行生成多种风格的脚本
            successful_results = []
            failed_results = []

            for style in styles:
                self.logger.info(f"准备生成 {style.value} 风格的脚本...")
                try:
                    result = self._generate_single_script_sync(
                        task_id=task_id,
                        topic=topic,
                        source_content=source_content,
                        style=style,
                        creator_id=creator_id,
                        persona=persona,
                        user_requirements=user_requirements,
                        material_context=material_context,
                    )
                    successful_results.append(result)
                    self.logger.info(
                        f"生成脚本成功 - 风格: {style.value}, 脚本ID: {result.get('script_id')}"
                    )

                except Exception as e:
                    failed_results.append({"style": style.value, "error": str(e)})
                    self.logger.error(f"生成脚本失败 - 风格: {style.value}, 错误: {e}")

            # 返回批量生成结果
            batch_result = {
                "task_id": task_id,
                "topic": topic,
                "persona_id": persona_id,
                "requested_styles": [s.value for s in styles],
                "successful_results": successful_results,
                "failed_results": failed_results,
                "total_count": len(styles),
                "success_count": len(successful_results),
                "failure_count": len(failed_results),
                "generated_at": datetime.utcnow(),
            }

            self.logger.info(
                f"批量脚本生成完成 - 总数: {len(styles)}, 成功: {len(successful_results)}, 失败: {len(failed_results)}"
            )
            for style in styles:
                success = any(
                    r.get("script_style") == style.value for r in successful_results
                )
                self.logger.info(
                    f"风格 {style.value} 生成{'成功' if success else '失败'}"
                )

            return batch_result

        except Exception as e:
            self.logger.error(f"批量生成脚本异常: {e}")
            self.logger.error(f"错误详情: {traceback.format_exc()}")
            raise

    @log_performance(get_script_generator_logger(), "生成单脚本")
    def generate_single_script_sync(
        self,
        task_id: str,
        topic: str,
        source_content: str,
        material_context: Optional[Dict] = None,
        persona_id: Optional[int] = None,
        script_style: Optional[str] = None,
        creator_id: Optional[str] = None,
        user_requirements: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        公共接口：同步生成单个脚本
        
        Args:
            task_id: 任务ID
            topic: 主题
            source_content: 源内容
            material_context: 素材上下文
            persona_id: 人设ID
            script_style: 脚本风格（字符串形式）
            creator_id: 创建者ID
            user_requirements: 用户需求
        
        Returns:
            生成结果包装在success/error结构中
        """
        try:
            self.logger.info(f"开始单脚本生成 - 任务ID: {task_id}, 风格: {script_style}")
            
            # 获取人设信息
            persona = None
            if persona_id:
                persona = sync_get_persona_by_id(persona_id)
                if not persona:
                    self.logger.warning(f"未找到人设ID: {persona_id}")
                else:
                    self.logger.info(f"成功获取人设信息: {persona.get('name', 'unknown')}")
            
            # 转换脚本风格字符串为枚举
            style = ScriptStyle.DEFAULT  # 默认风格
            if script_style:
                style_mapping = {
                    "default": ScriptStyle.DEFAULT,
                    "product_geek": ScriptStyle.PRODUCT_GEEK,
                }
                style = style_mapping.get(script_style.lower(), ScriptStyle.DEFAULT)
            
            # 调用私有方法生成脚本
            result = self._generate_single_script_sync(
                task_id=task_id,
                topic=topic,
                source_content=source_content,
                style=style,
                creator_id=creator_id,
                persona=persona,
                user_requirements=user_requirements,
                material_context=material_context,
            )
            
            # 包装成功结果
            return {
                "success": True,
                "script_data": result,
                "task_id": task_id,
                "script_style": script_style
            }
            
        except Exception as e:
            self.logger.error(f"单脚本生成失败 - 任务ID: {task_id}, 错误: {str(e)}")
            self.logger.error(f"错误详情: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id,
                "script_style": script_style
            }

    def _generate_single_script_sync(
        self,
        task_id: str,
        topic: str,
        source_content: str,
        style: ScriptStyle,
        creator_id: Optional[str] = None,
        persona: Optional[Any] = None,
        user_requirements: Optional[str] = None,
        material_context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """同步生成单个风格的脚本"""
        script_id = str(uuid4())

        try:
            self.logger.info(f"开始生成脚本 - ID: {script_id}, 风格: {style.value}")

            # 创建脚本记录
            script_data = {
                "task_id": task_id,
                "creator_id": creator_id,
                "persona_id": persona.get("id") if persona else None,
                "script_style": style.value,
                "generation_status": GenerationStatus.PROCESSING.value,
            }

            script_record = sync_create_script_content(script_data)
            if not script_record:
                raise RuntimeError("创建脚本记录失败")

            actual_script_id = script_record.get("id", script_id)
            self.logger.info(f"脚本记录创建成功 - 数据库ID: {actual_script_id}")

            # 构建提示词（对齐异步版本的模板与上下文构建）
            prompt = self._build_script_prompt_sync(
                topic=topic,
                source_content=source_content,
                style=style,
                persona=persona,
                user_requirements=user_requirements,
                material_context=material_context,
            )

            self.logger.debug(f"脚本生成提示词长度: {len(prompt)} 字符")
            # 打印Prompt预览与完整内容
            try:
                preview_len = 800
                self.logger.info(
                    "脚本生成LLM请求提示词预览(前%d字): %s",
                    preview_len,
                    (prompt or "")[:preview_len],
                )
                self.logger.debug("脚本生成LLM请求提示词完整内容:\n%s", prompt)
            except Exception:
                pass

            # 调用模型客户端生成脚本（自动根据配置选择 OpenAI/Gemini）
            generated_content = self.script_client.generate_script(
                prompt=prompt, max_tokens=8000, temperature=0.7
            )

            if not generated_content:
                # 统一错误消息，不再强绑定 Gemini
                raise RuntimeError("LLM 脚本生成接口返回空内容")

            self.logger.info(f"脚本生成成功 - 内容长度: {len(generated_content)} 字符")
            # 打印LLM输出预览与完整内容
            try:
                preview_len = 800
                self.logger.info(
                    "LLM输出内容预览(前%d字): %s",
                    preview_len,
                    (generated_content or "")[:preview_len],
                )
                self.logger.debug("LLM输出完整内容:\n%s", generated_content)
            except Exception:
                pass

            # 解析生成的脚本（与异步版字段保持一致）
            parsed_script = self._parse_generated_script_sync(generated_content, style)

            # 统计信息
            word_count = len(parsed_script.get("narration", ""))
            scene_count = len(parsed_script.get("scenes", []))
            estimated_duration = self._estimate_duration_sync(
                parsed_script.get("narration", "")
            )
            material_count = len(parsed_script.get("material_mapping", {}) or {})

            # 日志中强调material_mapping统计
            mm = parsed_script.get("material_mapping", {}) or {}
            try:
                self.logger.info(
                    "material_mapping键数: %d, 键列表预览: %s",
                    len(mm),
                    list(mm.keys())[:10],
                )
                self.logger.debug(
                    "material_mapping完整: %s", json.dumps(mm, ensure_ascii=False)
                )
            except Exception:
                pass

            # 更新脚本记录（仅使用允许字段）
            update_data = {
                "titles": parsed_script.get("titles")
                or (
                    [parsed_script.get("title", topic)]
                    if parsed_script.get("title")
                    else []
                ),
                "description": parsed_script.get("description", ""),
                "narration": parsed_script.get("narration", ""),
                "material_mapping": mm,
                "scenes": parsed_script.get("scenes", []),
                "tags": parsed_script.get("tags", []),
                "word_count": word_count,
                "estimated_duration": estimated_duration,
                "material_count": material_count,
                "generation_prompt": prompt,
                "ai_response": generated_content,
                "generation_status": GenerationStatus.COMPLETED.value,
                "generated_at": datetime.utcnow(),
            }

            # 更新脚本内容（同步数据库）
            try:
                self.logger.debug("更新脚本内容到数据库...")
                _ = sync_update_script_content(actual_script_id, update_data)
            except Exception:
                # 数据库更新失败不阻断返回
                self.logger.warning("更新脚本内容到数据库失败，继续返回内存结果")

            # 构建返回结果
            result = {
                "script_id": actual_script_id,
                "task_id": task_id,
                "script_style": style.value,
                "title": parsed_script.get("title", topic),
                "titles": parsed_script.get("titles", []),
                "description": parsed_script.get("description", ""),
                "narration": parsed_script.get("narration", ""),
                "material_mapping": parsed_script.get("material_mapping", {}),
                "tags": parsed_script.get("tags", []),
                "scenes": parsed_script.get("scenes", []),
                "word_count": word_count,
                "scene_count": scene_count,
                "estimated_duration": estimated_duration,
                "material_count": material_count,
                "persona_id": persona.get("id") if persona else None,
                "generation_status": GenerationStatus.COMPLETED.value,
                "generated_at": datetime.utcnow(),
                "raw_content": generated_content,
                "generation_prompt": prompt,
            }

            self.logger.info(
                f"脚本生成完成 - 字数: {word_count}, 场景数: {scene_count}, 预计时长: {estimated_duration}秒, 素材数: {material_count}"
            )
            return result

        except Exception as e:
            self.logger.error(f"生成脚本失败 - ID: {script_id}, 错误: {str(e)}")
            raise

    def _build_script_prompt_sync(
        self,
        topic: str,
        source_content: str,
        style: ScriptStyle,
        persona: Optional[Dict] = None,
        user_requirements: Optional[str] = None,
        material_context: Optional[Dict] = None,
    ) -> str:
        """同步构建脚本生成提示词（对齐异步版本）"""

        # 选择模板风格
        template_style = self._get_template_style_sync(style)

        # 获取系统与内容模板（同步DB）
        system_templates = sync_get_prompt_templates_by_type_and_style(
            TemplateType.SYSTEM.value, template_style.value
        )
        content_templates = sync_get_prompt_templates_by_type_and_style(
            TemplateType.SCRIPT_CONTENT.value, template_style.value
        )

        prompt_parts: List[str] = []

        # 系统提示词
        if system_templates:
            system_prompt = (
                system_templates[0].get("content")
                if isinstance(system_templates[0], dict)
                else system_templates[0].content
            )
            prompt_parts.append(f"## 系统角色\n{system_prompt}")
        else:
            # 回落到内置风格
            # 根据脚本风格选择对应的提示词风格
            if style == ScriptStyle.PRODUCT_GEEK:
                prompt_style = PromptStyleType.PRODUCT_GEEK
            else:
                prompt_style = PromptStyleType.DEFAULT
                
            style_config = ScriptPromptConfig.STYLES.get(prompt_style)
            prompt_parts.extend(
                [
                    style_config["role_description"],
                    style_config["core_task"],
                    style_config["methodology"],
                ]
            )

        # 人设信息
        if persona:
            persona_info = f"""
## 人设信息
- 名称: {persona.get('name', '未知')}
- 类型: {persona.get('persona_type', '未知')}
- 风格: {persona.get('style', '未知')}
- 目标受众: {persona.get('target_audience', '未知')}
- 特征: {persona.get('characteristics', '未知')}
- 语调: {persona.get('tone', '未知')}
- 关键词: {', '.join(persona.get('keywords', [])) if persona.get('keywords') else '无'}
"""
            prompt_parts.append(persona_info)

        # 主题与用户要求、原文内容
        topic_info = f"""
## 生成要求
- 主题: {topic}
- 用户要求: {user_requirements or '无特殊要求'}
"""
        prompt_parts.append(topic_info)

        if source_content:
            prompt_parts.append(f"## 原文内容\n{source_content[:20000]}...")

        # 素材上下文
        if material_context:
            # 同步版material_context结构兼容：优先从summary推导统计信息
            analysis_results = material_context.get("analysis_results", [])
            summary = material_context.get("summary", {}) or {}

            # 计算素材数量
            total_count = (
                material_context.get("material_count")
                or summary.get("total_count")
                or (len(analysis_results) if isinstance(analysis_results, list) else 0)
            )

            # 计算素材类型集合
            type_set = set()
            # 如果material_context已有类型列表则复用
            preset_types = material_context.get("material_types") or []
            for t in preset_types:
                if t:
                    type_set.add(str(t))

            # 从summary补充
            if summary.get("image_count"):
                type_set.add("image")
            if summary.get("video_count"):
                type_set.add("video")

            # 从analysis_results推断
            for material in analysis_results or []:
                try:
                    if isinstance(material, dict):
                        file_type = material.get("file_type")
                        file_format = material.get("file_format")
                        if file_type in ["image", "video"]:
                            type_set.add(file_type)
                        elif file_format:
                            upper_fmt = str(file_format).upper()
                            if upper_fmt in [
                                "PNG",
                                "JPEG",
                                "JPG",
                                "WEBP",
                                "GIF",
                                "BMP",
                            ]:
                                type_set.add("image")
                            else:
                                type_set.add("video")
                    else:
                        # 对象型：基于file_format推断
                        fmt = getattr(material, "file_format", None)
                        if fmt:
                            upper_fmt = str(fmt).upper()
                            if upper_fmt in [
                                "PNG",
                                "JPEG",
                                "JPG",
                                "WEBP",
                                "GIF",
                                "BMP",
                            ]:
                                type_set.add("image")
                            else:
                                type_set.add("video")
                except Exception:
                    continue

            material_types_str = ", ".join(sorted(type_set))

            context_info = f"""
## 素材上下文
- 可用素材数量: {total_count}
- 素材类型: {material_types_str}
- 素材描述: {material_context.get('description', '无')}
"""

            if analysis_results:
                materials_info = "\n## 可用素材列表\n"
                for material in analysis_results:
                    try:
                        if isinstance(material, dict):
                            status = str(material.get("analysis_status", "")).lower()
                            if status == "completed":
                                material_id = str(
                                    material.get("media_item_id") or "unknown"
                                )
                                # 类型推断（优先file_type，其次file_format）
                                m_type = material.get("file_type")
                                if not m_type:
                                    m_fmt = material.get("file_format")
                                    if m_fmt and str(m_fmt).upper() in [
                                        "PNG",
                                        "JPEG",
                                        "JPG",
                                        "WEBP",
                                        "GIF",
                                        "BMP",
                                    ]:
                                        m_type = "image"
                                    elif m_fmt:
                                        m_type = "video"
                                description = (
                                    material.get("ai_description")
                                    or material.get("description")
                                    or "无描述"
                                )
                                url = (
                                    material.get("file_url")
                                    or material.get("url")
                                    or ""
                                )
                                materials_info += (
                                    f"- 素材ID: {material_id}\n"
                                    f"  类型: {m_type or 'unknown'}\n"
                                    f"  描述: {description}\n"
                                    f"  URL: {url}\n\n"
                                )
                        else:
                            # 对象型（MaterialAnalysis）
                            from_obj_completed = (
                                hasattr(material, "analysis_status")
                                and getattr(material.analysis_status, "value", None)
                                == "completed"
                            )
                            if from_obj_completed:
                                material_id = (
                                    str(material.media_item_id)
                                    if hasattr(material, "media_item_id")
                                    else "unknown"
                                )
                                fmt = getattr(material, "file_format", None)
                                upper_fmt = str(fmt).upper() if fmt else ""
                                m_type = (
                                    "image"
                                    if upper_fmt
                                    in ["PNG", "JPEG", "JPG", "WEBP", "GIF", "BMP"]
                                    else "video"
                                )
                                description = (
                                    getattr(material, "description", None)
                                    or getattr(material, "ai_description", None)
                                    or "无描述"
                                )
                                # 同步链路优先 file_url
                                url = ""
                                if hasattr(material, "file_url") and getattr(
                                    material, "file_url"
                                ):
                                    url = getattr(material, "file_url")
                                elif hasattr(material, "cloud_url") and getattr(
                                    material, "cloud_url"
                                ):
                                    url = getattr(material, "cloud_url")
                                materials_info += (
                                    f"- 素材ID: {material_id}\n"
                                    f"  类型: {m_type}\n"
                                    f"  描述: {description}\n"
                                    f"  URL: {url}\n\n"
                                )
                    except Exception:
                        continue
                # 在上下文尾部加入“场景与素材使用硬约束”以引导模型达成更高覆盖率
                # 计算素材与视频素材数量
                try:
                    completed_items = []
                    video_ids = []
                    for m in analysis_results:
                        try:
                            status = (
                                (m.get("analysis_status") or "").lower()
                                if isinstance(m, dict)
                                else (
                                    getattr(m, "analysis_status", None).value
                                    if getattr(m, "analysis_status", None)
                                    else ""
                                )
                            )
                            if status == "completed":
                                if isinstance(m, dict):
                                    completed_items.append(m)
                                    # 判断是否视频
                                    m_type = m.get("file_type")
                                    if not m_type:
                                        fmt = m.get("file_format")
                                        if fmt and str(fmt).upper() in [
                                            "PNG",
                                            "JPEG",
                                            "JPG",
                                            "WEBP",
                                            "GIF",
                                            "BMP",
                                        ]:
                                            m_type = "image"
                                        elif fmt:
                                            m_type = "video"
                                    if m_type == "video":
                                        video_ids.append(
                                            str(m.get("media_item_id") or "")
                                        )
                                else:
                                    completed_items.append(
                                        {
                                            "media_item_id": str(
                                                getattr(m, "media_item_id", "")
                                            ),
                                            "file_format": getattr(
                                                m, "file_format", None
                                            ),
                                        }
                                    )
                                    fmt = str(getattr(m, "file_format", "")).upper()
                                    if fmt and fmt not in [
                                        "PNG",
                                        "JPEG",
                                        "JPG",
                                        "WEBP",
                                        "GIF",
                                        "BMP",
                                    ]:
                                        video_ids.append(
                                            str(getattr(m, "media_item_id", ""))
                                        )
                        except Exception:
                            continue
                    total_completed = len(completed_items)
                    unique_video_ids = [vid for vid in video_ids if vid]
                    unique_video_ids = list(dict.fromkeys(unique_video_ids))
                except Exception:
                    total_completed = 0
                    unique_video_ids = []

                # 目标场景与覆盖率要求描述
                coverage_target = f"至少使用已完成素材的80%以上(>= {max(1, int(round((total_completed or 0) * 0.8)))} 个)；每个场景严格关联且仅关联1个素材。"
                video_priority = "必须优先并全部使用以下视频素材ID（如存在）：" + (
                    ", ".join(unique_video_ids) if unique_video_ids else "无视频素材"
                )
                scene_hint = "场景数请与素材量自适应（可按素材数量设置同等或略少的场景数，避免冗余），允许合理合并但必须满足覆盖率目标。"

                constraints = f"""
## 重要硬约束（请严格遵守）
- 场景-素材映射：每个场景仅关联一个素材（material_id 不得为数组或多个ID）。
- 覆盖率目标：{coverage_target}
- 视频素材优先：{video_priority}
- 场景数量：{scene_hint}
- 素材使用：只使用提供的素材ID，不得使用未声明的素材ID。
"""
                context_info += materials_info + constraints
            prompt_parts.append(context_info)

        # 内容模板
        if content_templates:
            content_prompt = (
                content_templates[0].get("content")
                if isinstance(content_templates[0], dict)
                else content_templates[0].content
            )
            prompt_parts.append(f"## 生成指令\n{content_prompt}")

        # 输出格式
        format_instruction = """
## 输出格式
请严格按照以下JSON格式输出，注意scenes中必须使用实际的素材ID：
{
    "titles": ["标题1", "标题2", "标题3"],
    "narration": "完整的旁白文本",
    "scenes": [
        {
            "scene_id": 1,
            "timing": "0-5s",
            "narration": "这一段的旁白",
            "material_id": "material_id_1",
            "description": "场景描述"
        },
        {
            "scene_id": 2,
            "timing": "5-10s",
            "narration": "下一段的旁白",
            "material_id": "material_id_2",
            "description": "场景描述"
        }
    ],
    "description": "视频整体描述",
    "tags": ["标签1", "标签2", "标签3"],
    "estimated_duration": 60
}

重要说明：
1. scenes中的material_id必须使用实际提供的素材ID
2. 请根据素材的描述选择最合适的素材匹配到对应场景
3. 如果某个场景不需要素材，material_id可以为null
4. 只使用提供的素材ID，不得使用未声明的素材ID
"""
        prompt_parts.append(format_instruction)

        return "\n\n".join(prompt_parts)

    def _parse_generated_script_sync(
        self, generated_content: str, style: ScriptStyle
    ) -> Dict[str, Any]:
        """同步解析生成的脚本内容（对齐异步版本字段）"""
        try:
            content = (generated_content or "").strip()
            # 直接解析JSON
            if content.startswith("{"):
                data = json.loads(content)
                return self._normalize_parsed_data_sync(data, style)

            # 尝试从markdown代码块或文本中提取JSON
            json_patterns = [
                r"```json\s*(\{.*?\})\s*```",
                r"```\s*(\{.*?\})\s*```",
                r"\{[\s\S]*\}",
            ]
            for pattern in json_patterns:
                m = re.search(pattern, content, re.DOTALL)
                if m:
                    raw = m.group(1) if m.groups() else m.group(0)
                    try:
                        data = json.loads(raw)
                        return self._normalize_parsed_data_sync(data, style)
                    except json.JSONDecodeError:
                        continue

            self.logger.warning("无法解析JSON，使用默认结构")
            return self._get_default_content_sync(style)

        except Exception as e:
            self.logger.error(f"解析脚本响应失败: {str(e)}")
            return self._get_default_content_sync(style)

    def _normalize_parsed_data_sync(
        self, data: Dict[str, Any], style: ScriptStyle
    ) -> Dict[str, Any]:
        """规范化解析结果为异步版一致的字段"""
        normalized = {
            "title": (
                data.get("title") or (data.get("titles") or [""])[0]
                if data.get("titles")
                else ""
            ),
            "titles": data.get("titles") or [],
            "description": data.get("description", ""),
            "narration": data.get("narration") or data.get("script", ""),
            "material_mapping": data.get("material_mapping") or {},
            "tags": data.get("tags") or [],
            "estimated_duration": data.get("estimated_duration") or 60,
            "scenes": data.get("scenes") or [],
        }

        # 保障scenes为列表，字段齐全，使用timing/material_id
        if not isinstance(normalized["scenes"], list):
            normalized["scenes"] = []
        fixed_scenes = []
        for idx, scene in enumerate(normalized["scenes"], start=1):
            if not isinstance(scene, dict):
                continue
            fixed_scene = {
                "scene_id": scene.get("scene_id", idx),
                "timing": scene.get("timing") or f"{(idx-1)*5}-{idx*5}s",
                "narration": scene.get("narration", ""),
                "material_id": scene.get("material_id"),
                "description": scene.get(
                    "description", scene.get("material_description", "")
                ),
            }
            fixed_scenes.append(fixed_scene)
        normalized["scenes"] = fixed_scenes

        # 确保必要字段存在
        if not normalized["narration"]:
            normalized["narration"] = f"这是一个{style.value}风格的脚本内容。"

        return normalized

    def _get_default_content_sync(self, style: ScriptStyle) -> Dict[str, Any]:
        """默认内容（与异步版字段一致）"""
        return {
            "title": f"{style.value}风格标题",
            "titles": [
                f"{style.value}风格标题1",
                f"{style.value}风格标题2",
                f"{style.value}风格标题3",
            ],
            "description": f"{style.value}风格的视频内容",
            "narration": f"这是一个{style.value}风格的脚本内容。",
            "material_mapping": {
                "default_1": {
                    "type": "image",
                    "description": "默认图片",
                    "timing": "0-5s",
                    "scene_usage": "开头展示",
                }
            },
            "tags": [style.value, "视频", "内容"],
            "estimated_duration": 60,
            "scenes": [
                {
                    "scene_id": 1,
                    "timing": "0-60s",
                    "narration": f"这是一个{style.value}风格的脚本内容。",
                    "material_id": "default_1",
                    "description": "默认场景",
                }
            ],
        }

    def _create_default_script_sync(
        self, generated_content: str, style: ScriptStyle
    ) -> Dict[str, Any]:
        """创建默认脚本结构"""

        # 从生成内容中提取标题和描述
        lines = generated_content.strip().split("\n")
        title = lines[0][:50] if lines else "精彩内容"
        description = lines[1][:100] if len(lines) > 1 else "这是一个精彩的视频"

        # 使用生成内容作为口播稿
        narration = (
            generated_content[:500] if generated_content else "这是一个精彩的视频内容。"
        )

        # 创建简单的场景结构
        scenes = [
            {
                "scene_id": 1,
                "narration": narration,
                "material_id": None,
                "material_description": "背景素材",
                "duration": 60.0,
                "scene_type": "main",
            }
        ]

        return {
            "title": title,
            "description": description,
            "narration": narration,
            "scenes": scenes,
        }

    def _estimate_duration_sync(self, narration: str) -> float:
        """同步估算脚本时长"""
        if not narration:
            return 0.0

        # 简单估算：中文平均每分钟200字，英文每分钟150词
        char_count = len(narration)

        # 假设主要是中文内容
        duration = char_count / 200 * 60  # 转换为秒

        # 最小15秒，最大120秒
        duration = max(15.0, min(120.0, duration))

        return round(duration, 1)

    def _get_template_style_sync(self, script_style: ScriptStyle) -> TemplateStyle:
        """将脚本风格转换为模板风格（与异步版一致）"""
        style_mapping = {
            ScriptStyle.DEFAULT: TemplateStyle.DEFAULT,
            ScriptStyle.PRODUCT_GEEK: TemplateStyle.DEFAULT,  # 产品极客也使用默认模板风格
        }
        return style_mapping.get(script_style, TemplateStyle.DEFAULT)
