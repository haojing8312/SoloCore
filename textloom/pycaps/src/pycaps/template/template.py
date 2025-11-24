from abc import ABC, abstractmethod
import os

class Template(ABC):

    def __init__(self, name: str):
        self._name = name

    @abstractmethod
    def get_json_path(self) -> str:
        pass

    def get_folder_path(self) -> str:
        return os.path.dirname(self.get_json_path())
