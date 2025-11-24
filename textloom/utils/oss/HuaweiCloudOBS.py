import os

from obs import ObsClient

from utils.oss.storage_interface import ObjectStorage
from utils.web_configs import WEB_CONFIGS


class HuaweiCloudOBS(ObjectStorage):
    def __init__(self):
        self.client = ObsClient(
            access_key_id=WEB_CONFIGS.ACCESS_KEY_ID,
            secret_access_key=WEB_CONFIGS.SECRET_ACCESS_KEY,
            server=WEB_CONFIGS.ENDPOINT,
            timeout=10,  # 设置超时时间（单位：秒）
        )
        self.bucket_name = WEB_CONFIGS.BUCKET_NAME
        self.domain_name = WEB_CONFIGS.DOMAIN_NAME

    def upload_file(self, file_path, object_key=None):
        """上传文件到OBS，并返回文件的URL"""
        if object_key is None:
            object_key = os.path.basename(file_path)

        resp = self.client.putFile(self.bucket_name, object_key, file_path)

        if resp.status < 300:
            print(f"文件上传成功，ObjectKey: {object_key}")
            url = f"https://{self.domain_name}/{object_key}"
            return url
        else:
            raise Exception(
                f"文件上传失败，状态码: {resp.status}, 错误信息: {resp.errorMessage}"
            )

    def download_file(self, object_key, download_path):
        """通过文件的对象键从OBS下载文件"""
        resp = self.client.getObject(self.bucket_name, object_key, download_path)

        if resp.status < 300:
            print(f"文件下载成功，保存到: {download_path}")
        else:
            raise Exception(
                f"文件下载失败，状态码: {resp.status}, 错误信息: {resp.errorMessage}"
            )

    # 实现扩展方法
    def delete_file(self, object_key):
        """删除OBS中的文件"""
        resp = self.client.deleteObject(self.bucket_name, object_key)

        if resp.status < 300:
            print(f"文件删除成功，ObjectKey: {object_key}")
            return True
        else:
            raise Exception(
                f"文件删除失败，状态码: {resp.status}, 错误信息: {resp.errorMessage}"
            )

    def list_files(self, prefix="", max_keys=1000):
        """列出OBS中的文件"""
        resp = self.client.listObjects(
            self.bucket_name, prefix=prefix, max_keys=max_keys
        )

        if resp.status < 300:
            return resp.body.contents
        else:
            raise Exception(
                f"列出文件失败，状态码: {resp.status}, 错误信息: {resp.errorMessage}"
            )

    def file_exists(self, object_key):
        """检查文件是否存在于OBS中"""
        resp = self.client.getObjectMetadata(self.bucket_name, object_key)

        return resp.status < 300


# 使用示例
if __name__ == "__main__":
    # 请替换为你的华为云访问密钥和秘钥
    ACCESS_KEY_ID = WEB_CONFIGS.ACCESS_KEY_ID
    SECRET_ACCESS_KEY = WEB_CONFIGS.SECRET_ACCESS_KEY
    ENDPOINT = WEB_CONFIGS.ENDPOINT
    BUCKET_NAME = WEB_CONFIGS.BUCKET_NAME
    DOMAIN_NAME = WEB_CONFIGS.DOMAIN_NAME

    obs = HuaweiCloudOBS()

    # 上传文件
    file_path = "path/to/your/local/file.txt"
    try:
        file_url = obs.upload_file(file_path)
        print(f"文件的URL: {file_url}")
    except Exception as e:
        print(str(e))

    # 下载文件
    object_key = "file.txt"  # 上传时使用的对象键
    download_path = "path/to/save/file.txt"
    try:
        obs.download_file(object_key, download_path)
    except Exception as e:
        print(str(e))
