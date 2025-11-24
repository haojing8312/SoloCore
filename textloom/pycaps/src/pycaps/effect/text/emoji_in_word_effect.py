from .text_effect import TextEffect
from pycaps.common import Document, Word
from pycaps.tag import TagCondition
from typing import List, Optional
import random

class EmojiInWordEffect(TextEffect):
    '''
    This effect will add an emoji to the end of each phrase that matches the tag condition.
    '''

    def __init__(self, emojis: List[str], tag_condition: TagCondition, avoid_use_same_emoji_in_a_row: bool = True):
        self._emojies = emojis
        self._tag_condition = tag_condition
        self._avoid_use_same_emoji_in_a_row = avoid_use_same_emoji_in_a_row

        if len(self._emojies) == 0:
            raise ValueError("Emojies list cannot be empty")

    def run(self, document: Document) -> None:
        last_matching_word: Optional[Word] = None
        last_used_emoji: Optional[str] = None
        for word in document.get_words():
            if self._tag_condition.evaluate(list(word.get_all_tags_in_document())):
                last_matching_word = word

            elif last_matching_word:
                last_used_emoji = self._get_random_emoji(last_used_emoji)
                last_matching_word.text += last_used_emoji
                last_matching_word = None

        if last_matching_word:
            last_matching_word.text += self._get_random_emoji(last_used_emoji)

    def _get_random_emoji(self, last_used_emoji: Optional[str]) -> str:
        if not self._avoid_use_same_emoji_in_a_row or not last_used_emoji:
            return " " + random.choice(self._emojies)

        new_emoji = random.choice(self._emojies)
        if new_emoji == last_used_emoji:
            return self._emojies[(self._emojies.index(new_emoji) + 1) % len(self._emojies)]

        return " " + new_emoji
