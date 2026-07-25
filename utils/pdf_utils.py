# utils/pdf_utils.py
import io
from pypdf import PdfReader, PdfWriter
from pypdf.errors import FileNotDecryptedError


class PdfPasswordRequiredError(Exception):
    """Se lanza cuando el PDF está protegido con contraseña y no se proporcionó una."""
    pass


class PdfIncorrectPasswordError(Exception):
    """Se lanza cuando la contraseña proporcionada no es válida."""
    pass


class PdfUtils:

    @staticmethod
    def is_locked(file_content: bytes) -> bool:
        """
        Revisa si el archivo PDF está protegido con contraseña.
        """
        reader = PdfReader(io.BytesIO(file_content))
        return reader.is_encrypted

    @staticmethod
    def unlock_pdf(file_content: bytes, password: str | None = None) -> bytes:
        """
        Si el PDF está bloqueado:
            - Si se provee password, intenta desbloquearlo y retorna los bytes ya desencriptados.
            - Si no se provee password, lanza PdfPasswordRequiredError.
        Si NO está bloqueado, retorna el mismo contenido sin modificar.
        """
        reader = PdfReader(io.BytesIO(file_content))

        if not reader.is_encrypted:
            return file_content

        if not password:
            raise PdfPasswordRequiredError(
                "El archivo PDF está protegido con contraseña. Debe proporcionarla."
            )

        result = reader.decrypt(password)
        if result == 0:
            raise PdfIncorrectPasswordError("La contraseña proporcionada es incorrecta.")

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        return output_buffer.getvalue()

    @staticmethod
    def is_pdf(file_content: bytes) -> bool:
        """
        Detecta si el contenido corresponde a un PDF revisando la firma binaria (%PDF-).
        Más confiable que confiar en la extensión del archivo.
        """
        return file_content[:5] == b"%PDF-"