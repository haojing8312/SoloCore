from pycaps.ai.llm import Llm
import os

class Gpt(Llm):

    OPENAI_API_KEY_NAME = "PYCAPS_OPENAI_API_KEY"

    def __init__(self):
        self._client = None

    def send_message(self, prompt: str, model: str = "gpt-4.1-mini") -> str:
        return self._get_client().responses.create(model=model, input=prompt).output_text
    
    def is_enabled(self) -> bool:
        return os.getenv(self.OPENAI_API_KEY_NAME) is not None

    def _get_client(self):
        try:
            from openai import OpenAI

            if self._client:
                return self._client

            self._client = OpenAI(api_key=os.getenv(self.OPENAI_API_KEY_NAME))
            return self._client
        except ImportError:
            raise ImportError(
                "OpenAI API not found. "
                "Please install it with: pip install openai"
            )
        except Exception as e:
            raise RuntimeError(
                f"Error initializing OpenAI client: {e}\n\n"
                "Please ensure you have authenticated correctly via PYCAPS_OPENAI_API_KEY."
            )
