"""
文件上传集成测试

此测试确保：
1. 存储服务可以正常初始化（不抛出配置错误）
2. 文件上传接口可以正常工作
3. 配置错误会被正确捕获和报告
"""

import pytest
import io
from fastapi import UploadFile
from unittest.mock import Mock, patch


class TestStorageServiceIntegration:
    """测试存储服务集成"""

    def test_storage_factory_can_create_storage(self):
        """
        测试 StorageFactory 可以创建存储实例

        这会触发所有存储类的导入，验证配置字段映射正确
        """
        from utils.oss.storage_factory import StorageFactory
        from config import settings

        try:
            storage = StorageFactory.get_storage()
            assert storage is not None
        except AttributeError as e:
            pytest.fail(
                f"创建存储实例失败: {e}\n"
                "这通常是 web_configs.py 字段映射错误导致的"
            )

    def test_storage_service_handles_minio_config(self):
        """测试 MinIO 存储配置处理"""
        from utils.oss.MinioStorage import MinioStorage

        # 验证 MinioStorage 可以初始化
        try:
            storage = MinioStorage()
            assert storage is not None
            assert storage.client is not None
        except AttributeError as e:
            pytest.fail(f"MinIO 存储初始化失败: {e}")

    def test_storage_service_handles_obs_config(self):
        """
        测试华为云 OBS 存储配置处理

        即使用户不使用华为云 OBS，这个类也必须能够初始化
        因为 storage_factory.py 会在模块级导入它
        """
        from utils.oss.HuaweiCloudOBS import HuaweiCloudOBS

        try:
            # 华为云 OBS 初始化可能会失败（因为缺少凭证）
            # 但不应该抛出 AttributeError（配置字段不存在）
            storage = HuaweiCloudOBS()
        except AttributeError as e:
            pytest.fail(
                f"华为云 OBS 初始化失败: {e}\n"
                "这是之前 500 错误的根本原因\n"
                "检查 web_configs.py 是否正确映射了 obs_* 字段"
            )
        except Exception as e:
            # 其他异常（如缺少凭证）是可以接受的
            pass


class TestFileUploadEndpoint:
    """测试文件上传接口"""

    @pytest.mark.asyncio
    async def test_upload_attachment_requires_storage(self):
        """测试文件上传需要存储服务"""
        from utils.oss.storage_factory import StorageFactory

        # 验证可以获取存储实例
        storage = StorageFactory.get_storage()
        assert storage is not None


class TestConfigErrorHandling:
    """测试配置错误处理"""

    def test_missing_storage_config_is_detectable(self):
        """测试缺失的存储配置可以被检测"""
        from config import Settings

        settings = Settings()

        # 验证必需的配置字段存在
        if settings.storage_type == 'minio':
            assert hasattr(settings, 'minio_endpoint')
            assert hasattr(settings, 'minio_access_key')
            assert hasattr(settings, 'minio_secret_key')
            assert hasattr(settings, 'minio_bucket_name')
        elif settings.storage_type == 'huawei_obs':
            assert hasattr(settings, 'obs_access_key')
            assert hasattr(settings, 'obs_secret_key')
            assert hasattr(settings, 'obs_endpoint')
            assert hasattr(settings, 'obs_bucket')

    def test_web_configs_reflects_current_storage_type(self):
        """测试 WEB_CONFIGS 反映当前存储类型"""
        from utils.web_configs import WEB_CONFIGS
        from config import settings

        assert WEB_CONFIGS.STORAGE_TYPE == settings.storage_type


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
