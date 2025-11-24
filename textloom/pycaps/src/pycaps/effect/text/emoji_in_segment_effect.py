from .text_effect import TextEffect
from pycaps.common import Document, Segment, Line, TimeFragment, Word
from typing import Optional
import random
from enum import Enum
from pycaps.tag import BuiltinTag
from .emoji_in_segment_getter import EmojiInSegmentGetter

class EmojiAlign(str, Enum):
    BOTTOM = "bottom"
    TOP = "top"
    RANDOM = "random"

class EmojiInSegmentEffect(TextEffect):
    '''
    This effect adds an emoji to a segment text if it can be meaningfully represented with an emoji.
    '''
    def __init__(
            self,
            chance_to_apply: float = 0.5,
            align: EmojiAlign = EmojiAlign.RANDOM,
            ignore_segments_with_duration_less_than: float = 0,
            max_uses_of_each_emoji: int = 2,
            max_consecutive_segments_with_emoji: int = 3
        ):
        self._chance_to_apply = chance_to_apply
        self._align = align
        self._ignore_segments_with_duration_less_than = ignore_segments_with_duration_less_than
        self._max_uses_of_each_emoji = max_uses_of_each_emoji
        self._max_consecutive_segments_with_emoji = max_consecutive_segments_with_emoji

        self._emojies_frequencies = {}
        self._last_emoji = None
        self._consecutive_segments_with_emoji = 0
        self._emoji_getter = EmojiInSegmentGetter()

    def run(self, document: Document) -> None:
        self._emoji_getter.start(document)
        for segment in document.segments:
            if random.random() > self._chance_to_apply:
                self._consecutive_segments_with_emoji = 0
                continue
            
            emoji = self.__get_relevant_emoji(segment)
            if emoji is None:
                self._consecutive_segments_with_emoji = 0
                continue
            
            self.__add_emoji_to_segment(segment, emoji)

    def __get_relevant_emoji(self, segment: Segment) -> Optional[str]:
        if self._ignore_segments_with_duration_less_than > 0 and \
            segment.time.end - segment.time.start < self._ignore_segments_with_duration_less_than:
            return None
        
        if self._max_consecutive_segments_with_emoji > 0 and \
            self._consecutive_segments_with_emoji >= self._max_consecutive_segments_with_emoji:
            return None

        emoji = self._emoji_getter.get_emoji(segment)
        emoji_frequency = self._emojies_frequencies.get(emoji, 0)
        if self._max_uses_of_each_emoji > 0 and emoji_frequency >= self._max_uses_of_each_emoji:
            return None
        
        if self._last_emoji is not None and self._last_emoji == emoji:
            return None
        
        self._emojies_frequencies[emoji] = emoji_frequency + 1
        self._consecutive_segments_with_emoji += 1
        self._last_emoji = emoji

        return emoji

    def __add_emoji_to_segment(self, segment: Segment, emoji: str):
        align = self._align
        if align == EmojiAlign.RANDOM:
            align = random.choice([EmojiAlign.BOTTOM, EmojiAlign.TOP])

        moment = segment.time.start if align == EmojiAlign.TOP else segment.time.end
        time = TimeFragment(start=moment, end=moment)
        new_line = Line(time=time)
        emoji_word = Word(text=emoji, semantic_tags={BuiltinTag.EMOJI_FOR_SEGMENT}, time=time)
        new_line.words.add(emoji_word)

        if align == EmojiAlign.BOTTOM:
            segment.lines.add(new_line)
        else:
            segment.lines.add(new_line, 0)
