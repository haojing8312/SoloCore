from .template import Template
from .local_template import LocalTemplate
from .builtin_template import BuiltinTemplate
from .template_service import TemplateService

class TemplateFactory:

    def __init__(self):
        self._template_service = TemplateService()

    def create(self, name: str) -> Template:
        if self._template_service.is_valid_local_template(name):
            return LocalTemplate(name)
        elif self._template_service.is_valid_builtin_template(name):
            return BuiltinTemplate(name)
        
        raise RuntimeError(f"Template '{name}' not found")
