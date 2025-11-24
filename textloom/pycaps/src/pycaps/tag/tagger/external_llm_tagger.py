from typing import Dict
from pycaps.common import Tag
from pycaps.ai import LlmProvider
from pycaps.logger import logger
import re

class ExternalLlmTagger:
    """
    Handles the interaction with LLM for semantic tagging of text.
    This class is responsible for generating appropriate prompts and
    processing LLM responses to tag text according to given topics.
    """

    def __init__(self):
        self._llm = LlmProvider.get()

    def process(self, text: str, rules: Dict[Tag, str]) -> str:
        """
        Process text using LLM to identify and tag relevant terms according to given rules.

        Args:
            text: The text to analyze
            rules: Dictionary mapping tags to their topics (e.g., {Tag('emotion'): 'emotions and feelings'})

        Returns:
            Text with XML-like tags around relevant terms
            Example: "I feel <emotion>happy</emotion> about my <finance>investment</finance>"
        """
        prompt = self._build_prompt(text, rules)
        response = self._llm.send_message(prompt)
        return self._process_response(text, response, rules)

    def _build_prompt(self, text: str, rules: Dict[Tag, str]) -> str:
        """
        Builds the prompt for the LLM with clear instructions about the tagging task.
        """
        # Convert rules to a formatted string for the prompt
        rules_str = "\n".join([
            f"- Tag '{prompt}' with <{tag.name}> tag"
            for tag, prompt in rules.items()
        ])

        return f"""Please analyze the following text and tag relevant terms according to these rules:

{rules_str}

Important guidelines:
1. Use XML-like tags with the exact class names provided
2. Only tag specific words or short phrases, not entire sentences
3. Tags should not overlap
4. Preserve the exact original text, only adding tags
5. If a term matches multiple categories, use the most specific one
6. Do not add any explanations or additional text. Just return the text with the tags.

Text to analyze:
{text}

Tagged version:"""

    def _process_response(self, original_text: str, tagged_text: str, rules: Dict[Tag, str]) -> str:
        """
        Validates the LLM response.
        Ensures the response follows the expected format and contains valid tags.
        Returns the original text if the tagged text is not valid, otherwise returns the tagged text received.
        """
        tagged_text_without_tags = tagged_text.strip()
        for tag in rules.keys():
            pattern = f'<{tag.name}>(.*?)</{tag.name}>'
            tagged_text_without_tags = re.sub(pattern, r'\1', tagged_text_without_tags)
        
        if original_text != tagged_text_without_tags:
            logger().warning(f"The tagged text is not equal to the original text:\nOriginal text: \"{original_text}\"\nTagged text (without tags): \"{tagged_text_without_tags}\"")
            logger().warning("Using the original text instead.")
            return original_text
        
        return tagged_text.strip()
