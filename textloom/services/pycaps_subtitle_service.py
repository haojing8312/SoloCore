"""
PyCaps 字幕服务
完全基于PyCaps项目的字幕生成服务，替代原有的字幕渲染系统
"""

import os
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from config import settings
from services.pycaps_converter import convert_srt_to_pycaps_json
from utils.storage_utils import upload_file_to_storage
from utils.sync_logging import get_logger


class PyCapsSubtitleService:
    """PyCaps 字幕生成服务"""

    def __init__(self):
        """初始化服务"""
        self.logger = get_logger("pycaps_subtitle")
        self.temp_dir = settings.workspace_dir or "/tmp"
        self.enabled = settings.dynamic_subtitle_enabled

        self.logger.info(f"PyCaps字幕服务初始化完成 - 启用状态: {self.enabled}")

    def process_video_subtitles(
        self,
        video_url: str,
        subtitles_url: str,
        template: str,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        处理视频动态字幕

        Args:
            video_url: 原视频URL
            subtitles_url: 字幕文件URL (.srt格式)
            template: PyCaps模板名称 (如: hype, minimalist, explosive等)
            task_id: 任务ID，用于日志追踪

        Returns:
            处理结果，包含新的视频URL或错误信息
        """
        if not self.enabled:
            return {
                "success": True,
                "video_url": video_url,
                "message": "动态字幕功能已禁用，返回原视频",
                "processed": False,
            }

        try:
            self.logger.info(f"开始处理PyCaps动态字幕 - 任务ID: {task_id}")
            self.logger.info(f"原视频URL: {video_url}")
            self.logger.info(f"字幕URL: {subtitles_url}")
            self.logger.info(f"模板: {template}")

            # 验证必需参数
            if not video_url or not subtitles_url or not template:
                return self._error_result("缺少必需参数：video_url, subtitles_url, template", task_id)

            # 创建临时工作目录
            with tempfile.TemporaryDirectory(
                prefix=f"pycaps_{task_id}_", dir=self.temp_dir
            ) as work_dir:
                work_path = Path(work_dir)

                # 下载视频文件
                video_path = self._download_file(
                    video_url, work_path / "input_video.mp4"
                )
                if not video_path:
                    return self._error_result("视频文件下载失败", task_id)

                # 下载字幕文件
                subtitle_path = self._download_file(
                    subtitles_url, work_path / "subtitles.srt"
                )
                if not subtitle_path:
                    return self._error_result("字幕文件下载失败", task_id)

                # SRT转JSON
                subtitle_json_path = self._convert_srt_to_json(
                    subtitle_path, work_path / "subtitles.json"
                )
                if not subtitle_json_path:
                    return self._error_result("SRT转JSON失败", task_id)

                # 生成动态字幕视频
                output_video_path = work_path / "output_video.mp4"
                result = self._generate_video_with_pycaps(
                    video_path=video_path,
                    subtitle_json_path=subtitle_json_path,
                    template=template,
                    output_path=output_video_path,
                )

                if not result["success"]:
                    return result

                # 上传处理后的视频
                new_video_url = self._upload_processed_video(output_video_path, task_id)

                if not new_video_url:
                    return self._error_result("处理后视频上传失败", task_id)

                self.logger.info(f"PyCaps字幕处理完成 - 新视频URL: {new_video_url}")
                return {
                    "success": True,
                    "video_url": new_video_url,
                    "original_video_url": video_url,
                    "processed": True,
                    "message": "PyCaps字幕处理成功",
                }

        except Exception as e:
            error_msg = f"PyCaps字幕处理失败: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return self._error_result(error_msg, task_id)

    def _download_file(self, url: str, target_path: Path) -> Optional[Path]:
        """下载文件到指定路径"""
        try:
            self.logger.info(f"下载文件: {url} -> {target_path}")

            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = target_path.stat().st_size
            self.logger.info(f"文件下载成功: {target_path}, 大小: {file_size} bytes")
            return target_path

        except Exception as e:
            self.logger.error(f"文件下载失败: {url} - {e}")
            return None

    def _convert_srt_to_json(self, srt_path: Path, json_path: Path) -> Optional[Path]:
        """将SRT文件转换为PyCaps JSON格式"""
        try:
            self.logger.info(f"转换SRT到JSON: {srt_path} -> {json_path}")

            # 使用转换器
            output_file = convert_srt_to_pycaps_json(str(srt_path), str(json_path))

            if output_file and Path(output_file).exists():
                self.logger.info(f"SRT转JSON成功: {output_file}")
                return Path(output_file)
            else:
                self.logger.error("SRT转JSON失败：输出文件不存在")
                return None

        except Exception as e:
            self.logger.error(f"SRT转JSON失败: {e}")
            return None

    def _generate_video_with_pycaps(
        self,
        video_path: Path,
        subtitle_json_path: Path,
        template: str,
        output_path: Path,
    ) -> Dict[str, Any]:
        """使用PyCaps生成带字幕的视频"""
        try:
            self.logger.info("开始使用PyCaps生成字幕视频")

            # 导入PyCaps模块
            from services.pycaps.template.template_factory import TemplateFactory
            from services.pycaps.template.template_loader import TemplateLoader

            # 创建模板并构建PyCaps pipeline
            template_factory = TemplateFactory()
            template = template_factory.create(template)
            builder = TemplateLoader(template).with_input_video(str(video_path)).load(False)
            
            # 设置字幕数据
            builder = builder.with_subtitle_data_path(str(subtitle_json_path))
            
            # 设置输出文件
            builder = builder.with_output_video(str(output_path))
            
            # 构建并运行pipeline（在单独线程中避免asyncio冲突）
            pipeline = builder.build()
            
            # 使用线程池执行PyCaps以避免与FastAPI的asyncio循环冲突
            import asyncio
            import threading
            
            def run_pipeline():
                return pipeline.run()
            
            # 在单独线程中运行
            result = None
            exception = None
            
            def thread_target():
                nonlocal result, exception
                try:
                    result = run_pipeline()
                except Exception as e:
                    exception = e
            
            thread = threading.Thread(target=thread_target)
            thread.start()
            thread.join()
            
            if exception:
                raise exception

            # 检查输出文件
            if output_path.exists() and output_path.stat().st_size > 0:
                file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                self.logger.info(f"PyCaps视频生成成功，文件大小: {file_size:.2f}MB")
                return {"success": True}
            else:
                return {"success": False, "error": "PyCaps生成的视频文件无效"}

        except Exception as e:
            error_msg = f"PyCaps视频生成失败: {e}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return {"success": False, "error": error_msg}

    def _upload_processed_video(
        self, video_path: Path, task_id: Optional[str]
    ) -> Optional[str]:
        """上传处理后的视频到存储服务"""
        try:
            # 生成上传文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pycaps_subtitle_{task_id}_{timestamp}.mp4"

            # 上传到存储服务
            video_url = upload_file_to_storage(
                file_path=str(video_path), filename=filename, content_type="video/mp4"
            )

            if video_url:
                self.logger.info(f"视频上传成功: {video_url}")
                return video_url
            else:
                self.logger.error("视频上传失败: upload_file_to_storage返回None")
                return None

        except Exception as e:
            self.logger.error(f"视频上传失败: {e}")
            return None

    def _error_result(
        self, message: str, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成错误结果"""
        self.logger.error(f"任务ID: {task_id} - {message}")
        return {
            "success": False,
            "error": message,
            "task_id": task_id,
            "processed": False,
        }

    def get_available_templates(self) -> Dict[str, Any]:
        """获取可用的PyCaps模板列表"""
        try:
            # 导入PyCaps模板相关模块
            from services.pycaps.template.template_service import TemplateService

            service = TemplateService()
            builtin_templates = service.list_builtin_templates()
            local_templates = service.list_local_templates()
            
            # 合并所有模板
            all_templates = builtin_templates + local_templates

            return {
                "success": True,
                "templates": all_templates,
                "total": len(all_templates)
            }

        except Exception as e:
            self.logger.error(f"获取模板列表失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "templates": [],
                "total": 0
            }