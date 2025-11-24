from pycaps.common import Document, Tag
from .api_sender import send
from pycaps.logger import logger
from typing import Dict

class PycapsTaggerApi:

    _FEATURE_NAME = "tagger"

    def process(self, text: str, rules: Dict[Tag, str]) -> str:
        payload = {}
        payload["text"] = text
        payload["rules"] = [{"tag": tag.name, "prompt": prompt} for tag, prompt in rules.items()]
        try:
            response = send(self._FEATURE_NAME, payload)
            if (not response.get("success", False) or not response.get("result", None)):
                logger().error(f"Llm tagger API error: {response.get('error_message', '')}")
                logger().error("Using text without tags instead")
                return text
            else:
                return response["result"]
        except Exception as e:
            logger().error(f"Unexpected error from API, ignoring AI tags feature. Error: {e}")
            return text
