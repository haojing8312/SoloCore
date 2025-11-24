"""
存储工具类
用于上传文件到云存储服务（MinIO、华为OBS等）
"""

import os
from pathlib import Path
from typing import Optional

from config import settings
from utils.sync_logging import get_logger

logger = get_logger("storage_utils")


def upload_file_to_storage(
    file_path: str, filename: str, content_type: str = "application/octet-stream"
) -> Optional[str]:
    """
    上传文件到存储服务

    Args:
        file_path: 本地文件路径
        filename: 上传后的文件名
        content_type: 文件MIME类型

    Returns:
        文件的公网访问URL，失败返回None
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None

        # 根据配置选择存储服务
        storage_type = getattr(settings, "storage_type", "local")

        if storage_type == "minio":
            return _upload_to_minio(file_path, filename, content_type)
        elif storage_type == "obs":
            return _upload_to_obs(file_path, filename, content_type)
        elif storage_type == "local":
            return _upload_to_local(file_path, filename)
        else:
            logger.warning(f"不支持的存储类型: {storage_type}，使用本地存储")
            return _upload_to_local(file_path, filename)

    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        return None


def _upload_to_minio(file_path: str, filename: str, content_type: str) -> Optional[str]:
    """上传到MinIO"""
    try:
        from minio import Minio
        from minio.error import S3Error

        # MinIO配置 - 确保所有参数都是字符串类型
        endpoint = getattr(settings, "minio_endpoint", None)
        access_key = getattr(settings, "minio_access_key", None)
        secret_key = getattr(settings, "minio_secret_key", None)
        # 优先使用 minio_bucket_name，fallback 到 minio_bucket
        bucket_name = getattr(settings, "minio_bucket_name", None) or getattr(settings, "minio_bucket", None)
        secure = getattr(settings, "minio_secure", False)

        # 参数验证和默认值处理
        if not endpoint:
            endpoint = "localhost:9000"
        if not access_key:
            logger.error("MinIO access_key 未配置")
            return None
        if not secret_key:
            logger.error("MinIO secret_key 未配置")
            return None
        if not bucket_name:
            bucket_name = "textloom"
        
        # 确保所有参数都是字符串
        endpoint = str(endpoint)
        access_key = str(access_key)
        secret_key = str(secret_key)
        bucket_name = str(bucket_name)

        logger.info(f"MinIO配置: endpoint={endpoint}, bucket={bucket_name}, secure={secure}")

        if not access_key or not secret_key:
            logger.error("MinIO认证信息缺失")
            return None

        # 创建MinIO客户端
        client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

        # 确保bucket存在
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)

        # 上传文件
        client.fput_object(
            bucket_name=bucket_name,
            object_name=filename,
            file_path=file_path,
            content_type=content_type,
        )

        # 生成公网访问URL
        protocol = "https" if secure else "http"
        # 优先使用 minio_domain_name 作为域名
        domain_name = getattr(settings, "minio_domain_name", None)
        if domain_name:
            file_url = f"{protocol}://{domain_name}/{bucket_name}/{filename}"
        else:
            file_url = f"{protocol}://{endpoint}/{bucket_name}/{filename}"

        logger.info(f"文件上传到MinIO成功: {file_url}")
        return file_url

    except ImportError:
        logger.error("MinIO客户端库未安装")
        return None
    except S3Error as e:
        logger.error(f"MinIO上传失败: {e}")
        return None
    except Exception as e:
        logger.error(f"MinIO上传异常: {e}")
        return None


def _upload_to_obs(file_path: str, filename: str, content_type: str) -> Optional[str]:
    """上传到华为云OBS"""
    try:
        from obs import ObsClient

        # OBS配置
        endpoint = getattr(settings, "obs_endpoint", "")
        access_key = getattr(settings, "obs_access_key", "")
        secret_key = getattr(settings, "obs_secret_key", "")
        bucket_name = getattr(settings, "obs_bucket", "textloom")

        if not access_key or not secret_key or not endpoint:
            logger.error("华为云OBS认证信息缺失")
            return None

        # 创建OBS客户端
        client = ObsClient(
            access_key_id=access_key, secret_access_key=secret_key, server=endpoint
        )

        # 上传文件
        response = client.putFile(
            bucketName=bucket_name,
            objectKey=filename,
            file_path=file_path,
            metadata={"Content-Type": content_type},
        )

        if response.status < 300:
            # 生成公网访问URL
            file_url = f"https://{bucket_name}.{endpoint}/{filename}"
            logger.info(f"文件上传到OBS成功: {file_url}")
            return file_url
        else:
            logger.error(f"OBS上传失败: {response.errorCode} - {response.errorMessage}")
            return None

    except ImportError:
        logger.error("华为云OBS客户端库未安装")
        return None
    except Exception as e:
        logger.error(f"OBS上传异常: {e}")
        return None
    finally:
        try:
            client.close()
        except AttributeError:
            # client对象可能未正确初始化
            logger.debug("OBS客户端对象未正确初始化，跳过关闭操作")
        except Exception as e:
            logger.warning(f"关闭OBS客户端连接时发生错误: {e}")


def _upload_to_local(file_path: str, filename: str) -> Optional[str]:
    """上传到本地存储"""
    try:
        # 本地存储目录
        upload_dir = getattr(settings, "local_storage_dir", "./uploads")
        base_url = getattr(
            settings, "local_storage_base_url", "http://localhost:8000/uploads"
        )

        upload_path = Path(upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)

        target_path = upload_path / filename

        # 复制文件
        import shutil

        shutil.copy2(file_path, target_path)

        # 生成访问URL
        file_url = f"{base_url.rstrip('/')}/{filename}"

        logger.info(f"文件保存到本地成功: {file_url}")
        return file_url

    except Exception as e:
        logger.error(f"本地存储失败: {e}")
        return None
