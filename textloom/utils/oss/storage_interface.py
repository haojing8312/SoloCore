from abc import ABC, abstractmethod


class ObjectStorage(ABC):
    """
    对象存储抽象基类，定义所有存储服务都应实现的通用接口
    """

    @abstractmethod
    def upload_file(self, file_path, object_key=None):
        """
        上传文件到对象存储

        Args:
            file_path: 本地文件路径
            object_key: 对象键名，如果为None则使用文件名

        Returns:
            str: 上传后的文件URL
        """
        pass

    @abstractmethod
    def download_file(self, object_key, download_path):
        """
        从对象存储下载文件

        Args:
            object_key: 对象键名
            download_path: 下载保存的本地路径
        """
        pass

    # 扩展方法 - 这些是可选实现的新功能

    def delete_file(self, object_key):
        """
        删除对象存储中的文件

        Args:
            object_key: 对象键名

        Returns:
            bool: 删除是否成功
        """
        raise NotImplementedError("此存储服务未实现删除文件功能")

    def list_files(self, prefix="", max_keys=1000):
        """
        列出对象存储中的文件

        Args:
            prefix: 前缀过滤
            max_keys: 最大返回数量

        Returns:
            list: 文件对象列表
        """
        raise NotImplementedError("此存储服务未实现列出文件功能")

    def file_exists(self, object_key):
        """
        检查文件是否存在

        Args:
            object_key: 对象键名

        Returns:
            bool: 文件是否存在
        """
        raise NotImplementedError("此存储服务未实现检查文件是否存在功能")

    async def upload_file_async(self, file_path, object_key=None):
        """
        异步上传文件

        Args:
            file_path: 本地文件路径
            object_key: 对象键名，如果为None则使用文件名

        Returns:
            str: 上传后的文件URL
        """
        raise NotImplementedError("此存储服务未实现异步上传功能")

    async def download_file_async(self, object_key, download_path):
        """
        异步下载文件

        Args:
            object_key: 对象键名
            download_path: 下载保存的本地路径
        """
        raise NotImplementedError("此存储服务未实现异步下载功能")
