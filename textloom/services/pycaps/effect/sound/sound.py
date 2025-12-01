import os

class Sound:
    def __init__(self, name: str, file_path: str, validate_on_init: bool = False):
        """初始化音效对象

        Args:
            name: 音效名称
            file_path: 音效文件路径
            validate_on_init: 是否在初始化时验证文件存在（默认False，延迟到使用时验证）
        """
        self._name = name
        self._file_path = file_path

        # 只在明确要求时才在初始化时验证
        if validate_on_init and not os.path.exists(self._file_path):
            raise FileNotFoundError(f"Sound file not found: {self._file_path}")

    def get_name(self) -> str:
        return self._name

    def get_file_path(self) -> str:
        """获取音效文件路径，并验证文件存在"""
        if not os.path.exists(self._file_path):
            raise FileNotFoundError(f"Sound file not found: {self._file_path}")
        return self._file_path

    def exists(self) -> bool:
        """检查音效文件是否存在"""
        return os.path.exists(self._file_path)
