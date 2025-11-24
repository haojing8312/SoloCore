from .base_segment_splitter import BaseSegmentSplitter
from pycaps.common import Document, Segment, Line, TimeFragment

class LimitByWordsSplitter(BaseSegmentSplitter):
    """
    A segment splitter that limits the number of words in each segment.
    It will divide each segment received into chunks of a maximum of `limit` words.
    If the last chunk generated has less than `limit` words, it will not use the next segment for completion.

    For example,
    limit = 3
    segment 1: "Hello world"
    segment 2: "This is a test"

    The splitter will return:
    segment 1: "Hello world"
    segment 2: "This is a"
    segment 3: "test"
    """
    def __init__(self, limit: int):
        self.limit = limit

    def split(self, document: Document) -> None:
        new_segments = []
        segment_index = 0
        word_index = 0
        segments = document.segments
        while segment_index < len(segments):
            segment = segments[segment_index]
            segment_words = segment.lines[0].words
            current_words = segment_words[word_index:word_index + self.limit]
            if len(current_words) == 0:
                segment_index += 1
                word_index = 0
                continue

            segment_time = TimeFragment(start=current_words[0].time.start, end=current_words[-1].time.end)
            new_segment = Segment(time=segment_time)
            new_line = Line(time=segment_time)
            new_line.words.set_all(current_words)
            new_segment.lines.add(new_line)
            new_segments.append(new_segment)
            word_index += self.limit

        document.segments.set_all(new_segments)
