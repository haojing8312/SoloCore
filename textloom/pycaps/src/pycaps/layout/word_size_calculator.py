from pycaps.common import Document, ElementState
from pycaps.renderer import CssSubtitleRenderer

class WordSizeCalculator:
    def __init__(self, renderer: CssSubtitleRenderer):
        self._renderer = renderer

    def calculate(self, document: Document) -> None:
        for word in document.get_words():
            max_width = 0
            max_height = 0
            for line_state, word_state in ElementState.get_all_valid_states_combinations():
                w, h = self._renderer.get_word_size(word, line_state, word_state)
                if w <= 0 or h <= 0:
                    continue
                max_width = max(max_width, w)
                max_height = max(max_height, h)
            word.max_layout.size.width = max_width
            word.max_layout.size.height = max_height
