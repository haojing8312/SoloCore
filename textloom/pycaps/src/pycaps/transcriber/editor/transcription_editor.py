from pycaps.common import Document
import webview
import os
from typing import Optional

class _Api:
    def __init__(self, document: Document):
        self._document = document
        self._result_document: Optional[Document] = None

    def get_document_as_json(self) -> dict:
        return self._document.to_dict()
    
    def get_result_document(self) -> Optional[Document]:
        return self._result_document

    def save(self, document_dict: dict):
        self._result_document = Document.from_dict(document_dict)

        if webview.active_window():
            webview.active_window().destroy()

    def cancel(self):
        self._result_document = None
        if webview.active_window():
            webview.active_window().destroy()

class TranscriptionEditor:

    def run(self, document: Document) -> Document:
        html_file_path = os.path.join(os.path.dirname(__file__), 'editor.html')
        html_content = open(html_file_path, 'r', encoding='utf-8').read()

        window_title = "Subtitle Editor"
        api = _Api(document)
        webview.create_window(
            window_title,
            html=html_content,
            width=1200,
            height=800,
            resizable=True,
            js_api=api
        )
        webview.start()
        
        result_document = api.get_result_document()
        if result_document:
            return result_document
        return document
