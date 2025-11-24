import os
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用程序设置（仅从环境读取）"""

    # 基础应用信息
    app_name: str = "TextLoom API"
    app_version: str = "1.0.0"
    debug: bool = False

    # JWT 设置（密钥不提供默认值）
    secret_key: Optional[str] = None
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # JWT安全配置
    jwt_issuer: str = "textloom-api"
    jwt_require_iat: bool = True  # 要求issued at时间
    jwt_require_exp: bool = True  # 要求过期时间
    jwt_verify_signature: bool = True
    jwt_leeway: int = 0  # 时间偏移容忍度（秒）

    # 数据库设置（不提供默认值）
    database_url: Optional[str] = None

    # 数据库连接池设置（优化后的生产级配置）
    database_pool_size: int = 15  # 提升基础连接池大小以支持更高并发
    database_max_overflow: int = 8  # 增加溢出连接数，避免连接饥饿
    database_pool_timeout: int = 45  # 适当增加超时时间
    database_pool_recycle: int = 3600  # 1小时回收，平衡连接复用与资源释放
    database_pool_pre_ping: bool = True  # 连接前测试有效性，保证连接质量

    # Celery数据库连接池设置（任务处理优化配置）
    celery_database_pool_size: int = 12  # Celery专用连接池大小，支持更多并发任务
    celery_database_max_overflow: int = 6  # Celery允许的溢出连接，处理突发负载
    celery_database_min_connections: int = 3  # 最小连接数，保证基础可用性

    # 服务器设置
    host: str = "0.0.0.0"
    port: int = 48095

    # CORS 安全配置（不再使用通配符，需从环境指定可信域清单，JSON 数组格式）
    allowed_origins: List[str] = []  # 必须明确指定可信域名，不允许使用 "*"
    cors_allow_credentials: bool = False  # 默认禁用凭据，根据需要开启
    cors_allowed_methods: List[str] = [
        "GET",
        "POST",
        "PUT",
        "DELETE",
    ]  # 仅允许业务必需的HTTP方法
    cors_allowed_headers: List[str] = [
        "Content-Type",
        "Authorization",
        "x-test-token",
    ]  # 仅允许必要的请求头
    cors_expose_headers: List[str] = [
        "Content-Length",
        "Content-Type",
    ]  # 限制暴露的响应头
    cors_max_age: int = 86400  # 24小时预检请求缓存

    # 大模型配置（密钥/地址不提供默认值，模型名可提供默认）
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    openai_model_name: str = "Qwen/Qwen2.5-VL-72B-Instruct"
    script_model_name: str = "deepseek-chat"

    # 图片分析配置
    image_analysis_model_name: str = "Qwen/Qwen2.5-VL-72B-Instruct"

    # Editly 视频引擎配置
    editly_executable_path: Optional[str] = None  # 自定义 editly 路径（留空自动查找）
    editly_fast_mode: bool = True  # 快速模式（跳过部分质量检查）

    # 视频合成默认配置（非敏感，提供默认值）
    video_default_aspect: str = "9:16"
    video_default_width: int = 1080
    video_default_height: int = 1920
    video_default_fps: int = 30  # 帧率配置
    video_default_page_mode: int = 4
    video_default_matting: int = 1
    video_resize_mode: str = "contain-blur"  # 视频缩放模式: contain, cover, contain-blur

    # 数字人与声音配置（非敏感，提供默认值）
    digital_human_entity_id: str = ""
    digital_human_name: str = "数字人"
    digital_human_cover: str = ""

    voice_entity_id: str = ""
    voice_name: str = ""
    voice_id: int = 0
    voice_type: int = 0

    # 背景配置（默认空）
    background_image_url: str = ""
    background_color: str = "#000000"  # 默认背景颜色（纯色背景）

    # 字幕样式配置（非敏感，提供默认值）
    subtitle_enable: bool = False
    subtitle_color: str = "#ffffff"
    subtitle_font_name: str = "DejaVu Sans"
    subtitle_font_size: float = 76.8
    subtitle_width: float = 1079.4666666666667
    subtitle_height: float = 85.33333333333333
    subtitle_x: float = 0
    subtitle_y: float = 1706.6666666666667
    subtitle_depth: int = 500
    subtitle_border_style: bool = True
    subtitle_outline: int = 0
    subtitle_outline_color: str = "#3B3B3B"

    # 文件限制
    max_file_size: int = 52428800  # 50MB
    download_timeout: int = 30
    max_images_per_task: int = 20
    max_videos_per_task: int = 5

    # 任务处理设置（性能优化配置）
    task_polling_interval: int = 3  # 减少轮询间隔，提升响应性
    max_concurrent_tasks: int = 5  # 增加并发任务数
    task_timeout: int = 3600

    # 数据库连接池健康检查设置
    db_health_check_interval: int = 300  # 5分钟检查一次连接池健康状态
    db_connection_retry_attempts: int = 3  # 连接重试次数
    db_connection_retry_delay: int = 5  # 重试间隔秒数

    # Redis 配置（优化连接池和超时设置）
    redis_host: Optional[str] = None
    redis_port: Optional[int] = None
    redis_db: Optional[int] = None
    redis_password: Optional[str] = None
    redis_max_connections: int = 30  # 增加Redis连接池大小
    redis_socket_timeout: int = 45  # 适当增加超时
    redis_socket_connect_timeout: int = 15  # 连接超时保持较短

    # Celery 配置
    celery_worker_concurrency: int = 4
    celery_worker_max_memory_per_child: int = 200000
    celery_broker_connection_retry_on_startup: bool = True
    celery_task_always_eager: bool = False

    # 多视频生成设置
    multi_video_generation_enabled: bool = True
    multi_video_count: int = 3
    multi_video_generation_timeout: int = 1800

    # 视频标题组件配置
    video_title_enabled: bool = True
    video_title_font_size: float = 22.5
    video_title_color: str = "rgb(253, 217, 103)"
    video_title_font_family: str = "NotoSerifSC Regular"
    video_title_top: float = 85.33333333333333
    video_title_margin_left: float = 89.6
    video_title_width: float = 853.3333333333334
    video_title_height: float = 170.66666666666666

    # 视频副标题配置
    video_subtitle_enabled: bool = True
    video_subtitle_text: str = "本视频由TEXTLOOM抓取和生成"
    video_subtitle_font_size: float = 15
    video_subtitle_color: str = "rgb(253, 217, 103)"
    video_subtitle_font_family: str = "NotoSerifSC Regular"
    video_subtitle_top: float = 1403.7333333333333
    video_subtitle_margin_left: float = 473.59999999999997
    video_subtitle_width: float = 490.6666666666667
    video_subtitle_height: float = 247.46666666666667

    # 日志设置
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # 内部测试接口专用 Token（仅用于 dev/staging，prod 可为空禁用）
    internal_test_token: Optional[str] = None

    # 动态字幕配置
    dynamic_subtitle_enabled: bool = False
    dynamic_subtitle_style: str = "default"
    dynamic_subtitle_animation: str = "fade_in"
    dynamic_subtitle_font_size: int = 24
    dynamic_subtitle_font_color: str = "#FFFFFF"

    # 存储配置
    storage_type: str = "local"  # 可选: huawei_obs, minio, local
    local_storage_dir: str = "./uploads"
    local_storage_base_url: str = "http://localhost:8000/uploads"

    # 华为云 OBS（不提供默认值）
    obs_access_key: Optional[str] = None
    obs_secret_key: Optional[str] = None
    obs_endpoint: Optional[str] = None
    obs_bucket: Optional[str] = None

    # MinIO（不提供默认值，网络参数提供默认）
    minio_endpoint: Optional[str] = None
    minio_access_key: Optional[str] = None
    minio_secret_key: Optional[str] = None
    minio_secure: bool = False
    minio_bucket: Optional[str] = None
    minio_bucket_name: Optional[str] = None
    minio_domain_name: Optional[str] = None

    # 工作空间配置
    workspace_dir: str = "./workspace"

    # 监控配置（prometheus_client库要求）
    prometheus_multiproc_dir: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略.env中未定义的额外配置项

    def get_current_model_name(self) -> str:
        """获取当前应该使用的主模型名称"""
        return self.openai_model_name

    def get_current_script_model_name(self) -> str:
        """获取当前应该使用的脚本生成模型名称"""
        return self.script_model_name

    def get_allowed_origins(self) -> List[str]:
        """
        获取CORS允许的源列表，根据环境提供安全默认值
        开发环境：允许本地域名
        生产环境：仅允许明确配置的可信域名
        """
        if self.allowed_origins:
            # 如果环境变量中有配置，优先使用
            return self.allowed_origins

        # 根据环境提供安全默认值
        if self.debug:
            # 开发环境：允许本地域名和常用开发端口
            return [
                "http://localhost:3000",  # React/Next.js 默认端口
                "http://localhost:8080",  # Vue.js 默认端口
                "http://localhost:8000",  # 本地API端口
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8080",
                "http://127.0.0.1:8000",
            ]
        else:
            # 生产环境：默认空列表，必须明确配置
            logger.warning(
                "CORS allowed_origins 未配置，生产环境下将拒绝所有跨域请求。"
                "请设置 ALLOWED_ORIGINS 环境变量。"
            )
            return []


# 全局设置实例
settings = Settings()


def get_settings() -> Settings:
    """获取全局设置实例"""
    return settings


# 引入logging模块，用于get_allowed_origins方法中的警告
import logging

logger = logging.getLogger(__name__)

# 确保日志目录存在
os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
