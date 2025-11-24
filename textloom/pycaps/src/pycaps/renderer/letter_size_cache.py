from typing import Dict
from pycaps.common import Size

class LetterSizeCache:
    def __init__(self, css_content: str):
        self._css_content = css_content
        self._cache: Dict[str, Size] = {}

    def get(self, letter, css_classes: str) -> Size:
        key = self.__build_key(letter, css_classes)
        if key not in self._cache:
            raise RuntimeError(f"{letter} with classes {css_classes} is not cached")
        return self._cache[key]
    
    def has(self, letter, css_classes: str) -> bool:
        key = self.__build_key(letter, css_classes)
        return key in self._cache
    
    def set_all(self, data: Dict[str, Size], css_classes: str) -> None:
        for letter, size in data.items():
            key = self.__build_key(letter, css_classes)
            self._cache[key] = size

    def __build_key(self, letter: str, css_classes: str) -> str:
        used_css_classes = [c for c in css_classes.split() if c in self._css_content]
        return f"letter:{letter}|css_classes:{','.join(used_css_classes)}"
