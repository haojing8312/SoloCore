"""
同步素材分析器 - 用于Celery任务
完全同步版本的MaterialAnalyzer，避免事件循环冲突
"""

import asyncio
import base64
import json
import math
import os
import re
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from config import settings
from models.celery_db import sync_create_material_analysis
from models.material_analysis import (
    AnalysisStatus,
    MaterialAnalysis,
    QualityLevel,
    VideoAnalysis,
    VideoKeyFrame,
)
from models.task import MediaItem, MediaType
from utils.oss.storage_factory import StorageFactory
from utils.sync_clients import get_sync_openai_client
from utils.sync_logging import get_material_analyzer_logger, log_performance


class SyncMaterialAnalyzer:
    """同步素材分析器：使用多模态AI分析图片视频内容"""

    def __init__(self, workspace_dir: str = "workspace"):
        """初始化同步素材分析器"""
        # 兼容测试：保持属性为字符串
        self.workspace_dir = workspace_dir
        # 实际路径对象
        self.workspace_path = Path(workspace_dir)
        self.processed_dir = self.workspace_path / "processed"
        self.logs_dir = self.workspace_path / "logs"
        self.keyframes_dir = self.workspace_path / "keyframes"

        # 创建必要的目录
        for dir_path in [self.processed_dir, self.logs_dir, self.keyframes_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # 初始化日志器
        self.logger = get_material_analyzer_logger()

        # 支持的文件格式
        self.image_formats = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
        self.video_formats = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}

        # AI分析配置
        self.max_tokens = 800
        self.analysis_model = settings.image_analysis_model_name

        # OpenAI客户端（与分析器日志器统一，便于将调试写入 sync_material_analyzer 日志文件）
        self.openai_client = get_sync_openai_client(logger=self.logger)

        # 并发分析配置（即便在同步实现中，也暴露信号量以便测试/兼容）
        self.max_concurrent_analysis = 4
        self.analysis_semaphore = asyncio.Semaphore(self.max_concurrent_analysis)

        self.logger.info(f"SyncMaterialAnalyzer初始化完成 - 工作目录: {workspace_dir}")

    # ==================== 与tests同步的辅助同步方法 ====================

    # 已移除：旧的同步图片上下文直连方法（降级逻辑）

    # 已移除：旧的关键帧同步方法（降级逻辑）

    def _extract_keywords_sync(self, description: str) -> List[str]:
        """从中文描述中提取关键词（简化实现，尽量覆盖常见词）。"""
        if not description:
            return []
        # 粗略分词：按非中文/字母数字分割，保留长度>=2的片段
        tokens = [
            t
            for t in re.split(r"[^\u4e00-\u9fa5A-Za-z0-9]+", description)
            if len(t) >= 2
        ]
        # 频次统计
        freq: Dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        # 常见科技相关高权重词加权
        boost = {
            "科技": 2,
            "产品": 2,
            "手机": 3,
            "技术": 2,
            "界面": 2,
            "演示": 2,
            "创新": 2,
        }
        for k, v in list(freq.items()):
            if k in boost:
                freq[k] = v + boost[k]
        # 选Top 10
        sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [k for k, _ in sorted_tokens[:10]]
        return keywords

    def _validate_analysis_result_sync(self, result: Dict[str, Any]) -> bool:
        """校验分析结果结构。"""
        if not isinstance(result, dict):
            return False
        required_keys = {"media_item_id", "ai_description", "analysis_status"}
        if not required_keys.issubset(result.keys()):
            return False
        if not result.get("ai_description"):
            return False
        return True

    def _build_material_context_sync(
        self, analysis_results: List[Dict[str, Any]], media_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """构建素材总体上下文摘要。"""
        total = len(analysis_results)
        image_ids = {m["id"] for m in media_files if m.get("file_type") == "image"}
        video_ids = {m["id"] for m in media_files if m.get("file_type") == "video"}
        image_count = len(
            [r for r in analysis_results if r.get("media_item_id") in image_ids]
        )
        video_count = len(
            [r for r in analysis_results if r.get("media_item_id") in video_ids]
        )
        # 汇总标签
        all_tags: List[str] = []
        for r in analysis_results:
            if isinstance(r.get("key_objects"), list):
                all_tags.extend(r["key_objects"])
        # 去重保序
        seen = set()
        unique_tags = []
        for t in all_tags:
            if t not in seen:
                unique_tags.append(t)
                seen.add(t)
        context = {
            "summary": {
                "total_count": total,
                "image_count": image_count,
                "video_count": video_count,
            },
            "tags": unique_tags,
            "analysis_results": analysis_results,
        }
        return context

    def _parse_json_strict(self, text: str) -> Dict[str, Any]:
        """健壮解析模型返回文本为JSON。
        - 去除markdown代码块(```/```json)
        - 抽取首个看似完整的JSON对象
        - 尝试修复截断的JSON
        - 再进行json.loads
        """
        if not text:
            raise ValueError("empty_response")
        s = text.strip()
        # 去除markdown代码块包裹
        if s.startswith("```"):
            s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
            s = re.sub(r"\s*```$", "", s, flags=re.IGNORECASE)
            s = s.strip()
        # 若前缀非"{"，尝试提取首个大括号包围段
        if not s.startswith("{"):
            m = re.search(r"\{[\s\S]*\}", s)
            if m:
                s = m.group(0)

        # 首先尝试直接解析
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass

        # 尝试修复截断的JSON
        s = self._repair_truncated_json(s)
        return json.loads(s)

    def _repair_truncated_json(self, text: str) -> str:
        """尝试修复截断的JSON字符串。"""
        s = text.strip()

        # 计算未闭合的括号
        open_braces = s.count("{") - s.count("}")
        open_brackets = s.count("[") - s.count("]")

        # 检查是否在字符串中间被截断（奇数个未转义引号）
        in_string = False
        escaped = False
        for char in s:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = not in_string

        # 如果在字符串中间截断，先闭合字符串
        if in_string:
            s = s + '"'

        # 闭合未闭合的括号
        s = s + "]" * open_brackets + "}" * open_braces

        return s

    # ==================== 工具方法：ffprobe + ffmpeg ====================

    def _persist_material_analysis(
        self,
        media_item: MediaItem,
        analysis: MaterialAnalysis,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """将素材分析结果入库（成功/失败都写入）。"""
        try:
            file_type = (
                "image"
                if media_item.media_type == MediaType.IMAGE
                else (
                    "video" if media_item.media_type == MediaType.VIDEO else "unknown"
                )
            )
            payload = {
                "task_id": str(media_item.task_id),
                "media_item_id": (
                    str(getattr(media_item, "id", ""))
                    if getattr(media_item, "id", None)
                    else None
                ),
                "original_url": getattr(media_item, "original_url", None)
                or getattr(media_item, "file_url", None)
                or "",
                "file_url": getattr(analysis, "cloud_url", None)
                or getattr(media_item, "file_url", None),
                "file_type": file_type,
                "file_size": getattr(media_item, "file_size", None),
                "status": (
                    analysis.analysis_status.value
                    if hasattr(analysis.analysis_status, "value")
                    else str(analysis.analysis_status)
                ),
                "ai_description": getattr(analysis, "description", None),
                "extracted_text": None,
                "key_objects": getattr(analysis, "tags", None) or [],
                "emotional_tone": None,
                "visual_style": None,
                "quality_score": getattr(analysis, "quality_score", None),
                "quality_level": getattr(analysis, "quality_level", None),
                "usage_suggestions": getattr(analysis, "usage_suggestions", None) or [],
                "duration": getattr(analysis, "duration", None),
                "fps": None,
                "resolution": getattr(analysis, "resolution", None),
                "key_frames": (extra or {}).get("key_frames") if extra else None,
                "dimensions": getattr(analysis, "resolution", None),
                "color_palette": [],
            }
            sync_create_material_analysis(payload)
        except Exception as e:
            # 不阻断主流程
            try:
                self.logger.error(f"素材分析结果入库失败(忽略): {e}")
            except Exception:
                pass

    def _probe_video_metadata_ffprobe(
        self, source: str, timeout_seconds: int = 15
    ) -> Optional[Dict[str, Any]]:
        """使用 ffprobe 获取视频元数据(width/height/duration/fps)。失败返回 None。"""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                source,
            ]
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout_seconds,
            )
            if proc.returncode != 0:
                return None
            data = json.loads(proc.stdout.decode("utf-8") or "{}")
            streams = data.get("streams") or []
            format_info = data.get("format") or {}
            vstream = None
            for s in streams:
                if s.get("codec_type") == "video":
                    vstream = s
                    break
            if not vstream:
                return None
            width = vstream.get("width")
            height = vstream.get("height")
            duration = None
            try:
                if format_info.get("duration") is not None:
                    duration = float(format_info.get("duration"))
                elif vstream.get("duration") is not None:
                    duration = float(vstream.get("duration"))
            except Exception:
                duration = None
            fps = None
            try:
                fr = vstream.get("avg_frame_rate") or vstream.get("r_frame_rate")
                if isinstance(fr, str) and "/" in fr:
                    num, den = fr.split("/")
                    num = float(num)
                    den = float(den) if float(den) != 0 else 1.0
                    fps = num / den if den else None
            except Exception:
                fps = None
            if not width or not height:
                return None
            return {
                "width": int(width),
                "height": int(height),
                "duration": duration,
                "fps": fps,
            }
        except Exception as e:
            try:
                self.logger.warning(f"ffprobe探测失败: {e}")
            except Exception:
                pass
            return None

    def _extract_keyframes_ffmpeg(
        self, video_path: str, num_frames: int = 3
    ) -> List[Dict[str, Any]]:
        """使用 ffmpeg 按时间均匀抽取关键帧，返回本地帧信息列表。"""
        try:
            meta = self._probe_video_metadata_ffprobe(video_path)
            if not meta or not meta.get("duration"):
                return []
            duration = float(meta["duration"])
            if duration <= 0:
                return []
            timestamps = [
                duration * i / (num_frames + 1) for i in range(1, num_frames + 1)
            ]
            results: List[Dict[str, Any]] = []
            for idx, ts in enumerate(timestamps):
                out_name = f"keyframe_{idx}_{int(ts*1000)}.jpg"
                out_path = str(self.keyframes_dir / out_name)
                cmd = [
                    "ffmpeg",
                    "-ss",
                    f"{ts}",
                    "-i",
                    video_path,
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    "-y",
                    out_path,
                ]
                proc = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
                )
                if proc.returncode == 0 and os.path.exists(out_path):
                    results.append(
                        {
                            "timestamp": ts,
                            "frame_path": out_path,
                            "frame_filename": out_name,
                        }
                    )
            return results
        except Exception as e:
            self.logger.error(f"ffmpeg关键帧提取失败: {e}")
            return []

    def _analyze_single_media_sync(
        self, media_file: Dict[str, Any], extracted_content: str, task_id: str
    ) -> Dict[str, Any]:
        # 已废弃
        raise NotImplementedError(
            "_analyze_single_media_sync 已移除，请使用 analyze_material_with_context"
        )

    def analyze_materials_sync(
        self, media_files: List[Dict[str, Any]], extracted_content: str, task_id: str
    ) -> Dict[str, Any]:
        # 已废弃
        raise NotImplementedError(
            "analyze_materials_sync 已移除，请使用 analyze_materials_with_context"
        )

    @log_performance(get_material_analyzer_logger(), "分析素材列表")
    def analyze_materials_with_context(
        self, media_items: List[MediaItem]
    ) -> Dict[str, Any]:
        """
        分析素材列表（含上下文信息）

        Args:
            media_items: 媒体项目列表

        Returns:
            分析结果汇总
        """
        self.logger.info(f"开始分析 {len(media_items)} 个素材文件（含上下文）")
        from concurrent.futures import ThreadPoolExecutor, as_completed

        analysis_results: List[MaterialAnalysis] = []
        success_count = 0
        failed_count = 0
        with ThreadPoolExecutor(max_workers=self.max_concurrent_analysis) as executor:
            future_to_item = {
                executor.submit(self.analyze_material_with_context, item): item
                for item in media_items
            }
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    analysis_results.append(result)
                    if result.analysis_status == AnalysisStatus.COMPLETED:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    self.logger.error(
                        f"并发分析异常 - ID: {getattr(item, 'id', None)}, 错误: {e}"
                    )
        summary = {
            "total_analyzed": len(media_items),
            "success_count": success_count,
            "failed_count": failed_count,
            "analysis_results": analysis_results,
            "images_analyzed": len(
                [
                    r
                    for r in analysis_results
                    if hasattr(r, "file_format")
                    and r.file_format in ["JPEG", "PNG", "GIF"]
                ]
            ),
            "videos_analyzed": len(
                [r for r in analysis_results if hasattr(r, "duration") and r.duration]
            ),
        }
        self.logger.info(f"素材分析完成 - 成功: {success_count}, 失败: {failed_count}")
        return summary

    def analyze_material_with_context(self, media_item: MediaItem) -> MaterialAnalysis:
        """
        分析包含上下文信息的素材文件

        Args:
            media_item: 包含文件路径和上下文信息的媒体项目对象

        Returns:
            素材分析结果
        """
        file_path = Path(media_item.local_path) if media_item.local_path else None
        local_exists = bool(file_path) and file_path.exists()
        if not local_exists:
            # 允许视频素材在无本地文件时使用直链URL进行分析
            if media_item.media_type == MediaType.VIDEO and (
                getattr(media_item, "file_url", None)
                or getattr(media_item, "original_url", None)
            ):
                self.logger.warning(
                    f"本地文件缺失，改用URL进行视频分析: local={file_path}, url={getattr(media_item, 'file_url', None) or getattr(media_item, 'original_url', None)}"
                )
            else:
                self.logger.error(f"文件不存在: {file_path}")
                raise RuntimeError(f"文件不存在: {file_path}")

        display_source = (
            str(file_path)
            if local_exists
            else (
                getattr(media_item, "file_url", None)
                or getattr(media_item, "original_url", None)
                or "unknown"
            )
        )
        self.logger.info(f"开始分析素材文件(含上下文): {display_source}")
        self.logger.info(f"素材类型: {media_item.media_type}")

        # 记录上下文信息
        if media_item.context_before or media_item.context_after:
            self.logger.debug(
                f"上下文信息 - 前文: '{media_item.context_before[-100:] if media_item.context_before else '无'}...'"
            )
            self.logger.debug(
                f"上下文信息 - 后文: '{media_item.context_after[:100] if media_item.context_after else '无'}...'"
            )

        # 将 material_id 注入到运行期上下文，供提示词填充
        try:
            self._runtime_material_id = str(
                getattr(media_item, "id", "runtime-material-id")
            )
        except Exception:
            self._runtime_material_id = "runtime-material-id"

        # 创建分析记录
        analysis = MaterialAnalysis(
            media_item_id=media_item.id, analysis_status=AnalysisStatus.PROCESSING
        )

        try:
            if media_item.media_type == MediaType.IMAGE:
                self.logger.info("开始图片分析(含上下文)...")
                result = self._analyze_image_with_context(media_item, analysis)
                self.logger.info(
                    f"图片分析完成 - 状态: {result.analysis_status}, 分辨率: {result.resolution}"
                )
                return result
            elif media_item.media_type == MediaType.VIDEO:
                self.logger.info("开始视频分析(含上下文)...")
                result = self._analyze_video_with_context(media_item, analysis)
                self.logger.info(
                    f"视频分析完成 - 状态: {result.analysis_status}, 时长: {result.duration}秒"
                )
                return result
            else:
                self.logger.warning("暂不支持音频文件分析")
                analysis.analysis_status = AnalysisStatus.FAILED
                analysis.error_message = "暂不支持音频文件分析"
                return analysis

        except Exception as e:
            self.logger.error(f"分析素材失败: {str(e)}")
            self.logger.error(f"错误详情: {traceback.format_exc()}")

            analysis.analysis_status = AnalysisStatus.FAILED
            analysis.error_message = str(e)
            return analysis

    def _analyze_image_with_context(
        self, media_item: MediaItem, analysis: MaterialAnalysis
    ) -> MaterialAnalysis:
        """分析图片素材（含上下文）"""
        try:
            # 获取图片基本信息
            with Image.open(media_item.local_path) as img:
                width, height = img.size
                format_name = img.format
                is_animated = hasattr(img, "is_animated") and img.is_animated

                analysis.resolution = f"{width}x{height}"
                analysis.file_format = format_name

                self.logger.info(
                    f"图片信息: 格式={format_name}, 尺寸={width}x{height}, 动图={is_animated}"
                )

            # 上传到云存储（与原版保持一致）
            cloud_url = self._upload_to_cloud(media_item.local_path, "images")
            if cloud_url:
                analysis.cloud_url = cloud_url
                analysis.upload_status = "completed"
                self.logger.info(f"图片已上传到云存储: {cloud_url}")
            else:
                analysis.upload_status = "failed"
                self.logger.warning("图片上传到云存储失败")

            # AI分析图片内容（含上下文）
            ai_result = self._analyze_image_with_ai_context(
                media_item.local_path,
                analysis.resolution,
                context_before=media_item.context_before,
                context_after=media_item.context_after,
                surrounding_paragraph=media_item.surrounding_paragraph,
                caption=getattr(media_item, "caption", None),
            )

            # 保存AI分析结果（字段对齐MaterialAnalysis）
            analysis.description = ai_result.get("description", "")
            analysis.contextual_description = ai_result.get(
                "contextual_description", ""
            )
            analysis.contextual_purpose = ai_result.get("contextual_purpose", "")
            analysis.content_role = ai_result.get("content_role", "")
            analysis.semantic_relevance = ai_result.get("semantic_relevance", 0.0)
            analysis.tags = ai_result.get("tags", [])
            analysis.quality_level = ai_result.get("quality_level")
            analysis.quality_score = ai_result.get("quality_score")
            analysis.usage_suggestions = ai_result.get("usage_suggestions", [])
            analysis.contextual_voiceover_script = ai_result.get(
                "contextual_voiceover_script", ""
            )
            analysis.voiceover_script = ai_result.get("voiceover_script", "")
            analysis.raw_ai_response = (
                ai_result.get("raw_response") if isinstance(ai_result, dict) else None
            )

            # 兼容tests字段：为同步版增加ai_description/key_objects别名
            try:
                analysis.__dict__["ai_description"] = analysis.description
                analysis.__dict__["key_objects"] = analysis.tags or []
            except Exception:
                pass

            if analysis.description:
                analysis.analysis_status = AnalysisStatus.COMPLETED
                self.logger.info(
                    f"AI图片分析成功 - 描述长度: {len(analysis.description)}"
                )
            else:
                analysis.analysis_status = AnalysisStatus.FAILED
                analysis.error_message = "AI分析返回空结果"
                self.logger.warning(f"AI图片分析失败: {analysis.error_message}")

            analysis.analyzed_at = datetime.utcnow()
            # 入库（成功/失败都写入）
            try:
                self._persist_material_analysis(media_item, analysis)
            except Exception as _e:
                self.logger.warning(f"图片分析结果入库失败(忽略)：{_e}")
            return analysis

        except Exception as e:
            raise RuntimeError(f"图片分析失败: {str(e)}")

    def _analyze_video_with_context(
        self, media_item: MediaItem, analysis: MaterialAnalysis
    ) -> MaterialAnalysis:
        """分析视频素材（含上下文）"""
        try:
            # 使用 ffprobe 获取元数据（支持本地或URL）
            source_local = media_item.local_path
            source_url = getattr(media_item, "file_url", None) or getattr(
                media_item, "original_url", None
            )
            probe_source = (
                source_local
                if (source_local and Path(source_local).exists())
                else (source_url or "")
            )
            meta = self._probe_video_metadata_ffprobe(probe_source)
            if not meta or not meta.get("width") or not meta.get("height"):
                raise RuntimeError("ffprobe未获取到有效视频元数据")
            width = int(meta["width"])
            height = int(meta["height"])
            duration = float(meta.get("duration") or 0)
            analysis.resolution = f"{width}x{height}"
            analysis.duration = duration
            try:
                if source_local and Path(source_local).exists():
                    analysis.file_format = Path(source_local).suffix[1:].upper()
                elif source_url:
                    analysis.file_format = Path(source_url).suffix[1:].upper()
            except Exception:
                pass
            self.logger.info(
                f"视频信息(ffprobe): 分辨率={width}x{height}, 时长={duration:.1f}秒"
            )

            # 上传到云存储（若无本地文件则直接复用现有URL）
            if source_local and Path(source_local).exists():
                cloud_url = self._upload_to_cloud(source_local, "videos")
                if cloud_url:
                    analysis.cloud_url = cloud_url
                    analysis.upload_status = "completed"
                    self.logger.info(f"视频已上传到云存储: {cloud_url}")
                else:
                    analysis.upload_status = "failed"
                    self.logger.warning("视频上传到云存储失败")
            else:
                if source_url:
                    analysis.cloud_url = source_url
                    analysis.upload_status = "completed"
                else:
                    analysis.upload_status = "failed"

            # 提取关键帧（ffmpeg），上传minio后用图片携带上下文分析
            key_source = (
                source_local
                if (source_local and Path(source_local).exists())
                else (source_url or "")
            )
            keyframes = self._extract_keyframes_ffmpeg(key_source, num_frames=3)
            if not keyframes:
                raise RuntimeError("关键帧提取失败，无法进行视频分析")
            uploaded_keyframes: List[Dict[str, Any]] = []
            for kf in keyframes:
                url = self._upload_to_cloud(kf["frame_path"], "keyframes")
                if url:
                    kf["frame_url"] = url
                uploaded_keyframes.append(kf)
            ai_result = self._analyze_video_with_ai_context(
                uploaded_keyframes,
                analysis.resolution,
                duration,
                context_before=media_item.context_before,
                context_after=media_item.context_after,
                surrounding_paragraph=media_item.surrounding_paragraph,
            )

            # 保存AI分析结果（字段对齐MaterialAnalysis）
            analysis.description = ai_result.get("description", "")
            analysis.contextual_description = ai_result.get(
                "contextual_description", ""
            )
            analysis.contextual_purpose = ai_result.get("contextual_purpose", "")
            analysis.content_role = ai_result.get("content_role", "")
            analysis.semantic_relevance = ai_result.get("semantic_relevance", 0.0)
            analysis.tags = ai_result.get("tags", [])
            analysis.quality_level = ai_result.get("quality_level")
            analysis.quality_score = ai_result.get("quality_score")
            analysis.usage_suggestions = ai_result.get("usage_suggestions", [])
            analysis.contextual_voiceover_script = ai_result.get(
                "contextual_voiceover_script", ""
            )
            analysis.voiceover_script = ai_result.get("voiceover_script", "")
            analysis.raw_ai_response = (
                ai_result.get("raw_response") if isinstance(ai_result, dict) else None
            )

            # 兼容tests字段：为同步版增加ai_description/key_objects别名
            try:
                analysis.__dict__["ai_description"] = analysis.description
                analysis.__dict__["key_objects"] = analysis.tags or []
            except Exception:
                pass

            if analysis.description:
                analysis.analysis_status = AnalysisStatus.COMPLETED
                self.logger.info(
                    f"AI视频分析成功 - 描述长度: {len(analysis.description)}"
                )
            else:
                analysis.analysis_status = AnalysisStatus.FAILED
                analysis.error_message = "AI分析返回空结果"
                self.logger.warning(f"AI视频分析失败: {analysis.error_message}")

            analysis.analyzed_at = datetime.utcnow()
            # 入库（附带关键帧信息）
            try:
                kf_payload = {
                    "key_frames": [
                        {
                            "timestamp": k.get("timestamp"),
                            "frame_url": k.get("frame_url") or k.get("frame_path"),
                        }
                        for k in uploaded_keyframes
                    ]
                }
            except Exception:
                kf_payload = None
            try:
                self._persist_material_analysis(media_item, analysis, extra=kf_payload)
            except Exception as _e:
                self.logger.warning(f"视频分析结果入库失败(忽略)：{_e}")
            return analysis

        except Exception as e:
            raise RuntimeError(f"视频分析失败: {str(e)}")

    # 注意：视频AI分析逻辑在文件后部定义，避免重复定义

    def _analyze_image_with_ai_context(
        self,
        image_path: str,
        resolution: str,
        context_before: str = None,
        context_after: str = None,
        surrounding_paragraph: str = None,
        caption: str = None,
    ) -> Dict[str, Any]:
        """使用AI分析图片内容（含上下文）

        业务层在此构建完整提示词；工具层仅负责转发与重试。
        """
        try:
            # 组装“上下文三明治”
            context_sandwich_parts = []
            if surrounding_paragraph:
                context_sandwich_parts.append(f"【所在段落】\n{surrounding_paragraph}")
            if context_before:
                context_sandwich_parts.append(f"【前文】\n{context_before}")
            if caption:
                context_sandwich_parts.append(f"【图注】\n{caption}")
            if context_after:
                context_sandwich_parts.append(f"【后文】\n{context_after}")
            context_sandwich = (
                "\n\n".join(context_sandwich_parts)
                if context_sandwich_parts
                else "(无)"
            )

            # 构建业务侧完整提示词（严格JSON输出）
            prompt = f"""
# 角色：
你是一名顶尖的AI媒体分析师与短视频内容策略师。你的任务是深入理解给定的【视觉素材】及其【文本上下文】，并输出一份可直接用于视频脚本创作的、结构化的JSON分析报告。

# 工作流程 (思维链 - 请严格遵循)：

1.  第一笔：视觉分析 (Analyze the Visual)。首先，仔细观察【视觉素材】。
    -   客观描述其内容、构图、风格和情感基调。
    -   如果素材中包含清晰的文字，使用OCR技术将其完整提取出来。

2.  第二步：上下文分析 (Analyze the Context)。接下来，阅读我提供的【文本上下文】。
    -   回答一个核心问题：作者在这里使用这张图的意图是什么？
    -   结合上下文，总结出这张图在本篇文章中的深层含义和扮演的角色。

3.  第三步：叙事功能建议 (Suggest the Function)。最后，基于前两步的综合分析，为这张素材在短视频脚本中可能扮演的角色提出建议。
    -   从以下预设的角色列表中，选择1-3个最匹配的角色：["opening_hook", "data_evidence", "b_roll_material", "product_showcase", "concept_explanation", "emotional_highlight", "conclusion_summary"]。

4.  第四步：整合输出 (Format the Output)。将以上所有分析结果，整合到一个严格的JSON对象中。

---
# 输入信息：

1.  【视觉素材】: (已附带图片)
2.  【文本上下文】(上下文三明治)：
{context_sandwich}
3.  图片分辨率: {resolution}
4.  material_id: {{material_id}}
5.  material_type: image

---
# 输出要求：
- 严格按照以下JSON格式输出，不得有任何额外说明：

{{
  "material_id": "{{material_id}}",
  "material_type": "image",
  "visual_description": "...",
  "contextual_meaning": "...",
  "extracted_text_ocr": "...",
  "suggested_narrative_functions": ["...", "..."],
  "keywords": ["...", "..."]
}}
"""

            # 使用同步OpenAI客户端分析图片（通用转发）
            # 如果传入的是URL或data URL，直接使用；否则尝试上传本地文件
            image_url = None
            try:
                if isinstance(image_path, str) and (
                    image_path.startswith("http://")
                    or image_path.startswith("https://")
                    or image_path.startswith("data:")
                ):
                    image_url = image_path
                else:
                    image_url = self._upload_to_cloud(image_path, "temp_analysis")
                    if not image_url:
                        with open(image_path, "rb") as image_file:
                            image_data = base64.b64encode(image_file.read()).decode(
                                "utf-8"
                            )
                            image_url = f"data:image/jpeg;base64,{image_data}"
            except Exception:
                # 最后退路：如果上面都失败，仍尝试将原字符串作为URL传入
                image_url = image_path

            # 将 material_id 注入提示词占位
            material_id_str = ""
            try:
                # 来自上层 analyze_material_with_context 传入的 analysis.media_item_id
                # 此处无法直接拿到 media_item.id，改为在JSON中由模型原样输出占位值
                # 为保持一致性，这里生成一次运行时ID作为占位
                material_id_str = (
                    getattr(self, "_runtime_material_id", None) or "runtime-material-id"
                )
            except Exception:
                material_id_str = "runtime-material-id"
            prompt_final = prompt.replace("{{material_id}}", material_id_str)

            # 通用图片分析调用（不含任何降级分支）
            ai_response = self.openai_client.analyze_image(
                image_url=image_url, prompt=prompt_final, model=self.analysis_model
            )

            if not ai_response:
                raise RuntimeError("OpenAI API调用失败")

            self.logger.info("AI图片上下文分析完成")

            # 解析AI响应（严格JSON）+ 兼容字段别名
            parsed = self._parse_json_strict(ai_response)
            # 字段别名以兼容历史调用链
            if "description" not in parsed and "visual_description" in parsed:
                parsed["description"] = parsed.get("visual_description")
            if (
                "contextual_description" not in parsed
                and "contextual_meaning" in parsed
            ):
                parsed["contextual_description"] = parsed.get("contextual_meaning")
            if "tags" not in parsed and "keywords" in parsed:
                parsed["tags"] = parsed.get("keywords")
            parsed["raw_response"] = ai_response
            return parsed

        except Exception as e:
            self.logger.error(f"AI图片分析失败: {str(e)}")
            raise

    def _analyze_video_with_ai_context(
        self,
        keyframes: List[Dict],
        resolution: str,
        duration: float,
        context_before: str = None,
        context_after: str = None,
        surrounding_paragraph: str = None,
        caption: str = None,
    ) -> Dict[str, Any]:
        """使用AI分析视频内容（含上下文）"""
        # 必须有关键帧
        if not keyframes:
            raise RuntimeError("关键帧为空，无法进行视频分析")
        first = keyframes[0]
        image_ref = first.get("frame_url") or first.get("frame_path")
        if not image_ref:
            raise RuntimeError("关键帧缺少可用引用")
        # 复用图片分析逻辑
        return self._analyze_image_with_ai_context(
            image_ref,
            resolution,
            context_before,
            context_after,
            surrounding_paragraph,
            caption,
        )

    # 已移除：旧的 _extract_keyframes（请使用 _extract_keyframes_ffmpeg）

    # 已移除：旧的 _parse_ai_response_with_context（统一直接 json.loads）

    def _upload_to_cloud(self, file_path: str, category: str) -> Optional[str]:
        """上传文件到云存储（与原版一致，使用StorageFactory）。"""
        try:
            storage = StorageFactory.get_storage()
            filename = Path(file_path).name
            cloud_key = f"{category}/{filename}"
            url = storage.upload_file(file_path, cloud_key)
            self.logger.info(f"文件已上传到云存储: {url}")
            return url
        except Exception as e:
            self.logger.error(f"云存储上传失败 - 文件: {file_path}, 错误: {str(e)}")
            return None
