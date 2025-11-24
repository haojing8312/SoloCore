from pycaps.common import Document
import json

class SubtitleDataService:
    def __init__(self, path: str):
        self._path = path

    def save(self, document: Document) -> None:
        with open(self._path, "w") as f:
            json.dump(document.to_dict(), f)

    def load(self) -> Document:
        with open(self._path, "r") as f:
            return Document.from_dict(json.load(f))
