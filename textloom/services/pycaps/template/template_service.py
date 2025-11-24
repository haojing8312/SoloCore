import os
import importlib.resources as resources
from .constants import BUILTIN_TEMPLATES_PACKAGE, CONFIG_FILE_NAME

class TemplateService:
    def list_builtin_templates(self) -> list[str]:
        template_path = resources.files(BUILTIN_TEMPLATES_PACKAGE)
        return [p.name for p in template_path.iterdir() if p.is_dir()]

    def list_local_templates(self) -> list[str]:
        return [d for d in os.listdir(os.getcwd()) if self.is_valid_local_template(d)]

    def is_valid_local_template(self, name: str) -> bool:
        path = os.path.join(os.getcwd(), name) 
        return os.path.isdir(path) and os.path.isfile(os.path.join(path, CONFIG_FILE_NAME))

    def is_valid_builtin_template(self, name: str) -> bool:
        try:
            return resources.files(BUILTIN_TEMPLATES_PACKAGE + "." + name).is_dir()
        except:
            return False
