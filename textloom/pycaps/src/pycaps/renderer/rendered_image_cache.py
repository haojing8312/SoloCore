from typing import Optional, TYPE_CHECKING
from pycaps.common import CacheStrategy

if TYPE_CHECKING:
    from PIL.Image import Image

class RenderedImageCache:
    def __init__(self, css_content: str, cache_strategy: CacheStrategy):
        self._css_content = css_content
        self._cache_strategy = cache_strategy
        self._cache = {}

    def has(self, index: int, text: str, css_classes: str, first_n_letters: Optional[str]) -> bool:
        key = self.__build_key(index, text, css_classes, first_n_letters)
        return key in self._cache

    def get(self, index: int, text: str, css_classes: str, first_n_letters: Optional[str]) -> Optional['Image']:
        if not self.has(index, text, css_classes, first_n_letters):
            raise ValueError(f"No cached image found for text: {text} and CSS classes: {css_classes}")
        
        # Important, keep in mind that None is a valid cached value: it means that the image can't be generated (element probably hidden)
        key = self.__build_key(index, text, css_classes, first_n_letters)
        return self._cache.get(key)

    def set(self, index: int, text: str, css_classes: str, first_n_letters: Optional[str], image: Optional['Image']) -> None:
        if self._cache_strategy == CacheStrategy.NONE:
            return
        key = self.__build_key(index, text, css_classes, first_n_letters)
        self._cache[key] = image

    def __build_key(self, index: int, text: str, css_classes: str, first_n_letters: Optional[str]) -> str:
        if self._cache_strategy == CacheStrategy.CSS_CLASSES_AWARE:
            index = -1
        used_css_classes = [c for c in css_classes.split() if c in self._css_content]
        return f"word:{text}|index:{index}|first_{first_n_letters or -1}_letters|css_classes:{','.join(used_css_classes)}"
