from ..effect import Effect
from pycaps.renderer import CssSubtitleRenderer

class ClipEffect(Effect):
    def set_renderer(self, renderer: CssSubtitleRenderer) -> None:
        self._renderer = renderer
