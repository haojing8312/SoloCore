from typing import List, Callable
from pycaps.tag import TagCondition
from pycaps.common import ElementType, EventType, Document, WordClip
from .tag_based_selector import TagBasedSelector
from .time_event_selector import TimeEventSelector

class WordClipSelector:
    """
    A flexible and composable selector for WordClips, allowing filters
    by tag, time, or any other property.
    """
    def __init__(self):
        self._filters: List[Callable[[List[WordClip]], List[WordClip]]] = []

    def filter_by_tag(self, tag_condition: TagCondition) -> 'WordClipSelector':
        def filter_fn(clips: List[WordClip]) -> List[WordClip]:
            return TagBasedSelector(tag_condition).select(clips)
        self._filters.append(filter_fn)
        return self

    def filter_by_time(self, when: EventType, what: ElementType, duration: float, delay: float) -> 'WordClipSelector':
        def filter_fn(clips: List[WordClip]) -> List[WordClip]:
            return TimeEventSelector(when, what, duration, delay).select(clips)
        self._filters.append(filter_fn)
        return self

    def select(self, document: Document) -> List[WordClip]:
        result = document.get_word_clips()
        for f in self._filters:
            result = f(result)
        return result
