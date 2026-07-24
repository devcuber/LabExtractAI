import io
import csv

def dict_to_csv_string(flat_dict: dict) -> str:
    """Convierte un diccionario plano en un string CSV de una sola fila (cabeceras y valores)."""
    headers = list(flat_dict.keys())
    values = [flat_dict[h] for h in headers]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(values)

    return output.getvalue().strip()