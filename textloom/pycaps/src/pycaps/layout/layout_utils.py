from typing import Tuple
from pycaps.common import WordClip, ElementType
from .definitions import VerticalAlignment, VerticalAlignmentType


class LayoutUtils:
    @staticmethod
    def get_vertical_alignment_position(alignment: VerticalAlignment, element_height: int, container_height: int) -> int:
        if alignment.align == VerticalAlignmentType.CENTER:
            offset = alignment.offset + 0.5
            return (container_height - element_height) * offset
        elif alignment.align == VerticalAlignmentType.TOP:
            return container_height * alignment.offset
        elif alignment.align == VerticalAlignmentType.BOTTOM:
            # we avoid sending it to the max bottom when the default offset (0.0) is used,
            # doing this, we leave a gap at the bottom 
            offset = alignment.offset + 0.95
            return container_height * offset - element_height
        
        raise ValueError(f"Invalid alignment: {alignment.align}")
    
    @staticmethod
    def get_clip_container_center(clip: WordClip, target_container: ElementType) -> Tuple[float, float]:
        '''
        Get the center of the container (line, segment, word) of the clip
        Important: keep in mind it returns float values.
        If you need using it for final position or size, you should use int() (we are working with pixels)
        '''
        if target_container == ElementType.LINE:
            layout = clip.get_line().max_layout
        elif target_container == ElementType.SEGMENT:
            layout = clip.get_segment().max_layout
        else:
            # default to word container
            layout = clip.get_word().max_layout

        center = layout.get_center()
        return (center.x, center.y)
