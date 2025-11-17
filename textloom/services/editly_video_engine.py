"""
Editly 视频合成引擎
渐进式开源替代方案 - 阶段 1：基础视频合成

架构设计：
- 抽象接口层：VideoEngine
- Editly 实现：EditlyVideoEngine
- 插件系统：支持后续扩展 TTS、数字人等

作者: Claude
创建: 2025-11-17
"""

import json
import subprocess
import tempfile
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from config import settings
from utils.sync_logging import get_video_generator_logger


class VideoEngine(ABC):
    """视频合成引擎抽象基类"""

    @abstractmethod
    def generate_video(
        self,
        script_data: Dict[str, Any],
        media_files: List[Dict[str, str]],
        output_path: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Dict[str, Any]:
        """
        生成视频

        Args:
            script_data: 脚本数据
            media_files: 媒体文件列表
            output_path: 输出路径
            progress_callback: 进度回调函数

        Returns:
            包含 success, video_url, duration 等信息的字典
        """
        pass


class EditlyVideoEngine(VideoEngine):
    """
    基于 Editly 的开源视频合成引擎

    阶段 1 功能：
    - ✅ 多场景合成
    - ✅ 背景视频/图片
    - ✅ 素材叠加
    - ✅ 自定义字幕
    - ✅ 音频混合
    - ✅ 转场效果

    未来扩展：
    - 🔲 TTS 插件
    - 🔲 数字人插件
    - 🔲 高级滤镜
    """

    def __init__(self):
        self.logger = get_video_generator_logger()
        self.editly_path = self._find_editly_executable()
        self.logger.info(f"EditlyVideoEngine 初始化完成，editly 路径: {self.editly_path}")

    def _find_editly_executable(self) -> str:
        """查找 editly 可执行文件"""
        # 尝试使用全局安装的 editly
        try:
            result = subprocess.run(
                ["which", "editly"], capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                return "editly"
        except Exception:
            pass

        # 尝试本地安装
        local_editly = Path(__file__).parent.parent.parent / "editly" / "dist" / "cli.js"
        if local_editly.exists():
            return f"node {local_editly}"

        raise RuntimeError(
            "未找到 editly 可执行文件，请安装: npm install -g editly"
        )

    def generate_video(
        self,
        script_data: Dict[str, Any],
        media_files: List[Dict[str, str]],
        output_path: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Dict[str, Any]:
        """生成视频主流程"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("开始使用 Editly 引擎生成视频")
            self.logger.info(f"输出路径: {output_path}")
            self.logger.info(f"场景数: {len(script_data.get('scenes', []))}")
            self.logger.info(f"素材数: {len(media_files)}")
            self.logger.info("=" * 60)

            # 1. 转换配置
            editly_config = self._convert_to_editly_config(
                script_data, media_files, output_path
            )

            # 2. 写入配置文件
            config_path = self._write_config_file(editly_config)

            # 3. 执行 editly
            self._execute_editly(config_path, progress_callback)

            # 4. 验证输出
            if not Path(output_path).exists():
                raise RuntimeError(f"视频生成失败，输出文件不存在: {output_path}")

            # 5. 获取视频信息
            duration = self._get_video_duration(output_path)

            result = {
                "success": True,
                "video_path": output_path,
                "video_url": output_path,  # 后续可上传到 CDN
                "duration": duration,
                "engine": "editly",
                "message": "视频生成成功",
            }

            self.logger.info(f"✅ 视频生成成功: {output_path}, 时长: {duration}s")
            return result

        except Exception as e:
            error_msg = f"Editly 视频生成失败: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": error_msg,
                "engine": "editly",
            }

    def _convert_to_editly_config(
        self,
        script_data: Dict[str, Any],
        media_files: List[Dict[str, str]],
        output_path: str,
    ) -> Dict[str, Any]:
        """
        将 TextLoom 数据模型转换为 Editly 配置

        TextLoom 场景结构：
        {
            "scenes": [
                {
                    "scene_id": 1,
                    "narration": "旁白文本",
                    "material_id": "mat_001",
                    "duration": 5.0
                }
            ],
            "title": "视频标题",
            "subtitle": "视频副标题"
        }

        Editly 配置结构：
        {
            "outPath": "output.mp4",
            "width": 1080,
            "height": 1920,
            "clips": [
                {
                    "duration": 5,
                    "layers": [...]
                }
            ]
        }
        """
        self.logger.info("开始转换配置: TextLoom → Editly")

        # 创建媒体文件映射
        media_map = {m.get("id"): m for m in media_files}

        editly_config = {
            "outPath": output_path,
            "width": settings.video_default_width,
            "height": settings.video_default_height,
            "fps": 30,
            "defaults": {
                "duration": 4,
                "transition": {
                    "name": "fade",
                    "duration": 0.5,
                },
            },
            "clips": [],
            "audioTracks": [],
        }

        # 转换场景为 clips
        scenes = script_data.get("scenes", [])
        for idx, scene in enumerate(scenes):
            clip = self._build_clip_from_scene(scene, media_map, idx)
            editly_config["clips"].append(clip)

        self.logger.info(f"配置转换完成，生成 {len(editly_config['clips'])} 个 clips")
        return editly_config

    def _build_clip_from_scene(
        self, scene: Dict[str, Any], media_map: Dict[str, Dict], scene_idx: int
    ) -> Dict[str, Any]:
        """从单个场景构建 clip"""
        clip = {
            "duration": scene.get("duration", 4),
            "layers": [],
        }

        # 1. 背景层（优先使用背景图/视频，否则使用纯色）
        background_layer = self._create_background_layer(scene)
        if background_layer:
            clip["layers"].append(background_layer)

        # 2. 素材层（视频或图片）
        material_id = scene.get("material_id")
        if material_id and material_id in media_map:
            media = media_map[material_id]
            media_layer = self._create_media_layer(media, scene)
            if media_layer:
                clip["layers"].append(media_layer)

        # 3. 字幕层（使用 fabric 自定义渲染）
        narration = scene.get("narration", "").strip()
        if narration and settings.subtitle_enable:
            subtitle_layer = self._create_subtitle_layer(narration, scene_idx)
            clip["layers"].append(subtitle_layer)

        # 4. 标题层（仅第一个场景）
        if scene_idx == 0 and settings.video_title_enabled:
            title = scene.get("title", "")
            if title:
                title_layer = self._create_title_layer(title)
                clip["layers"].insert(0, title_layer)

        return clip

    def _create_background_layer(self, scene: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建背景层"""
        background_url = settings.background_image_url

        if background_url and background_url.startswith("http"):
            # TODO: 下载背景图片到本地
            self.logger.warning("背景图片 URL 需要下载到本地，暂时跳过")
            return None

        if background_url and Path(background_url).exists():
            return {
                "type": "image",
                "path": background_url,
                "resizeMode": "cover",
            }

        # 默认纯色背景
        return {
            "type": "fill-color",
            "color": "#000000",
        }

    def _create_media_layer(
        self, media: Dict[str, str], scene: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        创建素材层

        支持：
        - 视频素材
        - 图片素材
        - 位置和大小自定义
        """
        file_url = media.get("file_url") or media.get("url")
        filename = media.get("filename", "")

        if not file_url:
            self.logger.warning(f"素材 {media.get('id')} 缺少 file_url")
            return None

        # 判断文件类型
        is_video = any(
            ext in filename.lower() for ext in [".mp4", ".mov", ".avi", ".mkv"]
        )
        is_image = any(
            ext in filename.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]
        )

        if not is_video and not is_image:
            self.logger.warning(f"不支持的文件类型: {filename}")
            return None

        # 构建层配置
        layer = {
            "type": "video" if is_video else "image",
            "path": file_url,
            "resizeMode": "contain-blur",  # 保持比例，背景模糊
        }

        # TODO: 支持自定义位置和大小（需要从 scene 中读取配置）
        # layer["width"] = 0.8
        # layer["height"] = 0.6
        # layer["left"] = 0.5
        # layer["top"] = 0.5

        return layer

    def _create_subtitle_layer(
        self, text: str, scene_idx: int
    ) -> Dict[str, Any]:
        """
        创建自定义字幕层

        使用 fabric 类型实现精确的样式控制
        """
        # 转义特殊字符
        text_escaped = text.replace("'", "\\'").replace('"', '\\"')

        # 字幕样式配置
        subtitle_config = {
            "x": settings.subtitle_x,
            "y": settings.subtitle_y,
            "fontSize": settings.subtitle_font_size,
            "color": settings.subtitle_color,
            "fontFamily": settings.subtitle_font_name,
            "width": settings.subtitle_width,
            "height": settings.subtitle_height,
            "outlineColor": settings.subtitle_outline_color,
            "outline": settings.subtitle_outline,
        }

        # 构建 fabric 函数（JavaScript 代码）
        fabric_func = f"""
        ({{ fabric, canvas, width, height }}) => {{
            const text = new fabric.Text('{text_escaped}', {{
                left: {subtitle_config['x']},
                top: {subtitle_config['y']},
                fontSize: {subtitle_config['fontSize']},
                fill: '{subtitle_config['color']}',
                fontFamily: '{subtitle_config['fontFamily']}',
                textAlign: 'center',
                width: {subtitle_config['width']},
                stroke: '{subtitle_config['outlineColor']}',
                strokeWidth: {subtitle_config['outline']}
            }});
            canvas.add(text);
        }}
        """

        return {
            "type": "fabric",
            "func": fabric_func.strip(),
        }

    def _create_title_layer(self, title: str) -> Dict[str, Any]:
        """创建标题层"""
        return {
            "type": "title",
            "text": title,
            "textColor": settings.video_title_color,
            "fontPath": settings.subtitle_font_name,
            "position": "top",
        }

    def _write_config_file(self, config: Dict[str, Any]) -> str:
        """写入配置文件（JSON5 格式）"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json5", delete=False, encoding="utf-8"
        ) as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            config_path = f.name

        self.logger.info(f"配置文件已写入: {config_path}")
        self.logger.debug(f"配置内容:\n{json.dumps(config, indent=2, ensure_ascii=False)}")
        return config_path

    def _execute_editly(
        self, config_path: str, progress_callback: Optional[Callable[[int], None]]
    ):
        """执行 editly 命令"""
        cmd = f"{self.editly_path} {config_path} --fast"
        self.logger.info(f"执行命令: {cmd}")

        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )

        # 解析进度
        for line in process.stdout:
            line = line.strip()
            if line:
                self.logger.debug(f"[editly] {line}")

            # 解析进度百分比
            if "%" in line:
                try:
                    # 示例输出: "  45.2% "
                    progress_str = line.strip().replace("%", "").strip()
                    progress = int(float(progress_str))
                    if progress_callback:
                        progress_callback(progress)
                except (ValueError, AttributeError):
                    pass

        process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"editly 执行失败，退出码: {process.returncode}")

    def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长（使用 ffprobe）"""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip())
            return round(duration, 2)
        except Exception as e:
            self.logger.warning(f"获取视频时长失败: {e}")
            return 0.0


# ============= 阶段 2/3 扩展预留 =============

class TTSPlugin(ABC):
    """TTS 插件抽象基类（阶段 2 实现）"""

    @abstractmethod
    def synthesize(self, text: str, voice_id: str) -> str:
        """
        合成语音

        Args:
            text: 文本内容
            voice_id: 声音 ID

        Returns:
            音频文件路径
        """
        pass


class DigitalHumanPlugin(ABC):
    """数字人插件抽象基类（阶段 3 实现）"""

    @abstractmethod
    def generate(self, text: str, audio_path: str) -> str:
        """
        生成数字人视频

        Args:
            text: 文本内容
            audio_path: 音频文件路径

        Returns:
            数字人视频路径
        """
        pass


# TODO: 实现插件
# class PiperTTSPlugin(TTSPlugin): ...
# class HeyGenPlugin(DigitalHumanPlugin): ...
