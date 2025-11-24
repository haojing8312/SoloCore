"""
Web配置模块，将应用配置转换为OSS模块兼容的配置对象
"""

from config import settings


class WebConfigs:
    """Web配置类，提供OSS模块所需的配置属性"""

    def __init__(self):
        self._settings = settings

    # 存储类型
    @property
    def STORAGE_TYPE(self):
        return self._settings.storage_type

    # 华为云OBS配置
    @property
    def ACCESS_KEY_ID(self):
        return self._settings.obs_access_key_id

    @property
    def SECRET_ACCESS_KEY(self):
        return self._settings.obs_secret_access_key

    @property
    def ENDPOINT(self):
        return self._settings.obs_endpoint

    @property
    def BUCKET_NAME(self):
        return self._settings.obs_bucket_name

    @property
    def DOMAIN_NAME(self):
        return self._settings.obs_domain_name

    # MinIO配置
    @property
    def MINIO_ENDPOINT(self):
        return self._settings.minio_endpoint

    @property
    def MINIO_ACCESS_KEY(self):
        return self._settings.minio_access_key

    @property
    def MINIO_SECRET_KEY(self):
        return self._settings.minio_secret_key

    @property
    def MINIO_SECURE(self):
        return self._settings.minio_secure

    @property
    def MINIO_BUCKET_NAME(self):
        return self._settings.minio_bucket_name

    @property
    def MINIO_DOMAIN_NAME(self):
        return self._settings.minio_domain_name

    # MinIO超时与连接池配置
    @property
    def MINIO_CONNECT_TIMEOUT(self):
        return self._settings.minio_connect_timeout

    @property
    def MINIO_READ_TIMEOUT(self):
        return self._settings.minio_read_timeout

    @property
    def MINIO_MAX_POOL_SIZE(self):
        return self._settings.minio_max_pool_size


# 创建全局配置实例
WEB_CONFIGS = WebConfigs()
