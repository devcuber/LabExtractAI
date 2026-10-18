import asyncio
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import download_lab_extraction_csv, get_lab_extraction_result
from models.lab_extraction_request import LabExtractionRequest, LabExtractionStatus
from services.lab_service import (
    ExtractionRequestFailedError,
    ExtractionRequestNotFoundError,
    ExtractionResultMissingError,
    ExtractionResultNotReadyError,
    LabAnalyzerService,
)


def run(coroutine):
    return asyncio.run(coroutine)


def make_request(status, result_json=None, error_message=None):
    return LabExtractionRequest(
        id=uuid4(),
        user_id=uuid4(),
        file_content=b"content",
        mime_type="image/png",
        original_filename="estudio.png",
        status=status,
        result_json=result_json,
        error_message=error_message,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc) if status in {LabExtractionStatus.COMPLETED, LabExtractionStatus.FAILED} else None,
    )


def make_service(request):
    repository = SimpleNamespace(get_by_id=AsyncMock(return_value=request))
    return LabAnalyzerService(SimpleNamespace(), repository), repository


def test_get_extraction_result_returns_completed_json():
    result_json = {"resourceType": "Observation", "status": "final"}
    request = make_request(LabExtractionStatus.COMPLETED, result_json=result_json)
    service, repository = make_service(request)

    assert run(service.get_extraction_result(request.id, request.user_id)) == result_json
    repository.get_by_id.assert_awaited_once_with(request.id, request.user_id)


@pytest.mark.parametrize("status", [LabExtractionStatus.PENDING, LabExtractionStatus.PROCESSING])
def test_get_extraction_result_rejects_unfinished_request(status):
    request = make_request(status)
    service, _ = make_service(request)

    with pytest.raises(ExtractionResultNotReadyError) as error:
        run(service.get_extraction_result(request.id, request.user_id))

    assert error.value.status == status


def test_get_extraction_result_rejects_missing_request():
    request_id = uuid4()
    service, _ = make_service(None)

    with pytest.raises(ExtractionRequestNotFoundError):
        run(service.get_extraction_result(request_id, uuid4()))


def test_get_extraction_result_rejects_failed_request():
    request = make_request(LabExtractionStatus.FAILED, error_message="LLM unavailable")
    service, _ = make_service(request)

    with pytest.raises(ExtractionRequestFailedError) as error:
        run(service.get_extraction_result(request.id, request.user_id))

    assert error.value.error_message == "LLM unavailable"


def test_get_extraction_result_rejects_completed_request_without_json():
    request = make_request(LabExtractionStatus.COMPLETED)
    service, _ = make_service(request)

    with pytest.raises(ExtractionResultMissingError):
        run(service.get_extraction_result(request.id, request.user_id))


def test_get_extraction_csv_returns_csv_and_original_filename():
    result_json = {
        "resourceType": "Observation",
        "status": "final",
        "code": {"text": "Glucosa"},
        "valueQuantity": {"value": 95, "unit": "mg/dL"},
    }
    request = make_request(LabExtractionStatus.COMPLETED, result_json=result_json)
    request.original_filename = "biometría hemática.pdf"
    service, repository = make_service(request)

    csv_data, original_filename = run(service.get_extraction_csv(request.id, request.user_id))

    assert original_filename == "biometría hemática.pdf"
    assert "Status,,,final,," in csv_data
    assert "Texto Original,Código LOINC,Descripción LOINC,Valor,Rango de Referencia,Interpretación" in csv_data
    assert "Glucosa,,,95 mg/dL,," in csv_data
    repository.get_by_id.assert_awaited_once_with(request.id, request.user_id)


@pytest.mark.parametrize("status", [LabExtractionStatus.PENDING, LabExtractionStatus.PROCESSING])
def test_get_extraction_csv_rejects_unfinished_request(status):
    request = make_request(status)
    service, _ = make_service(request)

    with pytest.raises(ExtractionResultNotReadyError):
        run(service.get_extraction_csv(request.id, request.user_id))


def test_get_extraction_csv_rejects_missing_request():
    service, _ = make_service(None)

    with pytest.raises(ExtractionRequestNotFoundError):
        run(service.get_extraction_csv(uuid4(), uuid4()))


def test_get_extraction_csv_rejects_failed_request():
    request = make_request(LabExtractionStatus.FAILED, error_message="LLM unavailable")
    service, _ = make_service(request)

    with pytest.raises(ExtractionRequestFailedError):
        run(service.get_extraction_csv(request.id, request.user_id))


def test_get_extraction_csv_rejects_completed_request_without_json():
    request = make_request(LabExtractionStatus.COMPLETED)
    service, _ = make_service(request)

    with pytest.raises(ExtractionResultMissingError):
        run(service.get_extraction_csv(request.id, request.user_id))


def test_csv_endpoint_returns_download_response_with_utf8_filename():
    request_id = uuid4()
    service = SimpleNamespace(
        get_extraction_csv=AsyncMock(return_value=("Status,final", "biometría hemática.pdf"))
    )

    response = run(download_lab_extraction_csv(request_id, uuid4(), service))

    assert response.status_code == 200
    assert response.media_type == "text/csv"
    assert response.charset == "utf-8"
    assert response.body == b"Status,final"
    assert response.headers["content-disposition"] == (
        "attachment; filename=\"biometría hemática_clinical_data.csv\"; "
        "filename*=UTF-8''biometr%C3%ADa%20hem%C3%A1tica_clinical_data.csv"
    )
    service.get_extraction_csv.assert_awaited_once_with(request_id, ANY)


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (ExtractionRequestNotFoundError(), 404, "La solicitud de extracción no existe."),
        (
            ExtractionResultNotReadyError(LabExtractionStatus.PROCESSING),
            409,
            {"message": "La extracción aún no está completada.", "status": "processing"},
        ),
        (
            ExtractionRequestFailedError("LLM unavailable"),
            422,
            {"message": "La extracción falló.", "error": "LLM unavailable"},
        ),
        (
            ExtractionResultMissingError(),
            500,
            "La solicitud está completada, pero no contiene resultado.",
        ),
    ],
)
def test_csv_endpoint_maps_domain_errors(error, expected_status, expected_detail):
    service = SimpleNamespace(get_extraction_csv=AsyncMock(side_effect=error))

    with pytest.raises(HTTPException) as raised:
        run(download_lab_extraction_csv(uuid4(), uuid4(), service))

    assert raised.value.status_code == expected_status
    assert raised.value.detail == expected_detail

    request_id = uuid4()
    service = SimpleNamespace(get_extraction_result=AsyncMock(return_value={"resourceType": "Observation"}))

    assert run(get_lab_extraction_result(request_id, uuid4(), service)) == {"resourceType": "Observation"}


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (ExtractionRequestNotFoundError(), 404, "La solicitud de extracción no existe."),
        (
            ExtractionResultNotReadyError(LabExtractionStatus.PROCESSING),
            409,
            {"message": "La extracción aún no está completada.", "status": "processing"},
        ),
        (
            ExtractionRequestFailedError("LLM unavailable"),
            422,
            {"message": "La extracción falló.", "error": "LLM unavailable"},
        ),
        (
            ExtractionResultMissingError(),
            500,
            "La solicitud está completada, pero no contiene resultado.",
        ),
    ],
)
def test_endpoint_maps_domain_errors(error, expected_status, expected_detail):
    service = SimpleNamespace(get_extraction_result=AsyncMock(side_effect=error))

    with pytest.raises(HTTPException) as raised:
        run(get_lab_extraction_result(uuid4(), uuid4(), service))

    assert raised.value.status_code == expected_status
    assert raised.value.detail == expected_detail
