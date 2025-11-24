from .definitions import SubtitleLayoutOptions
from pycaps.common import Document
from math import inf

class LayoutUpdater:
    def __init__(self, layout_options: SubtitleLayoutOptions):
        self._options = layout_options

    def update_max_sizes(self, document: Document) -> None:
        """
        Refreshes the words, lines and segments max sizes, using the word clips sizes as reference.
        """
        for segment in document.segments:
            segment_width = 0
            segment_height = 0
            for line in segment.lines:
                line_width = 0
                line_height = 0
                for word in line.words:
                    word.max_layout.size.width = max(clip.layout.size.width for clip in word.clips)
                    word.max_layout.size.height = max(clip.layout.size.height for clip in word.clips)
                    line_width += word.max_layout.size.width + self._options.x_words_space
                    line_height = max(line_height, word.max_layout.size.height + self._options.y_words_space)

                line.max_layout.size.width = line_width
                line.max_layout.size.height = line_height
                segment_width = max(segment_width, line_width)
                segment_height += line_height

            segment.max_layout.size.width = segment_width
            segment.max_layout.size.height = segment_height

    def update_max_positions(self, document: Document) -> None:
        '''
        Refreshes the words, lines and segments max positions, using the word clips positions as reference.
        '''
        for segment in document.segments:
            segment_x = inf
            segment_y = inf
            for line in segment.lines:
                line_x = inf
                line_y = inf
                for word in line.words:
                    word.max_layout.position.x = min(clip.layout.position.x for clip in word.clips)
                    word.max_layout.position.y = min(clip.layout.position.y for clip in word.clips)
                    line_x = min(line_x, word.max_layout.position.x)
                    line_y = min(line_y, word.max_layout.position.y)

                line.max_layout.position.x = line_x
                line.max_layout.position.y = line_y
                segment_x = min(segment_x, line_x)
                segment_y = min(segment_y, line_y)

            segment.max_layout.position.x = segment_x
            segment.max_layout.position.y = segment_y