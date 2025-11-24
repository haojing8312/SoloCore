from typing import Optional
from pycaps.common import Document, Segment
from pycaps.api import EmojiInSegmentsApi, ApiKeyService
from pycaps.ai import LlmProvider
from pycaps.logger import logger
from .emoji_in_segment_llm_getter import EmojiInSegmentLlmGetter

class EmojiInSegmentGetter:

    def __init__(self) -> None:
        self._getter: Optional[EmojiInSegmentsApi|EmojiInSegmentLlmGetter] = None
        self._started = False
    
    def start(self, document: Document) -> None:
        if ApiKeyService.has():
            self._getter = EmojiInSegmentsApi()
            self._getter.start(document)
        elif LlmProvider.get().is_enabled():
            logger().warning("Pycaps API is not set, using external LLM API key for AI auto emojis for segments effect.")
            self._getter = EmojiInSegmentLlmGetter()
            self._getter.start(document)
        else:
            logger().warning("Neither Pycaps API nor external LLM API key are set. Ignoring AI auto emojis for segments effect.")

        self._started = True

    def get_emoji(self, segment: Segment) -> Optional[str]:
        if not self._started:
            raise RuntimeError("Call start() first.")
        
        if not self._getter:
            return None
        
        return self._getter.get_emoji(segment)
