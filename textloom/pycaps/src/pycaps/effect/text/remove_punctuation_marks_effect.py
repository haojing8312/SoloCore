from .text_effect import TextEffect
from pycaps.common import Document, Word
import re

class RemovePunctuationMarksEffect(TextEffect):
    '''
    This effect removes punctuation marks from the words.
    It can also receive a list of exceptions, which are punctuation marks that will not be removed.
    For example, if you want to remove the punctuation marks from the words, but not the ellipsis, you can use:
    ```python
    RemovePunctuationMarksEffect(punctuation_marks=['.'], exception_marks=['...'])
    ```
    '''
    def __init__(self, punctuation_marks: list[str] = ['.'], exception_marks: list[str] = ['...']):
        self._punctuation_marks = sorted(punctuation_marks, key=len, reverse=True)
        self._exception_marks = sorted(exception_marks, key=len, reverse=True)

    def run(self, document: Document) -> None:
        for word in document.get_words():
            text = word.text
            placeholder_prefix = "⟨EXC"  # Use rare Unicode character for safety
            placeholders = []

            # Step 1: Temporarily remove exceptions and store positions
            for exc in self._exception_marks:
                pattern = re.escape(exc)
                def _replacer(match):
                    placeholder = f"{placeholder_prefix}{len(placeholders)}⟩"
                    placeholders.append((placeholder, match.group(0), match.start()))
                    return placeholder
                text = re.sub(pattern, _replacer, text)

            # Step 2: Remove all punctuation marks
            for mark in self._punctuation_marks:
                text = text.replace(mark, '')

            # Step 3: Re-insert exceptions at correct placeholder positions
            for placeholder, value, _ in placeholders:
                text = text.replace(placeholder, value)

            word.text = text
