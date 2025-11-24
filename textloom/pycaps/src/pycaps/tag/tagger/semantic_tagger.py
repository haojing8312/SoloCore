import re
from pycaps.common import Word, Document, Tag
from .ai_tagger import AiTagger
from typing import Dict

class SemanticTagger:
    '''
    Register of semantic rules for the word-level tagger.
    The matching words are tagged with the tag name of the rule that matched.

    This class implements three types of rules:
     - Regex rules: Use regular expressions to find and tag matching words
     - AI rules: Use a language model to identify and tag relevant words/phrases related to a received topic
    '''

    def __init__(self):
        self._regex_rules: Dict[Tag, str] = {}
        self._ai_rules: Dict[Tag, str] = {}
        self._wordlist_rules: Dict[Tag, list[str]] = {}
        self._ai_tagger = AiTagger()

    def add_regex_rule(self, tag: Tag, pattern: str) -> None:
        """Register a new regex-based rule."""
        self._regex_rules[tag] = pattern

    def add_ai_rule(self, tag: Tag, instructions: str) -> None:
        """Register a new AI-based rule."""
        self._ai_rules[tag] = instructions

    def add_wordlist_rule(self, tag: Tag, wordlist: list[str]) -> None:
        self._wordlist_rules[tag] = list(map(lambda w: self._sanitize_word_text(w), wordlist))

    def tag(self, document: Document) -> None:
        """Apply all registered rules to the document."""
        self._apply_wordlist_rules(document)
        self._apply_regex_rules(document)
        self._apply_ai_rules(document)

    def _apply_wordlist_rules(self, document: Document) -> None:
        for tag, wordlist in self._wordlist_rules.items():
            for word in document.get_words():
                if self._sanitize_word_text(word.text) in wordlist:
                    word.semantic_tags.add(tag)

    def _apply_regex_rules(self, document: Document) -> None:
        """Apply regex rules to the document."""
        words = document.get_words()
        text = document.get_text().strip()

        for tag, pattern in self._regex_rules.items():
            matches = re.finditer(pattern, text)
            matches_positions = [(match.start(), match.end()) for match in matches]
            self._tag_matching_words(words, matches_positions, tag)

    def _apply_ai_rules(self, document: Document) -> None:
        """
        Apply AI rules to the document. Internally it uses a LLM with all the rules.
        """
        if not self._ai_rules:
            return

        words = document.get_words()
        text = document.get_text().strip()
        
        tagged_text = self._ai_tagger.process(text, self._ai_rules)
        text_positions_mapping = self._build_text_positions_mapping(tagged_text)
        for tag in self._ai_rules.keys():
            pattern = f'<{tag.name}>(.*?)</{tag.name}>'
            matches = re.finditer(pattern, tagged_text)
            matches_positions = [(m.start(1), m.end(1)-1) for m in matches]
            mapped_matches_positions = [(text_positions_mapping.get(start, 0), text_positions_mapping.get(end, 0)) for start, end in matches_positions]
            self._tag_matching_words(words, mapped_matches_positions, tag)
    
    def _build_text_positions_mapping(self, tagged_text: str) -> dict[int, int]:
        """Build a mapping of positions in the tagged text to the original text."""
        mapping = {}
        tagged_pos = 0
        original_pos = 0
        in_tag = False
        while tagged_pos < len(tagged_text):
            char = tagged_text[tagged_pos]
            if char == '<':
                in_tag = True
            if not in_tag:
                mapping[tagged_pos] = original_pos
                original_pos += 1
            if char == '>':
                in_tag = False
            tagged_pos += 1

        return mapping

    def _tag_matching_words(self, words: list[Word], matches_positions: list[tuple[int, int]], tag: Tag) -> None:
        """Tag words that match the found patterns."""
        for match_start, match_end in matches_positions:
            current_pos = 0
            for word in words:
                word_start = current_pos
                word_end = current_pos + len(word.text) + 1 # for space char
                
                if self._word_overlaps_with_match(word_start, word_end, match_start, match_end):
                    word.semantic_tags.add(tag)
                
                current_pos = word_end

    def _word_overlaps_with_match(self, word_start: int, word_end: int, 
                                 match_start: int, match_end: int) -> bool:
        """Determine if a word overlaps with a found match."""
        return (word_start <= match_start < word_end) or \
               (word_start < match_end <= word_end) or \
               (match_start <= word_start and match_end >= word_end)
    
    def _sanitize_word_text(self, text):
        return re.sub(r'[^\w]+', '', text).lower()
