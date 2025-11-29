"""
配置一致性单元测试

此测试确保：
1. web_configs.py 中的字段映射与 config.py 中的字段名称一致
2. 所有存储配置可以正常初始化（即使不使用该存储后端）
3. 配置字段的类型匹配预期

目的：防止类似 'obs_access_key_id' vs 'obs_access_key' 的字段名不匹配问题
此类问题会导致模块导入时抛出 AttributeError，即使用户没有使用该存储后端
"""

import pytest
from typing import get_type_hints
from config import Settings
from utils.web_configs import WebConfigs, WEB_CONFIGS


class TestWebConfigsFieldMapping:
    """测试 WebConfigs 属性与 Settings 字段的映射一致性"""

    @pytest.fixture
    def settings(self):
        """创建测试用的 Settings 实例"""
        return Settings()

    @pytest.fixture
    def web_configs(self, settings):
        """创建测试用的 WebConfigs 实例"""
        config = WebConfigs()
        config._settings = settings
        return config

    def test_huawei_obs_config_fields_mapping(self, web_configs, settings):
        """
        测试华为云 OBS 配置字段映射

        这是此前导致 500 错误的根本原因：
        - web_configs.py 试图访问 settings.obs_access_key_id
        - 但 config.py 实际定义的是 settings.obs_access_key
        """
        field_mappings = {
            'ACCESS_KEY_ID': 'obs_access_key',
            'SECRET_ACCESS_KEY': 'obs_secret_key',
            'ENDPOINT': 'obs_endpoint',
            'BUCKET_NAME': 'obs_bucket',
            'DOMAIN_NAME': 'obs_domain_name',
        }

        for property_name, settings_field in field_mappings.items():
            # 1. 验证 Settings 有这个字段
            assert hasattr(settings, settings_field), \
                f"Settings 缺少字段: {settings_field} (WebConfigs.{property_name} 需要它)"

            # 2. 验证 WebConfigs 可以访问这个属性
            try:
                value = getattr(web_configs, property_name)
                # 值可以是 None（未配置）或实际值
            except AttributeError as e:
                pytest.fail(
                    f"WebConfigs.{property_name} 访问失败: {e}\n"
                    f"检查 web_configs.py 是否正确映射到 settings.{settings_field}\n"
                    f"这会导致模块导入时抛出 AttributeError，即使不使用华为云 OBS"
                )

    def test_minio_config_fields_mapping(self, web_configs, settings):
        """测试 MinIO 配置字段映射"""
        field_mappings = {
            'MINIO_ENDPOINT': 'minio_endpoint',
            'MINIO_ACCESS_KEY': 'minio_access_key',
            'MINIO_SECRET_KEY': 'minio_secret_key',
            'MINIO_SECURE': 'minio_secure',
            'MINIO_BUCKET_NAME': 'minio_bucket_name',
            'MINIO_DOMAIN_NAME': 'minio_domain_name',
            'MINIO_CONNECT_TIMEOUT': 'minio_connect_timeout',
            'MINIO_READ_TIMEOUT': 'minio_read_timeout',
            'MINIO_MAX_POOL_SIZE': 'minio_max_pool_size',
        }

        for property_name, settings_field in field_mappings.items():
            assert hasattr(settings, settings_field), \
                f"Settings 缺少字段: {settings_field} (WebConfigs.{property_name} 需要它)"

            try:
                value = getattr(web_configs, property_name)
            except AttributeError as e:
                pytest.fail(
                    f"WebConfigs.{property_name} 访问失败: {e}\n"
                    f"检查 web_configs.py 是否正确映射到 settings.{settings_field}"
                )

    def test_storage_type_field_mapping(self, web_configs, settings):
        """测试存储类型字段映射"""
        assert hasattr(settings, 'storage_type'), \
            "Settings 缺少字段: storage_type"

        try:
            storage_type = web_configs.STORAGE_TYPE
            # 验证是有效的存储类型
            assert storage_type in ['minio', 'huawei_obs', 's3'], \
                f"storage_type 值无效: {storage_type}"
        except AttributeError as e:
            pytest.fail(f"WebConfigs.STORAGE_TYPE 访问失败: {e}")


