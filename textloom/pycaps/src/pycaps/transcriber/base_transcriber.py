from abc import ABC, abstractmethod
from pycaps.common import Document

class AudioTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> Document:
        """
        Transcribes an audio file and returns a Document object.

        The Document object contains information about word-by-word timing information.

        Args:
            audio_path: Path to the audio file to be transcribed.

        Returns:
            A Document object.
        """
        pass 