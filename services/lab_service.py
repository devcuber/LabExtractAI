import json
import io
import csv
from core.base_llm_provider import BaseLLMProvider

class LabAnalyzerService:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def extract_data(self, file_content: bytes) -> dict:
        prompt = """
        Actúa como un experto en HL7 FHIR R4. Crea un recurso 'Observation' 
        basado en el archivo adjunto. Omite campos vacíos, no uses dataAbsentReason, 
        responde solo con el JSON puro.
        """
        
        # Llamas al nuevo método del provider
        response_text = self.llm.ask_with_file(prompt, file_content)
        
        # Limpieza
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)

    def json_to_fhir_tabular_csv(self, data: dict) -> str:
        """
        Convierte un diccionario JSON anidado (recurso FHIR) en un string CSV plano,
        aplanando las estructuras con notación de puntos y omitiendo los campos nulos o ausentes.
        """
        def flatten_dict(nested_dict, parent_key="", sep="."):
            items = []
            for k, v in nested_dict.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                elif isinstance(v, list):
                    # Maneja listas simples o mapea diccionarios internos dentro de la lista (ej. coding)
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            items.extend(flatten_dict(item, f"{new_key}[{i}]", sep=sep).items())
                        else:
                            items.append((f"{new_key}[{i}]", item))
                else:
                    if v is not None and v != "":
                        items.append((new_key, v))
            return dict(items)

        # 1. Aplanamos el JSON omitiendo nulos/vacíos de forma nativa
        flattened_data = flatten_dict(data)

        # 2. Preparamos los encabezados y los valores para el CSV
        headers = list(flattened_data.keys())
        values = [flattened_data[h] for h in headers]

        # 3. Generamos el texto CSV utilizando StringIO y el módulo csv estándar
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerow(values)
        
        return output.getvalue().strip()

    async def extract_and_transform(self, file_content: bytes) -> dict:
        """
        Orquesta el flujo completo: 
        1. Envía el PDF a extract_data para obtener el JSON del recurso FHIR.
        2. Pasa el JSON al aplanador para generar el CSV tabular dinámico.
        3. Retorna ambos resultados listos para ser consumidos por el endpoint.
        """
        # 1. Obtenemos el JSON estructurado desde el LLM usando el PDF
        json_data = await self.extract_data(file_content)
        
        # 2. Transformamos el JSON obtenido al formato CSV tabular FHIR
        csv_data = self.json_to_fhir_tabular_csv(json_data)
        
        # 3. Armamos la respuesta unificada para el endpoint
        return {
            "json_data": json_data,
            "csv_data": csv_data
        }