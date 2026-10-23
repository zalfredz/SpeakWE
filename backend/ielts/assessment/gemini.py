"""Minimal Gemini REST client (generateContent). The key goes in a header, never in the URL or logs."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .errors import GeminiError, GeminiOutputError

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiClient:
    def __init__(self, api_key: str, model: str, timeout_s: int = 180):
        self.api_key, self.model, self.timeout_s = api_key, model, timeout_s

    def generate(self, body: dict) -> dict:
        req = Request(API.format(model=self.model), data=json.dumps(body).encode(), method="POST",
                      headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key})
        try:
            with urlopen(req, timeout=self.timeout_s) as res:
                answer = json.loads(res.read())
        except HTTPError as e:
            raise GeminiError(e.code, e.read().decode(errors="replace")) from e
        except OSError as e:            # URLError, timeouts, connection resets during read
            raise GeminiError(0, str(e)) from e
        except ValueError as e:         # a 2xx body that is not JSON (proxy page, truncated body)
            raise GeminiError(0, f"non-JSON response: {e}") from e
        try:
            return json.loads(answer["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise GeminiOutputError(200, f"unparseable answer: {str(answer)[:200]}") from e
