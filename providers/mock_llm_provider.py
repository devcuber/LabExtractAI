import json
from core.base_llm_provider import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    
    def ask(self, prompt: str) -> str:
        # Respuesta simulada para llamadas de texto plano si las usas
        return "Respuesta simulada del Mock"

    def ask_with_file(self, prompt: str, file_bytes: bytes, mime_type: str = "application/pdf") -> str:
        # Simulamos la respuesta estricta con el JSON completo de la CBC provisto
        mock_observation = {
            "resourceType": "Observation",
            "id": "cbc-drlogy-yashpatel-20241202",
            "meta": {
                "profile": [
                    "http://hl7.org/fhir/StructureDefinition/Observation"
                ]
            },
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "laboratory",
                            "display": "Laboratory"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "58410-AB",
                        "display": "Complete blood count panel"
                    }
                ],
                "text": "Complete Blood Count (CBC)"
            },
            "subject": {
                "reference": "Patient/yash-m-patel",
                "display": "Yash M. Patel"
            },
            "effectiveDateTime": "2024-12-02T15:11:00+05:30",
            "issued": "2024-12-02T16:35:00+05:30",
            "performer": [
                {
                    "display": "Medical Lab Technician (B.Otatink)"
                },
                {
                    "display": "Dr. Payal Shah (MD, Pathologist)"
                },
                {
                    "display": "Dr. Vimal Shah (MD, Pathologist)"
                }
            ],
            "interpretation": [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "165384001",
                            "display": "Further investigation required"
                        }
                    ],
                    "text": "Further confirm for Anemia"
                }
            ],
            "method": {
                "text": "Fully automated cell counter - Mindray 300"
            },
            "note": [
                {
                    "text": "Thanks for Reference"
                }
            ],
            "component": [
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "718-7",
                                "display": "Hemoglobin [Mass/volume] in Blood"
                            }
                        ],
                        "text": "Hemoglobin (Hb)"
                    },
                    "valueQuantity": {
                        "value": 12.5,
                        "unit": "g/dL",
                        "system": "http://unitsofmeasure.org",
                        "code": "g/dL"
                    },
                    "interpretation": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                    "code": "L",
                                    "display": "Low"
                                }
                            ]
                        }
                    ],
                    "referenceRange": [
                        {
                            "low": {
                                "value": 13,
                                "unit": "g/dL",
                                "system": "http://unitsofmeasure.org",
                                "code": "g/dL"
                            },
                            "high": {
                                "value": 17,
                                "unit": "g/dL",
                                "system": "http://unitsofmeasure.org",
                                "code": "g/dL"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "789-8",
                                "display": "Erythrocytes [#/volume] in Blood"
                            }
                        ],
                        "text": "Total RBC count"
                    },
                    "valueQuantity": {
                        "value": 5.2,
                        "unit": "mill/cumm",
                        "system": "http://unitsofmeasure.org",
                        "code": "10*6/uL"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 4.5,
                                "unit": "mill/cumm",
                                "system": "http://unitsofmeasure.org",
                                "code": "10*6/uL"
                            },
                            "high": {
                                "value": 5.5,
                                "unit": "mill/cumm",
                                "system": "http://unitsofmeasure.org",
                                "code": "10*6/uL"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "4544-3",
                                "display": "Hematocrit [Volume Fraction] of Blood"
                            }
                        ],
                        "text": "Packed Cell Volume (PCV)"
                    },
                    "valueQuantity": {
                        "value": 57.5,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    },
                    "interpretation": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                    "code": "H",
                                    "display": "High"
                                }
                            ]
                        }
                    ],
                    "referenceRange": [
                        {
                            "low": {
                                "value": 40,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            },
                            "high": {
                                "value": 50,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "787-2",
                                "display": "Mean corpuscular volume"
                            }
                        ],
                        "text": "Mean Corpuscular Volume (MCV)"
                    },
                    "valueQuantity": {
                        "value": 87.75,
                        "unit": "fL",
                        "system": "http://unitsofmeasure.org",
                        "code": "fL"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 83,
                                "unit": "fL",
                                "system": "http://unitsofmeasure.org",
                                "code": "fL"
                            },
                            "high": {
                                "value": 101,
                                "unit": "fL",
                                "system": "http://unitsofmeasure.org",
                                "code": "fL"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "788-0",
                                "display": "Mean corpuscular hemoglobin"
                            }
                        ],
                        "text": "MCH"
                    },
                    "valueQuantity": {
                        "value": 27.2,
                        "unit": "pg",
                        "system": "http://unitsofmeasure.org",
                        "code": "pg"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 27,
                                "unit": "pg",
                                "system": "http://unitsofmeasure.org",
                                "code": "pg"
                            },
                            "high": {
                                "value": 32,
                                "unit": "pg",
                                "system": "http://unitsofmeasure.org",
                                "code": "pg"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "786-4",
                                "display": "Mean corpuscular hemoglobin concentration"
                            }
                        ],
                        "text": "MCHC"
                    },
                    "valueQuantity": {
                        "value": 32.8,
                        "unit": "g/dL",
                        "system": "http://unitsofmeasure.org",
                        "code": "g/dL"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 32.5,
                                "unit": "g/dL",
                                "system": "http://unitsofmeasure.org",
                                "code": "g/dL"
                            },
                            "high": {
                                "value": 34.5,
                                "unit": "g/dL",
                                "system": "http://unitsofmeasure.org",
                                "code": "g/dL"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "30517-5",
                                "display": "Red cell distribution width (RDW) - coefficient of variation in Blood"
                            }
                        ],
                        "text": "RDW"
                    },
                    "valueQuantity": {
                        "value": 13.6,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 11.6,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            },
                            "high": {
                                "value": 14,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "6690-2",
                                "display": "Leukocytes [#/volume] in Blood"
                            }
                        ],
                        "text": "Total WBC count"
                    },
                    "valueQuantity": {
                        "value": 9000,
                        "unit": "/cumm",
                        "system": "http://unitsofmeasure.org",
                        "code": "/uL"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 4000,
                                "unit": "/cumm",
                                "system": "http://unitsofmeasure.org",
                                "code": "/uL"
                            },
                            "high": {
                                "value": 11000,
                                "unit": "/cumm",
                                "system": "http://unitsofmeasure.org",
                                "code": "/uL"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "770-8",
                                "display": "Neutrophils [Percent] in Blood by Automated count"
                            }
                        ],
                        "text": "Neutrophils"
                    },
                    "valueQuantity": {
                        "value": 60,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 50,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            },
                            "high": {
                                "value": 62,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "771-6",
                                "display": "Lymphocytes [Percent] in Blood by Automated count"
                            }
                        ],
                        "text": "Lymphocytes"
                    },
                    "valueQuantity": {
                        "value": 31,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 20,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            },
                            "high": {
                                "value": 40,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "713-8",
                                "display": "Eosinophils [Percent] in Blood by Automated count"
                            }
                        ],
                        "text": "Eosinophils"
                    },
                    "valueQuantity": {
                        "value": 1,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 0,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            },
                            "high": {
                                "value": 6,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "775-7",
                                "display": "Monocytes [Percent] in Blood by Automated count"
                            }
                        ],
                        "text": "Monocytes"
                    },
                    "valueQuantity": {
                        "value": 7,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 0,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            },
                            "high": {
                                "value": 10,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "706-2",
                                "display": "Basophils [Percent] in Blood by Automated count"
                            }
                        ],
                        "text": "Basophils"
                    },
                    "valueQuantity": {
                        "value": 1,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 0,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            },
                            "high": {
                                "value": 2,
                                "unit": "%",
                                "system": "http://unitsofmeasure.org",
                                "code": "%"
                            }
                        }
                    ]
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "777-3",
                                "display": "Platelets [#/volume] in Blood"
                            }
                        ],
                        "text": "Platelet Count"
                    },
                    "valueQuantity": {
                        "value": 150000,
                        "unit": "/cumm",
                        "system": "http://unitsofmeasure.org",
                        "code": "/uL"
                    },
                    "interpretation": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                    "code": "B",
                                    "display": "Borderline"
                                }
                            ]
                        }
                    ],
                    "referenceRange": [
                        {
                            "low": {
                                "value": 150000,
                                "unit": "/cumm",
                                "system": "http://unitsofmeasure.org",
                                "code": "/uL"
                            },
                            "high": {
                                "value": 410000,
                                "unit": "/cumm",
                                "system": "http://unitsofmeasure.org",
                                "code": "/uL"
                            }
                        }
                    ]
                }
            ]
        }
        
        # Retornamos el JSON completo serializado como texto
        return json.dumps(mock_observation)