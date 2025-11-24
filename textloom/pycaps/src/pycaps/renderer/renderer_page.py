from pycaps.common import Tag, ElementState
from typing import Optional

class RendererPage:

    DEFAULT_CSS_CLASS_FOR_EACH_WORD: str = "word"
    DEFAULT_CSS_CLASS_FOR_EACH_LINE: str = "line"

    def get_html(
            self,
            custom_css: str = "",
            base_url: Optional[str] = None,
            segment_tags: list[Tag] = [],
            line_tags: list[Tag] = [],
            line_state: ElementState = ElementState.LINE_NOT_NARRATED_YET,
            words: list[str] = [],
            word_tags: list[list[Tag]] = [],
            word_states: list[ElementState] = []
        ) -> str:
        base_tag = f'<base href="{base_url}">' if base_url else ""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            {base_tag}
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    overflow: hidden;
                    font-family: sans-serif;
                }} 

                #subtitle-container {{
                    display: inline-block;
                }}

                .{self.DEFAULT_CSS_CLASS_FOR_EACH_LINE} {{
                    display: flex;
                    width: fit-content;
                }}

                {custom_css}
            </style>
        </head>
        <body>
            <div id="subtitle-container">
                <div class="{self.get_line_css_classes(segment_tags, line_tags, line_state)}">
                    {"".join([self.get_word_html(index, word, word_tags[index], word_states[index]) for index, word in enumerate(words)])}
                </div>
            </div>
        </body>
        </html>
        """
    
    def get_line_css_classes(self, segment_tags: list[Tag], line_tags: list[Tag], line_state: ElementState) -> str:
        css_classes = [self.DEFAULT_CSS_CLASS_FOR_EACH_LINE]
        css_classes.extend([tag.name for tag in segment_tags])
        css_classes.extend([tag.name for tag in line_tags])
        css_classes.append(line_state.value)
        return " ".join(css_classes)
    
    def get_word_css_classes(self, word_tags: list[Tag], index: Optional[int] = None, word_state: Optional[ElementState] = None) -> str:
        css_classes = [self.DEFAULT_CSS_CLASS_FOR_EACH_WORD]
        if index is not None:
            css_classes.append(f"word-{index}-in-line")
        css_classes.extend([tag.name for tag in word_tags])
        if word_state:
            css_classes.append(word_state.value)
        return " ".join(css_classes)
    
    def get_word_html(self, index: int, word: str, word_tags: list[Tag], word_state: ElementState) -> str:
        return f"<span class=\"{self.get_word_css_classes(word_tags, index, word_state)}\">{word}</span>"
    