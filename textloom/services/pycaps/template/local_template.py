from .template import Template
import os
from .constants import CONFIG_FILE_NAME

class LocalTemplate(Template):

    def get_json_path(self) -> str:
        return os.path.join(os.getcwd(), self._name, CONFIG_FILE_NAME)
