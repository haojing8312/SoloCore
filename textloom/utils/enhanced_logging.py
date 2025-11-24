"""
增强的统一日志系统
提供项目级别的日志配置、格式化、轮转和结构化日志功能
用于替换项目中的所有print()语句
"""

import json
import logging
import logging.handlers
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional, Union

from config import settings

# 确保日志目录存在
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 工作空间日志目录
WORKSPACE_LOG_DIR = Path("workspace/logs")
WORKSPACE_LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class LogConfig:
    """日志配置类"""

    name: str
    level: str = "INFO"
    file_path: Optional[str] = None
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    use_json_format: bool = False
    include_traceback: bool = True


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器，支持JSON输出"""

    def __init__(self, use_json: bool = False):
        self.use_json = use_json
        if use_json:
            super().__init__()
        else:
            super().__init__(
                "[%(asctime)s] %(levelname)8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

    def format(self, record):
        if not self.use_json:
            return super().format(record)

        # JSON格式日志
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "process_id": os.getpid(),
            "thread_id": record.thread,
        }

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加自定义字段
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data, ensure_ascii=False)


class EnhancedLogger:
    """增强的日志器类，提供统一的日志接口"""

    def __init__(self, config: LogConfig):
        self.config = config
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger(self.config.name)

        # 避免重复添加处理器
        if logger.handlers:
            return logger

        logger.setLevel(logging.DEBUG)  # 设置最低级别，由handler控制实际输出

        # 创建格式化器
        formatter = StructuredFormatter(use_json=self.config.use_json_format)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, self.config.level.upper()))
        logger.addHandler(console_handler)

        # 文件处理器（带轮转）
        if self.config.file_path:
            file_handler = logging.handlers.RotatingFileHandler(
                self.config.file_path,
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)

        # 错误日志文件处理器
        if self.config.file_path:
            error_log_path = Path(self.config.file_path).with_suffix(".error.log")
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_path,
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count,
                encoding="utf-8",
            )
            error_handler.setFormatter(formatter)
            error_handler.setLevel(logging.ERROR)
            logger.addHandler(error_handler)

        return logger

    def debug(self, message: str, extra: Dict[str, Any] = None, **kwargs):
        """调试日志"""
        self._log(logging.DEBUG, message, extra, **kwargs)

    def info(self, message: str, extra: Dict[str, Any] = None, **kwargs):
        """信息日志"""
        self._log(logging.INFO, message, extra, **kwargs)

    def warning(self, message: str, extra: Dict[str, Any] = None, **kwargs):
        """警告日志"""
        self._log(logging.WARNING, message, extra, **kwargs)

    def error(
        self,
        message: str,
        extra: Dict[str, Any] = None,
        exc_info: bool = None,
        **kwargs,
    ):
        """错误日志"""
        if exc_info is None:
            exc_info = self.config.include_traceback
        self._log(logging.ERROR, message, extra, exc_info=exc_info, **kwargs)

    def critical(
        self,
        message: str,
        extra: Dict[str, Any] = None,
        exc_info: bool = None,
        **kwargs,
    ):
        """严重错误日志"""
        if exc_info is None:
            exc_info = self.config.include_traceback
        self._log(logging.CRITICAL, message, extra, exc_info=exc_info, **kwargs)

    def _log(self, level: int, message: str, extra: Dict[str, Any] = None, **kwargs):
        """内部日志记录方法"""
        if extra:
            # 将额外数据附加到记录中
            record_extra = {"extra_data": extra}
            self.logger.log(level, message, extra=record_extra, **kwargs)
        else:
            self.logger.log(level, message, **kwargs)


# 日志器缓存
_logger_cache: Dict[str, EnhancedLogger] = {}


def get_enhanced_logger(
    name: str,
    level: str = None,
    file_path: str = None,
    use_json: bool = False,
    **kwargs,
) -> EnhancedLogger:
    """
    获取增强的日志器实例

    Args:
        name: 日志器名称
        level: 日志级别
        file_path: 日志文件路径
        use_json: 是否使用JSON格式
        **kwargs: 其他配置参数

    Returns:
        增强的日志器实例
    """
    if name in _logger_cache:
        return _logger_cache[name]

    config = LogConfig(
        name=name,
        level=level or settings.log_level,
        file_path=file_path,
        use_json_format=use_json,
        **kwargs,
    )

    logger = EnhancedLogger(config)
    _logger_cache[name] = logger

    return logger


# 预定义的组件日志器
def get_api_logger() -> EnhancedLogger:
    """获取API路由日志器"""
    return get_enhanced_logger("textloom.api", file_path=str(LOG_DIR / "api.log"))


def get_database_logger() -> EnhancedLogger:
    """获取数据库操作日志器"""
    return get_enhanced_logger(
        "textloom.database", file_path=str(LOG_DIR / "database.log")
    )


def get_task_logger() -> EnhancedLogger:
    """获取任务处理日志器"""
    return get_enhanced_logger("textloom.tasks", file_path=str(LOG_DIR / "tasks.log"))


def get_service_logger() -> EnhancedLogger:
    """获取服务层日志器"""
    return get_enhanced_logger(
        "textloom.services", file_path=str(LOG_DIR / "services.log")
    )


def get_security_logger() -> EnhancedLogger:
    """获取安全相关日志器"""
    return get_enhanced_logger(
        "textloom.security",
        file_path=str(LOG_DIR / "security.log"),
        use_json=True,  # 安全日志使用结构化格式
    )


def get_performance_logger() -> EnhancedLogger:
    """获取性能监控日志器"""
    return get_enhanced_logger(
        "textloom.performance",
        file_path=str(LOG_DIR / "performance.log"),
        use_json=True,  # 性能日志使用结构化格式
    )


def get_business_logger() -> EnhancedLogger:
    """获取业务逻辑日志器"""
    return get_enhanced_logger(
        "textloom.business", file_path=str(LOG_DIR / "business.log")
    )


# 向后兼容函数
def get_logger(name: str, level: str = "INFO") -> EnhancedLogger:
    """向后兼容的日志器获取函数"""
    return get_enhanced_logger(name, level)


# 高级日志功能装饰器
def log_function_call(logger: EnhancedLogger = None, level: str = "DEBUG"):
    """函数调用日志装饰器"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_enhanced_logger(f"textloom.{func.__module__}")

            func_name = f"{func.__module__}.{func.__name__}"

            # 记录函数调用
            logger.debug(
                f"🔧 调用函数: {func_name}",
                extra={
                    "function": func_name,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                },
            )

            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()

                logger.debug(
                    f"✅ 函数完成: {func_name} | 耗时: {duration:.3f}秒",
                    extra={
                        "function": func_name,
                        "duration_seconds": duration,
                        "success": True,
                    },
                )
                return result

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(
                    f"❌ 函数异常: {func_name} | 耗时: {duration:.3f}秒 | 错误: {e}",
                    extra={
                        "function": func_name,
                        "duration_seconds": duration,
                        "success": False,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


def log_api_request(logger: EnhancedLogger = None):
    """API请求日志装饰器"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_api_logger()

            # 提取请求信息
            request = kwargs.get("request") or (args[0] if args else None)
            if hasattr(request, "method"):
                method = request.method
                url = str(request.url)
                client_ip = getattr(request.client, "host", "unknown")

                logger.info(
                    f"🌐 API请求: {method} {url}",
                    extra={
                        "method": method,
                        "url": url,
                        "client_ip": client_ip,
                        "endpoint": func.__name__,
                    },
                )

            start_time = datetime.now()
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()

                logger.info(
                    f"✅ API响应: {func.__name__} | 耗时: {duration:.3f}秒",
                    extra={
                        "endpoint": func.__name__,
                        "duration_seconds": duration,
                        "success": True,
                    },
                )
                return result

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(
                    f"❌ API异常: {func.__name__} | 耗时: {duration:.3f}秒 | 错误: {e}",
                    extra={
                        "endpoint": func.__name__,
                        "duration_seconds": duration,
                        "success": False,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步版本的包装器
            nonlocal logger
            if logger is None:
                logger = get_api_logger()

            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()

                logger.info(
                    f"✅ 同步调用: {func.__name__} | 耗时: {duration:.3f}秒",
                    extra={
                        "function": func.__name__,
                        "duration_seconds": duration,
                        "success": True,
                    },
                )
                return result

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(
                    f"❌ 同步调用异常: {func.__name__} | 耗时: {duration:.3f}秒 | 错误: {e}",
                    extra={
                        "function": func.__name__,
                        "duration_seconds": duration,
                        "success": False,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

        # 检查是否是异步函数
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 快捷日志函数，用于替换print()语句
class QuickLogger:
    """快捷日志类，提供简单的日志方法"""

    def __init__(self, name: str = "textloom"):
        self.logger = get_enhanced_logger(name)

    def debug(self, *args, **kwargs):
        """调试信息（替换调试类print）"""
        message = " ".join(str(arg) for arg in args)
        self.logger.debug(message, extra=kwargs if kwargs else None)

    def info(self, *args, **kwargs):
        """一般信息（替换状态类print）"""
        message = " ".join(str(arg) for arg in args)
        self.logger.info(message, extra=kwargs if kwargs else None)

    def warning(self, *args, **kwargs):
        """警告信息（替换警告类print）"""
        message = " ".join(str(arg) for arg in args)
        self.logger.warning(message, extra=kwargs if kwargs else None)

    def error(self, *args, **kwargs):
        """错误信息（替换错误类print）"""
        message = " ".join(str(arg) for arg in args)
        self.logger.error(message, extra=kwargs if kwargs else None)

    def critical(self, *args, **kwargs):
        """严重错误（替换严重错误类print）"""
        message = " ".join(str(arg) for arg in args)
        self.logger.critical(message, extra=kwargs if kwargs else None)


# 全局快捷日志实例
quick_log = QuickLogger()


# 简化的日志函数，可直接替换print()
def log_debug(*args, **kwargs):
    """调试日志（替换调试print）"""
    quick_log.debug(*args, **kwargs)


def log_info(*args, **kwargs):
    """信息日志（替换普通print）"""
    quick_log.info(*args, **kwargs)


def log_warning(*args, **kwargs):
    """警告日志（替换警告print）"""
    quick_log.warning(*args, **kwargs)


def log_error(*args, **kwargs):
    """错误日志（替换错误print）"""
    quick_log.error(*args, **kwargs)


def log_critical(*args, **kwargs):
    """严重错误日志（替换严重错误print）"""
    quick_log.critical(*args, **kwargs)


# 日志轮转配置函数
def setup_log_rotation():
    """设置日志轮转策略"""
    import logging.handlers

    # 为主要日志文件设置轮转
    log_files = [
        LOG_DIR / "api.log",
        LOG_DIR / "database.log",
        LOG_DIR / "tasks.log",
        LOG_DIR / "services.log",
        LOG_DIR / "security.log",
        LOG_DIR / "performance.log",
        LOG_DIR / "business.log",
    ]

    for log_file in log_files:
        if log_file.exists():
            # 检查文件大小，如果超过限制则触发轮转
            if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
                handler = logging.handlers.RotatingFileHandler(
                    log_file, maxBytes=10 * 1024 * 1024, backupCount=5
                )
                handler.doRollover()


# 日志清理函数
def cleanup_old_logs(days: int = 30):
    """清理指定天数之前的日志文件"""
    import time
    from pathlib import Path

    cutoff_time = time.time() - (days * 24 * 60 * 60)

    for log_dir in [LOG_DIR, WORKSPACE_LOG_DIR]:
        for log_file in log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    log_info(f"清理旧日志文件: {log_file}")
                except Exception as e:
                    log_error(f"清理日志文件失败: {log_file}, 错误: {e}")


# 初始化日志系统
def init_logging_system():
    """初始化整个日志系统"""
    # 设置日志轮转
    setup_log_rotation()

    # 清理旧日志（超过30天）
    cleanup_old_logs(30)

    # 记录系统启动
    logger = get_enhanced_logger("textloom.system")
    logger.info("🚀 TextLoom日志系统已初始化")
    logger.info(f"📁 日志目录: {LOG_DIR.absolute()}")
    logger.info(f"📁 工作空间日志目录: {WORKSPACE_LOG_DIR.absolute()}")
    logger.info(f"📊 日志级别: {settings.log_level}")


# 兼容性导入，保持与sync_logging.py的兼容
from .sync_logging import (
    get_material_analyzer_logger,
    get_material_processor_logger,
    get_script_generator_logger,
    get_task_processor_logger,
    get_video_generator_logger,
    log_api_call,
    log_api_response,
    log_database_operation,
    log_file_operation,
    log_performance,
    log_task_error,
    log_task_progress,
    log_task_start,
    log_task_success,
)
