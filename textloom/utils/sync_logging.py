"""
Celery任务专用日志配置模块
提供统一的日志格式和处理器配置
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings

# 确保日志目录存在
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_celery_logger(
    name: str = "celery_tasks", level: str = "INFO", log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置Celery任务专用日志器

    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径（可选）

    Returns:
        配置好的日志器
    """

    # 创建日志器
    logger = logging.getLogger(name)
    # 为确保文件日志包含DEBUG信息，将logger级别提升到DEBUG
    # 控制台输出级别仍由下方handler控制
    logger.setLevel(logging.DEBUG)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 统一的日志格式
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper()))
    logger.addHandler(console_handler)

    # 文件处理器
    if not log_file:
        log_file = LOG_DIR / f"celery_{name}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # 错误日志文件处理器
    error_log_file = LOG_DIR / f"celery_{name}_error.log"
    error_handler = logging.FileHandler(error_log_file, encoding="utf-8")
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)

    logger.info(f"Celery日志器 '{name}' 初始化完成")
    logger.info(f"日志文件: {log_file}")
    logger.info(f"错误日志文件: {error_log_file}")

    return logger


def setup_component_logger(component_name: str) -> logging.Logger:
    """
    为特定组件设置日志器

    Args:
        component_name: 组件名称

    Returns:
        配置好的日志器
    """
    return setup_celery_logger(
        name=f"sync_{component_name}",
        level=settings.log_level,
        log_file=LOG_DIR / f"sync_{component_name}.log",
    )


def log_task_start(logger: logging.Logger, task_name: str, task_id: str, **kwargs):
    """记录任务开始日志"""
    logger.info(f"🚀 任务开始: {task_name} | 任务ID: {task_id} | 参数: {kwargs}")


def log_task_progress(
    logger: logging.Logger, task_id: str, progress: int, message: str
):
    """记录任务进度日志"""
    logger.info(f"📊 任务进度: {task_id} | {progress}% | {message}")


def log_task_success(
    logger: logging.Logger, task_name: str, task_id: str, result: dict
):
    """记录任务成功日志"""
    logger.info(f"✅ 任务成功: {task_name} | 任务ID: {task_id} | 结果: {result}")


def log_task_error(
    logger: logging.Logger, task_name: str, task_id: str, error: Exception
):
    """记录任务错误日志"""
    logger.error(
        f"❌ 任务失败: {task_name} | 任务ID: {task_id} | 错误: {error}", exc_info=True
    )


def log_api_call(logger: logging.Logger, service: str, method: str, **kwargs):
    """记录API调用日志"""
    logger.debug(f"🔗 API调用: {service}.{method} | 参数: {kwargs}")


def log_api_response(
    logger: logging.Logger,
    service: str,
    method: str,
    success: bool,
    response_info: dict,
):
    """记录API响应日志"""
    status = "成功" if success else "失败"
    logger.debug(f"📨 API响应: {service}.{method} | {status} | 信息: {response_info}")


def log_database_operation(
    logger: logging.Logger,
    operation: str,
    table: str,
    success: bool,
    details: dict = None,
):
    """记录数据库操作日志"""
    status = "成功" if success else "失败"
    details_str = f" | 详情: {details}" if details else ""
    logger.debug(f"🗄️ 数据库操作: {operation} {table} | {status}{details_str}")


def log_file_operation(
    logger: logging.Logger,
    operation: str,
    file_path: str,
    success: bool,
    size: int = None,
):
    """记录文件操作日志"""
    status = "成功" if success else "失败"
    size_str = f" | 大小: {size} bytes" if size else ""
    logger.debug(f"📁 文件操作: {operation} {file_path} | {status}{size_str}")


# 通用日志器获取函数
def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    获取指定名称的日志器

    Args:
        name: 日志器名称
        level: 日志级别

    Returns:
        配置好的日志器
    """
    return setup_celery_logger(name=name, level=level)


# 预定义的组件日志器
def get_material_processor_logger() -> logging.Logger:
    """获取素材处理器日志器"""
    return setup_component_logger("material_processor")


def get_material_analyzer_logger() -> logging.Logger:
    """获取素材分析器日志器"""
    return setup_component_logger("material_analyzer")


def get_script_generator_logger() -> logging.Logger:
    """获取脚本生成器日志器"""
    return setup_component_logger("script_generator")


def get_video_generator_logger() -> logging.Logger:
    """获取视频生成器日志器"""
    return setup_component_logger("video_generator")


def get_task_processor_logger() -> logging.Logger:
    """获取任务处理器日志器"""
    return setup_component_logger("task_processor")


# 性能监控装饰器
def log_performance(logger: logging.Logger, operation_name: str):
    """性能监控装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(
                    f"⏱️ 性能监控: {operation_name} | 耗时: {duration:.2f}秒 | 成功"
                )
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(
                    f"⏱️ 性能监控: {operation_name} | 耗时: {duration:.2f}秒 | 失败: {e}"
                )
                raise

        return wrapper

    return decorator
