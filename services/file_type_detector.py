import os


class FileTypeDetector:
    """
    Responsable única y exclusivamente de determinar el mime_type real
    de un archivo subido y validar si está soportado por el sistema.

    Detecta el tipo inspeccionando los 'magic bytes' (firma binaria) del
    contenido, en lugar de confiar ciegamente en el Content-Type que
    declara el navegador (que puede venir vacío o ser incorrecto).
    """

    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
    }

    # Extensiones aceptadas, usadas solo como respaldo/validación cruzada
    ALLOWED_EXTENSIONS = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }

    def detect(self, content: bytes, filename: str | None, declared_content_type: str | None) -> str:
        """
        Devuelve el mime_type real del archivo. Si no puede reconocer la
        firma binaria, recurre al content_type declarado y luego a la
        extensión del nombre de archivo como último respaldo.
        """
        header = content[:16]

        if header.startswith(b"%PDF"):
            return "application/pdf"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if header[0:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "image/webp"

        if declared_content_type in self.ALLOWED_MIME_TYPES:
            return declared_content_type

        ext = os.path.splitext(filename or "")[1].lower()
        if ext in self.ALLOWED_EXTENSIONS:
            return self.ALLOWED_EXTENSIONS[ext]

        return "application/octet-stream"

    def is_allowed(self, mime_type: str) -> bool:
        return mime_type in self.ALLOWED_MIME_TYPES