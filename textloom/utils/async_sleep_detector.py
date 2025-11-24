"""
异步上下文阻塞Sleep检测器
========================

在运行时检测异步上下文中的阻塞sleep调用，提供实时告警。
用于生产环境中监控潜在的性能问题。
"""

import asyncio
import functools
import inspect
import logging
import threading
import time
import warnings
from contextlib import contextmanager
from typing import Any, Callable, Optional

logger = logging.getLogger("async_sleep_detector")


class AsyncSleepDetector:
    """异步Sleep检测器"""

    def __init__(self, warning_threshold: float = 0.01):
        """
        Args:
            warning_threshold: 告警阈值（秒），超过此时间的sleep调用会被告警
        """
        self.warning_threshold = warning_threshold
        self.enabled = True
        self.original_sleep = time.sleep
        self._patched = False

    def enable(self):
        """启用检测器"""
        if not self._patched:
            self._patch_sleep()
            self._patched = True
        self.enabled = True
        logger.info("异步Sleep检测器已启用")

    def disable(self):
        """禁用检测器"""
        self.enabled = False
        logger.info("异步Sleep检测器已禁用")

    def _patch_sleep(self):
        """修补time.sleep函数"""

        def patched_sleep(duration: float):
            if self.enabled:
                self._check_async_context(duration)
            return self.original_sleep(duration)

        time.sleep = patched_sleep

    def _check_async_context(self, duration: float):
        """检查当前是否在异步上下文中"""
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_running_loop()
            if loop and loop.is_running():
                # 在事件循环中调用阻塞sleep
                frame = inspect.currentframe()
                call_info = self._get_call_info(frame)

                if duration >= self.warning_threshold:
                    warning_msg = (
                        f"⚠️  检测到异步上下文中的阻塞sleep调用！"
                        f"\n   位置: {call_info['file']}:{call_info['line']}"
                        f"\n   函数: {call_info['function']}"
                        f"\n   持续时间: {duration}秒"
                        f"\n   建议: 使用 await asyncio.sleep({duration}) 替代"
                    )
                    warnings.warn(warning_msg, UserWarning, stacklevel=5)
                    logger.warning(warning_msg)

        except RuntimeError:
            # 没有运行中的事件循环，这是正常的同步调用
            pass
        except Exception as e:
            # 检测过程中出错，不影响正常功能
            logger.debug(f"Sleep检测器错误: {e}")

    def _get_call_info(self, frame):
        """获取调用信息"""
        try:
            # 向上查找调用栈，跳过检测器内部的帧
            current_frame = frame
            for _ in range(10):  # 最多向上查找10层
                current_frame = current_frame.f_back
                if current_frame is None:
                    break

                code = current_frame.f_code
                filename = code.co_filename

                # 跳过检测器内部文件
                if "async_sleep_detector.py" in filename:
                    continue

                return {
                    "file": filename.split("/")[-1],
                    "line": current_frame.f_lineno,
                    "function": code.co_name,
                }

        except Exception:
            pass

        return {"file": "unknown", "line": 0, "function": "unknown"}

    def restore(self):
        """恢复原始sleep函数"""
        time.sleep = self.original_sleep
        self._patched = False
        logger.info("已恢复原始sleep函数")


# 全局检测器实例
_global_detector: Optional[AsyncSleepDetector] = None


def enable_async_sleep_detection(warning_threshold: float = 0.01):
    """启用全局异步Sleep检测

    Args:
        warning_threshold: 告警阈值（秒）
    """
    global _global_detector

    if _global_detector is None:
        _global_detector = AsyncSleepDetector(warning_threshold)

    _global_detector.enable()


def disable_async_sleep_detection():
    """禁用全局异步Sleep检测"""
    global _global_detector

    if _global_detector:
        _global_detector.disable()


def restore_original_sleep():
    """恢复原始sleep函数"""
    global _global_detector

    if _global_detector:
        _global_detector.restore()
        _global_detector = None


@contextmanager
def async_sleep_detection(warning_threshold: float = 0.01):
    """上下文管理器形式的Sleep检测

    with async_sleep_detection():
        # 在此块中会检测阻塞sleep调用
        some_async_function()
    """
    enable_async_sleep_detection(warning_threshold)
    try:
        yield
    finally:
        disable_async_sleep_detection()


def monitor_async_performance(func: Callable = None, *, threshold: float = 0.01):
    """装饰器：监控异步函数中的阻塞调用

    @monitor_async_performance
    async def my_async_function():
        time.sleep(0.1)  # 这会被检测到并告警
    """

    def decorator(f):
        if asyncio.iscoroutinefunction(f):

            @functools.wraps(f)
            async def wrapper(*args, **kwargs):
                with async_sleep_detection(threshold):
                    return await f(*args, **kwargs)

            return wrapper
        else:

            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                with async_sleep_detection(threshold):
                    return f(*args, **kwargs)

            return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


# 为开发模式提供的便捷函数
def setup_development_monitoring():
    """设置开发模式监控"""
    import os

    # 只在开发模式下启用
    if os.environ.get("TEXTLOOM_ENV", "development") == "development":
        enable_async_sleep_detection(warning_threshold=0.005)  # 5ms阈值
        logger.info("开发模式：异步Sleep检测已启用")


if __name__ == "__main__":
    # 测试代码
    async def test_async_function():
        print("测试异步函数中的sleep调用...")
        time.sleep(0.1)  # 这应该被检测到
        await asyncio.sleep(0.1)  # 这是正确的异步调用

    def test_sync_function():
        print("测试同步函数中的sleep调用...")
        time.sleep(0.1)  # 这不应该被告警

    async def main():
        # 启用检测
        enable_async_sleep_detection(warning_threshold=0.05)

        print("1. 测试异步上下文...")
        await test_async_function()

        print("\n2. 测试同步上下文...")
        test_sync_function()

        # 恢复
        restore_original_sleep()

    # 运行测试
    asyncio.run(main())
