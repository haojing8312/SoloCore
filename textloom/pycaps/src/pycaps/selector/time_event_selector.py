from typing import List, Union
from pycaps.common import ElementType, EventType, Word, Line, Segment, WordClip
from pycaps.utils import times_intersect

class TimeEventSelector:
    """
    Selects WordClips whose clips intersect a time window relative to a narration event
    (start or end) of a given element (word, line, or segment).

    Parameters:
        event_type: EventType.STARTS_NARRATION or EventType.ENDS_NARRATION
        element_type: the scope of the event (ElementType.WORD, LINE or SEGMENT)
        duration: duration of the time window
        delay: offset from the event before the window starts

    Example:
        TimeEventSelector(EventType.STARTS_NARRATION, ElementType.SEGMENT, duration=10, delay=2)
        → selects all WordClips whose clip intersects [segment.start + 2, segment.start + 12]
    """

    def __init__(self, event_type: EventType, element_type: ElementType, duration: float, delay: float) -> None:
        self._event_type = event_type
        self._element_type = element_type
        self._duration = duration
        self._delay = delay

    def select(self, clips: List[WordClip]) -> List[WordClip]:
        match self._element_type:
            case ElementType.WORD:
                return self.__filter_by_words(clips)
            case ElementType.LINE:
                return self.__filter_by_lines(clips)
            case ElementType.SEGMENT:
                return self.__filter_by_segments(clips)

    def __get_event_time_range(self, element: Union[Word, Line, Segment]) -> tuple[float, float]:
        if self._event_type == EventType.ON_NARRATION_STARTS:
            start = element.time.start + self._delay
        else:  # ENDS_NARRATION
            start = element.time.end - self._delay - self._duration
        end = start + self._duration
        return start, end

    def __filter_by_words(self, clips: List[WordClip]) -> List[WordClip]:
        return [
            clip for clip in clips
            if times_intersect(
                *self.__get_event_time_range(clip.get_word()),
                clip.media_clip.start,
                clip.media_clip.end
            )
        ]

    def __filter_by_lines(self, clips: List[WordClip]) -> List[WordClip]:
        return [
            clip for clip in clips
            if times_intersect(
                *self.__get_event_time_range(clip.get_line()),
                clip.media_clip.start,
                clip.media_clip.end
            )
        ]

    def __filter_by_segments(self, clips: List[WordClip]) -> List[WordClip]:
        return [
            clip for clip in clips
            if times_intersect(
                *self.__get_event_time_range(clip.get_segment()),
                clip.media_clip.start,
                clip.media_clip.end
            )
        ]
