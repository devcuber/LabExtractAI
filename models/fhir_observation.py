"""
Modelos Pydantic para el recurso FHIR R4 `Observation`, usados como
`response_schema` para forzar structured output en el LLM.

Este NO es el schema oficial completo de HL7 FHIR (ese incluye recursión,
polimorfismo vía oneOf, y cientos de campos que Gemini no soporta bien
en structured output). Es un subset deliberado, enfocado en el caso de
uso de este proyecto: mapear un reporte de laboratorio a un único
Observation que actúa como panel general, usando `component` para cada
resultado individual.

Referencia oficial: https://hl7.org/fhir/R4/observation.html
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Coding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None


class CodeableConcept(BaseModel):
    coding: Optional[list[Coding]] = None
    text: Optional[str] = None


class Identifier(BaseModel):
    system: Optional[str] = None
    value: Optional[str] = None


class Reference(BaseModel):
    """
    Referencia a otro recurso FHIR (ej. Patient). 'reference' apunta a
    un recurso real ya persistido (ej. "Patient/123") y NO debe ser
    llenado por el LLM, ya que no tiene acceso a IDs de recursos
    existentes en el sistema. 'display' es el texto legible permitido
    cuando no se cuenta con el recurso enlazado.
    """
    reference: Optional[str] = None
    display: Optional[str] = None


class Quantity(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    system: Optional[str] = Field(default="http://unitsofmeasure.org")
    code: Optional[str] = None


class ReferenceRange(BaseModel):
    low: Optional[Quantity] = None
    high: Optional[Quantity] = None
    text: Optional[str] = None
    type: Optional[CodeableConcept] = None


class ObservationComponent(BaseModel):
    """
    Un resultado individual dentro del panel (ej. Glucosa, Hemoglobina,
    Colesterol total, etc.).

    Solo uno de los campos value* debería venir poblado por resultado,
    ya que representan el value[x] polimórfico de FHIR. Se declaran
    todas las variantes explícitamente porque Gemini structured output
    no soporta oneOf/unión de tipos.
    """

    code: CodeableConcept
    valueQuantity: Optional[Quantity] = None
    valueString: Optional[str] = None
    valueCodeableConcept: Optional[CodeableConcept] = None
    interpretation: Optional[list[CodeableConcept]] = None
    referenceRange: Optional[list[ReferenceRange]] = None


class FhirObservation(BaseModel):
    """
    Observation raíz que actúa como panel general de laboratorio.
    Los resultados individuales van dentro de `component`.

    Nota: no incluye 'id', ya que ese campo es asignado por el servidor
    que persiste el recurso, no por el proceso de extracción del LLM.
    """

    resourceType: Literal["Observation"] = "Observation"
    identifier: Optional[list[Identifier]] = None
    status: Literal[
        "registered", "preliminary", "final", "amended"
    ] = "final"
    category: Optional[list[CodeableConcept]] = None
    code: CodeableConcept
    subject: Optional[Reference] = None
    effectiveDateTime: Optional[str] = None
    issued: Optional[str] = None
    component: list[ObservationComponent]