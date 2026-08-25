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
    def _extract_loinc_code(cls, code_dict: dict) -> str:
        """
        Busca el código oficial (code) del estándar LOINC
        """
        if not isinstance(code_dict, dict):
            return ""

        codings = code_dict.get("coding", [])
        if isinstance(codings, list):
            for coding in codings:
                if isinstance(coding, dict):
                    # Opcionalmente se puede validar que system sea 'http://loinc.org'
                    code_val = coding.get("code")
                    if code_val:
                        return str(code_val)

        return ""

    @classmethod
    def _extract_original_text(cls, code_dict: dict) -> str:
        """
        Busca el texto original tal como lo escribió el laboratorio,
        sin normalizar (campo 'text' de CodeableConcept).
        """
        if not isinstance(code_dict, dict):
            return ""

        text = code_dict.get("text")
        if isinstance(text, str):
            return text

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
                return cls._extract_loinc_display(val) or cls._extract_original_text(val)

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
                text = cls._extract_loinc_display(interp) or cls._extract_original_text(interp)
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
        Extrae metadatos globales y los resultados (raíz o componentes) en una
        lista de diccionarios para formato CSV vertical.

        Estructura del archivo resultante (en orden):
            1. Status
            2. Effective Date
            3. Patient Name
            4. Fila de encabezado literal (Texto Original, Código LOINC,
               Descripción LOINC, Valor, Rango de Referencia, Interpretación)
            5. Interpretación global (si existe)
            6. Observación raíz (si existe)
            7. Componentes del panel

        Nota: esta lista debe pasarse a `list_to_csv_string(rows, write_header=False)`
        para que csv.DictWriter no agregue un encabezado automático adicional
        antes de "Status".
        """
        HEADERS = [
            "Texto Original",
            "Código LOINC",
            "Descripción LOINC",
            "Valor",
            "Rango de Referencia",
            "Interpretación",
        ]

        def _empty_row(texto_original: str, valor: str = "") -> dict:
            return {
                "Texto Original": texto_original,
                "Código LOINC": "",
                "Descripción LOINC": "",
                "Valor": valor,
                "Rango de Referencia": "",
                "Interpretación": "",
            }

        result = []

        # 1. Metadatos globales (Status, Effective Date, Patient Name)
        if "status" in data:
            result.append(_empty_row("Status", data["status"]))
        if "effectiveDateTime" in data:
            result.append(_empty_row("Effective Date", data["effectiveDateTime"]))
        if "subject" in data and isinstance(data["subject"], dict):
            name = data["subject"].get("display") or data["subject"].get("reference", "")
            result.append(_empty_row("Patient Name", name))

        # 2. Fila de encabezado literal, insertada justo después de los metadatos
        result.append({col: col for col in HEADERS})

        # 3. Interpretación global (como fila de datos, ya después del encabezado)
        global_interp = cls._extract_interpretation(data)
        if global_interp:
            row = _empty_row("Global Interpretation")
            row["Interpretación"] = global_interp
            result.append(row)

        # 4. Caso A: Observación simple en la raíz
        root_code = data.get("code", {})
        root_texto = cls._extract_original_text(root_code)
        root_code_val = cls._extract_loinc_code(root_code)
        root_display = cls._extract_loinc_display(root_code)

        if root_texto or root_display or root_code_val:
            result.append({
                "Texto Original": root_texto,
                "Código LOINC": root_code_val,
                "Descripción LOINC": root_display,
                "Valor": cls._extract_fhir_value(data),
                "Rango de Referencia": cls._extract_reference_range(data),
                "Interpretación": cls._extract_interpretation(data),
            })

        # 5. Caso B: Componentes del panel
        components = data.get("component", [])
        if isinstance(components, list):
            for comp in components:
                if not isinstance(comp, dict):
                    continue

                comp_code = comp.get("code", {})
                param_texto = cls._extract_original_text(comp_code)
                param_code_val = cls._extract_loinc_code(comp_code)
                param_display = cls._extract_loinc_display(comp_code)

                if not param_texto and not param_display and not param_code_val:
                    continue

                result.append({
                    "Texto Original": param_texto,
                    "Código LOINC": param_code_val,
                    "Descripción LOINC": param_display,
                    "Valor": cls._extract_fhir_value(comp),
                    "Rango de Referencia": cls._extract_reference_range(comp),
                    "Interpretación": cls._extract_interpretation(comp),
                })

        return result

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