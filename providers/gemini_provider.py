import io
import time
from google import genai
from google.genai import types
from core.base_llm_provider import BaseLLMProvider
from google.genai.errors import ServerError as GoogleServerError

class GeminiLLMProvider(BaseLLMProvider):

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._system_instruction: str | None = None

    def set_system_instruction(self, instruction: str):
        """Define el prompt de configuración de sistema o rol general del LLM."""
        self._system_instruction = instruction

    def ask(self, prompt: str) -> str:
        grounding_tool = types.Tool(google_search=types.GoogleSearch())

        config = types.GenerateContentConfig(
            tools=[grounding_tool],
            system_instruction=self._system_instruction
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )

        return response.text

    def ask_with_file(self, prompt: str, file_bytes: bytes, mime_type: str = "application/pdf") -> str:
        # Creamos la parte del contenido directamente desde los bytes en memoria
        file_part = types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime_type
        )
        config = types.GenerateContentConfig(
            temperature=0.0,
            system_instruction=self._system_instruction,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            response_mime_type="application/json"
        )
        try:
            # Enviamos los bytes y el prompt en una sola petición síncrona e inmediata
            response = self._client.models.generate_content(
                model=self._model,
                contents=[file_part, prompt],
                config=config,
            )   
        except GoogleServerError as e:
            raise ConnectionError(str(e))
        
        return response.text