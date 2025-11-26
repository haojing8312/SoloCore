"""
同步任务处理器 - 用于Celery任务
集成所有同步处理组件，实现完整的4阶段处理流程
"""

from __future__ import annotations

import os
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from config import settings
from models.celery_db import (
    sync_get_task_by_id,
    # sync_update_task_multi_video_results,  # 已移除：单视频模式不再需要此函数
    sync_update_task_progress,
    sync_update_task_status,
)
from models.script_generation import ScriptStyle
from models.task import TaskStatus
from processors.sync_material_analyzer import SyncMaterialAnalyzer
from processors.sync_material_processor import SyncMaterialProcessor
from services.sync_script_generator import SyncScriptGenerator
from services.sync_video_generator import SyncVideoGenerator
from utils.sync_logging import get_task_processor_logger, log_performance

logger = get_task_processor_logger()


class SyncTaskProcessor:
    """同步任务处理器 - 完整的4阶段处理流程"""

    def _determine_script_style(self, index: int, total_count: int) -> str:
        """确定子任务的脚本风格"""
        if index == 0:
            return "default"
        elif index == 1 and total_count >= 2:
            return "product_geek"
        else:
            return "default"  # 超过2个时重复使用默认风格

    def _generate_scripts_parallel(
        self,
        task_id: str,
        sub_task_ids: List[str],
        topic: str,
        source_content: str,
        material_context: dict,
        persona_id: Optional[int],
        progress_callback: Optional[Callable[[int, str, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        单视频模式脚本生成（保持兼容性接口）

        注意：虽然名称是parallel，但在单视频模式下只生成一个脚本
        保留参数 sub_task_ids 是为了兼容现有调用代码
        """
        try:
            # 单视频模式：只生成一个脚本
            logger.info(f"开始生成单视频脚本 - 任务: {task_id}")

            # 获取脚本风格（从数据库或使用默认值）
            task_info = sync_get_task_by_id(task_id)
            script_style = task_info.get("script_style_type", "default") if task_info else "default"

            if progress_callback:
                progress_callback(60, "script_generation", f"开始生成脚本（风格: {script_style}）...")

            # 生成单个脚本
            script_result = self.script_generator.generate_single_script_sync(
                task_id=task_id,
                topic=topic,
                source_content=source_content,
                material_context=material_context,
                persona_id=persona_id,
                script_style=script_style
            )

            if script_result.get("success"):
                script_data = script_result.get("script_data", {})

                # 更新主任务的脚本样式（脚本详细数据已保存在 script_contents 表中）
                try:
                    # 只保存脚本样式类型到主任务表
                    sync_update_task_status(task_id, "processing", {
                        "script_style_type": script_style
                    })
                except Exception as e:
                    logger.warning(f"更新主任务脚本样式失败: {e}")

                logger.info(f"单视频脚本生成成功 - 任务: {task_id}")

                if progress_callback:
                    progress_callback(75, "script_generation", "脚本生成完成")

                # 返回兼容格式（使用虚拟sub_task_id）
                return [{
                    "sub_task_id": sub_task_ids[0] if sub_task_ids else f"{task_id}_video_1",
                    "success": True,
                    "script_data": script_data,
                    "script_style": script_style
                }]
            else:
                # 脚本生成失败
                error_msg = script_result.get("error", "脚本生成失败")
                logger.error(f"单视频脚本生成失败 - 任务: {task_id}: {error_msg}")

                return [{
                    "sub_task_id": sub_task_ids[0] if sub_task_ids else f"{task_id}_video_1",
                    "success": False,
                    "error": error_msg
                }]

        except Exception as e:
            error_msg = f"脚本生成异常: {str(e)}"
            logger.error(f"单视频脚本生成异常 - 任务: {task_id}: {e}", exc_info=True)

            return [{
                "sub_task_id": sub_task_ids[0] if sub_task_ids else f"{task_id}_video_1",
                "success": False,
                "error": error_msg
            }]

    def _update_main_task_progress(self, task_id: str, sub_task_ids: List[str] = None):
        """
        单视频模式进度更新（简化版）

        注意：sub_task_ids 参数保留用于兼容性，但在单视频模式下已不使用
        进度现在基于主任务的实际执行阶段，而不是子任务状态
        """
        # 单视频模式：此方法已简化为空操作
        # 进度由主流程在各阶段直接调用 sync_update_task_progress 更新
        # 保留此方法仅为兼容现有调用点
        logger.debug(f"单视频模式：跳过 _update_main_task_progress (任务: {task_id})")

    def _generate_videos_parallel(
        self,
        task_id: str,
        sub_task_ids: List[str],
        media_files: List[Dict[str, str]],
        mode: str,
        script_results: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, str, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        单视频模式视频生成（保持兼容性接口）

        注意：虽然名称是parallel，但在单视频模式下只生成一个视频
        保留参数 sub_task_ids 是为了兼容现有调用代码

        Args:
            script_results: 脚本生成结果列表，包含 script_data
        """
        try:
            logger.info(f"开始生成单视频 - 任务: {task_id}")

            if progress_callback:
                progress_callback(80, "video_generation", "开始生成视频...")

            # 从 script_results 参数获取脚本数据（内存传递，不从数据库读取）
            if not script_results or len(script_results) == 0:
                error_msg = f"任务 {task_id} 脚本结果为空"
                logger.error(error_msg)
                return [{
                    "sub_task_id": sub_task_ids[0] if sub_task_ids else f"{task_id}_video_1",
                    "success": False,
                    "error": error_msg
                }]

            # 获取第一个（也是唯一的）脚本结果
            first_script = script_results[0]
            script_data = first_script.get("script_data")
            if not script_data:
                error_msg = f"任务 {task_id} 脚本数据为空"
                logger.error(error_msg)
                return [{
                    "sub_task_id": sub_task_ids[0] if sub_task_ids else f"{task_id}_video_1",
                    "success": False,
                    "error": error_msg
                }]

            script_style = first_script.get("script_style", "default")
            logger.info(f"从内存获取脚本数据 - 任务: {task_id}, 样式: {script_style}")

            # 调用视频生成方法（包含 TTS 音频生成）
            result = self.video_generator.generate_single_video_by_style(
                script_data=script_data,
                media_files=media_files,
                task_id=task_id,
                script_style=script_style,
                mode=mode
            )

            if result and result.get('success'):
                result_status = result.get('status', 'unknown')
                video_url = result.get('video_url')
                thumbnail_url = result.get('thumbnail_url', '')
                duration = result.get('duration', 0)
                course_media_id = result.get('course_media_id')

                # 只有当视频真正完成时才设置为completed
                if result_status == "completed" and video_url:
                    # 视频已立即完成
                    logger.info(f"单视频立即完成 - 任务: {task_id}: {video_url}")

                    if progress_callback:
                        progress_callback(100, "video_generation", "视频生成完成")

                    return [{
                        "sub_task_id": sub_task_ids[0] if sub_task_ids else f"{task_id}_video_1",
                        "success": True,
                        "status": "completed",
                        "video_url": video_url,
                        "thumbnail_url": thumbnail_url,
                        "duration": duration,
                        "script_style": script_style
                    }]

                elif result_status == "processing" and course_media_id:
                    # 视频正在处理中，由轮询任务负责后续更新
                    logger.info(f"单视频提交成功 - 任务: {task_id}，等待轮询: course_media_id={course_media_id}")

                    if progress_callback:
                        progress_callback(90, "video_generation", "视频生成中，等待处理...")

                    return [{
                        "sub_task_id": sub_task_ids[0] if sub_task_ids else f"{task_id}_video_1",
                        "success": True,
                        "status": "processing",
                        "course_media_id": course_media_id,
                        "script_style": script_style,
                        # message字段仅用于Celery任务状态,不应传递给数据库更新
                        # "message": "视频生成中，由轮询任务处理"
                    }]

                else:
                    # 提交成功但状态异常
                    error_msg = f"视频提交成功但状态异常: status={result_status}, video_url={video_url}, course_media_id={course_media_id}"
                    logger.error(f"单视频状态异常 - 任务: {task_id}: {error_msg}")

                    return [{
                        "sub_task_id": sub_task_ids[0] if sub_task_ids else f"{task_id}_video_1",
                        "success": False,
                        "error": error_msg
                    }]

            else:
                error_msg = result.get('error', '视频生成失败') if result else '视频生成失败'
                logger.error(f"单视频生成失败 - 任务: {task_id}: {error_msg}")

                return [{
                    "sub_task_id": sub_task_ids[0] if sub_task_ids else f"{task_id}_video_1",
                    "success": False,
                    "error": error_msg
                }]

        except Exception as e:
            error_msg = f"视频生成异常: {str(e)}"
            logger.error(f"单视频生成异常 - 任务: {task_id}: {e}", exc_info=True)

            return [{
                "sub_task_id": sub_task_ids[0] if sub_task_ids else f"{task_id}_video_1",
                "success": False,
                "error": error_msg
            }]

    def __init__(self, workspace_dir: str) -> None:
        """初始化同步任务处理器"""
        self.workspace_dir: str = workspace_dir

        # 初始化各组件
        self.material_processor: SyncMaterialProcessor = SyncMaterialProcessor(
            workspace_dir
        )
        self.material_analyzer: SyncMaterialAnalyzer = SyncMaterialAnalyzer(
            workspace_dir
        )
        self.script_generator: SyncScriptGenerator = SyncScriptGenerator()
        self.video_generator: SyncVideoGenerator = SyncVideoGenerator()

        logger.info(f"SyncTaskProcessor初始化完成 - 工作空间: {workspace_dir}")

    @log_performance(get_task_processor_logger(), "完整任务处理")
    def process_text_to_video_task(
        self,
        task_id: str,
        source_file: str,
        workspace_dir: str,
        mode: str = "multi_scene",
        persona_id: Optional[int] = None,
        multi_video_count: int = 1,
        progress_callback: Optional[Callable[[int, str, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        同步处理文本转视频任务 - 完整4阶段流程

        Args:
            task_id: 任务ID
            source_file: 源文件路径
            workspace_dir: 工作目录
            mode: 视频模式 (multi_scene/single_scene)
            persona_id: 人设ID
            multi_video_count: 多视频数量
            progress_callback: 进度回调函数

        Returns:
            处理结果字典
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"开始处理文本转视频任务 - ID: {task_id}")
            logger.info(
                f"参数 - 源文件: {source_file}, 模式: {mode}, 多视频数: {multi_video_count}"
            )

            # 更新任务状态为处理中
            sync_update_task_status(task_id, "processing", "开始处理任务")
            
            # 更新当前阶段
            from models.celery_db import sync_update_task_stage
            sync_update_task_stage(task_id, "material_processing")

            # ================ 阶段1: 素材处理 (0-25%) ================
            if progress_callback:
                progress_callback(5, "material_processing", "开始处理素材...")

            stage1_start = datetime.utcnow()
            logger.info(f"📎 阶段1开始: 素材处理 - 任务: {task_id}")

            material_result = self.material_processor.process_materials_sync(
                source_file=source_file, task_id=task_id, workspace_dir=workspace_dir
            )

            stage1_duration = (datetime.utcnow() - stage1_start).total_seconds()

            if not material_result.get("success"):
                logger.error(
                    f"❌ 阶段1失败: 素材处理 - 任务: {task_id}, 耗时: {stage1_duration:.2f}s"
                )
                raise RuntimeError(f"素材处理失败: {material_result.get('error')}")

            media_files = material_result.get("media_files", [])
            extracted_content = material_result.get("extracted_content", "")

            # 验证是否有有效的extracted_content
            if not extracted_content or len(extracted_content.strip()) < 10:
                error_msg = "没有有效的源内容，无法继续处理"
                logger.error(f"❌ {error_msg} - 任务: {task_id}")
                sync_update_task_status(
                    task_id, 
                    TaskStatus.FAILED,
                    {
                        "error_message": error_msg,
                        "completed_at": datetime.utcnow()
                    }
                )
                raise RuntimeError(error_msg)

            logger.info(
                f"✅ 阶段1完成: 素材处理 - 任务: {task_id}, 耗时: {stage1_duration:.2f}s, "
                f"素材数: {len(media_files)}个, 内容长度: {len(extracted_content)}字符"
            )
            sync_update_task_progress(
                task_id, 25, "material_processing", "素材处理完成"
            )

            if progress_callback:
                progress_callback(
                    25,
                    "material_processing",
                    f"素材处理完成，共{len(media_files)}个文件",
                )

            # ================ 阶段2: 素材分析 (25-50%) ================
            sync_update_task_stage(task_id, "material_analysis")
            if progress_callback:
                progress_callback(30, "material_analysis", "开始AI分析素材...")

            stage2_start = datetime.utcnow()
            logger.info(
                f"📎 阶段2开始: 素材分析 - 任务: {task_id}, 素材数: {len(media_files)}个"
            )
            # 将阶段1产出的 media_files 转换为 MediaItem 列表
            from models.task import MediaItem, MediaType

            media_items: List[MediaItem] = []
            for m in media_files:
                try:
                    media_type = (
                        MediaType.IMAGE
                        if (
                            m.get("file_type") == "image"
                            or m.get("media_type") == "image"
                        )
                        else MediaType.VIDEO
                    )
                    item = MediaItem(
                        id=m.get("id"),
                        task_id=m.get("task_id"),
                        original_url=m.get("original_url")
                        or m.get("url")
                        or m.get("file_url"),
                        media_type=media_type,
                        filename=m.get("filename"),
                        file_size=m.get("file_size"),
                        mime_type=m.get("mime_type"),
                        resolution=m.get("resolution"),
                        local_path=m.get("local_path"),
                        file_url=m.get("file_url"),
                        context_before=m.get("context_before"),
                        context_after=m.get("context_after"),
                        surrounding_paragraph=m.get("surrounding_paragraph")
                        or m.get("context"),
                        position_in_content=m.get("position")
                        or m.get("position_in_content"),
                        caption=m.get("caption"),
                    )
                    media_items.append(item)
                except Exception:
                    continue
            analysis_result = self.material_analyzer.analyze_materials_with_context(
                media_items
            )

            stage2_duration = (datetime.utcnow() - stage2_start).total_seconds()

            # analyze_materials_with_context 总是返回summary，不包含 success 布尔
            total_analyzed = analysis_result.get("total_analyzed", 0)
            failed_count = analysis_result.get("failed_count", 0)
            fail_rate = (failed_count / total_analyzed) if total_analyzed else 1.0
            if total_analyzed > 0 and fail_rate > 0.9:
                # 失败率>90%，终止任务
                logger.error(
                    f"❌ 阶段2失败: 素材分析失败率过高({fail_rate:.0%}) - 任务: {task_id}, 耗时: {stage2_duration:.2f}s"
                )
                sync_update_task_progress(
                    task_id, 50, "material_analysis", "素材分析失败率>90%"
                )
                raise RuntimeError("素材分析失败率过高，终止任务")

            material_context = {
                "summary": {
                    "total_count": analysis_result.get("total_analyzed", 0),
                    "image_count": analysis_result.get("images_analyzed", 0),
                    "video_count": analysis_result.get("videos_analyzed", 0),
                },
                "analysis_results": analysis_result.get("analysis_results", []),
            }
            analysis_results = analysis_result.get("analysis_results", [])

            logger.info(
                f"✅ 阶段2完成: 素材分析 - 任务: {task_id}, 耗时: {stage2_duration:.2f}s, "
                f"分析结果: {len(analysis_results)}个, 上下文键: {len(material_context)}个"
            )
            sync_update_task_progress(task_id, 50, "material_analysis", "素材分析完成")

            if progress_callback:
                progress_callback(
                    50,
                    "material_analysis",
                    f"素材分析完成，分析了{len(analysis_results)}个文件",
                )

            # ================ 阶段3: 跳过子任务拆分 (单视频模式) ================
            # 注意: 多视频架构已移除，直接使用单视频模式
            stage3_start = datetime.utcnow()
            logger.info(
                f"📎 阶段3: 单视频模式 - 任务: {task_id} (跳过子任务拆分)"
            )

            # 单视频模式：创建一个虚拟子任务ID用于兼容现有流程
            sub_task_ids = [f"{task_id}_video_1"]

            # 从数据库获取脚本风格
            from models.celery_db import sync_get_task_by_id
            task_info = sync_get_task_by_id(task_id)
            script_style = task_info.get("script_style_type", "default") if task_info else "default"
            logger.debug(f"使用脚本风格: {script_style}")

            stage3_duration = (datetime.utcnow() - stage3_start).total_seconds()
            logger.info(
                f"✅ 阶段3完成: 单视频模式 - 任务: {task_id}, 耗时: {stage3_duration:.2f}s"
            )

            if progress_callback:
                progress_callback(55, "sub_task_creation", "单视频模式，跳过子任务拆分")

            # ================ 阶段4: 脚本生成 (55-75%) ================
            sync_update_task_stage(task_id, "script_generation")
            if progress_callback:
                progress_callback(60, "script_generation", "开始并行生成脚本...")

            stage4_start = datetime.utcnow()
            logger.info(
                f"📎 阶段4开始: 并行脚本生成 - 任务: {task_id}, 子任务数: {len(sub_task_ids)}"
            )

            # 提取主题
            topic_start = datetime.utcnow()
            topic = self._extract_topic_from_content_sync(extracted_content)
            topic_duration = (datetime.utcnow() - topic_start).total_seconds()
            logger.debug(f"主题提取完成: '{topic}' - 耗时: {topic_duration:.2f}s")

            # 并行生成脚本
            script_gen_start = datetime.utcnow()
            script_results = self._generate_scripts_parallel(
                task_id=task_id,
                sub_task_ids=sub_task_ids,
                topic=topic,
                source_content=extracted_content,
                material_context=material_context,
                persona_id=persona_id,
                progress_callback=progress_callback
            )
            script_gen_duration = (datetime.utcnow() - script_gen_start).total_seconds()

            stage4_duration = (datetime.utcnow() - stage4_start).total_seconds()

            successful_scripts = [r for r in script_results if r.get("success")]
            failed_scripts = [r for r in script_results if not r.get("success")]
            
            if not successful_scripts:
                logger.error(
                    f"❌ 阶段4失败: 脚本生成 - 任务: {task_id}, 耗时: {stage4_duration:.2f}s"
                )
                raise RuntimeError(f"所有脚本生成失败: {[r.get('error') for r in failed_scripts]}")

            logger.info(
                f"✅ 阶段4完成: 并行脚本生成 - 任务: {task_id}, 总耗时: {stage4_duration:.2f}s, "
                f"生成耗时: {script_gen_duration:.2f}s, 成功脚本: {len(successful_scripts)}个"
            )
            sync_update_task_progress(task_id, 75, "script_generation", "脚本生成完成")

            if progress_callback:
                progress_callback(
                    75,
                    "script_generation",
                    f"脚本生成完成，成功: {len(successful_scripts)}个，失败: {len(failed_scripts)}个",
                )

            # ================ 阶段5: 视频生成 (75-100%) ================
            sync_update_task_stage(task_id, "video_generation")
            if progress_callback:
                progress_callback(80, "video_generation", "开始并行生成视频...")

            stage5_start = datetime.utcnow()
            logger.info(
                f"📎 阶段5开始: 并行视频生成 - 任务: {task_id}, 成功脚本数: {len(successful_scripts)}个"
            )

            # 并行生成视频（基于已有脚本的子任务）
            video_gen_start = datetime.utcnow()
            video_results = self._generate_videos_parallel(
                task_id=task_id,
                sub_task_ids=sub_task_ids,
                media_files=media_files,
                mode=mode,
                script_results=successful_scripts,  # 传递脚本结果（内存传递）
                progress_callback=progress_callback
            )
            video_gen_duration = (datetime.utcnow() - video_gen_start).total_seconds()
            stage5_duration = (datetime.utcnow() - stage5_start).total_seconds()

            # 分类视频结果
            completed_videos = [r for r in video_results if r.get("success") and r.get("status") == "completed"]
            failed_videos = [r for r in video_results if not r.get("success")]
            processing_videos = [r for r in video_results if r.get("status") in ("processing", "queued")]

            logger.info(
                f"✅ 阶段5完成: 并行视频生成 - 任务: {task_id}, 总耗时: {stage5_duration:.2f}s, "
                f"生成耗时: {video_gen_duration:.2f}s, 已完成: {len(completed_videos)}个, "
                f"进行中: {len(processing_videos)}个, 失败: {len(failed_videos)}个"
            )

            # 更新多视频结果到数据库
            multi_video_results = []
            for i, result in enumerate(video_results):
                video_result = {
                    "sub_task_id": result.get("sub_task_id", f"{task_id}_video_{i+1}"),
                    "sub_task_index": result.get("sub_task_index", i + 1),
                    "script_style": result.get("script_style", "default"),
                    "success": result.get("success", False),
                    "video_url": result.get("video_url"),
                    "thumbnail_url": result.get("thumbnail_url"),
                    "duration": result.get("duration"),
                    "course_media_id": result.get("course_media_id"),
                    "error": result.get("error"),
                    "generated_at": datetime.utcnow().isoformat(),
                }
                multi_video_results.append(video_result)

            # sync_update_task_multi_video_results(task_id, multi_video_results)
            # ↑ 已注释：单视频模式不再需要更新 multi_video_results 字段（该字段已从数据库删除）
            logger.debug(f"单视频模式：跳过 multi_video_results 更新 (任务: {task_id})")

            # 使用_update_main_task_progress方法来基于子任务实际状态更新主任务
            # 这样避免了基于video_results的不准确状态判断
            logger.info("基于子任务状态更新主任务状态...")
            self._update_main_task_progress(task_id, sub_task_ids)
            
            # 获取更新后的主任务状态用于日志
            from models.celery_db import sync_get_task_by_id
            updated_task = sync_get_task_by_id(task_id)
            if updated_task:
                final_status = updated_task.get("status", "processing")
                progress = updated_task.get("progress", 85)
                final_description = f"状态已基于子任务更新为: {final_status}"
            else:
                final_status = "processing"
                progress = 85
                final_description = "状态更新中..."

            status_update_start = datetime.utcnow()
            status_update_duration = (
                datetime.utcnow() - status_update_start
            ).total_seconds()

            # 构建返回结果
            total_duration = (datetime.utcnow() - start_time).total_seconds()

            # 基于实际视频结果统计
            completed_videos = [r for r in video_results if r.get("success") and r.get("status") == "completed"]
            failed_videos = [r for r in video_results if not r.get("success")]
            processing_videos = [r for r in video_results if r.get("status") in ("processing", "queued")]
            
            # 总结性日志
            logger.info(
                f"🎉 任务完成总结 - 任务ID: {task_id}\n"
                f"  • 总耗时: {total_duration:.2f}s\n"
                f"  • 阶段1(素材处理): {stage1_duration:.2f}s\n"
                f"  • 阶段2(素材分析): {stage2_duration:.2f}s\n"
                f"  • 阶段3(子任务拆分): {stage3_duration:.2f}s\n"
                f"  • 阶段4(脚本生成): {stage4_duration:.2f}s\n"
                f"  • 阶段5(视频生成): {stage5_duration:.2f}s\n"
                f"  • 状态更新: {status_update_duration:.3f}s\n"
                f"  • 最终状态: {final_status}\n"
                f"  • 视频结果: 已完成{len(completed_videos)}个, 进行中{len(processing_videos)}个, 失败{len(failed_videos)}个"
            )

            result = {
                "task_id": task_id,
                "status": final_status,
                "progress": progress,
                "description": final_description,
                "processing_time": total_duration,
                # 素材处理结果
                "material_count": len(media_files),
                "extracted_content_length": len(extracted_content),
                # 分析结果
                "analysis_results_count": len(analysis_results),
                # 脚本结果
                "script_count": len(successful_scripts),
                "scripts": successful_scripts,
                # 视频结果
                "video_results": video_results,
                "successful_video_count": len(completed_videos),
                "failed_video_count": len(failed_videos),
                "processing_video_count": len(processing_videos),
                # 多视频结果详情
                "multi_video_results": multi_video_results,
                # 阶段耗时统计
                "stage_durations": {
                    "material_processing": f"{stage1_duration:.2f}s",
                    "material_analysis": f"{stage2_duration:.2f}s",
                    "script_generation": f"{stage3_duration:.2f}s",
                    "video_generation": f"{stage4_duration:.2f}s",
                    "status_update": f"{status_update_duration:.3f}s",
                },
                # 第一个成功视频的信息（向后兼容）
                "video_url": (
                    completed_videos[0].get("video_url") if completed_videos else None
                ),
                "script_title": (
                    successful_scripts[0].get("title", topic)
                    if successful_scripts
                    else topic
                ),
                "script_description": (
                    successful_scripts[0].get("description", "")
                    if successful_scripts
                    else ""
                ),
                "video_duration": (
                    completed_videos[0].get("duration", 0) if completed_videos else 0
                ),
                "completed_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"✅ 任务处理完成 - ID: {task_id}, 状态: {final_status}, 总耗时: {total_duration:.2f}秒"
            )
            return result

        except Exception as e:
            total_duration = (datetime.utcnow() - start_time).total_seconds()
            error_msg = str(e)

            logger.error(
                f"❌ 任务处理器失败 - 任务ID: {task_id}\n"
                f"  • 总耗时: {total_duration:.2f}s\n"
                f"  • 错误信息: {error_msg}\n"
                f"  • 错误类型: {type(e).__name__}",
                exc_info=True,
            )

            # 更新任务为失败状态
            try:
                sync_update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    {
                        "error_message": error_msg,
                        "error_type": type(e).__name__,
                        "total_duration": f"{total_duration:.2f}s",
                        "completed_at": datetime.utcnow(),
                    },
                )
            except Exception as db_error:
                logger.error(f"更新任务失败状态时出错: {db_error}")

            raise
            logger.error(f"错误详情: {traceback.format_exc()}")

            # 更新失败状态
            sync_update_task_status(task_id, "failed", error_msg)

            if progress_callback:
                progress_callback(0, "failed", error_msg)

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # 返回失败结果
            return {
                "task_id": task_id,
                "status": "failed",
                "error": error_msg,
                "processing_time": processing_time,
                "failed_at": datetime.utcnow().isoformat(),
            }

    def _extract_topic_from_content_sync(self, content: str) -> str:
        """从内容中同步提取主题"""
        try:
            import re

            # 尝试提取第一个标题
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if title_match:
                return title_match.group(1).strip()

            # 如果没有找到标题，取前50个字符作为主题
            clean_content = re.sub(r"[#*\-\[\](){}]", "", content)
            lines = [line.strip() for line in clean_content.split("\n") if line.strip()]
            if lines:
                topic = lines[0][:50]
                return topic if len(topic) < 50 else topic + "..."

            return "视频内容"

        except Exception:
            return "视频内容"
