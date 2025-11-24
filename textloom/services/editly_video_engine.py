"""
Editly 视频合成引擎
渐进式开源替代方案 - 阶段 1：基础视频合成

架构设计：
- 抽象接口层：VideoEngine
- Editly 实现：EditlyVideoEngine
- 插件系统：支持后续扩展 TTS、数字人等

职责分离：
- EditlyVideoEngine: 专注于调用 Editly 引擎
- EditlyConfigConverter: 专注于数据转换

作者: Claude
创建: 2025-11-17
更新: 2025-11-17 - 分离配置转换逻辑
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
from services.editly_config_converter import EditlyConfigConverter


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
        self.converter = EditlyConfigConverter()
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

            # 1. 转换配置（使用独立的转换器）
            editly_config = self.converter.convert(
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


    def _write_config_file(self, config: Dict[str, Any]) -> str:
        """写入配置文件（JSON5 格式）"""
        # 创建持久化配置目录
        config_dir = Path("workspace/editly_configs")
        config_dir.mkdir(parents=True, exist_ok=True)

        # 从输出路径提取任务信息作为文件名
        out_path = config.get("outPath", "")
        if out_path:
            # 例如: workspace/processed/task_id_video_1_output.mp4 -> task_id_video_1
            base_name = Path(out_path).stem.replace("_output", "")
        else:
            # 如果没有输出路径，使用时间戳
            from datetime import datetime
            base_name = f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 保存到持久化目录
        config_path = config_dir / f"{base_name}.json5"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        self.logger.info(f"✅ 配置文件已保存: {config_path}")
        self.logger.debug(f"配置内容:\n{json.dumps(config, indent=2, ensure_ascii=False)}")
        return str(config_path)

    def _execute_editly(
        self, config_path: str, progress_callback: Optional[Callable[[int], None]]
    ):
        """执行 editly 命令"""
        cmd = f"{self.editly_path} {config_path}"
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
