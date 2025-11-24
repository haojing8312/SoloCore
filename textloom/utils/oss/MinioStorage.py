import os

from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager
from urllib3.util import Retry
from urllib3.util.timeout import Timeout

from utils.oss.storage_interface import ObjectStorage
from utils.web_configs import WEB_CONFIGS


class MinioStorage(ObjectStorage):
    """MinIO对象存储实现"""

    def __init__(self):
        # 从配置中获取MinIO连接信息
        # 配置自定义HTTP客户端，加入超时与重试，避免无限等待
        connect_timeout = getattr(WEB_CONFIGS, "MINIO_CONNECT_TIMEOUT", 5.0)
        read_timeout = getattr(WEB_CONFIGS, "MINIO_READ_TIMEOUT", 20.0)
        max_pool_size = getattr(WEB_CONFIGS, "MINIO_MAX_POOL_SIZE", 10)

        # urllib3 PoolManager 作为 MinIO 的 http_client
        # 设置连接池与重试策略（对连接失败/超时进行快速失败）
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.3,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=("GET", "PUT", "POST", "HEAD"),
        )
        http_client = PoolManager(
            num_pools=max_pool_size,
            maxsize=max_pool_size,
            retries=retry,
            timeout=Timeout(connect=connect_timeout, read=read_timeout),
        )

        self.client = Minio(
            endpoint=WEB_CONFIGS.MINIO_ENDPOINT,
            access_key=WEB_CONFIGS.MINIO_ACCESS_KEY,
            secret_key=WEB_CONFIGS.MINIO_SECRET_KEY,
            secure=WEB_CONFIGS.MINIO_SECURE,
            http_client=http_client,  # 自定义HTTP客户端
        )
        self.bucket_name = WEB_CONFIGS.MINIO_BUCKET_NAME
        self.domain_name = WEB_CONFIGS.MINIO_DOMAIN_NAME

        # 使用懒加载，避免在初始化时就发起网络请求
        self._bucket_checked = False

    def _ensure_bucket_exists(self):
        """确保存储桶存在（懒加载）"""
        if not self._bucket_checked:
            try:
                if not self.client.bucket_exists(self.bucket_name):
                    self.client.make_bucket(self.bucket_name)
                self._bucket_checked = True
            except S3Error as e:
                raise Exception(f"MinIO存储桶检查失败: {e}")

    def upload_file(self, file_path, object_key=None):
        """上传文件到MinIO，并返回文件的URL"""
        # 在实际使用时才检查存储桶
        self._ensure_bucket_exists()

        if object_key is None:
            object_key = os.path.basename(file_path)

        try:
            # 获取文件大小和MIME类型
            file_size = os.path.getsize(file_path)
            content_type = self._get_content_type(file_path)

            # 上传文件
            self.client.fput_object(
                self.bucket_name, object_key, file_path, content_type=content_type
            )

            # 根据提供的URL格式构建URL
            url = f"https://{self.domain_name}/{self.bucket_name}/{object_key}"
            return url
        except S3Error as e:
            raise Exception(f"文件上传失败: {e}")

    def download_file(self, object_key, download_path):
        """通过文件的对象键从MinIO下载文件"""
        # 在实际使用时才检查存储桶
        self._ensure_bucket_exists()

        try:
            self.client.fget_object(self.bucket_name, object_key, download_path)
        except S3Error as e:
            raise Exception(f"文件下载失败: {e}")

    def delete_file(self, object_key):
        """删除MinIO中的文件"""
        # 在实际使用时才检查存储桶
        self._ensure_bucket_exists()

        try:
            self.client.remove_object(self.bucket_name, object_key)
            return True
        except S3Error as e:
            raise Exception(f"文件删除失败: {e}")

    def list_files(self, prefix="", max_keys=1000):
        """列出MinIO中的文件"""
        # 在实际使用时才检查存储桶
        self._ensure_bucket_exists()

        try:
            objects = self.client.list_objects(
                self.bucket_name, prefix=prefix, recursive=True
            )

            result = []
            count = 0
            for obj in objects:
                if count >= max_keys:
                    break
                result.append(obj)
                count += 1

            return result
        except S3Error as e:
            raise Exception(f"列出文件失败: {e}")

    def file_exists(self, object_key):
        """检查文件是否存在于MinIO中"""
        # 在实际使用时才检查存储桶
        self._ensure_bucket_exists()

        try:
            self.client.stat_object(self.bucket_name, object_key)
            return True
        except S3Error:
            return False

    def _get_content_type(self, file_path):
        """根据文件扩展名获取MIME类型"""
        extension = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".html": "text/html",
            ".htm": "text/html",
            ".json": "application/json",
            ".xml": "application/xml",
            ".mp4": "video/mp4",
            ".mp3": "audio/mpeg",
            ".zip": "application/zip",
        }
        return content_types.get(extension, "application/octet-stream")


# 使用示例
if __name__ == "__main__":
    storage = MinioStorage()

    # 上传文件
    file_path = "utils/oss/requirements.txt"
    try:
        file_url = storage.upload_file(file_path)
    except Exception as e:
        raise Exception(f"文件上传失败: {e}")

    # 下载文件
    object_key = "utils/oss/requirements.txt"  # 上传时使用的对象键
    download_path = "requirements.txt1"
    try:
        storage.download_file(object_key, download_path)
    except Exception as e:
        raise Exception(f"文件下载失败: {e}")
