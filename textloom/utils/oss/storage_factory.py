from utils.oss.HuaweiCloudOBS import HuaweiCloudOBS
from utils.oss.MinioStorage import MinioStorage
from utils.oss.MinioStorageAsync import MinioStorageAsync
from utils.oss.storage_interface import ObjectStorage
from utils.web_configs import WEB_CONFIGS


class StorageFactory:
    """
    存储工厂类，根据配置创建合适的存储实现
    """

    @staticmethod
    def get_storage() -> ObjectStorage:
        """
        根据配置获取存储实例

        Returns:
            ObjectStorage: 存储实例
        """
        storage_type = getattr(WEB_CONFIGS, "STORAGE_TYPE", "huawei_obs").lower()

        if storage_type == "huawei_obs":
            return HuaweiCloudOBS()
        elif storage_type == "minio":
            return MinioStorage()
        else:
            raise ValueError(f"不支持的存储类型: {storage_type}")

    @staticmethod
    def get_storage_by_type(storage_type: str) -> ObjectStorage:
        """
        根据指定的类型获取存储实例

        Args:
            storage_type: 存储类型，如 "huawei_obs", "minio"

        Returns:
            ObjectStorage: 存储实例
        """
        storage_type = storage_type.lower()

        if storage_type == "huawei_obs":
            return HuaweiCloudOBS()
        elif storage_type == "minio":
            return MinioStorage()
        else:
            raise ValueError(f"不支持的存储类型: {storage_type}")

    @staticmethod
    def get_async_storage() -> ObjectStorage:
        """
        获取异步存储实例（如果支持）

        Returns:
            ObjectStorage: 支持异步操作的存储实例
        """
        storage_type = getattr(WEB_CONFIGS, "STORAGE_TYPE", "huawei_obs").lower()

        if storage_type == "minio":
            return MinioStorageAsync()
        else:
            raise ValueError(f"存储类型 {storage_type} 不支持异步操作")

    @staticmethod
    def get_async_storage_by_type(storage_type: str) -> ObjectStorage:
        """
        根据指定的类型获取异步存储实例（如果支持）

        Args:
            storage_type: 存储类型，如 "minio"

        Returns:
            ObjectStorage: 支持异步操作的存储实例
        """
        storage_type = storage_type.lower()

        if storage_type == "minio":
            return MinioStorageAsync()
        else:
            raise ValueError(f"存储类型 {storage_type} 不支持异步操作")


# 使用示例
if __name__ == "__main__":
    # 根据配置获取存储实例
    storage = StorageFactory.get_storage()

    # 使用存储实例
    file_path = "path/to/your/local/file.txt"
    try:
        file_url = storage.upload_file(file_path)
        print(f"文件的URL: {file_url}")
    except Exception as e:
        print(str(e))

    # 显式指定存储类型
    huawei_storage = StorageFactory.get_storage_by_type("huawei_obs")
    minio_storage = StorageFactory.get_storage_by_type("minio")

    # 获取异步存储实例（如果支持）
    try:
        async_storage = StorageFactory.get_async_storage_by_type("minio")
        # 使用异步方法需要在异步环境中调用
        # await async_storage.upload_file_async(file_path)
    except ValueError as e:
        print(str(e))
