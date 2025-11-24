from typing import List, Optional
from pycaps.common import ElementState, Document, Segment, Line
from .layout_utils import LayoutUtils
from .definitions import SubtitleLayoutOptions

class PositionsCalculator:
    def __init__(self, layout_options: SubtitleLayoutOptions):
        self._options = layout_options

    def calculate(self, document: Document, video_width: int, video_height: int) -> None:
        """
        Calculates the positions of the words in the document.
        """
        for segment in document.segments:
            self.update_words_positions_in_segment(segment, video_width, video_height)
    
    # I'm not sure if this is the best approach, but it is good enough for now.
    def update_words_positions_in_segment(
            self,
            segment: Segment,
            video_width: int,
            video_height: int,
        ) -> None:
        y = self._calculate_base_y_position(segment, video_height)

        for line in segment.lines:
            if self._is_stable_line(line):
                for state in ElementState.get_all_line_states():
                    words_width = self._get_words_width_for_line_state(line, state)
                    if words_width is None:
                        continue
                    self._set_clip_positions(line, words_width, y, video_width, state)
            else:
                word_widths = [word.max_layout.size.width for word in line.words]
                self._set_clip_positions(line, word_widths, y, video_width)

            y += line.max_layout.size.height + self._options.y_words_space

    def _set_clip_positions(
            self,
            line: Line,
            words_width: List[int],
            y: int,
            video_width: int,
            state: Optional[ElementState] = None,
        ) -> None:
        line_width = sum(words_width) + (len(words_width) - 1) * self._options.x_words_space
        start_x_for_line = (video_width - line_width) // 2
        slot_x = start_x_for_line
        for i, word in enumerate(line.words):
            slot_width = words_width[i]
            for clip in word.clips:
                if state is None or state in clip.states:
                    # the clip is located in the center of the slot
                    clip.layout.position.x = slot_x + (slot_width - clip.layout.size.width) // 2
                    clip.layout.position.y = y + (line.max_layout.size.height - clip.layout.size.height) // 2
                    clip.media_clip.set_position((clip.layout.position.x, clip.layout.position.y))

            slot_x += slot_width + self._options.x_words_space

    def _is_stable_line(self, line: Line) -> bool:
        '''
        Returns True if the line is stable, False otherwise.
        A stable line is a line where all the clips for each word for a line state have the same width.
        For example,
        line state: "being narrated"
        if the word "hello" has a clip with width 100px when being narrated and 50px when not being narrated,
        the line is not stable.
        '''
        line_states_that_support_words_in_multiple_states = [ElementState.LINE_BEING_NARRATED]
        for state in line_states_that_support_words_in_multiple_states:
            for word in line.words:
                last_clip_width = None
                for clip in word.clips:
                    if state in clip.states:
                        if last_clip_width is None:
                            last_clip_width = clip.layout.size.width
                        elif last_clip_width != clip.layout.size.width:
                            return False
                
        return True

    def _get_words_width_for_line_state(self, line: Line, state: ElementState) -> Optional[List[int]]:
        '''
        Returns the width of the words in the line in a specific state.
        If there is a word with no clips for the given line state, returns None.
        '''
        words_width = []
        for word in line.words:
            max_clip_width = 0
            for clip in word.clips:
                if state in clip.states:
                    max_clip_width = max(max_clip_width, clip.layout.size.width)
            if max_clip_width == 0:
                return None
            words_width.append(max_clip_width)
        return words_width

    def _calculate_base_y_position(self, segment: Segment, video_height: int) -> float:
        """Calculates the base Y position for the subtitle block."""
        if not segment.lines:
            return 0.0
            
        total_block_height = sum(line.max_layout.size.height for line in segment.lines)
        return LayoutUtils.get_vertical_alignment_position(self._options.vertical_align, total_block_height, video_height)
