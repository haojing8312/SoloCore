from typing import Optional
from .llm import Llm
from .gpt import Gpt

class LlmProvider:
    _llm: Optional[Llm] = None

    @staticmethod
    def get() -> Llm:
        if LlmProvider._llm is None:
            LlmProvider._llm = Gpt()
        return LlmProvider._llm
    
    @staticmethod
    def set(llm: Llm):
        LlmProvider._llm = llm
