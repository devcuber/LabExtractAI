import io
import time
from google import genai
from google.genai import types
from core.base_llm_provider import BaseLLMProvider
from google.genai.errors import ServerError as GoogleServerError

class GeminiLLMProvider(BaseLLMProvider):

    def __init__(
        self,
        api_key: str,
        config: types.GenerateContentConfig,
        model: str = "gemini-2.5-flash",
    ):
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._config = config

    def ask(self, prompt: str, file_bytes: bytes = None, mime_type: str = "application/pdf") -> str:
        contents = [prompt]

        if file_bytes is not None:
            file_part = types.Part.from_bytes(
                data=file_bytes,
                mime_type=mime_type
            )
            contents = [file_part, prompt]

        max_retries = 5
        retry_delay_seconds = 5

        for attempt in range(max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=self._config,
                )
                return response.text
            except GoogleServerError as e:
                if attempt == max_retries:
                    raise ConnectionError(str(e))
                time.sleep(retry_delay_seconds)