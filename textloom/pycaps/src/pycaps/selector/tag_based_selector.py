from typing import List
from pycaps.common import WordClip
from pycaps.tag import TagCondition

class TagBasedSelector:
    def __init__(self, tag_condition: TagCondition):
        """
        Filters WordClips based on the tags of their associated Word.
        Keeps only WordClips where the parent Word matches the tag condition.
        """
        self._tag_condition = tag_condition

    def select(self, clips: List[WordClip]) -> List[WordClip]:
        return [
            clip for clip in clips
            if self._tag_condition.evaluate(list(clip.get_word().get_all_tags_in_document()))
        ]