class TestStorageClassesInitialization:
    """
    测试所有存储实现类可以安全初始化

    重要：即使用户只使用 MinIO，storage_factory.py 的模块级导入
    也会初始化所有存储类（HuaweiCloudOBS, S3Storage 等）
    因此所有类必须能够在配置不完整时安全初始化
    """

    def test_storage_factory_import_succeeds(self):
        """
        storage_factory 应该可以安全导入

        此测试模拟了之前的 500 错误场景：
        - 用户配置了 MinIO
        - 但 storage_factory.py 的模块级导入会加载 HuaweiCloudOBS
        - HuaweiCloudOBS.__init__() 访问了不存在的配置字段
        - 导致 AttributeError，文件上传返回 500
        """
        try:
            from utils.oss.storage_factory import StorageFactory
            assert StorageFactory is not None
        except AttributeError as e:
            pytest.fail(
                f"storage_factory 导入失败: {e}\n"
                "这通常是因为模块级导入的存储类访问了不存在的配置字段\n"
                "请检查 web_configs.py 中的字段名是否与 config.py 一致"
            )
        except Exception as e:
            pytest.fail(f"storage_factory 导入时发生未预期的错误: {e}")

    def test_minio_storage_import_succeeds(self):
        """MinIO 存储实现类应该可以安全导入"""
        try:
            from utils.oss.MinioStorage import MinioStorage
            assert MinioStorage is not None
        except AttributeError as e:
            pytest.fail(
                f"MinioStorage 导入失败: {e}\n"
                "检查类初始化是否访问了不存在的配置字段"
            )

    def test_huawei_obs_storage_import_succeeds(self):
        """
        华为云 OBS 存储实现类应该可以安全导入

        这是之前 500 错误的直接原因：
        HuaweiCloudOBS.__init__() 访问了 WEB_CONFIGS.ACCESS_KEY_ID
        而 web_configs.py 试图读取 settings.obs_access_key_id（错误）
        实际字段名是 settings.obs_access_key
        """
        try:
            from utils.oss.HuaweiCloudOBS import HuaweiCloudOBS
            assert HuaweiCloudOBS is not None
        except AttributeError as e:
            pytest.fail(
                f"HuaweiCloudOBS 导入失败: {e}\n"
                "这通常是字段名不匹配导致的\n"
                "检查 web_configs.py 是否正确映射了 obs_* 字段"
            )


class TestConfigFieldTypes:
    """测试配置字段类型正确性"""

    def test_settings_storage_fields_types(self):
        """验证 Settings 中存储相关字段的类型注解"""
        settings_hints = get_type_hints(Settings)

        # MinIO 字段类型检查
        minio_string_fields = [
            'minio_endpoint', 'minio_access_key', 'minio_secret_key',
            'minio_bucket_name', 'minio_domain_name'
        ]
        for field in minio_string_fields:
            assert field in settings_hints, f"Settings 缺少字段: {field}"
            assert 'str' in str(settings_hints[field]), \
                f"字段 {field} 应该是字符串类型，当前是: {settings_hints[field]}"

        # MinIO 布尔字段
        assert 'minio_secure' in settings_hints
        assert 'bool' in str(settings_hints['minio_secure']), \
            f"minio_secure 应该是布尔类型，当前是: {settings_hints['minio_secure']}"

        # MinIO 数值字段
        assert 'minio_connect_timeout' in settings_hints
        assert 'float' in str(settings_hints['minio_connect_timeout']).lower(), \
            f"minio_connect_timeout 应该是 float 类型"

        assert 'minio_read_timeout' in settings_hints
        assert 'float' in str(settings_hints['minio_read_timeout']).lower(), \
            f"minio_read_timeout 应该是 float 类型"

        assert 'minio_max_pool_size' in settings_hints
        assert 'int' in str(settings_hints['minio_max_pool_size']).lower(), \
            f"minio_max_pool_size 应该是 int 类型"

        # HuaweiOBS 字段类型检查
        obs_string_fields = [
            'obs_access_key', 'obs_secret_key', 'obs_endpoint',
            'obs_bucket', 'obs_domain_name'
        ]
        for field in obs_string_fields:
            assert field in settings_hints, f"Settings 缺少字段: {field}"
            assert 'str' in str(settings_hints[field]), \
                f"字段 {field} 应该是字符串类型，当前是: {settings_hints[field]}"


