import json
from core.base_llm_provider import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    
    def ask(self, prompt: str) -> str:
        # Respuesta simulada para llamadas de texto plano si las usas
        return "Respuesta simulada del Mock"

    def ask_with_file(self, prompt: str, file_bytes: bytes, mime_type: str = "application/pdf") -> str:
        # Simulamos la respuesta estricta en JSON que esperaría LabAnalyzerService
        mock_observation = {
            "resourceType": "Observation",
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "718-7",
                        "display": "Hemoglobin [Mass/volume] in Blood"
                    }
                ],
                "text": "Hemoglobina"
            },
            "valueQuantity": {
                "value": 14.5,
                "unit": "g/dL",
                "system": "http://unitsofmeasure.org",
                "code": "g/dL"
            }
        }
        
        # Retornamos el JSON envuelto en formato de texto puro (como lo limpia tu servicio)
        return json.dumps(mock_observation)