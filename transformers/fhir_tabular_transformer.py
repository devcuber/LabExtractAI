class FHIRTabularTransformer:

    @classmethod
    def _extract_loinc_display(cls, code_dict: dict) -> str:
        """
        Busca strictly la etiqueta oficial (display) del estándar LOINC
        """
        if not isinstance(code_dict, dict):
            return ""

        codings = code_dict.get("coding", [])
        if isinstance(codings, list):
            for coding in codings:
                if isinstance(coding, dict):
                    display_name = coding.get("display")
                    if display_name:
                        return display_name

        return ""

    @classmethod
    def _extract_fhir_value(cls, container: dict) -> str:
        for key, val in container.items():
            if not key.startswith("value"):
                continue

            if key == "valueQuantity" and isinstance(val, dict):
                v = val.get("value", "")
                u = val.get("unit") or val.get("code") or ""
                return f"{v} {u}".strip()

            elif key == "valueCodeableConcept" and isinstance(val, dict):
                return cls._extract_loinc_display(val)

            elif isinstance(val, (str, int, float, bool)):
                return str(val)

        return ""

    @classmethod
    def _extract_interpretation(cls, container: dict) -> str:
        interps = container.get("interpretation", [])
        if not isinstance(interps, list):
            return ""

        results = []
        for interp in interps:
            if isinstance(interp, dict):
                text = cls._extract_loinc_display(interp)
                if text:
                    results.append(text)
        return " - ".join(results)

    @classmethod
    def _extract_reference_range(cls, container: dict) -> str:
        ranges = container.get("referenceRange", [])
        if not isinstance(ranges, list) or not ranges:
            return ""

        first_range = ranges[0]
        if not isinstance(first_range, dict):
            return ""

        if "text" in first_range:
            return first_range["text"]

        low_obj = first_range.get("low", {})
        high_obj = first_range.get("high", {})

        low_val = low_obj.get("value") if isinstance(low_obj, dict) else None
        high_val = high_obj.get("value") if isinstance(high_obj, dict) else None
        unit = (low_obj.get("unit") or high_obj.get("unit") or "") if isinstance(low_obj, dict) else ""

        if low_val is not None and high_val is not None:
            return f"{low_val} - {high_val} {unit}".strip()
        elif low_val is not None:
            return f"> {low_val} {unit}".strip()
        elif high_val is not None:
            return f"< {high_val} {unit}".strip()

        return ""

    @classmethod
    def observation_to_vertical_rows(cls, data: dict) -> list[dict]:
        """
        Extrae metadatos globales y los resultados (raíz o componentes) 
        en una lista de diccionarios para formato CSV vertical.
        """
        rows = []

        # 1. Metadatos globales (se insertan como filas)
        if "id" in data:
            rows.append({"Parametro": "Observation ID", "Valor": data["id"], "Rango": "", "Interpretacion": ""})
        if "status" in data:
            rows.append({"Parametro": "Status", "Valor": data["status"], "Rango": "", "Interpretacion": ""})
        if "effectiveDateTime" in data:
            rows.append({"Parametro": "Effective Date", "Valor": data["effectiveDateTime"], "Rango": "", "Interpretacion": ""})
        
        if "subject" in data and isinstance(data["subject"], dict):
            name = data["subject"].get("display") or data["subject"].get("reference", "")
            rows.append({"Parametro": "Patient Name", "Valor": name, "Rango": "", "Interpretacion": ""})

        # Interpretación global (como un parámetro sin valor)
        global_interp = cls._extract_interpretation(data)
        if global_interp:
            rows.append({"Parametro": "Global Interpretation", "Valor": "", "Rango": "", "Interpretacion": global_interp})

        # 2. Caso A: Observación simple en la raíz
        root_display = cls._extract_loinc_display(data.get("code", {}))
        root_value = cls._extract_fhir_value(data)
        if root_display:
            rows.append({
                "Parametro": root_display,
                "Valor": root_value,
                "Rango": cls._extract_reference_range(data),
                "Interpretacion": cls._extract_interpretation(data)
            })

        # 3. Caso B: Componentes del panel
        components = data.get("component", [])
        if isinstance(components, list):
            for comp in components:
                if not isinstance(comp, dict):
                    continue

                param_display = cls._extract_loinc_display(comp.get("code", {}))
                if not param_display:
                    continue

                rows.append({
                    "Parametro": param_display,
                    "Valor": cls._extract_fhir_value(comp),
                    "Rango": cls._extract_reference_range(comp),
                    "Interpretacion": cls._extract_interpretation(comp)
                })

        return rows

    @classmethod
    def flatten_fhir_to_dict(cls, data: dict) -> dict:
        """
        Convierte un recurso FHIR Observation a diccionario plano utilizando
        las etiquetas LOINC originales como nombres de llaves.
        (Mantenido por compatibilidad).
        """
        flat = {}

        if "id" in data:
            flat["Observation ID"] = data["id"]
        if "status" in data:
            flat["Status"] = data["status"]
        if "effectiveDateTime" in data:
            flat["Effective Date"] = data["effectiveDateTime"]

        if "subject" in data and isinstance(data["subject"], dict):
            flat["Patient Name"] = data["subject"].get("display") or data["subject"].get("reference", "")

        global_interp = cls._extract_interpretation(data)
        if global_interp:
            flat["Global Interpretation"] = global_interp

        root_display = cls._extract_loinc_display(data.get("code", {}))
        if root_display:
            root_value = cls._extract_fhir_value(data)
            if root_value:
                flat[root_display] = root_value

            ref = cls._extract_reference_range(data)
            if ref:
                flat[f"{root_display} (Ref. Range)"] = ref

        components = data.get("component", [])
        if isinstance(components, list):
            for comp in components:
                if not isinstance(comp, dict):
                    continue

                param_display = cls._extract_loinc_display(comp.get("code", {}))
                if not param_display:
                    continue

                val = cls._extract_fhir_value(comp)
                if val:
                    flat[param_display] = val

                interp = cls._extract_interpretation(comp)
                if interp:
                    flat[f"{param_display} (Interpretation)"] = interp

                ref = cls._extract_reference_range(comp)
                if ref:
                    flat[f"{param_display} (Ref. Range)"] = ref

        return flat