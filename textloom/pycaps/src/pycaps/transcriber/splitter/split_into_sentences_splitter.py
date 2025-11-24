from .base_segment_splitter import BaseSegmentSplitter
from pycaps.common import Document, Segment, Word, TimeFragment, Line

class SplitIntoSentencesSplitter(BaseSegmentSplitter):
    """
    A segment splitter that splits each segment into sentences using the given separators.
    """
    def __init__(self, sentences_separators: list[str] = ['.', '?', '!', '...']):
        self._sentences_separators = sentences_separators

    def split(self, document: Document) -> None:
        sentences: list[list[Word]] = []
        current_sentence: list[Word] = []
        for segment in document.segments:
            for word in segment.get_words():
                current_sentence.append(word)
                if word.text.endswith(tuple(self._sentences_separators)):
                    sentences.append(current_sentence)
                    current_sentence = []

        if current_sentence:
            sentences.append(current_sentence)

        new_segments = []
        for sentence in sentences:
            time = TimeFragment(start=sentence[0].time.start, end=sentence[-1].time.end)
            new_segment = Segment(time=time)
            new_line = Line(time=time)
            new_line.words.set_all(sentence)
            new_segment.lines.add(new_line)
            new_segments.append(new_segment)

        document.segments.set_all(new_segments)
