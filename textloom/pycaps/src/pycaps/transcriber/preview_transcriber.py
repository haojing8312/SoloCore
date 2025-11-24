from pycaps.common import Document, Segment, Line, Word, TimeFragment
from .base_transcriber import AudioTranscriber

class PreviewTranscriber(AudioTranscriber):
    def transcribe(self, audio_path: str) -> Document:
        document = Document()
        structure = {
            (0, 2): "Hello! This is a sample subtitle preview.",
            (2.1, 4.1): "Use this preview to test styles and animations."
        }
        for time, text in structure.items():
            duration = time[1] - time[0]
            segment_time = TimeFragment(time[0], time[1])
            segment = Segment(time=segment_time)
            line = Line(time=segment_time)
            text_without_spaces = text.replace(" ", "")
            letter_duration = duration / len(text_without_spaces)
            last_word_end = time[0]
            for word_text in text.split():
                end = last_word_end + len(word_text) * letter_duration
                word_time = TimeFragment(start=last_word_end, end=end)
                word = Word(text=word_text, time=word_time)
                last_word_end = end
                line.words.add(word)
            
            segment.lines.add(line)
            document.segments.add(segment)
        
        return document
