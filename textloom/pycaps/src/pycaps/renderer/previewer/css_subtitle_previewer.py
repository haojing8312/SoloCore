from pycaps.common import ElementState, Tag
import webview
import os
from ..renderer_page import RendererPage
from typing import Optional
from pathlib import Path

class _Api:
    def __init__(self, custom_css: str, base_url: Optional[str] = None):
        self._renderer_page: RendererPage = RendererPage()
        self._custom_css = custom_css
        self._base_url = base_url

    def get_renderer_html(self, current_segment_data: dict) -> str:
        segment = current_segment_data
        line = segment['line']
        words = line['words']
        return self._renderer_page.get_html(
            custom_css=self._custom_css,
            base_url=self._base_url,
            segment_tags=segment['tags'],
            line_tags=line['tags'],
            line_state=ElementState(line['state']),
            words=[word['text'] for word in words],
            word_tags=[[Tag(tag) for tag in word['tags']] for word in words],
            word_states=[ElementState(word['state']) for word in words],
        )

class CssSubtitlePreviewer:

    def run(self, custom_css: str, resources_dir: Optional[str] = None) -> None:
        if resources_dir and not os.path.exists(resources_dir):
            raise FileNotFoundError(f"Resources directory not found: {resources_dir}")
        if resources_dir and not os.path.isdir(resources_dir):
            raise NotADirectoryError(f"Resources directory is not a directory: {resources_dir}")

        html_file_path = os.path.join(os.path.dirname(__file__), 'previewer.html')
        base_url = Path(resources_dir).resolve().as_uri() if resources_dir else None
        base_url = base_url + "/" if base_url and not base_url.endswith("/") else base_url

        window_title = "Subtitle Previewer"
        api = _Api(custom_css, base_url)
        webview.create_window(
            window_title,
            url=Path(html_file_path).resolve().as_uri(),
            width=1200,
            height=800,
            resizable=True,
            js_api=api
        )
        webview.start(debug=True)
