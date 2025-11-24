import hashlib
from pycaps.ai import LlmProvider

class ScriptUtils:
    basic_summary_cache = {}

    @staticmethod
    def get_basic_summary(script: str) -> str:
        cache_key = hashlib.md5(script.encode()).hexdigest()
        if cache_key in ScriptUtils.basic_summary_cache:
            return ScriptUtils.basic_summary_cache[cache_key]
        
        summary = LlmProvider.get().send_message(
            prompt=f"""
            Given the following video script, please provide a basic summary of the main topic.

            Basic guidelines:
            1. The summary should be short, a maximum of 50 words.
            2. Only respond with the summary, no other text.
            
            Script: {script}
            """
        )
        number_of_words = len(summary.split())
        if number_of_words > 75:
            summary = " ".join(summary.split()[:75]) + "..."
        ScriptUtils.basic_summary_cache[cache_key] = summary
        return summary
    
    