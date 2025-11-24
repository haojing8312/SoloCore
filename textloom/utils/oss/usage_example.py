import asyncio
import os

from utils.oss.storage_factory import StorageFactory


def sync_example():
    """同步操作示例"""
    print("===== 同步操作示例 =====")

    # 获取配置的存储服务
    storage = StorageFactory.get_storage()

    # 创建测试文件
    test_file = "test_upload.txt"
    with open(test_file, "w") as f:
        f.write("这是一个测试文件内容")

    try:
        # 上传文件
        print("上传文件...")
        file_url = storage.upload_file(test_file)
        print(f"文件的URL: {file_url}")

        # 检查文件是否存在
        object_key = os.path.basename(test_file)
        if storage.file_exists(object_key):
            print(f"文件 {object_key} 存在")
        else:
            print(f"文件 {object_key} 不存在")

        # 列出文件
        print("列出文件:")
        try:
            files = storage.list_files()
            for i, file in enumerate(files[:5]):  # 只显示前5个文件
                print(f"  {i+1}. {getattr(file, 'key', file)}")
        except NotImplementedError:
            print("  当前存储服务不支持列出文件")

        # 下载文件
        download_path = "test_download.txt"
        print(f"下载文件到 {download_path}...")
        storage.download_file(object_key, download_path)

        # 验证下载的文件内容
        with open(download_path, "r") as f:
            content = f.read()
        print(f"下载的文件内容: {content}")

        # 删除文件
        try:
            print("删除文件...")
            storage.delete_file(object_key)
            print(f"文件 {object_key} 已删除")
        except NotImplementedError:
            print("当前存储服务不支持删除文件")

    except Exception as e:
        print(f"操作失败: {e}")
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
        if os.path.exists(download_path):
            os.remove(download_path)


async def async_example():
    """异步操作示例"""
    print("\n===== 异步操作示例 =====")

    try:
        # 获取异步存储服务
        async_storage = StorageFactory.get_async_storage()

        # 创建测试文件
        test_file = "test_upload_async.txt"
        with open(test_file, "w") as f:
            f.write("这是一个异步测试文件内容")

        # 异步上传文件
        print("异步上传文件...")
        file_url = await async_storage.upload_file_async(test_file)
        print(f"文件的URL: {file_url}")

        # 异步下载文件
        object_key = os.path.basename(test_file)
        download_path = "test_download_async.txt"
        print(f"异步下载文件到 {download_path}...")
        await async_storage.download_file_async(object_key, download_path)

        # 验证下载的文件内容
        with open(download_path, "r") as f:
            content = f.read()
        print(f"下载的文件内容: {content}")

        # 删除文件
        print("删除文件...")
        async_storage.delete_file(object_key)
        print(f"文件 {object_key} 已删除")

    except ValueError as e:
        print(f"当前配置的存储服务不支持异步操作: {e}")
    except Exception as e:
        print(f"异步操作失败: {e}")
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
        if os.path.exists(download_path):
            os.remove(download_path)


def switch_storage_example():
    """切换存储服务示例"""
    print("\n===== 切换存储服务示例 =====")

    try:
        # 使用华为云OBS
        print("使用华为云OBS:")
        huawei_storage = StorageFactory.get_storage_by_type("huawei_obs")
        print(f"存储服务类型: {huawei_storage.__class__.__name__}")

        # 使用MinIO
        print("使用MinIO:")
        minio_storage = StorageFactory.get_storage_by_type("minio")
        print(f"存储服务类型: {minio_storage.__class__.__name__}")

    except Exception as e:
        print(f"切换存储服务失败: {e}")


if __name__ == "__main__":
    # 运行同步示例
    sync_example()

    # 运行异步示例
    asyncio.run(async_example())

    # 运行切换存储服务示例
    switch_storage_example()
