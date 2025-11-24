from pycaps.common import Tag

class BuiltinTag:
    FIRST_WORD_IN_DOCUMENT = Tag("first-word-in-document")
    FIRST_WORD_IN_SEGMENT = Tag("first-word-in-segment")
    FIRST_WORD_IN_LINE = Tag("first-word-in-line")
    LAST_WORD_IN_DOCUMENT = Tag("last-word-in-document")
    LAST_WORD_IN_SEGMENT = Tag("last-word-in-segment")
    LAST_WORD_IN_LINE = Tag("last-word-in-line")

    FIRST_LINE_IN_DOCUMENT = Tag("first-line-in-document")
    FIRST_LINE_IN_SEGMENT = Tag("first-line-in-segment")
    LAST_LINE_IN_DOCUMENT = Tag("last-line-in-document")
    LAST_LINE_IN_SEGMENT = Tag("last-line-in-segment")

    FIRST_SEGMENT_IN_DOCUMENT = Tag("first-segment-in-document")
    LAST_SEGMENT_IN_DOCUMENT = Tag("last-segment-in-document")

    EMOJI_FOR_SEGMENT = Tag("emoji-for-segment")
