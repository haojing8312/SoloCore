"""
同步客户端工具模块
为Celery任务提供OpenAI兼容格式和HTTP的同步客户端封装
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import settings
from utils.sync_logging import log_api_call, log_api_response

logger = logging.getLogger(__name__)

# ==================== OpenAI同步客户端 ====================


class SyncOpenAIClient:
    """OpenAI同步客户端封装"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """初始化OpenAI同步客户端

        Args:
            logger: 可选，指定用于输出日志的日志器；若不提供，默认使用
                    名为 "sync_material_analyzer" 的组件日志器，以便与
                    素材分析日志统一到同一日志文件。
        """
        self.client = OpenAI(
            api_key=settings.openai_api_key, base_url=settings.openai_api_base
        )
        self.max_retries = 3
        self.retry_delay = 1  # 秒
        # 允许注入专用日志器，默认回落到素材分析器日志器名称，便于统一输出到
        # logs/sync_material_analyzer.log 文件。
        self.logger = logger or logging.getLogger("sync_material_analyzer")

        self.logger.info(
            f"OpenAI同步客户端初始化完成 - Base URL: {settings.openai_api_base}"
        )

    # 已移除：带上下文提示的旧接口（由业务层统一构建prompt）

    def analyze_image(
        self, image_url: str, prompt: str, model: str = None
    ) -> Optional[str]:
        """
        通用图片分析：由上层业务构建完整提示词，这里仅转发请求

        Args:
            image_url: 图片URL（或 data URL）
            prompt: 已构建好的完整提示词（包含上下文/输出要求等）
            model: 模型名
        Returns:
            模型原始文本响应
        """
        if not model:
            model = settings.image_analysis_model_name

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]

        # 日志：打印Prompt与图片URL（预览）
        try:
            preview_len = 800
            self.logger.info(
                "[OpenAI][素材分析-通用] Prompt预览(前%d字): %s",
                preview_len,
                (prompt or "")[:preview_len],
            )
            self.logger.debug("[OpenAI][素材分析-通用] Prompt完整:\n%s", prompt)
            if isinstance(image_url, str):
                if image_url.startswith("data:image"):
                    safe_image_url = "data:image/... (base64省略)"
                else:
                    safe_image_url = (
                        image_url if len(image_url) <= 200 else image_url[:200] + "..."
                    )
                self.logger.debug(
                    "[OpenAI][素材分析-通用] Image URL(预览): %s", safe_image_url
                )
        except Exception:
            pass

        for attempt in range(self.max_retries):
            try:
                start_time = datetime.now()
                self.logger.debug(
                    f"调用OpenAI通用图片分析 - 尝试 {attempt + 1}/{self.max_retries}"
                )
                log_api_call(
                    self.logger,
                    "OpenAI",
                    "analyze_image_generic",
                    model=model,
                    image_url=image_url[:50] + "...",
                    prompt_length=len(prompt or ""),
                    attempt=attempt + 1,
                )

                response = self.client.chat.completions.create(
                    model=model, messages=messages, max_tokens=800, temperature=0.3
                )

                duration = (datetime.now() - start_time).total_seconds()
                if response.choices and response.choices[0].message.content:
                    result = response.choices[0].message.content.strip()
                    log_api_response(
                        self.logger,
                        "OpenAI",
                        "analyze_image_generic",
                        True,
                        {
                            "result_length": len(result),
                            "duration": f"{duration:.2f}s",
                            "tokens_used": (
                                response.usage.total_tokens
                                if response.usage
                                else "unknown"
                            ),
                        },
                    )
                    self.logger.info(
                        f"OpenAI通用图片分析成功 - 耗时: {duration:.2f}s, 结果长度: {len(result)}, Token使用: {response.usage.total_tokens if response.usage else 'unknown'}"
                    )
                    try:
                        preview_len = 800
                        self.logger.info(
                            "[OpenAI][素材分析-通用] 返回预览(前%d字): %s",
                            preview_len,
                            (result or "")[:preview_len],
                        )
                        self.logger.debug(
                            "[OpenAI][素材分析-通用] 返回完整:\n%s", result
                        )
                    except Exception:
                        pass
                    return result
                else:
                    log_api_response(
                        self.logger,
                        "OpenAI",
                        "analyze_image_generic",
                        False,
                        {"error": "empty_response", "duration": f"{duration:.2f}s"},
                    )
                    self.logger.warning(f"OpenAI返回空结果 - 耗时: {duration:.2f}s")
                    return None

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                error_msg = str(e)
                log_api_response(
                    self.logger,
                    "OpenAI",
                    "analyze_image_generic",
                    False,
                    {
                        "error": error_msg[:200],
                        "duration": f"{duration:.2f}s",
                        "attempt": attempt + 1,
                    },
                )
                self.logger.error(
                    f"OpenAI通用图片分析失败 (尝试 {attempt + 1}/{self.max_retries}): {error_msg} - 耗时: {duration:.2f}s"
                )

                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    self.logger.info(f"等待 {delay} 秒后重试...")
                    time.sleep(delay)  # Celery任务中使用同步sleep，指数退避重试
                else:
                    self.logger.error("OpenAI通用图片分析达到最大重试次数，放弃")
                    return None

        return None

    def generate_script(
        self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7
    ) -> Optional[str]:
        """使用OpenAI生成脚本内容"""
        for attempt in range(self.max_retries):
            try:
                start_time = datetime.now()
                self.logger.debug(
                    f"调用OpenAI生成脚本 - 尝试 {attempt + 1}/{self.max_retries}"
                )
                log_api_call(
                    self.logger,
                    "OpenAI",
                    "generate_script",
                    prompt_length=len(prompt),
                    max_tokens=max_tokens,
                    temperature=temperature,
                    attempt=attempt + 1,
                )
                # 记录Prompt预览与完整内容
                try:
                    preview_len = 800
                    self.logger.info(
                        "[OpenAI] Prompt预览(前%d字): %s",
                        preview_len,
                        (prompt or "")[:preview_len],
                    )
                    self.logger.debug("[OpenAI] Prompt完整:\n%s", prompt)
                except Exception:
                    pass

                response = self.client.chat.completions.create(
                    model=settings.script_model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                duration = (datetime.now() - start_time).total_seconds()

                if (
                    response.choices
                    and getattr(response.choices[0], "message", None)
                    and response.choices[0].message.content
                ):
                    result = response.choices[0].message.content.strip()
                    log_api_response(
                        self.logger,
                        "OpenAI",
                        "generate_script",
                        True,
                        {
                            "result_length": len(result),
                            "duration": f"{duration:.2f}s",
                            "tokens_used": (
                                response.usage.total_tokens
                                if response.usage
                                else "unknown"
                            ),
                        },
                    )
                    self.logger.info(
                        f"OpenAI脚本生成成功 - 耗时: {duration:.2f}s, 结果长度: {len(result)}, Token使用: {response.usage.total_tokens if response.usage else 'unknown'}"
                    )
                    try:
                        preview_len = 800
                        self.logger.info(
                            "[OpenAI] 输出预览(前%d字): %s",
                            preview_len,
                            (result or "")[:preview_len],
                        )
                        self.logger.debug("[OpenAI] 输出完整:\n%s", result)
                    except Exception:
                        pass
                    return result
                else:
                    log_api_response(
                        self.logger,
                        "OpenAI",
                        "generate_script",
                        False,
                        {"error": "empty_response", "duration": f"{duration:.2f}s"},
                    )
                    self.logger.warning(f"OpenAI返回空结果 - 耗时: {duration:.2f}s")
                    return None

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                error_msg = str(e)
                log_api_response(
                    self.logger,
                    "OpenAI",
                    "generate_script",
                    False,
                    {
                        "error": error_msg[:200],
                        "duration": f"{duration:.2f}s",
                        "attempt": attempt + 1,
                    },
                )
                self.logger.error(
                    f"OpenAI脚本生成失败 (尝试 {attempt + 1}/{self.max_retries}): {error_msg} - 耗时: {duration:.2f}s"
                )

                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    self.logger.info(f"等待 {delay} 秒后重试...")
                    time.sleep(delay)  # Celery任务中使用同步sleep，指数退避重试
                else:
                    self.logger.error("OpenAI脚本生成达到最大重试次数，放弃")
                    return None

        return None

    # 已移除：内部构建上下文提示词（由业务层负责组装prompt）


# ==================== HTTP同步客户端 ====================


class SyncHTTPClient:
    """HTTP同步客户端封装（基于requests）"""

    def __init__(self):
        """初始化HTTP同步客户端"""
        self.session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 设置默认headers
        self.session.headers.update(
            {
                "User-Agent": "TextLoom-Sync-Client/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        # 超时配置
        self.timeout = (10, 30)  # (连接超时, 读取超时)

        logger.info("HTTP同步客户端初始化完成")

    def download_file(
        self, url: str, headers: Dict[str, str] = None
    ) -> Optional[bytes]:
        """
        下载文件

        Args:
            url: 文件URL
            headers: 额外的请求头

        Returns:
            文件内容字节数据
        """
        try:
            start_time = datetime.now()
            log_api_call(
                logger,
                "HTTP",
                "download_file",
                url=url[:100] + "...",
                has_headers=bool(headers),
            )
            logger.info(f"开始下载文件: {url[:100]}...")

            request_headers = {}
            if headers:
                request_headers.update(headers)

            response = self.session.get(
                url, headers=request_headers, timeout=self.timeout, stream=True
            )

            response.raise_for_status()
            duration = (datetime.now() - start_time).total_seconds()

            # 检查文件大小
            content_length = response.headers.get("content-length")
            if content_length:
                file_size = int(content_length)
                max_size = 50 * 1024 * 1024  # 50MB
                if file_size > max_size:
                    log_api_response(
                        logger,
                        "HTTP",
                        "download_file",
                        False,
                        {
                            "error": "file_too_large",
                            "size": file_size,
                            "max_size": max_size,
                            "duration": f"{duration:.2f}s",
                        },
                    )
                    logger.error(
                        f"文件太大: {file_size} bytes (最大: {max_size} bytes) - 耗时: {duration:.2f}s"
                    )
                    return None

            # 读取文件内容
            content = response.content
            total_duration = (datetime.now() - start_time).total_seconds()

            log_api_response(
                logger,
                "HTTP",
                "download_file",
                True,
                {
                    "status_code": response.status_code,
                    "content_length": len(content),
                    "duration": f"{total_duration:.2f}s",
                    "content_type": response.headers.get("content-type"),
                },
            )

            logger.info(
                f"HTTP文件下载成功 - 大小: {len(content)} bytes, 耗时: {total_duration:.2f}s"
            )
            return content

        except requests.exceptions.RequestException as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)

            log_api_response(
                logger,
                "HTTP",
                "download_file",
                False,
                {
                    "error": error_msg[:200],
                    "duration": f"{duration:.2f}s",
                    "url": url[:100],
                },
            )

            logger.error(
                f"HTTP文件下载失败 - URL: {url[:100]}..., 错误: {error_msg}, 耗时: {duration:.2f}s"
            )
            return None
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)

            log_api_response(
                logger,
                "HTTP",
                "download_file",
                False,
                {
                    "error": f"exception_{type(e).__name__}",
                    "message": error_msg[:200],
                    "duration": f"{duration:.2f}s",
                },
            )

            logger.error(
                f"HTTP文件下载异常 - URL: {url[:100]}..., 错误: {error_msg}, 耗时: {duration:.2f}s"
            )
            return None

    def post_json(
        self, url: str, data: Dict[str, Any], headers: Dict[str, str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        发送JSON POST请求

        Args:
            url: 请求URL
            data: JSON数据
            headers: 额外的请求头

        Returns:
            响应JSON数据
        """
        try:
            logger.debug(f"发送POST请求: {url}")

            request_headers = {}
            if headers:
                request_headers.update(headers)

            response = self.session.post(
                url, json=data, headers=request_headers, timeout=self.timeout
            )

            response.raise_for_status()

            result = response.json()
            logger.debug(f"POST请求成功 - 状态码: {response.status_code}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"POST请求失败: {url} - 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"POST请求异常: {url} - 错误: {e}")
            return None

    def get_json(
        self, url: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        发送JSON GET请求

        Args:
            url: 请求URL
            params: 查询参数
            headers: 额外的请求头

        Returns:
            响应JSON数据
        """
        try:
            logger.debug(f"发送GET请求: {url}")

            request_headers = {}
            if headers:
                request_headers.update(headers)

            response = self.session.get(
                url, params=params, headers=request_headers, timeout=self.timeout
            )

            response.raise_for_status()

            result = response.json()
            logger.debug(f"GET请求成功 - 状态码: {response.status_code}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"GET请求失败: {url} - 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"GET请求异常: {url} - 错误: {e}")
            return None


# ==================== 客户端工厂 ====================


class SyncClientFactory:
    """同步客户端工厂类"""

    _openai_client: Optional[SyncOpenAIClient] = None
    _http_client: Optional[SyncHTTPClient] = None

    @classmethod
    def get_openai_client(
        cls, logger: Optional[logging.Logger] = None
    ) -> SyncOpenAIClient:
        """获取OpenAI同步客户端（单例）

        如果提供了 logger，则会将该日志器设置到现有实例或新创建的实例上，
        以便输出到指定组件日志文件。
        """
        if cls._openai_client is None:
            cls._openai_client = SyncOpenAIClient(logger=logger)
        elif logger is not None:
            try:
                cls._openai_client.logger = logger
            except Exception:
                pass
        return cls._openai_client

    @classmethod
    def get_http_client(cls) -> SyncHTTPClient:
        """获取HTTP同步客户端（单例）"""
        if cls._http_client is None:
            cls._http_client = SyncHTTPClient()
        return cls._http_client

    @classmethod
    def get_script_client(cls):
        """返回用于脚本生成的同步客户端（OpenAI兼容格式）"""
        return cls.get_openai_client()


# ==================== 便捷函数 ====================


def get_sync_openai_client(logger: Optional[logging.Logger] = None) -> SyncOpenAIClient:
    """获取OpenAI同步客户端

    Args:
        logger: 可选，指定用于输出日志的日志器
    """
    return SyncClientFactory.get_openai_client(logger=logger)


def get_sync_http_client() -> SyncHTTPClient:
    """获取HTTP同步客户端"""
    return SyncClientFactory.get_http_client()


def get_sync_script_client():
    """获取用于脚本生成的同步客户端（OpenAI兼容格式）"""
    return SyncClientFactory.get_script_client()
