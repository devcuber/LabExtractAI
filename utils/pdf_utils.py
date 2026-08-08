# utils/pdf_utils.py
import io
import logging
from pypdf import PdfReader, PdfWriter
from pypdf.errors import FileNotDecryptedError

logger = logging.getLogger(__name__)


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
        if not reader.is_encrypted:
            return False

        try:
            return reader.decrypt("") == 0
        except Exception:
            return True

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
            logger.info("El archivo PDF no requiere contraseña.")
            return file_content

        logger.info("El archivo PDF requiere contraseña para ser desbloqueado.")

        if not password:
            logger.info("No se proporcionó contraseña; intentando desbloquear con contraseña vacía.")
            result = reader.decrypt("")
            if result != 0:
                logger.info("PDF desbloqueado con contraseña vacía.")
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)

                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                logger.info("PDF desbloqueado con éxito con contraseña vacía.")
                return output_buffer.getvalue()

            logger.error("No se proporcionó contraseña para un PDF protegido.")
            raise PdfPasswordRequiredError(
                "El archivo PDF está protegido con contraseña. Debe proporcionarla."
            )

        logger.info("Contraseña propuesta para PDF: ***")
        result = reader.decrypt(password)
        if result == 0:
            logger.error("La contraseña proporcionada no es correcta.")
            raise PdfIncorrectPasswordError("La contraseña proporcionada es incorrecta.")

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        logger.info("PDF desbloqueado con éxito.")
        return output_buffer.getvalue()

    @staticmethod
    def is_pdf(file_content: bytes) -> bool:
        """
        Detecta si el contenido corresponde a un PDF revisando la firma binaria (%PDF-).
        Más confiable que confiar en la extensión del archivo.
        """
        return file_content[:5] == b"%PDF-"