from .template import Template
import importlib.resources as resources
from .constants import BUILTIN_TEMPLATES_PACKAGE, CONFIG_FILE_NAME

class BuiltinTemplate(Template):

    def get_json_path(self) -> str:
        template_path = resources.files(BUILTIN_TEMPLATES_PACKAGE).joinpath(self._name)
        config_path = template_path.joinpath(CONFIG_FILE_NAME)
        return config_path.as_posix()
