import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("GOOGLE_API_KEY", "fake-key-para-pruebas")

from fastapi.testclient import TestClient
import main
from providers.mock_llm_provider import MockLLMProvider
from services.lab_service import LabAnalyzerService

# Usamos tu MockLLMProvider real, sin modificarlo. Le agregamos un "spy" desde
# afuera para poder verificar qué mime_type le llegó en cada llamada, sin
# tocar la clase original.
mock_provider = MockLLMProvider()
received_mime_types = []
_original_ask_with_file = mock_provider.ask_with_file


def _spy_ask_with_file(prompt, file_bytes, mime_type="application/pdf"):
    received_mime_types.append(mime_type)
    return _original_ask_with_file(prompt, file_bytes, mime_type)


mock_provider.ask_with_file = _spy_ask_with_file

# Sustituimos el lab_service real de main.py por uno que usa el mock,
# SOLO para estas pruebas.
main.lab_service = LabAnalyzerService(llm_provider=mock_provider)

client = TestClient(main.app)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"contenido binario simulado de una imagen"
PDF_BYTES = b"%PDF-1.4\n" + b"contenido simulado de un pdf"
FAKE_EXE = b"contenido que no es ni pdf ni imagen"


def setup_function():
    # Limpiamos el registro de llamadas antes de cada test
    received_mime_types.clear()


def test_upload_png_returns_200_and_json_csv_data():
    response = client.post(
        "/api/v1/analyze-lab",
        files={"file": ("resultado.png", PNG_BYTES, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "json_data" in data
    assert "csv_data" in data
    assert data["json_data"]["resourceType"] == "Observation"
    # Confirmamos que el mime_type real (image/png) llegó hasta el provider
    assert received_mime_types == ["image/png"]


def test_upload_pdf_still_works_as_before():
    response = client.post(
        "/api/v1/analyze-lab",
        files={"file": ("resultado.pdf", PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 200
    assert received_mime_types == ["application/pdf"]


def test_upload_unsupported_file_returns_400():
    response = client.post(
        "/api/v1/analyze-lab",
        files={"file": ("virus.exe", FAKE_EXE, "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "no soportado" in response.json()["detail"].lower()
    # No debió siquiera intentar llamar al LLM
    assert received_mime_types == []


def test_upload_empty_file_returns_400():
    response = client.post(
        "/api/v1/analyze-lab",
        files={"file": ("vacio.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert received_mime_types == []


def test_mime_type_detected_even_if_browser_lies():
    # El navegador dice que es un PDF, pero los bytes son de un PNG real.
    # El sistema debe confiar en los magic bytes, no en el header.
    response = client.post(
        "/api/v1/analyze-lab",
        files={"file": ("foto_disfrazada.pdf", PNG_BYTES, "application/pdf")},
    )
    assert response.status_code == 200
    assert received_mime_types == ["image/png"]