class TestGlobalConfigInstance:
    """测试全局配置实例"""

    def test_web_configs_global_instance_accessible(self):
        """WEB_CONFIGS 全局实例应该可以正常访问"""
        try:
            from utils.web_configs import WEB_CONFIGS
            assert WEB_CONFIGS is not None
            assert isinstance(WEB_CONFIGS, WebConfigs)
        except Exception as e:
            pytest.fail(f"WEB_CONFIGS 全局实例访问失败: {e}")

    def test_web_configs_used_by_storage_classes(self):
        """
        验证存储类使用 WEB_CONFIGS 的方式是安全的

        存储类应该使用 getattr() 或 hasattr() 来安全访问可能不存在的配置
        而不是直接属性访问（会抛出 AttributeError）
        """
        from utils.web_configs import WEB_CONFIGS

        # 测试 MinIO 配置访问
        try:
            endpoint = getattr(WEB_CONFIGS, 'MINIO_ENDPOINT', None)
            access_key = getattr(WEB_CONFIGS, 'MINIO_ACCESS_KEY', None)
            secret_key = getattr(WEB_CONFIGS, 'MINIO_SECRET_KEY', None)
            # 这些可以是 None（未配置）
        except AttributeError as e:
            pytest.fail(f"MinIO 配置访问失败: {e}")

        # 测试华为云 OBS 配置访问
        try:
            access_key_id = getattr(WEB_CONFIGS, 'ACCESS_KEY_ID', None)
            secret_access_key = getattr(WEB_CONFIGS, 'SECRET_ACCESS_KEY', None)
            endpoint = getattr(WEB_CONFIGS, 'ENDPOINT', None)
            bucket = getattr(WEB_CONFIGS, 'BUCKET_NAME', None)
            domain = getattr(WEB_CONFIGS, 'DOMAIN_NAME', None)
        except AttributeError as e:
            pytest.fail(f"华为云 OBS 配置访问失败: {e}")


class TestConfigDocumentation:
    """测试配置文档完整性"""

    def test_env_example_covers_storage_fields(self):
        """验证 .env.example 文档覆盖所有存储相关字段"""
        # 读取 .env.example (从项目根目录)
        with open('.env.example', 'r', encoding='utf-8') as f:
            env_example_content = f.read()

        # 核心存储字段（必须在文档中）
        required_storage_fields = [
            # 通用
            'STORAGE_TYPE',
            # MinIO
            'MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY',
            'MINIO_BUCKET_NAME', 'MINIO_SECURE', 'MINIO_DOMAIN_NAME',
            'MINIO_CONNECT_TIMEOUT', 'MINIO_READ_TIMEOUT', 'MINIO_MAX_POOL_SIZE',
            # HuaweiOBS
            'OBS_ACCESS_KEY', 'OBS_SECRET_KEY', 'OBS_ENDPOINT',
            'OBS_BUCKET', 'OBS_DOMAIN_NAME',
        ]

        missing_docs = []
        for env_var in required_storage_fields:
            if env_var not in env_example_content:
                missing_docs.append(env_var)

        assert not missing_docs, \
            f".env.example 缺少以下配置字段的文档: {', '.join(missing_docs)}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
