import asyncio
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.lab_extraction_request import LabExtractionRequest, LabExtractionStatus
from services.lab_service import LabAnalyzerService
from utils.file_utils import UnsupportedFileTypeError
from utils.pdf_utils import PdfIncorrectPasswordError, PdfPasswordRequiredError, PdfUtils


PNG_CONTENT = b"\x89PNG\r\n\x1a\n" + b"laboratory-image"
PDF_CONTENT = b"%PDF-1.7\nprotected-or-unprotected-content"


def run(coroutine):
    return asyncio.run(coroutine)


def created_request(
    file_content: bytes = PNG_CONTENT,
    mime_type: str = "image/png",
    original_filename: str = "estudio.png",
) -> LabExtractionRequest:
    return LabExtractionRequest(
        id=uuid4(),
        file_content=file_content,
        mime_type=mime_type,
        original_filename=original_filename,
        status=LabExtractionStatus.PENDING,
        result_json=None,
        error_message=None,
        created_at=datetime.now(timezone.utc),
        completed_at=None,
    )


def make_service(repository):
    return LabAnalyzerService(
        llm_provider=SimpleNamespace(),
        extraction_request_repository=repository,
    )


def make_repository(result=None, exception=None):
    create = AsyncMock(return_value=result)
    if exception is not None:
        create.side_effect = exception
    return SimpleNamespace(create=create)


def test_enqueue_valid_image_persists_detected_mime_and_original_bytes():
    saved = created_request()
    repository = make_repository(result=saved)
    service = make_service(repository)

    result = run(service.enqueue_for_extraction(PNG_CONTENT, "  estudio.png  "))

    assert result == saved
    repository.create.assert_awaited_once()
    data = repository.create.await_args.args[0]
    assert data.file_content == PNG_CONTENT
    assert data.mime_type == "image/png"
    assert data.original_filename == "estudio.png"


def test_enqueue_unprotected_pdf_preserves_original_bytes(monkeypatch):
    saved = created_request(PDF_CONTENT, "application/pdf", "estudio.pdf")
    repository = make_repository(result=saved)
    service = make_service(repository)
    unlock_pdf = AsyncMock()

    def return_original(content, password):
        return content

    monkeypatch.setattr(PdfUtils, "unlock_pdf", staticmethod(return_original))

    result = run(service.enqueue_for_extraction(PDF_CONTENT, "estudio.pdf"))

    assert result == saved
    data = repository.create.await_args.args[0]
    assert data.file_content == PDF_CONTENT
    assert data.mime_type == "application/pdf"


def test_enqueue_protected_pdf_persists_unlocked_bytes(monkeypatch):
    unlocked_content = b"%PDF-1.7\nunlocked-content"
    saved = created_request(unlocked_content, "application/pdf", "seguro.pdf")
    repository = make_repository(result=saved)
    service = make_service(repository)

    def unlock_pdf(content, password):
        assert content == PDF_CONTENT
        assert password == "correcta"
        return unlocked_content

    monkeypatch.setattr(PdfUtils, "unlock_pdf", staticmethod(unlock_pdf))

    run(service.enqueue_for_extraction(PDF_CONTENT, "seguro.pdf", password="correcta"))

    data = repository.create.await_args.args[0]
    assert data.file_content == unlocked_content
    assert data.file_content != PDF_CONTENT
    assert data.mime_type == "application/pdf"


@pytest.mark.parametrize("filename", [None, "", "   "])
def test_enqueue_rejects_missing_original_filename(filename):
    repository = make_repository(result=created_request())
    service = make_service(repository)

    with pytest.raises(ValueError, match="nombre original"):
        run(service.enqueue_for_extraction(PNG_CONTENT, filename))

    repository.create.assert_not_awaited()


def test_enqueue_rejects_empty_file():
    repository = make_repository(result=created_request())
    service = make_service(repository)

    with pytest.raises(ValueError, match="archivo está vacío"):
        run(service.enqueue_for_extraction(b"", "estudio.png"))

    repository.create.assert_not_awaited()


def test_enqueue_rejects_unsupported_file_type():
    repository = make_repository(result=created_request())
    service = make_service(repository)

    with pytest.raises(UnsupportedFileTypeError):
        run(service.enqueue_for_extraction(b"unrecognized-data", "estudio.exe"))

    repository.create.assert_not_awaited()


def test_enqueue_propagates_password_required_error(monkeypatch):
    repository = make_repository(result=created_request())
    service = make_service(repository)

    def unlock_pdf(content, password):
        raise PdfPasswordRequiredError()

    monkeypatch.setattr(PdfUtils, "unlock_pdf", staticmethod(unlock_pdf))

    with pytest.raises(PdfPasswordRequiredError):
        run(service.enqueue_for_extraction(PDF_CONTENT, "protegido.pdf"))

    repository.create.assert_not_awaited()


def test_enqueue_propagates_incorrect_password_error(monkeypatch):
    repository = make_repository(result=created_request())
    service = make_service(repository)

    def unlock_pdf(content, password):
        raise PdfIncorrectPasswordError()

    monkeypatch.setattr(PdfUtils, "unlock_pdf", staticmethod(unlock_pdf))

    with pytest.raises(PdfIncorrectPasswordError):
        run(service.enqueue_for_extraction(PDF_CONTENT, "protegido.pdf", password="incorrecta"))

    repository.create.assert_not_awaited()


def test_enqueue_propagates_repository_error():
    database_error = RuntimeError("database unavailable")
    repository = make_repository(exception=database_error)
    service = make_service(repository)

    with pytest.raises(RuntimeError, match="database unavailable"):
        run(service.enqueue_for_extraction(PNG_CONTENT, "estudio.png"))

    repository.create.assert_awaited_once()
