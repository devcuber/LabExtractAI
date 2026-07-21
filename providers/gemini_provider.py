import io
import time
from google import genai
from google.genai import types
from core.base_llm_provider import BaseLLMProvider


class GeminiLLMProvider(BaseLLMProvider):

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def ask(self, prompt: str) -> str:
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[grounding_tool])

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )

        return response.text

    def ask_with_file(self, prompt: str, file_bytes: bytes, mime_type: str = "application/pdf") -> str:
        # Convertimos los bytes a un archivo en memoria (stream)
        # Esto evita que la SDK intente buscar una ruta en el disco duro
        file_stream = io.BytesIO(file_bytes)
        
        # Le damos un nombre al archivo dentro del objeto para que la API lo reconozca
        uploaded_file = self._client.files.upload(
            file=file_stream,
            config=types.UploadFileConfig(mime_type=mime_type)
        )
        
        # Bucle de espera (el resto de tu lógica es correcta)
        while uploaded_file.state.name == "PROCESSING":
            print("Esperando a que Gemini procese el PDF...")
            time.sleep(2)
            uploaded_file = self._client.files.get(name=uploaded_file.name)
            
        if uploaded_file.state.name == "FAILED":
            raise Exception("El procesamiento del archivo en Google falló.")
        
        response = self._client.models.generate_content(
            model=self._model,
            contents=[uploaded_file, prompt]
        )
        return response.text