from pycaps.common import Document, Segment, Line, Word, TimeFragment
from pycaps.logger import logger
from .base_transcriber import AudioTranscriber
from .splitter import SplitIntoSentencesSplitter

class GoogleAudioTranscriber(AudioTranscriber):
    def __init__(self, language: str, model_id: str = 'default'):
        """
        Transcribes audio using Google Cloud Speech-to-Text API.
        
        Args:
            language: Language code for the audio (e.g., "en-US", "es-ES").
            model_id: The recognition model to use.
        """
        self._language = language
        self._model_id = model_id
        self._segment_splitter = SplitIntoSentencesSplitter()
        self._client = None

    def transcribe(self, audio_path: str) -> Document:
        client = self._get_client()

        with open(audio_path, "rb") as audio_file:
            content = audio_file.read()

        audio = {"content": content}
        config = {
            "model": self._model_id,
            "enable_word_time_offsets": True,
            "enable_automatic_punctuation": True,
            "language_code": self._language,
        }

        logger().info("Sending audio to Google Speech-to-Text API for transcription...")
        operation = client.long_running_recognize(config=config, audio=audio)
        response = operation.result(timeout=600)
        
        document = self._convert_response_to_document(response)
        self._segment_splitter.split(document)
        logger().info("Transcription received and segmented from Google successfully.")
        
        return document

    def _convert_response_to_document(self, response) -> Document:
        """
        Converts the JSON response from Google STT into the pycaps Document structure.
        """
        document = Document()
        all_words = []

        for result in response.results:
            alternative = result.alternatives[0]
            all_words.extend(alternative.words)

        if not all_words:
            logger().warning("Google STT returned no words in the transcription.")
            return document

        # Create one single Segment and Line to contain all words.
        start_time = all_words[0].start_time.total_seconds()
        end_time = all_words[-1].end_time.total_seconds()
        if start_time == end_time:
            end_time = start_time + 0.01
        
        segment_time = TimeFragment(start=start_time, end=end_time)
        segment = Segment(time=segment_time)
        line = Line(time=segment_time)
        segment.lines.add(line)

        for word_info in all_words:
            word_text = word_info.word.strip()
            if not word_text:
                continue

            word_start = word_info.start_time.total_seconds()
            word_end = word_info.end_time.total_seconds()
            if word_start == word_end:
                word_end = word_start + 0.01
            word_time = TimeFragment(start=word_start, end=word_end)
            word = Word(text=word_text, time=word_time)
            line.words.add(word)

        document.segments.add(segment)
        return document

    def _get_client(self):
        if self._client:
            return self._client

        try:
            from google.cloud import speech
            self._client = speech.SpeechClient()
            return self._client
        except ImportError:
            raise ImportError(
                "Google Cloud Speech library not found. "
                "Please install it with: pip install google-cloud-speech"
            )
        except Exception as e:
            raise RuntimeError(
                f"Error initializing Google Speech client: {e}\n\n"
                "Please ensure you have authenticated correctly via GOOGLE_APPLICATION_CREDENTIALS."
            )
