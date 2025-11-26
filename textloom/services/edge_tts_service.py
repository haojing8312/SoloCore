"""
Edge TTS 文本转语音服务

使用微软 Edge TTS 将文本转换为语音音频文件。
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import edge_tts
from config import settings


class EdgeTTSService:
    """Edge TTS 文本转语音服务"""

    def __init__(self):
        """初始化 TTS 服务"""
        self.logger = logging.getLogger(__name__)
        self.voice = settings.tts_voice
        self.rate = settings.tts_rate
        self.volume = settings.tts_volume
        self.audio_format = settings.tts_audio_format

    def synthesize_speech(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        volume: Optional[str] = None,
    ) -> bool:
        """
        将文本转换为语音并保存到文件

        Args:
            text: 要转换的文本内容
            output_path: 输出音频文件路径（绝对路径）
            voice: 语音名称（可选，默认使用配置值）
            rate: 语速调节（可选，默认使用配置值）
            volume: 音量调节（可选，默认使用配置值）

        Returns:
            bool: 成功返回 True，失败返回 False

        Example:
            >>> service = EdgeTTSService()
            >>> success = service.synthesize_speech(
            ...     "这是一段测试文本",
            ...     "/path/to/output.mp3"
            ... )
        """
        if not text or not text.strip():
            self.logger.warning("文本为空，跳过 TTS 生成")
            return False

        # 使用提供的参数或默认配置
        voice_to_use = voice or self.voice
        rate_to_use = rate or self.rate
        volume_to_use = volume or self.volume

        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)

            # 调用异步方法生成音频
            asyncio.run(
                self._generate_audio_async(
                    text=text,
                    output_path=output_path,
                    voice=voice_to_use,
                    rate=rate_to_use,
                    volume=volume_to_use,
                )
            )

            # 验证文件是否生成
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                self.logger.info(
                    f"✅ TTS 音频生成成功: {output_path} "
                    f"({os.path.getsize(output_path)} bytes)"
                )
                return True
            else:
                self.logger.error(f"❌ TTS 音频文件生成失败或为空: {output_path}")
                return False

        except Exception as e:
            self.logger.error(f"❌ TTS 生成过程中发生错误: {e}", exc_info=True)
            return False

    async def _generate_audio_async(
        self,
        text: str,
        output_path: str,
        voice: str,
        rate: str,
        volume: str,
    ) -> None:
        """
        异步生成音频文件

        Args:
            text: 文本内容
            output_path: 输出路径
            voice: 语音名称
            rate: 语速
            volume: 音量
        """
        self.logger.info(
            f"🎤 开始 TTS 合成: voice={voice}, rate={rate}, volume={volume}"
        )
        self.logger.debug(f"文本内容: {text[:100]}...")  # 只记录前100个字符

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
        )

        await communicate.save(output_path)

    def synthesize_speech_with_retry(
        self,
        text: str,
        output_path: str,
        max_retries: int = 3,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        volume: Optional[str] = None,
    ) -> bool:
        """
        带重试机制的 TTS 合成

        Args:
            text: 要转换的文本内容
            output_path: 输出音频文件路径
            max_retries: 最大重试次数
            voice: 语音名称（可选）
            rate: 语速调节（可选）
            volume: 音量调节（可选）

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        for attempt in range(1, max_retries + 1):
            self.logger.info(f"🔄 TTS 生成尝试 {attempt}/{max_retries}")

            success = self.synthesize_speech(
                text=text,
                output_path=output_path,
                voice=voice,
                rate=rate,
                volume=volume,
            )

            if success:
                return True

            if attempt < max_retries:
                self.logger.warning(f"⚠️ 尝试 {attempt} 失败，准备重试...")
                # 简单的重试延迟（可选）
                import time

                time.sleep(1)

        self.logger.error(f"❌ TTS 生成失败，已重试 {max_retries} 次")
        return False

    @staticmethod
    def get_audio_duration(audio_path: str) -> Optional[float]:
        """
        获取音频文件时长（秒）

        Args:
            audio_path: 音频文件路径

        Returns:
            Optional[float]: 音频时长（秒），失败返回 None
        """
        logger = logging.getLogger(__name__)
        logger.debug(f"🔍 开始获取音频时长: {audio_path}")

        try:
            import subprocess
            import os

            # 检查文件是否存在
            if not os.path.exists(audio_path):
                logger.error(f"❌ 音频文件不存在: {audio_path}")
                return None

            logger.debug(f"✓ 音频文件存在，大小: {os.path.getsize(audio_path)} bytes")

            # Windows 下 Celery worker 中的 subprocess 需要特殊处理
            # 使用 shell=True 可以避免 ACCESS_DENIED 错误
            import platform

            use_shell = platform.system() == "Windows"

            if use_shell:
                # Windows: 使用 shell=True 并构建命令字符串
                cmd = (
                    f'ffprobe -v error -show_entries format=duration '
                    f'-of default=noprint_wrappers=1:nokey=1 "{audio_path}"'
                )
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    shell=True,
                )
            else:
                # Linux/Mac: 使用列表形式（更安全）
                result = subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        audio_path,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

            logger.debug(f"✓ ffprobe 执行成功，输出: '{result.stdout.strip()}'")

            duration = float(result.stdout.strip())
            logger.info(f"✅ 成功获取音频时长: {duration:.3f}s - {audio_path}")
            return duration

        except subprocess.CalledProcessError as e:
            logger.error(
                f"❌ ffprobe 执行失败: {audio_path}\n"
                f"   返回码: {e.returncode}\n"
                f"   stdout: {e.stdout}\n"
                f"   stderr: {e.stderr}"
            )
            return None
        except ValueError as e:
            logger.error(
                f"❌ 无法解析音频时长: {audio_path}\n"
                f"   错误: {e}\n"
                f"   输出: {result.stdout if 'result' in locals() else 'N/A'}"
            )
            return None
        except FileNotFoundError as e:
            logger.error(
                f"❌ ffprobe 命令不存在: {e}\n"
                f"   请确保 FFmpeg 已安装并在 PATH 中"
            )
            return None
        except Exception as e:
            logger.error(
                f"❌ 获取音频时长时发生未预期的错误: {audio_path}\n"
                f"   错误类型: {type(e).__name__}\n"
                f"   错误信息: {e}",
                exc_info=True
            )
            return None

    @staticmethod
    def list_available_voices(language: str = "zh-CN") -> list[str]:
        """
        列出可用的语音（同步版本）

        Args:
            language: 语言代码（如 zh-CN、en-US）

        Returns:
            list[str]: 可用的语音名称列表
        """
        try:
            voices = asyncio.run(edge_tts.list_voices())
            filtered_voices = [
                v["ShortName"]
                for v in voices
                if v["Locale"].startswith(language)
            ]
            return filtered_voices
        except Exception as e:
            logging.getLogger(__name__).error(f"❌ 无法列出可用语音: {e}")
            return []


# 全局实例（单例模式）
_tts_service_instance: Optional[EdgeTTSService] = None


def get_tts_service() -> EdgeTTSService:
    """
    获取 TTS 服务实例（单例）

    Returns:
        EdgeTTSService: TTS 服务实例
    """
    global _tts_service_instance
    if _tts_service_instance is None:
        _tts_service_instance = EdgeTTSService()
    return _tts_service_instance
