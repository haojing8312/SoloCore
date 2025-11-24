from .text_effect import TextEffect
from pycaps.common import Document, Word
from pycaps.tag import TagCondition
from typing import Callable, Optional

class ModifyWordsEffect(TextEffect):
    """
    Effect that applies a custom modification to each word that matches a given tag condition.

    This is useful to programmatically tweak visual properties (generally text), add metadata, or preprocess words
    before rendering or animation steps.

    Example:
        effect = ModifyWordsEffect(
            condition=TagCondition("highlight"),
            modifier=lambda word: setattr(word, "text", "$" + word.text + "$")
        )
    """
    def __init__(self, modifier: Callable[[Word], None], tag_condition: Optional[TagCondition] = None):
        self.modifier = modifier
        self.tag_condition = tag_condition

    def run(self, document: Document) -> None:
        for word in document.get_words():
            if self.tag_condition and self.tag_condition.evaluate(list(word.get_all_tags_in_document())):
                self.modifier(word)
