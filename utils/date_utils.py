"""
Utils para manipulação de datas.
"""
from datetime import datetime, date
import re


def validar_data(data_str: str) -> bool:
    """Valida se a string é uma data válida."""
    formatos = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d %m %Y",  # Novos formatos
        "%d de %B de %Y",
        "%B de %Y",
    ]
    for fmt in formatos:
        try:
            datetime.strptime(data_str, fmt)
            return True
        except ValueError:
            continue
    return False


def data_eh_futura(data_str: str) -> bool:
    """Verifica se a data é futura em relação ao dia atual."""
    hoje = date.today()
    data_obj = converter_data(data_str)
    if data_obj is None:
        return False
    return data_obj >= hoje


def converter_data(data_str: str) -> date | None:
    """Converte string para date no formato YYYY-MM-DD."""
    formatos = [
        ("%Y-%m-%d", "%Y-%m-%d"),
        ("%d/%m/%Y", "%Y-%m-%d"),
        ("%d-%m-%Y", "%Y-%m-%d"),
        ("%Y/%m/%d", "%Y-%m-%d"),
        ("%d %m %Y", "%d %m %Y"),  # Novos formatos
        ("%d de %B de %Y", "%d de %B de %Y"),
        ("%B de %Y", "%B de %Y"),
    ]
    for input_fmt, _ in formatos:
        try:
            dt = datetime.strptime(data_str, input_fmt)
            return dt.date()
        except ValueError:
            continue
    return None


def formatar_data_iso(data_str: str) -> str | None:
    """Converte data para formato YYYY-MM-DD."""
    data_obj = converter_data(data_str)
    if data_obj:
        return data_obj.isoformat()
    return None