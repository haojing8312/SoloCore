import os

class Sound:
    def __init__(self, name: str, file_path: str):
        self._name = name
        self._file_path = file_path

        if not os.path.exists(self._file_path):
            raise FileNotFoundError(f"Sound file not found: {self._file_path}")

    def get_name(self) -> str:
        return self._name

    def get_file_path(self) -> str:
        return self._file_path
