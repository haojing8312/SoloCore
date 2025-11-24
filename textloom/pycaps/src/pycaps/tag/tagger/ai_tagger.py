from typing import Dict
from pycaps.common import Tag
from pycaps.api import ApiKeyService, PycapsTaggerApi
from .external_llm_tagger import ExternalLlmTagger
from pycaps.ai import LlmProvider
from pycaps.logger import logger

class AiTagger:
    def process(self, text: str, rules: Dict[Tag, str]) -> str:
        """
        Process text using AI to identify and tag relevant terms according to given rules.

        Args:
            text: The text to analyze
            rules: Dictionary mapping tags to their topics (e.g., {Tag('emotion'): 'emotions and feelings'})

        Returns:
            Text with XML-like tags around relevant terms
            Example: "I feel <emotion>happy</emotion> about my <finance>investment</finance>"
        """
        if ApiKeyService.has():
            return PycapsTaggerApi().process(text, rules)
        elif LlmProvider.get().is_enabled():
            logger().warning("Pycaps API is not set, using external LLM API key for AI tagging rules.")
            return ExternalLlmTagger().process(text, rules)
        else:
            logger().warning("Neither Pycaps API nor external LLM API key are set. Ignoring AI tagging rules.")
            return text
