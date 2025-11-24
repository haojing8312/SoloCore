import argparse

from utils.oss.storage_factory import StorageFactory
from utils.web_configs import WEB_CONFIGS


def switch_storage(storage_type):
    """
    切换存储类型

    Args:
        storage_type: 存储类型，可选值：huawei_obs, minio
    """
    # 获取当前存储类型
    current_type = getattr(WEB_CONFIGS, "STORAGE_TYPE", "huawei_obs").lower()

    print(f"当前存储类型: {current_type}")
    print(f"切换到存储类型: {storage_type}")

    # 检查目标存储类型是否受支持
    try:
        test_storage = StorageFactory.get_storage_by_type(storage_type)
        print(
            f"目标存储类型 {storage_type} 已验证，实例类型: {test_storage.__class__.__name__}"
        )
    except ValueError as e:
        print(f"错误: {e}")
        return False

    # 修改配置文件
    try:
        # 读取配置文件
        with open("utils/web_configs.py", "r", encoding="utf-8") as f:
            config_content = f.read()

        # 替换存储类型
        if f'STORAGE_TYPE: str = "{current_type}"' in config_content:
            new_content = config_content.replace(
                f'STORAGE_TYPE: str = "{current_type}"',
                f'STORAGE_TYPE: str = "{storage_type}"',
            )
        else:
            print("无法在配置文件中找到STORAGE_TYPE配置项")
            return False

        # 写入配置文件
        with open("utils/web_configs.py", "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"存储类型已成功切换为 {storage_type}")
        print("请重启应用程序以应用更改")
        return True

    except Exception as e:
        print(f"切换存储类型时出错: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="切换存储类型")
    parser.add_argument(
        "type",
        choices=["huawei_obs", "minio"],
        help="存储类型，可选值：huawei_obs, minio",
    )

    args = parser.parse_args()
    switch_storage(args.type)
