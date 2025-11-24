import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

from minio import Minio
from minio.error import S3Error

from utils.oss.MinioStorage import MinioStorage
from utils.oss.storage_interface import ObjectStorage
from utils.web_configs import WEB_CONFIGS


class MinioStorageAsync(MinioStorage):
    """MinIO对象存储异步实现"""

    def __init__(self):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=10)

    async def upload_file_async(self, file_path, object_key=None):
        """异步上传文件到MinIO，并返回文件的URL"""
        if object_key is None:
            object_key = os.path.basename(file_path)

        try:
            # 使用线程池执行阻塞操作
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                self.executor, lambda: self._upload_file_impl(file_path, object_key)
            )
            return url
        except Exception as e:
            raise Exception(f"异步文件上传失败: {e}")

    async def download_file_async(self, object_key, download_path):
        """异步从MinIO下载文件"""
        try:
            # 使用线程池执行阻塞操作
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: self._download_file_impl(object_key, download_path),
            )
        except Exception as e:
            raise Exception(f"异步文件下载失败: {e}")

    def _upload_file_impl(self, file_path, object_key):
        """上传文件的实际实现（供异步方法调用）"""
        try:
            # 获取文件大小和MIME类型
            file_size = os.path.getsize(file_path)
            content_type = self._get_content_type(file_path)

            # 上传文件
            self.client.fput_object(
                self.bucket_name, object_key, file_path, content_type=content_type
            )

            print(f"文件上传成功，ObjectKey: {object_key}")
            # 根据提供的URL格式构建URL
            url = f"https://{self.domain_name}/minio/{self.bucket_name}/{object_key}"
            return url
        except S3Error as e:
            raise Exception(f"文件上传失败: {e}")

    def _download_file_impl(self, object_key, download_path):
        """下载文件的实际实现（供异步方法调用）"""
        try:
            self.client.fget_object(self.bucket_name, object_key, download_path)
            print(f"文件下载成功，保存到: {download_path}")
        except S3Error as e:
            raise Exception(f"文件下载失败: {e}")


# 使用示例
if __name__ == "__main__":
    storage = MinioStorageAsync()

    # 异步上传文件
    async def upload_example():
        file_path = "path/to/your/local/file.txt"
        try:
            file_url = await storage.upload_file_async(file_path)
            print(f"文件的URL: {file_url}")
        except Exception as e:
            print(str(e))

    # 异步下载文件
    async def download_example():
        object_key = "file.txt"
        download_path = "path/to/save/file.txt"
        try:
            await storage.download_file_async(object_key, download_path)
        except Exception as e:
            print(str(e))

    # 运行异步示例
    async def main():
        await upload_example()
        await download_example()

    # 在异步环境中运行
    asyncio.run(main())
