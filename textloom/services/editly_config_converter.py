"""
Editly 配置转换器 - TextLoom 数据模型转换为 Editly 配置

职责：
- 将 TextLoom 场景数据模型转换为 Editly JSON5 配置
- 处理场景 → Clip 映射
- 处理组件 → Layer 映射
- 生成 Fabric.js 字幕渲染代码
- 处理音频轨道和转场效果

设计原则：
- 单一职责：只负责数据转换，不涉及视频生成
- 可测试性：纯函数式转换逻辑，易于单元测试
- 可扩展性：支持自定义转换规则和插件

作者: Claude
创建: 2025-11-17
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings
from utils.sync_logging import get_video_generator_logger


class EditlyConfigConverter:
    """
    TextLoom → Editly 配置转换器

    转换流程：
    1. Scene → Clip
    2. Component → Layer
    3. SubtitlesStyle → Fabric.js
    4. AudioDriver → audioTracks
    5. Transition → transition
    """

    def __init__(self):
        """初始化转换器"""
        self.logger = get_video_generator_logger()
        self.logger.info("EditlyConfigConverter 初始化完成")

    def convert(
        self,
        script_data: Dict[str, Any],
        media_files: List[Dict[str, str]],
        output_path: str,
    ) -> Dict[str, Any]:
        """
        主转换入口

        Args:
            script_data: TextLoom 脚本数据
            media_files: 媒体文件列表
            output_path: 输出路径

        Returns:
            Editly 配置字典
        """
        self.logger.info("=" * 60)
        self.logger.info("开始数据转换: TextLoom → Editly")
        self.logger.info(f"场景数: {len(script_data.get('scenes', []))}")
        self.logger.info(f"素材数: {len(media_files)}")

        # 调试：输出第一个素材的详细信息
        if media_files:
            first_media = media_files[0]
            self.logger.info(f"🔍 第一个素材详情: id={first_media.get('id')}, local_path={first_media.get('local_path')}, file_url={first_media.get('file_url')}")

        # 创建媒体文件映射
        media_map = {m.get("id"): m for m in media_files}

        # 构建基础配置
        editly_config = self._build_base_config(output_path)

        # 转换场景为 clips
        scenes = script_data.get("scenes", [])
        for idx, scene in enumerate(scenes):
            clip = self._convert_scene_to_clip(scene, media_map, idx)
            editly_config["clips"].append(clip)

        # 添加场景级音频轨道（TTS 生成的旁白）
        scene_audio_tracks = self._extract_scene_audio_tracks(scenes)
        if scene_audio_tracks:
            editly_config["audioTracks"].extend(scene_audio_tracks)

        # 添加全局音频轨道（背景音乐等）
        global_audio_tracks = self._extract_global_audio_tracks(script_data)
        if global_audio_tracks:
            editly_config["audioTracks"].extend(global_audio_tracks)

        self.logger.info(f"✓ 配置转换完成: {len(editly_config['clips'])} clips")
        self.logger.info("=" * 60)

        return editly_config

    def _build_base_config(self, output_path: str) -> Dict[str, Any]:
        """
        构建 Editly 基础配置

        Returns:
            基础配置字典
        """
        return {
            "outPath": output_path,
            "width": getattr(settings, "video_default_width", 1080),
            "height": getattr(settings, "video_default_height", 1920),
            "fps": getattr(settings, "video_default_fps", 30),
            "allowRemoteRequests": True,  # 允许加载远程URL资源
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

    def _convert_scene_to_clip(
        self,
        scene: Dict[str, Any],
        media_map: Dict[str, Dict],
        scene_idx: int,
    ) -> Dict[str, Any]:
        """
        场景 → Clip 转换

        TextLoom Scene 结构:
        {
            "scene_id": 1,
            "duration": 5.0,
            "narration": "旁白文本",
            "material_id": "mat_001",
            "components": [
                {
                    "category": 1,  # 1=素材, 2=数字人, 3=字幕
                    "businessId": "comp_001",
                    "position": {...},
                    "size": {...}
                }
            ],
            "audioDriver": {
                "audioUrl": "https://...",
                "volume": 1.0
            },
            "textDriver": {
                "textJson": "字幕文本"
            }
        }

        Editly Clip 结构:
        {
            "duration": 5,
            "layers": [...],
            "transition": {...}
        }
        """
        self.logger.debug(f"转换场景 {scene_idx + 1}: scene_id={scene.get('scene_id')}")

        # 优先使用音频实际时长作为场景时长，避免音频重叠
        audio_duration = scene.get("audio_duration")
        if audio_duration is not None:
            scene_duration = audio_duration
            self.logger.debug(f"使用音频时长作为场景时长: {scene_duration:.2f}s")
        else:
            scene_duration = scene.get("duration", 4)
            self.logger.debug(f"使用默认场景时长: {scene_duration:.2f}s")

        clip = {
            "duration": scene_duration,
            "layers": [],
        }

        # 1. 添加背景层
        background_layer = self._create_background_layer(scene)
        if background_layer:
            clip["layers"].append(background_layer)

        # 2. 添加素材层（视频/图片）
        material_id = scene.get("material_id")
        if material_id and material_id in media_map:
            media = media_map[material_id]
            media_layer = self._create_media_layer(media, scene)
            if media_layer:
                clip["layers"].append(media_layer)

        # 3. 处理组件层（components）
        components = scene.get("components", [])
        for comp in components:
            comp_layer = self._convert_component_to_layer(comp, media_map)
            if comp_layer:
                clip["layers"].append(comp_layer)

        # 4. 添加字幕层（从 narration 或 textDriver）
        subtitle_text = self._extract_subtitle_text(scene)
        if subtitle_text and getattr(settings, "subtitle_enable", True):
            subtitle_layer = self._create_subtitle_layer(subtitle_text, scene_idx)
            clip["layers"].append(subtitle_layer)

        # 5. 添加标题层（仅第一个场景）
        if scene_idx == 0 and getattr(settings, "video_title_enabled", False):
            title = scene.get("title", "")
            if title:
                title_layer = self._create_title_layer(title)
                clip["layers"].insert(0, title_layer)

        # 6. 添加转场效果
        transition = self._extract_transition(scene)
        if transition:
            clip["transition"] = transition

        self.logger.debug(f"  ✓ 生成 {len(clip['layers'])} 层")
        return clip

    def _create_background_layer(
        self, scene: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        创建背景层

        优先级：
        1. 场景指定的背景
        2. 全局配置的背景
        3. 默认纯色背景
        """
        # 场景背景（优先）
        scene_bg = scene.get("background_url")
        if scene_bg:
            return self._build_image_layer(scene_bg, "cover")

        # 全局背景
        global_bg = getattr(settings, "background_image_url", None)
        if global_bg:
            if global_bg.startswith("http"):
                self.logger.warning("背景图片 URL 需要下载到本地，暂时跳过")
                return None
            if Path(global_bg).exists():
                return self._build_image_layer(global_bg, "cover")

        # 默认纯色
        return {
            "type": "fill-color",
            "color": getattr(settings, "background_color", "#000000"),
        }

    def _create_media_layer(
        self, media: Dict[str, str], scene: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        创建素材层（视频/图片）

        Args:
            media: 媒体文件信息 {"id", "file_url", "local_path", "filename"}
            scene: 场景配置（可包含位置、大小信息）

        Returns:
            Layer 配置或 None
        """
        # 优先使用本地路径，避免远程URL导致的视频编码问题
        file_path = media.get("local_path") or media.get("file_url") or media.get("url")
        filename = media.get("filename", "")

        if not file_path:
            self.logger.warning(f"素材 {media.get('id')} 缺少 local_path 或 file_url")
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
            "path": file_path,
            "resizeMode": getattr(settings, "video_resize_mode", "contain-blur"),
        }

        # 自定义位置和大小（从 scene 配置中读取）
        position = scene.get("position", {})
        if position:
            layer["left"] = position.get("x", 0.5)
            layer["top"] = position.get("y", 0.5)

        size = scene.get("size", {})
        if size:
            layer["width"] = size.get("width", 1.0)
            layer["height"] = size.get("height", 1.0)

        return layer

    def _convert_component_to_layer(
        self, component: Dict[str, Any], media_map: Dict[str, Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        组件 → Layer 转换

        Component 类型:
        - category = 1: 素材（图片/视频）
        - category = 2: 数字人（需要特殊处理）
        - category = 3: 字幕/文本

        Args:
            component: TextLoom 组件配置
            media_map: 媒体文件映射

        Returns:
            Layer 配置或 None
        """
        category = component.get("category")
        business_id = component.get("businessId")

        if category == 1:  # 素材
            if business_id in media_map:
                media = media_map[business_id]
                return self._build_media_layer_from_component(media, component)

        elif category == 2:  # 数字人
            self.logger.warning(
                f"数字人组件 {business_id} 不支持（需要阶段3集成 SadTalker）"
            )
            return None

        elif category == 3:  # 字幕
            text = component.get("text", "")
            if text:
                return self._build_subtitle_layer_from_component(text, component)

        return None

    def _build_media_layer_from_component(
        self, media: Dict[str, str], component: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """从组件配置构建素材层"""
        # 优先使用本地路径，避免远程URL导致的视频编码问题
        file_path = media.get("local_path") or media.get("file_url") or media.get("url")
        filename = media.get("filename", "")

        if not file_path:
            return None

        is_video = any(
            ext in filename.lower() for ext in [".mp4", ".mov", ".avi", ".mkv"]
        )

        layer = {
            "type": "video" if is_video else "image",
            "path": file_path,
            "resizeMode": "contain",
        }

        # 应用组件的位置和大小
        position = component.get("position", {})
        if position:
            layer["left"] = position.get("x", 0.5)
            layer["top"] = position.get("y", 0.5)

        size = component.get("size", {})
        if size:
            layer["width"] = size.get("width", 1.0)
            layer["height"] = size.get("height", 1.0)

        return layer

    def _build_subtitle_layer_from_component(
        self, text: str, component: Dict[str, Any]
    ) -> Dict[str, Any]:
        """从组件配置构建字幕层"""
        # 使用组件的样式配置（如果有）
        style = component.get("style", {})

        return {
            "type": "subtitle",
            "text": text,
            "textColor": style.get("color", getattr(settings, "subtitle_color", "#ffffff")),
            "backgroundColor": style.get("bgColor", "rgba(0, 0, 0, 0.7)"),
        }

    def _create_subtitle_layer(
        self, text: str, scene_idx: int
    ) -> Dict[str, Any]:
        """
        创建自定义字幕层

        使用 Fabric.js 实现精确的样式控制

        Args:
            text: 字幕文本
            scene_idx: 场景索引

        Returns:
            Fabric.js layer 配置
        """
        # 转义特殊字符
        text_escaped = text.replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n")

        # 字幕样式配置
        subtitle_x = getattr(settings, "subtitle_x", 540)
        subtitle_y = getattr(settings, "subtitle_y", 1600)
        font_size = getattr(settings, "subtitle_font_size", 60)
        color = getattr(settings, "subtitle_color", "#ffffff")
        font_family = getattr(settings, "subtitle_font_name", "Arial")
        width = getattr(settings, "subtitle_width", 1000)
        outline_color = getattr(settings, "subtitle_outline_color", "#000000")
        outline = getattr(settings, "subtitle_outline", 2)

        # 构建 Fabric.js 函数（JavaScript 代码）
        fabric_func = f"""
        ({{ fabric, canvas, width, height }}) => {{
            const text = new fabric.Text('{text_escaped}', {{
                left: {subtitle_x},
                top: {subtitle_y},
                fontSize: {font_size},
                fill: '{color}',
                fontFamily: '{font_family}',
                textAlign: 'center',
                width: {width},
                stroke: '{outline_color}',
                strokeWidth: {outline}
            }});
            canvas.add(text);
        }}
        """

        return {
            "type": "fabric",
            "func": fabric_func.strip(),
        }

    def _create_title_layer(self, title: str) -> Dict[str, Any]:
        """
        创建标题层

        Args:
            title: 标题文本

        Returns:
            Title layer 配置
        """
        return {
            "type": "title",
            "text": title,
            "textColor": getattr(settings, "video_title_color", "#ffffff"),
            "fontPath": getattr(settings, "subtitle_font_name", "Arial"),
            "position": "top",
        }

    def _build_image_layer(
        self, path: str, resize_mode: str = "contain"
    ) -> Dict[str, Any]:
        """
        构建图片层

        Args:
            path: 图片路径
            resize_mode: 缩放模式

        Returns:
            Image layer 配置
        """
        return {
            "type": "image",
            "path": path,
            "resizeMode": resize_mode,
        }

    def _extract_subtitle_text(self, scene: Dict[str, Any]) -> str:
        """
        提取字幕文本

        优先级：
        1. textDriver.textJson
        2. narration
        """
        # 从 textDriver 提取
        text_driver = scene.get("textDriver", {})
        text_json = text_driver.get("textJson", "").strip()
        if text_json:
            return text_json

        # 从 narration 提取
        narration = scene.get("narration", "").strip()
        return narration

    def _extract_transition(self, scene: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        提取转场效果

        Args:
            scene: 场景配置

        Returns:
            Transition 配置或 None
        """
        transition = scene.get("transition")
        if not transition:
            return None

        return {
            "name": transition.get("name", "fade"),
            "duration": transition.get("duration", 0.5),
        }

    def _extract_scene_audio_tracks(
        self, scenes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        提取场景级音频轨道（TTS 生成的旁白）

        Args:
            scenes: 场景列表

        Returns:
            音频轨道列表（按场景顺序）
        """
        audio_tracks = []
        cumulative_time = 0.0  # 累计时间（秒）

        for scene in scenes:
            audio_path = scene.get("audio_path")
            if audio_path:
                # 优先使用音频实际时长，如果不存在则使用场景时长
                audio_duration = scene.get("audio_duration")
                if audio_duration is None:
                    # 兼容旧版本：如果没有audio_duration，使用scene的duration
                    audio_duration = scene.get("duration", 4.0)
                    self.logger.warning(
                        f"场景缺少 audio_duration 字段，使用 duration: {audio_duration:.2f}s"
                    )

                # 添加音频轨道
                audio_tracks.append({
                    "path": audio_path,
                    "start": cumulative_time,  # 音频开始时间
                    "mixVolume": 1.0,  # 旁白全音量
                })

                self.logger.debug(
                    f"添加场景音频: {audio_path}, "
                    f"开始时间: {cumulative_time:.2f}s, "
                    f"音频时长: {audio_duration:.2f}s"
                )

                # 累加音频时长（不是场景时长）
                cumulative_time += audio_duration
            else:
                # 如果没有音频，使用场景时长
                scene_duration = scene.get("duration", 4.0)
                cumulative_time += scene_duration

        self.logger.info(
            f"✓ 提取场景音频轨道: {len(audio_tracks)} 个, "
            f"总时长: {cumulative_time:.2f}s"
        )

        return audio_tracks

    def _extract_global_audio_tracks(
        self, script_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        提取全局音频轨道（背景音乐等）

        Args:
            script_data: 脚本数据

        Returns:
            音频轨道列表
        """
        audio_tracks = []

        # 全局背景音乐
        bg_music = script_data.get("background_music")
        if bg_music:
            audio_tracks.append({
                "path": bg_music,
                "mixVolume": 0.3,  # 背景音乐音量（低于旁白）
            })
            self.logger.info(f"✓ 添加背景音乐: {bg_music}")

        return audio_tracks

    def get_supported_transitions(self) -> List[str]:
        """
        获取支持的转场效果列表

        Returns:
            转场效果名称列表
        """
        return [
            "fade",
            "crosswarp",
            "directionalwipe",
            "circleopen",
            "crosszoom",
            "dreamy",
            "fadecolor",
            "randomsquares",
            "simplezoom",
            "swap",
            # ... 更多转场效果
        ]

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证 Editly 配置有效性

        Args:
            config: Editly 配置

        Returns:
            是否有效
        """
        required_fields = ["outPath", "width", "height", "fps", "clips"]

        for field in required_fields:
            if field not in config:
                self.logger.error(f"配置缺少必需字段: {field}")
                return False

        if not config["clips"]:
            self.logger.error("配置至少需要一个 clip")
            return False

        return True
