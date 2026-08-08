import os
from pypdf import PdfReader, PdfWriter

# ==========================================
# PARÁMETROS DE CONFIGURACIÓN
# ==========================================
# Reemplaza con la ruta completa o relativa de tu archivo PDF protegido
RUTA_ARCHIVO = r"/mnt/c/Users/activ/Downloads/Resultados.20620339.BH.QS.GralOrin.Densitometria.pwd01051973 (3).pdf"

# Contraseña para desbloquear el archivo
CONTRASENA = "01051973"


def desbloquear_pdf(ruta_entrada, password):
    # Verificar si el archivo existe
    if not os.path.exists(ruta_entrada):
        print(f"Error: No se encontró el archivo en la ruta: {ruta_entrada}")
        return

    # Obtener el directorio, el nombre base y la extensión del archivo original
    directorio, nombre_archivo = os.path.split(ruta_entrada)
    nombre_base, extension = os.path.splitext(nombre_archivo)

    # Construir la ruta de salida con el sufijo _desbloqueado
    nombre_salida = f"{nombre_base}_desbloqueado{extension}"
    if directorio:
        ruta_salida = os.path.join(directorio, nombre_salida)
    else:
        ruta_salida = nombre_salida

    try:
        # Leer el PDF protegido
        lector = PdfReader(ruta_entrada)

        # Desencriptar si es necesario
        if lector.is_encrypted:
            resultado = lector.decrypt(password)
            if resultado == 0:
                print(
                    "Error: La contraseña es incorrecta o no se pudo descifrar el archivo."
                )
                return

        # Escribir el nuevo PDF sin contraseña
        escritor = PdfWriter()
        for pagina in lector.pages:
            escritor.add_page(pagina)

        # Guardar el archivo resultante (reemplaza si ya existe)
        with open(ruta_salida, "wb") as archivo_salida:
            escritor.write(archivo_salida)

        print(f"¡Éxito! Archivo desbloqueado guardado en:\n{ruta_salida}")

    except Exception as e:
        print(f"Ocurrió un error al procesar el archivo: {e}")


if __name__ == "__main__":
    desbloquear_pdf(RUTA_ARCHIVO, CONTRASENA)