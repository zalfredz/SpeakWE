class TranscribeError(Exception):
    pass


class AudioError(Exception):
    pass


class GeminiError(Exception):
    def __init__(self, status: int, detail: str = ""):
        super().__init__(f"Gemini HTTP {status}: {detail[:200]}")
        self.status = status


class GeminiOutputError(GeminiError):
    """The API answered but the text is not JSON: treated like an invalid answer, so it is retried."""
