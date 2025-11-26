"""
同步视频生成器 - 基于 Editly 开源引擎

核心职责：
- 单视频生成管理（按风格）
- 子任务状态跟踪
- 委托 EditlyVideoEngine 进行视频生成
- 错误处理和日志记录

架构优势：
- 100% 开源方案（Editly）
- 零 API 成本
- 完全可控
- 本地生成

作者: Claude
创建: 2024
更新: 2025-11-24 - 重构为单视频生成模式，避免并发写入冲突
"""

import os
import traceback
from pathlib import Path
from typing import Any, Dict, List

from config import settings

# 同步数据库包装函数 - SubVideoTask 已移除
# from models.celery_db import (
#     sync_create_sub_video_task,
#     sync_update_sub_video_task,
# )
from services.edge_tts_service import get_tts_service
from services.editly_video_engine import EditlyVideoEngine
from utils.sync_logging import get_video_generator_logger, log_performance


class SyncVideoGenerator:
    """
    同步视频生成器 - Editly 引擎

    负责：
    1. 单视频生成（按指定风格或默认风格）
    2. 子任务创建和状态更新
    3. 委托 EditlyVideoEngine 进行视频生成
    4. 错误处理和结果封装
    """

    def __init__(self):
        """初始化同步视频生成器"""
        self.logger = get_video_generator_logger()

        # 初始化 Editly 视频引擎
        try:
            self.engine = EditlyVideoEngine()
            self.logger.info("EditlyVideoEngine 初始化成功")
        except Exception as e:
            self.logger.error(f"EditlyVideoEngine 初始化失败: {e}")
            raise RuntimeError(
                f"视频生成引擎初始化失败，服务不可用: {e}"
            )

        self.logger.info("SyncVideoGenerator 初始化完成（Editly 引擎）")

    @log_performance(get_video_generator_logger(), "生成单个视频（按风格）")
    def generate_single_video_by_style(
        self,
        script_data: Dict[str, Any],
        media_files: List[Dict[str, str]],
        task_id: str,
        script_style: str = None,
        mode: str = "multi_scene",
    ) -> Dict[str, Any]:
        """
        同步生成单个视频（使用指定风格或默认风格）

        Args:
            script_data: 脚本数据字典
            media_files: 媒体文件列表
            task_id: 主任务ID
            script_style: 视频风格（如果为None，使用默认风格"default"）
            mode: 合成模式

        Returns:
            视频生成结果字典
        """
        try:
            # 确定风格：优先使用参数，其次从script_data中获取，最后默认为"default"
            if script_style is None:
                script_style = script_data.get("script_style", "default")

            self.logger.info(
                f"开始生成单个视频 - 主任务ID: {task_id}, 风格: {script_style}"
            )

            # 生成唯一的子任务ID：使用 script_id + script_style
            script_id = script_data.get("script_id")
            if script_id:
                # 使用 script_id 的后8位确保唯一性
                unique_suffix = script_id.split('-')[-1][:8]
                sub_task_id = f"{task_id}_video_{script_style}_{unique_suffix}"
            else:
                # 降级方案：使用时间戳
                import time
                timestamp_suffix = str(int(time.time() * 1000))[-6:]
                sub_task_id = f"{task_id}_video_{script_style}_{timestamp_suffix}"

            self.logger.info(f"子任务ID: {sub_task_id}, 风格: {script_style}")

            # 直接调用单视频生成方法（无需线程池）
            result = self.generate_single_video_sync(
                script_data=script_data,
                media_files=media_files,
                task_id=task_id,
                sub_task_index=1,  # 单视频场景，索引固定为1
                mode=mode,
            )

            if result.get("success"):
                self.logger.info(
                    f"✅ 生成视频成功 - 子任务: {result.get('sub_task_id')}"
                )
            else:
                self.logger.error(
                    f"❌ 生成视频失败 - 子任务: {result.get('sub_task_id')}, "
                    f"错误: {result.get('error')}"
                )

            return result

        except Exception as e:
            self.logger.error(f"生成单个视频失败: {str(e)}")
            raise

    @log_performance(get_video_generator_logger(), "生成多个视频")
    def generate_multiple_videos_sync(
        self,
        scripts_data: List[Dict[str, Any]],
        media_files: List[Dict[str, str]],
        task_id: str,
        mode: str = "multi_scene",
    ) -> List[Dict[str, Any]]:
        """
        同步并发生成多个视频（已弃用，建议使用 generate_single_video_by_style）

        Args:
            scripts_data: 多个脚本数据列表
            media_files: 媒体文件列表
            task_id: 主任务ID
            mode: 合成模式

        Returns:
            多个视频生成结果的列表
        """
        self.logger.warning(
            "generate_multiple_videos_sync 已弃用，建议使用 generate_single_video_by_style"
        )

        try:
            self.logger.info(
                f"开始生成多个视频 - 主任务ID: {task_id}, 视频数量: {len(scripts_data)}"
            )

            # 顺序生成每个视频（避免并发写入冲突）
            results = []
            for i, script_data in enumerate(scripts_data):
                try:
                    result = self.generate_single_video_by_style(
                        script_data=script_data,
                        media_files=media_files,
                        task_id=task_id,
                        script_style=script_data.get("script_style"),
                        mode=mode,
                    )
                    results.append(result)
                except Exception as e:
                    script_style = script_data.get("script_style", "default")
                    error_result = {
                        "sub_task_index": i + 1,
                        "script_style": script_style,
                        "success": False,
                        "error": str(e),
                    }
                    results.append(error_result)
                    self.logger.error(f"生成视频异常 - 风格: {script_style}, 错误: {e}")

            successful_results = [r for r in results if r.get("success")]
            failed_results = [r for r in results if not r.get("success")]

            self.logger.info(
                f"多视频生成完成 - 成功: {len(successful_results)}, "
                f"失败: {len(failed_results)}"
            )

            return results

        except Exception as e:
            self.logger.error(f"生成多个视频失败: {str(e)}")
            raise

    def generate_single_video_sync(
        self,
        script_data: Dict[str, Any],
        media_files: List[Dict[str, str]],
        task_id: str,
        sub_task_index: int,
        mode: str = "multi_scene",
    ) -> Dict[str, Any]:
        """
        同步生成单个视频

        Args:
            script_data: 脚本数据
            media_files: 媒体文件列表
            task_id: 主任务ID
            sub_task_index: 子任务索引
            mode: 合成模式

        Returns:
            生成结果字典
        """
        sub_task_id = f"{task_id}_video_{sub_task_index}"
        script_style = script_data.get("script_style", "default")

        # 创建子任务记录 - 已移除，主任务直接管理视频生成
        # try:
        #     sync_create_sub_video_task(
        #         {
        #             "sub_task_id": sub_task_id,
        #             "parent_task_id": task_id,
        #             "script_style": script_style,
        #             "script_id": script_data.get("script_id"),
        #             "script_data": script_data,
        #             "status": "processing",
        #             "progress": 0,
        #         }
        #     )
        # except Exception as e:
        #     self.logger.warning(f"创建子任务记录失败(忽略继续): {e}")

        try:
            self.logger.info(
                f"开始生成视频 - 子任务: {sub_task_id}, 模式: {mode}"
            )
            self.logger.info(f"素材数量: {len(media_files)}")

            # 基本校验
            if not script_data or not isinstance(script_data, dict):
                return self._error_result(
                    "脚本数据无效：类型错误", sub_task_id, script_style
                )

            scenes_count = len(script_data.get("scenes", []))
            self.logger.info(f"脚本场景数: {scenes_count}")

            # ========== 音频生成步骤（TTS）==========
            if settings.tts_enabled:
                self.logger.info("🎤 开始生成旁白音频（Edge TTS）")
                script_data = self._generate_audio_for_scenes(
                    script_data, task_id, sub_task_id
                )
            else:
                self.logger.info("⚠️ TTS 功能已禁用，跳过音频生成")

            # 构建输出路径
            output_path = f"workspace/processed/{sub_task_id}_output.mp4"

            # 使用 Editly 引擎生成视频
            self.logger.info("调用 EditlyVideoEngine 进行视频生成")

            engine_result = self.engine.generate_video(
                script_data=script_data,
                media_files=media_files,
                output_path=output_path,
            )

            # 转换引擎返回格式为标准格式
            if engine_result.get("success"):
                final = {
                    "success": True,
                    "video_url": engine_result.get("video_url") or engine_result.get("video_path"),
                    "thumbnail_url": engine_result.get("thumbnail_url", ""),
                    "duration": engine_result.get("duration", 0),
                    "course_media_id": None,  # Editly 本地生成，无 course_media_id
                    "engine": "editly",
                    "mode": mode,
                    "status": "completed",
                    "sub_task_index": sub_task_index,
                    "script_style": script_style,
                    "sub_task_id": sub_task_id,
                    "message": engine_result.get("message", "视频生成成功"),
                }

                # 回写子任务状态 - 已移除，主任务直接管理
                # self._safe_update_sub_task(
                #     sub_task_id,
                #     {
                #         "status": "completed",
                #         "video_url": final.get("video_url"),
                #         "thumbnail_url": final.get("thumbnail_url"),
                #         "duration": final.get("duration"),
                #     },
                # )

                self.logger.info(
                    f"✅ 使用 Editly 引擎生成成功 - "
                    f"子任务: {sub_task_id}, 时长: {final.get('duration')}s"
                )
                return final
            else:
                # 引擎返回失败
                error = engine_result.get("error", "引擎生成失败")
                self.logger.error(f"视频生成失败: {error}")

                # 更新子任务状态为失败 - 已移除，主任务直接管理
                # self._safe_update_sub_task(
                #     sub_task_id,
                #     {
                #         "status": "failed",
                #         "error_message": error,
                #     },
                # )

                return self._error_result(error, sub_task_id, script_style)

        except Exception as e:
            error_traceback = traceback.format_exc()
            self.logger.error(f"视频生成异常 - 子任务: {sub_task_id}, 错误: {str(e)}")
            self.logger.error(f"错误详情: {error_traceback}")

            # 更新子任务状态为错误 - 已移除，主任务直接管理
            # self._safe_update_sub_task(
            #     sub_task_id,
            #     {
            #         "status": "error",
            #         "error_message": str(e),
            #     },
            # )

            return {
                "success": False,
                "error": str(e),
                "status": "error",
                "sub_task_index": sub_task_index,
                "script_style": script_style,
                "sub_task_id": sub_task_id,
            }

    def _error_result(
        self, error: str, sub_task_id: str, script_style: str
    ) -> Dict[str, Any]:
        """构建错误结果"""
        return {
            "success": False,
            "error": error,
            "status": "failed",
            "sub_task_id": sub_task_id,
            "script_style": script_style,
        }

    def _generate_audio_for_scenes(
        self, script_data: Dict[str, Any], task_id: str, sub_task_id: str
    ) -> Dict[str, Any]:
        """
        为场景生成 TTS 音频

        Args:
            script_data: 脚本数据（包含 scenes）
            task_id: 主任务 ID
            sub_task_id: 子任务 ID

        Returns:
            Dict[str, Any]: 更新后的脚本数据（每个 scene 添加 audio_path 字段）
        """
        scenes = script_data.get("scenes", [])
        if not scenes:
            self.logger.warning("脚本中没有场景，跳过音频生成")
            return script_data

        # 创建音频存储目录
        audio_dir = Path(f"workspace/task_{task_id}/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"为 {len(scenes)} 个场景生成音频，目录: {audio_dir}")

        # 获取 TTS 服务实例
        tts_service = get_tts_service()

        # 为每个场景生成音频
        audio_generated_count = 0
        audio_skipped_count = 0

        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", i + 1)
            narration = scene.get("narration", "").strip()

            if not narration:
                self.logger.info(f"场景 {scene_id} 没有旁白文本，跳过")
                audio_skipped_count += 1
                continue

            # 构建音频文件路径（使用绝对路径）
            audio_filename = f"scene_{scene_id}_narration.mp3"
            audio_path = audio_dir / audio_filename
            audio_path_str = str(audio_path.absolute())

            self.logger.info(
                f"生成场景 {scene_id} 的音频: {narration[:50]}..."
            )

            # 调用 TTS 服务生成音频（带重试）
            success = tts_service.synthesize_speech_with_retry(
                text=narration,
                output_path=audio_path_str,
                max_retries=3,
            )

            if success:
                # 获取音频时长
                duration = tts_service.get_audio_duration(audio_path_str)
                if duration:
                    scene["audio_duration"] = duration
                    self.logger.info(
                        f"✅ 场景 {scene_id} 音频生成成功，时长: {duration:.2f}s"
                    )
                else:
                    self.logger.warning(
                        f"⚠️ 无法获取场景 {scene_id} 音频时长"
                    )

                # 将音频路径添加到场景数据（使用绝对路径）
                scene["audio_path"] = audio_path_str
                audio_generated_count += 1
            else:
                self.logger.error(
                    f"❌ 场景 {scene_id} 音频生成失败，视频将继续生成但无音频"
                )
                audio_skipped_count += 1

        self.logger.info(
            f"🎤 音频生成完成: 成功 {audio_generated_count} 个，"
            f"跳过 {audio_skipped_count} 个，"
            f"共 {len(scenes)} 个场景"
        )

        return script_data

    # _safe_update_sub_task 方法已移除 - SubVideoTask 功能已完全移除
