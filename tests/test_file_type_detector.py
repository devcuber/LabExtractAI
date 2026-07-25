import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.file_type_detector import FileTypeDetector

detector = FileTypeDetector()


def test_detect_pdf_by_magic_bytes():
    content = b"%PDF-1.4\n%resto del archivo..."
    assert detector.detect(content, "resultado.pdf", "application/pdf") == "application/pdf"


def test_detect_png_by_magic_bytes():
    content = b"\x89PNG\r\n\x1a\n" + b"resto de bytes binarios..."
    assert detector.detect(content, "foto.png", None) == "image/png"


def test_detect_jpeg_by_magic_bytes():
    content = b"\xff\xd8\xff\xe0" + b"resto de bytes binarios..."
    assert detector.detect(content, "foto.jpg", None) == "image/jpeg"


def test_detect_webp_by_magic_bytes():
    content = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"resto..."
    assert detector.detect(content, "foto.webp", None) == "image/webp"


def test_detect_ignores_wrong_declared_content_type_when_bytes_are_recognizable():
    # El navegador "miente" diciendo que es PDF, pero los bytes son de un PNG real
    content = b"\x89PNG\r\n\x1a\n" + b"resto..."
    assert detector.detect(content, "foto.png", "application/pdf") == "image/png"


def test_detect_falls_back_to_extension_when_bytes_are_unrecognizable():
    content = b"contenido raro sin firma reconocible"
    assert detector.detect(content, "archivo.jpeg", None) == "image/jpeg"


def test_detect_returns_octet_stream_for_unknown_file():
    content = b"contenido totalmente desconocido"
    assert detector.detect(content, "archivo.exe", None) == "application/octet-stream"


def test_is_allowed_true_for_supported_types():
    assert detector.is_allowed("application/pdf") is True
    assert detector.is_allowed("image/png") is True
    assert detector.is_allowed("image/jpeg") is True
    assert detector.is_allowed("image/webp") is True


def test_is_allowed_false_for_unsupported_types():
    assert detector.is_allowed("application/octet-stream") is False
    assert detector.is_allowed("video/mp4") is False