from pycaps.common import Document, Segment
from typing import Optional
from .api_sender import send
from pycaps.logger import logger

class EmojiInSegmentsApi:

    _FEATURE_NAME = "emoji-in-segments"

    def __init__(self) -> None:
        self._cached_response: Optional[dict] = None

    def start(self, document: Document) -> None:
        payload = {}
        segment_texts = []
        for segment in document.segments:
            segment_texts.append(segment.get_text())
        payload["segments"] = segment_texts
        try:
            response = send(self._FEATURE_NAME, payload)
            if not response or type(response) != list:
                logger().error(f"Invalid response received API, ignoring emojies feature. Response: {response}")
                self._cached_response = []
            else:
                self._cached_response = response
        except Exception as e:
            logger().error(f"Unexpected error from API, ignoring emojies feature. Error: {e}")
            self._cached_response = []
        

    def get_emoji(self, segment: Segment) -> Optional[str]:
        if self._cached_response is None:
            raise RuntimeError("Call process() first")

        segment_text = segment.get_text().strip().lower()
        for processed_segment in self._cached_response:
            processed_text = processed_segment.get("text", "").strip().lower()
            if segment_text == processed_text:
                return processed_segment.get("emoji", None)
            
        logger().warning(f"This should not happen: segment text '{segment_text}' not found in cached response. No emoji used for it.")
        return None
