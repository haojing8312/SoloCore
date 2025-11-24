from ..pipeline.json_config_loader import JsonConfigLoader
from typing import overload, Literal, Optional
from pycaps.pipeline import CapsPipeline, CapsPipelineBuilder
from .template import Template
from .template_factory import TemplateFactory

class TemplateLoader:

    def __init__(self, template: Template|str):
        self._template: Template = TemplateFactory().create(template) if type(template) == str else template
        self._input_video_path: Optional[str] = None

    def with_input_video(self, input_video_path: str) -> "TemplateLoader":
        self._input_video_path = input_video_path
        return self

    @overload
    def load(self, should_build_pipeline: Literal[True] = True) -> CapsPipeline:
        ...
    @overload
    def load(self, should_build_pipeline: Literal[False]) -> CapsPipelineBuilder:
        ...
    def load(self, should_build_pipeline: bool = True) -> CapsPipeline | CapsPipelineBuilder:
        json_config_loader = JsonConfigLoader(self._template.get_json_path())
        builder = json_config_loader.load(False)
        if self._input_video_path:
            builder.with_input_video(self._input_video_path)
        if should_build_pipeline:
            return builder.build()
        return builder
    