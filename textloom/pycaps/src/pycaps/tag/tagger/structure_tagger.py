from typing import Callable, Dict, Union
from pycaps.common import Word, Document, Tag, Line, Segment
from pycaps.tag import BuiltinTag

class StructureTagger:
    '''
    It allows to register rules to tag elements based on their structure in the document.
    Then, the tagger will tag the elements that match the rules.

    These tags can be recalculated if the document structure changes.
    For example, when the user edits the transcription.
    '''

    def __init__(self):
        self._rules: Dict[Tag, Callable[[Document], list[Union[Word, Line, Segment]]]] = {}
        self._add_builtin_tags()

    def add_rule(self, tag: Tag, get_elements_to_tag: Callable[[Document], list[Union[Word, Line, Segment]]]) -> None:
        """Register a new rule. The function receives the document and returns a list of elements that should be tagged."""
        self._rules[tag] = get_elements_to_tag

    def tag(self, document: Document) -> None:
        """Apply all registered rules to the document."""
        for tag, get_elements_to_tag in self._rules.items():
            for element in get_elements_to_tag(document):
                element.structure_tags.add(tag)

    def clear(self, document: Document) -> None:
        """Removes all the structure tags in the document"""
        for segment in document.segments:
            segment.structure_tags.clear()
            for line in segment.lines:
                line.structure_tags.clear()
                for word in line.words:
                    word.structure_tags.clear()

    def _add_builtin_tags(self) -> None:
        self.add_rule(BuiltinTag.FIRST_WORD_IN_DOCUMENT, lambda document: [document.segments[0].lines[0].words[0]])
        self.add_rule(BuiltinTag.FIRST_WORD_IN_SEGMENT, lambda document: [segment.lines[0].words[0] for segment in document.segments])
        self.add_rule(BuiltinTag.FIRST_WORD_IN_LINE, lambda document: [line.words[0] for line in document.get_lines()])
        self.add_rule(BuiltinTag.LAST_WORD_IN_DOCUMENT, lambda document: [document.segments[-1].lines[-1].words[-1]])
        self.add_rule(BuiltinTag.LAST_WORD_IN_SEGMENT, lambda document: [segment.lines[-1].words[-1] for segment in document.segments])
        self.add_rule(BuiltinTag.LAST_WORD_IN_LINE, lambda document: [line.words[-1] for line in document.get_lines()])

        self.add_rule(BuiltinTag.FIRST_LINE_IN_DOCUMENT, lambda document: [document.segments[0].lines[0]])
        self.add_rule(BuiltinTag.FIRST_LINE_IN_SEGMENT, lambda document: [segment.lines[0] for segment in document.segments])
        self.add_rule(BuiltinTag.LAST_LINE_IN_DOCUMENT, lambda document: [document.segments[-1].lines[-1]])
        self.add_rule(BuiltinTag.LAST_LINE_IN_SEGMENT, lambda document: [segment.lines[-1] for segment in document.segments])

        self.add_rule(BuiltinTag.FIRST_SEGMENT_IN_DOCUMENT, lambda document: [document.segments[0]])
        self.add_rule(BuiltinTag.LAST_SEGMENT_IN_DOCUMENT, lambda document: [document.segments[-1]])
